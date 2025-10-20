#!/bin/bash
# Quick start script for Okta AWS authentication

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         AWS Okta SSO Authentication - Quick Start              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check AWS CLI installation
echo "🔍 Checking prerequisites..."
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found"
    echo "   Install with: brew install awscli"
    exit 1
fi

# Check AWS CLI version
AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1 | cut -d'/' -f2)
AWS_MAJOR=$(echo $AWS_VERSION | cut -d'.' -f1)

if [ "$AWS_MAJOR" -lt 2 ]; then
    echo "❌ AWS CLI v2 required (found v$AWS_VERSION)"
    echo "   Upgrade with: brew upgrade awscli"
    exit 1
fi

echo "✅ AWS CLI v$AWS_VERSION found"
echo ""

# Check if profile exists
read -p "Enter your AWS SSO profile name (e.g., jumia-sox-prod): " PROFILE_NAME

if grep -q "\[profile $PROFILE_NAME\]" ~/.aws/config 2>/dev/null; then
    echo "✅ Profile '$PROFILE_NAME' found in ~/.aws/config"
else
    echo "⚠️  Profile '$PROFILE_NAME' not found"
    echo ""
    read -p "Would you like to create it now? (y/n): " CREATE_PROFILE
    
    if [ "$CREATE_PROFILE" = "y" ]; then
        echo "Running setup script..."
        python3 scripts/setup_okta_profile.py
    else
        echo "Please run: python3 scripts/setup_okta_profile.py"
        exit 1
    fi
fi

echo ""
echo "🔐 Logging in to AWS SSO..."
aws sso login --profile "$PROFILE_NAME"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully logged in!"
    echo ""
    echo "📋 Your AWS identity:"
    aws sts get-caller-identity --profile "$PROFILE_NAME"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎉 Setup complete! Next steps:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1. Set environment variables:"
    echo "   export AWS_PROFILE=$PROFILE_NAME"
    echo "   export USE_OKTA_AUTH=true"
    echo ""
    echo "2. Or add to .env file:"
    echo "   echo 'AWS_PROFILE=$PROFILE_NAME' >> .env"
    echo "   echo 'USE_OKTA_AUTH=true' >> .env"
    echo ""
    echo "3. Test the connection:"
    echo "   python3 tests/test_okta_auth.py"
    echo ""
    echo "4. Run database tests:"
    echo "   python3 tests/test_database_connection.py"
    echo ""
    echo "📚 Documentation:"
    echo "   - Full guide: docs/setup/OKTA_AWS_SETUP.md"
    echo "   - Quick ref:  docs/setup/OKTA_QUICK_REFERENCE.md"
    echo "   - Flow diagram: docs/setup/OKTA_AUTH_FLOW.md"
    echo ""
else
    echo ""
    echo "❌ Login failed. Please check:"
    echo "   1. Your Okta credentials"
    echo "   2. Profile configuration in ~/.aws/config"
    echo "   3. Internet connection"
    exit 1
fi
