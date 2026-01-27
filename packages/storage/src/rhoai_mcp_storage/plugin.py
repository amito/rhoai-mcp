"""Plugin registration for Storage component."""

from typing import TYPE_CHECKING

from rhoai_mcp_core.clients.base import CRDDefinition
from rhoai_mcp_core.plugin import BasePlugin, PluginMetadata

from rhoai_mcp_storage import __version__

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from rhoai_mcp_core.server import RHOAIServer


class StoragePlugin(BasePlugin):
    """RHOAI MCP plugin for Storage (PVC) management.

    Provides tools for managing PersistentVolumeClaims that provide
    persistent storage for workbenches and other project resources.
    """

    def __init__(self) -> None:
        super().__init__(
            PluginMetadata(
                name="storage",
                version=__version__,
                description="Storage (PVC) management for RHOAI",
                maintainer="rhoai-mcp@redhat.com",
                requires_crds=[],  # Uses core K8s PVCs, no CRDs required
            )
        )

    def register_tools(self, mcp: "FastMCP", server: "RHOAIServer") -> None:
        """Register storage management tools."""
        from rhoai_mcp_storage.tools import register_tools

        register_tools(mcp, server)

    def register_resources(self, mcp: "FastMCP", server: "RHOAIServer") -> None:
        """Register storage-related MCP resources."""
        pass

    def get_crd_definitions(self) -> list[CRDDefinition]:
        """Return CRD definitions used by this plugin."""
        return []  # Uses core K8s PVCs, no CRDs

    def health_check(self, server: "RHOAIServer") -> tuple[bool, str]:
        """Storage plugin is always healthy (uses core K8s API)."""
        return True, "Storage uses core Kubernetes API"


def create_plugin() -> StoragePlugin:
    """Factory function for plugin creation."""
    return StoragePlugin()
