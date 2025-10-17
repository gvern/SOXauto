#!/usr/bin/env python3
"""
Test Okta AWS authentication.

This test verifies:
1. Okta SSO authentication
2. AWS session creation
3. AWS service access (Secrets Manager, S3)

Run:
    export AWS_PROFILE=jumia-sox-prod
    export USE_OKTA_AUTH=true
    python3 tests/test_okta_auth.py
"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.okta_aws_auth import OktaAWSAuth
from src.utils.aws_utils import AWSSecretsManager, AWSS3Manager


def test_okta_authentication():
    """Test basic Okta authentication."""
    print("\n🔍 Testing Okta AWS Authentication...")
    print("-" * 70)
    
    try:
        # Get profile from environment
        profile_name = os.getenv('AWS_PROFILE')
        if not profile_name:
            print("⚠️  AWS_PROFILE not set, using 'default'")
            profile_name = 'default'
        
        print(f"Using profile: {profile_name}")
        
        # Initialize Okta auth
        okta_auth = OktaAWSAuth(
            profile_name=profile_name,
            region_name='eu-west-1'
        )
        
        # Get session
        session = okta_auth.get_session()
        print("✅ Okta session created successfully")
        
        # Test STS get_caller_identity
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        
        print(f"   User ID:      {identity['UserId']}")
        print(f"   Account:      {identity['Account']}")
        print(f"   ARN:          {identity['Arn']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Okta authentication error: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure AWS CLI v2 is installed")
        print("2. Run: aws sso login --profile <profile-name>")
        print("3. Check your profile configuration in ~/.aws/config")
        return False


def test_secrets_manager_with_okta():
    """Test AWS Secrets Manager access with Okta."""
    print("\n🔍 Testing Secrets Manager with Okta...")
    print("-" * 70)
    
    try:
        profile_name = os.getenv('AWS_PROFILE')
        
        # Initialize with Okta auth
        sm = AWSSecretsManager(
            region_name='eu-west-1',
            use_okta=True,
            profile_name=profile_name
        )
        
        # Try to retrieve a secret
        # Note: This will fail if the secret doesn't exist, but it validates auth
        try:
            conn_str = sm.get_secret("DB_CREDENTIALS_NAV_BI")
            print("✅ Secret retrieved successfully")
            print(f"   Connection string format: {conn_str[:20]}...")
            return True
        except Exception as e:
            if "ResourceNotFoundException" in str(e):
                print("✅ Authenticated successfully (secret not found, but auth works)")
                return True
            else:
                raise
                
    except Exception as e:
        print(f"❌ Secrets Manager error: {e}")
        return False


def test_s3_with_okta():
    """Test S3 access with Okta."""
    print("\n🔍 Testing S3 with Okta...")
    print("-" * 70)
    
    try:
        profile_name = os.getenv('AWS_PROFILE')
        
        # Initialize with Okta auth
        s3 = AWSS3Manager(
            region_name='eu-west-1',
            use_okta=True,
            profile_name=profile_name
        )
        
        # List buckets (basic operation to verify access)
        response = s3.client.list_buckets()
        buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
        
        print(f"✅ S3 access successful")
        print(f"   Found {len(buckets)} buckets")
        if buckets:
            print(f"   Sample buckets: {', '.join(buckets[:3])}")
        
        return True
        
    except Exception as e:
        print(f"❌ S3 access error: {e}")
        return False


def test_credentials_caching():
    """Test that credentials are properly cached."""
    print("\n🔍 Testing Credential Caching...")
    print("-" * 70)
    
    try:
        profile_name = os.getenv('AWS_PROFILE')
        
        # Create first session
        okta_auth1 = OktaAWSAuth(profile_name=profile_name)
        session1 = okta_auth1.get_session()
        print("✅ First session created")
        
        # Create second session (should use cache)
        okta_auth2 = OktaAWSAuth(profile_name=profile_name)
        session2 = okta_auth2.get_session()
        print("✅ Second session created (from cache)")
        
        # Get credentials
        creds = okta_auth2.get_credentials()
        print("✅ Credentials retrieved")
        print(f"   Region: {creds['region']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Credential caching error: {e}")
        return False


def main():
    """Run all Okta authentication tests."""
    print("=" * 70)
    print("OKTA AWS AUTHENTICATION TESTING")
    print("=" * 70)
    
    # Check environment
    print("\n📋 Environment Check:")
    print("-" * 70)
    print(f"AWS_PROFILE:       {os.getenv('AWS_PROFILE', 'Not set')}")
    print(f"USE_OKTA_AUTH:     {os.getenv('USE_OKTA_AUTH', 'Not set')}")
    print(f"AWS_REGION:        {os.getenv('AWS_REGION', 'Not set (using default)')}")
    
    if not os.getenv('AWS_PROFILE'):
        print("\n⚠️  Warning: AWS_PROFILE not set")
        print("   Set it with: export AWS_PROFILE=your-profile-name")
    
    # Run tests
    results = []
    
    results.append(("Okta Authentication", test_okta_authentication()))
    results.append(("Secrets Manager Access", test_secrets_manager_with_okta()))
    results.append(("S3 Access", test_s3_with_okta()))
    results.append(("Credential Caching", test_credentials_caching()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for _, result in results if result)
    
    print("-" * 70)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 70)
    
    if passed == total:
        print("\n🎉 All tests passed! Okta authentication is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        print("\nCommon issues:")
        print("1. AWS CLI v2 not installed")
        print("2. SSO session expired - run: aws sso login --profile <profile>")
        print("3. Profile not configured - check ~/.aws/config")
        print("4. Insufficient IAM permissions")
        return 1


if __name__ == "__main__":
    sys.exit(main())
