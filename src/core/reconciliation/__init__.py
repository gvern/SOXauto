"""
Reconciliation Package

Business logic for SOX reconciliations (e.g., C-PG-1).

Includes:
- CPG1ReconciliationConfig: Business rules for C-PG-1 reconciliation
- run_reconciliation: Headless reconciliation engine for automation
- SummaryBuilder: Build financial reconciliation summaries
"""

from src.core.recon.cpg1 import CPG1ReconciliationConfig
from src.core.recon.run_reconciliation import run_reconciliation
from src.core.recon.summary_builder import SummaryBuilder

__all__ = [
    'CPG1ReconciliationConfig',
    'run_reconciliation',
    'SummaryBuilder',
]
