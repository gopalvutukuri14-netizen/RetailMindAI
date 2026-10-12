"""
Tests for product image extraction, schema integration, and FastAPI exposure.

Verifies:
- parse_image_url extracts real URLs, prefers MAIN variant, and handles edge cases.
- get_product_images retrieves image URLs from products_master.parquet without error.
- ResponseProduct schema supports image_url while preserving backward compatibility.
- POST /recommend serializes product images (valid URL as string, missing as null).
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.pipeline.product_images import parse_image_url, get_product_images, _IMAGE_CACHE
from backend.Agents.response.schema import ResponseProduct, ResponseResult


@pytest.fixture
def client():
    return TestClient(app)


def test_parse_image_url_standard():
    """Extracts large URL from typical Amazon image JSON."""
    raw = '[{"thumb": "https://m.media-amazon.com/thumb.jpg", "large": "https://m.media-amazon.com/large.jpg", "variant": "MAIN"}]'
    assert parse_image_url(raw) == "https://m.media-amazon.com/large.jpg"


def test_parse_image_url_prefers_main_variant():
    """Prefers MAIN variant over other variants."""
    raw = '[{"large": "https://m.media-amazon.com/pt01.jpg", "variant": "PT01"}, {"large": "https://m.media-amazon.com/main.jpg", "variant": "MAIN"}]'
    assert parse_image_url(raw) == "https://m.media-amazon.com/main.jpg"


def test_parse_image_url_fallback_to_hi_res_or_thumb():
    """Falls back to hi_res or thumb if large is not present."""
    raw_hi = '[{"hi_res": "https://m.media-amazon.com/hires.jpg", "variant": "MAIN"}]'
    assert parse_image_url(raw_hi) == "https://m.media-amazon.com/hires.jpg"

    raw_thumb = '[{"thumb": "https://m.media-amazon.com/thumb.jpg", "variant": "MAIN"}]'
    assert parse_image_url(raw_thumb) == "https://m.media-amazon.com/thumb.jpg"


def test_parse_image_url_missing_or_invalid():
    """Returns None for null, empty, non-json, or invalid image payloads."""
    assert parse_image_url(None) is None
    assert parse_image_url("") is None
    assert parse_image_url("[]") is None
    assert parse_image_url("invalid json") is None
    assert parse_image_url('{"not": "a list"}') is None
    assert parse_image_url('[{"large": "not-a-url"}]') is None


def test_get_product_images_known_asin():
    """Retrieves real image URL for a known ASIN in products_master.parquet."""
    # S10 ASIN B07RPHM14M
    images = get_product_images(["B07RPHM14M"])
    assert "B07RPHM14M" in images
    assert images["B07RPHM14M"] is not None
    assert images["B07RPHM14M"].startswith("https://m.media-amazon.com/")


def test_get_product_images_nonexistent_asin():
    """Returns None for an ASIN not present in the dataset."""
    images = get_product_images(["NON_EXISTENT_ASIN_99999"])
    assert images.get("NON_EXISTENT_ASIN_99999") is None


def test_response_product_backward_compatibility():
    """Instantiating ResponseProduct without image_url defaults to None."""
    p = ResponseProduct(
        asin="B001",
        title="Test Item",
        explanation="Explanation",
    )
    assert p.image_url is None
    data = p.model_dump()
    assert "image_url" in data
    assert data["image_url"] is None


def test_fastapi_recommend_exposes_image_url(client):
    """POST /recommend serializes valid image_url and null image_url in JSON."""
    result = ResponseResult(
        summary="Recommendations with images.",
        recommendations=[
            ResponseProduct(
                asin="B01",
                title="Product with Image",
                price_inr=19999.0,
                image_url="https://m.media-amazon.com/images/I/sample.jpg",
                explanation="Has image",
            ),
            ResponseProduct(
                asin="B02",
                title="Product without Image",
                price_inr=24999.0,
                image_url=None,
                explanation="Missing image",
            ),
        ],
        follow_up_suggestions=[],
    )

    with patch("backend.main.run_pipeline") as mock_pipeline:
        mock_pipeline.return_value = result

        resp = client.post("/recommend", json={"query": "test query", "top_k": 2})
        assert resp.status_code == 200
        data = resp.json()

        assert len(data["recommendations"]) == 2
        # Product 1 has image URL
        assert data["recommendations"][0]["image_url"] == "https://m.media-amazon.com/images/I/sample.jpg"
        # Product 2 has null image URL
        assert data["recommendations"][1]["image_url"] is None
        assert '"image_url":null' in resp.text
