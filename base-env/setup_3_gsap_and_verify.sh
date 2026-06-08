#!/bin/bash
# Base-env setup 3/3 — local GSAP cache, cleanup, verification.
#
# We do NOT `skills add` here (Thor's demo does): this template mounts its own
# skills at /.agents/skills/ as inline sources, so they're already present.
#
# We DO pre-download GSAP locally: headless Chrome rejects CDN TLS certs behind
# the sandbox's mitmproxy, so any composition the agent free-authors must load
# GSAP from a local file, not from a CDN. Our shipped starters already vendor
# gsap.min.js; this cache covers net-new compositions the agent writes.
set -euo pipefail
log() { echo; echo "=== $1 ==="; }
export NODE_TLS_REJECT_UNAUTHORIZED=0
export HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell

log "1/3 Local GSAP cache (for free-authored compositions)"
mkdir -p /workspace/.cache/libs
if [ -f /workspace/.cache/libs/gsap.min.js ]; then
  echo "GSAP already cached"
else
  curl -sk -o /workspace/.cache/libs/gsap.min.js https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js
  echo "GSAP: $(wc -c < /workspace/.cache/libs/gsap.min.js) bytes (reference local copies via file path, never a CDN)"
fi

log "2/3 Cleanup"
rm -rf /workspace/debs /var/tmp/google-chrome.deb /var/tmp/chs /var/tmp/all_deps.txt 2>/dev/null || true

log "3/3 Verification"
echo "  ffmpeg:                $(ffmpeg -version 2>&1 | head -1)"
echo "  chrome:                $(google-chrome-stable --version 2>&1)"
echo "  chrome-headless-shell: $(chrome-headless-shell --version 2>&1)"
echo "  hyperframes:           $(hyperframes --help 2>&1 | head -1)"
echo "  GSAP cache:            $(wc -c < /workspace/.cache/libs/gsap.min.js 2>/dev/null || echo 0) bytes"
echo "  BROWSER_PATH:          ${HYPERFRAMES_BROWSER_PATH:-NOT SET}"
echo "  agent skills:          $(ls /.agents/skills/ 2>/dev/null | wc -l) mounted"
echo
echo "=== BASE-ENV SETUP COMPLETE ==="
