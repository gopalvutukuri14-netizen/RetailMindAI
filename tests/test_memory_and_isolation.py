import os
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.models import Base, User, UserPreference, ConversationMemory
from backend.database.session import DATABASE_URL
from backend.Agents.memory import MemoryAgent
from backend.Agents.memory.schema import UserProfile
from backend.Agents.ranking.agent import RankingAgent


@pytest.fixture
def isolated_db_session_factory():
    """Isolated in-memory SQLite database session factory for reliable unit testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield TestingSession
    Base.metadata.drop_all(bind=engine)


def test_neon_cloud_postgres_connectivity_and_schema():
    """
    Verify live connectivity to authoritative Neon Cloud PostgreSQL,
    and verify Alembic revision 7da16e00e38b and public schema tables.
    """
    assert DATABASE_URL.startswith("postgresql"), "DATABASE_URL must be a PostgreSQL connection string"
    
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        version_str = conn.execute(text("SELECT version();")).scalar()
        assert "PostgreSQL" in version_str
        
        # Verify tables created by Alembic
        tables = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
        )).fetchall()
        table_names = [t[0] for t in tables]
        for expected in ["users", "otp_challenges", "user_preferences", "conversation_memory", "alembic_version"]:
            assert expected in table_names, f"Missing expected table: {expected}"

        # Verify applied Alembic head revision
        rev = conn.execute(text("SELECT version_num FROM alembic_version;")).scalar()
        assert rev == "7da16e00e38b", f"Expected Alembic revision 7da16e00e38b, got {rev}"


def test_new_user_has_neutral_empty_preferences(isolated_db_session_factory):
    """Every new user must start with clean, independent, neutral preferences without persona seeding."""
    session = isolated_db_session_factory()
    user = User(
        username="fresh_user",
        email="fresh@example.com",
        password_hash="argon2id$mock",
        is_verified=True,
    )
    session.add(user)
    session.commit()

    pref = UserPreference(
        user_id=user.id,
        preferred_categories=[],
        preferred_brands=[],
        excluded_brands=[],
        typical_budget_min=None,
        typical_budget_max=None,
        recurring_quality_tags=[],
    )
    session.add(pref)
    session.commit()

    agent = MemoryAgent(db_session_factory=isolated_db_session_factory)
    profile = agent.get_profile(user.id)

    assert profile.user_id == user.id
    assert profile.preferred_brands == []
    assert profile.excluded_brands == []
    assert profile.typical_budget_min is None
    assert profile.typical_budget_max is None
    assert profile.recurring_quality_tags == []

    # Ranking agent must consider this profile as having no biasing signal
    ranking_agent = RankingAgent()
    assert ranking_agent._profile_has_signal(profile) is False
    session.close()


def test_dynamic_preference_learning_and_updates(isolated_db_session_factory):
    """Preferences must be learned dynamically from conversation and updated when user changes them."""
    session = isolated_db_session_factory()
    user = User(
        username="shopper1",
        email="shopper1@example.com",
        password_hash="argon2id$mock",
        is_verified=True,
    )
    session.add(user)
    session.commit()
    user_id = user.id
    session.close()

    agent = MemoryAgent(db_session_factory=isolated_db_session_factory)

    # 1. First interaction: User seeks phone under 25000 with good camera
    class MockQueryUnderstanding1:
        budget_min = None
        budget_max = 25000.0
        quality_focus = "good camera"
        category = "cell_phones_and_accessories"

    agent.update_preferences_from_interaction(
        user_id=user_id,
        query_understanding=MockQueryUnderstanding1(),
        raw_query="I need a phone under ?25,000 with a good camera.",
    )

    profile1 = agent.get_profile(user_id)
    assert profile1.typical_budget_max == 25000.0
    assert "good camera" in profile1.recurring_quality_tags
    assert "cell_phones_and_accessories" in profile1.preferred_categories

    # Save turn in conversation memory
    agent.save_conversation_turn(
        user_id=user_id,
        conversation_id="conv_1",
        query_text="I need a phone under ?25,000 with a good camera.",
        context_summary="Recommended Pixel 7a and OnePlus Nord under ?25,000",
    )

    profile_after_turn = agent.get_profile(user_id)
    assert profile_after_turn.recent_context_summary == "Recommended Pixel 7a and OnePlus Nord under ?25,000"

    # 2. Later interaction: User updates their budget to 35000
    class MockQueryUnderstanding2:
        budget_min = None
        budget_max = 35000.0
        quality_focus = None
        category = None

    agent.update_preferences_from_interaction(
        user_id=user_id,
        query_understanding=MockQueryUnderstanding2(),
        raw_query="My budget has increased to ?35,000.",
    )

    profile2 = agent.get_profile(user_id)
    # Stored budget should be updated to 35000, while existing quality tag is preserved
    assert profile2.typical_budget_max == 35000.0
    assert "good camera" in profile2.recurring_quality_tags


def test_multi_user_isolation(isolated_db_session_factory):
    """Strict isolation: User A and User B cannot read or overwrite each other's preferences or memory."""
    session = isolated_db_session_factory()
    user_a = User(username="user_a", email="a@example.com", password_hash="argon2id$mock", is_verified=True)
    user_b = User(username="user_b", email="b@example.com", password_hash="argon2id$mock", is_verified=True)
    session.add_all([user_a, user_b])
    session.commit()
    id_a, id_b = user_a.id, user_b.id
    session.close()

    agent = MemoryAgent(db_session_factory=isolated_db_session_factory)

    # User A interacts and sets budget 50000 and quality 'high performance'
    class MockQueryA:
        budget_min = 20000.0
        budget_max = 50000.0
        quality_focus = "high performance"
        category = "electronics"

    agent.update_preferences_from_interaction(id_a, MockQueryA(), "Looking for premium laptop")
    agent.save_conversation_turn(id_a, "conv_a", "Looking for premium laptop", "Recommended ThinkPad")

    # Check User A's profile
    prof_a = agent.get_profile(id_a)
    assert prof_a.typical_budget_max == 50000.0
    assert "high performance" in prof_a.recurring_quality_tags
    assert prof_a.recent_context_summary == "Recommended ThinkPad"

    # Check User B's profile: MUST BE CLEAN AND NEUTRAL
    prof_b = agent.get_profile(id_b)
    assert prof_b.typical_budget_max is None
    assert prof_b.recurring_quality_tags == []
    assert prof_b.recent_context_summary is None

    # User B updates budget to 15000
    class MockQueryB:
        budget_min = None
        budget_max = 15000.0
        quality_focus = "budget friendly"
        category = "home_and_kitchen"

    agent.update_preferences_from_interaction(id_b, MockQueryB(), "Blender under 15k")
    agent.save_conversation_turn(id_b, "conv_b", "Blender under 15k", "Recommended Philips blender")

    # Verify User A's profile was UNTOUCHED by User B's interaction
    prof_a_recheck = agent.get_profile(id_a)
    assert prof_a_recheck.typical_budget_max == 50000.0
    assert "high performance" in prof_a_recheck.recurring_quality_tags
    assert prof_a_recheck.recent_context_summary == "Recommended ThinkPad"


