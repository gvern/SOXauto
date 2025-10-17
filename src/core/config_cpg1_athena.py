"""
IPE Configuration for AWS Athena - C-PG-1 Reconciliation
Based on Official Common Report Reference from Confluence

This configuration maps SQL Server sources to Athena equivalents for the C-PG-1 control.

Data Sources (Official Mapping):
- CR_04: NAV GL Balance (ACTUALS)
- IPE_07: Customer AR Balances (Detailed + Summary)
- IPE_08: Voucher Liabilities (BOB)
- IPE_10: Customer Prepayments (OMS)
- IPE_12: Packages Not Reconciled (OMS)
- IPE_31: Collection Accounts (Multi-table join)
- IPE_34: Marketplace Refund Liability (OMS)
- CR_05: FX Rates (Supporting)

STATUS: Table names marked with ??? need confirmation from technical team
"""

from typing import Dict, Any, List
from datetime import datetime


class AthenaTableMapping:
    """
    Official SQL Server → Athena table mapping
    Based on Common Report Reference documentation
    
    TODO: Replace all ??? with actual Athena table names from Carlos/Joao
    """
    
    # ===== PRIORITY 1: ACTUALS (NAV GL Balance) =====
    
    CR_04_NAV_GL_BALANCE = {
        'report_id': 'CR_04',
        'description': 'NAV GL Balance (ACTUALS side of reconciliation)',
        'sql_server_db': 'AIG_Nav_Jumia_Reconciliation',
        'sql_server_table': 'V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT',
        'athena_database': '???',  # TODO: process_central_fin_dwh?
        'athena_table': '???',     # TODO: Confirm table name
        'purpose': 'Source of truth - Final GL balance from NAV',
        'priority': 'CRITICAL'
    }
    
    # ===== PRIORITY 2: NAV BI Tables (Customer Ledger) =====
    
    IPE_07_CUSTOMER_LEDGER_DETAILED = {
        'report_id': 'IPE_07',
        'description': 'Detailed Customer Ledger Entry',
        'sql_server_db': 'AIG_Nav_DW',
        'sql_server_table': 'Detailed Customer Ledg_ Entry',
        'athena_database': '???',  # TODO: process_central_fin_dwh?
        'athena_table': '???',     # TODO: detailed_customer_ledg_entry?
        'purpose': 'Customer AR balances - detailed entries',
        'priority': 'HIGH'
    }
    
    IPE_07_CUSTOMER_LEDGER_SUMMARY = {
        'report_id': 'IPE_07',
        'description': 'Customer Ledger Entries (Summary)',
        'sql_server_db': 'AIG_Nav_DW',
        'sql_server_table': 'Customer Ledger Entries',
        'athena_database': '???',  # TODO: process_central_fin_dwh?
        'athena_table': '???',     # TODO: customer_ledger_entries?
        'purpose': 'Customer AR balances - summary entries',
        'priority': 'HIGH'
    }
    
    # ===== PRIORITY 3: Multi-Purpose OMS Table (Used by 3 IPEs) =====
    
    RPT_SOI_MULTI_PURPOSE = {
        'report_ids': ['IPE_10', 'IPE_12', 'IPE_34'],
        'description': 'Statement of Income Report (multi-purpose)',
        'sql_server_db': 'AIG_Nav_Jumia_Reconciliation',
        'sql_server_table': 'RPT_SOI',
        'athena_database': '???',  # TODO: process_central_fin_dwh?
        'athena_table': '???',     # TODO: rpt_soi?
        'purposes': {
            'IPE_10': 'Customer Prepayments (GL 18350)',
            'IPE_12': 'Packages Delivered Not Reconciled (GL 13005, 13024)',
            'IPE_34': 'Marketplace Refund Liability (GL 18317)'
        },
        'priority': 'HIGH',
        'note': 'Same table used 3 times with different WHERE clause filters'
    }
    
    # ===== PRIORITY 4: BOB Voucher Table =====
    
    IPE_08_VOUCHER_CLOSING = {
        'report_id': 'IPE_08',
        'description': 'Store Credit Voucher Closing Balances',
        'sql_server_db': 'AIG_Nav_Jumia_Reconciliation',
        'sql_server_table': 'V_STORECREDITVOUCHER_CLOSING',
        'athena_database': '???',  # TODO: process_pg_bob? or process_central_fin_dwh?
        'athena_table': '???',     # TODO: v_storecreditvoucher_closing?
        'purpose': 'Voucher liabilities from BOB system (GL 18412)',
        'priority': 'MEDIUM'
    }
    
    # ===== PRIORITY 5: Multi-Table Join (Collection Accounts) =====
    
    IPE_31_CASHREC_TRANSACTION = {
        'report_id': 'IPE_31',
        'description': 'Cash Receipt Transactions',
        'sql_server_db': 'AIG_Nav_Jumia_Reconciliation',
        'sql_server_table': 'RPT_CASHREC_TRANSACTION',
        'athena_database': '???',  # TODO: process_central_fin_dwh?
        'athena_table': '???',     # TODO: rpt_cashrec_transaction?
        'purpose': 'Collection accounts - cash receipts',
        'priority': 'MEDIUM'
    }
    
    IPE_31_CASHREC_REALLOCATIONS = {
        'report_id': 'IPE_31',
        'description': 'Cash Receipt Reallocations',
        'sql_server_db': 'AIG_Nav_Jumia_Reconciliation',
        'sql_server_table': 'RPT_CASHREC_REALLOCATIONS',
        'athena_database': '???',  # TODO: process_central_fin_dwh?
        'athena_table': '???',     # TODO: rpt_cashrec_reallocations?
        'purpose': 'Collection accounts - reallocations',
        'priority': 'MEDIUM'
    }
    
    IPE_31_PACKLIST_PAYMENTS = {
        'report_id': 'IPE_31',
        'description': 'Packlist Payments',
        'sql_server_db': 'AIG_Nav_Jumia_Reconciliation',
        'sql_server_table': 'RPT_PACKLIST_PAYMENTS',
        'athena_database': '???',  # TODO: process_central_fin_dwh?
        'athena_table': '???',     # TODO: rpt_packlist_payments?
        'purpose': 'Collection accounts - packlist payments',
        'priority': 'MEDIUM'
    }
    
    IPE_31_CASHDEPOSIT = {
        'report_id': 'IPE_31',
        'description': 'Cash Deposits',
        'sql_server_db': 'AIG_Nav_Jumia_Reconciliation',
        'sql_server_table': 'RPT_CASHDEPOSIT',
        'athena_database': '???',  # TODO: process_central_fin_dwh?
        'athena_table': '???',     # TODO: rpt_cashdeposit?
        'purpose': 'Collection accounts - cash deposits',
        'priority': 'MEDIUM'
    }
    
    # ===== PRIORITY 6: FX Rates (Supporting Data) =====
    
    CR_05_FX_RATES = {
        'report_id': 'CR_05',
        'description': 'Foreign Exchange Rates',
        'sql_server_db': 'AIG_Nav_Jumia_Reconciliation',
        'sql_server_table': 'RPT_FX_RATES',
        'athena_database': '???',  # TODO: process_central_fin_dwh?
        'athena_table': '???',     # TODO: rpt_fx_rates?
        'purpose': 'Currency conversion for all reconciliations',
        'priority': 'LOW'
    }


