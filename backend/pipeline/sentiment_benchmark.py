import time
import re
from collections import Counter, defaultdict

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


# ============================================================
# CONFIG
# ============================================================

PRODUCTS_PATH = "data/products_master.parquet"
REVIEWS_PATH = "data/reviews_master.parquet"
OUTPUT_PATH = "data/sentiment_benchmark_20k_balanced.parquet"

SAMPLE_SIZE = 20_000
RANDOM_STATE = 42


# ============================================================
# CATEGORY-SPECIFIC ASPECTS
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
        "camera",
        "cameras",
        "photo",
        "photos",
        "picture",
        "pictures",
        "photography",
        "video quality",
    ],

    "battery": [
        "battery",
        "battery life",
        "backup",
        "charge lasts",
    ],

    "display": [
        "display",
        "screen",
        "screens",
        "resolution",
        "brightness",
        "touchscreen",
        "touch screen",
    ],

    "performance": [
        "performance",
        "speed",
        "fast",
        "slow",
        "processor",
        "cpu",
        "lag",
        "lags",
    ],

    "charging": [
        "charging",
        "charger",
        "charging speed",
        "fast charging",
        "charge",
    ],

    "software": [
        "software",
        "android",
        "ios",
        "operating system",
        "os",
        "app",
        "apps",
        "update",
        "updates",
    ],

    "build_quality": [
        "build quality",
        "build",
        "construction",
        "solid",
        "sturdy",
        "plastic",
        "metal",
    ],

    "value": [
        "value",
        "price",
        "pricing",
        "cost",
        "money",
        "worth",
        "expensive",
        "cheap",
        "affordable",
    ],

    "sound_quality": [
        "sound",
        "audio",
        "speaker",
        "speakers",
        "bass",
        "volume",
        "sound quality",
    ],

    "connectivity": [
        "connectivity",
        "bluetooth",
        "wifi",
        "wi-fi",
        "network",
        "connection",
        "signal",
        "5g",
        "4g",
    ],

    "ease_of_use": [
        "easy to use",
        "easy",
        "simple",
        "setup",
        "installation",
        "install",
        "user friendly",
        "user-friendly",
    ],

    "quality": [
        "quality",
        "well made",
        "well-made",
        "poor quality",
        "good quality",
    ],

    "durability": [
        "durability",
        "durable",
        "lasts",
        "long lasting",
        "long-lasting",
        "sturdy",
        "broke",
        "broken",
    ],

    "size": [
        "size",
        "sized",
        "small",
        "large",
        "big",
        "tiny",
        "dimensions",
        "fit",
    ],

    "material": [
        "material",
        "fabric",
        "cotton",
        "leather",
        "wood",
        "metal",
        "plastic",
    ],

    "design": [
        "design",
        "style",
        "stylish",
        "look",
        "looks",
        "appearance",
        "beautiful",
    ],

    "fit": [
        "fit",
        "fits",
        "fitting",
        "tight",
        "loose",
        "small",
        "large",
    ],

    "comfort": [
        "comfort",
        "comfortable",
        "uncomfortable",
        "soft",
        "cushion",
        "cushioning",
    ],

    "appearance": [
        "appearance",
        "look",
        "looks",
        "color",
        "colour",
        "beautiful",
        "attractive",
    ],
}


# ============================================================
# SENTENCE SPLITTING
# ============================================================

def split_sentences(text):
    """
    Basic sentence splitter.

    We intentionally keep this lightweight because this is a
    large-scale benchmark and later the same method may run
    over 1.5M reviews.
    """

    if not text:
        return []

    text = str(text).strip()

    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?])\s+|\n+",
        text
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


# ============================================================
# ASPECT DETECTION
# ============================================================

def detect_aspects(text, category):
    """
    Detect category-specific aspects using keyword matching.
    """

    if not text:
        return []

    text_lower = text.lower()

    category_aspects = ASPECTS.get(category, [])

    detected = []

    for aspect in category_aspects:

        keywords = ASPECT_KEYWORDS.get(aspect, [])

        for keyword in keywords:

            if keyword.lower() in text_lower:
                detected.append(aspect)
                break

    return detected


# ============================================================
# ASPECT SENTIMENT
# ============================================================

