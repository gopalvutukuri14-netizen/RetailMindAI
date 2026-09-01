import pandas as pd
from pathlib import Path


DATA_DIR = Path("data")

PRODUCTS_FILE = DATA_DIR / "products_clean.csv"
SENTIMENT_FILE = DATA_DIR / "product_sentiment.csv"

OUTPUT_FILE = DATA_DIR / "products_for_embedding.csv"


def safe_text(value):
    """
    Convert a value into clean text.
    Returns None for missing/empty values.
    """

    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "" or value.lower() == "nan":
        return None

    return value


def add_field(parts, label, value):
    """
    Add a field to the product document only if it has a valid value.
    """

    value = safe_text(value)

    if value:
        parts.append(f"{label}: {value}")


def create_product_document(row):
    """
    Create one semantic text document for a product.
    This text will later be converted into embeddings.
    """

    parts = []

    # Basic product information
    add_field(parts, "Product", row.get("title"))
    add_field(parts, "Brand", row.get("brand"))
    add_field(parts, "Category", row.get("category"))

    # Price
    price = row.get("price_inr")

    if pd.notna(price):
        parts.append(f"Price: ₹{price:.2f}")

    # Technical specifications
    ram = row.get("ram_gb_numeric")

    if pd.notna(ram):
        parts.append(f"RAM: {ram} GB")

    storage = row.get("storage_gb_numeric")

    if pd.notna(storage):
        parts.append(f"Storage: {storage} GB")

    camera = row.get("camera_mp_numeric")

    if pd.notna(camera):
        parts.append(f"Camera: {camera} MP")

    battery = row.get("battery_mah_numeric")

    if pd.notna(battery):
        parts.append(f"Battery: {battery} mAh")

    add_field(parts, "Operating System", row.get("os"))
    add_field(parts, "Screen Size", row.get("screen_size"))
    add_field(parts, "Network", row.get("network"))
    add_field(parts, "Processor", row.get("processor"))

    # Product information
    add_field(parts, "Description", row.get("description"))
    add_field(parts, "Features", row.get("features"))

    # Review statistics
    total_reviews = row.get("total_reviews")

    if pd.notna(total_reviews):
        parts.append(f"Total Reviews: {int(total_reviews)}")

    average_rating = row.get("average_rating")

    if pd.notna(average_rating):
        parts.append(f"Average Rating: {average_rating}/5")

    sentiment_score = row.get("average_sentiment_score")

    if pd.notna(sentiment_score):
        parts.append(
            f"Average Customer Sentiment Score: {sentiment_score}"
        )

    positive_ratio = row.get("positive_ratio")

    if pd.notna(positive_ratio):
        parts.append(
            f"Positive Review Ratio: {positive_ratio * 100:.1f}%"
        )

    negative_ratio = row.get("negative_ratio")

    if pd.notna(negative_ratio):
        parts.append(
            f"Negative Review Ratio: {negative_ratio * 100:.1f}%"
        )

    # Join all information into one document
    return "\n".join(parts)


def main():

    print("Loading cleaned products...")

    products = pd.read_csv(PRODUCTS_FILE)

    print(f"Total products: {len(products)}")

    print("Loading product sentiment data...")

    sentiment = pd.read_csv(SENTIMENT_FILE)

    print(f"Products with sentiment data: {len(sentiment)}")

    print("Merging product and sentiment data...")

    merged = products.merge(
        sentiment,
        on="asin",
        how="left"
    )

    print(f"Merged products: {len(merged)}")

    print("Creating embedding documents...")

    merged["embedding_text"] = merged.apply(
        create_product_document,
        axis=1
    )

    # Keep important columns
    output_columns = [
        "asin",
        "title",
        "brand",
        "price_inr",
        "ram_gb_numeric",
        "storage_gb_numeric",
        "camera_mp_numeric",
        "battery_mah_numeric",
        "average_rating",
        "total_reviews",
        "average_sentiment_score",
        "positive_ratio",
        "negative_ratio",
        "embedding_text"
    ]

    final_df = merged[output_columns]

    print("Saving embedding dataset...")

    final_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(f"\nSaved file: {OUTPUT_FILE}")

    print("\nSample embedding document:\n")

    print(final_df["embedding_text"].iloc[0])

    print("\nCompleted successfully.")


if __name__ == "__main__":
    main()