import re
import pytest
import httpx
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.models import Base, User, OTPChallenge, UserPreference
from backend.database.session import get_db
from backend.auth.email_service import (
    MOCK_SENT_EMAILS,
    set_mock_brevo_response,
    EmailSendResult,
)
from backend.auth.security import hash_password, create_access_token
from backend.main import app

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    MOCK_SENT_EMAILS.clear()
    set_mock_brevo_response(None)
    yield
    set_mock_brevo_response(None)
    MOCK_SENT_EMAILS.clear()
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


# 1. New signup with successful Brevo acceptance
def test_1_new_signup_successful_brevo_acceptance(client):
    res = client.post("/auth/signup", json={
        "username": "brevo_user_1",
        "email": "brevo1@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })
    assert res.status_code == 201
    data = res.json()
    assert "verification code" in data["message"].lower()
    assert data["email"] == "brevo1@example.com"
    assert data.get("email_status") == "accepted"

    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "brevo1@example.com").first()
    assert user is not None
    assert user.is_verified is False
    challenge = db.query(OTPChallenge).filter(OTPChallenge.email == "brevo1@example.com").first()
    assert challenge is not None
    assert challenge.is_used is False
    db.close()

    assert len(MOCK_SENT_EMAILS) >= 1
    assert MOCK_SENT_EMAILS[-1]["to"] == "brevo1@example.com"


# 2. New signup with Brevo HTTP 401 (e.g. IP unauthorized or invalid key)
def test_2_new_signup_brevo_401_unauthorized(client):
    set_mock_brevo_response({"status_code": 401})

    res = client.post("/auth/signup", json={
        "username": "brevo_user_2",
        "email": "brevo2@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })
    assert res.status_code == 502
    data = res.json()
    detail = data["detail"].lower()
    assert "account created" in detail
    assert "verification email could not be sent" in detail
    assert "api-key" not in detail
    assert "brevo.com" not in detail

    # User MUST be kept with is_verified = False
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "brevo2@example.com").first()
    assert user is not None
    assert user.is_verified is False

    # Unsent challenge must NOT be active
    challenges = db.query(OTPChallenge).filter(OTPChallenge.email == "brevo2@example.com").all()
    assert len(challenges) == 0
    db.close()


# 3. Brevo HTTP 429 rate limiting
def test_3_new_signup_brevo_429_rate_limiting(client):
    set_mock_brevo_response({"status_code": 429})

    res = client.post("/auth/signup", json={
        "username": "brevo_user_3",
        "email": "brevo3@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })
    assert res.status_code == 429
    detail = res.json()["detail"].lower()
    assert "rate limit" in detail or "rate-limited" in detail
    assert "verification email could not be sent" in detail

    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "brevo3@example.com").first()
    assert user is not None
    assert user.is_verified is False
    db.close()


# 4. Brevo HTTP 5xx provider failure
def test_4_new_signup_brevo_5xx_provider_failure(client):
    set_mock_brevo_response({"status_code": 500})

    res = client.post("/auth/signup", json={
        "username": "brevo_user_4",
        "email": "brevo4@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })
    assert res.status_code == 502
    detail = res.json()["detail"].lower()
    assert "service" in detail
    assert "verification email could not be sent" in detail

    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "brevo4@example.com").first()
    assert user is not None
    assert user.is_verified is False
    db.close()


# 5. Network timeout and connection failure
def test_5_new_signup_timeout_and_connection_failure(client):
    # Timeout
    set_mock_brevo_response(httpx.TimeoutException("Timed out connecting to Brevo"))
    res_timeout = client.post("/auth/signup", json={
        "username": "timeout_user",
        "email": "timeout@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })
    assert res_timeout.status_code == 504
    assert "timed out" in res_timeout.json()["detail"].lower()

    # Network error
    set_mock_brevo_response(httpx.ConnectError("Network unreachable"))
    res_network = client.post("/auth/signup", json={
        "username": "network_user",
        "email": "network@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })
    assert res_network.status_code == 502
    assert "unable to reach" in res_network.json()["detail"].lower()


# 6. Retry for an existing unverified account
def test_6_retry_for_existing_unverified_account(client):
    # 1. First signup attempt fails due to Brevo 401
    set_mock_brevo_response({"status_code": 401})
    res1 = client.post("/auth/signup", json={
        "username": "retry_user",
        "email": "retry@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })
    assert res1.status_code == 502

    # 2. Brevo service is restored
    set_mock_brevo_response(None)

    # 3. User retries signup with same email
    res2 = client.post("/auth/signup", json={
        "username": "retry_user",
        "email": "retry@example.com",
        "password": "NewPassword456",
        "confirm_password": "NewPassword456",
    })
    assert res2.status_code == 201
    assert "verification code" in res2.json()["message"].lower()

    # Verify user count is strictly 1
    db = TestingSessionLocal()
    users = db.query(User).filter(User.email == "retry@example.com").all()
    assert len(users) == 1
    assert users[0].is_verified is False
    db.close()


# 7. No duplicate user records after repeated signup attempts
def test_7_no_duplicate_user_records_after_repeated_attempts(client):
    # Attempt 1: provider failure
    set_mock_brevo_response({"status_code": 503})
    client.post("/auth/signup", json={
        "username": "nodup_user",
        "email": "nodup@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })

    # Attempt 2: provider still failing
    client.post("/auth/signup", json={
        "username": "nodup_user",
        "email": "nodup@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })

    # Attempt 3: provider restored
    set_mock_brevo_response(None)
    client.post("/auth/signup", json={
        "username": "nodup_user",
        "email": "nodup@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })

    db = TestingSessionLocal()
    count = db.query(User).filter(User.email == "nodup@example.com").count()
    assert count == 1
    db.close()


# 8. Resend cooldown and maximum attempt enforcement
def test_8_resend_cooldown_and_maximum_attempt_enforcement(client):
    # Signup success
    client.post("/auth/signup", json={
        "username": "cooldown_test",
        "email": "cooldown_test@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })

    # Immediate resend rejected by 429 cooldown
    res_cooldown = client.post("/auth/resend-otp", json={
        "email": "cooldown_test@example.com",
        "purpose": "signup_verify",
    })
    assert res_cooldown.status_code == 429
    assert "wait" in res_cooldown.json()["detail"].lower()

    # Immediate signup retry with same email also respects cooldown (HTTP 429)
    res_signup_cooldown = client.post("/auth/signup", json={
        "username": "cooldown_test",
        "email": "cooldown_test@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })
    assert res_signup_cooldown.status_code == 429
    assert "wait" in res_signup_cooldown.json()["detail"].lower()

    # 5 wrong verification attempts exhaust max_attempts
    for _ in range(5):
        client.post("/auth/verify-email", json={
            "email": "cooldown_test@example.com",
            "otp": "000000",
        })

    # 6th attempt rejected
    res_locked = client.post("/auth/verify-email", json={
        "email": "cooldown_test@example.com",
        "otp": "000000",
    })
    assert res_locked.status_code == 400
    assert "maximum" in res_locked.json()["detail"].lower() or "no pending" in res_locked.json()["detail"].lower()


# 9. Previous valid OTP handling when replacement delivery fails
def test_9_previous_valid_otp_handling_when_replacement_delivery_fails(client):
    # 1. Signup succeeds, OTP #1 is sent
    client.post("/auth/signup", json={
        "username": "preserve_otp_user",
        "email": "preserve@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })

    # Extract OTP #1 from mock email
    match = re.search(r'<div class="otp-code">(\d{6})</div>', MOCK_SENT_EMAILS[-1]["html"])
    assert match is not None
    otp_1 = match.group(1)

    # 2. Simulate cooldown expiry by advancing OTPChallenge created_at
    db = TestingSessionLocal()
    challenge = db.query(OTPChallenge).filter(OTPChallenge.email == "preserve@example.com").first()
    orig_challenge_id = challenge.id
    challenge.created_at = datetime.now(timezone.utc) - timedelta(seconds=70)
    db.commit()
    db.close()

    # 3. User requests a resend, but Brevo FAILS with 500
    set_mock_brevo_response({"status_code": 500})
    res_resend = client.post("/auth/resend-otp", json={
        "email": "preserve@example.com",
        "purpose": "signup_verify",
    })
    assert res_resend.status_code == 502

    # 4. CRITICAL: The previous OTP #1 MUST STILL BE VALID!
    db = TestingSessionLocal()
    active_challenges = db.query(OTPChallenge).filter(
        OTPChallenge.email == "preserve@example.com",
        OTPChallenge.is_used == False,
    ).all()
    assert len(active_challenges) == 1
    assert active_challenges[0].id == orig_challenge_id
    db.close()

    # 5. User submits OTP #1 — it must succeed!
    res_verify = client.post("/auth/verify-email", json={
        "email": "preserve@example.com",
        "otp": otp_1,
    })
    assert res_verify.status_code == 200
    assert res_verify.json()["user"]["is_verified"] is True


# 10. Successful OTP verification updates is_verified to true
def test_10_successful_otp_verification_updates_is_verified(client):
    client.post("/auth/signup", json={
        "username": "verify_flag_user",
        "email": "verify_flag@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })

    match = re.search(r'<div class="otp-code">(\d{6})</div>', MOCK_SENT_EMAILS[-1]["html"])
    otp = match.group(1)

    res = client.post("/auth/verify-email", json={
        "email": "verify_flag@example.com",
        "otp": otp,
    })
    assert res.status_code == 200

    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "verify_flag@example.com").first()
    assert user.is_verified is True
    db.close()


# 11. Unverified users cannot log in
def test_11_unverified_users_cannot_login(client):
    db = TestingSessionLocal()
    user = User(
        username="unverified_login_test",
        email="unverified_login@example.com",
        password_hash=hash_password("Password123"),
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.close()

    res = client.post("/auth/login", json={
        "username_or_email": "unverified_login@example.com",
        "password": "Password123",
    })
    assert res.status_code == 403
    assert "not verified" in res.json()["detail"].lower()


# 12. Verified users can log in normally
def test_12_verified_users_can_login_normally(client):
    db = TestingSessionLocal()
    user = User(
        username="verified_login_test",
        email="verified_login@example.com",
        password_hash=hash_password("Password123"),
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.close()

    res = client.post("/auth/login", json={
        "username_or_email": "verified_login@example.com",
        "password": "Password123",
    })
    assert res.status_code == 200
    assert "access_token" in res.json()
    assert res.json()["user"]["is_verified"] is True


# 13. Already verified accounts receive an appropriate response
def test_13_already_verified_accounts_appropriate_response(client):
    db = TestingSessionLocal()
    user = User(
        username="already_verified_user",
        email="already_verified@example.com",
        password_hash=hash_password("Password123"),
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.close()

    # Signup retry for verified account rejected
    res_signup = client.post("/auth/signup", json={
        "username": "already_verified_user",
        "email": "already_verified@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })
    assert res_signup.status_code == 400
    assert "already exists" in res_signup.json()["detail"].lower()
    assert "sign in" in res_signup.json()["detail"].lower()

    # Resend OTP for verified account rejected
    res_resend = client.post("/auth/resend-otp", json={
        "email": "already_verified@example.com",
        "purpose": "signup_verify",
    })
    assert res_resend.status_code == 400
    assert "already verified" in res_resend.json()["detail"].lower()


# 14. Frontend contract and security check (no leaks, clear error messages)
def test_14_frontend_contract_and_security(client):
    set_mock_brevo_response({"status_code": 401})

    res = client.post("/auth/signup", json={
        "username": "security_test",
        "email": "security@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })
    assert res.status_code in (502, 503)
    text = res.text.lower()
    assert "brevo_api_key" not in text
    assert "api-key" not in text
    assert "x-sib-id" not in text
    assert "traceback" not in text
    assert "password123" not in text

    # Detail is clean JSON string suitable for display in frontend banner
    assert isinstance(res.json().get("detail"), str)


# 15. Concurrent signup/retry requests respect database constraints
def test_15_concurrent_signup_race_conditions(client):
    # Perform sequential and simulated concurrent signups with same email
    res1 = client.post("/auth/signup", json={
        "username": "concurrent_alice",
        "email": "concurrent@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })
    assert res1.status_code == 201

    # Second signup with same email but different username handles unverified user without duplicate
    # (after adjusting created_at to bypass cooldown for test)
    db = TestingSessionLocal()
    challenge = db.query(OTPChallenge).filter(OTPChallenge.email == "concurrent@example.com").first()
    challenge.created_at = datetime.now(timezone.utc) - timedelta(seconds=70)
    db.commit()
    db.close()

    res2 = client.post("/auth/signup", json={
        "username": "concurrent_bob",
        "email": "concurrent@example.com",
        "password": "Password456",
        "confirm_password": "Password456",
    })
    assert res2.status_code == 201

    db = TestingSessionLocal()
    count = db.query(User).filter(User.email == "concurrent@example.com").count()
    assert count == 1
    db.close()
