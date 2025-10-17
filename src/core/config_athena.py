# config_athena.py
"""
IPE Configuration for AWS Athena (V2)

This configuration uses Athena databases instead of SQL Server.
Queries use Athena SQL syntax (Presto/Trino based).

Key Differences from SQL Server version:
- Uses athena_database instead of secret_name
- Column names use snake_case (e.g., posting_date instead of [Posting Date])
- Date format: DATE('YYYY-MM-DD') instead of 'YYYY-MM-DD'
- No square brackets in identifiers
"""

from typing import Dict, Any, List


class IPEConfigAthena:
    """IPE configurations for AWS Athena"""
    
    # TODO: Confirm these database/table names with Carlos/Joao
    # Current values are PLACEHOLDERS based on discovery
    
    IPE_07_CONFIG = {
        'id': 'IPE_07',
        'description': 'Detailed customer ledger entries (G/L Entries)',
        
        # Athena configuration
        'athena_database': 'process_central_fin_dwh',  # TODO: CONFIRM with team
        
        # Query using Athena SQL syntax
        # TODO: Confirm table and column names
        'query': '''
            SELECT 
                posting_date,
                gl_account_no,
                amount,
                description,
                document_no,
                entry_no
            FROM g_l_entries
            WHERE posting_date < {cutoff_date}
            ORDER BY posting_date DESC
        ''',
        
        # Validation rules
        'validation': {
            'critical_columns': [
                'posting_date',
                'gl_account_no',
                'amount'
            ],
            'accuracy_positive': [
                {
                    'name': 'has_recent_entries',
                    'condition': "posting_date >= '2024-01-01'"
                }
            ],
            'accuracy_negative': [
                {
                    'name': 'no_future_dates',
                    'condition': "posting_date > datetime.now().strftime('%Y-%m-%d')"
                }
            ]
        }
    }
    
    IPE_08_CONFIG = {
        'id': 'IPE_08',
        'description': 'Financial reconciliation report (RPT_SOI)',
        
        # Athena configuration
        'athena_database': 'process_central_fin_dwh',  # TODO: CONFIRM with team
        
        # Query
        # TODO: Confirm table and column names for FINREC data
        'query': '''
            SELECT 
                report_date,
                account_code,
                balance,
                description
            FROM rpt_soi
            WHERE report_date < {cutoff_date}
            ORDER BY report_date DESC
        ''',
        
        'validation': {
            'critical_columns': [
                'report_date',
                'account_code',
                'balance'
            ],
            'accuracy_positive': [],
            'accuracy_negative': []
        }
    }
    
    IPE_09_CONFIG = {
        'id': 'IPE_09',
        'description': 'BOB Sales Orders',
        
        # Athena configuration
        'athena_database': 'process_pg_bob',  # ✅ CONFIRMED from discovery
        
        # Query
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
            'critical_columns': [
                'order_date',
                'order_id',
                'customer_id',
                'total_amount'
            ],
            'accuracy_positive': [
                {
                    'name': 'has_completed_orders',
                    'condition': "order_status == 'completed'"
                }
            ],
            'accuracy_negative': [
                {
                    'name': 'no_negative_amounts',
                    'condition': "total_amount < 0"
                }
            ]
        }
    }
    
    @classmethod
    def load_ipe_config(cls, ipe_id: str) -> Dict[str, Any]:
        """
        Load configuration for a specific IPE.
        
        Args:
            ipe_id: IPE identifier (e.g., 'IPE_07')
            
        Returns:
            IPE configuration dictionary
            
        Raises:
            ValueError: If IPE not found
        """
        config_map = {
            'IPE_07': cls.IPE_07_CONFIG,
            'IPE_08': cls.IPE_08_CONFIG,
            'IPE_09': cls.IPE_09_CONFIG,
        }
        
        if ipe_id not in config_map:
            raise ValueError(f"Unknown IPE: {ipe_id}")
        
        return config_map[ipe_id]
    
    @classmethod
    def list_ipes(cls) -> List[str]:
        """
        Get list of all configured IPEs.
        
        Returns:
            List of IPE identifiers
        """
        return ['IPE_07', 'IPE_08', 'IPE_09']


# Example usage
if __name__ == '__main__':
    print("Available IPEs (Athena version):")
    for ipe_id in IPEConfigAthena.list_ipes():
        config = IPEConfigAthena.load_ipe_config(ipe_id)
        print(f"  {ipe_id}: {config['description']}")
        print(f"    Database: {config['athena_database']}")
        print()
