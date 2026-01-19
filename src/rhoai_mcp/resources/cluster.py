"""MCP Resources for cluster-level information."""

from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import FastMCP

from rhoai_mcp.clients.base import CRDs

if TYPE_CHECKING:
    from rhoai_mcp.server import RHOAIServer


def register_resources(mcp: FastMCP, server: "RHOAIServer") -> None:
    """Register cluster-level MCP resources."""

    @mcp.resource("rhoai://cluster/status")
    def cluster_status() -> dict[str, Any]:
        """Get RHOAI cluster status and health.

        Returns overall cluster status including RHOAI operator status,
        available components, and system health.
        """
        k8s = server.k8s

        result: dict[str, Any] = {
            "connected": k8s.is_connected,
            "rhoai_available": False,
            "components": {},
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

    @mcp.resource("rhoai://cluster/components")
    def cluster_components() -> dict[str, Any]:
        """Get DataScienceCluster component status.

        Returns the status of each RHOAI component (dashboard, workbenches,
        model serving, pipelines, etc.).
        """
        k8s = server.k8s

        try:
            dsc_list = k8s.list(CRDs.DATA_SCIENCE_CLUSTER)
            if not dsc_list:
                return {
                    "error": "No DataScienceCluster found",
                    "message": "RHOAI operator may not be installed",
                }

            dsc = dsc_list[0]
            status = getattr(dsc, "status", None)

            result: dict[str, Any] = {
                "name": dsc.metadata.name,
                "phase": getattr(status, "phase", "Unknown") if status else "Unknown",
                "components": {},
            }

            if status:
                installed = getattr(status, "installedComponents", {}) or {}
                for component, state in installed.items():
                    result["components"][component] = {
                        "status": state,
                        "ready": state == "Installed" or state is True,
                    }

            return result
        except Exception as e:
            return {"error": str(e)}

    @mcp.resource("rhoai://cluster/accelerators")
    def cluster_accelerators() -> list[dict[str, Any]]:
        """Get available accelerator profiles (GPUs).

        Returns the list of AcceleratorProfile resources that define
        available GPU types and configurations.
        """
        k8s = server.k8s

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
