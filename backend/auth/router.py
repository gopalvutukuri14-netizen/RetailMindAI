import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.database.models import User, OTPChallenge, UserPreference
from .schemas import (
    SignupRequest,
    VerifyEmailRequest,
    ResendOtpRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from .security import (
    hash_password,
    verify_password,
    validate_password_strength,
    generate_otp,
    hash_otp,
    verify_otp_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    OTP_EXPIRY_MINUTES,
    OTP_RESEND_COOLDOWN_SECONDS,
    OTP_MAX_ATTEMPTS,
)
from .email_service import send_signup_verification_otp, send_password_reset_otp
from .dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    if req.password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    is_strong, msg = validate_password_strength(req.password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    existing_user_by_email = db.query(User).filter(User.email == req.email).first()
    if existing_user_by_email:
        if existing_user_by_email.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists.",
            )
        else:
            existing_user_by_email.username = req.username
            existing_user_by_email.password_hash = hash_password(req.password)
            user = existing_user_by_email
    else:
        existing_user_by_name = db.query(User).filter(User.username == req.username).first()
        if existing_user_by_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken.",
            )

        user = User(
            username=req.username,
            email=req.email,
            password_hash=hash_password(req.password),
            is_verified=False,
        )
        db.add(user)
        pref = UserPreference(user=user)
        db.add(pref)

    db.commit()
    db.refresh(user)

    db.query(OTPChallenge).filter(
        OTPChallenge.email == req.email,
        OTPChallenge.purpose == "signup_verify",
        OTPChallenge.is_used == False,
    ).update({"is_used": True})

    plain_otp = generate_otp()
    hashed = hash_otp(plain_otp, salt=req.email)
    expires = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    challenge = OTPChallenge(
        user_id=user.id,
        email=req.email,
        purpose="signup_verify",
        otp_hash=hashed,
        expires_at=expires,
        max_attempts=OTP_MAX_ATTEMPTS,
    )
    db.add(challenge)
    db.commit()

    send_signup_verification_otp(req.email, req.username, plain_otp, OTP_EXPIRY_MINUTES)

    return {
        "message": "Signup successful. Please enter the verification code sent to your email.",
        "email": req.email,
    }


@router.post("/verify-email", response_model=TokenResponse)
def verify_email(req: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    challenge = (
        db.query(OTPChallenge)
        .filter(
            OTPChallenge.email == req.email,
            OTPChallenge.purpose == "signup_verify",
            OTPChallenge.is_used == False,
        )
        .order_by(OTPChallenge.created_at.desc())
        .first()
    )

    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending verification code found. Please request a new one.",
        )

    if challenge.is_expired():
        challenge.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one.",
        )

    if challenge.attempts >= challenge.max_attempts:
        challenge.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum verification attempts exceeded. Please request a new code.",
        )

    if not verify_otp_hash(req.otp, challenge.otp_hash, salt=req.email):
        challenge.attempts += 1
        db.commit()
        remaining = challenge.max_attempts - challenge.attempts
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification code. {remaining} attempt(s) remaining.",
        )

    challenge.is_used = True
    user.is_verified = True
    db.commit()

    token = create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email,
        token_version=user.token_version,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/resend-otp")
def resend_otp(req: ResendOtpRequest, db: Session = Depends(get_db)):
    if req.purpose not in ("signup_verify", "password_reset"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP purpose.",
        )

    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        return {"message": "If this email is registered, a new verification code has been sent."}

    latest = (
        db.query(OTPChallenge)
        .filter(OTPChallenge.email == req.email, OTPChallenge.purpose == req.purpose)
        .order_by(OTPChallenge.created_at.desc())
        .first()
    )

    if latest:
        now = datetime.now(timezone.utc)
        created = latest.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        elapsed = (now - created).total_seconds()
        if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
            wait_seconds = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {wait_seconds} second(s) before requesting another code.",
            )

    db.query(OTPChallenge).filter(
        OTPChallenge.email == req.email,
        OTPChallenge.purpose == req.purpose,
        OTPChallenge.is_used == False,
    ).update({"is_used": True})

    plain_otp = generate_otp()
    hashed = hash_otp(plain_otp, salt=req.email)
    expires = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    challenge = OTPChallenge(
        user_id=user.id,
        email=req.email,
        purpose=req.purpose,
        otp_hash=hashed,
        expires_at=expires,
        max_attempts=OTP_MAX_ATTEMPTS,
    )
    db.add(challenge)
    db.commit()

    if req.purpose == "signup_verify":
        send_signup_verification_otp(req.email, user.username, plain_otp, OTP_EXPIRY_MINUTES)
    else:
        send_password_reset_otp(req.email, user.username, plain_otp, OTP_EXPIRY_MINUTES)

    return {"message": "A new verification code has been sent to your email."}


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter((User.username == req.username_or_email) | (User.email == req.username_or_email))
        .first()
    )

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email before logging in.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(
        user_id=user.id,
        username=user.username,
        email=user.email,
        token_version=user.token_version,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter((User.username == req.email_or_username) | (User.email == req.email_or_username))
        .first()
    )

    safe_msg = "If an account matches that email or username, a password reset code has been sent."

    if not user or not user.email:
        return {"message": safe_msg}

    db.query(OTPChallenge).filter(
        OTPChallenge.email == user.email,
        OTPChallenge.purpose == "password_reset",
        OTPChallenge.is_used == False,
    ).update({"is_used": True})

    plain_otp = generate_otp()
    hashed = hash_otp(plain_otp, salt=user.email)
    expires = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    challenge = OTPChallenge(
        user_id=user.id,
        email=user.email,
        purpose="password_reset",
        otp_hash=hashed,
        expires_at=expires,
        max_attempts=OTP_MAX_ATTEMPTS,
    )
    db.add(challenge)
    db.commit()

    send_password_reset_otp(user.email, user.username, plain_otp, OTP_EXPIRY_MINUTES)
    return {"message": safe_msg}


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    if req.new_password != req.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    is_strong, msg = validate_password_strength(req.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    challenge = (
        db.query(OTPChallenge)
        .filter(
            OTPChallenge.email == req.email,
            OTPChallenge.purpose == "password_reset",
            OTPChallenge.is_used == False,
        )
        .order_by(OTPChallenge.created_at.desc())
        .first()
    )

    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending password reset code found.",
        )

    if challenge.is_expired():
        challenge.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset code has expired. Please request a new one.",
        )

    if challenge.attempts >= challenge.max_attempts:
        challenge.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum attempts exceeded. Please request a new code.",
        )

    if not verify_otp_hash(req.otp, challenge.otp_hash, salt=req.email):
        challenge.attempts += 1
        db.commit()
        remaining = challenge.max_attempts - challenge.attempts
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reset code. {remaining} attempt(s) remaining.",
        )

    challenge.is_used = True
    user.password_hash = hash_password(req.new_password)
    user.token_version += 1
    user.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Password reset successfully. Please log in with your new password."}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
