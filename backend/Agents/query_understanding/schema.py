from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class Intent(str, Enum):
    PRODUCT_RECOMMENDATION = "product_recommendation"
    COMPARISON = "comparison"
    FOLLOW_UP = "follow_up"
    GENERAL_QUESTION = "general_question"


class BrandPreferences(BaseModel):
    preferred: Optional[list[str]] = None
    excluded: Optional[list[str]] = None


class ProductSpecs(BaseModel):
    ram_gb: Optional[float] = None
    storage_gb: Optional[float] = None
    camera_mp_min: Optional[float] = None
    battery_mah_min: Optional[float] = None


class QueryUnderstanding(BaseModel):
    intent: Intent
    category: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    brand: BrandPreferences
    specs: ProductSpecs
    quality_tags: list[str] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)
    raw_query: str

    @model_validator(mode="after")
    def check_budget_range(self):
        if (
            self.budget_min is not None
            and self.budget_max is not None
            and self.budget_min > self.budget_max
        ):
            raise ValueError("budget_min cannot be greater than budget_max")
        return self