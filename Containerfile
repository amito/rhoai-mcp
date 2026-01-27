# Multi-stage Containerfile for RHOAI MCP Server
# Optimized for Podman with Red Hat UBI base images
# Supports all transport modes (stdio, SSE, streamable-http)
#
# Build with: podman build -f Containerfile -t rhoai-mcp .

# =============================================================================
# Stage 1: Builder - Install dependencies with uv
# =============================================================================
FROM registry.access.redhat.com/ubi9/python-312 AS builder

# Copy uv from official image for fast, reproducible builds
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory (UBI default is /opt/app-root/src)
WORKDIR /opt/app-root/src

# Copy workspace configuration and lockfile first for better layer caching
COPY pyproject.toml uv.lock ./

# Copy all package definitions (needed for workspace resolution)
COPY packages/core/pyproject.toml packages/core/
COPY packages/notebooks/pyproject.toml packages/notebooks/
COPY packages/inference/pyproject.toml packages/inference/
COPY packages/pipelines/pyproject.toml packages/pipelines/
COPY packages/connections/pyproject.toml packages/connections/
COPY packages/storage/pyproject.toml packages/storage/
COPY packages/projects/pyproject.toml packages/projects/

# Copy README files (required by pyproject.toml metadata)
COPY README.md ./
COPY packages/core/README.md packages/core/ 2>/dev/null || echo "Core README not required"
COPY packages/notebooks/README.md packages/notebooks/ 2>/dev/null || echo "Notebooks README not required"
COPY packages/inference/README.md packages/inference/ 2>/dev/null || echo "Inference README not required"
COPY packages/pipelines/README.md packages/pipelines/ 2>/dev/null || echo "Pipelines README not required"
COPY packages/connections/README.md packages/connections/ 2>/dev/null || echo "Connections README not required"
COPY packages/storage/README.md packages/storage/ 2>/dev/null || echo "Storage README not required"
COPY packages/projects/README.md packages/projects/ 2>/dev/null || echo "Projects README not required"

# Create placeholder README files if they don't exist
RUN for pkg in core notebooks inference pipelines connections storage projects; do \
        if [ ! -f "packages/$pkg/README.md" ]; then \
            echo "# rhoai-mcp-$pkg" > "packages/$pkg/README.md"; \
        fi \
    done

# Install dependencies only (no dev dependencies, no install of local packages yet)
RUN uv sync --frozen --no-dev --no-install-workspace

# Copy all package source code
COPY packages/ ./packages/

# Install all workspace packages
RUN uv sync --frozen --no-dev

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM registry.access.redhat.com/ubi9/python-312 AS runtime

# Labels for container metadata
LABEL org.opencontainers.image.title="RHOAI MCP Server"
LABEL org.opencontainers.image.description="MCP server for Red Hat OpenShift AI - enables AI agents to interact with RHOAI environments"
LABEL org.opencontainers.image.vendor="Red Hat"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/admiller/rhoai-mcp-prototype"

# Set working directory (UBI default is /opt/app-root/src)
WORKDIR /opt/app-root/src

# Copy virtual environment from builder
COPY --from=builder /opt/app-root/src/.venv /opt/app-root/src/.venv

# Copy package source code (needed for editable installs)
COPY --from=builder /opt/app-root/src/packages /opt/app-root/src/packages

# Add virtual environment to PATH
ENV PATH="/opt/app-root/src/.venv/bin:$PATH"

# Environment variables with container-friendly defaults
# Transport: default to stdio for Claude Desktop compatibility
ENV RHOAI_MCP_TRANSPORT="stdio"
# HTTP binding: use 0.0.0.0 for container networking
ENV RHOAI_MCP_HOST="0.0.0.0"
ENV RHOAI_MCP_PORT="8000"
# Auth: default to auto-detection
ENV RHOAI_MCP_AUTH_MODE="auto"
# Logging: default to INFO
ENV RHOAI_MCP_LOG_LEVEL="INFO"

# Expose port for HTTP transports (SSE, streamable-http)
EXPOSE 8000

# UBI runs as non-root by default (UID 1001)
USER 1001

# Health check for HTTP transports
# Note: Only works with SSE/streamable-http, not stdio
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)" || exit 0

# Default entrypoint runs the MCP server
ENTRYPOINT ["rhoai-mcp"]

# Default to stdio transport (can be overridden with --transport sse|streamable-http)
CMD ["--transport", "stdio"]
