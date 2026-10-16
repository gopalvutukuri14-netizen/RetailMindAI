"""
SmartPick - BGE-M3 Product Embedding Pipeline

Reads:  data/products_master.parquet  (embedding_text + parent_asin columns)
Writes: data/product_embeddings.npy          (float32 memmap, shape [N, 1024])
        data/product_embedding_parent_asins.csv

Features:
  - Dense-only encoding  (sparse + ColBERT disabled -> ~2-3x faster on GPU)
  - Explicit L2 normalisation for cosine similarity compatibility in ChromaDB
  - Memory-mapped .npy output (250K x 1024 x 4B = 1 GB, never all in RAM)
  - Chunk-level checkpoint / resume  (safe to Ctrl+C and restart)
  - Per-chunk ETA, speed, and GPU memory reporting
  - show_progress_bar on inner BGE-M3 batch loop
  - Dynamic embedding dimension detection from first chunk output
  - Absolute paths resolved relative to this file (CWD-independent)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import torch
from FlagEmbedding import BGEM3FlagModel


# ============================================================
# PATHS  (always resolved relative to this file, not CWD)
# ============================================================

_HERE = Path(__file__).resolve().parent          # backend/pipeline/
_DATA = _HERE.parent.parent / "data"             # project root / data/

INPUT_FILE        = _DATA / "products_master.parquet"
OUTPUT_FILE       = _DATA / "product_embeddings.npy"
PARENT_ASIN_FILE  = _DATA / "product_embedding_parent_asins.csv"
PROGRESS_FILE     = _DATA / "embedding_progress.json"


# ============================================================
# CONFIG
# ============================================================

# Batch size fed to BGE-M3 per GPU forward pass.
# Benchmark showed 12 is stable on RTX 4060 8 GB at max_length=1024.
BATCH_SIZE = 12

# Number of products per outer checkpoint cycle.
# BGE-M3 internally splits this into BATCH_SIZE sub-batches.
CHUNK_SIZE = 5_000

# BGE-M3 hard token limit (model max is 8192, but 1024 covers all products).
MAX_LENGTH = 1_024

MODEL_NAME = "BAAI/bge-m3"

# BGE-M3 dense vector dimension (1024 for bge-m3).
# Detected dynamically from the first chunk; this is used for pre-allocation.
_EXPECTED_DIM = 1_024


# ============================================================
# CHECKPOINT HELPERS
# ============================================================

def save_progress(completed_rows: int, total_rows: int) -> None:
    """Persist current row offset so an interrupted run can resume."""
    payload = {
        "completed_rows": int(completed_rows),
        "total_rows":     int(total_rows),
        "model":          MODEL_NAME,
        "batch_size":     BATCH_SIZE,
        "chunk_size":     CHUNK_SIZE,
        "max_length":     MAX_LENGTH,
    }
    PROGRESS_FILE.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def load_progress(total_rows: int) -> int:
    """
    Return the row index to resume from.
    Returns 0 if no valid checkpoint exists or if the checkpoint
    belongs to a different dataset (different total_rows).
    """
    if not PROGRESS_FILE.exists():
        return 0

    try:
        payload     = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        completed   = int(payload.get("completed_rows", 0))
        saved_total = int(payload.get("total_rows", total_rows))

        if saved_total != total_rows:
            print(
                f"\nWARNING: Progress file belongs to a different dataset "
                f"({saved_total:,} rows vs current {total_rows:,})."
            )
            print("Starting from row 0.")
            return 0

        return min(completed, total_rows)

    except Exception as exc:
        print(f"\nWARNING: Could not read progress file ({exc}). Starting from row 0.")
        return 0


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 70)
    print("SMARTPICK - BGE-M3 PRODUCT EMBEDDINGS")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. CUDA CHECK
    # --------------------------------------------------------

    print("\nChecking CUDA...")

    if torch.cuda.is_available():
        device     = "cuda"
        gpu_props  = torch.cuda.get_device_properties(0)
        print(f"CUDA available  : YES")
        print(f"GPU             : {torch.cuda.get_device_name(0)}")
        print(f"GPU memory      : {gpu_props.total_memory / 1024**3:.2f} GB")
    else:
        device = "cpu"
        print("CUDA available  : NO")
        print("WARNING: Running on CPU. Embeddings will be very slow.")

    # --------------------------------------------------------
    # 2. LOAD PRODUCTS
    # --------------------------------------------------------

    print(f"\nLoading products from:\n  {INPUT_FILE}")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    df = pd.read_parquet(
        INPUT_FILE,
        columns=["parent_asin", "embedding_text"]
    )
    print(f"Total products  : {len(df):,}")

    # --------------------------------------------------------
    # 3. VALIDATE INPUT DATA
    # --------------------------------------------------------

    for col in ("parent_asin", "embedding_text"):
        if col not in df.columns:
            raise ValueError(f"Required column missing from parquet: '{col}'")

    dup_count = int(df["parent_asin"].duplicated().sum())
    if dup_count:
        raise ValueError(
            f"Found {dup_count:,} duplicate parent_asin values in input."
        )

    texts = df["embedding_text"].fillna("").astype(str).tolist()

    empty_count = sum(1 for t in texts if not t.strip())
    if empty_count:
        raise ValueError(
            f"{empty_count:,} products have empty embedding_text. "
            "Re-run preprocessing to fix."
        )

    total_products = len(df)

    # --------------------------------------------------------
    # 4. PREPARE MEMORY-MAPPED OUTPUT FILE
    # --------------------------------------------------------
    #
    # 250,000 x 1,024 x 4 bytes = 1.02 GB
    # The memmap keeps only active rows in RAM; the rest live on disk.

    print("\nPreparing embedding output file...")

    if not OUTPUT_FILE.exists():
        embeddings: np.memmap = np.lib.format.open_memmap(
            OUTPUT_FILE,
            mode="w+",
            dtype=np.float32,
            shape=(total_products, _EXPECTED_DIM),
        )
        print(f"Created         : {OUTPUT_FILE}")
        print(f"Shape           : ({total_products:,}, {_EXPECTED_DIM})")
        print(f"Dtype           : float32")
    else:
        embeddings = np.lib.format.open_memmap(OUTPUT_FILE, mode="r+")
        expected   = (total_products, _EXPECTED_DIM)
        if embeddings.shape != expected:
            raise ValueError(
                f"Existing embedding file has shape {embeddings.shape}, "
                f"expected {expected}. Delete it to start fresh."
            )
        print(f"Resuming file   : {OUTPUT_FILE}")
        print(f"Shape           : {embeddings.shape}")

    # --------------------------------------------------------
    # 5. LOAD / CHECK CHECKPOINT
    # --------------------------------------------------------

    start_row = load_progress(total_products)
    print(f"\nAlready embedded: {start_row:,} / {total_products:,}")

    if start_row >= total_products:
        print("\nAll embeddings already complete. Skipping to validation.")

    else:

        # ----------------------------------------------------
        # 6. LOAD BGE-M3 MODEL
        # ----------------------------------------------------

        print("\nLoading BGE-M3 model...")

        model = BGEM3FlagModel(
            MODEL_NAME,
            use_fp16=(device == "cuda"),
        )

        print("BGE-M3 loaded.")

        if device == "cuda":
            print(f"Active CUDA device : {torch.cuda.current_device()}")
            print(f"GPU name           : {torch.cuda.get_device_name(0)}")

        # ----------------------------------------------------
        # 7. GENERATE EMBEDDINGS  (chunk loop)
        # ----------------------------------------------------

        print("\nGenerating embeddings...")
        print(f"  Model       : {MODEL_NAME}")
        print(f"  Batch size  : {BATCH_SIZE}")
        print(f"  Chunk size  : {CHUNK_SIZE}")
        print(f"  Max length  : {MAX_LENGTH}")
        print(f"  Device      : {device}")
        print(f"  Remaining   : {total_products - start_row:,} products")

        embedding_dim: Optional[int] = None
        overall_start = time.time()

        for chunk_start in range(start_row, total_products, CHUNK_SIZE):

            chunk_end   = min(chunk_start + CHUNK_SIZE, total_products)
            chunk_texts = texts[chunk_start:chunk_end]
            chunk_size  = len(chunk_texts)

            print(f"\n{'-' * 70}")
            print(f"Chunk rows    : {chunk_start:,} - {chunk_end - 1:,}")
            print(f"Chunk size    : {chunk_size:,}")

            chunk_t0 = time.time()

            # ------------------------------------------------
            # FIX 1 & 2 — Dense-only + show_progress_bar
            #
            # return_sparse=False   disables sparse BM25 head
            # return_colbert_vecs=False  disables ColBERT head
            # Together: ~2-3x throughput, much lower VRAM use.
            # show_progress_bar: shows inner batch progress.
            # ------------------------------------------------

            result = model.encode(
                chunk_texts,
                batch_size=BATCH_SIZE,
                max_length=MAX_LENGTH,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )

            dense_vectors = np.asarray(
                result["dense_vecs"],
                dtype=np.float32,
            )

            # ------------------------------------------------
            # FIX 6 — Detect embedding dimension dynamically
            # ------------------------------------------------

            if embedding_dim is None:
                embedding_dim = dense_vectors.shape[1]
                print(f"Embedding dim : {embedding_dim}  (detected)")

                if embeddings.shape[1] != embedding_dim:
                    raise ValueError(
                        f"Embedding file pre-allocated with dim={embeddings.shape[1]}, "
                        f"but model returned dim={embedding_dim}. "
                        f"Delete {OUTPUT_FILE} and restart."
                    )

            # Validate chunk shape
            expected_shape = (chunk_size, embedding_dim)
            if dense_vectors.shape != expected_shape:
                raise ValueError(
                    f"Unexpected embedding shape {dense_vectors.shape}, "
                    f"expected {expected_shape}."
                )

            # ------------------------------------------------
            # FIX 3 — Explicit L2 normalisation
            #
            # BGE-M3 normalises by default, but we enforce it
            # explicitly so ChromaDB cosine similarity is
            # guaranteed correct regardless of library version.
            # ------------------------------------------------

            norms = np.linalg.norm(dense_vectors, axis=1, keepdims=True)
            dense_vectors = dense_vectors / np.maximum(norms, 1e-12)

            # Write to memmap and flush to disk immediately
            embeddings[chunk_start:chunk_end] = dense_vectors
            embeddings.flush()

            # Save checkpoint
            save_progress(chunk_end, total_products)

            # ------------------------------------------------
            # FIX 4 — Per-chunk ETA + speed reporting
            # ------------------------------------------------

            elapsed      = time.time() - chunk_t0
            speed        = chunk_size / elapsed if elapsed > 0 else 0
            completed    = chunk_end
            pct          = completed / total_products * 100
            remaining    = total_products - completed
            eta_secs     = remaining / speed if speed > 0 else 0
            overall_secs = time.time() - overall_start

            print(f"Processed     : {chunk_size:,}")
            print(f"Speed         : {speed:,.0f} products/sec")
            print(f"Progress      : {completed:,} / {total_products:,}  ({pct:.2f}%)")
            print(f"ETA           : {eta_secs / 60:.1f} min")
            print(f"Elapsed total : {overall_secs / 60:.1f} min")

            if device == "cuda":
                allocated = torch.cuda.memory_allocated(0)
                reserved  = torch.cuda.memory_reserved(0)
                print(f"GPU allocated : {allocated / 1024**3:.2f} GB")
                print(f"GPU reserved  : {reserved  / 1024**3:.2f} GB")

            # Cleanup
            del result, dense_vectors, chunk_texts
            if device == "cuda":
                torch.cuda.empty_cache()

        overall_elapsed = time.time() - overall_start
        print(f"\nEmbedding generation complete in {overall_elapsed / 60:.2f} minutes.")

    # --------------------------------------------------------
    # 8. FINAL VALIDATION
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FINAL EMBEDDING VALIDATION")
    print("=" * 70)

    # Re-open as read-only to confirm file integrity on disk.
    del embeddings
    embeddings = np.load(OUTPUT_FILE, mmap_mode="r")

    expected_shape = (total_products, _EXPECTED_DIM)
    print(f"Shape           : {embeddings.shape}")
    print(f"Expected        : {expected_shape}")

    if embeddings.shape != expected_shape:
        raise ValueError(
            f"Embedding shape mismatch: {embeddings.shape} != {expected_shape}"
        )

    # Spot-check first, middle, and last vectors.
    check_indices = [0, total_products // 2, total_products - 1]

    for idx in check_indices:
        vec = embeddings[idx]
        if not np.isfinite(vec).all():
            raise ValueError(
                f"Non-finite values (NaN/inf) at embedding index {idx}."
            )

    for idx in check_indices:
        norm = float(np.linalg.norm(embeddings[idx]))
        if not (0.99 < norm < 1.01):
            raise ValueError(
                f"Embedding {idx} is not unit-normalised (norm={norm:.4f}). "
                "ChromaDB cosine similarity will be incorrect."
            )

    print("[PASS] Shape check")
    print("[PASS] Finite-value check  (no NaN / inf)")
    print("[PASS] Unit-norm check     (L2 = 1.0 +/- 0.01)")

    # --------------------------------------------------------
    # 9. SAVE PARENT-ASIN MAPPING
    # --------------------------------------------------------

    print("\nSaving parent_asin mapping...")

    df[["parent_asin"]].to_csv(PARENT_ASIN_FILE, index=False)
    print(f"Saved           : {PARENT_ASIN_FILE}")

    mapping = pd.read_csv(PARENT_ASIN_FILE)
    if len(mapping) != total_products:
        raise ValueError(
            f"parent_asin CSV row count ({len(mapping):,}) "
            f"!= total products ({total_products:,})."
        )
    if not mapping["parent_asin"].reset_index(drop=True).equals(
        df["parent_asin"].reset_index(drop=True)
    ):
        raise ValueError(
            "parent_asin ordering in CSV does not match product DataFrame."
        )

    print("[PASS] Embedding <-> parent_asin alignment verified")

    # --------------------------------------------------------
    # 10. FINAL GPU MEMORY & SAMPLE
    # --------------------------------------------------------

    if device == "cuda":
        allocated = torch.cuda.memory_allocated(0)
        reserved  = torch.cuda.memory_reserved(0)
        print(f"\nFinal GPU allocated : {allocated / 1024**3:.2f} GB")
        print(f"Final GPU reserved  : {reserved  / 1024**3:.2f} GB")

    print("\nSample embedding (first 10 dims of row 0):")
    print(np.round(embeddings[0][:10], 6))

    # --------------------------------------------------------
    # 11. COMPLETE
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("BGE-M3 EMBEDDING PIPELINE COMPLETE")
    print("=" * 70)
    print(f"Products embedded   : {total_products:,}")
    print(f"Embedding dimension : {_EXPECTED_DIM}")
    print(f"Embeddings file     : {OUTPUT_FILE}")
    print(f"Mapping file        : {PARENT_ASIN_FILE}")
    print("\nNext step: load product embeddings and metadata into ChromaDB.")


if __name__ == "__main__":
    main()
