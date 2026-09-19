"""
LangGraph StateGraph wiring for RetailMind AI.

Builds the full agent pipeline as a directed graph:

    START
      │
      ▼
    query_understanding
      │
      ├──────────────┐
      ▼              ▼
    retrieval      memory       (parallel — no dependency between them)
      │              │
      └──────┬───────┘
             ▼
          ranking               (waits for both retrieval + memory)
             │
      ┌──────┴──────┐
      ▼             ▼
     xai        follow_up       (parallel — no dependency between them)
      │             │
      └──────┬──────┘
             ▼
          response              (waits for both xai + follow_up)
             │
             ▼
            END

``run_pipeline()`` is the single entry point used by the API.
"""

from langgraph.graph import StateGraph, START, END

from .state import PipelineState
from .nodes import (
    query_understanding_node,
    retrieval_node,
    memory_node,
    ranking_node,
    xai_node,
    followup_node,
    response_node,
)

from backend.Agents.response import ResponseResult


def build_graph() -> StateGraph:
    """
    Construct and compile the RetailMind AI pipeline graph.

    Returns a compiled LangGraph ``CompiledGraph`` that accepts a
    ``PipelineState`` dict and executes all nodes in dependency order.
    """

    graph = StateGraph(PipelineState)

    # ── Register nodes ───────────────────────────────────────────
    graph.add_node("query_understanding", query_understanding_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("memory", memory_node)
    graph.add_node("ranking", ranking_node)
    graph.add_node("xai", xai_node)
    graph.add_node("follow_up", followup_node)
    graph.add_node("response", response_node)

    # ── Wire edges ───────────────────────────────────────────────
    # Entry point
    graph.add_edge(START, "query_understanding")

    # After query understanding: fan out to retrieval + memory
    graph.add_edge("query_understanding", "retrieval")
    graph.add_edge("query_understanding", "memory")

    # Ranking waits for both retrieval and memory
    graph.add_edge("retrieval", "ranking")
    graph.add_edge("memory", "ranking")

    # After ranking: fan out to XAI + follow-up
    graph.add_edge("ranking", "xai")
    graph.add_edge("ranking", "follow_up")

    # Response waits for both XAI and follow-up
    graph.add_edge("xai", "response")
    graph.add_edge("follow_up", "response")

    # Exit
    graph.add_edge("response", END)

    return graph.compile()


# Compile once at module level — the compiled graph is stateless and
# reusable across requests (state is passed in per invocation).
pipeline = build_graph()


def run_pipeline(
    raw_query: str,
    user_id: str = "anonymous",
    top_k: int = 5,
) -> ResponseResult:
    """
    Run the full RetailMind AI pipeline end-to-end.

    Args:
        raw_query: The user's natural-language shopping query.
        user_id:   Profile identifier for memory-based personalization.
                   Defaults to "anonymous" (no personalization).
        top_k:     Number of products to retrieve and rank.

    Returns:
        A ``ResponseResult`` ready to be serialized and sent to the
        frontend.
    """

    initial_state: PipelineState = {
        "raw_query": raw_query,
        "user_id": user_id,
        "top_k": top_k,
    }

    # LangGraph's invoke() runs the full graph synchronously and
    # returns the final accumulated state dict.
    final_state = pipeline.invoke(initial_state)

    return final_state["response_result"]


# ── Demo / smoke test ────────────────────────────────────────────

def demo():
    """Quick end-to-end smoke test — run from project root with:
        python -m backend.orchestrator.graph
    """
    print("=" * 60)
    print("RetailMind AI — Full Pipeline Demo")
    print("=" * 60)

    query = "Best Samsung phone under 20000 with good camera"
    user_id = "camera_focused"

    print(f"\nQuery:   {query}")
    print(f"User ID: {user_id}")
    print("-" * 60)

    result = run_pipeline(raw_query=query, user_id=user_id, top_k=5)

    print(f"\n[Summary]\n{result.summary}\n")

    for i, product in enumerate(result.recommendations, start=1):
        print(f"  #{i}  {product.title}")
        print(f"      Brand: {product.brand}  |  Price: Rs.{product.price_inr}")
        print(f"      Why:   {product.explanation}")
        if product.key_factors:
            print(f"      Tags:  {', '.join(product.key_factors)}")
        print()

    if result.additional_information:
        print(f"[Additional info]\n{result.additional_information}\n")

    if result.follow_up_suggestions:
        print("[Follow-up suggestions]")
        for suggestion in result.follow_up_suggestions:
            print(f"   - {suggestion}")

    print("\n" + "=" * 60)
    print("Pipeline completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    demo()
