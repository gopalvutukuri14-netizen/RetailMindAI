import pandas as pd
import numpy as np
import torch
from FlagEmbedding import BGEM3FlagModel


INPUT_FILE = "data/products_for_embedding.csv"
OUTPUT_FILE = "data/product_embeddings.npy"
ASIN_FILE = "data/product_embedding_asins.csv"


def main():

    print("=" * 60)
    print("BGE-M3 GPU Embedding Pipeline")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Check GPU
    # ---------------------------------------------------------

    print("\nChecking CUDA...")

    if torch.cuda.is_available():
        device = "cuda"
        print("CUDA available: YES")
        print(f"GPU: {torch.cuda.get_device_name(0)}")

        gpu_memory = torch.cuda.get_device_properties(0).total_memory
        print(
            f"GPU memory: "
            f"{gpu_memory / (1024 ** 3):.2f} GB"
        )

    else:
        device = "cpu"
        print("CUDA available: NO")
        print("WARNING: Running on CPU!")

    # ---------------------------------------------------------
    # 2. Load products
    # ---------------------------------------------------------

    print("\nLoading products...")

    df = pd.read_csv(INPUT_FILE)

    print(f"Total products: {len(df)}")

    # ---------------------------------------------------------
    # 3. Prepare embedding text
    # ---------------------------------------------------------

    if "embedding_text" not in df.columns:
        raise ValueError(
            "Column 'embedding_text' not found in CSV."
        )

    texts = df["embedding_text"].fillna("").tolist()

    # ---------------------------------------------------------
    # 4. Load BGE-M3
    # ---------------------------------------------------------

    print("\nLoading BGE-M3 model...")

    model = BGEM3FlagModel(
        "BAAI/bge-m3",
        use_fp16=(device == "cuda")
    )

    print("BGE-M3 loaded.")

    # ---------------------------------------------------------
    # 5. Verify GPU after model loading
    # ---------------------------------------------------------

    if device == "cuda":
        print(
            f"CUDA device currently active: "
            f"{torch.cuda.current_device()}"
        )

        print(
            f"GPU name: "
            f"{torch.cuda.get_device_name(torch.cuda.current_device())}"
        )

    # ---------------------------------------------------------
    # 6. Generate embeddings
    # ---------------------------------------------------------

    print("\nGenerating embeddings...")

    print("Batch size: 12")
    print("Max length: 1024")
    print(f"Device: {device}")

    embeddings = model.encode(
        texts,
        batch_size=12,
        max_length=1024
    )["dense_vecs"]

    print("\nEmbeddings generated.")

    print(f"Embedding shape: {embeddings.shape}")

    # ---------------------------------------------------------
    # 7. Save embeddings
    # ---------------------------------------------------------

    np.save(
        OUTPUT_FILE,
        embeddings
    )

    # ---------------------------------------------------------
    # 8. Save ASIN mapping
    # ---------------------------------------------------------

    if "asin" not in df.columns:
        raise ValueError(
            "Column 'asin' not found in CSV."
        )

    df[["asin"]].to_csv(
        ASIN_FILE,
        index=False
    )

    # ---------------------------------------------------------
    # 9. Final GPU memory information
    # ---------------------------------------------------------

    if device == "cuda":

        allocated = torch.cuda.memory_allocated(0)
        reserved = torch.cuda.memory_reserved(0)

        print()
        print(
            f"GPU memory allocated: "
            f"{allocated / (1024 ** 3):.2f} GB"
        )

        print(
            f"GPU memory reserved: "
            f"{reserved / (1024 ** 3):.2f} GB"
        )

    # ---------------------------------------------------------
    # 10. Output
    # ---------------------------------------------------------

    print()
    print(f"Saved embeddings: {OUTPUT_FILE}")
    print(f"Saved ASIN mapping: {ASIN_FILE}")

    print()
    print("Sample embedding:")
    print(embeddings[0][:10])

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()