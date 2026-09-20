"""
Node functions for the LangGraph orchestrator.

Each function is a thin wrapper around one agent:
  1. Reads what it needs from PipelineState
  2. Calls the agent
  3. Returns a partial dict that LangGraph merges into state

Expensive resources (BGE-M3 model, ChromaDB, Gemini clients) are
created once at module level and reused across requests — they are
thread-safe for read-only inference and stateless API calls.
"""

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from backend.Agents.query_understanding import QueryUnderstandingAgent, Intent
from backend.Agents.retrieval import RetrievalAgent
from backend.Agents.memory import MemoryAgent
from backend.Agents.ranking import RankingAgent
from backend.Agents.xai import XAIAgent
from backend.Agents.follow_up import FollowUpAgent
from backend.Agents.response import ResponseAgent, ResponseResult, ResponseProduct
from backend.pipeline.retrieval import ProductRetriever

from .state import PipelineState

load_dotenv()


# ── Singleton agent instances ────────────────────────────────────
# Instantiated lazily on first use, then cached for the process
# lifetime.  This avoids loading the BGE-M3 model (≈2 GB) on every
# request while still keeping the import side-effect-free.

_query_understanding_agent: QueryUnderstandingAgent | None = None
_retriever: ProductRetriever | None = None
_retrieval_agent: RetrievalAgent | None = None
_memory_agent: MemoryAgent | None = None
_ranking_agent: RankingAgent | None = None
_xai_agent: XAIAgent | None = None
_followup_agent: FollowUpAgent | None = None
_response_agent: ResponseAgent | None = None
_gemini_client: genai.Client | None = None


def _get_query_understanding_agent() -> QueryUnderstandingAgent:
    global _query_understanding_agent
    if _query_understanding_agent is None:
        _query_understanding_agent = QueryUnderstandingAgent()
    return _query_understanding_agent


def _get_retrieval_agent() -> RetrievalAgent:
    global _retriever, _retrieval_agent
    if _retrieval_agent is None:
        _retriever = ProductRetriever()
        _retrieval_agent = RetrievalAgent(retriever=_retriever)
    return _retrieval_agent


def _get_memory_agent() -> MemoryAgent:
    global _memory_agent
    if _memory_agent is None:
        _memory_agent = MemoryAgent()
    return _memory_agent


def _get_ranking_agent() -> RankingAgent:
    global _ranking_agent
    if _ranking_agent is None:
        _ranking_agent = RankingAgent()
    return _ranking_agent


def _get_xai_agent() -> XAIAgent:
    global _xai_agent
    if _xai_agent is None:
        _xai_agent = XAIAgent()
    return _xai_agent


def _get_followup_agent() -> FollowUpAgent:
    global _followup_agent
    if _followup_agent is None:
        _followup_agent = FollowUpAgent()
    return _followup_agent


def _get_response_agent() -> ResponseAgent:
    global _response_agent
    if _response_agent is None:
        _response_agent = ResponseAgent()
    return _response_agent


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


# ── Node functions ───────────────────────────────────────────────
# Each returns a partial dict that LangGraph merges into state.


def query_understanding_node(state: PipelineState) -> dict:
    """
    Parse the raw user query into structured fields:
    intent, category, budget, brand preferences, specs, quality tags.
    """
    agent = _get_query_understanding_agent()
    result = agent.understand(state["raw_query"])
    return {"query_understanding": result}


