from backend.Agents.query_understanding.agent import (
    QueryUnderstandingAgent,
)
from backend.Agents.retrieval.agent import RetrievalAgent


def main():
    print("Initializing Query Understanding Agent...")
    query_agent = QueryUnderstandingAgent()

    print("Initializing Retrieval Agent...")
    retrieval_agent = RetrievalAgent()

    query_text = (
        "Samsung phone under ₹30000 "
        "with 8GB RAM and a good camera"
    )

    print(f"\nQuery: {query_text}")

    structured_query = query_agent.understand(query_text)

    print("\nStructured query:")
    print(structured_query.model_dump_json(indent=2))

    print("\nRetrieving products...")
    result = retrieval_agent.retrieve(
        query=structured_query,
        top_k=10,
    )

    print("\nApplied filters:")
    print(result.hard_filters_applied)

    print(f"\nCandidates returned: {result.total_candidates_returned}")

    for index, product in enumerate(result.products, start=1):
        print(f"\n{index}. {product.title}")
        print(f"   Product ID: {product.asin}")
        print(f"   Brand: {product.brand}")
        print(f"   Price INR: {product.price_inr}")
        print(f"   Category: {structured_query.category}")
        print(f"   Distance: {product.distance}")
        print(f"   Average sentiment: {product.average_sentiment_score}")
        print(f"   RAM match: {product.meets_ram}")

    if not result.products:
        print("\nNo candidates returned. Check the filters and category values.")
    else:
        print("\nRetrieval integration test completed.")


if __name__ == "__main__":
    main()