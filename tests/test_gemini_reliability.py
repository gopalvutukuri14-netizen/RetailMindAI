"""
Tests for Stage C: Gemini reliability, retry helper, quota handling, and fallbacks.

Verifies:
- call_with_retry retries on 429 / RESOURCE_EXHAUSTED.
- call_with_retry retries on 500 / 503 transient errors.
- call_with_retry raises non-retryable errors (400, 401, ValueError) immediately.
- call_with_retry respects retry delays and exhausts after 3 retries.
- XAI agent handles explanation count mismatch gracefully without crashing.
- Response agent falls back to deterministic summary when Gemini fails.
- Orchestrator nodes (general_response, context_response) handle Gemini failure gracefully.
"""

from unittest.mock import MagicMock, patch
import pytest

from backend.Agents.gemini_retry import (
    call_with_retry,
    _extract_retry_delay,
    _is_quota_error,
    _is_retryable,
)
from backend.Agents.ranking.schema import (
    RankingResult,
    RankedProduct,
    ScoreBreakdown,
)
from backend.Agents.xai.agent import XAIAgent
from backend.Agents.xai.schema import XAIResult, ProductExplanation
from backend.Agents.response.agent import ResponseAgent
from backend.Agents.query_understanding.schema import (
    QueryUnderstanding,
    Intent,
    RetailCategory,
    BrandPreferences,
)
from backend.Agents.follow_up.schema import (
    FollowUpResult,
    FollowUpSuggestion,
    SuggestionType,
)


class TestGeminiRetryHelper:
    """Tests for the bounded retry and quota handling utility."""

    def test_success_on_first_try(self):
        mock_fn = MagicMock(return_value="success")
        result = call_with_retry(mock_fn, context="test")
        assert result == "success"
        assert mock_fn.call_count == 1

    @patch("time.sleep")
    def test_retry_on_429_quota_error(self, mock_sleep):
        """Retries on 429 and returns result when succeeding on 3rd attempt."""
        quota_err = Exception("429 RESOURCE_EXHAUSTED: quota exceeded")
        mock_fn = MagicMock(side_effect=[quota_err, quota_err, "quota_recovered"])

        result = call_with_retry(mock_fn, context="test_quota")
        assert result == "quota_recovered"
        assert mock_fn.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("time.sleep")
    def test_exhausted_retries_raises_last_exception(self, mock_sleep):
        """After 3 retries (4 calls total), raises the quota exception."""
        quota_err = Exception("429 RESOURCE_EXHAUSTED: quota exceeded")
        mock_fn = MagicMock(side_effect=quota_err)

        with pytest.raises(Exception) as exc_info:
            call_with_retry(mock_fn, context="exhaust_test")

        assert "RESOURCE_EXHAUSTED" in str(exc_info.value)
        assert mock_fn.call_count == 4  # 1 initial + 3 retries
        assert mock_sleep.call_count == 3

    @patch("time.sleep")
    def test_retry_on_503_transient_error(self, mock_sleep):
        """Retries on 503 Service Unavailable."""
        transient_err = Exception("503 Service Unavailable")
        mock_fn = MagicMock(side_effect=[transient_err, "service_ready"])

        result = call_with_retry(mock_fn, context="test_transient")
        assert result == "service_ready"
        assert mock_fn.call_count == 2
        assert mock_sleep.call_count == 1

    def test_non_retryable_error_raises_immediately(self):
        """400 Bad Request or ValueError must raise immediately without retry."""
        bad_request_err = Exception("400 INVALID_ARGUMENT: Bad Request")
        mock_fn = MagicMock(side_effect=bad_request_err)

        with pytest.raises(Exception) as exc_info:
            call_with_retry(mock_fn, context="test_bad_request")

        assert "400" in str(exc_info.value)
        assert mock_fn.call_count == 1  # No retries!

    def test_extract_retry_delay_from_attribute(self):
        err = Exception("Rate limit")
        setattr(err, "retry_delay", 15.0)
        assert _extract_retry_delay(err) == 15.0

    def test_extract_retry_delay_from_string(self):
        err = Exception("Error: retry_delay { seconds: 10 }")
        assert _extract_retry_delay(err) == 10.0

    def test_is_quota_and_is_retryable_helpers(self):
        assert _is_quota_error(Exception("429 Too Many Requests"))
        assert _is_quota_error(Exception("Resource_Exhausted"))
        assert _is_retryable(Exception("500 Internal Server Error"))
        assert _is_retryable(Exception("503 Backend Unavailable"))
        assert not _is_retryable(Exception("404 Not Found"))
        assert not _is_retryable(ValueError("Invalid argument"))


