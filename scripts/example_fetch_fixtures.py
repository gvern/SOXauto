#!/usr/bin/env python3
"""
Example script demonstrating the entity-specific fixture fetching.

This script shows how to use fetch_live_fixtures.py with different entities.
"""

import subprocess
import sys
from pathlib import Path


def fetch_fixtures_for_entity(entity: str) -> None:
    """
    Fetch live fixtures for a specific entity.
    
    Args:
        entity: Entity code (e.g., 'EC_NG', 'JD_GH')
    """
    print(f"\n{'='*60}")
    print(f"Fetching fixtures for entity: {entity}")
    print(f"{'='*60}\n")
    
    # Construct the command
    script_path = Path(__file__).parent / "fetch_live_fixtures.py"
    cmd = [sys.executable, str(script_path), "--entity", entity]
    
    # Run the command
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Warnings/Errors:\n{result.stderr}")
        
        # Verify the output directory was created
        output_dir = Path(__file__).parent.parent / "tests" / "fixtures" / entity
        if output_dir.exists():
            print(f"\n✅ Output directory created: {output_dir}")
            
            # List files in the directory
            files = list(output_dir.glob("*.csv"))
            if files:
                print(f"📁 Files created ({len(files)}):")
                for f in sorted(files):
                    print(f"   - {f.name}")
            else:
                print("⚠️  No CSV files found in output directory")
        else:
            print(f"\n❌ Output directory not found: {output_dir}")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running fetch_live_fixtures.py: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")


def main() -> None:
    """Main function to demonstrate fetching fixtures for multiple entities."""
    print("""
╔════════════════════════════════════════════════════════════╗
║  Entity-Specific Fixture Fetching Example                 ║
║  Demonstrates how to fetch fixtures for multiple entities ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    # Example 1: Fetch for Nigeria (EC_NG)
    print("\n📌 Example 1: Fetching fixtures for Nigeria (EC_NG)")
    print("   Command: python scripts/fetch_live_fixtures.py --entity EC_NG")
    # Uncomment to actually run:
    # fetch_fixtures_for_entity("EC_NG")
    
    # Example 2: Fetch for Ghana (JD_GH)
    print("\n📌 Example 2: Fetching fixtures for Ghana (JD_GH)")
    print("   Command: python scripts/fetch_live_fixtures.py --entity JD_GH")
    # Uncomment to actually run:
    # fetch_fixtures_for_entity("JD_GH")
    
    print("\n" + "="*60)
    print("ℹ️  To actually fetch fixtures, uncomment the function calls")
    print("   in this script or run the commands shown above directly.")
    print("="*60 + "\n")
    
    # Show expected directory structure
    print("📂 Expected Directory Structure:")
    print("""
    tests/fixtures/
    ├── EC_NG/
    │   ├── fixture_CR_03.csv
    │   ├── fixture_CR_04.csv
    │   ├── fixture_CR_05.csv
    │   ├── fixture_IPE_07.csv
    │   ├── fixture_IPE_08.csv
    │   ├── fixture_DOC_VOUCHER_USAGE.csv
    │   ├── fixture_IPE_REC_ERRORS.csv
    │   └── JDASH.csv  # Manually placed (not overwritten)
    ├── JD_GH/
    │   ├── fixture_CR_03.csv
    │   ├── ...
    │   └── JDASH.csv  # Manually placed (not overwritten)
    └── ...
    """)


if __name__ == "__main__":
    main()
