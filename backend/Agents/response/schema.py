from pydantic import BaseModel, Field


class ResponseProduct(BaseModel):
    asin: str = Field(
        description="Product ASIN"
    )
    title: str = Field(
        description="Product title"
    )
    brand: str | None = Field(
        default=None,
        description="Product brand"
    )
    price_inr: float | None = Field(
        default=None,
        description="Product price in INR"
    )
    image_url: str | None = Field(
        default=None,
        description="Product image URL from dataset metadata if available"
    )
    explanation: str = Field(
        description="Short explanation of why this product was recommended"
    )
    key_factors: list[str] = Field(
        default_factory=list,
        description="Short factors supporting the recommendation"
    )


class ComparisonRow(BaseModel):
    aspect: str = Field(
        description="Comparison aspect, e.g. 'Price', 'Brand', 'Key Specifications', 'Customer Sentiment', 'Main Strengths', 'Known Limitations', 'Best Suited For'"
    )
    product_a: str = Field(
        description="Value or evidence for Product A (or 'Not available in catalog' if missing)"
    )
    product_b: str = Field(
        description="Value or evidence for Product B (or 'Not available in catalog' if missing)"
    )


class ComparisonData(BaseModel):
    heading: str = Field(
        description="Concise comparison heading, e.g. 'Comparing Product A vs Product B'"
    )
    product_a_asin: str | None = Field(
        default=None,
        description="ASIN for Product A"
    )
    product_b_asin: str | None = Field(
        default=None,
        description="ASIN for Product B"
    )
    rows: list[ComparisonRow] = Field(
        default_factory=list,
        description="Category-adapted comparison rows"
    )
    conclusion: str = Field(
        description="Short concluding paragraph explaining key differences and which suits which user"
    )


class ResponseResult(BaseModel):
    summary: str = Field(
        description="Short natural-language summary of the recommendation"
    )

    recommendations: list[ResponseProduct] = Field(
        default_factory=list,
        description="Recommended products to display"
    )

    additional_information: str = Field(
        default="",
        description="Useful additional information or comparison context"
    )

    comparison: ComparisonData | None = Field(
        default=None,
        description="Structured side-by-side comparison data and conclusion when comparing products"
    )

    follow_up_suggestions: list[str] = Field(
        default_factory=list,
        description="Natural follow-up actions the user can take"
    )