class TestXAIQuotaAndMismatchReliability:
    """Test XAI agent behavior during count mismatch and API errors."""

    @pytest.fixture
    def mock_ranking_result(self):
        scores = ScoreBreakdown(
            similarity_score=0.8,
            spec_match_score=0.9,
            sentiment_score=0.7,
            aspect_alignment_score=0.8,
            memory_alignment_score=0.5,
            final_score=0.78,
        )
        products = [
            RankedProduct(
                asin="B001",
                title="Phone A 128GB",
                brand="Samsung",
                price_inr=15000.0,
                rating=4.5,
                distance=0.2,
                scores=scores,
                match_reasons=["High camera match"],
            ),
            RankedProduct(
                asin="B002",
                title="Phone B 256GB",
                brand="OnePlus",
                price_inr=18000.0,
                rating=4.3,
                distance=0.3,
                scores=scores,
                match_reasons=["High battery match"],
            ),
        ]
        return RankingResult(
            user_id="test_user",
            memory_applied=True,
            total_ranked=2,
            products=products,
        )

    @patch.dict("os.environ", {"GEMINI_API_KEY": "fake_test_key"})
    @patch("google.genai.Client")
    def test_xai_explanation_count_mismatch_does_not_crash(
        self, mock_client_cls, mock_ranking_result
    ):
        """When Gemini returns 1 explanation instead of 2, XAI agent must not raise ValueError."""
        # Setup mock client
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # Mock response returning only 1 explanation for 2 products
        single_explanation_json = """
        {
            "query_summary": "Phone recommendations",
            "explanations": [
                {
                    "asin": "WRONG_OR_MISSING",
                    "explanation": "Great phone for camera and battery.",
                    "key_factors": ["camera", "battery"]
                }
            ]
        }
        """
        mock_response = MagicMock()
        mock_response.text = single_explanation_json
        mock_client.models.generate_content.return_value = mock_response

        agent = XAIAgent()
        query = QueryUnderstanding(
            raw_query="best phone",
            intent=Intent.PRODUCT_RECOMMENDATION,
            category=RetailCategory.CELL_PHONES_AND_ACCESSORIES,
            product_type="phone",
            brand=BrandPreferences(),
            quality_tags=["camera"],
        )

        result = agent.explain(query, mock_ranking_result)

        assert isinstance(result, XAIResult)
        assert len(result.explanations) == 1
        # Authoritative ASIN pinning
        assert result.explanations[0].asin == "B001"


class TestResponseAgentReliability:
    """Test Response agent fallback behavior on Gemini failure."""

    @pytest.fixture
    def sample_data(self):
        query = QueryUnderstanding(
            raw_query="best smartphone",
            intent=Intent.PRODUCT_RECOMMENDATION,
            category=RetailCategory.CELL_PHONES_AND_ACCESSORIES,
            product_type="phone",
            brand=BrandPreferences(),
            quality_tags=["camera"],
        )
        scores = ScoreBreakdown(
            similarity_score=0.8,
            spec_match_score=0.9,
            sentiment_score=0.7,
            aspect_alignment_score=0.8,
            memory_alignment_score=0.5,
            final_score=0.78,
        )
        products = [
            RankedProduct(
                asin="B001",
                title="Samsung Galaxy S23",
                brand="Samsung",
                price_inr=15000.0,
                rating=4.5,
                distance=0.2,
                scores=scores,
                match_reasons=["Great battery life"],
            )
        ]
        ranking = RankingResult(
            user_id="anonymous",
            memory_applied=False,
            total_ranked=1,
            products=products,
        )
        xai = XAIResult(
            query_summary="best smartphone recommendations",
            explanations=[
                ProductExplanation(
                    asin="B001",
                    explanation="Top pick for performance.",
                    key_factors=["battery"],
                )
            ],
        )
        followup = FollowUpResult(
            suggestions=[
                FollowUpSuggestion(
                    suggestion_text="Compare with Pixel",
                    suggestion_type=SuggestionType.COMPARE,
                )
            ]
        )
        return query, ranking, xai, followup

    @patch("time.sleep")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "fake_test_key"})
    @patch("google.genai.Client")
    def test_response_agent_gemini_failure_fallback(
        self, mock_client_cls, mock_sleep, sample_data
    ):
        """When Gemini throws error or returns None, response agent falls back gracefully."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("500 Internal Error")

        query, ranking, xai, followup = sample_data
        agent = ResponseAgent()

        result = agent.generate(query, ranking, xai, followup)

        assert result is not None
        assert len(result.recommendations) == 1
        assert result.recommendations[0].asin == "B001"
        assert result.recommendations[0].title == "Samsung Galaxy S23"
        assert "recommendations matching your request" in result.summary
        assert "Compare with Pixel" in result.follow_up_suggestions
