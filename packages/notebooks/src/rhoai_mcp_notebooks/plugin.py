"""Plugin registration for Notebooks component."""

from typing import TYPE_CHECKING

from rhoai_mcp_core.clients.base import CRDDefinition
from rhoai_mcp_core.plugin import BasePlugin, PluginMetadata

from rhoai_mcp_notebooks import __version__
from rhoai_mcp_notebooks.crds import NotebookCRDs

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from rhoai_mcp_core.server import RHOAIServer


class NotebooksPlugin(BasePlugin):
    """RHOAI MCP plugin for Notebook (Workbench) management.

    Provides tools for managing Kubeflow Notebook resources which power
    the RHOAI Workbench feature - Jupyter notebooks, VS Code, and RStudio
    development environments.
    """

    def __init__(self) -> None:
        super().__init__(
            PluginMetadata(
                name="notebooks",
                version=__version__,
                description="Workbench (Kubeflow Notebook) management for RHOAI",
                maintainer="kubeflow-team@redhat.com",
                requires_crds=["Notebook"],
            )
        )

    def register_tools(self, mcp: "FastMCP", server: "RHOAIServer") -> None:
        """Register notebook/workbench management tools."""
        from rhoai_mcp_notebooks.tools import register_tools

        register_tools(mcp, server)

    def register_resources(self, mcp: "FastMCP", server: "RHOAIServer") -> None:
        """Register notebook-related MCP resources."""
        # Notebooks don't have standalone resources - they're exposed via projects
        pass

    def get_crd_definitions(self) -> list[CRDDefinition]:
        """Return CRD definitions used by this plugin."""
        return [NotebookCRDs.NOTEBOOK]


def create_plugin() -> NotebooksPlugin:
    """Factory function for plugin creation.

    This is the entry point referenced in pyproject.toml.
    """
    return NotebooksPlugin()
