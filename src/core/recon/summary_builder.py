"""
Summary Builder Module

Builds financial reconciliation summaries for SOX controls.
Extracts the reconciliation metrics calculation logic from the main orchestrator.

This module is responsible for:
- Calculating Actuals from GL balances (CR_04)
- Calculating Target Values from component IPEs
- Computing variance and reconciliation status
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import pandas as pd

from src.core.recon.cpg1 import CPG1ReconciliationConfig


logger = logging.getLogger(__name__)


class SummaryBuilder:
    """
    Build financial reconciliation summaries.
    
    Uses CPG1ReconciliationConfig for business logic and rules.
    
    Example:
        >>> builder = SummaryBuilder(data_store)
        >>> metrics = builder.build()
        >>> print(f"Variance: {metrics['variance']}")
    """
    
    def __init__(self, data_store: Dict[str, pd.DataFrame]):
        """
        Initialize the summary builder.
        
        Args:
            data_store: Dictionary mapping IPE/CR IDs to DataFrames
        """
        self.data_store = data_store
        self.config = CPG1ReconciliationConfig
    
    def build(self) -> Dict[str, Any]:
        """
        Build complete reconciliation metrics.
        
        Returns:
            Dictionary with reconciliation metrics:
            {
                'actuals': float - GL balance total
                'target_values': float - Sum of component IPEs
                'variance': float - Difference
                'status': str - 'RECONCILED' or 'VARIANCE_DETECTED'
                'component_totals': dict - Per-IPE totals
            }
        """
        metrics = {
            'actuals': None,
            'target_values': None,
            'variance': None,
            'status': None,
            'component_totals': {},
        }
        
        # Calculate actuals
        metrics['actuals'] = self._calculate_actuals()
        
        # Calculate target values
        target_sum, component_totals = self._calculate_target_values()
        metrics['target_values'] = target_sum
        metrics['component_totals'] = component_totals
        
        # Calculate variance using config
        if metrics['actuals'] is not None and metrics['target_values'] is not None:
            variance_result = self.config.calculate_variance(
                actuals=metrics['actuals'],
                target_values=metrics['target_values'],
            )
            metrics.update(variance_result)
        
        return metrics
    
    def _calculate_actuals(self) -> float:
        """
        Calculate Actuals from CR_04 (NAV GL Balances).
        
        Returns:
            Total amount from GL balances, or None if not available
        """
        cr_04_df = self.data_store.get('CR_04')
        if cr_04_df is None or cr_04_df.empty:
            logger.warning("CR_04 data not available for actuals calculation")
            return None
        
        try:
            # Look for amount column
            amount_col = None
            for col in ['BALANCE_AT_DATE', 'Balance_At_Date', 'balance', 'Amount']:
                if col in cr_04_df.columns:
                    amount_col = col
                    break
            
            if amount_col:
                return float(cr_04_df[amount_col].sum())
            else:
                logger.warning("No amount column found in CR_04")
                return None
        except Exception as e:
            logger.warning(f"Could not calculate actuals: {e}")
            return None
    
    def _calculate_target_values(self) -> tuple:
        """
        Calculate Target Values from component IPEs.
        
        Returns:
            Tuple of (total_sum, component_totals_dict)
        """
        component_ipes = self.config.get_component_ipes()
        target_sum = 0.0
        component_totals = {}
        
        for ipe_id in component_ipes:
            df = self.data_store.get(ipe_id)
            if df is not None and not df.empty:
                try:
                    # Try to find an amount column
                    amount_cols = [
                        'Amount', 'amount', 'Remaining Amount', 'remaining_amount', 
                        'BALANCE_AT_DATE', 'Balance', 'Sum of Grand Total'
                    ]
                    for col in amount_cols:
                        if col in df.columns:
                            component_total = float(df[col].sum())
                            component_totals[ipe_id] = component_total
                            target_sum += component_total
                            break
                except Exception as e:
                    logger.warning(f"Could not calculate total for {ipe_id}: {e}")
        
        return target_sum, component_totals


def calculate_reconciliation_metrics(
    data_store: Dict[str, pd.DataFrame],
) -> Dict[str, Any]:
    """
    Calculate overall reconciliation metrics.
    
    Convenience function that creates a SummaryBuilder and builds metrics.
    
    Args:
        data_store: Dictionary mapping IPE/CR IDs to DataFrames
    
    Returns:
        Dictionary with reconciliation metrics
    """
    builder = SummaryBuilder(data_store)
    return builder.build()


__all__ = [
    'SummaryBuilder',
    'calculate_reconciliation_metrics',
]
