"""
C-PG-1 Reconciliation Business Logic

This defines how to calculate the reconciliation:
ACTUALS (CR_04) vs TARGET VALUES (sum of 6 components)

Extracted from legacy config_cpg1_athena.py to keep reconciliation logic
separate from data configuration.
"""

from typing import Dict, Any, List, Optional


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
            'threshold': 1000,  # Legacy threshold for backward compatibility
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
    def calculate_variance(
        cls,
        actuals: float,
        target_values: float,
        use_threshold_catalog: bool = False,
        country_code: Optional[str] = None,
        gl_account: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate reconciliation variance and determine status.
        
        Args:
            actuals: Actual amount from GL balance
            target_values: Sum of target value components
            use_threshold_catalog: If True, use threshold catalog system.
                                  Requires country_code parameter.
            country_code: Country code for threshold resolution (required if use_threshold_catalog=True)
            gl_account: GL account for threshold resolution (optional, improves precision)
        
        Returns:
            Dictionary with variance calculation results and status
        """
        variance = actuals - target_values
        abs_variance = abs(variance)
        
        # Determine threshold and status
        if use_threshold_catalog:
            if not country_code:
                raise ValueError(
                    "country_code is required when use_threshold_catalog=True"
                )
            
            # Use threshold catalog system
            from src.core.reconciliation.thresholds import (
                resolve_bucket_threshold,
                ThresholdType,
            )
            
            resolved = resolve_bucket_threshold(
                country_code=country_code,
                gl_account=gl_account,
            )
            
            threshold = resolved.value_usd
            
            # Note: This assumes variance is already in USD if using catalog
            # For LCY variance, caller should convert to USD first
            status = 'RECONCILED' if abs_variance < threshold else 'VARIANCE_DETECTED'
            
            return {
                'actuals': actuals,
                'target_values': target_values,
                'variance': variance,
                'abs_variance': abs_variance,
                'threshold': threshold,
                'status': status,
                'is_reconciled': status == 'RECONCILED',
                'threshold_source': 'catalog',
                'threshold_contract_version': resolved.contract_version,
                'threshold_contract_hash': resolved.contract_hash,
                'threshold_rule_description': resolved.matched_rule_description,
            }
        else:
            # Legacy behavior: use hardcoded threshold (backward compatibility)
            threshold = cls.RECONCILIATION_FORMULA['variance']['threshold']
            status = 'RECONCILED' if abs_variance < threshold else 'VARIANCE_DETECTED'
            
            return {
                'actuals': actuals,
                'target_values': target_values,
                'variance': variance,
                'abs_variance': abs_variance,
                'threshold': threshold,
                'status': status,
                'is_reconciled': status == 'RECONCILED',
                'threshold_source': 'legacy',
            }

