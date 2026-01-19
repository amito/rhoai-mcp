"""FastMCP server definition for RHOAI."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server.fastmcp import FastMCP

from rhoai_mcp import __version__
from rhoai_mcp.clients.base import K8sClient
from rhoai_mcp.config import RHOAIConfig, get_config

logger = logging.getLogger(__name__)


class RHOAIServer:
    """RHOAI MCP Server with Kubernetes client lifecycle management."""

    def __init__(self, config: RHOAIConfig | None = None) -> None:
        self._config = config or get_config()
        self._k8s_client: K8sClient | None = None
        self._mcp: FastMCP | None = None

    @property
    def config(self) -> RHOAIConfig:
        """Get server configuration."""
        return self._config

    @property
    def k8s(self) -> K8sClient:
        """Get the Kubernetes client.

        Raises:
            RuntimeError: If server is not running.
        """
        if self._k8s_client is None:
            raise RuntimeError("Server not running. K8s client not available.")
        return self._k8s_client

    @property
    def mcp(self) -> FastMCP:
        """Get the MCP server instance.

        Raises:
            RuntimeError: If server is not initialized.
        """
        if self._mcp is None:
            raise RuntimeError("Server not initialized.")
        return self._mcp

    def create_mcp(self) -> FastMCP:
        """Create and configure the FastMCP server."""
        # Create MCP server with lifespan
        mcp = FastMCP(
            name="rhoai-mcp",
            version=__version__,
            description="MCP server for Red Hat OpenShift AI - enables AI agents to "
            "interact with RHOAI environments including workbenches, "
            "model serving, pipelines, and data connections.",
        )

        # Store reference
        self._mcp = mcp

        # Register lifespan
        @mcp.custom_server_method("lifespan")
        @asynccontextmanager
        async def lifespan() -> AsyncIterator[None]:
            """Manage server lifecycle - connect K8s on startup, disconnect on shutdown."""
            logger.info("Starting RHOAI MCP server...")
            self._k8s_client = K8sClient(self._config)
            try:
                self._k8s_client.connect()
                logger.info("RHOAI MCP server started successfully")
                yield
            finally:
                logger.info("Shutting down RHOAI MCP server...")
                if self._k8s_client:
                    self._k8s_client.disconnect()
                self._k8s_client = None
                logger.info("RHOAI MCP server shut down")

        # Register all tools
        self._register_tools(mcp)

        # Register all resources
        self._register_resources(mcp)

        return mcp

    def _register_tools(self, mcp: FastMCP) -> None:
        """Register all MCP tools."""
        # Import and register tools from each module
        from rhoai_mcp.tools import projects, notebooks, inference, connections, storage, pipelines

        projects.register_tools(mcp, self)
        notebooks.register_tools(mcp, self)
        inference.register_tools(mcp, self)
        connections.register_tools(mcp, self)
        storage.register_tools(mcp, self)
        pipelines.register_tools(mcp, self)

        logger.info("Registered all MCP tools")

    def _register_resources(self, mcp: FastMCP) -> None:
        """Register all MCP resources."""
        from rhoai_mcp.resources import cluster, projects

        cluster.register_resources(mcp, self)
        projects.register_resources(mcp, self)

        logger.info("Registered all MCP resources")


# Global server instance
_server: RHOAIServer | None = None


def get_server() -> RHOAIServer:
    """Get the global server instance."""
    global _server
    if _server is None:
        _server = RHOAIServer()
    return _server


def create_server(config: RHOAIConfig | None = None) -> FastMCP:
    """Create and return the MCP server instance.

    This is the main entry point for creating the server.
    """
    global _server
    _server = RHOAIServer(config)
    return _server.create_mcp()
