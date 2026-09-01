import json
import sqlite3
from pathlib import Path

from .schema import UserProfile


DB_PATH = Path("data") / "memory.db"

# Pre-seeded demo profiles -- inserted once, only if the table is empty,
# so re-running the app during dev never overwrites manual test edits.
DEFAULT_PROFILES = [
    UserProfile(
        user_id="budget_conscious",
        typical_budget_max=10000,
    ),
    UserProfile(
        user_id="camera_focused",
        recurring_quality_tags=["good camera"],
    ),
    UserProfile(
        user_id="samsung_loyalist",
        preferred_brands=["Samsung"],
    ),
]


class MemoryAgent:
    """
    Stores and retrieves per-user shopping preference profiles in SQLite.

    Design choice: one table, one JSON blob column per user, rather than
    a fully normalized schema. For a handful of demo profiles this is
    simpler and sufficient; if this ever needs real querying across many
    users (e.g. "find all users who prefer Samsung"), that's the point
    to move to normalized columns -- not before.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._seed_defaults_if_empty()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL
                )
                """
            )

    def _seed_defaults_if_empty(self):
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
        if count == 0:
            for profile in DEFAULT_PROFILES:
                self.save_profile(profile)

    def get_profile(self, user_id: str) -> UserProfile:
        """
        Returns the stored profile for user_id, or a fresh empty profile
        if the user is unknown. An unknown user should never crash the
        pipeline -- it just means no personalization signal is available
        yet, which downstream agents (Ranking) can handle as "no
        preferences known."
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT profile_json FROM profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        if row is None:
            return UserProfile(user_id=user_id)

        data = json.loads(row[0])
        return UserProfile(**data)

    def save_profile(self, profile: UserProfile) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO profiles (user_id, profile_json)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET profile_json = excluded.profile_json
                """,
                (profile.user_id, profile.model_dump_json()),
            )


def demo():
    agent = MemoryAgent()

    print("Known profile (samsung_loyalist):")
    print(agent.get_profile("samsung_loyalist").model_dump_json(indent=2))

    print("\nUnknown profile (new_user_42) -- should be empty, not crash:")
    print(agent.get_profile("new_user_42").model_dump_json(indent=2))


if __name__ == "__main__":
    demo()