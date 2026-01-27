# Changelog

All notable changes to the `rhoai-mcp-notebooks` package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-XX

### Added
- Initial release as standalone package extracted from monolithic rhoai-mcp
- Plugin interface implementation for dynamic discovery
- Workbench (Kubeflow Notebook) management tools:
  - `list_workbenches` - List all workbenches in a project
  - `get_workbench` - Get detailed workbench information
  - `create_workbench` - Create a new workbench with configurable resources
  - `start_workbench` - Start a stopped workbench
  - `stop_workbench` - Stop a running workbench
  - `delete_workbench` - Delete a workbench (with confirmation)
  - `list_notebook_images` - List available notebook images
  - `get_workbench_url` - Get the access URL for a workbench
- CRD definitions for Kubeflow Notebooks
- Pydantic models for type-safe workbench operations
