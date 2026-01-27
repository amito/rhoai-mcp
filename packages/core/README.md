# rhoai-mcp-core

Core infrastructure package for RHOAI MCP Server.

Provides the plugin system, K8s client base, shared models, and server infrastructure
that other component packages build upon.

## Installation

```bash
pip install rhoai-mcp-core
```

## Components

- **Plugin System**: Protocol-based plugin interface with entry point discovery
- **K8s Client**: Base Kubernetes/OpenShift client with dynamic CRD support
- **Server**: FastMCP-based server with automatic plugin loading
- **Models**: Shared Pydantic models for common resources
- **Utils**: Labels, annotations, and error handling utilities
