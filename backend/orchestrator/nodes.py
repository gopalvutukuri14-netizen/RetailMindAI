"""
Node functions for the LangGraph orchestrator.

Each function:
1. Reads the required values from PipelineState.
2. Calls the relevant agent.
3. Returns a partial dictionary for LangGraph to merge into state.

Expensive resources are initialized lazily and reused.
"""

import os
import logging

from dotenv import load_dotenv
from google import genai
from google.genai import types

from backend.Agents.query_understanding import (
    QueryUnderstandingAgent,
    Intent,
)
from backend.Agents.retrieval import RetrievalAgent
from backend.Agents.memory import MemoryAgent
from backend.Agents.ranking import RankingAgent
from backend.Agents.xai import XAIAgent
from backend.Agents.follow_up import FollowUpAgent
from backend.Agents.response import (
    ResponseAgent,
    ResponseResult,
)
from backend.pipeline.retrieval import ProductRetriever
from backend.Agents.gemini_retry import call_with_retry

from .state import PipelineState

load_dotenv()

logger = logging.getLogger(__name__)


# ================================================================
# SUPPORTED PRODUCT CATEGORIES
# ================================================================

SUPPORTED_CATEGORIES = {
    "cell_phones_and_accessories": "Cell Phones & Accessories",
    "electronics": "Electronics",
    "home_and_kitchen": "Home & Kitchen",
    "clothing_shoes_and_jewelry": "Clothing, Shoes & Jewelry",
    "office_products": "Office Products",
    "sports_and_outdoors": "Sports & Outdoors",
}


def _normalize_category(category: str | None) -> str:
    """Normalize category names for reliable category comparisons."""
    if not category:
        return ""

    return "_".join(category.casefold().strip().replace("&", "and").split())


def _get_category_label(category: str | None) -> str:
    """Return a readable category name."""
    normalized = _normalize_category(category)

    if normalized in SUPPORTED_CATEGORIES:
        return SUPPORTED_CATEGORIES[normalized]

    return (category or "unknown product").strip()


# ================================================================
# LAZY SINGLETON AGENT INSTANCES
# ================================================================

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


# ================================================================
# QUERY UNDERSTANDING NODE
# ================================================================

def query_understanding_node(state: PipelineState) -> dict:
    """
    Convert the user's natural-language query into structured fields,
    including intent, category, product type, budget, brand and specs.
    """
    agent = _get_query_understanding_agent()
    result = agent.understand(state["raw_query"])

    return {"query_understanding": result}


# ================================================================
# ROUTER NODE
# ================================================================

def router_node(state: PipelineState) -> dict:
    """
    Route the request to the appropriate pipeline.

    Routes:
      product_pipeline  -> retrieval, memory, ranking, XAI,
                           follow-up and response
      context_response  -> comparison/follow-up using previous products
      general_response  -> greetings and general questions
      out_of_scope      -> unsupported product categories
    """
    qu = state["query_understanding"]
    intent = qu.intent
    has_previous = bool(state.get("previous_products"))

    # 1. General questions do not need product retrieval.
    if intent == Intent.GENERAL_QUESTION:
        return {"route": "general_response"}

    # 2. Use conversation context for follow-up/comparison requests
    # when previous recommendations are available.
    if intent in (Intent.FOLLOW_UP, Intent.COMPARISON) and has_previous:
        return {"route": "context_response"}

    # 3. Check whether the category belongs to our dataset.
    category = _normalize_category(qu.category)

    if category and category not in SUPPORTED_CATEGORIES:
        return {"route": "out_of_scope"}

    # 4. If category is empty, allow the query to continue.
    # Query Understanding may not always identify a category, and
    # the retrieval agent can still attempt to interpret the query.
    return {"route": "product_pipeline"}


# ================================================================
# RETRIEVAL NODE
# ================================================================