def calculate_aspect_sentiment(text, aspects):
    """
    Calculate sentiment for each detected aspect.

    Instead of assigning the overall review sentiment to every
    aspect, we look for sentences containing the aspect's
    keywords and run VADER on those sentences.

    Returns:
        {
            "battery": 0.72,
            "camera": -0.45
        }
    """

    if not text or not aspects:
        return {}

    sentences = split_sentences(text)

    if not sentences:
        return {}

    sentence_data = [
        (sentence, sentence.lower())
        for sentence in sentences
    ]

    aspect_scores = {}

    for aspect in aspects:

        keywords = ASPECT_KEYWORDS.get(aspect, [])

        matched_sentences = []

        for sentence, sentence_lower in sentence_data:

            for keyword in keywords:

                if keyword.lower() in sentence_lower:
                    matched_sentences.append(sentence)
                    break

        if not matched_sentences:
            continue

        scores = []

        for sentence in matched_sentences:

            score = analyzer.polarity_scores(sentence)["compound"]

            scores.append(score)

        if scores:
            aspect_scores[aspect] = round(
                sum(scores) / len(scores),
                4
            )

    return aspect_scores


# ============================================================
# LABEL
# ============================================================

def sentiment_label(score):

    if score >= 0.05:
        return "positive"

    if score <= -0.05:
        return "negative"

    return "neutral"


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("RETAILMIND AI - ASPECT SENTIMENT 20K BALANCED BENCHMARK")
print("=" * 70)


# ------------------------------------------------------------
# Load products
# ------------------------------------------------------------

print("\nLoading products...")

products = pd.read_parquet(PRODUCTS_PATH)

print(f"Products loaded: {len(products):,}")


required_product_columns = [
    "parent_asin",
    "main_category",
]

missing_product_columns = [
    col
    for col in required_product_columns
    if col not in products.columns
]

if missing_product_columns:
    raise ValueError(
        f"Missing product columns: {missing_product_columns}"
    )


products_small = products[
    [
        "parent_asin",
        "main_category",
    ]
].drop_duplicates("parent_asin")


# ------------------------------------------------------------
# Load reviews
# ------------------------------------------------------------

print("\nLoading reviews...")

reviews = pd.read_parquet(REVIEWS_PATH)

print(f"Total reviews: {len(reviews):,}")


required_review_columns = [
    "parent_asin",
    "rating",
    "title",
    "text",
]

missing_review_columns = [
    col
    for col in required_review_columns
    if col not in reviews.columns
]

if missing_review_columns:
    raise ValueError(
        f"Missing review columns: {missing_review_columns}"
    )


# ------------------------------------------------------------
# Join category
# ------------------------------------------------------------

print("\nJoining categories...")

reviews = reviews.merge(
    products_small,
    on="parent_asin",
    how="left",
)

missing_categories = reviews["main_category"].isna().sum()

print(f"Reviews without category: {missing_categories:,}")

if missing_categories > 0:
    raise ValueError(
        "Some reviews could not be joined to a product category."
    )


# ------------------------------------------------------------
# Balanced sampling
# ------------------------------------------------------------

print("\nCreating balanced six-category sample...")

categories = list(ASPECTS.keys())

base_count = SAMPLE_SIZE // len(categories)

remainder = SAMPLE_SIZE % len(categories)

samples = []

for index, category in enumerate(categories):

    category_reviews = reviews[
        reviews["main_category"] == category
    ]

    n = base_count + (1 if index < remainder else 0)

    if len(category_reviews) < n:

        raise ValueError(
            f"Not enough reviews for {category}: "
            f"{len(category_reviews):,} available, "
            f"{n:,} required"
        )

    sampled = category_reviews.sample(
        n=n,
        random_state=RANDOM_STATE + index,
    )

    samples.append(sampled)

    print(
        f"  {category:35s}: {len(sampled):,}"
    )


sample = pd.concat(
    samples,
    ignore_index=True
)

# Shuffle final dataset
sample = sample.sample(
    frac=1,
    random_state=RANDOM_STATE
).reset_index(drop=True)

print(f"\nBalanced sample: {len(sample):,}")


# ------------------------------------------------------------
# Combine title + text
# ------------------------------------------------------------

sample["review_text"] = (
    sample["title"].fillna("").astype(str)
    + ". "
    + sample["text"].fillna("").astype(str)
).str.strip()


# ------------------------------------------------------------
# Initialize VADER
# ------------------------------------------------------------

analyzer = SentimentIntensityAnalyzer()


# ------------------------------------------------------------
# Overall + aspect sentiment
# ------------------------------------------------------------

print("\nRunning overall VADER + aspect-level sentiment...")

start_time = time.time()

sentiment_scores = []
sentiment_labels = []
detected_aspects = []
aspect_sentiments = []

