"""
Test script for the XAI Agent.

Flow:

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
XAI
    ↓
Explanations
"""

from backend.Agents.query_understanding import QueryUnderstandingAgent
from backend.Agents.retrieval import RetrievalAgent
from backend.Agents.memory import MemoryAgent
from backend.Agents.ranking import RankingAgent
from backend.Agents.xai import XAIAgent


# ---------------------------------------------------------
# TEST CONFIGURATION
# ---------------------------------------------------------

USER_ID = "samsung_loyalist"

USER_QUERY = (
    "Samsung phone under ₹15,000 "
    "with good camera and long battery"
)


# ---------------------------------------------------------
# HELPER
# ---------------------------------------------------------

def print_score(label, value):
    """Print a score safely."""
    if value is None:
        print(f"{label:<22}: N/A")
    else:
        print(f"{label:<22}: {value:.3f}")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("Loading imports (this can take a while on first run)...")
    print()

    # =====================================================
    # 1. QUERY UNDERSTANDING
    # =====================================================

    print("=" * 70)
    print("USER QUERY")
    print("=" * 70)

    print(USER_QUERY)
    print()

    print("=" * 70)
    print("QUERY UNDERSTANDING")
    print("=" * 70)

    query_agent = QueryUnderstandingAgent()

    # IMPORTANT:
    # Your existing QueryUnderstandingAgent uses understand(),
    # not parse().
    understood_query = query_agent.understand(USER_QUERY)

    print(
        f"Intent            : "
        f"{understood_query.intent}"
    )

    print(
        f"Category          : "
        f"{understood_query.category}"
    )

    print(
        f"Budget Min        : "
        f"{understood_query.budget_min}"
    )

    print(
        f"Budget Max        : "
        f"{understood_query.budget_max}"
    )

    print(
        f"Preferred Brand   : "
        f"{understood_query.brand.preferred}"
    )

    print(
        f"Excluded Brand    : "
        f"{understood_query.brand.excluded}"
    )

    print(
        f"Quality Tags      : "
        f"{understood_query.quality_tags}"
    )

    print(
        f"Hard Constraints  : "
        f"{understood_query.hard_constraints}"
    )

    print()

    # =====================================================
    # 2. RETRIEVAL
    # =====================================================

    print("=" * 70)
    print("RETRIEVAL")
    print("=" * 70)

    retrieval_agent = RetrievalAgent()

    retrieval_result = retrieval_agent.retrieve(
        understood_query
    )

    print(
        f"Candidates retrieved : "
        f"{retrieval_result.total_candidates_returned}"
    )

    print(
        f"Query used            : "
        f"{retrieval_result.query_text_used}"
    )

    print(
        f"Hard filters applied  : "
        f"{retrieval_result.hard_filters_applied}"
    )

    print()

    # =====================================================
    # 3. MEMORY
    # =====================================================

    print("=" * 70)
    print("MEMORY")
    print("=" * 70)

    memory_agent = MemoryAgent()

    profile = memory_agent.get_profile(USER_ID)

    if profile is None:
        print("No stored profile found.")

    else:
        print(
            f"User ID              : "
            f"{profile.user_id}"
        )

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
            f"Recurring Quality    : "
            f"{profile.recurring_quality_tags}"
        )

    print()

    # =====================================================
    # 4. RANKING
    # =====================================================

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
        f"Memory applied : "
        f"{ranking_result.memory_applied}"
    )

    print(
        f"Total ranked   : "
        f"{ranking_result.total_ranked}"
    )

    print()

    # =====================================================
    # 5. RANKING SUMMARY
    # =====================================================

    print("=" * 70)
    print("RANKED PRODUCTS")
    print("=" * 70)

    for index, product in enumerate(
        ranking_result.products,
        start=1
    ):

        print()
        print(
            f"{index}. {product.title}"
        )

        print(
            f"   ASIN          : "
            f"{product.asin}"
        )

        print(
            f"   Brand         : "
            f"{product.brand}"
        )

        if product.price_inr is not None:
            print(
                f"   Price         : "
                f"₹{product.price_inr:.2f}"
            )
        else:
            print(
                "   Price         : N/A"
            )

        print_score(
            "   Similarity",
            product.scores.similarity_score
        )

        print_score(
            "   Spec Match",
            product.scores.spec_match_score
        )

        print_score(
            "   Sentiment",
            product.scores.sentiment_score
        )

        print_score(
            "   Aspect Alignment",
            product.scores.aspect_alignment_score
        )

        print_score(
            "   Memory Alignment",
            product.scores.memory_alignment_score
        )

        print_score(
            "   Final Score",
            product.scores.final_score
        )

        print(
            f"   Reasons       : "
            f"{product.match_reasons}"
        )

    print()

    # =====================================================
    # 6. XAI
    # =====================================================

    print("=" * 70)
    print("XAI / EXPLAINABILITY")
    print("=" * 70)

    xai_agent = XAIAgent()

    xai_result = xai_agent.explain(
        query=understood_query,
        ranking_result=ranking_result,
    )

    # =====================================================
    # 7. XAI QUERY SUMMARY
    # =====================================================

    print()
    print("QUERY SUMMARY")
    print("-" * 70)

    print(xai_result.query_summary)

    # =====================================================
    # 8. XAI PRODUCT EXPLANATIONS
    # =====================================================

    print()
    print("=" * 70)
    print("PRODUCT EXPLANATIONS")
    print("=" * 70)

    for index, explanation in enumerate(
        xai_result.explanations,
        start=1
    ):

        print()
        print(
            f"{index}. ASIN: "
            f"{explanation.asin}"
        )

        print(
            f"   Explanation:"
        )

        print(
            f"   {explanation.explanation}"
        )

        print(
            f"   Key Factors:"
        )

        for factor in explanation.key_factors:
            print(
                f"      • {factor}"
            )

    # =====================================================
    # 9. VALIDATION
    # =====================================================

    print()
    print("=" * 70)
    print("XAI VALIDATION")
    print("=" * 70)

    expected_count = len(ranking_result.products)
    actual_count = len(xai_result.explanations)

    print(
        f"Ranked products     : {expected_count}"
    )

    print(
        f"XAI explanations     : {actual_count}"
    )

    if expected_count == actual_count:
        print(
            "Explanation count    : PASS"
        )
    else:
        print(
            "Explanation count    : FAIL"
        )

    ranking_asins = [
        product.asin
        for product in ranking_result.products
    ]

    xai_asins = [
        explanation.asin
        for explanation in xai_result.explanations
    ]

    if ranking_asins == xai_asins:
        print(
            "Product order        : PASS"
        )
    else:
        print(
            "Product order        : FAIL"
        )

    print()
    print("=" * 70)
    print("XAI TEST COMPLETED")
    print("=" * 70)


# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------

if __name__ == "__main__":
    main()