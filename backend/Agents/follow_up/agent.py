import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from .schema import FollowUpResult

load_dotenv()

MODEL_NAME = "gemini-3.5-flash-lite"


class FollowUpAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")
        self.client = genai.Client(api_key=api_key)

    def suggest(self, query, ranking_result) -> FollowUpResult:
        facts = self._compute_result_facts(ranking_result)
        prompt = self._build_prompt(query, ranking_result, facts)

        response = self.client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FollowUpResult,
                temperature=0.3,
            ),
        )
        return FollowUpResult.model_validate_json(response.text)

    def _compute_result_facts(self, ranking_result) -> dict:
        products = ranking_result.products
        total = len(products)

        prices = [p.price_inr for p in products if p.price_inr is not None]
        if prices:
            price_range_text = f"₹{min(prices):.0f}-₹{max(prices):.0f} (average ₹{sum(prices)/len(prices):.0f})"
        else:
            price_range_text = "unknown (no price data available)"

        families = [" ".join(p.title.lower().split()[:3]) for p in products]
        distinct_families = len(set(families))

        return {
            "total_products": total,
            "price_range": price_range_text,
            "distinct_model_families": distinct_families,
        }

    def _build_prompt(self, query, ranking_result, facts: dict) -> str:
        titles = "\n".join(f"  - {p.title} (₹{p.price_inr if p.price_inr is not None else 'N/A'})"
                            for p in ranking_result.products)

        return f"""
You are the Follow-up Agent for RetailMind AI. Based on the search
results below, suggest 2-4 natural next questions or actions the user
might want -- things that would genuinely help them decide, not generic
filler.

User's original request: "{query.raw_query}"

Results returned:
{titles}

Facts about this result set:
- Total products shown: {facts['total_products']}
- Price range: {facts['price_range']}
- Distinct model families detected (rough estimate, based on title
  similarity): {facts['distinct_model_families']} out of {facts['total_products']}

Guidance (use judgement, these are not rigid rules):
- If distinct_model_families is much smaller than total_products, most
  results are variants of the same phone line -- consider suggesting
  the user broaden their brand or category to see more variety.
- If the price range is very narrow, a budget-adjustment suggestion is
  probably not useful; if it's wide, suggesting a tighter budget filter
  might help.
- If there are multiple genuinely different strong options, suggesting
  a side-by-side comparison of the top 2-3 is often useful.
- Only suggest clarifying the request if something about it was
  ambiguous (e.g. no budget given, or a vague quality term).

For each suggestion, pick the suggestion_type that best matches its intent:
  compare, refine_filter, broaden_search, or clarify.
Keep each suggestion_text short, natural, and phrased as something you'd
actually say to the user.
"""