def retrieval_node(state: PipelineState) -> dict:
    """
    Retrieve semantically relevant products from ChromaDB.

    The Retrieval Agent applies the category, budget, brand and
    product-type logic defined in its own implementation.
    """
    agent = _get_retrieval_agent()
    top_k = state.get("top_k", 10)

    result = agent.retrieve(
        state["query_understanding"],
        top_k=top_k,
    )

    return {"retrieval_result": result}


# ================================================================
# MEMORY NODE
# ================================================================

def memory_node(state: PipelineState) -> dict:
    """Load the user's stored preferences from SQLite."""
    agent = _get_memory_agent()
    user_id = state.get("user_id", "anonymous")

    result = agent.get_profile(user_id)

    return {"user_profile": result}


# ================================================================
# RANKING NODE
# ================================================================

def ranking_node(state: PipelineState) -> dict:
    """
    Rank retrieved products using similarity, specifications,
    sentiment, aspect alignment and user preferences.
    """
    agent = _get_ranking_agent()

    result = agent.rank(
        state["query_understanding"],
        state["retrieval_result"],
        state.get("user_profile"),
    )

    return {"ranking_result": result}


# ================================================================
# EXPLAINABLE AI NODE
# ================================================================

def xai_node(state: PipelineState) -> dict:
    """Generate explanations for the ranked products."""
    agent = _get_xai_agent()

    result = agent.explain(
        state["query_understanding"],
        state["ranking_result"],
    )

    return {"xai_result": result}


# ================================================================
# FOLLOW-UP NODE
# ================================================================

def followup_node(state: PipelineState) -> dict:
    """Generate useful next-step suggestions based on recommendations."""
    agent = _get_followup_agent()

    result = agent.suggest(
        state["query_understanding"],
        state["ranking_result"],
    )

    return {"followup_result": result}


# ================================================================
# FINAL RESPONSE NODE
# ================================================================

def response_node(state: PipelineState) -> dict:
    """Build the structured final response for the API/frontend."""
    agent = _get_response_agent()

    result = agent.generate(
        state["query_understanding"],
        state["ranking_result"],
        state["xai_result"],
        state["followup_result"],
    )

    return {"response_result": result}


# ================================================================
# GENERAL RESPONSE NODE
# ================================================================

def general_response_node(state: PipelineState) -> dict:
    """
    Handle greetings, general questions and similar requests
    without invoking product retrieval or ranking.
    """
    client = _get_gemini_client()
    raw_query = state["raw_query"]

    prompt = f"""
You are RetailMind AI, a retail product recommendation assistant.

Our current catalog supports these categories:
- Cell Phones & Accessories
- Electronics
- Home & Kitchen
- Clothing, Shoes & Jewelry
- Office Products
- Sports & Outdoors

The user said:
{raw_query}

This is a general question rather than a product search.

Instructions:
1. Respond naturally and helpfully.
2. Answer general questions concisely.
3. Do not invent catalog products, prices, or availability.
4. Do not generate product recommendations for this request.
5. Keep the response to 1-3 sentences.
"""

    def _call():
        return client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.5,
            ),
        )

    try:
        response = call_with_retry(_call, context="general_response_node")
        summary = (response.text or "").strip() or "How can I help with your shopping today?"
    except Exception as exc:
        logger.warning("general_response_node: Gemini unavailable: %s", exc)
        summary = "How can I help with your shopping today?"

    result = ResponseResult(
        summary=summary,
        recommendations=[],
        additional_information="",
        follow_up_suggestions=[
            "Find products within my budget",
            "Recommend the best-rated products",
            "Help me compare two products",
        ],
    )

    return {"response_result": result}


# ================================================================
# OUT-OF-SCOPE RESPONSE NODE
# ================================================================

