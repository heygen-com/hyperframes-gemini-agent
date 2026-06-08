#!/bin/bash
# Base-env setup 2/3 — chrome-headless-shell + the hyperframes CLI.
#
# Sandbox constraints (proven by Thor's reference demo):
#   - Node.js DNS is blocked, so `npx @puppeteer/browsers install` fails. Fetch
#     chrome-headless-shell with curl instead (curl honors the HTTP proxy).
#   - `npm install -g hyperframes` runs an onnxruntime-node postinstall that
#     also fails on the blocked DNS — install with --ignore-scripts, then run
#     that postinstall manually with the proxy env vars set.
set -euo pipefail
log() { echo; echo "=== $1 ==="; }

log "1/2 chrome-headless-shell (via curl, not @puppeteer/browsers)"
if command -v chrome-headless-shell >/dev/null 2>&1 && chrome-headless-shell --version >/dev/null 2>&1; then
  echo "already present: $(chrome-headless-shell --version)"
else
  CHROME_VERSION=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE)
  echo "stable: $CHROME_VERSION"
  mkdir -p /var/tmp/chs && cd /var/tmp/chs
  curl -sO "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-headless-shell-linux64.zip"
  unzip -qo chrome-headless-shell-linux64.zip
  mkdir -p /usr/local/chrome-headless-shell
  cp -r chrome-headless-shell-linux64/* /usr/local/chrome-headless-shell/
  ln -sf /usr/local/chrome-headless-shell/chrome-headless-shell /usr/bin/chrome-headless-shell
  echo "chrome-headless-shell: $(chrome-headless-shell --version)"
fi

# Each sandbox command is a fresh non-login shell, so persist the browser path
# everywhere a later command might read it.
export HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell
echo 'export HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell' > /etc/profile.d/hyperframes.sh 2>/dev/null || true
echo 'HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell' >> /etc/environment 2>/dev/null || true
echo 'export HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell' >> ~/.bashrc 2>/dev/null || true

log "2/2 hyperframes CLI (--ignore-scripts, then manual onnxruntime postinstall)"
export NODE_TLS_REJECT_UNAUTHORIZED=0
if command -v hyperframes >/dev/null 2>&1; then
  echo "already present: $(hyperframes --help 2>&1 | head -1)"
else
  npm install -g --ignore-scripts hyperframes
  ONNX="/usr/lib/node_modules/hyperframes/node_modules/onnxruntime-node"
  if [ -f "$ONNX/script/install.js" ]; then
    echo "running onnxruntime-node postinstall via proxy..."
    (cd "$ONNX" && GLOBAL_AGENT_HTTPS_PROXY="${HTTPS_PROXY:-${HTTP_PROXY:-}}" \
       GLOBAL_AGENT_HTTP_PROXY="${HTTP_PROXY:-}" NODE_TLS_REJECT_UNAUTHORIZED=0 \
       node ./script/install 2>/dev/null) || echo "  (onnxruntime warning — non-fatal; only used by some skills)"
  fi
  echo "hyperframes: $(hyperframes --help 2>&1 | head -1)"
fi
echo "=== setup 2/3 done ==="
