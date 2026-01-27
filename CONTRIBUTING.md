# Contributing to RHOAI MCP Server

This document describes the modular architecture and contribution guidelines for the RHOAI MCP Server.

## Repository Structure

```
rhoai-mcp/
├── packages/
│   ├── core/                  # rhoai-mcp-core (shared infrastructure)
│   ├── notebooks/             # rhoai-mcp-notebooks (Kubeflow team)
│   ├── inference/             # rhoai-mcp-inference (KServe team)
│   ├── pipelines/             # rhoai-mcp-pipelines
│   ├── connections/           # rhoai-mcp-connections
│   ├── storage/               # rhoai-mcp-storage
│   └── projects/              # rhoai-mcp-projects
├── container/                 # Container build files
├── tests/integration/         # Cross-component tests
├── pyproject.toml             # Workspace root configuration
└── uv.lock                    # Unified lockfile
```

## Component Packages

Each component is an independently versioned Python package:

| Package | Description | Maintainer |
|---------|-------------|------------|
| `rhoai-mcp-core` | Plugin system, K8s client, server infrastructure | rhoai-mcp@redhat.com |
| `rhoai-mcp-notebooks` | Workbench (Kubeflow Notebook) management | kubeflow-team@redhat.com |
| `rhoai-mcp-inference` | Model inference (KServe/ModelMesh) | kserve-team@redhat.com |
| `rhoai-mcp-pipelines` | Data Science Pipelines | pipelines-team@redhat.com |
| `rhoai-mcp-connections` | Data connection management | rhoai-mcp@redhat.com |
| `rhoai-mcp-storage` | Persistent storage management | rhoai-mcp@redhat.com |
| `rhoai-mcp-projects` | Data Science Project management | rhoai-mcp@redhat.com |

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- Access to a Kubernetes/OpenShift cluster (for integration testing)

### Getting Started

```bash
# Clone the repository
git clone https://github.com/admiller/rhoai-mcp-prototype.git
cd rhoai-mcp-prototype

# Install all packages in development mode
make dev

# Or using uv directly
uv sync --all-packages
```

### Running Tests

```bash
# Run all tests
make test

# Run tests for a specific package
make test-package PKG=notebooks

# Run unit tests only
make test-unit

# Run integration tests
make test-integration
```

### Code Quality

```bash
# Run linter
make lint

# Format code
make format

# Run type checker
make typecheck

# Run all checks
make check
```

### Running the Server Locally

```bash
# Run with SSE transport
make run-local

# Run with stdio transport
make run-local-stdio

# Run with debug logging
make run-local-debug
```

## Plugin Architecture

### Plugin Interface

Each component implements the `RHOAIMCPPlugin` protocol defined in `packages/core/src/rhoai_mcp_core/plugin.py`:

```python
class RHOAIMCPPlugin(Protocol):
    @property
    def metadata(self) -> PluginMetadata: ...

    def register_tools(self, mcp: FastMCP, server: RHOAIServer) -> None: ...

    def register_resources(self, mcp: FastMCP, server: RHOAIServer) -> None: ...

    def get_crd_definitions(self) -> list[CRDDefinition]: ...

    def health_check(self, server: RHOAIServer) -> tuple[bool, str]: ...
```

### Entry Point Registration

Plugins are discovered via Python entry points. Register your plugin in `pyproject.toml`:

```toml
[project.entry-points."rhoai_mcp.plugins"]
my_plugin = "rhoai_mcp_my_plugin.plugin:create_plugin"
```

### Adding a New Component

1. Create a new package directory under `packages/`:
   ```
   packages/my-component/
   ├── pyproject.toml
   ├── README.md
   └── src/rhoai_mcp_my_component/
       ├── __init__.py
       ├── plugin.py
       ├── client.py
       ├── models.py
       └── tools.py
   ```

2. Implement the plugin class:
   ```python
   from rhoai_mcp_core.plugin import BasePlugin, PluginMetadata

   class MyPlugin(BasePlugin):
       def __init__(self) -> None:
           super().__init__(
               PluginMetadata(
                   name="my-component",
                   version="0.1.0",
                   description="My component description",
                   maintainer="my-team@redhat.com",
                   requires_crds=["MyCustomResource"],
               )
           )

       def register_tools(self, mcp, server):
           # Register MCP tools
           pass

       def health_check(self, server):
           # Return (True, "message") if healthy
           # Return (False, "reason") if unhealthy
           pass

   def create_plugin() -> MyPlugin:
       return MyPlugin()
   ```

3. Register the entry point in your `pyproject.toml`:
   ```toml
   [project.entry-points."rhoai_mcp.plugins"]
   my-component = "rhoai_mcp_my_component.plugin:create_plugin"
   ```

4. Add your package to the workspace by updating the root `pyproject.toml` sources.

## Versioning

- **Core package**: Follows strict semantic versioning. Breaking changes require major version bump.
- **Component packages**: Independent versioning per team.
- **Container image**: Tagged with composite version or `latest` for main branch.

Components specify core compatibility:
```toml
dependencies = ["rhoai-mcp-core>=1.0.0,<2.0.0"]
```

## Graceful Degradation

Plugins that fail health checks (e.g., required CRDs not installed) are skipped. The server continues to operate with available plugins. This allows the container image to include all components while only activating those whose prerequisites are met.

## Container Build

```bash
# Build container image
make build

# Test the build
make test-build

# Run container with HTTP transport
make run-http

# Run container with stdio transport
make run-stdio
```

## Pull Request Guidelines

1. Ensure all tests pass: `make test`
2. Ensure code is formatted: `make format`
3. Ensure no lint errors: `make lint`
4. Update relevant documentation
5. Add tests for new functionality
6. Keep changes focused on the affected component(s)

## Questions?

For questions about specific components, reach out to the maintainer listed in the table above.
