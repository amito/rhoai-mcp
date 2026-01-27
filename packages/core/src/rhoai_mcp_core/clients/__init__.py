"""Kubernetes client infrastructure for RHOAI MCP."""

from rhoai_mcp_core.clients.base import (
    CRDDefinition,
    CRDs,
    K8sClient,
    get_k8s_client,
)

__all__ = [
    "CRDDefinition",
    "CRDs",
    "K8sClient",
    "get_k8s_client",
]
