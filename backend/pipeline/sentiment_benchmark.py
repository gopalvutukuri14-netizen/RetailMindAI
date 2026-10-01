from pathlib import Path
import time

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PRODUCTS_FILE = PROJECT_ROOT / "data" / "products_master.parquet"
REVIEWS_FILE = PROJECT_ROOT / "data" / "reviews_master.parquet"

OUTPUT_FILE = PROJECT_ROOT / "data" / "sentiment_benchmark_20k.parquet"

SAMPLE_SIZE = 20_000


# ============================================================
# CATEGORY-AWARE ASPECTS
# ============================================================

ASPECTS = {
    "Cell_Phones_and_Accessories": [
        "camera",
        "battery",
        "display",
        "performance",
        "charging",
        "software",
        "build_quality",
        "value",
    ],

    "Electronics": [
        "performance",
        "display",
        "sound_quality",
        "battery",
        "connectivity",
        "build_quality",
        "ease_of_use",
        "value",
    ],

    "Home_and_Kitchen": [
        "quality",
        "durability",
        "size",
        "ease_of_use",
        "material",
        "performance",
        "design",
        "value",
    ],

    "Clothing_Shoes_and_Jewelry": [
        "quality",
        "fit",
        "comfort",
        "material",
        "design",
        "durability",
        "appearance",
        "value",
    ],

    "Office_Products": [
        "quality",
        "durability",
        "ease_of_use",
        "performance",
        "design",
        "size",
        "value",
    ],

    "Sports_and_Outdoors": [
        "quality",
        "durability",
        "comfort",
        "size",
        "performance",
        "material",
        "ease_of_use",
        "value",
    ],
}


# ============================================================
# ASPECT KEYWORDS
# ============================================================

ASPECT_KEYWORDS = {
    "camera": [
        "camera", "photo", "photos", "picture", "pictures",
        "image", "images", "video", "zoom", "lens"
    ],

    "battery": [
        "battery", "battery life", "charge", "charging",
        "lasts", "power"
    ],

    "display": [
        "display", "screen", "resolution", "amoled", "lcd",
        "brightness", "touchscreen"
    ],

    "performance": [
        "performance", "fast", "slow", "speed", "processor",
        "lag", "laggy", "responsive"
    ],

    "charging": [
        "charging", "charger", "fast charge", "wireless charging"
    ],

    "software": [
        "software", "android", "ios", "update", "updates",
        "app", "apps", "interface"
    ],

    "build_quality": [
        "build", "built", "construction", "solid", "sturdy",
        "premium", "plastic", "metal"
    ],

    "sound_quality": [
        "sound", "audio", "music", "bass", "treble",
        "volume", "sound quality"
    ],

    "connectivity": [
        "bluetooth", "wifi", "wi-fi", "connection",
        "connectivity", "signal", "usb"
    ],

    "quality": [
        "quality", "good quality", "poor quality",
        "excellent quality"
    ],

    "durability": [
        "durable", "durability", "last", "lasting",
        "sturdy", "strong", "break", "broken"
    ],

    "size": [
        "size", "small", "large", "big", "tiny",
        "length", "width", "height"
    ],

    "ease_of_use": [
        "easy", "easier", "simple", "difficult",
        "hard to use", "easy to use", "setup"
    ],

    "material": [
        "material", "fabric", "leather", "cotton",
        "steel", "metal", "plastic", "wood"
    ],

    "design": [
        "design", "style", "stylish", "looks",
        "looking", "appearance"
    ],

    "value": [
        "value", "price", "worth", "money",
        "expensive", "cheap", "deal"
    ],

    "fit": [
        "fit", "fits", "fitting", "tight", "loose",
        "size", "comfortable"
    ],

    "comfort": [
        "comfortable", "comfort", "uncomfortable",
        "soft", "cushion"
    ],

    "appearance": [
        "appearance", "look", "looks", "color",
        "colour", "beautiful", "attractive"
    ],
}


# ============================================================
# HELPERS
# ============================================================

analyzer = SentimentIntensityAnalyzer()


def get_sentiment(text: str) -> tuple[float, str]:
    """
    Calculate VADER compound sentiment score and label.
    """

    if not isinstance(text, str) or not text.strip():
        return 0.0, "neutral"

    score = analyzer.polarity_scores(text)["compound"]

    if score >= 0.05:
        label = "positive"
    elif score <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    return score, label


