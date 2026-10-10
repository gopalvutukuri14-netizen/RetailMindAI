import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .schema import QueryUnderstanding


MODEL_NAME = "gemini-3.5-flash-lite"


class QueryUnderstandingAgent:

    def __init__(self):
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set in the environment."
            )

        self.client = genai.Client(
            api_key=api_key
        )

    def understand(self, query: str) -> QueryUnderstanding:

        prompt = f"""
You are the Query Understanding Agent for RetailMind AI.

Your job is ONLY to convert the user's natural-language
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

BUDGET

Extract budget only when the user explicitly gives
a budget.

Do NOT invent a budget.

Use:
- budget_min
- budget_max

BRANDS

Extract preferred brands only when explicitly mentioned.

Extract excluded brands only when explicitly mentioned.

Do NOT invent brands.

NUMERIC PRODUCT SPECIFICATIONS

Extract these specifications ONLY when explicitly
stated by the user:

- RAM in GB
- storage in GB
- minimum camera megapixels
- minimum battery capacity in mAh

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

HARD CONSTRAINTS

Put explicit non-negotiable requirements into
hard_constraints.

COMPARISON

For comparison queries, identify comparison intent.

Do not invent products or comparison criteria.

FOLLOW-UP

For follow-up queries, preserve follow-up intent.

GENERAL QUESTIONS

For general questions that are not product
recommendations, use general_question.

RAW QUERY

Always preserve the user's exact query in raw_query.

IMPORTANT

Do not recommend products.
Do not retrieve products.
Do not answer the user's question.

Only understand and structure the query.

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

        if not response.parsed:
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

            print(
                result.model_dump_json(
                    indent=2
                )
            )

        except Exception as exc:

            print(
                f"ERROR: {type(exc).__name__}: {exc}"
            )