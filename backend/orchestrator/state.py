"""
Shared state definition for the LangGraph orchestrator.

Every node in the pipeline reads from and writes to this TypedDict.
LangGraph merges partial dicts returned by each node into the
accumulating state automatically.
"""

from typing import TypedDict, Optional

from backend.Agents.query_understanding import QueryUnderstanding
from backend.Agents.retrieval import RetrievalResult
from backend.Agents.memory import UserProfile
from backend.Agents.ranking import RankingResult
from backend.Agents.xai import XAIResult
from backend.Agents.follow_up import FollowUpResult
from backend.Agents.response import ResponseResult


class PipelineState(TypedDict, total=False):
    """
    Full state flowing through the RetailMind AI pipeline.

    Fields are populated incrementally as each node executes.
    ``total=False`` means every key is optional at construction time —
    we start with just ``raw_query`` + ``user_id`` and the graph fills
    the rest.
    """

    # ── Inputs (set before the graph starts) ──────────────────────
    raw_query: str
    user_id: str
    top_k: int

    # ── Agent outputs (populated as nodes execute) ────────────────
    query_understanding: QueryUnderstanding
    retrieval_result: RetrievalResult
    user_profile: UserProfile
    ranking_result: RankingResult
    xai_result: XAIResult
    followup_result: FollowUpResult
    response_result: ResponseResult

    # ── Error tracking ────────────────────────────────────────────
    error: Optional[str]
