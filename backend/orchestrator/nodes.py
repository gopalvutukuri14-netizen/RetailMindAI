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

from backend.Agents.query_understanding import QueryUnderstandingAgent
from backend.Agents.retrieval import RetrievalAgent
from backend.Agents.memory import MemoryAgent
from backend.Agents.ranking import RankingAgent
from backend.Agents.xai import XAIAgent
from backend.Agents.follow_up import FollowUpAgent
from backend.Agents.response import ResponseAgent
from backend.pipeline.retrieval import ProductRetriever

from .state import PipelineState


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
