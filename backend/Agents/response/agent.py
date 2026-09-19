import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .schema import ResponseResult


# Load environment variables from .env
load_dotenv()

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
        Generate the final structured response.

        Inputs:
            query            -> Query Understanding result
            ranking_result   -> Ranking Agent result
            xai_result       -> XAI Agent result
            followup_result  -> Follow-up Agent result

        Output:
            ResponseResult for the frontend.
        """

        # Build the prompt using outputs from previous agents
        prompt = self._build_prompt(
            query,
            ranking_result,
            xai_result,
            followup_result,
        )

        # Ask Gemini for structured JSON output
        response = self.client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ResponseResult,
                temperature=0.3,
            ),
        )

        # Convert Gemini JSON into our Pydantic schema
        result = ResponseResult.model_validate_json(
            response.text
        )

        # Product identity comes from Ranking Agent,
        # not from the LLM.
        for response_product, ranked_product in zip(
            result.recommendations,
            ranking_result.products,
        ):
            response_product.asin = ranked_product.asin
            response_product.title = ranked_product.title
            response_product.brand = ranked_product.brand
            response_product.price_inr = ranked_product.price_inr

        # Follow-up suggestions come from Follow-up Agent.
        # Keep them unchanged instead of letting the LLM invent new ones.
        result.follow_up_suggestions = [
            suggestion.suggestion_text
            for suggestion in followup_result.suggestions
        ]

        return result

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
You are the Response Generation Agent for RetailMind AI.

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

2. Include the ranked products in the same order.

3. Use ONLY the products provided by the Ranking Agent.

4. Use the XAI explanations as the basis for explaining
   why each product was recommended.

5. Do not invent specifications, features, prices,
   review information, or customer opinions.

6. Do not change product identities.

7. Keep product explanations short and easy to understand.

8. additional_information should contain useful context
   from the supplied ranking and XAI information.
   If there is nothing useful to add, keep it short.

9. Do not create new follow-up questions.
   Use the suggestions supplied by the Follow-up Agent.

10. Keep the response concise and suitable for a shopping chatbot.

The final output must contain:
- summary
- recommendations
- additional_information
- follow_up_suggestions
""".strip()