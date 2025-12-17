"""
Example usage of audit_merge function demonstrating all key features.

This file serves as both documentation and a runnable example.
You can execute it to see the audit_merge function in action.
"""

import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.merge_utils import audit_merge


def example_1_clean_merge():
    """
    Example 1: Clean merge with no duplicates.
    
    This is the ideal scenario - one-to-one relationship.
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Clean Merge (No Duplicates)")
    print("="*80)
    
    # Customer master data - one row per customer
    customers = pd.DataFrame({
        'customer_id': ['C001', 'C002', 'C003'],
        'customer_name': ['ACME Corp', 'TechStart Inc', 'Global Trade Ltd'],
        'balance': [10000.00, 25000.00, 15000.00]
    })
    
    # GL actuals - one entry per customer
    gl_data = pd.DataFrame({
        'customer_id': ['C001', 'C002', 'C003'],
        'gl_account': ['12000', '12000', '12000'],
        'gl_balance': [10000.00, 25000.00, 15000.00]
    })
    
    print("\nCustomer Data (IPE_07):")
    print(customers)
    print("\nGL Data:")
    print(gl_data)
    
    # Audit the merge
    result = audit_merge(
        left=customers,
        right=gl_data,
        on='customer_id',
        name='example1_clean',
        out_dir='/tmp/merge_audit_examples'
    )
    
    print(f"\nAudit Result: {result}")
    print("\n✓ Safe to merge - no duplicates detected!")


def example_2_data_quality_issue():
    """
    Example 2: Data quality issue - duplicate customer records.
    
    This scenario indicates a problem in the source system where
    the same customer appears multiple times in the IPE extract.
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Data Quality Issue (Duplicate Customers in IPE)")
    print("="*80)
    
    # IPE extract with duplicate customer (data quality issue!)
    ipe_extract = pd.DataFrame({
        'customer_id': ['C001', 'C001', 'C002', 'C003'],  # C001 duplicated!
        'document_no': ['INV-001', 'INV-002', 'INV-003', 'INV-004'],
        'amount': [5000.00, 5000.00, 25000.00, 15000.00],
        'posting_date': ['2024-10-15', '2024-10-20', '2024-10-18', '2024-10-22']
    })
    
    # GL data (clean)
    gl_data = pd.DataFrame({
        'customer_id': ['C001', 'C002', 'C003'],
        'gl_balance': [10000.00, 25000.00, 15000.00]
    })
    
    print("\nIPE Extract (has duplicate C001):")
    print(ipe_extract)
    print("\nGL Data (clean):")
    print(gl_data)
    
    # Audit the merge
    result = audit_merge(
        left=ipe_extract,
        right=gl_data,
        on='customer_id',
        name='example2_ipe_duplicates',
        out_dir='/tmp/merge_audit_examples'
    )
    
    print(f"\nAudit Result: {result}")
    print("\n⚠️  WARNING: IPE extract has duplicate customer records!")
    print("   This indicates a data quality issue in the source system.")
    print(f"   Check: /tmp/merge_audit_examples/example2_ipe_duplicates.left_dup_keys.csv")