def detect_aspects(text: str, category: str) -> list[str]:
    """
    Detect category-specific aspects using keyword matching.
    """

    if not isinstance(text, str):
        return []

    text_lower = text.lower()

    allowed_aspects = ASPECTS.get(category, [])

    detected = []

    for aspect in allowed_aspects:
        keywords = ASPECT_KEYWORDS.get(aspect, [])

        for keyword in keywords:
            if keyword in text_lower:
                detected.append(aspect)
                break

    return detected


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("RETAILMIND AI - 20K SENTIMENT BENCHMARK")
    print("=" * 70)

    start = time.perf_counter()

    # --------------------------------------------------------
    # LOAD PRODUCTS
    # --------------------------------------------------------

    print("\nLoading product categories...")

    products = pd.read_parquet(
        PRODUCTS_FILE,
        columns=[
            "parent_asin",
            "main_category",
        ],
    )

    print(f"Products loaded: {len(products):,}")

    # --------------------------------------------------------
    # LOAD SAMPLE REVIEWS
    # --------------------------------------------------------

    print("\nLoading review sample...")

    reviews = pd.read_parquet(
        REVIEWS_FILE,
        columns=[
            "parent_asin",
            "asin",
            "rating",
            "title",
            "text",
            "timestamp",
            "verified_purchase",
            "helpful_vote",
        ],
    )

    print(f"Total reviews available: {len(reviews):,}")

    # Deterministic sample
    reviews = reviews.head(SAMPLE_SIZE).copy()

    print(f"Benchmark reviews: {len(reviews):,}")

    # --------------------------------------------------------
    # JOIN CATEGORY
    # --------------------------------------------------------

    print("\nJoining product categories...")

    reviews = reviews.merge(
        products,
        on="parent_asin",
        how="left",
        validate="many_to_one",
    )

    missing_category = reviews["main_category"].isna().sum()

    print(f"Reviews without category: {missing_category:,}")

    # --------------------------------------------------------
    # COMBINE TITLE + REVIEW
    # --------------------------------------------------------

    reviews["review_text"] = (
        reviews["title"].fillna("").astype(str)
        + ". "
        + reviews["text"].fillna("").astype(str)
    ).str.strip()

    # --------------------------------------------------------
    # VADER
    # --------------------------------------------------------

    print("\nRunning VADER sentiment...")

    sentiment_scores = []
    sentiment_labels = []

    for text in reviews["review_text"]:
        score, label = get_sentiment(text)

        sentiment_scores.append(score)
        sentiment_labels.append(label)

    reviews["sentiment_score"] = sentiment_scores
    reviews["sentiment_label"] = sentiment_labels

    # --------------------------------------------------------
    # ASPECT DETECTION
    # --------------------------------------------------------

    print("Running category-aware aspect detection...")

    reviews["aspects"] = [
        detect_aspects(text, category)
        for text, category
        in zip(
            reviews["review_text"],
            reviews["main_category"],
        )
    ]

    reviews["aspect_count"] = reviews["aspects"].apply(len)

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    reviews.to_parquet(
        OUTPUT_FILE,
        index=False,
        engine="pyarrow",
    )

    elapsed = time.perf_counter() - start

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)

    print(f"Reviews processed       : {len(reviews):,}")
    print(f"Processing time         : {elapsed:.2f} seconds")
    print(f"Reviews / second        : {len(reviews) / elapsed:,.0f}")

    print("\nSentiment distribution:")
    print(reviews["sentiment_label"].value_counts())

    print("\nAverage sentiment score:")
    print(f"{reviews['sentiment_score'].mean():.4f}")

    print("\nReviews with detected aspects:")
    print(
        f"{(reviews['aspect_count'] > 0).sum():,}"
        f" / {len(reviews):,}"
    )

    print("\nAspect frequency:")

    aspect_counts = {}

    for aspects in reviews["aspects"]:
        for aspect in aspects:
            aspect_counts[aspect] = (
                aspect_counts.get(aspect, 0) + 1
            )

    for aspect, count in sorted(
        aspect_counts.items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        print(f"  {aspect:20s}: {count:,}")

    print("\nCategory distribution:")
    print(reviews["main_category"].value_counts())

    print("\nSample processed reviews:")
    print("-" * 70)

    print(
        reviews[
            [
                "parent_asin",
                "main_category",
                "rating",
                "sentiment_score",
                "sentiment_label",
                "aspects",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print("\nOutput:")
    print(OUTPUT_FILE)

    print("\n" + "=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()