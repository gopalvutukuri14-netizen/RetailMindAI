from typing import Optional
from pydantic import BaseModel, Field


class RetrievedProduct(BaseModel):
    """One candidate product returned by the Retrieval Agent."""

    asin: str
    title: str
    brand: Optional[str] = None

    price_inr: Optional[float] = None
    ram_gb: Optional[float] = None
    storage_gb: Optional[float] = None
    camera_mp: Optional[float] = None
    battery_mah: Optional[float] = None

    average_rating: Optional[float] = None
    total_reviews: Optional[int] = None
    average_sentiment_score: Optional[float] = None
    positive_ratio: Optional[float] = None
    negative_ratio: Optional[float] = None

    # ChromaDB semantic distance (lower = more similar). Left unnormalized
    # on purpose -- Ranking Agent decides how to combine it with other signals.
    distance: float

    # Per-spec comparison against the user's stated minimums.
    #   True  -> product meets the stated minimum
    #   False -> product falls short
    #   None  -> spec unknown for this product, OR user didn't ask for it.
    # Unknown is never treated as "fails" -- too much of this catalog is
    # missing spec data for that to be a safe default.
    meets_ram: Optional[bool] = None
    meets_storage: Optional[bool] = None
    meets_camera: Optional[bool] = None
    meets_battery: Optional[bool] = None


class RetrievalResult(BaseModel):
    """Full output of one Retrieval Agent call."""

    query_text_used: str
    hard_filters_applied: dict = Field(default_factory=dict)
    hard_constraints_not_enforced: list[str] = Field(default_factory=list)
    total_candidates_returned: int
    products: list[RetrievedProduct] = Field(default_factory=list)