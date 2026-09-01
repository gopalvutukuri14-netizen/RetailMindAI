from typing import Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """
    Stored, evolving profile of a user's shopping preferences.

    No login/auth -- user_id is just an identifier for a demo profile
    (e.g. picked from a dropdown, or passed directly in the request body).
    This matches the project's documented scope: pre-seeded simulated
    profiles for demonstrating cross-session personalization, not a
    real authentication system.
    """

    user_id: str
    preferred_brands: list[str] = Field(default_factory=list)
    excluded_brands: list[str] = Field(default_factory=list)
    typical_budget_min: Optional[float] = None
    typical_budget_max: Optional[float] = None
    past_purchases: list[str] = Field(default_factory=list)
    recurring_quality_tags: list[str] = Field(default_factory=list)