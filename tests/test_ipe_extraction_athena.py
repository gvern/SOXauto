#!/usr/bin/env python3
"""
Test IPE Extraction with AWS Athena (V2)

This is the refactored version using awswrangler and Athena.
Replaces the SQL Server connection approach.

Usage:
    export AWS_PROFILE=007809111365_Data-Prod-DataAnalyst-NonFinance
    export AWS_REGION=eu-west-1
    export CUTOFF_DATE=2024-12-31
    python3 tests/test_ipe_extraction_athena.py
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.runners import IPERunnerAthena, IPEValidationError, IPEConnectionError
from src.core.catalog import get_athena_config, list_athena_ipes
from src.core.evidence import DigitalEvidenceManager


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + title.center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")


def print_section(title: str):
    """Print a section separator"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def test_ipe_extraction_athena(ipe_id: str = 'IPE_09'):
    """
    Test IPE extraction using AWS Athena.
    
    Args:
        ipe_id: IPE to test (default: IPE_09 - BOB, confirmed working)
    """
    print_header("IPE EXTRACTION TEST - AWS ATHENA VERSION")
    
    # Environment configuration
    aws_region = os.getenv('AWS_REGION', 'eu-west-1')
    cutoff_date = os.getenv('CUTOFF_DATE', '2024-12-31')
    
    print(f"\nEnvironment:")
    print(f"  AWS_REGION: {aws_region}")
    print(f"  CUTOFF_DATE: {cutoff_date}")
    
    print_section(f"IPE EXTRACTION TEST: {ipe_id}")
    
    try:
        # Load IPE configuration from the unified catalog (single source of truth)
        config = get_athena_config(ipe_id)
        print(f"\n✅ IPE Configuration loaded: {config['description']}")
        print(f"   Athena Database: {config['athena_database']}")
        print(f"   Cutoff date: {cutoff_date}")
        
        # Initialize components
        print(f"\n🔍 Initializing components...")
        evidence_manager = DigitalEvidenceManager()
        print(f"✅ Components initialized")
        
        # Create IPE runner (Athena version)
        print(f"\n🔍 Creating IPE runner (Athena)...")
        runner = IPERunnerAthena(
            ipe_config=config,
            cutoff_date=cutoff_date,
            evidence_manager=evidence_manager,
            aws_region=aws_region
        )
        print(f"✅ IPE runner created")
        
        # Execute extraction
        print(f"\n🚀 Executing IPE extraction via Athena...")
        print("-" * 70)
        
        start_time = datetime.now()
        df = runner.run()
        end_time = datetime.now()
        
        execution_time = (end_time - start_time).total_seconds()
        
        # Display results
        print_section("✅ IPE EXTRACTION SUCCESSFUL")
        print(f"Execution time: {execution_time:.2f} seconds")
        print(f"Rows extracted: {len(df)}")
        print(f"Columns: {len(df.columns)}")
        
        # Display validation results
        print(f"\n📊 Validation Results:")
        validation = runner.validation_results
        for test_name, result in validation.items():
            if test_name == 'overall_status':
                continue
            
            status_icon = "✅" if result['status'] == 'PASS' else "⚠️" if result['status'] == 'SKIPPED' else "❌"
            print(f"  {status_icon} {test_name}: {result['status']}")
            
            if result.get('message'):
                print(f"     {result['message']}")
            
            if result.get('issues'):
                for issue in result['issues']:
                    print(f"     - {issue}")
        
        print(f"\n  Overall Status: {validation['overall_status']}")
        
        # Display sample data
        print(f"\n📄 Sample Data (first 5 rows):")
        print(df.head().to_string())
        
        print(f"\n📦 Evidence Package:")
        print(f"   Location: evidence/{ipe_id}/")
        
        print_section("✅ INTEGRATION TEST SUCCESSFUL")
        
    except IPEConnectionError as e:
        print_section("❌ IPE EXTRACTION FAILED (CONNECTION ERROR)")
        print(f"Error: {e}")
        print(f"\nTroubleshooting:")
        print(f"  1. Verify AWS credentials are configured")
        print(f"  2. Check Athena database name in config")
        print(f"  3. Verify table exists in Athena database")
        print(f"  4. Check AWS_REGION environment variable")
        sys.exit(1)
        
    except IPEValidationError as e:
        print_section("⚠️  IPE EXTRACTION COMPLETED WITH VALIDATION ERRORS")
        print(f"Error: {e}")
        print(f"\nValidation Results:")
        if runner.validation_results:
            for test_name, result in runner.validation_results.items():
                if test_name == 'overall_status':
                    continue
                print(f"  {test_name}: {result['status']}")
                if result.get('issues'):
                    for issue in result['issues']:
                        print(f"    - {issue}")
        sys.exit(1)
        
    except Exception as e:
        print_section("❌ UNEXPECTED ERROR")
        print(f"Error: {e}")
        import traceback
        print(f"\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Test with IPE_09 (BOB) first since we confirmed it exists
    # Once team confirms NAV_BI mapping, we can test IPE_07
    
    print("\n⚠️  NOTE: Using IPE_09 (BOB) for testing")
    print("   BOB database confirmed as: process_pg_bob")
    print("   Once NAV_BI mapping confirmed, test with IPE_07")
    
    test_ipe_extraction_athena(ipe_id='IPE_09')
