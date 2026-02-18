"""MCP tool for Neural Navigator model recommendations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from rhoai_mcp.composites.neuralnav.client import (
    NeuralNavAPIError,
    NeuralNavClient,
    NeuralNavConnectionError,
)

if TYPE_CHECKING:
    from rhoai_mcp.server import RHOAIServer


def register_tools(mcp: FastMCP, server: RHOAIServer) -> None:
    """Register NeuralNav composite tools with the MCP server."""

    @mcp.tool()
    def recommend_model(
        text: str,
        use_case: str | None = None,
        user_count: int | None = None,
        preferred_gpu_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get LLM model recommendations from Neural Navigator.

        Runs the full NeuralNav recommendation flow: extracts intent from
        natural language, builds technical specifications, and returns
        the top-5 balanced model recommendations ranked by a weighted
        composite of accuracy, cost, latency, and deployment complexity.

        Args:
            text: Natural language description of the use case
                (e.g., "I need a chatbot for 5000 users with low latency").
            use_case: Override the extracted use case. Valid values:
                chatbot_conversational, code_completion, code_generation_detailed,
                translation, content_generation, summarization_short,
                document_analysis_rag, long_document_summarization,
                research_legal_analysis.
            user_count: Override the extracted user count.
            preferred_gpu_types: Override GPU preferences.
                Valid: L4, A100-40, A100-80, H100, H200, B200.

        Returns:
            Top-5 balanced model recommendations with assembled specification,
            or error dict if the request fails.
        """
        client = NeuralNavClient(server.config.neuralnav_url)

        try:
            result = client.recommend(
                text,
                use_case_override=use_case,
                user_count_override=user_count,
                gpu_types_override=preferred_gpu_types,
            )
        except NeuralNavConnectionError as e:
            return {
                "error": str(e),
                "hint": "Check RHOAI_MCP_NEURALNAV_URL configuration",
            }
        except NeuralNavAPIError as e:
            return {
                "error": "Neural Navigator API error",
                "status_code": e.status_code,
                "details": e.detail,
            }

        # Format recommendations with rank numbers
        recommendations = []
        for i, rec in enumerate(result.recommendations, 1):
            rec_dict = rec.model_dump(exclude_none=True)
            rec_dict["rank"] = i
            recommendations.append(rec_dict)

        response: dict[str, Any] = {
            "specification": result.specification,
            "recommendations": recommendations,
            "total_configs_evaluated": result.total_configs_evaluated,
            "configs_after_filters": result.configs_after_filters,
        }

        if not recommendations:
            response["message"] = "No configurations matched the requirements"

        return response
