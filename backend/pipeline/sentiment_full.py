import os
import time
import re
from collections import defaultdict

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


# ============================================================
# CONFIG
# ============================================================

PRODUCTS_PATH = "data/products_master.parquet"
REVIEWS_PATH = "data/reviews_master.parquet"

OUTPUT_DIR = "data/sentiment_chunks"
FINAL_OUTPUT = "data/reviews_sentiment.parquet"

CHUNK_SIZE = 50_000

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# CATEGORY ASPECTS
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
# KEYWORDS
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
# VADER
# ============================================================

analyzer = SentimentIntensityAnalyzer()


# ============================================================
# FUNCTIONS
# ============================================================

def split_sentences(text):
    if not text:
        return []

    text = str(text).strip()

    if not text:
        return []

    return [
        s.strip()
        for s in re.split(
            r"(?<=[.!?])\s+|\n+",
            text
        )
        if s.strip()
    ]


def detect_aspects(text, category):

    if not text:
        return []

    text_lower = text.lower()

    detected = []

    for aspect in ASPECTS.get(category, []):

        for keyword in ASPECT_KEYWORDS.get(aspect, []):

            if keyword.lower() in text_lower:
                detected.append(aspect)
                break

    return detected


def calculate_aspect_sentiment(text, aspects):

    if not text or not aspects:
        return {}

    sentences = split_sentences(text)

    if not sentences:
        return {}

    result = {}

    for aspect in aspects:

        keywords = ASPECT_KEYWORDS.get(
            aspect,
            []
        )

        matching_sentences = []

        for sentence in sentences:

            sentence_lower = sentence.lower()

            if any(
                keyword.lower() in sentence_lower
                for keyword in keywords
            ):
                matching_sentences.append(sentence)

        if not matching_sentences:
            continue

        scores = [
            analyzer.polarity_scores(sentence)["compound"]
            for sentence in matching_sentences
        ]

        result[aspect] = round(
            sum(scores) / len(scores),
            4
        )

    return result


def sentiment_label(score):

    if score >= 0.05:
        return "positive"

    if score <= -0.05:
        return "negative"

    return "neutral"


# ============================================================
# PROCESS ONE CHUNK
# ============================================================

def process_chunk(chunk, products):

    chunk = chunk.merge(
        products,
        on="parent_asin",
        how="left"
    )

    if chunk["main_category"].isna().any():

        missing = chunk["main_category"].isna().sum()

        raise ValueError(
            f"{missing} reviews could not be joined "
            f"to a product category."
        )

    texts = (
        chunk["title"]
        .fillna("")
        .astype(str)
        + ". "
        + chunk["text"]
        .fillna("")
        .astype(str)
    ).str.strip()

    sentiment_scores = []
    sentiment_labels = []
    aspects_list = []
    aspect_sentiments_list = []

    for text, category in zip(
        texts,
        chunk["main_category"]
    ):

        overall_score = analyzer.polarity_scores(
            text
        )["compound"]

        aspects = detect_aspects(
            text,
            category
        )

        aspect_sentiments = calculate_aspect_sentiment(
            text,
            aspects
        )

        sentiment_scores.append(
            round(overall_score, 4)
        )

        sentiment_labels.append(
            sentiment_label(overall_score)
        )

        aspects_list.append(aspects)

        aspect_sentiments_list.append(
            aspect_sentiments
        )

    chunk["sentiment_score"] = sentiment_scores

    chunk["sentiment_label"] = sentiment_labels

    chunk["aspects"] = aspects_list

    chunk["aspect_sentiments"] = (
        aspect_sentiments_list
    )

    return chunk


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("RETAILMIND AI - FULL REVIEW SENTIMENT PROCESSING")
print("=" * 70)

print("\nLoading products...")

products = pd.read_parquet(
    PRODUCTS_PATH,
    columns=[
        "parent_asin",
        "main_category",
    ]
).drop_duplicates("parent_asin")

print(
    f"Products loaded: {len(products):,}"
)


print("\nLoading reviews...")

reviews = pd.read_parquet(
    REVIEWS_PATH
)

total_reviews = len(reviews)

print(
    f"Reviews loaded: {total_reviews:,}"
)


# ============================================================
# CHECK EXISTING CHUNKS
# ============================================================

existing_chunks = sorted(
    [
        f
        for f in os.listdir(OUTPUT_DIR)
        if f.startswith("chunk_")
        and f.endswith(".parquet")
    ]
)

completed_indices = set()

