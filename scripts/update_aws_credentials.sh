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
CREDENTIALS_RAW=$(cat || true)

# Extract values (trim whitespace)
ACCESS_KEY=$(echo "$CREDENTIALS_RAW" | grep -iE "^[[:space:]]*aws_access_key_id[[:space:]]*=" | sed -E 's/.*=\s*//I' | tr -d '\r' | tr -d '\n' | xargs || true)
SECRET_KEY=$(echo "$CREDENTIALS_RAW" | grep -iE "^[[:space:]]*aws_secret_access_key[[:space:]]*=" | sed -E 's/.*=\s*//I' | tr -d '\r' | tr -d '\n' | xargs || true)
SESSION_TOKEN=$(echo "$CREDENTIALS_RAW" | grep -iE "^[[:space:]]*aws_session_token[[:space:]]*=" | sed -E 's/.*=\s*//I' | tr -d '\r' | tr -d '\n' | xargs || true)

# If parsing failed, offer manual entry fallback
if [ -z "${ACCESS_KEY:-}" ] || [ -z "${SECRET_KEY:-}" ] || [ -z "${SESSION_TOKEN:-}" ]; then
  echo "\nCouldn't parse credentials from pasted block. Switching to manual entry..."
  echo "Tip: Paste only the 3 lines without the [profile] header."
  echo ""
  read -r -p "AWS Access Key ID: " ACCESS_KEY
  if [ -z "$ACCESS_KEY" ]; then echo "Access Key ID cannot be empty" >&2; exit 1; fi
  read -rs -p "AWS Secret Access Key: " SECRET_KEY; echo
  if [ -z "$SECRET_KEY" ]; then echo "Secret Access Key cannot be empty" >&2; exit 1; fi
  echo "Paste AWS Session Token (end with Enter):"
  IFS= read -r SESSION_TOKEN
  if [ -z "$SESSION_TOKEN" ]; then echo "Session Token cannot be empty" >&2; exit 1; fi
fi

echo "Applying credentials to AWS CLI profile: $PROFILE"

# Ensure ~/.aws exists
AWS_DIR="$HOME/.aws"
mkdir -p "$AWS_DIR"
CRED_FILE="$AWS_DIR/credentials"

# If credentials file exists but is malformed (no [section] headers), reset it safely
NEED_RESET=0
if [ -f "$CRED_FILE" ]; then
  if ! grep -qE '^\s*\[.+\]\s*$' "$CRED_FILE"; then
    NEED_RESET=1
  fi
fi

if [ "$NEED_RESET" -eq 1 ]; then
  TS=$(date +%Y%m%d-%H%M%S)
  cp "$CRED_FILE" "$CRED_FILE.bak-$TS" || true
  echo "⚠️  Detected malformed credentials file. Backed up to $CRED_FILE.bak-$TS"
  # Write a minimal valid INI with our profile
  cat > "$CRED_FILE" <<EOF
[$PROFILE]
aws_access_key_id=$ACCESS_KEY
aws_secret_access_key=$SECRET_KEY
aws_session_token=$SESSION_TOKEN
EOF
  chmod 600 "$CRED_FILE"
else
  # Try using aws configure set. If it fails (e.g., due to parse errors), fall back to rewriting the file
  set +e
  aws configure set aws_access_key_id "$ACCESS_KEY" --profile "$PROFILE"
  CFG_RC1=$?
  aws configure set aws_secret_access_key "$SECRET_KEY" --profile "$PROFILE"
  CFG_RC2=$?
  aws configure set aws_session_token "$SESSION_TOKEN" --profile "$PROFILE"
  CFG_RC3=$?
  set -e

  if [ $CFG_RC1 -ne 0 ] || [ $CFG_RC2 -ne 0 ] || [ $CFG_RC3 -ne 0 ]; then
    echo "⚠️  aws configure failed to update credentials. Falling back to writing a clean credentials file."
    TS=$(date +%Y%m%d-%H%M%S)
    if [ -f "$CRED_FILE" ]; then
      cp "$CRED_FILE" "$CRED_FILE.bak-$TS" || true
      echo "   Backup: $CRED_FILE.bak-$TS"
    fi
    cat > "$CRED_FILE" <<EOF
[$PROFILE]
aws_access_key_id=$ACCESS_KEY
aws_secret_access_key=$SECRET_KEY
aws_session_token=$SESSION_TOKEN
EOF
    chmod 600 "$CRED_FILE"
  fi
fi

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
