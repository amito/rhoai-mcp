"""Plugin registration for Connections component."""

from typing import TYPE_CHECKING

from rhoai_mcp_core.clients.base import CRDDefinition
from rhoai_mcp_core.plugin import BasePlugin, PluginMetadata

from rhoai_mcp_connections import __version__

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from rhoai_mcp_core.server import RHOAIServer


class ConnectionsPlugin(BasePlugin):
    """RHOAI MCP plugin for Data Connection management.

    Provides tools for managing data connections (S3 secrets) that allow
    workbenches and pipelines to access external storage.
    """

    def __init__(self) -> None:
        super().__init__(
            PluginMetadata(
                name="connections",
                version=__version__,
                description="Data Connection (S3 secrets) management for RHOAI",
                maintainer="rhoai-mcp@redhat.com",
                requires_crds=[],  # Uses core K8s Secrets, no CRDs required
            )
        )

    def register_tools(self, mcp: "FastMCP", server: "RHOAIServer") -> None:
        """Register data connection management tools."""
        from rhoai_mcp_connections.tools import register_tools

        register_tools(mcp, server)

    def register_resources(self, mcp: "FastMCP", server: "RHOAIServer") -> None:
        """Register connection-related MCP resources."""
        pass

    def get_crd_definitions(self) -> list[CRDDefinition]:
        """Return CRD definitions used by this plugin."""
        return []  # Uses core K8s Secrets, no CRDs

    def health_check(self, server: "RHOAIServer") -> tuple[bool, str]:
        """Connections plugin is always healthy (uses core K8s API)."""
        return True, "Data connections use core Kubernetes API"


def create_plugin() -> ConnectionsPlugin:
    """Factory function for plugin creation."""
    return ConnectionsPlugin()