def out_of_scope_node(state: PipelineState) -> dict:
    """
    Explain that the requested category is not in the current catalog.
    """
    category = _get_category_label(
        state["query_understanding"].category
    )

    result = ResponseResult(
        summary=(
            f"You're looking for products in {category}. "
            "RetailMind AI currently supports six product categories: "
            "Cell Phones & Accessories, Electronics, Home & Kitchen, "
            "Clothing, Shoes & Jewelry, Office Products, and "
            "Sports & Outdoors. I couldn't identify your requested "
            "category as one of the supported categories, so I can't "
            "provide reliable recommendations for it."
        ),
        recommendations=[],
        additional_information=(
            "Try specifying a product from one of the supported categories."
        ),
        follow_up_suggestions=[
            "Find wireless headphones",
            "Find a non-stick cookware set",
            "Recommend running shoes",
        ],
    )

    return {"response_result": result}


# ================================================================
# CONTEXT / COMPARISON RESPONSE NODE
# ================================================================

def context_response_node(state: PipelineState) -> dict:
    """
    Handle comparisons and follow-up questions using previously
    returned products rather than performing a new retrieval.
    """
    client = _get_gemini_client()

    raw_query = state["raw_query"]
    previous = state.get("previous_products", [])
    intent = state["query_understanding"].intent

    # Build a factual representation of the previous recommendations.
    product_lines = []

    for i, product in enumerate(previous, start=1):
        title = product.get("title", "Unknown")
        brand = product.get("brand", "N/A")
        price = product.get("price_inr")
        price_str = f"₹{price}" if price is not None else "Not available"
        explanation = product.get("explanation", "")
        key_factors = ", ".join(product.get("key_factors", []))

        product_lines.append(
            f"#{i} {title} | Brand: {brand} | Price: {price_str}\n"
            f"Why recommended: {explanation}\n"
            f"Key factors: {key_factors}"
        )

    products_text = "\n\n".join(product_lines)

    if intent == Intent.COMPARISON:
        task = (
            "Compare the top two products. Explain their differences "
            "using only the available product information, including "
            "price, brand, features and customer sentiment when available."
        )
    else:
        task = (
            "Answer the user's follow-up using only the previously "
            "shown products. Do not invent new products or attributes."
        )

    prompt = f"""
You are RetailMind AI, a retail product recommendation assistant.

Previously returned products:

{products_text}

User's new question:
{raw_query}

Task:
{task}

Rules:
1. Reference only products included in the supplied context.
2. Never invent product specifications, prices or review statistics.
3. If a detail is unavailable, say that it is unavailable.
4. Keep the response clear and useful.
5. Return JSON matching the required response schema.
"""

    def _call():
        return client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ResponseResult,
                temperature=0.3,
            ),
        )

    try:
        response = call_with_retry(_call, context="context_response_node")
        if not response.text:
            raise RuntimeError("context_response_node: empty Gemini response")
        result = ResponseResult.model_validate_json(response.text)
    except Exception as exc:
        logger.warning(
            "context_response_node: Gemini unavailable, using plain fallback: %s", exc
        )
        from backend.Agents.response.schema import ResponseProduct
        recs = [
            ResponseProduct(
                asin=p.get("asin", ""),
                title=p.get("title", "Unknown"),
                brand=p.get("brand"),
                price_inr=p.get("price_inr"),
                image_url=p.get("image_url"),
                explanation=p.get("explanation", ""),
                key_factors=p.get("key_factors", []),
            )
            for p in previous
        ]
        return {
            "response_result": ResponseResult(
                summary="Here are the previously recommended products for your follow-up.",
                recommendations=recs,
                additional_information="",
                follow_up_suggestions=[],
            )
        }

    # Preserve factual product identity, prices, and image URLs from previous results.
    previous_by_title = {
        product.get("title", "").casefold().strip(): product
        for product in previous
    }

    for recommendation in result.recommendations:
        match = previous_by_title.get(
            recommendation.title.casefold().strip()
        )

        if match:
            recommendation.asin = match.get(
                "asin", recommendation.asin
            )
            recommendation.brand = match.get(
                "brand", recommendation.brand
            )
            recommendation.price_inr = match.get(
                "price_inr", recommendation.price_inr
            )
            if "image_url" in match:
                recommendation.image_url = match.get("image_url")

    return {"response_result": result}