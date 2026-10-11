import chromadb

client = chromadb.PersistentClient(path="data/chromadb")
collection = client.get_collection("retail_products")

category_filter = {
    "main_category": {
        "$eq": "Cell_Phones_and_Accessories"
    }
}

brand_filter = {
    "$and": [
        category_filter,
        {
            "brand": {
                "$in": ["Samsung", "SAMSUNG"]
            }
        },
    ]
}

budget_filter = {
    "$and": [
        brand_filter,
        {
            "price_inr": {
                "$lte": 30000
            }
        },
    ]
}


def count_matches(where):
    result = collection.get(
        where=where,
        limit=500,
        include=[],
    )
    return len(result["ids"])


if __name__ == "__main__":
    print("Total products:", collection.count())

    print(
        "Phone category:",
        count_matches(category_filter),
    )

    print(
        "Samsung variants in phone category:",
        count_matches(brand_filter),
    )

    print(
        "Samsung variants under ₹30,000:",
        count_matches(budget_filter),
    )