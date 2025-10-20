#!/usr/bin/env bash
# Wrapper to run the archived Okta quickstart script from the expected path

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec bash "$SCRIPT_DIR/archive/okta_quickstart.sh"
