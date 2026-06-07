#!/usr/bin/env python3
"""Render a HyperFrames composition on HeyGen's cloud and return the video URL.

Direct HTTPS to POST /v3/hyperframes/renders using `requests` (pre-installed in
the Gemini managed-agent sandbox). No npm install, no native deps, no Chrome.

Why direct API over the `hyperframes` CLI in-sandbox (verified in Phase 0a,
2026-06): the gVisor sandbox routes all egress through an MITM proxy. A `requests`
call to api.heygen.com is clean (TLS verifies, only api.heygen.com need be
allowlisted). The CLI's `npm install` pulls native postinstalls (onnxruntime-node,
sharp) that need a broad allowlist + a DNS-patch preloader + TLS-verification
disabled — fragile and insecure for a public template.

Auth: the sandbox's egress proxy injects `x-api-key` on api.heygen.com via the
agent's network `transform` config, so this script needs NO key in-sandbox. When
run locally (key in HEYGEN_API_KEY), it sets the header itself. So the key is
OPTIONAL — present locally, injected by the proxy in-sandbox.

Usage:
    python3 render_client.py <composition_dir> <variables.json> [options-json]

options-json (optional), any of:
    {"resolution":"1080p"|"4k","aspect_ratio":"16:9"|"9:16"|"1:1",
     "format":"mp4"|"webm"|"mov","quality":"draft"|"standard"|"high",
     "fps":30,"composition":"index.html","title":"..."}

Prints on success:
    {"render_id","video_url","thumbnail_url","duration","format"}

API contract (verified): request {"project":{"type":"base64",
"media_type":"application/zip","data":"<b64>"}, "variables":{...}, ...};
response {"render_id"}; poll GET .../{id} until status completed (carries
video_url/thumbnail_url/duration) or failed (carries failure_message).
"""

from __future__ import annotations

import base64
import io
import json
import os
import sys
import time
import zipfile

import requests

API_BASE = os.environ.get("HEYGEN_API_URL", "https://api.heygen.com").rstrip("/")
RENDERS_URL = f"{API_BASE}/v3/hyperframes/renders"
POLL_INTERVAL_SECONDS = 5
MAX_WAIT_SECONDS = 30 * 60

_ALLOWED_OPTIONS = {"fps", "quality", "format", "resolution", "aspect_ratio", "composition", "title"}
_SKIP_NAMES = {"manifest.json", ".DS_Store"}


def _auth_headers() -> dict:
    # Optional: present when running locally; in-sandbox the egress proxy
    # injects x-api-key, so an absent key is expected and fine.
    key = os.environ.get("HEYGEN_API_KEY")
    return {"x-api-key": key} if key else {}


def _zip_composition(comp_dir: str) -> bytes:
    if not os.path.isfile(os.path.join(comp_dir, "index.html")):
        raise SystemExit(f"No index.html at the root of {comp_dir}")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(comp_dir):
            for fname in files:
                if fname in _SKIP_NAMES or fname.endswith((".pyc", ".swp")):
                    continue
                abs_path = os.path.join(root, fname)
                zf.write(abs_path, os.path.relpath(abs_path, comp_dir))
    return buf.getvalue()


def render(comp_dir: str, variables: dict, options: dict | None = None) -> dict:
    options = options or {}
    zip_b64 = base64.b64encode(_zip_composition(comp_dir)).decode("ascii")
    body: dict = {"project": {"type": "base64", "media_type": "application/zip", "data": zip_b64}}
    if variables:
        body["variables"] = variables
    for field in _ALLOWED_OPTIONS:
        if options.get(field) is not None:
            body[field] = options[field]

    resp = requests.post(RENDERS_URL, headers=_auth_headers(), json=body, timeout=60)
    resp.raise_for_status()
    render_id = resp.json().get("render_id")
    if not render_id:
        raise RuntimeError(f"No render_id in response: {resp.text[:300]}")

    deadline = time.monotonic() + MAX_WAIT_SECONDS
    while True:
        detail = requests.get(f"{RENDERS_URL}/{render_id}", headers=_auth_headers(), timeout=30).json()
        status = detail.get("status")
        if status == "completed":
            if not detail.get("video_url"):
                raise RuntimeError(f"Completed but no video_url: {json.dumps(detail)[:300]}")
            return {
                "render_id": render_id,
                "video_url": detail["video_url"],
                "thumbnail_url": detail.get("thumbnail_url"),
                "duration": detail.get("duration"),
                "format": detail.get("format"),
            }
        if status == "failed":
            raise RuntimeError(f"Render {render_id} failed: {detail.get('failure_message') or 'no reason'}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"Render {render_id} still '{status}' after {MAX_WAIT_SECONDS}s")
        time.sleep(POLL_INTERVAL_SECONDS)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[2]) as fh:
        variables = json.load(fh)
    options = json.loads(argv[3]) if len(argv) > 3 and argv[3].strip() else {}
    print(json.dumps(render(argv[1], variables, options)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
