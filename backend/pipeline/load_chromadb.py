"""
Load SmartPick product data into ChromaDB.

Inputs:
    data/products_master.parquet
    data/product_sentiment.parquet
    data/product_embeddings.npy
    data/product_embedding_parent_asins.csv

Output:
    data/chromadb/

Collection:
    retail_products

Important:
    - Product ID = parent_asin
    - Embedding dimension = 1024
    - All 250,000 products are loaded
    - Missing prices remain missing; they are NOT converted to 0
"""

from pathlib import Path
import json
import sys
import time

import chromadb
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"

PRODUCTS_FILE = DATA_DIR / "products_master.parquet"
SENTIMENT_FILE = DATA_DIR / "product_sentiment.parquet"
EMBEDDINGS_FILE = DATA_DIR / "product_embeddings.npy"
MAPPING_FILE = DATA_DIR / "product_embedding_parent_asins.csv"

CHROMA_DIR = DATA_DIR / "chromadb"

COLLECTION_NAME = "retail_products"


# ============================================================
# SETTINGS
# ============================================================

BATCH_SIZE = 5_000
EXPECTED_PRODUCTS = 250_000
EXPECTED_EMBEDDING_DIM = 1024

# Set this to True only when you intentionally want to rebuild.
# Since you already deleted the old ChromaDB, True is safe here.
RECREATE_COLLECTION = True


# ============================================================
# HELPERS
# ============================================================

def print_header(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def clean_string(value):
    """Convert a value to a Chroma-safe string."""
    if value is None:
        return ""

    if isinstance(value, float) and np.isnan(value):
        return ""

    return str(value).strip()


def clean_number(value):
    """
    Convert numeric value to a Python float.

    Returns None for missing/invalid values.
    """
    if value is None:
        return None

    try:
        value = float(value)

        if np.isnan(value) or np.isinf(value):
            return None

        return value

    except (ValueError, TypeError):
        return None


def clean_int(value):
    """
    Convert numeric value to Python int.

    Returns None for missing/invalid values.
    """
    if value is None:
        return None

    try:
        value = float(value)

        if np.isnan(value) or np.isinf(value):
            return None

        return int(value)

    except (ValueError, TypeError):
        return None


def clean_metadata_value(value):
    """
    Chroma metadata supports scalar values.

    Convert:
        dict/list/tuple -> JSON string
        numpy scalar    -> Python scalar
        NaN              -> None
    """

    if value is None:
        return None

    if isinstance(value, float):
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating,)):
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)

    if isinstance(value, (dict, list, tuple)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)

    return str(value)


def first_existing_column(df, candidates):
    """Return the first column from candidates that exists."""
    for column in candidates:
        if column in df.columns:
            return column

    return None


# ============================================================
# VALIDATE FILES
# ============================================================

def validate_files():
    print_header("Checking input files")

    required_files = [
        PRODUCTS_FILE,
        SENTIMENT_FILE,
        EMBEDDINGS_FILE,
        MAPPING_FILE,
    ]

    for file_path in required_files:
        if not file_path.exists():
            print(f"[ERROR] Missing file:")
            print(f"        {file_path}")
            sys.exit(1)

        size_mb = file_path.stat().st_size / (1024 * 1024)

        print(f"[OK] {file_path.name:<40} {size_mb:,.1f} MB")


# ============================================================
# LOAD DATA
# ============================================================

