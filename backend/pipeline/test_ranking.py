from backend.Agents.query_understanding import QueryUnderstandingAgent
from backend.Agents.retrieval import RetrievalAgent
from backend.Agents.memory import MemoryAgent
from backend.Agents.ranking import RankingAgent


print("Loading imports (this can take a while on first run)...")


def main():

    # ---------------------------------------------------------
    # 1. User query
    # ---------------------------------------------------------
    query_text = "Samsung phone under ₹15,000 with good camera and long battery"

    print("\nUSER QUERY:")
    print(query_text)

    # ---------------------------------------------------------
    # 2. Query Understanding
    # ---------------------------------------------------------
    qu = QueryUnderstandingAgent().understand(query_text)

    # ---------------------------------------------------------
    # 3. Retrieval
    # ---------------------------------------------------------
    retrieved = RetrievalAgent().retrieve(qu, top_k=5)

    # ---------------------------------------------------------
    # 4. Memory
    # ---------------------------------------------------------
    profile = MemoryAgent().get_profile("samsung_loyalist")

    # ---------------------------------------------------------
    # 5. Ranking
    # ---------------------------------------------------------
    ranked = RankingAgent().rank(
        qu,
        retrieved,
        profile
    )

    print("\n" + "=" * 70)
    print("RANKING RESULTS")
    print("=" * 70)

    print(f"\nMemory applied: {ranked.memory_applied}")
    print(f"Total ranked: {ranked.total_ranked}")

    # ---------------------------------------------------------
    # 6. Display individual ranking scores
    # ---------------------------------------------------------
    for i, product in enumerate(ranked.products, 1):

        scores = product.scores

        print("\n" + "-" * 70)
        print(f"{i}. {product.title}")
        print("-" * 70)

        print(f"Brand             : {product.brand}")
        print(f"Price             : ₹{product.price_inr}")

        print(
            f"Similarity        : "
            f"{scores.similarity_score:.3f}"
            if scores.similarity_score is not None
            else "Similarity        : N/A"
        )

        print(
            f"Spec Match        : "
            f"{scores.spec_match_score:.3f}"
            if scores.spec_match_score is not None
            else "Spec Match        : N/A"
        )

        print(
            f"Sentiment         : "
            f"{scores.sentiment_score:.3f}"
            if scores.sentiment_score is not None
            else "Sentiment         : N/A"
        )

        print(
            f"Memory Alignment  : "
            f"{scores.memory_alignment_score:.3f}"
            if scores.memory_alignment_score is not None
            else "Memory Alignment  : N/A"
        )

        print(f"FINAL SCORE       : {scores.final_score:.3f}")

        print(f"Reasons           : {product.match_reasons}")


if __name__ == "__main__":
    main()