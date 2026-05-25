"""Tests for llm-d-planner MCP tools."""

from unittest.mock import MagicMock, patch

from rhoai_mcp.domains.llm_d_planner.models import DeploymentIntent
from rhoai_mcp.domains.llm_d_planner.tools import register_tools
from rhoai_mcp.utils.workflow_token import sign_step, verify_step


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
    server.config.planner_url = "http://localhost:8000"
    server.config.planner_timeout = 120
    return server


SAMPLE_INTENT = DeploymentIntent(
    use_case="chatbot_conversational",
    user_count=1000,
    experience_class="conversational",
    preferred_gpu_types=[],
    accuracy_priority="medium",
    cost_priority="medium",
    latency_priority="medium",
    complexity_priority="medium",
    domain_specialization=["general"],
)

SAMPLE_INTENT_DATA = {
    "use_case": "chatbot_conversational",
    "user_count": 1000,
    "experience_class": "conversational",
    "preferred_gpu_types": [],
    "accuracy_priority": "medium",
    "cost_priority": "medium",
    "latency_priority": "medium",
    "complexity_priority": "medium",
    "domain_specialization": ["general"],
    "additional_context": None,
}

SAMPLE_SLO_DEFAULTS = {
    "success": True,
    "slo_defaults": {
        "use_case": "chatbot_conversational",
        "ttft_ms": {"min": 50, "max": 200, "default": 150},
        "itl_ms": {"min": 20, "max": 80, "default": 65},
        "e2e_ms": {"min": 500, "max": 3000, "default": 2000},
    },
}

SAMPLE_WORKLOAD_PROFILE = {
    "success": True,
    "use_case": "chatbot_conversational",
    "workload_profile": {
        "prompt_tokens": 512,
        "output_tokens": 256,
        "peak_multiplier": 2.0,
        "distribution": "poisson",
        "active_fraction": 0.3,
        "requests_per_active_user_per_min": 2,
    },
}

SAMPLE_EXPECTED_RPS = {
    "success": True,
    "expected_rps": 10.0,
    "peak_rps": 20.0,
}


class TestExtractIntentTool:
    """Tests for extract_intent tool."""

    def test_tool_registration(self) -> None:
        """extract_intent tool is registered."""
        mock_mcp = _make_mock_mcp()
        register_tools(mock_mcp, _make_mock_server())
        assert "extract_intent" in mock_mcp._registered_tools

    @patch("rhoai_mcp.domains.llm_d_planner.tools.PlannerClient")
    def test_successful_extraction(self, mock_client_class: MagicMock) -> None:
        """Successful extraction returns intent fields and workflow token."""
        mock_client_class.return_value.extract_intent.return_value = SAMPLE_INTENT
        mock_mcp = _make_mock_mcp()
        register_tools(mock_mcp, _make_mock_server())
        extract_intent = mock_mcp._registered_tools["extract_intent"]

        result = extract_intent(text="I need a chatbot for 1000 users")

        assert result["use_case"] == "chatbot_conversational"
        assert result["user_count"] == 1000
        assert "workflow_token" in result
        # Verify token is valid and carries intent data
        data = verify_step(result["workflow_token"], "intent_extracted")
        assert "error" not in data
        assert data["use_case"] == "chatbot_conversational"

    @patch("rhoai_mcp.domains.llm_d_planner.tools.PlannerClient")
    def test_empty_text_returns_error(self, mock_client_class: MagicMock) -> None:
        """Empty text returns error without calling client."""
        mock_mcp = _make_mock_mcp()
        register_tools(mock_mcp, _make_mock_server())
        extract_intent = mock_mcp._registered_tools["extract_intent"]

        result = extract_intent(text="")

        assert "error" in result
        assert "non-empty" in result["error"]
        mock_client_class.assert_not_called()

    @patch("rhoai_mcp.domains.llm_d_planner.tools.PlannerClient")
    def test_text_exceeds_max_length(self, mock_client_class: MagicMock) -> None:
        """Text exceeding max length returns error."""
        mock_mcp = _make_mock_mcp()
        register_tools(mock_mcp, _make_mock_server())
        extract_intent = mock_mcp._registered_tools["extract_intent"]

        result = extract_intent(text="x" * 4001)

        assert "error" in result
        assert "max length" in result["error"]
        mock_client_class.assert_not_called()

    @patch("rhoai_mcp.domains.llm_d_planner.tools.PlannerClient")
    def test_connection_error(self, mock_client_class: MagicMock) -> None:
        """Connection error returns error dict."""
        from rhoai_mcp.domains.llm_d_planner.client import PlannerConnectionError

        mock_client_class.return_value.extract_intent.side_effect = PlannerConnectionError(
            "llm-d-planner service unavailable at http://localhost:8000"
        )
        mock_mcp = _make_mock_mcp()
        register_tools(mock_mcp, _make_mock_server())
        extract_intent = mock_mcp._registered_tools["extract_intent"]

        result = extract_intent(text="I need a chatbot")

        assert "error" in result
        assert "unavailable" in result["error"].lower()

    @patch("rhoai_mcp.domains.llm_d_planner.tools.PlannerClient")
    def test_api_error(self, mock_client_class: MagicMock) -> None:
        """API error returns error dict with status code."""
        from rhoai_mcp.domains.llm_d_planner.client import PlannerAPIError

        mock_client_class.return_value.extract_intent.side_effect = PlannerAPIError(
            status_code=500,
            detail="Internal server error"
        )
        mock_mcp = _make_mock_mcp()
        register_tools(mock_mcp, _make_mock_server())
        extract_intent = mock_mcp._registered_tools["extract_intent"]

        result = extract_intent(text="I need a chatbot")

        assert "error" in result
        assert "api error" in result["error"].lower()
        assert result["status_code"] == 500


