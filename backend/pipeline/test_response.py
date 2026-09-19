from backend.Agents.query_understanding import QueryUnderstandingAgent
from backend.Agents.retrieval import RetrievalAgent
from backend.Agents.memory import MemoryAgent
from backend.Agents.ranking import RankingAgent
from backend.Agents.xai import XAIAgent
from backend.Agents.follow_up import FollowUpAgent
from backend.Agents.response import ResponseAgent


def main():

    # 1. Understand the user's request
    qu = QueryUnderstandingAgent().understand(
        "Samsung phone under ₹15,000 with good camera and long battery"
    )

    # 2. Retrieve relevant products
    retrieved = RetrievalAgent().retrieve(
        qu,
        top_k=5
    )

    # 3. Load long-term user preferences
    profile = MemoryAgent().get_profile(
        "samsung_loyalist"
    )

    # 4. Rank the products
    ranked = RankingAgent().rank(
        qu,
        retrieved,
        profile
    )

    # 5. Generate explanations
    xai_result = XAIAgent().explain(
        qu,
        ranked
    )

    # 6. Generate follow-up suggestions
    followup_result = FollowUpAgent().suggest(
        qu,
        ranked
    )

    # 7. Generate final structured response
    response_result = ResponseAgent().generate(
        qu,
        ranked,
        xai_result,
        followup_result
    )

    # Display the final response
    print("\n===== FINAL RESPONSE =====")

    print("\nSUMMARY:")
    print(response_result.summary)

    print("\nRECOMMENDATIONS:")

    for i, product in enumerate(
        response_result.recommendations,
        start=1
    ):
        print(f"\n{i}. {product.title}")
        print(f"   ASIN: {product.asin}")
        print(f"   Brand: {product.brand}")
        print(f"   Price: ₹{product.price_inr}")
        print(f"   Why: {product.explanation}")
        print(f"   Factors: {product.key_factors}")

    print("\nADDITIONAL INFORMATION:")
    print(response_result.additional_information)

    print("\nFOLLOW-UP SUGGESTIONS:")

    for suggestion in response_result.follow_up_suggestions:
        print(f"- {suggestion}")


if __name__ == "__main__":
    main()