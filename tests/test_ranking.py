"""
Test script for the Ranking Agent.

This test runs the complete flow:

User Query
    ↓
Query Understanding
    ↓
Retrieval
    ↓
Memory
    ↓
Ranking
    ↓
Ranked Products

It prints:
- product information
- similarity score
- specification match
- overall sentiment
- aspect alignment
- memory alignment
- final ranking score
- explanation/reasons
"""

from backend.Agents.query_understanding import QueryUnderstandingAgent
from backend.Agents.retrieval import RetrievalAgent
from backend.Agents.memory import MemoryAgent
from backend.Agents.ranking import RankingAgent


# ---------------------------------------------------------
# TEST CONFIGURATION
# ---------------------------------------------------------

USER_ID = "samsung_loyalist"

USER_QUERY = (
    "Samsung phone under ₹15,000 "
    "with good camera and long battery"
)


# ---------------------------------------------------------
# HELPER FUNCTION
# ---------------------------------------------------------

def format_score(score):
    """
    Safely format a score.

    If the score is None, return N/A.
    Otherwise return the score with 3 decimal places.
    """
    if score is None:
        return "N/A"

    return f"{score:.3f}"


# ---------------------------------------------------------
# MAIN TEST
# ---------------------------------------------------------

def main():

    print("Loading imports (this can take a while on first run)...")
    print()

    # -----------------------------------------------------
    # 1. QUERY UNDERSTANDING
    # -----------------------------------------------------

    print("=" * 70)
    print("USER QUERY")
    print("=" * 70)

    print(USER_QUERY)
    print()

    print("=" * 70)
    print("QUERY UNDERSTANDING")
    print("=" * 70)

    query_agent = QueryUnderstandingAgent()

    understood_query = query_agent.understand(USER_QUERY)

    print(f"Intent        : {understood_query.intent}")
    print(f"Category      : {understood_query.category}")
    print(f"Budget Min    : {understood_query.budget_min}")
    print(f"Budget Max    : {understood_query.budget_max}")

    print(
        f"Preferred Brand : "
        f"{understood_query.brand.preferred}"
    )

    print(
        f"Quality Tags    : "
        f"{understood_query.quality_tags}"
    )

    print(
        f"Hard Constraints: "
        f"{understood_query.hard_constraints}"
    )

    print()

    # -----------------------------------------------------
    # 2. RETRIEVAL
    # -----------------------------------------------------

    print("=" * 70)
    print("RETRIEVAL")
    print("=" * 70)

    retrieval_agent = RetrievalAgent()

    retrieval_result = retrieval_agent.retrieve(
        understood_query
    )

    print(
        f"Candidates retrieved: "
        f"{retrieval_result.total_candidates_returned}"
    )

    print(
        f"Query used for retrieval: "
        f"{retrieval_result.query_text_used}"
    )

    print(
        f"Hard filters applied: "
        f"{retrieval_result.hard_filters_applied}"
    )

    print()

    # -----------------------------------------------------
    # 3. MEMORY
    # -----------------------------------------------------

    print("=" * 70)
    print("MEMORY")
    print("=" * 70)

    memory_agent = MemoryAgent()

    profile = memory_agent.get_profile(USER_ID)

    if profile is None:
        print("No stored user profile found.")

    else:
        print(f"User ID              : {profile.user_id}")
        print(
            f"Preferred Brands     : "
            f"{profile.preferred_brands}"
        )
        print(
            f"Excluded Brands      : "
            f"{profile.excluded_brands}"
        )
        print(
            f"Typical Budget Min   : "
            f"{profile.typical_budget_min}"
        )
        print(
            f"Typical Budget Max   : "
            f"{profile.typical_budget_max}"
        )
        print(
            f"Recurring Quality Tags: "
            f"{profile.recurring_quality_tags}"
        )

    print()

    # -----------------------------------------------------
    # 4. RANKING
    # -----------------------------------------------------

    print("=" * 70)
    print("RANKING")
    print("=" * 70)

    ranking_agent = RankingAgent()

    ranking_result = ranking_agent.rank(
        query=understood_query,
        retrieval_result=retrieval_result,
        profile=profile,
    )

    print(
        f"Memory applied: "
        f"{ranking_result.memory_applied}"
    )

    print(
        f"Total ranked: "
        f"{ranking_result.total_ranked}"
    )

    print()

    # -----------------------------------------------------
    # 5. DISPLAY RESULTS
    # -----------------------------------------------------

    print("=" * 70)
    print("RANKING RESULTS")
    print("=" * 70)

    for index, product in enumerate(
        ranking_result.products,
        start=1
    ):

        print()
        print("-" * 70)

        print(
            f"{index}. {product.title}"
        )

        print("-" * 70)

        print(
            f"ASIN              : "
            f"{product.asin}"
        )

        print(
            f"Brand             : "
            f"{product.brand}"
        )

        if product.price_inr is not None:
            print(
                f"Price             : "
                f"₹{product.price_inr:.2f}"
            )
        else:
            print(
                "Price             : N/A"
            )

        # -------------------------------------------------
        # SCORE BREAKDOWN
        # -------------------------------------------------

        print(
            f"Similarity        : "
            f"{format_score(product.scores.similarity_score)}"
        )

        print(
            f"Spec Match        : "
            f"{format_score(product.scores.spec_match_score)}"
        )

        print(
            f"Sentiment         : "
            f"{format_score(product.scores.sentiment_score)}"
        )

        print(
            f"Aspect Alignment  : "
            f"{format_score(product.scores.aspect_alignment_score)}"
        )

        print(
            f"Memory Alignment  : "
            f"{format_score(product.scores.memory_alignment_score)}"
        )

        print(
            f"FINAL SCORE       : "
            f"{format_score(product.scores.final_score)}"
        )

        # -------------------------------------------------
        # REASONS
        # -------------------------------------------------

        print(
            f"Reasons           : "
            f"{product.match_reasons}"
        )

    print()
    print("=" * 70)
    print("RANKING TEST COMPLETED SUCCESSFULLY")
    print("=" * 70)


# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------

if __name__ == "__main__":
    main()