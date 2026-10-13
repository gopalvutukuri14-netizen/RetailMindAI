import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from backend.database.models import Base, User, OTPChallenge, UserPreference, ConversationMemory


@pytest.fixture
def db_session():
    # In-memory SQLite for fast, isolated unit tests
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_user_creation_and_uniqueness(db_session):
    user1 = User(
        username="john_doe",
        email="john@example.com",
        password_hash="argon2id$mockhash",
        is_verified=False,
    )
    db_session.add(user1)
    db_session.commit()

    assert user1.id is not None
    assert user1.is_verified is False
    assert user1.token_version == 1

    # Duplicate username should raise IntegrityError
    user2 = User(
        username="john_doe",
        email="another@example.com",
        password_hash="argon2id$mockhash2",
    )
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Duplicate email should raise IntegrityError
    user3 = User(
        username="jane_doe",
        email="john@example.com",
        password_hash="argon2id$mockhash3",
    )
    db_session.add(user3)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_otp_challenge_expiry_and_attempts(db_session):
    now = datetime.now(timezone.utc)
    expires_future = now + timedelta(minutes=5)
    expires_past = now - timedelta(minutes=1)

    challenge_active = OTPChallenge(
        email="user@example.com",
        purpose="signup_verify",
        otp_hash="hash123",
        expires_at=expires_future,
    )
    challenge_expired = OTPChallenge(
        email="user@example.com",
        purpose="password_reset",
        otp_hash="hash456",
        expires_at=expires_past,
    )
    db_session.add_all([challenge_active, challenge_expired])
    db_session.commit()

    assert challenge_active.is_expired() is False
    assert challenge_expired.is_expired() is True

    # Test attempt counting
    challenge_active.attempts += 1
    db_session.commit()
    assert challenge_active.attempts == 1


def test_user_preference_and_memory_relationships(db_session):
    user = User(
        username="gadget_fan",
        email="gadget@example.com",
        password_hash="argon2id$hash",
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    pref = UserPreference(
        user_id=user.id,
        preferred_categories=["Electronics", "Cell Phones & Accessories"],
        preferred_brands=["Sony", "Samsung"],
        excluded_brands=["Apple"],
        typical_budget_min=5000.0,
        typical_budget_max=25000.0,
        recurring_quality_tags=["high battery", "fast charging"],
    )
    memory = ConversationMemory(
        user_id=user.id,
        conversation_id="conv-12345",
        query_text="Best noise cancelling headphones",
        context_summary="User prefers Sony with ANC",
    )
    db_session.add_all([pref, memory])
    db_session.commit()

    # Query back
    saved_user = db_session.query(User).filter(User.id == user.id).first()
    assert saved_user.preferences is not None
    assert saved_user.preferences.preferred_brands == ["Sony", "Samsung"]
    assert len(saved_user.conversation_memories) == 1
    assert saved_user.conversation_memories[0].query_text == "Best noise cancelling headphones"

    # Test cascade delete
    db_session.delete(saved_user)
    db_session.commit()

    assert db_session.query(UserPreference).filter(UserPreference.user_id == user.id).first() is None
    assert db_session.query(ConversationMemory).filter(ConversationMemory.user_id == user.id).first() is None
