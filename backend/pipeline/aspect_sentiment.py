"""
Extends sentiment_analysis.py: instead of one overall sentiment score
per review, this extracts a sentiment score PER ASPECT (camera, battery,
performance, display, value) by finding sentences that mention each
aspect and scoring those sentences specifically with VADER.

Keyword-based aspect matching, not a trained ABSA model -- an honest
scope choice for a project like this, not oversold as more than it is.

Input:  data/reviews.csv
Output: data/product_aspect_sentiment.csv
"""

import re
import pandas as pd
from nltk.sentiment import SentimentIntensityAnalyzer

INPUT_PATH = "data/reviews.csv"
OUTPUT_PATH = "data/product_aspect_sentiment.csv"

ASPECT_KEYWORDS = {
    "camera": ["camera", "photo", "photos", "picture", "pictures", "pic", "pics",
               "selfie", "selfies", "zoom", "video quality"],
    "battery": ["battery", "batteries", "charge", "charging", "charger",
                "battery life", "power drain"],
    "performance": ["performance", "speed", "fast", "slow", "lag", "laggy",
                     "processor", "cpu", "smooth", "freeze", "freezing", "hang", "hangs"],
    "display": ["screen", "display", "resolution", "brightness", "touchscreen",
                "touch screen"],
    "value": ["price", "value", "worth", "cheap", "expensive", "overpriced",
              "money", "bang for buck"],
}

SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")


def split_sentences(text: str) -> list:
    if not text or pd.isna(text):
        return []
    return [s.strip() for s in SENTENCE_SPLIT_RE.split(str(text)) if s.strip()]


def matched_aspects(sentence: str) -> list:
    lowered = sentence.lower()
    return [a for a, kws in ASPECT_KEYWORDS.items() if any(kw in lowered for kw in kws)]


def main():
    print("Loading reviews...")
    df = pd.read_csv(INPUT_PATH)
    print(f"Total reviews: {len(df)}")

    df["combined_text"] = (
        df["summary"].fillna("").astype(str) + ". " + df["review_text"].fillna("").astype(str)
    )

    analyzer = SentimentIntensityAnalyzer()
    product_aspect_scores = {}

    print("Scanning reviews for aspect mentions...")
    total = len(df)
    for i, row in enumerate(df.itertuples(index=False), start=1):
        if i % 20000 == 0:
            print(f"  processed {i}/{total} reviews...")
        asin = row.asin
        for sentence in split_sentences(row.combined_text):
            aspects = matched_aspects(sentence)
            if not aspects:
                continue
            compound = analyzer.polarity_scores(sentence)["compound"]
            for aspect in aspects:
                product_aspect_scores.setdefault(asin, {}).setdefault(aspect, []).append(compound)

    print("Aggregating per-product, per-aspect scores...")
    records = []
    for asin, aspect_data in product_aspect_scores.items():
        record = {"asin": asin}
        for aspect in ASPECT_KEYWORDS:
            scores = aspect_data.get(aspect, [])
            if scores:
                record[f"{aspect}_sentiment"] = round(sum(scores) / len(scores), 4)
                record[f"{aspect}_mentions"] = len(scores)
            else:
                record[f"{aspect}_sentiment"] = None
                record[f"{aspect}_mentions"] = 0
        records.append(record)

    result_df = pd.DataFrame(records)
    result_df.to_csv(OUTPUT_PATH, index=False)

    print(f"\nSaved: {OUTPUT_PATH}")
    print(f"Products with at least one aspect mention: {len(result_df)}")
    for aspect in ASPECT_KEYWORDS:
        covered = (result_df[f"{aspect}_mentions"] > 0).sum()
        print(f"  {aspect:12s}: {covered} / {len(result_df)} ({covered/len(result_df)*100:.1f}%)")


if __name__ == "__main__":
    main()