
from backend.Agents.query_understanding.agent import (
    QueryUnderstandingAgent,
)
from backend.Agents.retrieval.agent import RetrievalAgent
from backend.pipeline.retrieval import ProductRetriever


TEST_QUERIES = [
    (
        "Cell Phones & Accessories",
        "Cell_Phones_and_Accessories",
        "Samsung phone under ₹30000",
        ["phone", "smartphone", "galaxy"],
    ),
    (
        "Electronics",
        "Electronics",
        "wireless headphones for gaming",
        ["headphone", "headset", "earbud", "earphone"],
    ),
    (
        "Home & Kitchen",
        "Home_and_Kitchen",
        "non-stick cookware set",
        ["cookware", "pan", "pot", "kitchen"],
    ),
    (
        "Clothing, Shoes & Jewelry",
        "Clothing_Shoes_and_Jewelry",
        "durable jacket",
        ["jacket", "coat", "outerwear"],
    ),
    (
        "Office Products",
        "Office_Products",
        "comfortable office chair",
        ["chair", "office seating"],
    ),
    (
        "Sports & Outdoors",
        "Sports_and_Outdoors",
        "durable running shoes",
        ["running shoe", "trail shoe", "athletic shoe"],
    ),
]


def main():
    print("=" * 80)
    print("RETAILMIND AI - SIX-CATEGORY RETRIEVAL VALIDATION")
    print("=" * 80)

    query_agent = QueryUnderstandingAgent()
    base_retriever = ProductRetriever()
    retrieval_agent = RetrievalAgent(retriever=base_retriever)

    passed = 0
    failed = 0

    for (
        display_category,
        expected_category,
        query_text,
        relevant_keywords,
    ) in TEST_QUERIES:

        print(f"\n{'-' * 80}")
        print(f"Expected category: {display_category}")
        print(f"Query: {query_text}")

        try:
            structured_query = query_agent.understand(query_text)

            actual_category = (
                structured_query.category.value
                if structured_query.category is not None
                else None
            )

            print(f"Detected category: {actual_category}")

            if actual_category != expected_category:
                print("RESULT: FAIL - incorrect category detection")
                failed += 1
                continue

            result = retrieval_agent.retrieve(
                query=structured_query,
                top_k=5,
            )

            if not result.products:
                print("RESULT: FAIL - no candidates returned")
                failed += 1
                continue

            # Fetch the stored metadata for the returned product IDs.
            ids = [product.asin for product in result.products]

            stored = base_retriever.collection.get(
                ids=ids,
                include=["metadatas"],
            )

            metadata_by_id = dict(
                zip(stored["ids"], stored["metadatas"])
            )

            invalid_records = []
            wrong_category_records = []
            relevant_count = 0

            print(f"Candidates returned: {len(result.products)}")

            for i, product in enumerate(result.products, 1):
                metadata = metadata_by_id.get(product.asin, {})
                stored_category = metadata.get("main_category")

                if not product.asin or not product.title:
                    invalid_records.append(product.asin)

                if stored_category != expected_category:
                    wrong_category_records.append(
                        (product.title, stored_category)
                    )

                title_lower = product.title.casefold()
                is_relevant = any(
                    keyword in title_lower
                    for keyword in relevant_keywords
                )

                if is_relevant:
                    relevant_count += 1

                print(
                    f"{i}. {product.title}\n"
                    f"   Brand={product.brand} | "
                    f"Price INR={product.price_inr} | "
                    f"Stored category={stored_category} | "
                    f"Product-type match={is_relevant}"
                )

            errors = []

            if invalid_records:
                errors.append("invalid product records")

            if wrong_category_records:
                errors.append("products from the wrong category")

            if errors:
                print("RESULT: FAIL - " + ", ".join(errors))
                failed += 1
            else:
                print(
                    f"Product-type keyword matches: "
                    f"{relevant_count}/{len(result.products)}"
                )
                print("RESULT: PASS - category and record checks passed")
                passed += 1

                if relevant_count == 0:
                    print(
                        "WARNING: no title matched the expected "
                        "product-type keywords"
                    )

        except Exception as exc:
            print(f"RESULT: ERROR - {type(exc).__name__}: {exc}")
            failed += 1

    print(f"\n{'=' * 80}")
    print(f"Category checks passed: {passed}/6")
    print(f"Category checks failed: {failed}/6")
    print("=" * 80)


if __name__ == "__main__":
    main()
