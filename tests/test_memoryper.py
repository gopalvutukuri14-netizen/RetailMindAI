from backend.Agents.query_understanding import QueryUnderstandingAgent
from backend.Agents.retrieval import RetrievalAgent
from backend.Agents.memory import MemoryAgent
from backend.Agents.ranking import RankingAgent


def run_test(user_id):
    print("\n" + "=" * 80)
    print(f"TEST USER: {user_id}")
    print("=" * 80)

    # Current query intentionally does NOT mention a brand.
    query_text = "Good phone under ₹15,000 with a good camera"

    print(f"\nQuery: {query_text}")

    # 1. Understand current query
    qu = QueryUnderstandingAgent().understand(query_text)

    # 2. Retrieve products using ONLY the current query
    retrieved = RetrievalAgent().retrieve(qu, top_k=10)

    print(f"\nRetrieved candidates: {len(retrieved.products)}")

    # Show brands retrieved before memory/ranking
    print("\nBrands before ranking:")
    for product in retrieved.products:
        print(f"- {product.brand}: {product.title}")

    # 3. Load this user's long-term memory
    profile = MemoryAgent().get_profile(user_id)

    print(f"\nMemory:")
    print(f"Preferred brands: {profile.preferred_brands}")
    print(f"Excluded brands: {profile.excluded_brands}")
    print(f"Typical budget: ₹{profile.typical_budget_min} - ₹{profile.typical_budget_max}")
    print(f"Recurring quality tags: {profile.recurring_quality_tags}")

    # 4. Rank using current query + memory
    ranked = RankingAgent().rank(
        qu,
        retrieved,
        profile
    )

    # 5. Display ranking
    print("\nRANKED PRODUCTS:")

    for i, product in enumerate(ranked.products, 1):

        scores = product.scores

        print(f"\n{i}. {product.title}")
        print(f"   Brand             : {product.brand}")
        print(f"   Price             : ₹{product.price_inr}")

        print(
            f"   Similarity        : "
            f"{scores.similarity_score:.3f}"
            if scores.similarity_score is not None
            else "   Similarity        : N/A"
        )

        print(
            f"   Spec Match        : "
            f"{scores.spec_match_score:.3f}"
            if scores.spec_match_score is not None
            else "   Spec Match        : N/A"
        )

        print(
            f"   Sentiment         : "
            f"{scores.sentiment_score:.3f}"
            if scores.sentiment_score is not None
            else "   Sentiment         : N/A"
        )

        print(
            f"   Memory Alignment  : "
            f"{scores.memory_alignment_score:.3f}"
            if scores.memory_alignment_score is not None
            else "   Memory Alignment  : N/A"
        )

        print(f"   FINAL SCORE       : {scores.final_score:.3f}")

        if product.match_reasons:
            print(f"   Reasons           : {product.match_reasons}")


def main():

    print("Loading Ranking personalization test...")

    # Samsung-preferring user
    run_test("samsung_loyalist")

    # New user with no meaningful preferences
    run_test("new_user_42")


if __name__ == "__main__":
    main()