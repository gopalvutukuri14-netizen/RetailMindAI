
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .schema import QueryUnderstanding


MODEL_NAME = "gemini-3.5-flash-lite"


class QueryUnderstandingAgent:
    """Convert natural-language retail queries into structured data."""

    def __init__(self):
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set in the environment."
            )

        self.client = genai.Client(api_key=api_key)

    def understand(self, query: str) -> QueryUnderstanding:
        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        prompt = f"""
You are the Query Understanding Agent for RetailMind AI.

Your ONLY task is to convert the user's natural-language
retail query into the structured QueryUnderstanding schema.

Do NOT recommend products.
Do NOT retrieve products.
Do NOT answer the user's question.
Do NOT invent facts, prices, specifications, brands,
or constraints.

SUPPORTED RETAIL CATEGORIES

Use exactly one of these categories when the category
can be determined:

1. Cell_Phones_and_Accessories
2. Electronics
3. Home_and_Kitchen
4. Clothing_Shoes_and_Jewelry
5. Office_Products
6. Sports_and_Outdoors

CATEGORY GUIDANCE

Cell_Phones_and_Accessories:
- smartphone
- mobile phone
- phone
- phone accessories

Electronics:
- laptop
- headphones
- earbuds
- monitor
- television
- camera

Home_and_Kitchen:
- cookware
- kitchen appliance
- vacuum
- blender

Clothing_Shoes_and_Jewelry:
- shirt
- dress
- jacket
- shoes
- jewelry

Office_Products:
- office chair
- printer
- stationery
- desk organizer

Sports_and_Outdoors:
- running shoes
- football gear
- fitness equipment
- sports equipment

Choose the category that best matches the requested product.

If the category is unclear, use null.

INTENT

Intent must be one of:
- product_recommendation
- comparison
- follow_up
- general_question

Use product_recommendation for requests to find or recommend
products.

Use comparison when the user asks to compare products,
brands, or product features.

Use follow_up when the user refers to previous recommendations
or asks a follow-up about previously discussed products.

Use general_question for general informational questions
that are not product recommendation requests.

PRODUCT TYPE

Extract the specific main product being requested into
product_type.

Examples:
- "Samsung phone under ₹30000" -> "phone"
- "wireless headphones for gaming" -> "headphones"
- "non-stick cookware set" -> "cookware set"
- "durable jacket" -> "jacket"
- "comfortable office chair" -> "office chair"
- "durable running shoes" -> "running shoes"
- "running socks" -> "running socks"
- "hiking backpack" -> "backpack"

Rules:
- Extract the requested product, not its broad retail category.
- Preserve meaningful product-type terms such as "running shoes",
  "office chair", and "gaming headset".
- Do not include the brand, budget, or quality requirements
  in product_type.
- Do not confuse a product with a related accessory.
- If the query clearly requests multiple product types, or
  the product type cannot be determined, use null.
- For general questions such as "What is AMOLED?", use null
  unless a specific product is being requested.

BUDGET

Extract a budget only when explicitly stated.

Use:
- budget_min for the minimum price
- budget_max for the maximum price

Examples:
- "under ₹30000" -> budget_max = 30000
- "above ₹5000" -> budget_min = 5000
- "between ₹10000 and ₹20000" ->
  budget_min = 10000 and budget_max = 20000

Do not invent a budget.

BRANDS

Extract preferred brands only when explicitly mentioned.

Extract excluded brands only when explicitly excluded.

Do not invent brands.

NUMERIC PRODUCT SPECIFICATIONS

Extract the following only when explicitly stated:
- RAM in GB -> ram_gb
- storage in GB -> storage_gb
- minimum camera megapixels -> camera_mp_min
- minimum battery capacity in mAh -> battery_mah_min

Do not infer missing specifications from product names
or general knowledge.

QUALITATIVE REQUIREMENTS

Put qualitative requirements into quality_tags.

Examples:
- good camera
- comfortable
- durable
- lightweight
- gaming
- premium
- fast
- non-stick

Do not put the requested product type itself in quality_tags
unless it also expresses a separate quality or usage requirement.

HARD CONSTRAINTS

Put explicit non-negotiable requirements into hard_constraints.

Do not duplicate budget requirements or numeric specifications
in hard_constraints when they are already represented by
their dedicated fields.

COMPARISON

For comparison queries, identify comparison intent.

Extract a product_type only if the requested product type
can be identified clearly.

Do not invent products or comparison criteria.

FOLLOW-UP

For follow-up queries, preserve follow_up intent when the user
is referring to previously discussed products or recommendations.

If the product type cannot be identified from the current
query alone, use null rather than guessing.

GENERAL QUESTIONS

For general questions that are not product recommendations,
use general_question.

For example:
"What is the difference between AMOLED and OLED?"

This should be a general_question, with product_type = null
unless the user also requests a specific product.

RAW QUERY

Always preserve the user's original query in raw_query
without rewriting or summarizing it.

FINAL RULES

Return data matching the QueryUnderstanding schema exactly.
Use null for unknown optional values.
Do not recommend products, retrieve products, or answer
the user's question.

USER QUERY:
{query}
"""

        response = self.client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=QueryUnderstanding,
            ),
        )

        if response.parsed is None:
            raise RuntimeError(
                "Gemini returned no parsed QueryUnderstanding."
            )

        return response.parsed


if __name__ == "__main__":
    agent = QueryUnderstandingAgent()

    test_queries = [
        "Samsung phone under ₹30,000 with 8GB RAM and a good camera",
        "wireless headphones for gaming under ₹10,000",
        "comfortable office chair under ₹15,000",
        "durable running shoes",
        "non-stick cookware set under ₹5,000",
        "What is the difference between AMOLED and OLED?",
    ]

    print("=" * 70)
    print("RETAILMIND AI - QUERY UNDERSTANDING AGENT")
    print("=" * 70)

    for query in test_queries:
        print(f"\nQuery: {query}")

        try:
            result = agent.understand(query)

            print(result.model_dump_json(indent=2))

        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")
