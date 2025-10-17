#!/usr/bin/env python3
"""
Test AWS Athena Access and Discovery

This script tests your access to AWS Athena and helps discover:
1. Available Athena databases
2. Available tables in each database
3. Sample data from tables
4. Schema information

Usage:
    export AWS_PROFILE=007809111365_Data-Prod-DataAnalyst-NonFinance
    export AWS_REGION=eu-west-1
    python3 tests/test_athena_access.py
"""

import boto3
import os
from typing import List, Dict
import time

# Configuration
AWS_PROFILE = os.getenv('AWS_PROFILE', '007809111365_Data-Prod-DataAnalyst-NonFinance')
AWS_REGION = os.getenv('AWS_REGION', 'eu-west-1')
ATHENA_S3_OUTPUT = os.getenv('ATHENA_S3_OUTPUT', 's3://athena-query-results-s3-ew1-production-jdata/')

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_athena_permissions():
    """Test basic Athena permissions"""
    print_header("Testing Athena Permissions")
    
    try:
        client = boto3.client('athena', region_name=AWS_REGION)
        
        # Test ListDataCatalogs
        catalogs = client.list_data_catalogs()
        print(f"✅ Can list data catalogs: {len(catalogs.get('DataCatalogsSummary', []))} catalog(s)")
        
        for catalog in catalogs.get('DataCatalogsSummary', []):
            print(f"   - {catalog['CatalogName']} ({catalog['Type']})")
        
        return True
    except Exception as e:
        print(f"❌ Cannot access Athena: {e}")
        return False

def list_databases() -> List[str]:
    """List all Athena databases"""
    print_header("Discovering Athena Databases")
    
    client = boto3.client('athena', region_name=AWS_REGION)
    databases = []
    
    try:
        # Execute SHOW DATABASES query
        response = client.start_query_execution(
            QueryString='SHOW DATABASES',
            ResultConfiguration={'OutputLocation': ATHENA_S3_OUTPUT}
        )
        
        query_execution_id = response['QueryExecutionId']
        
        # Wait for query to complete
        print(f"⏳ Executing query: {query_execution_id}")
        while True:
            status = client.get_query_execution(QueryExecutionId=query_execution_id)
            state = status['QueryExecution']['Status']['State']
            
            if state == 'SUCCEEDED':
                break
            elif state in ['FAILED', 'CANCELLED']:
                reason = status['QueryExecution']['Status'].get('StateChangeReason', 'Unknown')
                print(f"❌ Query failed: {reason}")
                return []
            
            time.sleep(1)
        
        # Get results
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        
        # Extract database names (skip header row)
        for row in results['ResultSet']['Rows'][1:]:
            db_name = row['Data'][0].get('VarCharValue', '')
            if db_name:
                databases.append(db_name)
                print(f"   📊 {db_name}")
        
        print(f"\n✅ Found {len(databases)} database(s)")
        return databases
        
    except Exception as e:
        print(f"❌ Error listing databases: {e}")
        return []

def list_tables(database: str) -> List[str]:
    """List all tables in a database"""
    print(f"\n📋 Tables in database '{database}':")
    
    client = boto3.client('athena', region_name=AWS_REGION)
    tables = []
    
    try:
        response = client.start_query_execution(
            QueryString=f'SHOW TABLES IN {database}',
            QueryExecutionContext={'Database': database},
            ResultConfiguration={'OutputLocation': ATHENA_S3_OUTPUT}
        )
        
        query_execution_id = response['QueryExecutionId']
        
        # Wait for completion
        while True:
            status = client.get_query_execution(QueryExecutionId=query_execution_id)
            state = status['QueryExecution']['Status']['State']
            
            if state == 'SUCCEEDED':
                break
            elif state in ['FAILED', 'CANCELLED']:
                print(f"   ❌ Query failed")
                return []
            
            time.sleep(0.5)
        
        # Get results
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        
        # Extract table names
        for row in results['ResultSet']['Rows'][1:]:
            table_name = row['Data'][0].get('VarCharValue', '')
            if table_name:
                tables.append(table_name)
                print(f"   - {table_name}")
        
        print(f"   Total: {len(tables)} table(s)")
        return tables
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return []