for filename in existing_chunks:

    try:

        index = int(
            filename
            .replace("chunk_", "")
            .replace(".parquet", "")
        )

        completed_indices.add(index)

    except ValueError:
        pass


print(
    f"\nExisting completed chunks: "
    f"{len(completed_indices)}"
)


# ============================================================
# PROCESS CHUNKS
# ============================================================

start_time = time.time()

total_chunks = (
    total_reviews + CHUNK_SIZE - 1
) // CHUNK_SIZE


for chunk_index in range(total_chunks):

    output_file = os.path.join(
        OUTPUT_DIR,
        f"chunk_{chunk_index:04d}.parquet"
    )

    if chunk_index in completed_indices:

        print(
            f"\n[{chunk_index + 1}/{total_chunks}] "
            f"Skipping completed chunk"
        )

        continue

    start_row = chunk_index * CHUNK_SIZE

    end_row = min(
        start_row + CHUNK_SIZE,
        total_reviews
    )

    print(
        f"\n[{chunk_index + 1}/{total_chunks}] "
        f"Processing rows "
        f"{start_row:,} - {end_row - 1:,}"
    )

    chunk = reviews.iloc[
        start_row:end_row
    ].copy()

    chunk_start = time.time()

    processed = process_chunk(
        chunk,
        products
    )

    processed.to_parquet(
        output_file,
        index=False
    )

    chunk_time = time.time() - chunk_start

    speed = (
        len(processed) / chunk_time
        if chunk_time > 0
        else 0
    )

    print(
        f"  Saved: {output_file}"
    )

    print(
        f"  Processed: {len(processed):,}"
    )

    print(
        f"  Speed: {speed:,.0f} reviews/sec"
    )


# ============================================================
# COMBINE CHUNKS
# ============================================================

print("\n" + "=" * 70)
print("Combining sentiment chunks...")
print("=" * 70)

chunk_files = sorted(
    [
        os.path.join(
            OUTPUT_DIR,
            f
        )
        for f in os.listdir(OUTPUT_DIR)
        if f.startswith("chunk_")
        and f.endswith(".parquet")
    ]
)

if len(chunk_files) != total_chunks:

    raise RuntimeError(
        f"Expected {total_chunks} chunks, "
        f"but found {len(chunk_files)}."
    )


frames = []

for i, filepath in enumerate(chunk_files):

    print(
        f"Loading chunk "
        f"{i + 1}/{len(chunk_files)}..."
    )

    frames.append(
        pd.read_parquet(filepath)
    )


final_df = pd.concat(
    frames,
    ignore_index=True
)


# ============================================================
# VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("FINAL VALIDATION")
print("=" * 70)

print(
    f"Final review count: "
    f"{len(final_df):,}"
)

print(
    f"Expected review count: "
    f"{total_reviews:,}"
)


if len(final_df) != total_reviews:

    raise RuntimeError(
        "Final review count does not match "
        "the original review count."
    )


required_columns = [
    "parent_asin",
    "asin",
    "rating",
    "title",
    "text",
    "timestamp",
    "verified_purchase",
    "helpful_vote",
    "main_category",
    "sentiment_score",
    "sentiment_label",
    "aspects",
    "aspect_sentiments",
]


missing_columns = [
    col
    for col in required_columns
    if col not in final_df.columns
]


if missing_columns:

    raise RuntimeError(
        f"Missing final columns: "
        f"{missing_columns}"
    )


print("Row count check: PASS")

print("Schema check: PASS")

print(
    "Missing category:",
    final_df["main_category"].isna().sum()
)

print(
    "Missing sentiment:",
    final_df["sentiment_score"].isna().sum()
)


# ============================================================
# SAVE FINAL
# ============================================================

print("\nSaving final sentiment dataset...")

final_df.to_parquet(
    FINAL_OUTPUT,
    index=False
)

print(
    f"Saved: {FINAL_OUTPUT}"
)


# ============================================================
# SUMMARY
# ============================================================

elapsed = time.time() - start_time

print("\n" + "=" * 70)
print("FULL SENTIMENT PROCESSING COMPLETE")
print("=" * 70)

print(
    f"Reviews processed : {len(final_df):,}"
)

print(
    f"Total time        : {elapsed / 60:.2f} minutes"
)

print("\nSentiment distribution:")

print(
    final_df["sentiment_label"]
    .value_counts()
)

print("\nCategory distribution:")

print(
    final_df["main_category"]
    .value_counts()
)

print("\nOutput:")

print(FINAL_OUTPUT)

print("\nNext step:")

print(
    "Aggregate review sentiment and aspect "
    "sentiment into product-level features."
)