class IPEConfigAthena:
    """
    IPE Query Configurations for C-PG-1 Reconciliation
    
    Each config includes:
    - Placeholder Athena query (needs table names filled in)
    - Expected columns
    - Validation rules
    - Business logic notes
    """
    
    # ===== CR_04: ACTUALS (NAV GL Balance) =====
    
    CR_04_CONFIG = {
        'id': 'CR_04',
        'description': 'NAV GL Balance (ACTUALS)',
        'mapping': AthenaTableMapping.CR_04_NAV_GL_BALANCE,
        
        # TODO: Fill in actual table name
        'query_template': '''
            SELECT 
                country,
                gl_account_no,
                posting_date,
                amount_lcy,
                currency_code
            FROM {athena_database}.{athena_table}
            WHERE posting_date <= DATE '{cutoff_date}'
                AND country = '{country}'
                AND gl_account_no IN ('13003', '13004', '13005', '13009', 
                                       '13024', '18317', '18350', '18412')
        ''',
        
        'gl_accounts': ['13003', '13004', '13005', '13009', '13024', 
                        '18317', '18350', '18412'],
        
        'expected_columns': [
            'country',
            'gl_account_no',
            'posting_date',
            'amount_lcy',
            'currency_code'
        ]
    }
    
    # ===== IPE_07: Customer AR Balances =====
    
    IPE_07_CONFIG = {
        'id': 'IPE_07',
        'description': 'Customer AR Balances (Detailed + Summary)',
        'mappings': [
            AthenaTableMapping.IPE_07_CUSTOMER_LEDGER_DETAILED,
            AthenaTableMapping.IPE_07_CUSTOMER_LEDGER_SUMMARY
        ],
        
        # Query 1: Detailed entries
        'query_detailed_template': '''
            SELECT 
                country,
                posting_date,
                customer_no,
                document_no,
                amount_lcy,
                entry_type
            FROM {athena_database}.{athena_table_detailed}
            WHERE posting_date <= DATE '{cutoff_date}'
                AND entry_type = 'Application'
                AND country = '{country}'
        ''',
        
        # Query 2: Summary entries
        'query_summary_template': '''
            SELECT 
                country,
                posting_date,
                customer_no,
                document_no,
                amount_lcy
            FROM {athena_database}.{athena_table_summary}
            WHERE posting_date <= DATE '{cutoff_date}'
                AND country = '{country}'
        ''',
        
        'gl_accounts': ['13003', '13004', '13009'],
        
        'expected_columns': [
            'country',
            'posting_date',
            'customer_no',
            'document_no',
            'amount_lcy'
        ]
    }
    
    # ===== IPE_10: Customer Prepayments =====
    
    IPE_10_CONFIG = {
        'id': 'IPE_10',
        'description': 'Customer Prepayments TV',
        'mapping': AthenaTableMapping.RPT_SOI_MULTI_PURPOSE,
        
        # TODO: Need to know which columns to filter on for prepayments
        'query_template': '''
            SELECT 
                country,
                posting_date,
                transaction_type,
                amount_lcy,
                gl_account
            FROM {athena_database}.{athena_table}
            WHERE posting_date <= DATE '{cutoff_date}'
                AND country = '{country}'
                AND gl_account = '18350'
                -- TODO: Add filter for prepayment transaction type
        ''',
        
        'gl_accounts': ['18350'],
        
        'filter_note': 'Need to confirm: What column/value identifies prepayment transactions?'
    }
    
    # ===== IPE_12: Packages Not Reconciled =====
    
    IPE_12_CONFIG = {
        'id': 'IPE_12',
        'description': 'TV - Packages Delivered Not Reconciled',
        'mapping': AthenaTableMapping.RPT_SOI_MULTI_PURPOSE,
        
        # TODO: Need to know which columns to filter on for unreconciled packages
        'query_template': '''
            SELECT 
                country,
                posting_date,
                transaction_type,
                amount_lcy,
                gl_account
            FROM {athena_database}.{athena_table}
            WHERE posting_date <= DATE '{cutoff_date}'
                AND country = '{country}'
                AND gl_account IN ('13005', '13024')
                -- TODO: Add filter for unreconciled package status
        ''',
        
        'gl_accounts': ['13005', '13024'],
        
        'filter_note': 'Need to confirm: What column/value identifies unreconciled packages?'
    }
    
    # ===== IPE_34: Refund Liability =====
    
    IPE_34_CONFIG = {
        'id': 'IPE_34',
        'description': 'Marketplace Refund Liability',
        'mapping': AthenaTableMapping.RPT_SOI_MULTI_PURPOSE,
        
        # TODO: Need to know which columns to filter on for refunds
        'query_template': '''
            SELECT 
                country,
                posting_date,
                transaction_type,
                amount_lcy,
                gl_account
            FROM {athena_database}.{athena_table}
            WHERE posting_date <= DATE '{cutoff_date}'
                AND country = '{country}'
                AND gl_account = '18317'
                -- TODO: Add filter for refund transaction type
        ''',
        
        'gl_accounts': ['18317'],
        
        'filter_note': 'Need to confirm: What column/value identifies refund transactions?'
    }
    
    # ===== IPE_08: Voucher Liabilities =====
    
    IPE_08_CONFIG = {
        'id': 'IPE_08',
        'description': 'TV - Voucher Liabilities',
        'mapping': AthenaTableMapping.IPE_08_VOUCHER_CLOSING,
        
        # TODO: Fill in actual table name
        'query_template': '''
            SELECT 
                country,
                closing_date,
                voucher_id,
                amount_lcy,
                status
            FROM {athena_database}.{athena_table}
            WHERE closing_date = DATE '{cutoff_date}'
                AND country = '{country}'
                AND status = 'OPEN'
        ''',
        
        'gl_accounts': ['18412'],
        
        'expected_columns': [
            'country',
            'closing_date',
            'voucher_id',
            'amount_lcy',
            'status'
        ]
    }
    
    # ===== IPE_31: Collection Accounts (Multi-table join) =====
    
    IPE_31_CONFIG = {
        'id': 'IPE_31',
        'description': 'PG Detailed TV Extraction (Collection Accounts)',
        'mappings': [
            AthenaTableMapping.IPE_31_CASHREC_TRANSACTION,
            AthenaTableMapping.IPE_31_CASHREC_REALLOCATIONS,
            AthenaTableMapping.IPE_31_PACKLIST_PAYMENTS,
            AthenaTableMapping.IPE_31_CASHDEPOSIT
        ],
        
        # TODO: Need to know join keys between these 4 tables
        'query_template': '''
            -- Complex multi-table join
            -- TODO: Confirm join keys and exact schema
            
            SELECT 
                t.country,
                t.transaction_date,
                t.transaction_id,
                t.amount_lcy,
                r.reallocation_amount,
                p.payment_amount,
                d.deposit_amount
            FROM {athena_database}.{table_transaction} t
            LEFT JOIN {athena_database}.{table_reallocations} r
                ON t.transaction_id = r.transaction_id  -- TODO: Confirm join key
            LEFT JOIN {athena_database}.{table_payments} p
                ON t.transaction_id = p.transaction_id  -- TODO: Confirm join key
            LEFT JOIN {athena_database}.{table_deposit} d
                ON t.transaction_id = d.transaction_id  -- TODO: Confirm join key
            WHERE t.transaction_date <= DATE '{cutoff_date}'
                AND t.country = '{country}'
        ''',
        
        'join_note': 'Need to confirm: What are the join keys between the 4 tables?'
    }
    
    # ===== CR_05: FX Rates (Supporting) =====
    
    CR_05_CONFIG = {
        'id': 'CR_05',
        'description': 'FX Rates',
        'mapping': AthenaTableMapping.CR_05_FX_RATES,
        
        # TODO: Fill in actual table name
        'query_template': '''
            SELECT 
                currency_code,
                rate_date,
                exchange_rate,
                base_currency
            FROM {athena_database}.{athena_table}
            WHERE rate_date <= DATE '{cutoff_date}'
        ''',
        
        'expected_columns': [
            'currency_code',
            'rate_date',
            'exchange_rate',
            'base_currency'
        ]
    }


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


# Quick access to all configs
ALL_CPG1_CONFIGS = {
    'CR_04': IPEConfigAthena.CR_04_CONFIG,
    'IPE_07': IPEConfigAthena.IPE_07_CONFIG,
    'IPE_08': IPEConfigAthena.IPE_08_CONFIG,
    'IPE_10': IPEConfigAthena.IPE_10_CONFIG,
    'IPE_12': IPEConfigAthena.IPE_12_CONFIG,
    'IPE_31': IPEConfigAthena.IPE_31_CONFIG,
    'IPE_34': IPEConfigAthena.IPE_34_CONFIG,
    'CR_05': IPEConfigAthena.CR_05_CONFIG,
}
