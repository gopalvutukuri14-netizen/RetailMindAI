"""
Tests for Stage D: LangGraph orchestrator graph, routing, and run_pipeline guard.

Verifies:
- run_pipeline() returns ResponseResult on successful graph completion.
- run_pipeline() raises RuntimeError if response_result is unexpectedly missing (guard test).
- router_node correctly routes general questions to general_response.
- router_node correctly routes follow-up queries with previous products to context_response.
- router_node correctly routes unsupported categories to out_of_scope.
- router_node correctly routes shopping queries to product_pipeline.
"""

from unittest.mock import MagicMock, patch
import pytest

from backend.orchestrator.graph import run_pipeline
from backend.orchestrator.nodes import router_node
from backend.orchestrator.state import PipelineState
from backend.Agents.query_understanding.schema import (
    QueryUnderstanding,
    Intent,
    RetailCategory,
    BrandPreferences,
)
from backend.Agents.response.schema import ResponseResult, ResponseProduct


class TestLangGraphPipeline:
    """Test LangGraph pipeline orchestrator and guards."""

    @pytest.fixture
    def sample_response_result(self):
        return ResponseResult(
            summary="Recommended products",
            recommendations=[
                ResponseProduct(
                    asin="B001",
                    title="Phone Test",
                    brand="Samsung",
                    price_inr=12000.0,
                    explanation="Great camera and battery.",
                    key_factors=["Camera", "Battery"],
                )
            ],
            follow_up_suggestions=["Compare with other models"],
            additional_information="",
        )

    def test_run_pipeline_success(self, sample_response_result):
        """run_pipeline() invokes the pipeline and extracts response_result."""
        with patch("backend.orchestrator.graph.pipeline.invoke") as mock_invoke:
            mock_invoke.return_value = {
                "response_result": sample_response_result
            }

            result = run_pipeline(
                raw_query="best smartphone under 15000",
                user_id="test_user",
                top_k=5,
            )

            assert result == sample_response_result
            mock_invoke.assert_called_once()
            call_state = mock_invoke.call_args[0][0]
            assert call_state["raw_query"] == "best smartphone under 15000"
            assert call_state["user_id"] == "test_user"
            assert call_state["top_k"] == 5

    def test_run_pipeline_missing_response_result_guard(self):
        """D1: Guard raises informative RuntimeError if response_result is None/missing."""
        with patch("backend.orchestrator.graph.pipeline.invoke") as mock_invoke:
            # Simulate a broken graph branch that returned without setting response_result
            mock_invoke.return_value = {
                "raw_query": "hello",
                "route": "unknown_branch",
            }

            with pytest.raises(RuntimeError) as exc_info:
                run_pipeline(raw_query="hello")

            assert "Pipeline completed without producing a response_result" in str(
                exc_info.value
            )


class TestRouterNode:
    """Test graph router routing decisions."""

    def test_route_general_question(self):
        qu = QueryUnderstanding(
            raw_query="hi, what can you do?",
            intent=Intent.GENERAL_QUESTION,
            brand=BrandPreferences(),
        )
        state: PipelineState = {
            "raw_query": "hi",
            "user_id": "test",
            "top_k": 5,
            "query_understanding": qu,
        }
        res = router_node(state)
        assert res["route"] == "general_response"

    def test_route_context_response_when_previous_products_present(self):
        qu = QueryUnderstanding(
            raw_query="which one has better battery?",
            intent=Intent.COMPARISON,
            brand=BrandPreferences(),
        )
        state: PipelineState = {
            "raw_query": "which one has better battery?",
            "user_id": "test",
            "top_k": 5,
            "query_understanding": qu,
            "previous_products": [{"asin": "B1"}, {"asin": "B2"}],
        }
        res = router_node(state)
        assert res["route"] == "context_response"

    def test_route_product_pipeline_when_no_previous_products_for_comparison(self):
        qu = QueryUnderstanding(
            raw_query="compare samsung vs apple",
            intent=Intent.COMPARISON,
            category=RetailCategory.CELL_PHONES_AND_ACCESSORIES,
            brand=BrandPreferences(),
        )
        state: PipelineState = {
            "raw_query": "compare samsung vs apple",
            "user_id": "test",
            "top_k": 5,
            "query_understanding": qu,
            "previous_products": [],
        }
        res = router_node(state)
        # Without previous products, must route through product_pipeline
        assert res["route"] == "product_pipeline"

    def test_route_out_of_scope_category(self):
        # Construct QueryUnderstanding with an unsupported category value
        qu = QueryUnderstanding(
            raw_query="car tires",
            intent=Intent.PRODUCT_RECOMMENDATION,
            category=None,
            brand=BrandPreferences(),
        )
        # Set category attribute directly to simulate an unsupported external category
        qu.category = "Automotive"  # type: ignore

        state: PipelineState = {
            "raw_query": "car tires",
            "user_id": "test",
            "top_k": 5,
            "query_understanding": qu,
        }
        res = router_node(state)
        assert res["route"] == "out_of_scope"

    def test_route_product_pipeline_for_valid_recommendation(self):
        qu = QueryUnderstanding(
            raw_query="best budget phone",
            intent=Intent.PRODUCT_RECOMMENDATION,
            category=RetailCategory.CELL_PHONES_AND_ACCESSORIES,
            product_type="phone",
            brand=BrandPreferences(),
        )
        state: PipelineState = {
            "raw_query": "best budget phone",
            "user_id": "test",
            "top_k": 5,
            "query_understanding": qu,
        }
        res = router_node(state)
        assert res["route"] == "product_pipeline"