def load_data():
    print_header("Loading product metadata")

    products = pd.read_parquet(PRODUCTS_FILE)

    print(f"Products loaded: {len(products):,}")
    print(f"Columns: {len(products.columns)}")

    if "parent_asin" not in products.columns:
        print("[ERROR] products_master.parquet does not contain parent_asin")
        sys.exit(1)

    products["parent_asin"] = products["parent_asin"].astype(str).str.strip()

    # Remove completely invalid IDs.
    products = products[
        products["parent_asin"].notna()
        & (products["parent_asin"] != "")
        & (products["parent_asin"].str.lower() != "nan")
    ].copy()

    # Check duplicate IDs.
    duplicate_count = products["parent_asin"].duplicated().sum()

    if duplicate_count > 0:
        print(
            f"[ERROR] Found {duplicate_count:,} duplicate parent_asin values."
        )
        sys.exit(1)

    print("[OK] parent_asin is unique")

    print_header("Loading sentiment data")

    sentiment = pd.read_parquet(SENTIMENT_FILE)

    print(f"Sentiment rows: {len(sentiment):,}")
    print(f"Sentiment columns: {len(sentiment.columns)}")

    if "parent_asin" not in sentiment.columns:
        print("[ERROR] product_sentiment.parquet does not contain parent_asin")
        sys.exit(1)

    sentiment["parent_asin"] = (
        sentiment["parent_asin"].astype(str).str.strip()
    )

    duplicate_sentiment = sentiment["parent_asin"].duplicated().sum()

    if duplicate_sentiment > 0:
        print(
            f"[WARNING] Sentiment contains "
            f"{duplicate_sentiment:,} duplicate parent_asin values."
        )

        # Keep first row if duplicate sentiment exists.
        sentiment = sentiment.drop_duplicates(
            subset=["parent_asin"],
            keep="first",
        )

    print_header("Loading embeddings")

    embeddings = np.load(
        EMBEDDINGS_FILE,
        mmap_mode="r",
    )

    print(f"Embedding shape: {embeddings.shape}")

    if embeddings.ndim != 2:
        print("[ERROR] Embeddings must be a 2D matrix.")
        sys.exit(1)

    if embeddings.shape[1] != EXPECTED_EMBEDDING_DIM:
        print(
            f"[ERROR] Expected embedding dimension "
            f"{EXPECTED_EMBEDDING_DIM}, "
            f"got {embeddings.shape[1]}"
        )
        sys.exit(1)

    if embeddings.shape[0] != len(products):
        print(
            f"[ERROR] Embedding count ({embeddings.shape[0]:,}) "
            f"does not match product count ({len(products):,})."
        )
        sys.exit(1)

    print("[OK] Embedding dimensions are correct")

    print_header("Loading embedding → parent_asin mapping")

    mapping = pd.read_csv(MAPPING_FILE)

    print(f"Mapping rows: {len(mapping):,}")
    print(f"Mapping columns: {list(mapping.columns)}")

    # Detect mapping column.
    mapping_id_column = first_existing_column(
        mapping,
        [
            "parent_asin",
            "parent_asin_id",
            "id",
        ],
    )

    if mapping_id_column is None:
        print(
            "[ERROR] Could not find parent_asin column "
            "in embedding mapping."
        )
        sys.exit(1)

    mapping_ids = (
        mapping[mapping_id_column]
        .astype(str)
        .str.strip()
        .tolist()
    )

    if len(mapping_ids) != embeddings.shape[0]:
        print(
            f"[ERROR] Mapping count ({len(mapping_ids):,}) "
            f"does not match embeddings "
            f"({embeddings.shape[0]:,})."
        )
        sys.exit(1)

    # Validate mapping IDs against product IDs.
    product_ids = set(products["parent_asin"])

    missing_products = [
        pid for pid in mapping_ids
        if pid not in product_ids
    ]

    if missing_products:
        print(
            f"[ERROR] {len(missing_products):,} embedding IDs "
            f"are missing from products_master."
        )
        print("Example:", missing_products[:5])
        sys.exit(1)

    if len(set(mapping_ids)) != len(mapping_ids):
        print("[ERROR] Duplicate IDs found in embedding mapping.")
        sys.exit(1)

    print("[OK] Embedding mapping validated")

    # IMPORTANT:
    # Reorder products according to embedding mapping.
    #
    # This guarantees:
    #
    # embeddings[i]
    #       ↓
    # mapping_ids[i]
    #       ↓
    # products row for mapping_ids[i]
    #
    product_lookup = products.set_index("parent_asin", drop=False)

    ordered_products = product_lookup.loc[mapping_ids].reset_index(
        drop=True
    )

    # Sanity check.
    if not (
        ordered_products["parent_asin"].astype(str).tolist()
        == mapping_ids
    ):
        print("[ERROR] Product/embedding alignment failed.")
        sys.exit(1)

    print("[OK] Embedding ↔ product alignment validated")

    return ordered_products, sentiment, embeddings, mapping_ids


