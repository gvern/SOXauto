#!/usr/bin/env python3
"""
Test database connectivity and basic query execution.

This test verifies:
1. AWS Secrets Manager access
2. Database connection establishment
3. Parameterized query execution

Run:
    python3 tests/test_database_connection.py
"""
import os
import sys
import pyodbc

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.aws_utils import AWSSecretsManager


def test_secret_manager():
    """Test AWS Secrets Manager access."""
    print("\n🔍 Testing AWS Secrets Manager Access...")
    print("-" * 70)
    
    aws_region = os.getenv("AWS_REGION", "eu-west-1")
    
    try:
        sm = AWSSecretsManager(aws_region)
        conn_str = sm.get_secret("DB_CREDENTIALS_NAV_BI")
        print(f"✅ Secret retrieved successfully")
        print(f"   Connection string format: {conn_str[:20]}...")
        return conn_str
    except Exception as e:
        print(f"❌ Secrets Manager error: {e}")
        return None


def test_database_connection(conn_str):
    """Test database connection."""
    print("\n🔍 Testing Database Connection...")
    print("-" * 70)
    
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        print("✅ Database connection successful")
        
        # Test simple query
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print(f"   SQL Server version: {version[:50]}...")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False


def test_parameterized_query(conn_str):
    """Test parameterized query execution."""
    print("\n🔍 Testing Parameterized Query Execution...")
    print("-" * 70)
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Test query with parameter
        test_query = """
            SELECT COUNT(*) as record_count
            FROM [dbo].[Customer Ledger Entries]
            WHERE [Posting Date] < ?
        """
        
        cutoff_date = os.getenv("CUTOFF_DATE", "2024-01-01")
        cursor.execute(test_query, (cutoff_date,))
        result = cursor.fetchone()
        
        print(f"✅ Parameterized query executed successfully")
        print(f"   Records found (before {cutoff_date}): {result[0]:,}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Parameterized query error: {e}")
        return False


def main():
    """Run all connection tests."""
    print("=" * 70)
    print("DATABASE CONNECTION TESTING")
    print("=" * 70)
    
    # Check environment
    if not os.getenv("AWS_REGION"):
        print("❌ AWS_REGION environment variable not set")
        print("   Run: export AWS_REGION='eu-west-1'")
        return False
    
    # Test sequence
    conn_str = test_secret_manager()
    if not conn_str:
        return False
    
    if not test_database_connection(conn_str):
        return False
    
    if not test_parameterized_query(conn_str):
        return False
    
    print("\n" + "=" * 70)
    print("✅ ALL CONNECTION TESTS PASSED")
    print("=" * 70)
    print("\nNext step: Run single IPE extraction test")
    print("  python3 tests/test_single_ipe_extraction.py")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
