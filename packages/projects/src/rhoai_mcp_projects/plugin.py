"""Plugin registration for Projects component."""

from typing import TYPE_CHECKING

from rhoai_mcp_core.clients.base import CRDDefinition
from rhoai_mcp_core.plugin import BasePlugin, PluginMetadata

from rhoai_mcp_projects import __version__

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from rhoai_mcp_core.server import RHOAIServer


class ProjectsPlugin(BasePlugin):
    """RHOAI MCP plugin for Data Science Project management.

    Provides tools for managing Data Science Projects (namespaces with
    RHOAI-specific labels and annotations).
    """

    def __init__(self) -> None:
        super().__init__(
            PluginMetadata(
                name="projects",
                version=__version__,
                description="Data Science Project management for RHOAI",
                maintainer="rhoai-mcp@redhat.com",
                requires_crds=[],  # Uses core K8s namespaces and OpenShift Projects
            )
        )

    def register_tools(self, mcp: "FastMCP", server: "RHOAIServer") -> None:
        """Register project management tools."""
        from rhoai_mcp_projects.tools import register_tools

        register_tools(mcp, server)

    def register_resources(self, mcp: "FastMCP", server: "RHOAIServer") -> None:
        """Register project-related MCP resources."""
        from rhoai_mcp_projects.resources import register_resources

        register_resources(mcp, server)

    def get_crd_definitions(self) -> list[CRDDefinition]:
        """Return CRD definitions used by this plugin."""
        return []  # Uses core K8s namespaces and OpenShift Projects API

    def health_check(self, server: "RHOAIServer") -> tuple[bool, str]:
        """Projects plugin is always healthy (uses core K8s API)."""
        return True, "Projects uses core Kubernetes and OpenShift APIs"


def create_plugin() -> ProjectsPlugin:
    """Factory function for plugin creation."""
    return ProjectsPlugin()
