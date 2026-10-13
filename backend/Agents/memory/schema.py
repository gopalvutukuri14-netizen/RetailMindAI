from typing import Optional, List
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """
    Stored, dynamically evolving profile of a user's shopping preferences.
    Populated securely from authoritative Cloud PostgreSQL for authenticated users.
    Anonymous sessions receive a neutral, unpersisted default profile.
    """
    user_id: str
    preferred_brands: List[str] = Field(default_factory=list)
    excluded_brands: List[str] = Field(default_factory=list)
    typical_budget_min: Optional[float] = None
    typical_budget_max: Optional[float] = None
    past_purchases: List[str] = Field(default_factory=list)
    recurring_quality_tags: List[str] = Field(default_factory=list)
    preferred_categories: List[str] = Field(default_factory=list)
    recent_context_summary: Optional[str] = None
