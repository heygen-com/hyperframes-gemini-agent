#!/bin/bash
# Base-env setup 1/3 — Google Chrome (for local HyperFrames rendering).
#
# Why this is fiddly: the Gemini sandbox runs gVisor as root with an overlay FS
# and an egress MITM proxy. `apt-get install` crashes on systemd postinst, /opt
# is mounted noexec, and parallel dpkg extraction hits Bus errors. So we:
#   - apt-get *download* (not install) Chrome + its recursive deps
#   - dpkg -x extract sequentially
#   - copy Chrome out of /opt (noexec) into /usr/local, then symlink onto PATH
# (Pattern proven by Thor's reference demo, thorwebdev/gemini-managed-hyperframes-agent.)
set -euo pipefail
log() { echo; echo "=== $1 ==="; }

log "Pre-installed tools"
echo "node $(node -v) | npm $(npm -v) | ffmpeg $(ffmpeg -version 2>&1 | head -1)"

if command -v google-chrome-stable >/dev/null 2>&1 && google-chrome-stable --version >/dev/null 2>&1; then
  echo "Chrome already present: $(google-chrome-stable --version)"; echo "=== setup 1/3 done ==="; exit 0
fi

log "Downloading Chrome .deb + recursive deps (download, not install)"
mkdir -p /workspace/debs && cd /workspace/debs
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /var/tmp/google-chrome.deb

deps="ca-certificates fonts-liberation libasound2t64 libatk-bridge2.0-0t64 libatk1.0-0t64 \
  libatspi2.0-0t64 libc6 libcairo2 libcups2t64 libcurl4 libdbus-1-3 libexpat1 libgbm1 \
  libglib2.0-0 libgtk-3-0t64 libnspr4 libnss3 libpango-1.0-0 libudev1 libvulkan1 libx11-6 \
  libxcb1 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxkbcommon0 libxrandr2 wget xdg-utils"
apt-get update -qq 2>/dev/null || true
apt-cache depends --recurse --no-recommends --no-suggests --no-conflicts --no-breaks \
  --no-replaces --no-enhances $deps | grep "^\w" | sort -u > /var/tmp/all_deps.txt
echo "Downloading $(wc -l < /var/tmp/all_deps.txt) packages..."
xargs apt-get download < /var/tmp/all_deps.txt 2>/dev/null || true

log "Extracting sequentially (parallel hits overlay-FS Bus errors)"
for deb in /workspace/debs/*.deb; do [ -f "$deb" ] && dpkg -x "$deb" / 2>/dev/null || true; done
dpkg -x /var/tmp/google-chrome.deb / 2>/dev/null || true

log "Relocating Chrome out of noexec /opt"
cp -a /opt/google/chrome /usr/local/chrome
ln -sf /usr/local/chrome/google-chrome /usr/bin/google-chrome-stable
ln -sf /usr/local/chrome/google-chrome /usr/bin/google-chrome
echo "Chrome: $(google-chrome-stable --version)"
echo "=== setup 1/3 done ==="
