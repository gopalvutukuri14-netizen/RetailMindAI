from backend.orchestrator.graph import run_pipeline

TEST_CASES = [
    ("Phones", "Samsung phone under ₹30000 with 8GB RAM"),
    ("Electronics", "Wireless headphones for gaming under ₹5000"),
    ("Home & Kitchen", "Non-stick cookware set under ₹10000"),
    ("Clothing", "Durable jacket under ₹5000"),
    ("Office Products", "Comfortable ergonomic office chair"),
    ("Sports & Outdoors", "Durable running shoes"),
]


def main():
    failures = []

    for category, query in TEST_CASES:
        print("\n" + "=" * 75)
        print(f"CATEGORY: {category}")
        print(f"QUERY: {query}")

        try:
            result = run_pipeline(
                raw_query=query,
                top_k=5,
            )

            recommendations = result.recommendations
            print(f"SUMMARY: {result.summary}")
            print(f"PRODUCT COUNT: {len(recommendations)}")

            if not recommendations:
                failures.append((category, "No recommendations"))

            for index, product in enumerate(recommendations, 1):
                print(
                    f"{index}. {product.title} "
                    f"| Price: {product.price_inr}"
                )

        except Exception as exc:
            failures.append((category, repr(exc)))
            print(f"ERROR: {exc}")

    print("\n" + "=" * 75)
    print("FULL PIPELINE EVALUATION SUMMARY")

    if failures:
        for category, error in failures:
            print(f"FAIL: {category} - {error}")
    else:
        print("All six queries completed with recommendations.")

    print(
        "\nNote: successful execution does not guarantee "
        "that every recommendation is relevant."
    )


if __name__ == "__main__":
    main()
