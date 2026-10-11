"""
Tests for Stage E: FastAPI endpoints, request validation (4xx), and error sanitization (500).

Verifies:
- GET / returns 200 running message.
- GET /health returns 200 healthy status.
- POST /recommend validates input: top_k < 1 or > 20 returns 422 Unprocessable Entity.
- POST /recommend returns 200 with serialized ResponseResult when pipeline succeeds.
- POST /recommend sanitizes 500 errors and does not leak internal exception details.
- POST /understand operates lazily and sanitizes error on failure.
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.Agents.response.schema import ResponseResult, ResponseProduct
from backend.Agents.query_understanding.schema import (
    QueryUnderstanding,
    Intent,
    RetailCategory,
    BrandPreferences,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_root_endpoint(client):
    """GET / returns status 200 and startup message."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "RetailMind AI backend is running"}


def test_health_endpoint(client):
    """GET /health returns status 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_recommend_validation_top_k_too_low(client):
    """POST /recommend with top_k < 1 returns 422 Unprocessable Entity."""
    response = client.post(
        "/recommend",
        json={"query": "phone", "top_k": 0},
    )
    assert response.status_code == 422


def test_recommend_validation_top_k_too_high(client):
    """POST /recommend with top_k > 20 returns 422 Unprocessable Entity."""
    response = client.post(
        "/recommend",
        json={"query": "phone", "top_k": 25},
    )
    assert response.status_code == 422


def test_recommend_validation_missing_query(client):
    """POST /recommend without required 'query' field returns 422."""
    response = client.post(
        "/recommend",
        json={"top_k": 5},
    )
    assert response.status_code == 422


def test_recommend_success(client):
    """POST /recommend with valid body invokes pipeline and returns 200."""
    sample_result = ResponseResult(
        summary="Here are your recommendations.",
        recommendations=[
            ResponseProduct(
                asin="B001",
                title="Galaxy S23",
                brand="Samsung",
                price_inr=15000.0,
                explanation="High camera rating.",
                key_factors=["Camera"],
            )
        ],
        follow_up_suggestions=["Compare with Pixel"],
        additional_information="",
    )

    with patch("backend.main.run_pipeline") as mock_pipeline:
        mock_pipeline.return_value = sample_result

        response = client.post(
            "/recommend",
            json={"query": "Samsung phone under 15000", "top_k": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Here are your recommendations."
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["asin"] == "B001"
        assert data["follow_up_suggestions"] == ["Compare with Pixel"]


def test_recommend_error_sanitization(client):
    """POST /recommend sanitizes 500 internal error detail without leaking stack trace."""
    sensitive_internal_error = (
        "Internal DB Connection String: postgres://user:secretpassword@internal.db/prod"
    )

    with patch("backend.main.run_pipeline") as mock_pipeline:
        mock_pipeline.side_effect = RuntimeError(sensitive_internal_error)

        response = client.post(
            "/recommend",
            json={"query": "Samsung phone", "top_k": 5},
        )

        assert response.status_code == 500
        data = response.json()
        # Must NOT expose sensitive error or internal error text
        assert sensitive_internal_error not in data["detail"]
        assert "secretpassword" not in data["detail"]
        assert "recommendation pipeline encountered an error" in data["detail"]


def test_understand_endpoint_success(client):
    """POST /understand returns parsed query structure."""
    mock_qu = QueryUnderstanding(
        raw_query="best budget phone",
        intent=Intent.PRODUCT_RECOMMENDATION,
        category=RetailCategory.CELL_PHONES_AND_ACCESSORIES,
        product_type="phone",
        brand=BrandPreferences(),
    )

    with patch(
        "backend.Agents.query_understanding.QueryUnderstandingAgent"
    ) as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_agent.understand.return_value = mock_qu

        response = client.post(
            "/understand",
            json={"query": "best budget phone"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "product_recommendation"
        assert data["product_type"] == "phone"


def test_understand_endpoint_failure_sanitization(client):
    """POST /understand returns sanitized 500 if agent crashes."""
    with patch(
        "backend.Agents.query_understanding.QueryUnderstandingAgent"
    ) as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_agent.understand.side_effect = ValueError("Missing Gemini API Key secret")

        response = client.post(
            "/understand",
            json={"query": "best budget phone"},
        )

        assert response.status_code == 500
        data = response.json()
        assert "secret" not in data["detail"]
        assert "Query understanding failed" in data["detail"]
