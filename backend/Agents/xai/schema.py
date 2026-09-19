from pydantic import BaseModel, Field


class ProductExplanation(BaseModel):
    """
    One product's explanation. Grounded strictly in the scores and
    match_reasons Ranking Agent already computed -- the LLM's job here
    is to turn structured signals into natural language, not to invent
    new reasons that weren't actually part of the scoring.
    """

    asin: str
    explanation: str = Field(
        description="1-2 natural sentences explaining why this product was recommended, "
                     "grounded only in the provided scores and reasons."
    )
    key_factors: list[str] = Field(
        default_factory=list,
        description="Short bullet-style factors (3-5 words each), e.g. "
                     "'Strong camera reviews' or 'Within your usual budget'.",
    )


class XAIResult(BaseModel):
    query_summary: str = Field(
        description="One short sentence restating what the user asked for, "
                     "for context alongside the explanations."
    )
    explanations: list[ProductExplanation] = Field(default_factory=list)