def router_node(state: PipelineState) -> dict:
    """
    Decide which pipeline branch to take based on the parsed intent,
    category scope, and whether previous conversation context is available.

    Routes:
      - "product_pipeline"  → full retrieval → ranking → xai → response
      - "context_response"  → use previous products for comparison/follow-up
      - "general_response"  → handle greetings, goodbyes, general questions
      - "out_of_scope"      → category not in our dataset (we only have cell phones)
    """
    qu = state["query_understanding"]
    intent = qu.intent
    has_previous = bool(state.get("previous_products"))

    # 1. General questions (greetings, goodbyes, "what is AMOLED?")
    if intent == Intent.GENERAL_QUESTION:
        return {"route": "general_response"}

    # 2. Follow-up / comparison with previous context
    if intent in (Intent.FOLLOW_UP, Intent.COMPARISON) and has_previous:
        return {"route": "context_response"}

    # 3. Out-of-scope category detection
    #    Our dataset only covers: cell phones, smartphones, mobile phones,
    #    and phone accessories. Everything else is out of scope.
    category = (qu.category or "").lower().strip()

    # If category is empty, the LLM couldn't determine it — default to
    # in-scope (assume it's about phones).
    if category:
        IN_SCOPE_KEYWORDS = [
            "phone", "smartphone", "mobile", "cell", "cellphone",
            "handset", "android", "iphone", "samsung", "accessory",
            "accessories", "case", "charger", "cable", "headset",
            "earphone", "earbuds", "screen protector",
        ]
        is_in_scope = any(kw in category for kw in IN_SCOPE_KEYWORDS)

        if not is_in_scope:
            return {"route": "out_of_scope"}

    # 4. Default: full product pipeline
    return {"route": "product_pipeline"}


def retrieval_node(state: PipelineState) -> dict:
    """
    Semantic search over ChromaDB using the parsed query.
    Returns top-K candidate products with metadata + meets_* flags.
    """
    agent = _get_retrieval_agent()
    top_k = state.get("top_k", 10)
    result = agent.retrieve(state["query_understanding"], top_k=top_k)
    return {"retrieval_result": result}


def memory_node(state: PipelineState) -> dict:
    """
    Load the user's stored preference profile from SQLite.
    Returns an empty profile (not an error) for unknown users.
    """
    agent = _get_memory_agent()
    user_id = state.get("user_id", "anonymous")
    result = agent.get_profile(user_id)
    return {"user_profile": result}


def ranking_node(state: PipelineState) -> dict:
    """
    Score and rank candidates using similarity, spec match, sentiment,
    aspect alignment, and memory alignment signals.
    """
    agent = _get_ranking_agent()
    result = agent.rank(
        state["query_understanding"],
        state["retrieval_result"],
        state.get("user_profile"),
    )
    return {"ranking_result": result}


def xai_node(state: PipelineState) -> dict:
    """
    Generate natural-language explanations for why each product
    was ranked the way it was.
    """
    agent = _get_xai_agent()
    result = agent.explain(
        state["query_understanding"],
        state["ranking_result"],
    )
    return {"xai_result": result}


def followup_node(state: PipelineState) -> dict:
    """
    Suggest 2-4 natural next questions or actions the user
    might want to take based on the results.
    """
    agent = _get_followup_agent()
    result = agent.suggest(
        state["query_understanding"],
        state["ranking_result"],
    )
    return {"followup_result": result}


def response_node(state: PipelineState) -> dict:
    """
    Synthesize all upstream outputs into the final structured
    response for the frontend.
    """
    agent = _get_response_agent()
    result = agent.generate(
        state["query_understanding"],
        state["ranking_result"],
        state["xai_result"],
        state["followup_result"],
    )
    return {"response_result": result}


# ── Shortcut nodes (bypass the heavy product pipeline) ───────────


