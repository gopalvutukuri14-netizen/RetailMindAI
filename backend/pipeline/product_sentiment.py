import pandas as pd
from pathlib import Path


DATA_DIR = Path("data")

REVIEWS_FILE = DATA_DIR / "reviews_sentiment.csv"
PRODUCTS_FILE = DATA_DIR / "products_clean.csv"
OUTPUT_FILE = DATA_DIR / "product_sentiment.csv"


def main():

    print("Loading sentiment reviews...")

    reviews = pd.read_csv(REVIEWS_FILE)

    print(f"Total reviews: {len(reviews)}")

    print("Aggregating sentiment by product...")

    product_sentiment = (
        reviews
        .groupby("asin")
        .agg(
            total_reviews=("review_id", "count"),
            average_rating=("rating", "mean"),
            average_sentiment_score=("sentiment_score", "mean"),
            positive_reviews=(
                "sentiment_label",
                lambda x: (x == "positive").sum()
            ),
            negative_reviews=(
                "sentiment_label",
                lambda x: (x == "negative").sum()
            ),
            neutral_reviews=(
                "sentiment_label",
                lambda x: (x == "neutral").sum()
            )
        )
        .reset_index()
    )

    # Calculate sentiment ratios

    product_sentiment["positive_ratio"] = (
        product_sentiment["positive_reviews"]
        / product_sentiment["total_reviews"]
    )

    product_sentiment["negative_ratio"] = (
        product_sentiment["negative_reviews"]
        / product_sentiment["total_reviews"]
    )

    product_sentiment["neutral_ratio"] = (
        product_sentiment["neutral_reviews"]
        / product_sentiment["total_reviews"]
    )

    # Round numerical values

    product_sentiment["average_rating"] = (
        product_sentiment["average_rating"].round(3)
    )

    product_sentiment["average_sentiment_score"] = (
        product_sentiment["average_sentiment_score"].round(4)
    )

    product_sentiment["positive_ratio"] = (
        product_sentiment["positive_ratio"].round(3)
    )

    product_sentiment["negative_ratio"] = (
        product_sentiment["negative_ratio"].round(3)
    )

    product_sentiment["neutral_ratio"] = (
        product_sentiment["neutral_ratio"].round(3)
    )

    print(f"Products with reviews: {len(product_sentiment)}")

    print("Saving product sentiment data...")

    product_sentiment.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(f"\nSaved file: {OUTPUT_FILE}")

    print("\nSample output:")

    print(product_sentiment.head())


if __name__ == "__main__":
    main()