# ============================================================
# BUILD SENTIMENT LOOKUP
# ============================================================

def prepare_sentiment(sentiment):
    """
    Prepare sentiment dataframe for joining.

    Only columns that are useful for retrieval/ranking are retained.
    """

    print_header("Preparing product sentiment")

    sentiment = sentiment.copy()

    # Keep all columns because your current product_sentiment.parquet
    # contains the 19 aspect sentiment fields.
    sentiment = sentiment.drop_duplicates(
        subset=["parent_asin"],
        keep="first",
    )

    sentiment_lookup = sentiment.set_index("parent_asin")

    print(f"Unique sentiment products: {len(sentiment_lookup):,}")

    return sentiment_lookup


# ============================================================
# BUILD CHROMA METADATA
# ============================================================

def build_metadata(product_row, sentiment_row=None):
    """
    Create ChromaDB metadata for one product.
    """

    parent_asin = clean_string(product_row.get("parent_asin"))

    title = clean_string(product_row.get("title"))
    brand = clean_string(product_row.get("brand"))
    category = clean_string(product_row.get("main_category"))

    price_usd = clean_number(product_row.get("price"))
    price_inr = clean_number(product_row.get("price_inr"))

    average_rating = clean_number(
        product_row.get("average_rating")
    )

    rating_number = clean_int(
        product_row.get("rating_number")
    )

    # --------------------------------------------------------
    # Sentiment
    # --------------------------------------------------------

    review_count = None
    average_sentiment = None
    positive_ratio = None
    negative_ratio = None
    review_confidence = None

    if sentiment_row is not None:

        review_count = clean_int(
            sentiment_row.get("review_count")
        )

        average_sentiment = clean_number(
            sentiment_row.get("average_sentiment")
        )

        positive_ratio = clean_number(
            sentiment_row.get("positive_ratio")
        )

        negative_ratio = clean_number(
            sentiment_row.get("negative_ratio")
        )

        review_confidence = clean_number(
            sentiment_row.get("review_confidence")
        )

    # If sentiment data has average_rating and the product
    # metadata does not, use sentiment's value.
    if average_rating is None and sentiment_row is not None:
        average_rating = clean_number(
            sentiment_row.get("average_rating")
        )

    # --------------------------------------------------------
    # Core metadata
    # --------------------------------------------------------

    metadata = {
        "parent_asin": parent_asin,
        "title": title,
        "brand": brand,
        "main_category": category,

        # Keep original USD price.
        # Missing remains absent rather than 0.
        "price_usd": price_usd,

        # INR converted price.
        "price_inr": price_inr,

        "price_currency": clean_string(
            product_row.get("price_currency")
        ),

        "price_source": clean_string(
            product_row.get("price_source")
        ),

        "average_rating": average_rating,
        "rating_number": rating_number,

        "review_count": review_count,
        "average_sentiment": average_sentiment,
        "positive_ratio": positive_ratio,
        "negative_ratio": negative_ratio,
        "review_confidence": review_confidence,
    }

    # --------------------------------------------------------
    # Aspect sentiment
    # --------------------------------------------------------

    aspect_columns = [
        "appearance",
        "battery",
        "build_quality",
        "camera",
        "charging",
        "comfort",
        "connectivity",
        "design",
        "display",
        "durability",
        "ease_of_use",
        "fit",
        "material",
        "performance",
        "quality",
        "size",
        "software",
        "sound_quality",
        "value",
    ]

    for aspect in aspect_columns:

        value = None

        if sentiment_row is not None:
            value = clean_number(
                sentiment_row.get(aspect)
            )

        metadata[f"sentiment_{aspect}"] = value

    # --------------------------------------------------------
    # Remove None values
    #
    # Chroma metadata should not contain Python None values.
    # Missing numeric values are simply omitted.
    # --------------------------------------------------------

    metadata = {
        key: value
        for key, value in metadata.items()
        if value is not None
    }

    return metadata


