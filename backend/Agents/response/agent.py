import os
import logging

from dotenv import load_dotenv
from google import genai
from google.genai import types

from pydantic import BaseModel, Field
from .schema import ResponseResult, ResponseProduct
from backend.Agents.gemini_retry import call_with_retry
from backend.pipeline.product_images import get_product_images
from backend.orchestrator.comparison_helper import build_category_comparison_data


class ResponseSynthesis(BaseModel):
    summary: str = Field(
        description="Short natural-language summary of the recommendations"
    )
    additional_information: str = Field(
        default="",
        description="Useful context or highlights across the options"
    )


# Load environment variables from .env
load_dotenv()

logger = logging.getLogger(__name__)

# Gemini model used for response generation
MODEL_NAME = "gemini-3.5-flash-lite"


class ResponseAgent:
    """
    Response Agent converts the outputs of the previous agents
    into a final structured response for the frontend.

    Ranking decides:
        Which products should be recommended?

    XAI explains:
        Why were they recommended?

    Follow-up suggests:
        What can the user do next?

    Response Agent:
        Organizes all of this into a user-friendly response.
    """

    def __init__(self):
        # Get Gemini API key from .env
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in .env"
            )

        # Create Gemini client
        self.client = genai.Client(
            api_key=api_key
        )

    def generate(
        self,
        query,
        ranking_result,
        xai_result,
        followup_result,
    ) -> ResponseResult:
        """
        Generate the final response while preserving product identity,
        ranking order, and follow-up suggestions from upstream agents.
        """

        if not ranking_result.products:
            return ResponseResult(
                summary="No matching products were found for your request.",
                recommendations=[],
                additional_information=(
                    "Try changing your product type, budget, or preferences."
                ),
                follow_up_suggestions=[
                    suggestion.suggestion_text
                    for suggestion in followup_result.suggestions
                ],
            )

        prompt = self._build_prompt(
            query,
            ranking_result,
            xai_result,
            followup_result,
        )

        def _call():
            return self.client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ResponseSynthesis,
                    temperature=0.3,
                ),
            )

        # If Gemini is unavailable, fall back to a deterministic summary
        # built from actual ranked + XAI data already in the pipeline.
        try:
            response = call_with_retry(_call, context="ResponseAgent")
            if not response.text:
                raise RuntimeError("ResponseAgent: empty Gemini response")
            generated = ResponseSynthesis.model_validate_json(response.text)
            summary = generated.summary
            additional_information = generated.additional_information
        except Exception as exc:
            logger.warning(
                "ResponseAgent: falling back to deterministic summary after error: %s",
                exc,
            )
            product_type = getattr(query, "product_type", None) or "products"
            summary = (
                f"Here are the top {len(ranking_result.products)} "
                f"{product_type} recommendations matching your request."
            )
            additional_information = ""

        generated_summary = (summary or "").replace("RetailMind AI", "SmartPick").replace("RetailMind", "SmartPick")
        generated_additional = (additional_information or "").replace("RetailMind AI", "SmartPick").replace("RetailMind", "SmartPick")

        # Match explanations by ASIN, not by list position.
        explanations_by_asin = {
            explanation.asin: explanation
            for explanation in xai_result.explanations
        }

        # Rebuild recommendations from the authoritative ranking output.
        # This preserves the ranking order and prevents invented products.
        recommendations = []

        asins = [ranked_product.asin for ranked_product in ranking_result.products]
        image_urls = get_product_images(asins)

        for ranked_product in ranking_result.products:
            explanation = explanations_by_asin.get(ranked_product.asin)

            recommendations.append(
                ResponseProduct(
                    asin=ranked_product.asin,
                    title=ranked_product.title,
                    brand=ranked_product.brand,
                    price_inr=ranked_product.price_inr,
                    image_url=image_urls.get(ranked_product.asin),
                    explanation=(
                        explanation.explanation
                        if explanation
                        else (
                            ranked_product.match_reasons[0]
                            if ranked_product.match_reasons
                            else "Recommended based on the available ranking signals."
                        )
                    ),
                    key_factors=(
                        explanation.key_factors
                        if explanation
                        else []
                    ),
                )
            )

        comparison_data = None
        intent_val = getattr(query, "intent", None)
        if intent_val and str(intent_val).lower() == "comparison" and len(recommendations) >= 2:
            prod_a_dict = recommendations[0].model_dump()
            prod_b_dict = recommendations[1].model_dump()
            category_val = getattr(query.category, "value", str(query.category)) if getattr(query, "category", None) else None
            comparison_data = build_category_comparison_data(prod_a_dict, prod_b_dict, category=category_val)

        return ResponseResult(
            summary=generated_summary,
            recommendations=recommendations,
            additional_information=generated_additional,
            comparison=comparison_data,
            follow_up_suggestions=[
                suggestion.suggestion_text
                for suggestion in followup_result.suggestions
            ],
        )

    def _build_prompt(
        self,
        query,
        ranking_result,
        xai_result,
        followup_result,
    ) -> str:
        """
        Build the prompt sent to Gemini.

        The prompt contains:
        - Original user query
        - Ranked products
        - XAI explanations
        - Follow-up suggestions
        """

        # Build product information
        product_blocks = []

        for i, product in enumerate(
            ranking_result.products,
            start=1
        ):
            block = f"""
Rank {i}
ASIN: {product.asin}
Title: {product.title}
Brand: {product.brand}
Price: {"₹" + str(product.price_inr) if product.price_inr is not None else "unknown"}

Ranking score: {product.scores.final_score:.3f}
Reasons: {product.match_reasons}
""".strip()

            product_blocks.append(block)

        products_text = "\n\n".join(product_blocks)

        # Build XAI information
        xai_blocks = []

        for explanation in xai_result.explanations:
            xai_blocks.append(
                f"""
ASIN: {explanation.asin}
Explanation: {explanation.explanation}
Key factors: {explanation.key_factors}
""".strip()
            )

        xai_text = "\n\n".join(xai_blocks)

        # Build follow-up information
        followup_text = "\n".join(
            f"- {s.suggestion_text}"
            for s in followup_result.suggestions
        )

        return f"""
You are the Response Generation Agent for SmartPick.

Your job is to convert the outputs of the previous agents
into a clear, concise, structured response for the shopper.

User's original request:
"{query.raw_query}"

RANKED PRODUCTS:
{products_text}

XAI EXPLANATIONS:
{xai_text}

FOLLOW-UP SUGGESTIONS:
{followup_text}

Rules:

1. Create a short summary explaining what the user asked for.

2. Do not invent specifications, features, prices,
   review information, or customer opinions.

3. Keep product explanations short and easy to understand.

4. additional_information should contain useful context
   from the supplied ranking and XAI information.
   If there is nothing useful to add, keep it short.

5. Keep the response concise and suitable for a shopping chatbot.

The final output must contain:
- summary
- additional_information
""".strip()