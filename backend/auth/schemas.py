from typing import Optional
from datetime import datetime
import re
from pydantic import BaseModel, Field, field_validator

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: str = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Account password")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")

    @field_validator("username")
    def validate_username(cls, v: str) -> str:
        clean = v.strip().lower()
        if not clean.replace("_", "").isalnum():
            raise ValueError("Username may only contain letters, numbers, and underscores.")
        return clean

    @field_validator("email")
    def normalize_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address format.")
        return clean


class VerifyEmailRequest(BaseModel):
    email: str
    otp: str = Field(..., min_length=6, max_length=6)

    @field_validator("email")
    def normalize_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address format.")
        return clean

    @field_validator("otp")
    def normalize_otp(cls, v: str) -> str:
        return v.strip()


class ResendOtpRequest(BaseModel):
    email: str
    purpose: str = Field("signup_verify", description="'signup_verify' or 'password_reset'")

    @field_validator("email")
    def normalize_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address format.")
        return clean


class LoginRequest(BaseModel):
    username_or_email: str = Field(..., description="Username or email address")
    password: str = Field(..., min_length=1)

    @field_validator("username_or_email")
    def normalize_identifier(cls, v: str) -> str:
        return v.strip().lower()


class ForgotPasswordRequest(BaseModel):
    email_or_username: str = Field(..., description="Registered email or username")

    @field_validator("email_or_username")
    def normalize_identifier(cls, v: str) -> str:
        return v.strip().lower()


class ResetPasswordRequest(BaseModel):
    email: str
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str = Field(..., min_length=8)

    @field_validator("email")
    def normalize_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address format.")
        return clean

    @field_validator("otp")
    def normalize_otp(cls, v: str) -> str:
        return v.strip()


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
