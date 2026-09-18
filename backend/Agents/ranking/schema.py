from typing import Optional
from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    """
    Transparent per-signal scoring, so Ranking's output can be explained
    later (this is literally what your XAI Agent will read from).
    Each sub-score is 0-1. None means that signal was not available for
    this product/query -- it's excluded from the weighted average
    entirely, not counted as a zero.
    """

    similarity_score: Optional[float] = None
    spec_match_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    memory_alignment_score: Optional[float] = None
    aspect_alignment_score: Optional[float] = None

    final_score: float


class RankedProduct(BaseModel):
    asin: str
    title: str
    brand: Optional[str] = None
    price_inr: Optional[float] = None

    scores: ScoreBreakdown

    # Plain-language notes on why this scored the way it did -- rough
    # material for XAI Agent, not a substitute for it.
    match_reasons: list[str] = Field(default_factory=list)


class RankingResult(BaseModel):
    user_id: Optional[str] = None
    memory_applied: bool
    total_ranked: int
    products: list[RankedProduct] = Field(default_factory=list)