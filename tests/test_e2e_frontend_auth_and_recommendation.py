import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["TESTING"] = "true"

from backend.database.models import Base, User, OTPChallenge, UserPreference, ConversationMemory
from backend.database.session import get_db
from backend.auth.email_service import MOCK_SENT_EMAILS
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
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    MOCK_SENT_EMAILS.clear()
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_full_auth_and_recommendation_flow(client):
    # 1. Signup
    signup_res = client.post("/auth/signup", json={
        "username": "e2e_shopper",
        "email": "e2e_shopper@example.com",
        "password": "Password123",
        "confirm_password": "Password123",
    })
    assert signup_res.status_code == 201

    # Extract OTP from mock email
    assert len(MOCK_SENT_EMAILS) >= 1
    import re
    otp_match = re.search(r'<div class="otp-code">(\d{6})</div>', MOCK_SENT_EMAILS[-1]["html"])
    assert otp_match is not None
    otp = otp_match.group(1)

    # 2. Verify Email
    verify_res = client.post("/auth/verify-email", json={
        "email": "e2e_shopper@example.com",
        "otp": otp,
    })
    assert verify_res.status_code == 200
    token_data = verify_res.json()
    token = token_data["access_token"]
    assert token_data["user"]["is_verified"] is True

    # 3. /auth/me with Bearer token
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "e2e_shopper"

    # 4. Authenticated recommendation request (fast-path general/budget query)
    headers = {"Authorization": f"Bearer {token}"}
    rec_res = client.post("/recommend", headers=headers, json={
        "query": "Hello! Can you help me find good products?",
        "user_id": "anonymous",  # client-supplied ID must be overridden by verified JWT
    })
    assert rec_res.status_code == 200
    data = rec_res.json()
    assert "summary" in data

    # 5. Anonymous recommendation request should not fail and should not require token
    anon_res = client.post("/recommend", json={
        "query": "Hello from guest user!",
        "user_id": "anonymous",
    })
    assert anon_res.status_code == 200
