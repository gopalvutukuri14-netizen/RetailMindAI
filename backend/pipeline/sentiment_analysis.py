import pandas as pd
from nltk.sentiment import SentimentIntensityAnalyzer


INPUT_PATH = "data/reviews.csv"
OUTPUT_PATH = "data/reviews_sentiment.csv"


def get_sentiment(text, analyzer):
    """
    Analyze review sentiment using VADER.

    Returns:
        sentiment_label
        sentiment_score
    """

    if pd.isna(text) or not str(text).strip():
        return "neutral", 0.0

    scores = analyzer.polarity_scores(str(text))
    compound_score = scores["compound"]

    if compound_score >= 0.05:
        label = "positive"
    elif compound_score <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    return label, compound_score


def main():

    print("Loading reviews...")

    df = pd.read_csv(INPUT_PATH)

    print(f"Total reviews: {len(df)}")

    analyzer = SentimentIntensityAnalyzer()

    print("Analyzing sentiments...")

    # Combine summary and review text
    df["combined_text"] = (
        df["summary"].fillna("").astype(str)
        + ". "
        + df["review_text"].fillna("").astype(str)
    )

    sentiments = df["combined_text"].apply(
        lambda text: get_sentiment(text, analyzer)
    )

    df["sentiment_label"] = sentiments.apply(lambda x: x[0])
    df["sentiment_score"] = sentiments.apply(lambda x: x[1])

    # Remove temporary column
    df.drop(columns=["combined_text"], inplace=True)

    df.to_csv(OUTPUT_PATH, index=False)

    print("\nSentiment analysis completed.")

    print("\nSentiment distribution:")

    print(
        df["sentiment_label"]
        .value_counts()
    )

    print(f"\nSaved file: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()