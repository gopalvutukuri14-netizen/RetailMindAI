import os
import pandas as pd
import numpy as np
import chromadb


# -----------------------------
# File paths
# -----------------------------

PRODUCTS_FILE = "data/products_for_embedding.csv"
EMBEDDINGS_FILE = "data/product_embeddings.npy"
ASINS_FILE = "data/product_embedding_asins.csv"

CHROMA_PATH = "data/chromadb"


def clean_metadata(value):
    """
    ChromaDB metadata does not support NaN values.
    Convert missing values into safe defaults.
    """

    if pd.isna(value):
        return None

    if isinstance(value, np.generic):
        return value.item()

    return value


def main():

    print("Loading product data...")

    products_df = pd.read_csv(PRODUCTS_FILE)

    print(f"Total products: {len(products_df)}")


    print("Loading embeddings...")

    embeddings = np.load(EMBEDDINGS_FILE)

    print(f"Embeddings shape: {embeddings.shape}")


    print("Loading ASIN mapping...")

    asins_df = pd.read_csv(ASINS_FILE)

    print(f"ASIN mappings: {len(asins_df)}")


    # -----------------------------
    # Validation
    # -----------------------------

    if len(products_df) != len(embeddings):

        raise ValueError(
            f"Mismatch: {len(products_df)} products "
            f"but {len(embeddings)} embeddings"
        )


    print("\nConnecting to ChromaDB...")


    client = chromadb.PersistentClient(
        path=CHROMA_PATH
    )


    # -----------------------------
    # Delete existing collection
    # -----------------------------

    collection_name = "retail_products"

    try:
        client.delete_collection(collection_name)
        print("Existing collection deleted.")

    except Exception:
        print("Creating new collection.")


    collection = client.create_collection(
        name=collection_name,
        metadata={
            "description": "RetailMind AI smartphone product embeddings"
        }
    )


    print("\nPreparing product data...")


    documents = []
    metadatas = []
    ids = []


    for index, row in products_df.iterrows():

        asin = str(row["asin"])


        # -----------------------------
        # Document text
        # -----------------------------

        document = str(
            row.get(
                "embedding_text",
                row.get("title", "")
            )
        )


        # -----------------------------
        # Metadata
        # -----------------------------

        metadata = {

            "asin": asin,

            "title": str(row.get("title", "")),

            "brand": str(row.get("brand", "")),

            "price_inr": clean_metadata(
                row.get("price_inr")
            ),

            "ram_gb": clean_metadata(
                row.get("ram_gb_numeric")
            ),

            "storage_gb": clean_metadata(
                row.get("storage_gb_numeric")
            ),

            "camera_mp": clean_metadata(
                row.get("camera_mp_numeric")
            ),

            "battery_mah": clean_metadata(
                row.get("battery_mah_numeric")
            ),

            "average_rating": clean_metadata(
                row.get("average_rating")
            ),

            "total_reviews": clean_metadata(
                row.get("total_reviews")
            ),

            "average_sentiment_score": clean_metadata(
                row.get("average_sentiment_score")
            ),

            "positive_ratio": clean_metadata(
                row.get("positive_ratio")
            ),

            "negative_ratio": clean_metadata(
                row.get("negative_ratio")
            )
        }


        # Remove None values
        metadata = {
            key: value
            for key, value in metadata.items()
            if value is not None
        }


        documents.append(document)

        metadatas.append(metadata)

        ids.append(asin)


    print("Loading products into ChromaDB...")


    # -----------------------------
    # Batch insertion
    # -----------------------------

    batch_size = 100


    for start in range(0, len(products_df), batch_size):

        end = min(
            start + batch_size,
            len(products_df)
        )


        collection.add(

            ids=ids[start:end],

            documents=documents[start:end],

            embeddings=embeddings[start:end].tolist(),

            metadatas=metadatas[start:end]

        )


        print(
            f"Loaded products {start} to {end}"
        )


    print("\nChromaDB loading completed!")


    print(
        f"Total products in database: "
        f"{collection.count()}"
    )


    print(
        f"\nDatabase saved at: {CHROMA_PATH}"
    )


if __name__ == "__main__":
    main()