def general_response_node(state: PipelineState) -> dict:
    """
    Handle non-product queries: greetings, goodbyes, general questions
    like "What is AMOLED?". No retrieval, no ranking — just a direct
    LLM response.
    """
    client = _get_gemini_client()
    raw_query = state["raw_query"]

    prompt = f"""
You are RetailMind AI, a friendly and helpful shopping assistant
specializing in smartphones.

The user said: "{raw_query}"

This is NOT a product search — it's a greeting, goodbye, or general
question. Respond naturally and helpfully.

Rules:
1. If it's a greeting, welcome them warmly and remind them you can
   help find smartphones.
2. If it's a goodbye, thank them and wish them well.
3. If it's a general question (e.g. "What is AMOLED?"), answer it
   concisely from your knowledge.
4. Keep the response short (1-3 sentences).
5. Do NOT recommend any products.
6. Do NOT make up product names or prices.
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.5),
    )

    result = ResponseResult(
        summary=response.text.strip(),
        recommendations=[],
        additional_information="",
        follow_up_suggestions=[
            "Show me budget phones under 10000",
            "What Samsung phones do you recommend?",
            "Find me a phone with great camera",
        ],
    )
    return {"response_result": result}


def out_of_scope_node(state: PipelineState) -> dict:
    """
    Handle queries about categories we don't have data for.
    Our dataset only covers cell phones & accessories — anything else
    (watches, laptops, TVs, etc.) gets a polite redirect.
    """
    category = (state["query_understanding"].category or "unknown product").strip()
    raw_query = state["raw_query"]

    result = ResponseResult(
        summary=(
            f"I appreciate your interest in {category}! However, RetailMind AI "
            f"currently specializes in **cell phones and smartphone accessories** only. "
            f"I don't have data on {category} in my catalog, so I can't provide "
            f"accurate recommendations for that category.\n\n"
            f"But I'd love to help you find the perfect phone! Try asking something like "
            f"the suggestions below."
        ),
        recommendations=[],
        additional_information="",
        follow_up_suggestions=[
            "Show me budget phones under 10000",
            "Best Samsung phone with good camera",
            "Premium phone with great display and battery",
        ],
    )
    return {"response_result": result}


def context_response_node(state: PipelineState) -> dict:
    """
    Handle follow-up/comparison queries that reference previously
    shown products. Uses the previous products from conversation
    context instead of running a new retrieval.
    """
    client = _get_gemini_client()
    raw_query = state["raw_query"]
    previous = state.get("previous_products", [])
    intent = state["query_understanding"].intent

    # Build product context from previous results
    product_lines = []
    for i, p in enumerate(previous, start=1):
        title = p.get("title", "Unknown")
        brand = p.get("brand", "N/A")
        price = p.get("price_inr")
        price_str = f"Rs.{price}" if price is not None else "N/A"
        explanation = p.get("explanation", "")
        key_factors = ", ".join(p.get("key_factors", []))
        product_lines.append(
            f"#{i} {title} | Brand: {brand} | Price: {price_str}\n"
            f"    Why recommended: {explanation}\n"
            f"    Key factors: {key_factors}"
        )
    products_text = "\n\n".join(product_lines)

    if intent == Intent.COMPARISON:
        task = (
            "Compare the top 2 products in detail. Highlight their "
            "differences in price, brand, features, and customer sentiment. "
            "Present it as a clear side-by-side comparison."
        )
    else:
        task = (
            "Answer the user's follow-up question using ONLY the "
            "previously shown products. Do not invent new products."
        )

    prompt = f"""
You are RetailMind AI, a shopping assistant specializing in smartphones.

The user previously received these product recommendations:

{products_text}

Now the user asks: "{raw_query}"

Task: {task}

Rules:
1. ONLY reference the products shown above. Never invent products.
2. Use the actual product names, prices, and details from above.
3. Be specific and helpful.
4. Keep the response concise but informative.
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ResponseResult,
            temperature=0.3,
        ),
    )

    result = ResponseResult.model_validate_json(response.text)

    # Override product identity from the previous context to avoid
    # LLM hallucinating ASINs/prices.  Only keep products that match
    # the previous set (the LLM may have selected a subset for comparison).
    prev_by_title = {}
    for p in previous:
        prev_by_title[p.get("title", "").lower().strip()] = p

    for rp in result.recommendations:
        match = prev_by_title.get(rp.title.lower().strip())
        if match:
            rp.asin = match.get("asin", rp.asin)
            rp.brand = match.get("brand", rp.brand)
            rp.price_inr = match.get("price_inr", rp.price_inr)

    return {"response_result": result}
