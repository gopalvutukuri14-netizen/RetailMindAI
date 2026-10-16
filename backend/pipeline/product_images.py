"""
Product image lookup service for SmartPick.

Extracts real product image URLs from data/products_master.parquet without
modifying ChromaDB, embeddings, or ranking weights.
"""

from typing import Optional, Any
from pathlib import Path
import json
import logging
import pyarrow.dataset as ds

logger = logging.getLogger(__name__)

DATA_PATH = Path("data/products_master.parquet")

# In-memory cache to avoid repeated parquet scans for frequent/recent ASINs
_IMAGE_CACHE: dict[str, Optional[str]] = {}


def parse_image_url(images_raw: Any) -> Optional[str]:
    """
    Parse the raw 'images' column value and extract the best image URL.

    The dataset stores images as a JSON string of objects containing
    'large', 'hi_res', 'thumb', and 'variant'.
    Prefers the 'MAIN' variant and high-resolution/large image URL.
    """
    if not images_raw:
        return None

    items = None
    if isinstance(images_raw, str):
        try:
            items = json.loads(images_raw)
        except Exception:
            return None
    elif isinstance(images_raw, list):
        items = images_raw

    if not isinstance(items, list) or len(items) == 0:
        return None

    # Prefer 'MAIN' variant if present
    main_items = [
        img for img in items
        if isinstance(img, dict) and img.get("variant") == "MAIN"
    ]
    chosen = main_items[0] if main_items else items[0]

    if not isinstance(chosen, dict):
        return None

    url = chosen.get("large") or chosen.get("hi_res") or chosen.get("thumb")
    if isinstance(url, str) and url.strip().startswith("http"):
        return url.strip()

    return None


def get_product_images(asins: list[str]) -> dict[str, Optional[str]]:
    """
    Look up image URLs for a list of parent ASINs.

    Returns a dict mapping {asin: image_url_or_none}.
    """
    if not asins:
        return {}

    result: dict[str, Optional[str]] = {}
    missing_asins = []

    for asin in asins:
        if asin in _IMAGE_CACHE:
            result[asin] = _IMAGE_CACHE[asin]
        else:
            missing_asins.append(asin)

    if not missing_asins:
        return result

    if not DATA_PATH.exists():
        logger.warning(
            "products_master.parquet not found at %s. Image lookup skipped.",
            DATA_PATH,
        )
        for asin in missing_asins:
            result[asin] = None
            _IMAGE_CACHE[asin] = None
        return result

    try:
        dataset = ds.dataset(str(DATA_PATH), format="parquet")
        filter_expr = ds.field("parent_asin").isin(missing_asins)
        table = dataset.to_table(
            filter=filter_expr,
            columns=["parent_asin", "images"],
        ).to_pydict()

        found_asins = table.get("parent_asin", [])
        found_images = table.get("images", [])

        mapping = {
            asin: parse_image_url(raw)
            for asin, raw in zip(found_asins, found_images)
        }

        for asin in missing_asins:
            img_url = mapping.get(asin)
            result[asin] = img_url
            _IMAGE_CACHE[asin] = img_url

    except Exception as exc:
        logger.error("Failed to query product images from parquet: %s", exc)
        for asin in missing_asins:
            result[asin] = None
            _IMAGE_CACHE[asin] = None

    return result


def get_product_image(asin: str) -> Optional[str]:
    """Look up image URL for a single parent ASIN."""
    return get_product_images([asin]).get(asin)
