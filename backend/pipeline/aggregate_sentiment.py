import pandas as pd
import ast
import os


# ============================================================
# CONFIG
# ============================================================

REVIEWS_SENTIMENT_PATH = "data/reviews_sentiment.parquet"
PRODUCTS_PATH = "data/products_master.parquet"
OUTPUT_PATH = "data/product_sentiment.parquet"


# ============================================================
# HELPERS
# ============================================================

def parse_aspect_sentiments(value):
    """
    Convert aspect_sentiments into a Python dictionary.

    Handles dictionaries and string representations safely.
    """

    if isinstance(value, dict):
        return value

    if pd.isna(value):
        return {}

    if isinstance(value, str):

        try:
            parsed = ast.literal_eval(value)

            if isinstance(parsed, dict):
                return parsed

        except (ValueError, SyntaxError):
            return {}

    return {}


# ============================================================
# START
# ============================================================

print("=" * 70)
print("RETAILMIND AI - PRODUCT SENTIMENT AGGREGATION")
print("=" * 70)


# ============================================================
# LOAD REVIEWS
# ============================================================

print("\nLoading review sentiment data...")

reviews = pd.read_parquet(
    REVIEWS_SENTIMENT_PATH
)

print(
    f"Reviews loaded: {len(reviews):,}"
)


# ============================================================
# VALIDATION
# ============================================================

required_columns = [
    "parent_asin",
    "rating",
    "main_category",
    "sentiment_score",
    "sentiment_label",
    "aspect_sentiments",
]

missing = [
    col
    for col in required_columns
    if col not in reviews.columns
]

if missing:

    raise ValueError(
        f"Missing columns: {missing}"
    )


# ============================================================
# BASIC PRODUCT AGGREGATION
# ============================================================

print("\nCalculating product-level statistics...")

product_stats = (
    reviews
    .groupby("parent_asin")
    .agg(
        review_count=(
            "parent_asin",
            "size"
        ),

        average_rating=(
            "rating",
            "mean"
        ),

        average_sentiment=(
            "sentiment_score",
            "mean"
        ),

        sentiment_std=(
            "sentiment_score",
            "std"
        ),

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
        ),
    )
    .reset_index()
)


# ============================================================
# RATIOS
# ============================================================

product_stats["positive_ratio"] = (
    product_stats["positive_reviews"]
    / product_stats["review_count"]
)

product_stats["negative_ratio"] = (
    product_stats["negative_reviews"]
    / product_stats["review_count"]
)

product_stats["neutral_ratio"] = (
    product_stats["neutral_reviews"]
    / product_stats["review_count"]
)


# ============================================================
# ASPECT SENTIMENT
# ============================================================

print("\nCalculating aspect-level sentiment...")

aspect_values = {}

for parent_asin, aspect_dicts in (
    reviews
    .groupby("parent_asin")["aspect_sentiments"]
):

    totals = {}
    counts = {}

    for value in aspect_dicts:

        parsed = parse_aspect_sentiments(value)

        for aspect, score in parsed.items():

            if not isinstance(score, (int, float)):
                continue

            totals[aspect] = (
                totals.get(aspect, 0.0)
                + float(score)
            )

            counts[aspect] = (
                counts.get(aspect, 0)
                + 1
            )

    aspect_values[parent_asin] = {
        aspect: round(
            totals[aspect] / counts[aspect],
            4
        )
        for aspect in totals
        if counts[aspect] > 0
    }


# Convert dictionary to dataframe

aspect_df = pd.DataFrame(
    [
        {
            "parent_asin": parent_asin,
            **values
        }
        for parent_asin, values
        in aspect_values.items()
    ]
)


# ============================================================
# MERGE ASPECT FEATURES
# ============================================================

unique_aspects = set()

for values in aspect_values.values():
    for aspect in values:
        unique_aspects.add(aspect)

print(
    f"Unique aspects found: {len(unique_aspects)}"
)

if not aspect_df.empty:

    product_stats = product_stats.merge(
        aspect_df,
        on="parent_asin",
        how="left"
    )


# ============================================================
# LOAD PRODUCT DATA
# ============================================================

print("\nLoading product metadata...")

products = pd.read_parquet(
    PRODUCTS_PATH
)

