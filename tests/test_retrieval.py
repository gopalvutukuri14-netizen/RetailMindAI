from backend.pipeline.retrieval import ProductRetriever


def main():

    print("Starting retrieval test...\n")

    # Initialize retriever
    retriever = ProductRetriever()

    # Test query
    query = (
        "Suggest a smartphone with good camera "
        "and long battery life"
    )

    print(f"\nQuery: {query}")
    print("\nSearching...\n")

    # Retrieve products
    results = retriever.search(
        query=query,
        top_k=5
    )

    print("=" * 70)
    print("TOP RETRIEVED PRODUCTS")
    print("=" * 70)

    for index, product in enumerate(results, start=1):

        metadata = product["metadata"]

        print(f"\n{index}. {metadata.get('title', 'Unknown')}")

        print(f"ASIN: {product['asin']}")

        print(
            f"Brand: "
            f"{metadata.get('brand', 'N/A')}"
        )

        print(
            f"Price: "
            f"{metadata.get('price_inr', 'N/A')}"
        )

        print(
            f"Rating: "
            f"{metadata.get('average_rating', 'N/A')}"
        )

        print(
            f"Sentiment Score: "
            f"{metadata.get('average_sentiment_score', 'N/A')}"
        )

        print(
            f"Distance: "
            f"{product['distance']:.4f}"
        )

        print("-" * 70)


if __name__ == "__main__":
    main()