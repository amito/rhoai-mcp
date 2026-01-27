# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RHOAI MCP Server is an MCP (Model Context Protocol) server that enables AI agents to interact with Red Hat OpenShift AI (RHOAI) environments. It provides programmatic access to RHOAI features (projects, workbenches, model serving, pipelines, data connections, storage) through a plugin-based architecture.

## Build and Development Commands

```bash
# Setup development environment
uv sync --all-packages          # Install all workspace packages
make dev                         # Alias for setup

# Run the server locally
uv run rhoai-mcp                 # Default (stdio transport)
uv run rhoai-mcp --transport sse # HTTP transport

# Testing
make test                        # All tests
make test-unit                   # Unit tests only (packages/*/tests)
make test-integration            # Integration tests (tests/integration)
make test-package PKG=core       # Single package tests

# Code quality
make lint                        # ruff check
make format                      # ruff format + fix
make typecheck                   # mypy
make check                       # lint + typecheck

# Container operations
make build                       # Build container image
make run-http                    # Run with SSE transport
make run-stdio                   # Run with stdio transport
make run-dev                     # Debug logging + dangerous ops enabled
```

## Architecture

### UV Workspace Structure

This is a monorepo managed by `uv` with independent packages in `packages/`:

- **core**: Plugin system, K8s client, configuration, server entry point (`rhoai-mcp` command)
- **notebooks**: Kubeflow Notebook/Workbench management
- **inference**: KServe InferenceService model serving
- **pipelines**: Data Science Pipelines (DSPA)
- **connections**: S3 data connections
- **storage**: PersistentVolumeClaim management
- **projects**: Data Science Project (namespace) management
- **training**: Kubeflow Training Operator integration

### Plugin System

Plugins are discovered via Python entry points in the `rhoai_mcp.plugins` group. Each plugin implements `RHOAIMCPPlugin` protocol (defined in `packages/core/src/rhoai_mcp_core/plugin.py`):

```python
# Entry point declaration in pyproject.toml:
[project.entry-points."rhoai_mcp.plugins"]
notebooks = "rhoai_mcp_notebooks.plugin:create_plugin"
```

Plugin interface:
- `metadata`: Returns `PluginMetadata` (name, version, required CRDs)
- `register_tools()`: Registers MCP tools with FastMCP
- `register_resources()`: Registers MCP resources
- `get_crd_definitions()`: Returns CRD definitions for the plugin
- `health_check()`: Verifies required CRDs are available (graceful degradation)

### Package Structure Pattern

Each package follows this layout:
```
packages/<name>/
├── pyproject.toml           # Package metadata, entry points
├── src/rhoai_mcp_<name>/
│   ├── __init__.py
│   ├── plugin.py            # Plugin factory and registration
│   ├── client.py            # K8s resource client
│   ├── models.py            # Pydantic models
│   ├── tools.py             # MCP tool implementations
│   ├── resources.py         # MCP resource implementations
│   └── crds.py              # CRD definitions
└── tests/
```

### Configuration

Environment variables use `RHOAI_MCP_` prefix. Key settings:
- `AUTH_MODE`: auto | kubeconfig | token
- `TRANSPORT`: stdio | sse | streamable-http
- `KUBECONFIG_PATH`, `KUBECONFIG_CONTEXT`: For kubeconfig auth
- `API_SERVER`, `API_TOKEN`: For token auth
- `ENABLE_DANGEROUS_OPERATIONS`: Enable delete operations
- `READ_ONLY_MODE`: Disable all writes

### Key Dependencies

- `mcp>=1.0.0`: Model Context Protocol (FastMCP)
- `kubernetes>=28.1.0`: K8s Python client
- `pydantic>=2.0.0`: Data validation and settings

## Code Style

- Python 3.10+, line length 100
- Ruff for linting/formatting (isort included)
- Mypy with `disallow_untyped_defs=true`
- Pytest with `asyncio_mode = "auto"`
