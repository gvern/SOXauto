#!/usr/bin/env python3
"""
Headless Reconciliation Test Script

Command-line script for testing the run_reconciliation function.
This script allows running the reconciliation engine without a GUI,
outputting results as JSON for easy integration with external tools.

Usage:
    python scripts/run_headless_test.py --cutoff-date 2025-09-30 --company EC_NG
    python scripts/run_headless_test.py --config config.json
    python scripts/run_headless_test.py --help

Output:
    JSON object containing all reconciliation results, suitable for API consumption.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict

# Ensure project modules are importable
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.core.reconciliation.run_reconciliation import run_reconciliation


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run SOX reconciliation in headless mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run with command line parameters
    python scripts/run_headless_test.py --cutoff-date 2025-09-30 --company EC_NG

    # Run with JSON config file
    python scripts/run_headless_test.py --config my_config.json

    # Run with custom IPEs and output to file
    python scripts/run_headless_test.py --cutoff-date 2025-09-30 --company EC_NG \\
        --ipes IPE_07,IPE_08,CR_03 --output results.json

    # Run without bridge analysis (faster)
    python scripts/run_headless_test.py --cutoff-date 2025-09-30 --company EC_NG --no-bridges
        """,
    )
    
    # Required parameters (can be provided via config file)
    parser.add_argument(
        "--cutoff-date",
        dest="cutoff_date",
        help="Cutoff date in YYYY-MM-DD format (e.g., 2025-09-30)",
    )
    
    parser.add_argument(
        "--company",
        dest="company",
        help="Company code (e.g., EC_NG, EC_KE, JD_GH)",
    )
    
    # Optional parameters
    parser.add_argument(
        "--config",
        dest="config_file",
        help="Path to JSON config file containing all parameters",
    )
    
    parser.add_argument(
        "--ipes",
        dest="ipes",
        help="Comma-separated list of IPE IDs to load (e.g., IPE_07,IPE_08,CR_03)",
    )
    
    parser.add_argument(
        "--output",
        dest="output_file",
        help="Path to output JSON file (default: stdout)",
    )
    
    parser.add_argument(
        "--no-bridges",
        dest="no_bridges",
        action="store_true",
        help="Skip bridge analysis (faster execution)",
    )
    
    parser.add_argument(
        "--no-quality",
        dest="no_quality",
        action="store_true",
        help="Skip quality checks",
    )
    
    parser.add_argument(
        "--summary-only",
        dest="summary_only",
        action="store_true",
        help="Output summary only (exclude full dataframe records)",
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress all non-JSON output",
    )
    
    return parser.parse_args()


def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load parameters from a JSON config file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}", file=sys.stderr)
        sys.exit(1)


def build_params(args: argparse.Namespace) -> Dict[str, Any]:
    """Build reconciliation parameters from command line arguments."""
    params = {}
    
    # Load from config file if provided
    if args.config_file:
        params = load_config_file(args.config_file)
    
    # Override with command line arguments
    if args.cutoff_date:
        params['cutoff_date'] = args.cutoff_date
    
    if args.company:
        # Format company code for SQL
        params['id_companies_active'] = f"('{args.company}')"
        # Store raw company code for multi-entity fixture loading
        params['company'] = args.company
    
    if args.ipes:
        params['required_ipes'] = [ipe.strip() for ipe in args.ipes.split(',')]
    
    if args.no_bridges:
        params['run_bridges'] = False
    
    if args.no_quality:
        params['validate_quality'] = False
    
    return params


def filter_summary_output(result: Dict[str, Any]) -> Dict[str, Any]:
    """Filter result to include only summary information."""
    summary = {
        'status': result.get('status'),
        'timestamp': result.get('timestamp'),
        'params': result.get('params'),
        'dataframe_summaries': result.get('dataframe_summaries'),
        'data_sources': result.get('data_sources'),
        'quality_reports': result.get('quality_reports'),
        'categorization': result.get('categorization'),
        'bridges': result.get('bridges'),
        'reconciliation': result.get('reconciliation'),
        'errors': result.get('errors'),
        'warnings': result.get('warnings'),
    }
    return summary


def main():
    """Main entry point for the headless reconciliation test."""
    args = parse_args()
    
    # Configure logging
    if args.verbose and not args.quiet:
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )
    elif not args.quiet:
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
        )
    
    # Build parameters
    params = build_params(args)
    
    # Validate required parameters
    if 'cutoff_date' not in params:
        print("Error: --cutoff-date is required (or provide via --config)", file=sys.stderr)
        sys.exit(1)
    
    if 'id_companies_active' not in params:
        print("Error: --company is required (or provide via --config)", file=sys.stderr)
        sys.exit(1)
    
    # Log start
    if not args.quiet:
        print(f"🚀 Starting headless reconciliation...", file=sys.stderr)
        print(f"   Cutoff Date: {params['cutoff_date']}", file=sys.stderr)
        print(f"   Company: {params['id_companies_active']}", file=sys.stderr)
        if 'required_ipes' in params:
            print(f"   IPEs: {', '.join(params['required_ipes'])}", file=sys.stderr)
    
    # Run reconciliation
    start_time = datetime.now()
    result = run_reconciliation(params)
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # Add execution time to result
    result['execution_time_seconds'] = elapsed
    
    # Filter to summary if requested
    if args.summary_only:
        result = filter_summary_output(result)
    
    # Output result
    output_json = json.dumps(result, indent=2, default=str)
    
    if args.output_file:
        try:
            with open(args.output_file, 'w') as f:
                f.write(output_json)
            if not args.quiet:
                print(f"✅ Results written to: {args.output_file}", file=sys.stderr)
        except IOError as e:
            print(f"Error: Failed to write output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output_json)
    
    # Log completion
    if not args.quiet:
        print(f"", file=sys.stderr)
        print(f"📊 Reconciliation Complete", file=sys.stderr)
        print(f"   Status: {result.get('status', 'UNKNOWN')}", file=sys.stderr)
        print(f"   Execution Time: {elapsed:.2f}s", file=sys.stderr)
        
        if result.get('errors'):
            print(f"   ❌ Errors: {len(result['errors'])}", file=sys.stderr)
            for err in result['errors'][:3]:
                print(f"      - {err}", file=sys.stderr)
        
        if result.get('warnings'):
            print(f"   ⚠️  Warnings: {len(result['warnings'])}", file=sys.stderr)
        
        recon = result.get('reconciliation', {})
        if recon.get('status'):
            print(f"   Reconciliation Status: {recon.get('status')}", file=sys.stderr)
            if recon.get('variance') is not None:
                print(f"   Variance: {recon.get('variance'):,.2f}", file=sys.stderr)
    
    # Exit with appropriate code
    if result.get('status') == 'ERROR':
        sys.exit(1)
    elif result.get('status') == 'WARNING':
        sys.exit(0)  # Warnings are still success
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