print(
    f"Products loaded: {len(products):,}"
)


# Keep only useful identification fields.

product_identity = products[
    [
        "parent_asin",
        "main_category",
        "title",
        "brand",
    ]
].drop_duplicates(
    "parent_asin"
)


# ============================================================
# MERGE WITH PRODUCT IDENTITY
# ============================================================

product_sentiment = product_identity.merge(
    product_stats,
    on="parent_asin",
    how="left"
)


# ============================================================
# PRODUCTS WITHOUT REVIEWS
# ============================================================

product_sentiment["review_count"] = (
    product_sentiment["review_count"]
    .fillna(0)
    .astype(int)
)

reviewless_count = (
    product_sentiment["review_count"] == 0
).sum()

print(
    f"\nProducts without reviews: "
    f"{reviewless_count:,}"
)


# ============================================================
# ROUND NUMERIC FEATURES
# ============================================================

numeric_columns = [
    "average_rating",
    "average_sentiment",
    "sentiment_std",
    "positive_ratio",
    "negative_ratio",
    "neutral_ratio",
]

for column in numeric_columns:

    if column in product_sentiment.columns:

        product_sentiment[column] = (
            product_sentiment[column]
            .round(4)
        )


# ============================================================
# REVIEW CONFIDENCE
# ============================================================

"""
A product with 1 review should not have the same confidence
as a product with 100 reviews.

This is not a ranking score. It is simply a confidence signal.
"""

product_sentiment["review_confidence"] = (
    product_sentiment["review_count"]
    / (
        product_sentiment["review_count"]
        + 10
    )
).round(4)


# ============================================================
# VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("VALIDATION")
print("=" * 70)


print(
    f"Products in sentiment table: "
    f"{len(product_sentiment):,}"
)

print(
    f"Products in master dataset: "
    f"{len(products):,}"
)


# Every parent_asin should be unique.

duplicate_count = (
    product_sentiment["parent_asin"]
    .duplicated()
    .sum()
)

print(
    f"Duplicate parent_asin: "
    f"{duplicate_count}"
)

if duplicate_count != 0:

    raise ValueError(
        "Duplicate parent_asin values found."
    )


# Product coverage

reviewed_products = (
    product_stats["parent_asin"]
    .nunique()
)

print(
    f"Products with reviews: "
    f"{reviewed_products:,}"
)


# ============================================================
# ASPECT SUMMARY
# ============================================================

aspect_columns = [
    column
    for column in product_sentiment.columns
    if column in {
        "camera",
        "battery",
        "display",
        "performance",
        "charging",
        "software",
        "build_quality",
        "value",
        "sound_quality",
        "connectivity",
        "ease_of_use",
        "quality",
        "durability",
        "size",
        "material",
        "design",
        "fit",
        "comfort",
        "appearance",
    }
]

print(
    f"\nAspect sentiment columns: "
    f"{len(aspect_columns)}"
)

for column in sorted(aspect_columns):

    non_null = (
        product_sentiment[column]
        .notna()
        .sum()
    )

    print(
        f"  {column:20s}: "
        f"{non_null:,} products"
    )


# ============================================================
# SAMPLE
# ============================================================

print("\nSample product sentiment:")

display_columns = [
    "parent_asin",
    "main_category",
    "title",
    "review_count",
    "average_rating",
    "average_sentiment",
    "positive_ratio",
    "negative_ratio",
    "review_confidence",
]

display_columns = [
    column
    for column in display_columns
    if column in product_sentiment.columns
]

print(
    product_sentiment[
        display_columns
    ]
    .head(15)
    .to_string(index=False)
)


# ============================================================
# SAVE
# ============================================================

print("\nSaving product sentiment...")

product_sentiment.to_parquet(
    OUTPUT_PATH,
    index=False
)

print(
    f"Saved: {OUTPUT_PATH}"
)


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 70)
print("PRODUCT SENTIMENT AGGREGATION COMPLETE")
print("=" * 70)

print(
    f"Final products: "
    f"{len(product_sentiment):,}"
)

print(
    f"Output: {OUTPUT_PATH}"
)

print(
    "\nNext step:"
)

print(
    "Generate BGE-M3 embeddings for the "
    "250K product embedding_text records."
)