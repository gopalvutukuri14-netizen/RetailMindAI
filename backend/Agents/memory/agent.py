import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import re

from backend.database.session import SessionLocal
from backend.database.models import User, UserPreference, ConversationMemory
from .schema import UserProfile

logger = logging.getLogger(__name__)

# Sensitive keywords that must never be stored in conversation memory
SENSITIVE_PATTERNS = [
    re.compile(r"password\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"token\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"otp\s*[:=]\s*\d+", re.IGNORECASE),
    re.compile(r"bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
]


def _sanitize_text(text: str) -> str:
    """Strip any potential authentication credentials, tokens or OTPs."""
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


class MemoryAgent:
    """
    Cloud PostgreSQL-backed Memory Agent.

    Strict rules:
    1. Authenticated users: Load and persist dynamic preferences from/to Cloud PostgreSQL.
    2. Anonymous users: Return a neutral, empty profile. Never persist or share memory.
    3. No hardcoded personas: Real users always start with fresh, neutral memory.
    4. Multi-user isolation: Every query is strictly scoped to the authenticated user's UUID.
    """

    def __init__(self, db_session_factory=SessionLocal):
        self.session_factory = db_session_factory

    def get_profile(self, user_id: str) -> UserProfile:
        """
        Retrieve the stored profile for user_id from Cloud PostgreSQL.
        Returns a fresh neutral profile for anonymous, invalid, or new users.
        """
        if not user_id or user_id in ("anonymous", "null", "undefined"):
            return UserProfile(user_id="anonymous")

        session = self.session_factory()
        try:
            # Query user preference securely scoped to user_id
            pref = (
                session.query(UserPreference)
                .filter(UserPreference.user_id == user_id)
                .first()
            )

            # Query the most recent conversation memory for context continuity
            latest_memory = (
                session.query(ConversationMemory)
                .filter(ConversationMemory.user_id == user_id)
                .order_by(ConversationMemory.created_at.desc())
                .first()
            )

            recent_summary = latest_memory.context_summary if latest_memory else None

            if not pref:
                # Neutral empty profile for user with no saved preferences yet
                return UserProfile(
                    user_id=user_id,
                    recent_context_summary=recent_summary,
                )

            return UserProfile(
                user_id=user_id,
                preferred_brands=list(pref.preferred_brands or []),
                excluded_brands=list(pref.excluded_brands or []),
                typical_budget_min=pref.typical_budget_min,
                typical_budget_max=pref.typical_budget_max,
                recurring_quality_tags=list(pref.recurring_quality_tags or []),
                preferred_categories=list(pref.preferred_categories or []),
                recent_context_summary=recent_summary,
            )
        except Exception as exc:
            logger.error(f"Error fetching profile for user {user_id}: {exc}")
            # Safe fallback: return neutral profile rather than crashing the pipeline
            return UserProfile(user_id=user_id)
        finally:
            session.close()

    def update_preferences_from_interaction(
        self,
        user_id: str,
        query_understanding: Any,
        raw_query: str,
    ) -> None:
        """
        Dynamically learn preferences from natural interaction.
        Updates budget, quality priorities, and categories in PostgreSQL for authenticated user.
        """
        if not user_id or user_id in ("anonymous", "null", "undefined"):
            return

        session = self.session_factory()
        try:
            pref = (
                session.query(UserPreference)
                .filter(UserPreference.user_id == user_id)
                .first()
            )

            if not pref:
                pref = UserPreference(
                    user_id=user_id,
                    preferred_categories=[],
                    preferred_brands=[],
                    excluded_brands=[],
                    recurring_quality_tags=[],
                )
                session.add(pref)

            # 1. Learn or update budget dynamically
            # If the user stated a budget or modified it (e.g. "budget increased to 35000", "under 25000")
            if hasattr(query_understanding, "budget_max") and query_understanding.budget_max is not None:
                pref.typical_budget_max = float(query_understanding.budget_max)

            if hasattr(query_understanding, "budget_min") and query_understanding.budget_min is not None:
                pref.typical_budget_min = float(query_understanding.budget_min)

            # 2. Learn quality priorities (e.g. "good camera", "long battery")
            if hasattr(query_understanding, "quality_focus") and query_understanding.quality_focus:
                quality_tag = str(query_understanding.quality_focus).strip().lower()
                current_tags = list(pref.recurring_quality_tags or [])
                if quality_tag and quality_tag not in current_tags:
                    current_tags.append(quality_tag)
                    pref.recurring_quality_tags = current_tags

            # 3. Learn categories of recurring interest
            if hasattr(query_understanding, "category") and query_understanding.category:
                cat = str(query_understanding.category).strip()
                current_cats = list(pref.preferred_categories or [])
                if cat and cat not in current_cats:
                    current_cats.append(cat)
                    pref.preferred_categories = current_cats

            pref.updated_at = datetime.now(timezone.utc)
            session.commit()
            logger.info(f"Updated preferences dynamically in PostgreSQL for user {user_id}")
        except Exception as exc:
            session.rollback()
            logger.error(f"Failed to update preferences for user {user_id}: {exc}")
        finally:
            session.close()

    def save_conversation_turn(
        self,
        user_id: str,
        conversation_id: str,
        query_text: str,
        context_summary: str,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Persist a conversation turn to PostgreSQL for authenticated users.
        Ensures strict user scoping and data sanitization.
        """
        if not user_id or user_id in ("anonymous", "null", "undefined"):
            return

        session = self.session_factory()
        try:
            sanitized_query = _sanitize_text(query_text)
            sanitized_summary = _sanitize_text(context_summary)

            memory = ConversationMemory(
                user_id=user_id,
                conversation_id=conversation_id or f"conv_{user_id}",
                query_text=sanitized_query,
                context_summary=sanitized_summary,
                context_data=context_data or {},
            )
            session.add(memory)
            session.commit()
            logger.info(f"Persisted conversation memory for user {user_id}")
        except Exception as exc:
            session.rollback()
            logger.error(f"Failed to persist conversation memory for user {user_id}: {exc}")
        finally:
            session.close()
