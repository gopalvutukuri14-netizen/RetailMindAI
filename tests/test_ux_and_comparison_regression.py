"""
Regression tests for UX Improvements, Category Examples,
Performance Instrumentation, and Structured Product Comparison Experience.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

os.environ["TESTING"] = "true"

from backend.main import app
from backend.Agents.response.schema import ResponseResult, ResponseProduct, ComparisonData, ComparisonRow
from backend.orchestrator.comparison_helper import (
    extract_product_specs,
    select_two_products_to_compare,
    build_category_comparison_data,
)
from backend.orchestrator.nodes import context_response_node, general_response_node, out_of_scope_node
from backend.orchestrator.state import PipelineState


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Category Context & API forwarding regression tests
# ---------------------------------------------------------------------------

def test_recommend_endpoint_accepts_and_forwards_category(client):
    """When category is provided in /recommend, it is passed to run_pipeline."""
    sample_result = ResponseResult(
        summary="Phones for you",
        recommendations=[],
        follow_up_suggestions=[],
    )

    with patch("backend.main.run_pipeline") as mock_pipeline:
        mock_pipeline.return_value = sample_result

        response = client.post(
            "/recommend",
            json={
                "query": "best smartphone with 8GB RAM",
                "user_id": "test_user",
                "top_k": 5,
                "category": "Cell Phones & Accessories",
            },
        )

        assert response.status_code == 200
        mock_pipeline.assert_called_once_with(
            raw_query="best smartphone with 8GB RAM",
            user_id="test_user",
            top_k=5,
            previous_products=None,
            category="Cell Phones & Accessories",
        )


def test_recommend_endpoint_omits_category_when_not_provided(client):
    """When category is None, run_pipeline is called without category kwarg."""
    sample_result = ResponseResult(
        summary="Results",
        recommendations=[],
        follow_up_suggestions=[],
    )

    with patch("backend.main.run_pipeline") as mock_pipeline:
        mock_pipeline.return_value = sample_result

        response = client.post(
            "/recommend",
            json={
                "query": "wireless noise cancelling headphones",
                "user_id": "test_user",
                "top_k": 3,
            },
        )

        assert response.status_code == 200
        mock_pipeline.assert_called_once_with(
            raw_query="wireless noise cancelling headphones",
            user_id="test_user",
            top_k=3,
            previous_products=None,
        )


# ---------------------------------------------------------------------------
# 2. Comparison Helper & Spec Extraction tests
# ---------------------------------------------------------------------------

def test_extract_product_specs_for_phone():
    """Phone specifications (RAM, Storage, Battery) are extracted or marked safely."""
    prod = {
        "title": "Samsung Galaxy S23 5G 128GB 8GB RAM Smartphone 5000mAh",
        "category": "Cell Phones & Accessories",
        "description": "Crisp 6.1 AMOLED display with 50MP triple camera system",
    }
    specs = extract_product_specs(prod, "Cell Phones & Accessories")
    assert "RAM" in specs
    assert specs["RAM"] == "8GB"
    assert "Storage" in specs
    assert specs["Storage"] == "128GB"
    assert "Battery" in specs
    assert "5000" in specs["Battery"]
    assert "mAh" in specs["Battery"]


def test_extract_product_specs_honest_missing_values():
    """Missing specifications are not hallucinated."""
    prod = {
        "title": "Basic Simple Phone Stand",
        "category": "Cell Phones & Accessories",
        "description": "",
    }
    specs = extract_product_specs(prod, "Cell Phones & Accessories")
    assert specs.get("RAM") is None
    assert specs.get("Storage") is None
    assert specs.get("Battery") is None


def test_select_two_products_defaults_to_top_two():
    """When user requests general comparison, top two products are chosen."""
    products = [
        {"asin": "A1", "title": "Product One", "price_inr": 1000},
        {"asin": "A2", "title": "Product Two", "price_inr": 2000},
        {"asin": "A3", "title": "Product Three", "price_inr": 3000},
    ]
    p1, p2 = select_two_products_to_compare(products, "Compare the top two products")
    assert p1["asin"] == "A1"
    assert p2["asin"] == "A2"


def test_select_two_products_specific_indices():
    """When user asks for 1st and 3rd products, those specific products are chosen."""
    products = [
        {"asin": "A1", "title": "Product One", "price_inr": 1000},
        {"asin": "A2", "title": "Product Two", "price_inr": 2000},
        {"asin": "A3", "title": "Product Three", "price_inr": 3000},
    ]
    p1, p2 = select_two_products_to_compare(products, "compare the first and third products")
    assert p1["asin"] == "A1"
    assert p2["asin"] == "A3"


def test_build_category_comparison_data_honest_missing_price_and_specs():
    """Comparison table marks missing prices and specs honestly with 'Not available in catalog'."""
    p1 = {
        "asin": "B001",
        "title": "Noise Cancelling Headphones Pro",
        "brand": "SoundBrand",
        "category": "Electronics",
        "price_inr": None,  # Missing price
        "rating": 4.5,
        "sentiment_score": 0.85,
    }
    p2 = {
        "asin": "B002",
        "title": "Everyday Bluetooth Headset 40h Battery",
        "brand": "DailyAudio",
        "category": "Electronics",
        "price_inr": 2999.0,
        "rating": 4.1,
        "sentiment_score": 0.72,
    }

    comp_data = build_category_comparison_data(p1, p2, "Electronics")
    assert isinstance(comp_data, ComparisonData)
    assert comp_data.heading.startswith("Comparing") or "Comparison" in comp_data.heading
    assert comp_data.product_a_asin == "B001"
    assert comp_data.product_b_asin == "B002"

    # Check rows
    rows_by_aspect = {r.aspect: r for r in comp_data.rows}
    assert "Price" in rows_by_aspect
    assert rows_by_aspect["Price"].product_a == "Price unavailable"
    assert "₹2,999" in rows_by_aspect["Price"].product_b

    # Check specs honest fallback
    assert "Brand" in rows_by_aspect
    assert rows_by_aspect["Brand"].product_a == "SoundBrand"
    assert rows_by_aspect["Brand"].product_b == "DailyAudio"

    # Conclusion must be present and non-empty
    assert len(comp_data.conclusion) > 10


# ---------------------------------------------------------------------------
# 3. Context Response Node (Comparison flow)
# ---------------------------------------------------------------------------

def test_context_response_node_generates_structured_comparison():
    """Context response node on comparison query produces ComparisonData and 2 cards."""
    previous_products = [
        {
            "asin": "B01PHONE",
            "title": "Smartphone Alpha 128GB 8GB RAM 5000mAh",
            "brand": "AlphaBrand",
            "category": "Cell Phones & Accessories",
            "price_inr": 18999.0,
            "rating": 4.4,
            "sentiment_score": 0.8,
            "explanation": "Great performance phone.",
        },
        {
            "asin": "B02PHONE",
            "title": "Smartphone Beta 256GB 12GB RAM 4500mAh",
            "brand": "BetaBrand",
            "category": "Cell Phones & Accessories",
            "price_inr": 24999.0,
            "rating": 4.6,
            "sentiment_score": 0.88,
            "explanation": "High capacity gaming phone.",
        },
    ]

    mock_qu = MagicMock()
    mock_qu.intent = "comparison"
    mock_qu.category = "Cell Phones & Accessories"

    state: PipelineState = {
        "raw_query": "Compare these two phones",
        "user_id": "test_shopper",
        "top_k": 2,
        "previous_products": previous_products,
        "query_understanding": mock_qu,
    }

    result_state = context_response_node(state)
    assert "response_result" in result_state
    resp: ResponseResult = result_state["response_result"]

    assert resp.comparison is not None
    assert len(resp.recommendations) == 2
    assert resp.recommendations[0].asin == "B01PHONE"
    assert resp.recommendations[1].asin == "B02PHONE"
    assert "Comparing" in resp.comparison.heading or "Comparison" in resp.comparison.heading
    assert any(row.aspect == "RAM" for row in resp.comparison.rows)
    assert len(resp.comparison.conclusion) > 0


# ---------------------------------------------------------------------------
# 4. Latency Logging & Secret Safety
# ---------------------------------------------------------------------------

def test_timing_logs_do_not_leak_secrets(caplog):
    """Timing logs must log stage latencies without printing auth secrets or passwords."""
    import logging

    with caplog.at_level(logging.INFO):
        client = TestClient(app)
        # Call health check
        client.get("/health")

        # Verify no secret tokens or keys are present in logs
        for record in caplog.records:
            msg = record.getMessage()
            assert "brevo_api_key" not in msg.lower()
            assert "gemini_api_key" not in msg.lower()
            assert "password" not in msg.lower()
            assert "bearer" not in msg.lower()


# ---------------------------------------------------------------------------
# 5. SmartPick Assistant Introduction & Greeting Regression Tests
# ---------------------------------------------------------------------------

def test_general_response_node_greeting_uses_smartpick():
    """Generic greeting directly in general_response_node returns the canonical SmartPick introduction."""
    state: PipelineState = {
        "raw_query": "hello",
        "user_id": "guest_user",
        "top_k": 5,
    }
    result_state = general_response_node(state)
    assert "response_result" in result_state
    res: ResponseResult = result_state["response_result"]
    assert "SmartPick" in res.summary
    assert "RetailMind" not in res.summary
    assert "Hello! I am SmartPick, your AI shopping assistant" in res.summary


def test_out_of_scope_node_uses_smartpick():
    """Out-of-scope response introduces supported categories using SmartPick."""
    mock_qu = MagicMock()
    mock_qu.category = None

    state: PipelineState = {
        "raw_query": "can I buy real estate?",
        "user_id": "test_user",
        "top_k": 5,
        "query_understanding": mock_qu,
    }
    result_state = out_of_scope_node(state)
    assert "response_result" in result_state
    res: ResponseResult = result_state["response_result"]
    assert "SmartPick currently supports six product categories" in res.summary
    assert "RetailMind" not in res.summary


def test_generic_greeting_recommend_endpoint_guest_user(client):
    """POST /recommend with greeting returns SmartPick introduction for guest user."""
    response = client.post("/recommend", json={"query": "hello", "user_id": "anonymous"})
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "SmartPick" in data["summary"]
    assert "RetailMind" not in data["summary"]
    assert "Hello! I am SmartPick, your AI shopping assistant" in data["summary"]


def test_generic_greeting_recommend_endpoint_authenticated_user(client):
    """POST /recommend with greeting returns SmartPick introduction for authenticated user."""
    from backend.auth.security import create_access_token
    token = create_access_token(user_id="auth_shopper_1", username="shopper1", email="shopper1@example.com")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/recommend", headers=headers, json={"query": "hi", "user_id": "anonymous"})
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "SmartPick" in data["summary"]
    assert "RetailMind" not in data["summary"]
    assert "Hello! I am SmartPick, your AI shopping assistant" in data["summary"]

