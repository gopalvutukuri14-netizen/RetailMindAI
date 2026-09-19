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
    explanation: str = Field(
        description="Short explanation of why this product was recommended"
    )
    key_factors: list[str] = Field(
        default_factory=list,
        description="Short factors supporting the recommendation"
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

    follow_up_suggestions: list[str] = Field(
        default_factory=list,
        description="Natural follow-up actions the user can take"
    )