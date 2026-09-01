import pandas as pd
import numpy as np
from FlagEmbedding import BGEM3FlagModel


INPUT_FILE = "data/products_for_embedding.csv"
OUTPUT_FILE = "data/product_embeddings.npy"
ASIN_FILE = "data/product_embedding_asins.csv"


def main():

    print("Loading products...")

    df = pd.read_csv(INPUT_FILE)

    print(f"Total products: {len(df)}")

    # Make sure embedding text exists
    texts = df["embedding_text"].fillna("").tolist()

    print("Loading BGE-M3 model...")

    model = BGEM3FlagModel(
        "BAAI/bge-m3",
        use_fp16=True
    )

    print("Generating embeddings...")

    embeddings = model.encode(
        texts,
        batch_size=12,
        max_length=1024
    )["dense_vecs"]

    print("Embeddings generated.")

    print(f"Embedding shape: {embeddings.shape}")

    # Save embeddings
    np.save(
        OUTPUT_FILE,
        embeddings
    )

    # Save ASIN mapping
    df[["asin"]].to_csv(
        ASIN_FILE,
        index=False
    )

    print()
    print(f"Saved embeddings: {OUTPUT_FILE}")
    print(f"Saved ASIN mapping: {ASIN_FILE}")

    print()
    print("Sample embedding:")

    print(embeddings[0][:10])


if __name__ == "__main__":
    main()