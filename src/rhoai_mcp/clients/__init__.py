"""Kubernetes client abstractions for RHOAI resources."""

from rhoai_mcp.clients.base import K8sClient, CRDs, get_k8s_client
from rhoai_mcp.clients.projects import ProjectClient
from rhoai_mcp.clients.notebooks import NotebookClient
from rhoai_mcp.clients.inference import InferenceClient
from rhoai_mcp.clients.connections import ConnectionClient
from rhoai_mcp.clients.storage import StorageClient
from rhoai_mcp.clients.pipelines import PipelineClient

__all__ = [
    "K8sClient",
    "CRDs",
    "get_k8s_client",
    "ProjectClient",
    "NotebookClient",
    "InferenceClient",
    "ConnectionClient",
    "StorageClient",
    "PipelineClient",
]
