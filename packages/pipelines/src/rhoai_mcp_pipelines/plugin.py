"""Plugin registration for Pipelines component."""

from typing import TYPE_CHECKING

from rhoai_mcp_core.clients.base import CRDDefinition
from rhoai_mcp_core.plugin import BasePlugin, PluginMetadata

from rhoai_mcp_pipelines import __version__
from rhoai_mcp_pipelines.crds import PipelinesCRDs

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from rhoai_mcp_core.server import RHOAIServer


class PipelinesPlugin(BasePlugin):
    """RHOAI MCP plugin for Data Science Pipelines management.

    Provides tools for managing DataSciencePipelinesApplication (DSPA)
    resources which power the RHOAI Pipelines feature.
    """

    def __init__(self) -> None:
        super().__init__(
            PluginMetadata(
                name="pipelines",
                version=__version__,
                description="Data Science Pipelines (DSPA) management for RHOAI",
                maintainer="pipelines-team@redhat.com",
                requires_crds=["DataSciencePipelinesApplication"],
            )
        )

    def register_tools(self, mcp: "FastMCP", server: "RHOAIServer") -> None:
        """Register pipeline management tools."""
        from rhoai_mcp_pipelines.tools import register_tools

        register_tools(mcp, server)

    def register_resources(self, mcp: "FastMCP", server: "RHOAIServer") -> None:
        """Register pipeline-related MCP resources."""
        pass

    def get_crd_definitions(self) -> list[CRDDefinition]:
        """Return CRD definitions used by this plugin."""
        return [PipelinesCRDs.DSPA]


def create_plugin() -> PipelinesPlugin:
    """Factory function for plugin creation."""
    return PipelinesPlugin()
