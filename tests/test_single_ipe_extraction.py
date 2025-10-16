#!/usr/bin/env python3
"""
Test complete IPE extraction flow with a single IPE.

This test verifies:
1. IPE configuration loading
2. Component initialization
3. Full IPE extraction with validation
4. Evidence package generation

Run:
    python3 tests/test_single_ipe_extraction.py
    
    # Or test specific IPE:
    TEST_IPE_ID="CR_03_04" python3 tests/test_single_ipe_extraction.py
"""
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.ipe_runner import IPERunner
from src.core.config import IPE_CONFIGS, AWS_REGION
from src.utils.aws_utils import AWSSecretsManager
from src.core.evidence_manager import DigitalEvidenceManager


def test_ipe_extraction(ipe_id="IPE_07", cutoff_date=None):
    """
    Test complete IPE extraction with validation and evidence generation.
    
    Args:
        ipe_id: IPE to test (default: IPE_07)
        cutoff_date: Cutoff date for extraction (default: from env or 2024-01-01)
    
    Returns:
        bool: True if test passes, False otherwise
    """
    print("=" * 70)
    print(f"SINGLE IPE EXTRACTION TEST: {ipe_id}")
    print("=" * 70)
    
    # Get IPE config
    try:
        ipe_config = next(c for c in IPE_CONFIGS if c['id'] == ipe_id)
        print(f"\n✅ IPE Configuration loaded: {ipe_config['description']}")
    except StopIteration:
        print(f"\n❌ IPE '{ipe_id}' not found in configuration")
        print(f"   Available IPEs: {', '.join([c['id'] for c in IPE_CONFIGS])}")
        return False
    
    # Setup
    cutoff_date = cutoff_date or os.getenv("CUTOFF_DATE", "2024-01-01")
    print(f"   Cutoff date: {cutoff_date}")
    
    # Initialize components
    print("\n🔍 Initializing components...")
    try:
        secret_manager = AWSSecretsManager(AWS_REGION)
        evidence_manager = DigitalEvidenceManager()
        print("✅ Components initialized")
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Create IPE runner
    print("\n🔍 Creating IPE runner...")
    try:
        runner = IPERunner(
            ipe_config=ipe_config,
            secret_manager=secret_manager,
            cutoff_date=cutoff_date,
            evidence_manager=evidence_manager
        )
        print("✅ IPE runner created")
    except Exception as e:
        print(f"❌ Runner creation error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Execute IPE
    print("\n🚀 Executing IPE extraction...")
    print("-" * 70)
    start_time = datetime.now()
    
    try:
        df = runner.run()
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "=" * 70)
        print("✅ IPE EXTRACTION SUCCESSFUL")
        print("=" * 70)
        print(f"Execution time: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
        print(f"Records extracted: {len(df):,}")
        print(f"Columns: {len(df.columns)}")
        print(f"Memory usage: ~{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
        
        # Show sample columns
        print(f"\nSample columns: {', '.join(df.columns[:5].tolist())}...")
        
        # Validation summary
        print("\n📊 Validation Results:")
        validation = runner.validation_results
        
        if 'completeness' in validation:
            comp = validation['completeness']
            print(f"   Completeness: {comp['status']}")
            print(f"     Expected: {comp.get('expected_count', 'N/A'):,}")
            print(f"     Actual: {comp.get('actual_count', 'N/A'):,}")
        
        if 'accuracy_positive' in validation:
            acc_pos = validation['accuracy_positive']
            print(f"   Accuracy Positive: {acc_pos['status']}")
            print(f"     Witness count: {acc_pos.get('witness_count', 'N/A')}")
        
        if 'accuracy_negative' in validation:
            acc_neg = validation['accuracy_negative']
            print(f"   Accuracy Negative: {acc_neg['status']}")
            print(f"     Excluded count: {acc_neg.get('excluded_count', 'N/A')}")
        
        # Evidence package
        if 'data_integrity_hash' in validation:
            hash_value = validation['data_integrity_hash']
            print(f"\n🔐 Data Integrity Hash: {hash_value[:16]}...")
        
        # Overall status
        overall_status = validation.get('overall_status', 'UNKNOWN')
        if overall_status == 'SUCCESS':
            print("\n✅ All validations passed")
        else:
            print(f"\n⚠️  Overall status: {overall_status}")
        
        # Performance assessment
        if elapsed < 180:  # 3 minutes
            print(f"\n🚀 Performance: EXCELLENT (under 3 minutes)")
        elif elapsed < 300:  # 5 minutes
            print(f"\n✅ Performance: GOOD (under 5 minutes)")
        else:
            print(f"\n⚠️  Performance: Consider optimization (over 5 minutes)")
        
        return True
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 70)
        print("❌ IPE EXTRACTION FAILED")
        print("=" * 70)
        print(f"Execution time: {elapsed:.2f} seconds")
        print(f"Error: {e}")
        
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        
        # Print validation results if available
        if hasattr(runner, 'validation_results') and runner.validation_results:
            print("\n⚠️  Partial validation results:")
            for key, value in runner.validation_results.items():
                print(f"   {key}: {value}")
        
        return False


def main():
    """Run single IPE extraction test."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  IPE EXTRACTION INTEGRATION TEST".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    # Check environment
    if not os.getenv("AWS_REGION"):
        print("❌ ERROR: AWS_REGION environment variable not set")
        print("\n💡 Set it with:")
        print("   export AWS_REGION='eu-west-1'")
        return False
    
    print(f"Environment:")
    print(f"  AWS_REGION: {os.getenv('AWS_REGION')}")
    print(f"  CUTOFF_DATE: {os.getenv('CUTOFF_DATE', '2024-01-01 (default)')}")
    print()
    
    # Test IPE_07 by default, or use TEST_IPE_ID env var
    ipe_to_test = os.getenv("TEST_IPE_ID", "IPE_07")
    
    success = test_ipe_extraction(ipe_id=ipe_to_test)
    
    if success:
        print("\n" + "=" * 70)
        print("🎉 INTEGRATION TEST COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Review evidence package in /tmp/evidence/")
        print("  2. Test additional IPEs if needed")
        print("  3. Proceed to Docker build testing")
        print("  4. Review INTEGRATION_TESTING_PREP.md for next phase")
    else:
        print("\n" + "=" * 70)
        print("❌ INTEGRATION TEST FAILED")
        print("=" * 70)
        print("\nTroubleshooting:")
        print("  1. Check database connectivity")
        print("  2. Verify test data exists for cutoff date")
        print("  3. Review error logs above")
        print("  4. Consult INTEGRATION_TESTING_PREP.md")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