class TestPrepareModelTechSpecs:
    """Tests for prepare_model_tech_specs tool."""

    def test_tool_registration(self) -> None:
        """prepare_model_tech_specs tool is registered."""
        mock_mcp = _make_mock_mcp()
        register_tools(mock_mcp, _make_mock_server())
        assert "prepare_model_tech_specs" in mock_mcp._registered_tools

    @patch("rhoai_mcp.domains.llm_d_planner.tools.PlannerClient")
    def test_successful_spec_building(self, mock_client_class: MagicMock) -> None:
        """Builds specification from intent token and API defaults."""
        mock_client = mock_client_class.return_value
        mock_client.get_slo_defaults.return_value = SAMPLE_SLO_DEFAULTS
        mock_client.get_workload_profile.return_value = SAMPLE_WORKLOAD_PROFILE
        mock_client.get_expected_rps.return_value = SAMPLE_EXPECTED_RPS

        mock_mcp = _make_mock_mcp()
        register_tools(mock_mcp, _make_mock_server())
        prepare = mock_mcp._registered_tools["prepare_model_tech_specs"]

        token = sign_step("intent_extracted", SAMPLE_INTENT_DATA)
        result = prepare(workflow_token=token)

        assert "error" not in result
        spec = result["specification"]
        assert spec["use_case"] == "chatbot_conversational"
        assert spec["user_count"] == 1000
        assert spec["slo_targets"]["ttft_ms"] == 150
        assert spec["traffic_profile"]["prompt_tokens"] == 512
        assert "workflow_token" in result
        # Verify output token carries spec data
        data = verify_step(result["workflow_token"], "specs_prepared")
        assert "error" not in data

    @patch("rhoai_mcp.domains.llm_d_planner.tools.PlannerClient")
    def test_user_overrides_applied(self, mock_client_class: MagicMock) -> None:
        """User overrides replace intent/default values."""
        mock_client = mock_client_class.return_value
        mock_client.get_slo_defaults.return_value = SAMPLE_SLO_DEFAULTS
        mock_client.get_workload_profile.return_value = SAMPLE_WORKLOAD_PROFILE
        mock_client.get_expected_rps.return_value = SAMPLE_EXPECTED_RPS

        mock_mcp = _make_mock_mcp()
        register_tools(mock_mcp, _make_mock_server())
        prepare = mock_mcp._registered_tools["prepare_model_tech_specs"]

        token = sign_step("intent_extracted", SAMPLE_INTENT_DATA)
        result = prepare(
            workflow_token=token,
            user_count=5000,
            ttft_max_ms=100,
        )

        assert "error" not in result
        spec = result["specification"]
        assert spec["user_count"] == 5000  # overridden
        assert spec["slo_targets"]["ttft_ms"] == 100  # overridden
        assert spec["slo_targets"]["itl_ms"] == 65  # default

    def test_missing_workflow_token(self) -> None:
        """Missing workflow_token returns error."""
        mock_mcp = _make_mock_mcp()
        register_tools(mock_mcp, _make_mock_server())
        prepare = mock_mcp._registered_tools["prepare_model_tech_specs"]

        result = prepare(workflow_token="")

        assert "error" in result

    def test_wrong_step_token(self) -> None:
        """Token from wrong step returns error."""
        mock_mcp = _make_mock_mcp()
        register_tools(mock_mcp, _make_mock_server())
        prepare = mock_mcp._registered_tools["prepare_model_tech_specs"]

        token = sign_step("specs_prepared", {"some": "data"})
        result = prepare(workflow_token=token)

        assert "error" in result
        assert "Wrong workflow order" in result["error"]
