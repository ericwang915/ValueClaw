#!/usr/bin/env bash
# Pre-activation check for the Google Workspace (gog) skill.
# Exit 0 = ready, exit 1 = not ready (output tells the user what to fix).

set -euo pipefail

# ?? 1. Is gog installed? ??????????????????????????????????????????????????????
if ! command -v gog &>/dev/null; then
    cat <<'EOF'
ERROR: The 'gog' CLI is not installed.

To install on macOS:
  brew install steipete/tap/gogcli

To install on Linux:
  curl -fsSL https://api.github.com/repos/steipete/gogcli/releases/latest \
    | grep browser_download_url | grep linux_amd64
  # Download the tarball, extract, then: sudo install -m 0755 gog /usr/local/bin/gog

More info: https://github.com/steipete/gogcli
EOF
    exit 1
fi

echo "gog version: $(gog --version 2>/dev/null || echo 'unknown')"

# ?? 2. Is at least one account configured? ????????????????????????????????????
AUTH_OUTPUT=$(gog auth list 2>&1)
if echo "$AUTH_OUTPUT" | grep -qi "no tokens"; then
    cat <<'EOF'

ERROR: No Google account is configured in gog.

Setup steps:
  1. Go to https://console.cloud.google.com/apis/credentials
  2. Create an OAuth 2.0 Client ID (Desktop App type)
  3. Download the client_secret.json file
  4. Run:
       gog auth credentials /path/to/client_secret.json
       gog auth add you@gmail.com --services gmail,calendar,drive,contacts,sheets,docs
  5. A browser window will open ? authorize the app.

After setup, try again.
EOF
    exit 1
fi

echo ""
echo "Configured accounts:"
echo "$AUTH_OUTPUT"
echo ""
echo "Ready to use Google Workspace commands."
