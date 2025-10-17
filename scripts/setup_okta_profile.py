#!/usr/bin/env python3
"""
Okta AWS Profile Setup Script

This script helps configure AWS SSO profiles for Okta authentication.
Run this script to set up your AWS CLI profile for Okta-based authentication.

Usage:
    python3 scripts/setup_okta_profile.py
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.okta_aws_auth import setup_okta_profile


def main():
    """Interactive setup for Okta AWS profile."""
    print("=" * 70)
    print("AWS OKTA SSO PROFILE SETUP")
    print("=" * 70)
    print()
    print("This script will help you configure AWS CLI for Okta SSO authentication.")
    print()
    
    # Gather information
    print("Please provide the following information:")
    print("-" * 70)
    
    profile_name = input("Profile name (e.g., jumia-sox-prod): ").strip()
    if not profile_name:
        print("❌ Profile name is required")
        return
    
    sso_start_url = input("Okta SSO start URL: ").strip()
    if not sso_start_url:
        print("❌ SSO start URL is required")
        return
    
    sso_region = input("SSO region (default: eu-west-1): ").strip() or "eu-west-1"
    
    account_id = input("AWS account ID (12 digits): ").strip()
    if not account_id or len(account_id) != 12 or not account_id.isdigit():
        print("❌ Invalid AWS account ID (must be 12 digits)")
        return
    
    role_name = input("IAM role name (e.g., SOXAutomationRole): ").strip()
    if not role_name:
        print("❌ Role name is required")
        return
    
    print()
    print("-" * 70)
    print("Configuration Summary:")
    print("-" * 70)
    print(f"Profile Name:     {profile_name}")
    print(f"SSO Start URL:    {sso_start_url}")
    print(f"SSO Region:       {sso_region}")
    print(f"Account ID:       {account_id}")
    print(f"Role Name:        {role_name}")
    print("-" * 70)
    print()
    
    confirm = input("Create this profile? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Setup cancelled")
        return
    
    try:
        # Create the profile
        setup_okta_profile(
            profile_name=profile_name,
            sso_start_url=sso_start_url,
            sso_region=sso_region,
            account_id=account_id,
            role_name=role_name
        )
        
        print()
        print("=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print()
        print("1. Login to AWS SSO:")
        print(f"   aws sso login --profile {profile_name}")
        print()
        print("2. Verify your credentials:")
        print(f"   aws sts get-caller-identity --profile {profile_name}")
        print()
        print("3. Set environment variables:")
        print(f"   export AWS_PROFILE={profile_name}")
        print("   export USE_OKTA_AUTH=true")
        print()
        print("4. Test database connection:")
        print("   python3 tests/test_database_connection.py")
        print()
        print("For more information, see: docs/setup/OKTA_AWS_SETUP.md")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error creating profile: {e}")
        return


if __name__ == "__main__":
    main()
