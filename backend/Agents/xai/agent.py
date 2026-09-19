import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .schema import XAIResult


# Load environment variables from .env
load_dotenv()

# Gemini model used for generating explanations
MODEL_NAME = "gemini-3.5-flash-lite"


class XAIAgent:
    """
    XAI Agent converts Ranking Agent's structured results
    into simple explanations that the user can understand.

    Ranking decides:
        "Which product ranks higher?"

    XAI explains:
        "Why was this product ranked this way?"
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

    def explain(self, query, ranking_result) -> XAIResult:
        """
        Generate explanations for the ranked products.

        Input:
            query          -> QueryUnderstanding result
            ranking_result -> Ranking Agent result

        Output:
            XAIResult containing explanations for each product.
        """

        # Build the prompt using the query and ranking results
        prompt = self._build_prompt(
            query,
            ranking_result
        )

        # Ask Gemini to generate structured XAI output
        response = self.client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=XAIResult,
                temperature=0.3,
            ),
        )

        # Convert Gemini's JSON response into our Pydantic schema
        result = XAIResult.model_validate_json(
            response.text
        )

        # Make sure Gemini returned one explanation per product
        if len(result.explanations) != len(ranking_result.products):
            raise ValueError(
                "XAI explanation count does not match "
                "ranking result count."
            )

        # ASIN is a database identifier.
        # We should NOT trust the LLM to reproduce it correctly.
        # Take the original ASIN directly from Ranking Agent.
        for explanation, ranked_product in zip(
            result.explanations,
            ranking_result.products,
        ):
            explanation.asin = ranked_product.asin

        return result

    def _build_prompt(self, query, ranking_result) -> str:
        """
        Build the prompt that is sent to Gemini.

        The prompt contains:
        - User's original query
        - Quality preferences
        - Ranked products
        - Ranking scores
        - Pre-computed reasons
        """

        product_blocks = []

        # Create one information block for every ranked product
        for i, product in enumerate(
            ranking_result.products,
            start=1
        ):
            s = product.scores

            block = f"""
Rank {i}: {product.title}
ASIN: {product.asin}
Brand: {product.brand}
Price: {"₹" + str(product.price_inr) if product.price_inr is not None else "unknown"}

Final score: {s.final_score:.3f}
Similarity to query: {s.similarity_score}
Spec match: {s.spec_match_score}
Overall sentiment: {s.sentiment_score}
Aspect alignment: {s.aspect_alignment_score}
Memory alignment: {s.memory_alignment_score}

Pre-computed reasons:
{product.match_reasons}
""".strip()

            product_blocks.append(block)

        # Combine all product blocks into one prompt section
        products_text = "\n\n".join(
            product_blocks
        )

        # Prompt tells Gemini exactly what it can and cannot do
        return f"""
You are the Explainability (XAI) Agent for RetailMind AI.

Your job is to convert the structured ranking data into
clear and trustworthy explanations for the shopper.

User's original request:
"{query.raw_query}"

Quality preferences:
{query.quality_tags}

Ranked products:

{products_text}

Rules:

1. Write exactly one explanation for every product.

2. Keep the same order as the ranked products.

3. Copy every ASIN exactly as provided.
   Never modify, invent, or substitute an ASIN.

4. Ground explanations ONLY in the provided query,
   product information, scores, and pre-computed reasons.

5. Do not invent product specifications, features,
   review details, or customer opinions.

6. Mention weaknesses when they appear in the
   pre-computed reasons.

7. Keep each explanation to 1-2 sentences.

8. Keep key_factors short, around 3-5 words each.

9. query_summary should be one short sentence
   describing what the user requested.
""".strip()