def example_3_cartesian_product_danger():
    """
    Example 3: Cartesian product risk - both sides have duplicates.
    
    This is the dangerous scenario that audit_merge is designed to catch.
    Merging would create an exploding join.
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Cartesian Product Risk (Both Sides Have Duplicates)")
    print("="*80)
    
    # Multiple transactions per customer
    transactions = pd.DataFrame({
        'customer_id': ['C001', 'C001', 'C002'],
        'transaction_id': ['TXN-A', 'TXN-B', 'TXN-C'],
        'amount': [5000.00, 3000.00, 25000.00],
        'transaction_type': ['Sale', 'Return', 'Sale']
    })
    
    # Multiple GL entries per customer
    gl_entries = pd.DataFrame({
        'customer_id': ['C001', 'C001', 'C002'],
        'gl_entry_id': ['GL-1', 'GL-2', 'GL-3'],
        'gl_amount': [4500.00, 3500.00, 25000.00],
        'gl_account': ['12000', '12000', '12000']
    })
    
    print("\nTransactions (2 for C001):")
    print(transactions)
    print("\nGL Entries (2 for C001):")
    print(gl_entries)
    
    # Audit the merge
    result = audit_merge(
        left=transactions,
        right=gl_entries,
        on='customer_id',
        name='example3_cartesian',
        out_dir='/tmp/merge_audit_examples'
    )
    
    print(f"\nAudit Result: {result}")
    print("\n⚠️  DANGER: Cartesian Product Risk!")
    print("   Customer C001:")
    print("   - Left side: 2 transactions")
    print("   - Right side: 2 GL entries")
    print("   - Merge result: 2 × 2 = 4 rows (EXPLOSION!)")
    print("\n   The merge would duplicate amounts, causing reconciliation errors.")


def example_4_composite_key():
    """
    Example 4: Multi-column join key (composite key).
    
    Shows how to audit merges on multiple columns.
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Composite Join Key (Customer + Product)")
    print("="*80)
    
    # Sales data by customer and product
    sales = pd.DataFrame({
        'customer_id': ['C001', 'C001', 'C002', 'C003'],
        'product_id': ['P100', 'P100', 'P200', 'P300'],  # C001-P100 duplicated
        'order_id': ['ORD-1', 'ORD-2', 'ORD-3', 'ORD-4'],
        'quantity': [10, 5, 20, 15],
        'sale_amount': [1000.00, 500.00, 4000.00, 3000.00]
    })
    
    # Inventory cost by customer and product
    inventory = pd.DataFrame({
        'customer_id': ['C001', 'C002', 'C003'],
        'product_id': ['P100', 'P200', 'P300'],
        'unit_cost': [80.00, 180.00, 180.00],
        'inventory_value': [800.00, 3600.00, 2700.00]
    })
    
    print("\nSales Data (C001-P100 appears twice):")
    print(sales)
    print("\nInventory Data:")
    print(inventory)
    
    # Audit with composite key
    result = audit_merge(
        left=sales,
        right=inventory,
        on=['customer_id', 'product_id'],  # Multiple columns
        name='example4_composite',
        out_dir='/tmp/merge_audit_examples'
    )
    
    print(f"\nAudit Result: {result}")
    print("\n⚠️  Duplicate composite key detected: (C001, P100)")


def example_5_integration_in_workflow():
    """
    Example 5: Integration into a reconciliation workflow.
    
    Shows how to use audit_merge as a safety check in production code.
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Integration in Reconciliation Workflow")
    print("="*80)
    
    def safe_reconciliation(ipe_df, gl_df, join_key):
        """
        Reconciliation workflow with built-in merge auditing.
        """
        print(f"\n1. Auditing merge on key: {join_key}")
        
        # Audit the merge operation
        audit_result = audit_merge(
            left=ipe_df,
            right=gl_df,
            on=join_key,
            name='reconciliation_audit',
            out_dir='/tmp/merge_audit_examples'
        )
        
        # Decision logic based on audit results
        if audit_result['has_duplicates']:
            print("\n   ⚠️  WARNING: Duplicates detected in merge operation!")
            print(f"   - Left duplicates: {audit_result['left_duplicates']}")
            print(f"   - Right duplicates: {audit_result['right_duplicates']}")
            print("   - Action: Review duplicate keys before proceeding")
            
            # In production, you might:
            # - Send alert to reconciliation team
            # - Log to audit trail
            # - Halt automated process for manual review
            return None
        else:
            print("\n   ✓ Merge audit passed - proceeding with reconciliation")
        
        # Safe to merge
        print("\n2. Performing merge...")
        merged = ipe_df.merge(gl_df, on=join_key, how='outer', indicator=True)
        
        print(f"\n3. Reconciliation complete:")
        print(f"   - Total records: {len(merged)}")
        print(f"   - Matched: {(merged['_merge'] == 'both').sum()}")
        print(f"   - IPE only: {(merged['_merge'] == 'left_only').sum()}")
        print(f"   - GL only: {(merged['_merge'] == 'right_only').sum()}")
        
        return merged
    
    # Example data
    ipe = pd.DataFrame({
        'customer_id': ['C001', 'C002', 'C003'],
        'ipe_balance': [10000.00, 25000.00, 15000.00]
    })
    
    gl = pd.DataFrame({
        'customer_id': ['C001', 'C002', 'C003', 'C004'],  # C004 only in GL
        'gl_balance': [10000.00, 25000.00, 15000.00, 5000.00]
    })
    
    print("\nRunning safe reconciliation workflow...")
    safe_reconciliation(ipe, gl, 'customer_id')


def main():
    """Run all examples."""
    print("\n" + "#"*80)
    print("# AUDIT_MERGE FUNCTION - COMPREHENSIVE EXAMPLES")
    print("#"*80)
    
    example_1_clean_merge()
    example_2_data_quality_issue()
    example_3_cartesian_product_danger()
    example_4_composite_key()
    example_5_integration_in_workflow()
    
    print("\n" + "#"*80)
    print("# ALL EXAMPLES COMPLETE")
    print("#"*80)
    print("\n📁 Output files: /tmp/merge_audit_examples/")
    print("   - merge_audit.log")
    print("   - *.left_dup_keys.csv")
    print("   - *.right_dup_keys.csv")


if __name__ == '__main__':
    main()
