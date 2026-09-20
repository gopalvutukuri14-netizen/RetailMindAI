"""
LangGraph StateGraph wiring for RetailMind AI.

Builds the full agent pipeline as a directed graph with conditional
routing based on query intent:

    START
      |
      v
    query_understanding
      |
      v
    router ──────────────────────────────────────────
      |                    |                         |
      | "product_pipeline" | "context_response"      | "general_response"
      v                    v                         v
    retrieval + memory   context_response_node     general_response_node
      |                    |                         |
      v                   END                       END
    ranking
      |
    xai + follow_up
      |
      v
    response
      |
     END

``run_pipeline()`` is the single entry point used by the API.
"""

from langgraph.graph import StateGraph, START, END

from .state import PipelineState
from .nodes import (
    query_understanding_node,
    router_node,
    retrieval_node,
    memory_node,
    ranking_node,
    xai_node,
    followup_node,
    response_node,
    general_response_node,
    context_response_node,
    out_of_scope_node,
)

from backend.Agents.response import ResponseResult


def _route_after_router(state: PipelineState) -> str:
    """Return the route string set by router_node."""
    return state["route"]


def build_graph() -> StateGraph:
    """
    Construct and compile the RetailMind AI pipeline graph.

    Returns a compiled LangGraph ``CompiledGraph`` that accepts a
    ``PipelineState`` dict and executes all nodes in dependency order.
    """

    graph = StateGraph(PipelineState)

    # ── Register nodes ───────────────────────────────────────────
    graph.add_node("query_understanding", query_understanding_node)
    graph.add_node("router", router_node)
    # Product pipeline nodes
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("memory", memory_node)
    graph.add_node("ranking", ranking_node)
    graph.add_node("xai", xai_node)
    graph.add_node("follow_up", followup_node)
    graph.add_node("response", response_node)
    # Shortcut nodes
    graph.add_node("general_response", general_response_node)
    graph.add_node("context_response", context_response_node)
    graph.add_node("out_of_scope", out_of_scope_node)

    # ── Wire edges ───────────────────────────────────────────────
    # Entry point
    graph.add_edge(START, "query_understanding")
    graph.add_edge("query_understanding", "router")

    # Conditional branching after router.
    # For product_pipeline, we route to "retrieval" — memory also
    # needs to run in parallel, so we add it as a second conditional
    # target for the same route.
    def _route_to_list(state: PipelineState) -> list[str]:
        """Return list of next nodes based on route."""
        route = state["route"]
        if route == "product_pipeline":
            return ["retrieval", "memory"]
        elif route == "context_response":
            return ["context_response"]
        elif route == "out_of_scope":
            return ["out_of_scope"]
        else:
            return ["general_response"]

    graph.add_conditional_edges(
        "router",
        _route_to_list,
        ["retrieval", "memory", "context_response", "general_response", "out_of_scope"],
    )

    # Product pipeline: ranking waits for both retrieval and memory
    graph.add_edge("retrieval", "ranking")
    graph.add_edge("memory", "ranking")

    # After ranking: fan out to XAI + follow-up
    graph.add_edge("ranking", "xai")
    graph.add_edge("ranking", "follow_up")

    # Response waits for both XAI and follow-up
    graph.add_edge("xai", "response")
    graph.add_edge("follow_up", "response")

    # All terminal nodes → END
    graph.add_edge("response", END)
    graph.add_edge("general_response", END)
    graph.add_edge("context_response", END)
    graph.add_edge("out_of_scope", END)

    return graph.compile()


# Compile once at module level — the compiled graph is stateless and
# reusable across requests (state is passed in per invocation).
pipeline = build_graph()


def run_pipeline(
    raw_query: str,
    user_id: str = "anonymous",
    top_k: int = 5,
    previous_products: list[dict] | None = None,
) -> ResponseResult:
    """
    Run the full RetailMind AI pipeline end-to-end.

    Args:
        raw_query:          The user's natural-language shopping query.
        user_id:            Profile identifier for memory-based personalization.
                            Defaults to "anonymous" (no personalization).
        top_k:              Number of products to retrieve and rank.
        previous_products:  Products from the last recommendation (if any),
                            used for follow-up/comparison queries.

    Returns:
        A ``ResponseResult`` ready to be serialized and sent to the
        frontend.
    """

    initial_state: PipelineState = {
        "raw_query": raw_query,
        "user_id": user_id,
        "top_k": top_k,
    }

    if previous_products:
        initial_state["previous_products"] = previous_products

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
    print("RetailMind AI -- Full Pipeline Demo")
    print("=" * 60)

    # Test 1: Normal product query
    print("\n--- Test 1: Product recommendation ---")
    query = "Best Samsung phone under 20000 with good camera"
    result = run_pipeline(raw_query=query, user_id="camera_focused", top_k=3)
    print(f"Query: {query}")
    print(f"Summary: {result.summary}")
    print(f"Products: {len(result.recommendations)}")
    for p in result.recommendations:
        print(f"  - {p.title} (Rs.{p.price_inr})")

    # Test 2: General question
    print("\n--- Test 2: General question (bye) ---")
    query2 = "bye"
    result2 = run_pipeline(raw_query=query2)
    print(f"Query: {query2}")
    print(f"Response: {result2.summary}")
    print(f"Products: {len(result2.recommendations)} (should be 0)")

    # Test 3: Comparison with context
    print("\n--- Test 3: Comparison with previous products ---")
    prev = [p.model_dump() for p in result.recommendations[:2]]
    query3 = "Compare the top 2 options"
    result3 = run_pipeline(raw_query=query3, previous_products=prev)
    print(f"Query: {query3}")
    print(f"Summary: {result3.summary}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    demo()
