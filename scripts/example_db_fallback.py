#!/usr/bin/env python3
"""
Quick Example: Using DB_CONNECTION_STRING fallback for IPE extraction

This script demonstrates how to run an IPE extraction using the
DB_CONNECTION_STRING environment variable when Secrets Manager is not accessible.
"""

import os
import sys

# Example connection string (REPLACE WITH YOUR ACTUAL VALUES)
DB_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=your-server.database.windows.net;"
    "DATABASE=NAV_BI;"
    "UID=your_username;"
    "PWD=your_password;"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)

# Set environment variables
os.environ['AWS_PROFILE'] = '007809111365_Data-Prod-DataAnalyst-NonFinance'
os.environ['AWS_REGION'] = 'eu-west-1'
os.environ['CUTOFF_DATE'] = '2024-12-31'
os.environ['DB_CONNECTION_STRING'] = DB_CONNECTION_STRING

# Import after setting env vars
from src.core.ipe_runner import IPERunner
from src.utils.aws_utils import AWSSecretsManager
from src.core.config import IPEConfig

def main():
    """Run IPE extraction with DB_CONNECTION_STRING fallback"""
    
    print("=" * 70)
    print("IPE EXTRACTION WITH DB_CONNECTION_STRING FALLBACK")
    print("=" * 70)
    print()
    
    # Load IPE configuration
    ipe_id = "IPE_07"
    config = IPEConfig.load_ipe_config(ipe_id)
    print(f"✅ Loaded config for {ipe_id}: {config['ipe_name']}")
    
    # Initialize components
    secret_manager = AWSSecretsManager()
    
    # Create IPE runner
    runner = IPERunner(
        ipe_id=ipe_id,
        config=config,
        secret_manager=secret_manager
    )
    print(f"✅ IPE runner initialized")
    print()
    
    # Run extraction
    print("🚀 Starting extraction...")
    try:
        df = runner.run()
        print(f"✅ Extraction successful: {len(df)} rows retrieved")
        print()
        print("Sample data:")
        print(df.head())
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