for text_value, category in zip(
    sample["review_text"],
    sample["main_category"]
):

    # Overall review sentiment
    overall_score = analyzer.polarity_scores(
        text_value
    )["compound"]

    label = sentiment_label(overall_score)

    # Detect aspects
    aspects = detect_aspects(
        text_value,
        category
    )

    # Aspect-specific sentiment
    aspect_scores = calculate_aspect_sentiment(
        text_value,
        aspects
    )

    sentiment_scores.append(
        round(overall_score, 4)
    )

    sentiment_labels.append(label)

    detected_aspects.append(aspects)

    aspect_sentiments.append(aspect_scores)


sample["sentiment_score"] = sentiment_scores

sample["sentiment_label"] = sentiment_labels

sample["aspects"] = detected_aspects

sample["aspect_sentiments"] = aspect_sentiments


elapsed = time.time() - start_time

reviews_per_second = (
    len(sample) / elapsed
    if elapsed > 0
    else 0
)


# ============================================================
# RESULTS
# ============================================================

print("\n" + "=" * 70)
print("BENCHMARK RESULTS")
print("=" * 70)

print(
    f"Reviews processed : {len(sample):,}"
)

print(
    f"Processing time   : {elapsed:.2f} seconds"
)

print(
    f"Reviews / second  : {reviews_per_second:,.0f}"
)


# ------------------------------------------------------------
# Category distribution
# ------------------------------------------------------------

print("\nCategory distribution:")

print(
    sample["main_category"]
    .value_counts()
    .sort_index()
)


# ------------------------------------------------------------
# Overall sentiment
# ------------------------------------------------------------

print("\nOverall sentiment distribution:")

print(
    sample["sentiment_label"]
    .value_counts()
)


print(
    f"\nAverage overall sentiment score: "
    f"{sample['sentiment_score'].mean():.4f}"
)


# ------------------------------------------------------------
# Aspect detection
# ------------------------------------------------------------

sample["has_aspect"] = sample["aspects"].apply(
    lambda x: len(x) > 0
)

print("\nAspect detection by category:")

aspect_summary = (
    sample
    .groupby("main_category", observed=False)
    .agg(
        reviews=("parent_asin", "size"),
        reviews_with_aspects=("has_aspect", "sum"),
    )
)

aspect_summary["detection_rate"] = (
    aspect_summary["reviews_with_aspects"]
    / aspect_summary["reviews"]
    * 100
)

print(aspect_summary)


# ------------------------------------------------------------
# Aspect frequency
# ------------------------------------------------------------

print("\nAspect frequency by category:")

for category in categories:

    category_rows = sample[
        sample["main_category"] == category
    ]

    counter = Counter()

    for aspects in category_rows["aspects"]:

        counter.update(aspects)

    print(f"\n{category}")

    for aspect, count in counter.most_common():

        print(
            f"  {aspect:20s}: {count:,}"
        )


# ------------------------------------------------------------
# Aspect sentiment statistics
# ------------------------------------------------------------

print("\nAspect sentiment statistics:")

aspect_score_values = defaultdict(list)

for aspect_scores in sample["aspect_sentiments"]:

    for aspect, score in aspect_scores.items():

        aspect_score_values[aspect].append(score)


for aspect, scores in sorted(
    aspect_score_values.items()
):

    print(
        f"  {aspect:20s} "
        f"count={len(scores):5d} "
        f"avg={sum(scores) / len(scores):.4f}"
    )


# ------------------------------------------------------------
# Rating vs sentiment
# ------------------------------------------------------------

print("\nRating vs overall sentiment:")

rating_summary = (
    sample
    .groupby("rating", observed=False)["sentiment_score"]
    .agg(
        ["count", "mean"]
    )
    .round(4)
)

print(rating_summary)


# ------------------------------------------------------------
# Sample output
# ------------------------------------------------------------

print("\nSample processed reviews:")

print("-" * 70)

display_columns = [
    "parent_asin",
    "main_category",
    "rating",
    "sentiment_score",
    "sentiment_label",
    "aspects",
    "aspect_sentiments",
]

print(
    sample[
        display_columns
    ]
    .head(15)
    .to_string(index=False)
)


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

sample.to_parquet(
    OUTPUT_PATH,
    index=False
)

print("\nOutput:")

print(OUTPUT_PATH)


# ============================================================
# COMPLETE
# ============================================================

print("\n" + "=" * 70)
print("ASPECT SENTIMENT BENCHMARK COMPLETE")
print("=" * 70)