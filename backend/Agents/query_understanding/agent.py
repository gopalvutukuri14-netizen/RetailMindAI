import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from .schema import QueryUnderstanding

load_dotenv()

# Lightweight structured-extraction task -> use the Flash-Lite tier, not the
# flagship coding/agent model. Cheaper, faster, and more than sufficient here.
# Verify the current stable Flash-Lite model ID in your Google AI Studio
# console before relying on this string long-term -- Google ships new model
# IDs frequently, and you want a "stable" (non "-preview") tagged one.
MODEL_NAME = "gemini-3.5-flash-lite"


class QueryUnderstandingAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")
        self.client = genai.Client(api_key=api_key)

    def understand(self, query: str) -> QueryUnderstanding:
        prompt = f"""
You are the Query Understanding Agent for RetailMind AI,
an AI-powered retail product recommendation system.
Your task is to understand the user's natural-language query
and extract the relevant shopping requirements.

Follow these rules carefully:

1. Identify the intent as one of:
   - product_recommendation
   - comparison
   - follow_up
   - general_question

2. Identify the product category if mentioned.

3. Extract the minimum and maximum budget if mentioned.

4. Extract preferred and excluded brands.

5. Extract product specifications ONLY when the user gives an explicit
   number in the query:
   - RAM (in GB)
   - storage (in GB)
   - minimum camera megapixels
   - minimum battery capacity (in mAh)
   If the user does not state an explicit number for a spec, leave that
   field as null. Do NOT estimate or infer a number from vague language
   like "good camera" or "long battery" -- those belong in quality_tags
   instead (see rule 6).

6. Extract quality requirements that are described in words rather than
   numbers, such as:
   - good camera
   - long battery
   - gaming
   - premium display
   Put these phrases in quality_tags exactly as the user implies them,
   even when a corresponding specs field (rule 5) is left null.

7. Extract hard constraints explicitly required by the user (e.g.
   "not refurbished", "must be in stock", "5G only").

8. Do not invent information that is not present in the query. Numeric
   spec values must come directly from a number the user stated -- never
   from your own estimate of what a qualitative phrase "usually" means.

9. Always preserve the original query in raw_query.

10. For product category, use canonical retail categories.
For mobile phones, always use "smartphone" rather than "phone".

User query:
{query}
"""
        response = self.client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QueryUnderstanding,
                temperature=0.1,  # low variance -- this is extraction, not creative generation
            ),
        )
        return QueryUnderstanding.model_validate_json(response.text)


def demo():
    agent = QueryUnderstandingAgent()
    query = (
        "What is the difference between AMOLED and OLED?"
    )
    result = agent.understand(query)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    demo()