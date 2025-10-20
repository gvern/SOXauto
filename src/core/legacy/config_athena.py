"""
config_athena.py (shim)

Purpose
- Eliminate redundancy by delegating shared IPEs to the C-PG-1 Athena config
- Preserve the public API used by tests: IPEConfigAthena.load_ipe_config / list_ipes

Notes
- IPE_09 (BOB) remains here as the currently confirmed working config
- IPE_07 and IPE_08 are delegated to src.core.config_cpg1_athena.IPEConfigAthena
"""

from typing import Dict, Any, List


class IPEConfigAthena:
    """Thin wrapper exposing a stable API and de-duplicated config entries."""

    # Keep the confirmed-working IPE_09 locally
    _IPE_09: Dict[str, Any] = {
        'id': 'IPE_09',
        'description': 'BOB Sales Orders',
        'athena_database': 'process_pg_bob',
        'query': '''
            SELECT 
                order_date,
                order_id,
                customer_id,
                total_amount,
                order_status
            FROM pg_bob_sales_order
            WHERE order_date < {cutoff_date}
            ORDER BY order_date DESC
        ''',
        'validation': {
            'critical_columns': ['order_date', 'order_id', 'customer_id', 'total_amount'],
            'accuracy_positive': [{'name': 'has_completed_orders', 'condition': "order_status == 'completed'"}],
            'accuracy_negative': [{'name': 'no_negative_amounts', 'condition': 'total_amount < 0'}],
        },
    }

    @classmethod
    def _cpg1_map(cls) -> Dict[str, Dict[str, Any]]:
        """Load C-PG-1 Athena configs (delegated to avoid duplication)."""
        try:
            from src.core.config_cpg1_athena import IPEConfigAthena as CPG1
            return {
                'IPE_07': CPG1.IPE_07_CONFIG,
                'IPE_08': CPG1.IPE_08_CONFIG,
                # You can add more delegated IPEs over time (e.g., IPE_10, IPE_12...)
            }
        except Exception:
            # Soft fallback if CPG1 module is not available in some contexts
            return {}

    @classmethod
    def load_ipe_config(cls, ipe_id: str) -> Dict[str, Any]:
        """Return the de-duplicated IPE configuration by ID."""
        if ipe_id == 'IPE_09':
            return cls._IPE_09
        cpg1 = cls._cpg1_map()
        if ipe_id in cpg1:
            return cpg1[ipe_id]
        raise ValueError(f"Unknown IPE: {ipe_id}")

    @classmethod
    def list_ipes(cls) -> List[str]:
        """List all available IPEs exposed by this shim."""
        return ['IPE_07', 'IPE_08', 'IPE_09']


if __name__ == '__main__':
    print("Available IPEs (Athena shim):")
    for ipe_id in IPEConfigAthena.list_ipes():
        cfg = IPEConfigAthena.load_ipe_config(ipe_id)
        print(f"  {ipe_id}: {cfg.get('description')}")
        print(f"    Database: {cfg.get('athena_database')}")