# ============================================================
# BUILD DOCUMENT
# ============================================================

def build_document(product_row):
    """
    Document stored alongside the embedding.

    The embedding was generated from embedding_text.
    We therefore prefer embedding_text here as the searchable
    product representation.
    """

    embedding_text = product_row.get("embedding_text")

    if embedding_text is not None:
        text = str(embedding_text).strip()

        if text and text.lower() != "nan":
            return text

    # Fallback if embedding_text is unavailable.
    title = clean_string(product_row.get("title"))
    brand = clean_string(product_row.get("brand"))
    category = clean_string(product_row.get("main_category"))

    parts = []

    if title:
        parts.append(title)

    if brand:
        parts.append(f"Brand: {brand}")

    if category:
        parts.append(f"Category: {category}")

    return ". ".join(parts)


# ============================================================
# CREATE CHROMA COLLECTION
# ============================================================

def create_collection():
    print_header("Creating ChromaDB")

    CHROMA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"ChromaDB path:")
    print(f"  {CHROMA_DIR}")

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    existing_collections = [
        collection.name
        for collection in client.list_collections()
    ]

    print(f"Existing collections: {existing_collections}")

    if COLLECTION_NAME in existing_collections:

        if RECREATE_COLLECTION:
            print(
                f"[INFO] Deleting existing collection: "
                f"{COLLECTION_NAME}"
            )

            client.delete_collection(
                name=COLLECTION_NAME
            )

        else:
            print(
                f"[INFO] Using existing collection: "
                f"{COLLECTION_NAME}"
            )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "description": (
                "SmartPick product collection "
                "using BGE-M3 embeddings"
            ),
            "embedding_model": "BAAI/bge-m3",
            "embedding_dimension": EXPECTED_EMBEDDING_DIM,
            "id_field": "parent_asin",
            "dataset_size": EXPECTED_PRODUCTS,
        },
    )

    print(f"[OK] Collection ready: {COLLECTION_NAME}")

    return client, collection


# ============================================================
# INSERT PRODUCTS
# ============================================================

