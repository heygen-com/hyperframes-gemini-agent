#!/usr/bin/env bash
#
# Smoke test: invoke the agent with a fixed prompt and confirm it returns a
# playable video URL. Mirrors the prober pattern in Google's templates repo.
#
# Requires:
#   GEMINI_API_KEY   — your Gemini API key (Google bills the interaction)
#   HEYGEN_API_KEY   — the HeyGen key the sandbox uses to render
#
# Usage:
#   GEMINI_API_KEY=... HEYGEN_API_KEY=... ./probers/probe-render.sh
#
# ----------------------------------------------------------------------------
# UNVERIFIED endpoint + response shape. The Interactions API is in preview;
# the endpoint URL and the path to the video URL in the response below are
# best-effort from the public docs and MUST be confirmed against a live call
# (Phase 0a / Phase 4). Update INTERACTIONS_URL and the jq extraction once the
# real shape is known.
# ----------------------------------------------------------------------------

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROMPT="${PROBE_PROMPT:-make a 15-second social promo for a coffee app called Brew, dark theme}"

: "${GEMINI_API_KEY:?GEMINI_API_KEY must be set}"
: "${HEYGEN_API_KEY:?HEYGEN_API_KEY must be set}"

INTERACTIONS_URL="${INTERACTIONS_URL:-https://generativelanguage.googleapis.com/v1beta/interactions}"

echo "→ Building payload for prompt: ${PROMPT}"
PAYLOAD="$(python3 "${REPO_ROOT}/generate_payload.py" --prompt "${PROMPT}")"

echo "→ Invoking agent…"
RESPONSE="$(curl -sS -X POST "${INTERACTIONS_URL}" \
  -H "x-goog-api-key: ${GEMINI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}")"

# The agent returns its final text (which contains the video URL JSON or a
# markdown link). Try a couple of plausible extraction paths, then fall back to
# scraping the first https URL that looks like a video out of the raw text.
VIDEO_URL="$(echo "${RESPONSE}" | jq -r '
  (.output_text // .response // .text // empty)
' 2>/dev/null | grep -oE 'https://[^ ")]+' | head -n1 || true)"

if [[ -z "${VIDEO_URL}" ]]; then
  VIDEO_URL="$(echo "${RESPONSE}" | grep -oE 'https://[^ "\\]+\.(mp4|webm|mov)[^ "\\]*' | head -n1 || true)"
fi

if [[ -z "${VIDEO_URL}" ]]; then
  echo "✗ No video URL found in agent response." >&2
  echo "  Raw response (first 800 chars):" >&2
  echo "${RESPONSE:0:800}" >&2
  exit 1
fi

echo "→ Agent returned: ${VIDEO_URL}"
echo "→ Verifying it serves video…"
CONTENT_TYPE="$(curl -sSI "${VIDEO_URL}" | tr -d '\r' | awk -F': ' 'tolower($1)=="content-type"{print $2}')"

if [[ "${CONTENT_TYPE}" == video/* ]]; then
  echo "✓ Render produced a playable URL (content-type: ${CONTENT_TYPE})"
  exit 0
fi

echo "✗ URL did not serve a video (content-type: ${CONTENT_TYPE:-unknown})" >&2
exit 1