def test_anonymous_session_isolation(isolated_db_session_factory):
    """Anonymous sessions must never persist to PostgreSQL or contaminate other profiles."""
    agent = MemoryAgent(db_session_factory=isolated_db_session_factory)

    anon_prof = agent.get_profile("anonymous")
    assert anon_prof.user_id == "anonymous"
    assert anon_prof.typical_budget_max is None
    assert anon_prof.preferred_brands == []

    # Attempting to update anonymous profile does nothing
    class MockAnonQuery:
        budget_min = None
        budget_max = 10000.0
        quality_focus = "waterproof"
        category = "sports_and_outdoors"

    agent.update_preferences_from_interaction("anonymous", MockAnonQuery(), "running shoes")
    agent.save_conversation_turn("anonymous", "conv_anon", "running shoes", "shoes summary")

    # Verify no records were inserted into the database
    session = isolated_db_session_factory()
    assert session.query(UserPreference).count() == 0
    assert session.query(ConversationMemory).count() == 0
    session.close()


def test_conversation_memory_redaction(isolated_db_session_factory):
    """Ensure sensitive tokens, passwords, and OTPs are redacted from conversation memory."""
    session = isolated_db_session_factory()
    user = User(username="test_sec", email="sec@example.com", password_hash="argon2id$mock", is_verified=True)
    session.add(user)
    session.commit()
    user_id = user.id
    session.close()

    agent = MemoryAgent(db_session_factory=isolated_db_session_factory)
    raw_text = "My password: SecretPassword123 and token: eyJhbGciOiJIUzI1Ni... and otp: 123456"
    agent.save_conversation_turn(user_id, "conv_sec", raw_text, "User asked query with credentials")

    session = isolated_db_session_factory()
    saved = session.query(ConversationMemory).filter(ConversationMemory.user_id == user_id).first()
    assert saved is not None
    assert "SecretPassword123" not in saved.query_text
    assert "123456" not in saved.query_text
    assert "[REDACTED]" in saved.query_text
    session.close()
