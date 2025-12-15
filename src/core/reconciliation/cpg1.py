"""
C-PG-1 Reconciliation Business Logic

This defines how to calculate the reconciliation:
ACTUALS (CR_04) vs TARGET VALUES (sum of 6 components)

Extracted from legacy config_cpg1_athena.py to keep reconciliation logic
separate from data configuration.
"""

from typing import Dict, Any, List


class CPG1ReconciliationConfig:
    """
    C-PG-1 Reconciliation Business Logic
    
    This defines how to calculate the reconciliation:
    ACTUALS (CR_04) vs TARGET VALUES (sum of 6 components)
    """
    
    RECONCILIATION_FORMULA = {
        'actuals': {
            'source': 'CR_04',
            'calculation': 'SUM(amount_lcy) from NAV GL Balance'
        },
        'target_values': {
            'components': [
                {'id': 'IPE_07', 'name': 'Customer AR Balances'},
                {'id': 'IPE_10', 'name': 'Customer Prepayments'},
                {'id': 'IPE_08', 'name': 'Voucher Liabilities'},
                {'id': 'IPE_31', 'name': 'Collection Accounts'},
                {'id': 'IPE_34', 'name': 'Refund Liability'},
                {'id': 'IPE_12', 'name': 'Packages Not Reconciled'}
            ],
            'calculation': 'SUM of all component amounts'
        },
        'variance': {
            'formula': 'actuals - target_values',
            'threshold': 1000,  # Acceptable variance in LCY
            'status_rules': {
                'RECONCILED': 'abs(variance) < threshold',
                'VARIANCE_DETECTED': 'abs(variance) >= threshold'
            }
        }
    }
    
    GL_ACCOUNT_MAPPING = {
        '13003': 'Customer AR - Trade',
        '13004': 'Customer AR - Other',
        '13005': 'Packages Delivered Not Reconciled',
        '13009': 'Customer AR - Allowance for Doubtful Accounts',
        '13024': 'Packages Not Reconciled - Other',
        '18317': 'Marketplace Refund Liability',
        '18350': 'Customer Prepayments',
        '18412': 'Voucher Liabilities'
    }

    @classmethod
    def get_component_ipes(cls) -> List[str]:
        """Return list of IPE IDs that comprise the target values."""
        return [comp['id'] for comp in cls.RECONCILIATION_FORMULA['target_values']['components']]
    
    @classmethod
    def get_gl_description(cls, gl_account: str) -> str:
        """Get human-readable description for a GL account number."""
        return cls.GL_ACCOUNT_MAPPING.get(gl_account, f"Unknown GL: {gl_account}")
    
    @classmethod
    def calculate_variance(cls, actuals: float, target_values: float) -> Dict[str, Any]:
        """Calculate reconciliation variance and determine status."""
        variance = actuals - target_values
        abs_variance = abs(variance)
        threshold = cls.RECONCILIATION_FORMULA['variance']['threshold']
        
        status = 'RECONCILED' if abs_variance < threshold else 'VARIANCE_DETECTED'
        
        return {
            'actuals': actuals,
            'target_values': target_values,
            'variance': variance,
            'abs_variance': abs_variance,
            'threshold': threshold,
            'status': status,
            'is_reconciled': status == 'RECONCILED'
        }
