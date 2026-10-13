import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.database.models import Base, User, OTPChallenge, UserPreference
from backend.database.session import get_db
from backend.auth.email_service import MOCK_SENT_EMAILS
from backend.auth.security import create_access_token, hash_password
from backend.main import app

test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    Base.metadata.create_all(bind=test_engine)
    MOCK_SENT_EMAILS.clear()
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def client():
    return TestClient(app)

def test_signup_success_and_brevo_email(client):
    payload = {
        "username": "alice_test",
        "email": "alice@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    }
    res = client.post("/auth/signup", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert "verification code" in data["message"].lower()

    assert len(MOCK_SENT_EMAILS) == 1
    assert MOCK_SENT_EMAILS[0]["to"] == "alice@example.com"
    assert "Verify your SmartPick account" in MOCK_SENT_EMAILS[0]["subject"]

def test_signup_validation_failures(client):
    res = client.post("/auth/signup", json={
        "username": "mismatch_user",
        "email": "mismatch@example.com",
        "password": "Password123",
        "confirm_password": "DifferentPassword123",
    })
    assert res.status_code == 400
    assert "do not match" in res.json()["detail"].lower()

    res = client.post("/auth/signup", json={
        "username": "weak_user",
        "email": "weak@example.com",
        "password": "PasswordOnly",
        "confirm_password": "PasswordOnly",
    })
    assert res.status_code == 400
    assert "digit" in res.json()["detail"].lower()

def test_verify_email_and_login_flow(client):
    client.post("/auth/signup", json={
        "username": "bob_test",
        "email": "bob@example.com",
        "password": "SecurePassword1",
        "confirm_password": "SecurePassword1",
    })

    db = TestingSessionLocal()
    challenge = db.query(OTPChallenge).filter(OTPChallenge.email == "bob@example.com").first()
    assert challenge is not None
    db.close()

    mock_email = MOCK_SENT_EMAILS[-1]["html"]
    import re
    otp_match = re.search(r'<div class="otp-code">(\d{6})</div>', mock_email)
    assert otp_match is not None
    plain_otp = otp_match.group(1)

    res_wrong = client.post("/auth/verify-email", json={
        "email": "bob@example.com",
        "otp": "000000",
    })
    assert res_wrong.status_code == 400
    assert "invalid" in res_wrong.json()["detail"].lower()

    res_verify = client.post("/auth/verify-email", json={
        "email": "bob@example.com",
        "otp": plain_otp,
    })
    assert res_verify.status_code == 200
    token_data = res_verify.json()
    assert "access_token" in token_data
    assert token_data["user"]["is_verified"] is True
    jwt_token = token_data["access_token"]

    res_me = client.get("/auth/me", headers={"Authorization": f"Bearer {jwt_token}"})
    assert res_me.status_code == 200
    assert res_me.json()["username"] == "bob_test"

    res_login = client.post("/auth/login", json={
        "username_or_email": "bob_test",
        "password": "SecurePassword1",
    })
    assert res_login.status_code == 200
    assert "access_token" in res_login.json()

def test_login_unverified_rejected(client):
    db = TestingSessionLocal()
    user = User(
        username="unverified_user",
        email="unverified@example.com",
        password_hash=hash_password("Password123"),
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.close()

    res = client.post("/auth/login", json={
        "username_or_email": "unverified_user",
        "password": "Password123",
    })
    assert res.status_code == 403
    assert "verify your email" in res.json()["detail"].lower()

def test_forgot_and_reset_password_flow(client):
    db = TestingSessionLocal()
    user = User(
        username="carol_test",
        email="carol@example.com",
        password_hash=hash_password("OldPassword1"),
        is_verified=True,
    )
    db.add(user)
    db.commit()
    user_id = user.id
    token_v1 = user.token_version
    db.close()

    old_jwt = create_access_token(user_id, "carol_test", "carol@example.com", token_version=token_v1)

    res_forgot = client.post("/auth/forgot-password", json={"email_or_username": "carol@example.com"})
    assert res_forgot.status_code == 200

    mock_email = MOCK_SENT_EMAILS[-1]["html"]
    import re
    otp_match = re.search(r'<div class="otp-code">(\d{6})</div>', mock_email)
    reset_otp = otp_match.group(1)

    res_reset = client.post("/auth/reset-password", json={
        "email": "carol@example.com",
        "otp": reset_otp,
        "new_password": "NewPassword2",
        "confirm_new_password": "NewPassword2",
    })
    assert res_reset.status_code == 200
    assert "successfully" in res_reset.json()["message"].lower()

    res_old_login = client.post("/auth/login", json={
        "username_or_email": "carol_test",
        "password": "OldPassword1",
    })
    assert res_old_login.status_code == 401

    res_new_login = client.post("/auth/login", json={
        "username_or_email": "carol_test",
        "password": "NewPassword2",
    })
    assert res_new_login.status_code == 200

    res_old_token = client.get("/auth/me", headers={"Authorization": f"Bearer {old_jwt}"})
    assert res_old_token.status_code == 401
    assert "revoked" in res_old_token.json()["detail"].lower()
