# Workflow Orchestration for C-PG-1

This directory contains the workflow orchestration code for the C-PG-1 reconciliation process.

## Current Architecture: n8n

The project now uses **n8n** for workflow orchestration. n8n is a low-code workflow automation platform that provides:

- ✅ **Visual workflow builder**: Design workflows without writing code
- ✅ **Easy maintenance**: Non-developers can modify workflows
- ✅ **Built-in integrations**: Connect to databases, APIs, and services easily
- ✅ **Monitoring dashboard**: Visual representation of workflow state
- ✅ **Error handling**: Built-in retry and error notification mechanisms

## Active Files

- **`workflow.py`**: Python-based workflow orchestrator for SOX PG-01 automation (used for programmatic access)

## Archived: Temporal.io Implementation

The previous Temporal.io implementation has been archived and is located in:
- **`archive_temporal/`**: Contains the deprecated Temporal workflow, activities, and worker code

See `archive_temporal/README.md` for details about the archived implementation.

## n8n Workflow Setup

For n8n workflow configuration and deployment, refer to:
- The project's n8n instance documentation
- The ops team for access to the n8n dashboard

## Python Workflow (workflow.py)

The `workflow.py` module provides a Python-based workflow for programmatic SOX PG-01 automation:

```python
from src.orchestrators.workflow import execute_ipe_workflow

# Execute the workflow
results, status_code = execute_ipe_workflow(
    cutoff_date="2025-01-31",
    country="NG"
)
```

This is useful for:
- Integration with other Python services
- Batch processing via scripts
- CI/CD pipeline integration
