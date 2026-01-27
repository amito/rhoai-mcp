"""FastMCP server definition for RHOAI with plugin discovery."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from importlib.metadata import entry_points
from typing import TYPE_CHECKING, AsyncIterator

from mcp.server.fastmcp import FastMCP

from rhoai_mcp_core import __version__
from rhoai_mcp_core.clients.base import K8sClient
from rhoai_mcp_core.config import RHOAIConfig, get_config

if TYPE_CHECKING:
    from rhoai_mcp_core.plugin import RHOAIMCPPlugin

logger = logging.getLogger(__name__)

# Entry point group name for plugin discovery
PLUGIN_ENTRY_POINT_GROUP = "rhoai_mcp.plugins"


class RHOAIServer:
    """RHOAI MCP Server with plugin discovery and Kubernetes client lifecycle management."""

    def __init__(self, config: RHOAIConfig | None = None) -> None:
        self._config = config or get_config()
        self._k8s_client: K8sClient | None = None
        self._mcp: FastMCP | None = None
        self._plugins: dict[str, "RHOAIMCPPlugin"] = {}
        self._healthy_plugins: dict[str, "RHOAIMCPPlugin"] = {}

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

    @property
    def plugins(self) -> dict[str, "RHOAIMCPPlugin"]:
        """Get all discovered plugins."""
        return self._plugins

    @property
    def healthy_plugins(self) -> dict[str, "RHOAIMCPPlugin"]:
        """Get plugins that passed health checks."""
        return self._healthy_plugins

    def _discover_plugins(self) -> dict[str, "RHOAIMCPPlugin"]:
        """Discover and load plugins from entry points.

        Returns:
            Dictionary mapping plugin names to plugin instances.
        """
        plugins: dict[str, "RHOAIMCPPlugin"] = {}

        # Use Python 3.10+ compatible entry_points API
        if sys.version_info >= (3, 10):
            eps = entry_points(group=PLUGIN_ENTRY_POINT_GROUP)
        else:
            # Fallback for older Python versions
            all_eps = entry_points()
            eps = all_eps.get(PLUGIN_ENTRY_POINT_GROUP, [])

        for ep in eps:
            try:
                logger.debug(f"Loading plugin from entry point: {ep.name}")
                factory = ep.load()
                plugin = factory()

                # Verify plugin has required interface
                if not hasattr(plugin, "metadata"):
                    logger.warning(
                        f"Plugin {ep.name} does not have metadata, skipping"
                    )
                    continue

                plugins[plugin.metadata.name] = plugin
                logger.info(
                    f"Discovered plugin: {plugin.metadata.name} v{plugin.metadata.version}"
                )
            except Exception as e:
                logger.error(f"Failed to load plugin {ep.name}: {e}")

        return plugins

    def _check_plugin_health(self) -> dict[str, "RHOAIMCPPlugin"]:
        """Check health of all discovered plugins.

        Returns:
            Dictionary of plugins that passed health checks.
        """
        healthy: dict[str, "RHOAIMCPPlugin"] = {}

        for name, plugin in self._plugins.items():
            try:
                is_healthy, message = plugin.health_check(self)
                if is_healthy:
                    healthy[name] = plugin
                    logger.info(f"Plugin {name} health check passed: {message}")
                else:
                    logger.warning(f"Plugin {name} unavailable: {message}")
            except Exception as e:
                logger.warning(f"Plugin {name} health check failed with error: {e}")

        return healthy

    def _create_lifespan(self):
        """Create the lifespan context manager for the MCP server."""
        server_self = self

        @asynccontextmanager
        async def lifespan(app) -> AsyncIterator[None]:
            """Manage server lifecycle - connect K8s on startup, disconnect on shutdown."""
            logger.info("Starting RHOAI MCP server...")

            # Connect to Kubernetes
            server_self._k8s_client = K8sClient(server_self._config)
            try:
                server_self._k8s_client.connect()

                # Check plugin health after K8s connection is established
                server_self._healthy_plugins = server_self._check_plugin_health()

                logger.info(
                    f"RHOAI MCP server started with {len(server_self._healthy_plugins)} "
                    f"active plugins out of {len(server_self._plugins)} discovered"
                )
                yield
            finally:
                logger.info("Shutting down RHOAI MCP server...")
                if server_self._k8s_client:
                    server_self._k8s_client.disconnect()
                server_self._k8s_client = None
                logger.info("RHOAI MCP server shut down")

        return lifespan

    def create_mcp(self) -> FastMCP:
        """Create and configure the FastMCP server."""
        # Discover plugins first
        self._plugins = self._discover_plugins()
        logger.info(f"Discovered {len(self._plugins)} plugins")

        # Create MCP server with lifespan
        # Host/port configured for container networking (0.0.0.0 allows external access)
        mcp = FastMCP(
            name="rhoai-mcp",
            instructions="MCP server for Red Hat OpenShift AI - enables AI agents to "
            "interact with RHOAI environments including workbenches, "
            "model serving, pipelines, and data connections.",
            lifespan=self._create_lifespan(),
            host=self._config.host,
            port=self._config.port,
        )

        # Store reference
        self._mcp = mcp

        # Register tools and resources from all discovered plugins
        # Note: We register from all plugins, but health checks happen at runtime
        # This allows tools to provide meaningful error messages if CRDs are missing
        self._register_plugin_tools(mcp)
        self._register_plugin_resources(mcp)

        # Register core resources (cluster status, etc.)
        self._register_core_resources(mcp)

        return mcp

    def _register_plugin_tools(self, mcp: FastMCP) -> None:
        """Register MCP tools from all discovered plugins."""
        for name, plugin in self._plugins.items():
            try:
                plugin.register_tools(mcp, self)
                logger.debug(f"Registered tools from plugin: {name}")
            except Exception as e:
                logger.error(f"Failed to register tools from plugin {name}: {e}")

        logger.info(f"Registered tools from {len(self._plugins)} plugins")

    def _register_plugin_resources(self, mcp: FastMCP) -> None:
        """Register MCP resources from all discovered plugins."""
        for name, plugin in self._plugins.items():
            try:
                plugin.register_resources(mcp, self)
                logger.debug(f"Registered resources from plugin: {name}")
            except Exception as e:
                logger.error(f"Failed to register resources from plugin {name}: {e}")

        logger.info(f"Registered resources from {len(self._plugins)} plugins")

    def _register_core_resources(self, mcp: FastMCP) -> None:
        """Register core MCP resources for cluster information."""
        from rhoai_mcp_core.clients.base import CRDs

        @mcp.resource("rhoai://cluster/status")
        def cluster_status() -> dict:
            """Get RHOAI cluster status and health.

            Returns overall cluster status including RHOAI operator status,
            available components, and loaded plugins.
            """
            k8s = self.k8s

            result: dict = {
                "connected": k8s.is_connected,
                "rhoai_available": False,
                "components": {},
                "plugins": {
                    "discovered": list(self._plugins.keys()),
                    "active": list(self._healthy_plugins.keys()),
                },
                "accelerators": [],
            }

            # Check for DataScienceCluster
            try:
                dsc_list = k8s.list(CRDs.DATA_SCIENCE_CLUSTER)
                if dsc_list:
                    result["rhoai_available"] = True
                    dsc = dsc_list[0]
                    status = getattr(dsc, "status", None)
                    if status:
                        # Extract component status
                        installed = getattr(status, "installedComponents", {}) or {}
                        for component, state in installed.items():
                            result["components"][component] = state
            except Exception:
                pass

            # Check for accelerator profiles
            try:
                accelerators = k8s.list(CRDs.ACCELERATOR_PROFILE)
                result["accelerators"] = [
                    {
                        "name": acc.metadata.name,
                        "display_name": (acc.metadata.annotations or {}).get(
                            "openshift.io/display-name", acc.metadata.name
                        ),
                        "enabled": getattr(acc.spec, "enabled", True)
                        if hasattr(acc, "spec")
                        else True,
                    }
                    for acc in accelerators
                ]
            except Exception:
                pass

            return result

        @mcp.resource("rhoai://cluster/plugins")
        def cluster_plugins() -> dict:
            """Get information about loaded plugins.

            Returns details about all discovered plugins and their health status.
            """
            plugin_info = {}

            for name, plugin in self._plugins.items():
                meta = plugin.metadata
                is_healthy = name in self._healthy_plugins
                plugin_info[name] = {
                    "version": meta.version,
                    "description": meta.description,
                    "maintainer": meta.maintainer,
                    "requires_crds": meta.requires_crds,
                    "healthy": is_healthy,
                }

            return {
                "total_discovered": len(self._plugins),
                "total_active": len(self._healthy_plugins),
                "plugins": plugin_info,
            }

        @mcp.resource("rhoai://cluster/accelerators")
        def cluster_accelerators() -> list[dict]:
            """Get available accelerator profiles (GPUs).

            Returns the list of AcceleratorProfile resources that define
            available GPU types and configurations.
            """
            k8s = self.k8s

            try:
                accelerators = k8s.list(CRDs.ACCELERATOR_PROFILE)
                return [
                    {
                        "name": acc.metadata.name,
                        "display_name": (acc.metadata.annotations or {}).get(
                            "openshift.io/display-name", acc.metadata.name
                        ),
                        "description": (acc.metadata.annotations or {}).get(
                            "openshift.io/description", ""
                        ),
                        "enabled": getattr(acc.spec, "enabled", True)
                        if hasattr(acc, "spec")
                        else True,
                        "identifier": getattr(acc.spec, "identifier", "nvidia.com/gpu")
                        if hasattr(acc, "spec")
                        else "nvidia.com/gpu",
                        "tolerations": getattr(acc.spec, "tolerations", [])
                        if hasattr(acc, "spec")
                        else [],
                    }
                    for acc in accelerators
                ]
            except Exception as e:
                return [{"error": str(e)}]

        logger.info("Registered core MCP resources")


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