def get_table_schema(database: str, table: str):
    """Get schema information for a table"""
    print(f"\n🔍 Schema for {database}.{table}:")
    
    client = boto3.client('athena', region_name=AWS_REGION)
    
    try:
        response = client.start_query_execution(
            QueryString=f'DESCRIBE {database}.{table}',
            QueryExecutionContext={'Database': database},
            ResultConfiguration={'OutputLocation': ATHENA_S3_OUTPUT}
        )
        
        query_execution_id = response['QueryExecutionId']
        
        # Wait for completion
        while True:
            status = client.get_query_execution(QueryExecutionId=query_execution_id)
            state = status['QueryExecution']['Status']['State']
            
            if state == 'SUCCEEDED':
                break
            elif state in ['FAILED', 'CANCELLED']:
                print(f"   ❌ Query failed")
                return
            
            time.sleep(0.5)
        
        # Get results
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        
        # Print schema
        for row in results['ResultSet']['Rows'][1:]:  # Skip header
            col_name = row['Data'][0].get('VarCharValue', '')
            col_type = row['Data'][1].get('VarCharValue', '') if len(row['Data']) > 1 else ''
            print(f"   - {col_name}: {col_type}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")

def sample_table_data(database: str, table: str, limit: int = 5):
    """Get sample data from a table"""
    print(f"\n📄 Sample data from {database}.{table} (limit {limit}):")
    
    client = boto3.client('athena', region_name=AWS_REGION)
    
    try:
        response = client.start_query_execution(
            QueryString=f'SELECT * FROM {database}.{table} LIMIT {limit}',
            QueryExecutionContext={'Database': database},
            ResultConfiguration={'OutputLocation': ATHENA_S3_OUTPUT}
        )
        
        query_execution_id = response['QueryExecutionId']
        
        # Wait for completion
        while True:
            status = client.get_query_execution(QueryExecutionId=query_execution_id)
            state = status['QueryExecution']['Status']['State']
            
            if state == 'SUCCEEDED':
                break
            elif state in ['FAILED', 'CANCELLED']:
                print(f"   ❌ Query failed")
                return
            
            time.sleep(0.5)
        
        # Get results
        results = client.get_query_results(QueryExecutionId=query_execution_id)
        
        # Print sample data
        rows = results['ResultSet']['Rows']
        if len(rows) <= 1:
            print("   (No data)")
            return
        
        # Print header
        headers = [col.get('VarCharValue', '') for col in rows[0]['Data']]
        print(f"   {' | '.join(headers)}")
        print(f"   {'-' * 60}")
        
        # Print data rows
        for row in rows[1:limit+1]:
            values = [col.get('VarCharValue', 'NULL') for col in row['Data']]
            print(f"   {' | '.join(values)}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    """Main test function"""
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "       AWS ATHENA ACCESS TEST & DISCOVERY".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    
    print(f"\nConfiguration:")
    print(f"  AWS Profile: {AWS_PROFILE}")
    print(f"  AWS Region: {AWS_REGION}")
    print(f"  Athena S3 Output: {ATHENA_S3_OUTPUT}")
    
    # Test permissions
    if not test_athena_permissions():
        print("\n❌ Cannot access Athena. Check your AWS credentials and permissions.")
        return
    
    # Discover databases
    databases = list_databases()
    
    if not databases:
        print("\n⚠️  No databases found or insufficient permissions.")
        print("\nNext steps:")
        print("  1. Verify your AWS_PROFILE has Athena access")
        print("  2. Ask your team for the correct Athena database names")
        return
    
    # Explore interesting databases
    interesting_keywords = ['nav', 'fin', 'bob', 'rec', 'dwh', 'bi']
    
    print_header("Exploring Relevant Databases")
    
    for db in databases:
        # Check if database name contains interesting keywords
        if any(keyword in db.lower() for keyword in interesting_keywords):
            print(f"\n🔍 Exploring '{db}' (matches keywords: {', '.join([k for k in interesting_keywords if k in db.lower()])})")
            
            # List tables
            tables = list_tables(db)
            
            # If we find interesting tables, get more details
            interesting_tables = ['g_l_entries', 'gl_entries', 'ledger', 'rpt_soi', 'orders', 'voucher']
            
            for table in tables[:10]:  # Limit to first 10 tables
                if any(keyword in table.lower() for keyword in interesting_tables):
                    get_table_schema(db, table)
                    sample_table_data(db, table, limit=3)
    
    # Summary
    print_header("Discovery Summary")
    print(f"\n✅ Successfully connected to AWS Athena")
    print(f"📊 Found {len(databases)} database(s)")
    print(f"\n📝 Next Steps:")
    print(f"   1. Review the databases and tables above")
    print(f"   2. Identify which databases map to NAV_BI, FINREC, BOB")
    print(f"   3. Update IPE configurations with correct database/table names")
    print(f"   4. Install awswrangler: pip install awswrangler")
    print(f"   5. Refactor IPE extraction to use Athena instead of SQL Server")

if __name__ == "__main__":
    main()