def insert_products(
    collection,
    products,
    sentiment_lookup,
    embeddings,
    mapping_ids,
):
    print_header("Loading products into ChromaDB")

    total = len(products)

    print(f"Total products: {total:,}")
    print(f"Batch size: {BATCH_SIZE:,}")
    print()

    start_time = time.time()

    inserted = 0
    products_with_price = 0
    products_without_price = 0
    products_with_sentiment = 0

    for start in range(0, total, BATCH_SIZE):

        end = min(
            start + BATCH_SIZE,
            total,
        )

        batch_products = products.iloc[start:end]

        ids = []
        batch_embeddings = []
        documents = []
        metadatas = []

        for local_index, (_, product_row) in enumerate(
            batch_products.iterrows()
        ):

            global_index = start + local_index

            parent_asin = mapping_ids[global_index]

            # ------------------------------------------------
            # Validate ID alignment one more time.
            # ------------------------------------------------

            product_parent_asin = str(
                product_row["parent_asin"]
            ).strip()

            if product_parent_asin != parent_asin:
                print(
                    "\n[ERROR] ID alignment mismatch!"
                )
                print(
                    f"Embedding index: {global_index}"
                )
                print(
                    f"Mapping ID: {parent_asin}"
                )
                print(
                    f"Product ID: {product_parent_asin}"
                )
                sys.exit(1)

            # ------------------------------------------------
            # Embedding
            # ------------------------------------------------

            vector = np.asarray(
                embeddings[global_index],
                dtype=np.float32,
            )

            if vector.shape != (
                EXPECTED_EMBEDDING_DIM,
            ):
                print(
                    "\n[ERROR] Invalid embedding shape:"
                    f" {vector.shape}"
                )
                sys.exit(1)

            if not np.all(np.isfinite(vector)):
                print(
                    "\n[ERROR] Embedding contains "
                    "NaN or infinite values."
                )
                sys.exit(1)

            # ------------------------------------------------
            # Sentiment
            # ------------------------------------------------

            sentiment_row = None

            if parent_asin in sentiment_lookup.index:
                sentiment_row = sentiment_lookup.loc[
                    parent_asin
                ]

                products_with_sentiment += 1

            # ------------------------------------------------
            # Metadata
            # ------------------------------------------------

            metadata = build_metadata(
                product_row,
                sentiment_row,
            )

            # ------------------------------------------------
            # Document
            # ------------------------------------------------

            document = build_document(
                product_row
            )

            # ------------------------------------------------
            # Price statistics
            # ------------------------------------------------

            price_inr = clean_number(
                product_row.get("price_inr")
            )

            if price_inr is None:
                products_without_price += 1
            else:
                products_with_price += 1

            ids.append(parent_asin)
            batch_embeddings.append(
                vector.tolist()
            )
            documents.append(document)
            metadatas.append(metadata)

        # ----------------------------------------------------
        # Add batch
        # ----------------------------------------------------

        collection.add(
            ids=ids,
            embeddings=batch_embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        inserted = end

        elapsed = time.time() - start_time

        rate = inserted / elapsed if elapsed > 0 else 0

        remaining = total - inserted

        eta_seconds = (
            remaining / rate
            if rate > 0
            else 0
        )

        percent = (
            inserted / total * 100
        )

        print(
            f"[{inserted:>7,}/{total:,}] "
            f"{percent:6.2f}% | "
            f"{rate:,.0f} products/sec | "
            f"ETA {eta_seconds / 60:.1f} min"
        )

    elapsed = time.time() - start_time

    print()
    print("[OK] ChromaDB insertion complete")
    print(f"Inserted: {inserted:,}")
    print(f"Time: {elapsed / 60:.2f} minutes")

    print()
    print("Price statistics:")
    print(
        f"  With price:    {products_with_price:,}"
    )
    print(
        f"  Without price: {products_without_price:,}"
    )

    print()
    print("Sentiment statistics:")
    print(
        f"  With sentiment: "
        f"{products_with_sentiment:,}"
    )

    return inserted


# ============================================================
# VALIDATE COLLECTION
# ============================================================

def validate_collection(collection):
    print_header("Validating ChromaDB")

    count = collection.count()

    print(f"Collection count: {count:,}")

    if count != EXPECTED_PRODUCTS:
        print(
            f"[ERROR] Expected "
            f"{EXPECTED_PRODUCTS:,} products, "
            f"but ChromaDB contains {count:,}."
        )
        sys.exit(1)

    print(
        f"[PASS] Collection contains exactly "
        f"{EXPECTED_PRODUCTS:,} products"
    )

    # --------------------------------------------------------
    # Sample records
    # --------------------------------------------------------

    sample_size = min(5, count)

    sample = collection.get(
        limit=sample_size,
        include=[
            "metadatas",
            "documents",
            "embeddings",
        ],
    )

    print()
    print(f"Sample records: {sample_size}")

    if sample["ids"]:

        for i, product_id in enumerate(
            sample["ids"]
        ):

            metadata = sample["metadatas"][i]

            print()
            print(f"  ID: {product_id}")
            print(
                f"  Title: "
                f"{metadata.get('title', '')[:100]}"
            )
            print(
                f"  Brand: "
                f"{metadata.get('brand', '')}"
            )
            print(
                f"  Category: "
                f"{metadata.get('main_category', '')}"
            )
            print(
                f"  Price INR: "
                f"{metadata.get('price_inr', 'N/A')}"
            )

    # --------------------------------------------------------
    # Verify embedding dimension.
    # --------------------------------------------------------

    if sample.get("embeddings") is not None and len(sample["embeddings"]) > 0:

        first_embedding = np.asarray(
            sample["embeddings"][0]
        )

        print()
        print(
            f"Sample embedding dimension: "
            f"{first_embedding.shape[0]}"
        )

        if first_embedding.shape[0] != EXPECTED_EMBEDDING_DIM:
            print(
                "[ERROR] ChromaDB embedding dimension "
                "is incorrect."
            )
            sys.exit(1)

        print(
            "[PASS] Embedding dimension = 1024"
        )

    # --------------------------------------------------------
    # Verify required metadata.
    # --------------------------------------------------------

    required_metadata = [
        "parent_asin",
        "title",
        "brand",
        "main_category",
    ]

    missing_metadata = []

    if sample["metadatas"]:

        for field in required_metadata:

            if field not in sample["metadatas"][0]:
                missing_metadata.append(field)

    if missing_metadata:

        print(
            "[ERROR] Missing metadata fields:"
        )
        print(missing_metadata)
        sys.exit(1)

    print(
        "[PASS] Required metadata fields present"
    )


# ============================================================
# SEMANTIC SEARCH SMOKE TEST
# ============================================================

def semantic_search_test(collection):
    print_header("Semantic Search Smoke Test")

    test_query = (
        "best smartphone with good camera "
        "battery and performance"
    )

    print(f"Query: {test_query}")

    # IMPORTANT:
    # We do NOT generate a query embedding here.
    #
    # ChromaDB cannot automatically use the BGE-M3
    # embedding model unless an embedding function is
    # configured for the collection.
    #
    # Therefore this smoke test only runs if a query
    # embedding function is available.
    #
    # For now, we validate the collection itself.
    print()
    print(
        "[INFO] ChromaDB collection is ready for "
        "external BGE-M3 query embeddings."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    overall_start = time.time()

    print()
    print("=" * 70)
    print("SmartPick - ChromaDB Loader")
    print("=" * 70)

    print()
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Data directory: {DATA_DIR}")
    print(f"ChromaDB directory: {CHROMA_DIR}")
    print(f"Collection: {COLLECTION_NAME}")

    # --------------------------------------------------------
    # Step 1
    # --------------------------------------------------------

    validate_files()

    # --------------------------------------------------------
    # Step 2
    # --------------------------------------------------------

    (
        products,
        sentiment,
        embeddings,
        mapping_ids,
    ) = load_data()

    # --------------------------------------------------------
    # Step 3
    # --------------------------------------------------------

    sentiment_lookup = prepare_sentiment(
        sentiment
    )

    # --------------------------------------------------------
    # Step 4
    # --------------------------------------------------------

    client, collection = create_collection()

    # --------------------------------------------------------
    # Step 5
    # --------------------------------------------------------

    inserted = insert_products(
        collection=collection,
        products=products,
        sentiment_lookup=sentiment_lookup,
        embeddings=embeddings,
        mapping_ids=mapping_ids,
    )

    # --------------------------------------------------------
    # Step 6
    # --------------------------------------------------------

    validate_collection(collection)

    # --------------------------------------------------------
    # Step 7
    # --------------------------------------------------------

    semantic_search_test(collection)

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    total_time = time.time() - overall_start

    print()
    print("=" * 70)
    print("CHROMADB LOAD COMPLETE")
    print("=" * 70)

    print()
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Products:   {inserted:,}")
    print(f"Embeddings: {EXPECTED_EMBEDDING_DIM}-dim BGE-M3")
    print(f"Database:   {CHROMA_DIR}")
    print(
        f"Total time: {total_time / 60:.2f} minutes"
    )

    print()
    print("Next step:")
    print(
        "Update the Retrieval Agent to use this "
        "new ChromaDB collection."
    )

    print()


if __name__ == "__main__":
    main()