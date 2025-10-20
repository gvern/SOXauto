#!/usr/bin/env bash
# scripts/update_aws_credentials.sh
#
# Simple, safe helper to paste temporary AWS session credentials and
# update the local AWS CLI credentials file for the profile:
#   007809111365_Data-Prod-DataAnalyst-NonFinance
#
# Usage:
# 1. Obtain temporary credentials from the AWS SSO portal (Command line / programmatic access -> Option 2)
# 2. Run this script and paste the three lines (aws_access_key_id / aws_secret_access_key / aws_session_token)
# 3. The script will parse and apply them using 'aws configure set' (no credentials are committed)

set -euo pipefail

PROFILE="007809111365_Data-Prod-DataAnalyst-NonFinance"

echo "=============================================="
echo " AWS Temporary Credentials Updater"
echo " Profile: $PROFILE"
echo "=============================================="

echo "Paste the credentials block (3 lines) and then press Ctrl+D when finished:" 
cat <<'__EOF_PROMPT__'
Example input:
aws_access_key_id=ASIA...
aws_secret_access_key=... 
aws_session_token=...
__EOF_PROMPT__

# Read whole stdin until EOF
CREDENTIALS_RAW=$(cat)

# Extract values (trim whitespace)
ACCESS_KEY=$(echo "$CREDENTIALS_RAW" | grep -i "aws_access_key_id" | sed -E 's/.*=\s*//I' | tr -d '\r' | tr -d '\n' | xargs)
SECRET_KEY=$(echo "$CREDENTIALS_RAW" | grep -i "aws_secret_access_key" | sed -E 's/.*=\s*//I' | tr -d '\r' | tr -d '\n' | xargs)
SESSION_TOKEN=$(echo "$CREDENTIALS_RAW" | grep -i "aws_session_token" | sed -E 's/.*=\s*//I' | tr -d '\r' | tr -d '\n' | xargs)

if [ -z "$ACCESS_KEY" ] || [ -z "$SECRET_KEY" ] || [ -z "$SESSION_TOKEN" ]; then
  echo "Error: Could not parse all three credential values. Please paste the block exactly as provided by AWS." >&2
  exit 1
fi

echo "Applying credentials to AWS CLI profile: $PROFILE"

# Use aws cli to set values so we don't directly edit files. This keeps file permissions and format correct.
aws configure set aws_access_key_id "$ACCESS_KEY" --profile "$PROFILE"
aws configure set aws_secret_access_key "$SECRET_KEY" --profile "$PROFILE"
aws configure set aws_session_token "$SESSION_TOKEN" --profile "$PROFILE"

echo "Credentials applied. Verifying with STS..."

if aws sts get-caller-identity --profile "$PROFILE" >/dev/null 2>&1; then
  echo "✅ Verified identity for profile $PROFILE"
  echo "Note: These are temporary credentials — they will expire. Re-run this script to refresh."
  echo "For security, do not commit credentials to git. This script writes only to your local ~/.aws/credentials file."
else
  echo "⚠️  Verification failed. The profile was updated but STS call did not succeed. Check your pasted credentials and try again." >&2
  exit 1
fi

echo "Done."
#!/bin/bash
#
# AWS Credentials Quick Update
#
# This script provides a simple, secure way to update your temporary AWS credentials daily.
# It reads credentials pasted into the terminal and writes them to the AWS credentials file.
#
# Usage:
# 1. Copy the 3 credential lines from the AWS portal.
# 2. Run this script: ./scripts/update_aws_credentials.sh
# 3. Paste the credentials into the terminal.
# 4. Press Ctrl+D to save and finish.
#

set -e # Exit immediately if a command exits with a non-zero status.

PROFILE_NAME="007809111365_Data-Prod-DataAnalyst-NonFinance"
CREDS_FILE="$HOME/.aws/credentials"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║              AWS Credentials Quick Update                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Paste your 3 credential lines from the AWS portal below."
echo "Press Ctrl+D when you are done."
echo "----------------------------------------------------------------"

# Read all input from stdin until EOF (Ctrl+D)
CREDENTIALS=$(cat)

# Basic validation to see if we got any input
if [ -z "$CREDENTIALS" ]; then
    echo "❌ No input received. Aborting."
    exit 1
fi

# Create .aws directory if it doesn't exist
mkdir -p "$(dirname "$CREDS_FILE")"

# Write credentials to the file, overwriting previous content.
# This is safer as it removes any other profiles and ensures a clean state.
cat > "$CREDS_FILE" << EOF
[$PROFILE_NAME]
$CREDENTIALS
EOF

# Make the credentials file readable only by the current user
chmod 600 "$CREDS_FILE"

echo ""
echo "----------------------------------------------------------------"
echo "✅ Credentials updated successfully for profile: [$PROFILE_NAME]"
echo ""
echo "To verify, run:"
echo "   aws sts get-caller-identity --profile $PROFILE_NAME"
echo ""
echo "To use these credentials in your project, run:"
echo "   export AWS_PROFILE=$PROFILE_NAME"
echo "╚════════════════════════════════════════════════════════════╝"
