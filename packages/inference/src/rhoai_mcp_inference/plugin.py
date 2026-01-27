"""Plugin registration for Inference component."""

from typing import TYPE_CHECKING

from rhoai_mcp_core.clients.base import CRDDefinition
from rhoai_mcp_core.plugin import BasePlugin, PluginMetadata

from rhoai_mcp_inference import __version__
from rhoai_mcp_inference.crds import InferenceCRDs

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from rhoai_mcp_core.server import RHOAIServer


class InferencePlugin(BasePlugin):
    """RHOAI MCP plugin for Model Serving (KServe) management.

    Provides tools for managing KServe InferenceService resources which power
    the RHOAI Model Serving feature for deploying and serving ML models.
    """

    def __init__(self) -> None:
        super().__init__(
            PluginMetadata(
                name="inference",
                version=__version__,
                description="Model Serving (KServe InferenceService) management for RHOAI",
                maintainer="kserve-team@redhat.com",
                requires_crds=["InferenceService"],
            )
        )

    def register_tools(self, mcp: "FastMCP", server: "RHOAIServer") -> None:
        """Register model serving tools."""
        from rhoai_mcp_inference.tools import register_tools

        register_tools(mcp, server)

    def register_resources(self, mcp: "FastMCP", server: "RHOAIServer") -> None:
        """Register inference-related MCP resources."""
        pass

    def get_crd_definitions(self) -> list[CRDDefinition]:
        """Return CRD definitions used by this plugin."""
        return [InferenceCRDs.INFERENCE_SERVICE, InferenceCRDs.SERVING_RUNTIME]


def create_plugin() -> InferencePlugin:
    """Factory function for plugin creation."""
    return InferencePlugin()
