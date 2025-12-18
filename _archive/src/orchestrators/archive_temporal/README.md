# DEPRECATED: Temporal.io Implementation

> ⚠️ **DEPRECATED**: These files contain the Temporal.io implementation. The project now uses n8n for orchestration.

## Overview

This directory contains the archived Temporal.io orchestration code that was used before the project pivoted to n8n (a low-code workflow automation platform).

## Archived Files

- **`cpg1_workflow.py`**: The Temporal workflow definition for C-PG-1 reconciliation
- **`cpg1_activities.py`**: Temporal activities that wrap core business logic
- **`cpg1_worker.py`**: The Temporal worker script that processes workflows

## Related Archived Files

- **`tests/archive/test_temporal_setup.py`**: Unit tests for the Temporal setup
- **`scripts/run_full_reconciliation_temporal_DEPRECATED.py`**: The workflow starter script

## Why Was This Archived?

The project architecture has pivoted from a code-heavy orchestration approach (Temporal.io) to a low-code approach (n8n) for the following reasons:

1. **Reduced complexity**: n8n provides a visual workflow builder
2. **Faster iteration**: Non-developers can modify workflows
3. **Lower maintenance burden**: Less custom code to maintain
4. **Better visibility**: Visual representation of workflow state

## Do Not Use

These files are kept for historical reference only. Do not import or use any code from this directory in active development.

For current orchestration implementation, refer to the n8n workflows configured in the project's n8n instance.
