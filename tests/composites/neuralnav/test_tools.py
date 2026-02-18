"""Tests for NeuralNav recommend_model MCP tool."""

from unittest.mock import MagicMock, patch

from rhoai_mcp.composites.neuralnav.models import ModelRecommendation, RecommendationResult
from rhoai_mcp.composites.neuralnav.tools import register_tools


def _make_mock_mcp() -> MagicMock:
    """Create a mock FastMCP server that captures tool registrations."""
    mock = MagicMock()
    registered_tools: dict = {}

    def capture_tool():
        def decorator(f):
            registered_tools[f.__name__] = f
            return f

        return decorator

    mock.tool = capture_tool
    mock._registered_tools = registered_tools
    return mock


def _make_mock_server() -> MagicMock:
    """Create a mock RHOAIServer."""
    server = MagicMock()
    server.config.neuralnav_url = "http://localhost:8000"
    return server


SAMPLE_RESULT = RecommendationResult(
    specification={
        "use_case": "chatbot_conversational",
        "user_count": 1000,
        "slo_targets": {"ttft_ms": 150, "itl_ms": 65, "e2e_ms": 2000},
        "traffic_profile": {
            "prompt_tokens": 512,
            "output_tokens": 256,
            "expected_qps": 10.0,
        },
    },
    recommendations=[
        ModelRecommendation(
            model_id="meta-llama/Llama-3.1-70B-Instruct",
            model_name="Llama 3.1 70B",
            gpu_config={
                "gpu_type": "NVIDIA-H100",
                "gpu_count": 2,
                "tensor_parallel": 2,
                "replicas": 1,
            },
            predicted_ttft_p95_ms=140,
            predicted_itl_p95_ms=50,
            predicted_e2e_p95_ms=1200,
            predicted_throughput_qps=100.0,
            cost_per_hour_usd=3.98,
            cost_per_month_usd=2872.32,
            meets_slo=True,
            reasoning="Selected for chatbot",
            scores={
                "accuracy_score": 78,
                "price_score": 65,
                "latency_score": 95,
                "complexity_score": 90,
                "balanced_score": 75.3,
                "slo_status": "compliant",
            },
        ),
    ],
    total_configs_evaluated=2847,
    configs_after_filters=542,
)


class TestRecommendModelTool:
    """Tests for recommend_model tool."""

    def test_tool_registration(self) -> None:
        """recommend_model tool is registered."""
        mock_mcp = _make_mock_mcp()
        register_tools(mock_mcp, _make_mock_server())
        assert "recommend_model" in mock_mcp._registered_tools

    @patch("rhoai_mcp.composites.neuralnav.tools.NeuralNavClient")
    def test_successful_recommendation(self, mock_client_class: MagicMock) -> None:
        """Successful recommendation returns formatted result."""
        mock_client_class.return_value.recommend.return_value = SAMPLE_RESULT
        mock_mcp = _make_mock_mcp()
        mock_server = _make_mock_server()

        register_tools(mock_mcp, mock_server)
        recommend_model = mock_mcp._registered_tools["recommend_model"]

        result = recommend_model(text="I need a chatbot for 1000 users")

        assert "specification" in result
        assert "recommendations" in result
        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0]["rank"] == 1
        assert result["recommendations"][0]["model_id"] == "meta-llama/Llama-3.1-70B-Instruct"
        assert result["total_configs_evaluated"] == 2847

    @patch("rhoai_mcp.composites.neuralnav.tools.NeuralNavClient")
    def test_with_overrides(self, mock_client_class: MagicMock) -> None:
        """Overrides are passed to the client."""
        mock_client_class.return_value.recommend.return_value = SAMPLE_RESULT
        mock_mcp = _make_mock_mcp()
        mock_server = _make_mock_server()

        register_tools(mock_mcp, mock_server)
        recommend_model = mock_mcp._registered_tools["recommend_model"]

        recommend_model(
            text="I need a model",
            use_case="code_completion",
            user_count=5000,
            preferred_gpu_types=["H100"],
        )

        mock_client_class.return_value.recommend.assert_called_once_with(
            "I need a model",
            use_case_override="code_completion",
            user_count_override=5000,
            gpu_types_override=["H100"],
        )

    @patch("rhoai_mcp.composites.neuralnav.tools.NeuralNavClient")
    def test_connection_error(self, mock_client_class: MagicMock) -> None:
        """Connection error returns error dict."""
        from rhoai_mcp.composites.neuralnav.client import NeuralNavConnectionError

        mock_client_class.return_value.recommend.side_effect = NeuralNavConnectionError(
            "Neural Navigator service unavailable at http://localhost:8000"
        )
        mock_mcp = _make_mock_mcp()
        mock_server = _make_mock_server()

        register_tools(mock_mcp, mock_server)
        recommend_model = mock_mcp._registered_tools["recommend_model"]

        result = recommend_model(text="I need a chatbot")

        assert "error" in result
        assert "unavailable" in result["error"].lower()
        assert "hint" in result

    @patch("rhoai_mcp.composites.neuralnav.tools.NeuralNavClient")
    def test_api_error(self, mock_client_class: MagicMock) -> None:
        """API error returns error dict with status code."""
        from rhoai_mcp.composites.neuralnav.client import NeuralNavAPIError

        mock_client_class.return_value.recommend.side_effect = NeuralNavAPIError(
            status_code=500,
            detail="Internal Server Error",
        )
        mock_mcp = _make_mock_mcp()
        mock_server = _make_mock_server()

        register_tools(mock_mcp, mock_server)
        recommend_model = mock_mcp._registered_tools["recommend_model"]

        result = recommend_model(text="I need a chatbot")

        assert "error" in result
        assert result["status_code"] == 500

    @patch("rhoai_mcp.composites.neuralnav.tools.NeuralNavClient")
    def test_empty_recommendations(self, mock_client_class: MagicMock) -> None:
        """Empty recommendations returns message."""
        empty_result = RecommendationResult(
            specification={
                "use_case": "chatbot_conversational",
                "user_count": 1000,
                "slo_targets": {},
                "traffic_profile": {},
            },
            recommendations=[],
            total_configs_evaluated=2847,
            configs_after_filters=0,
        )
        mock_client_class.return_value.recommend.return_value = empty_result
        mock_mcp = _make_mock_mcp()
        mock_server = _make_mock_server()

        register_tools(mock_mcp, mock_server)
        recommend_model = mock_mcp._registered_tools["recommend_model"]

        result = recommend_model(text="I need a chatbot")

        assert result["recommendations"] == []
        assert "message" in result
