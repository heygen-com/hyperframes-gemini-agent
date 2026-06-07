#!/usr/bin/env python3
"""Synthesize a voiceover via HeyGen TTS and return its audio URL + duration.

Direct HTTPS to POST /v3/voices/speech (the v3 starfish TTS endpoint — verified
against the OpenAPI spec + a live call). Same shape as render_client.py: pure
`requests`, no install, and the key is OPTIONAL — the sandbox's egress proxy
injects `x-api-key` on api.heygen.com, so this needs no credential in-sandbox;
when run locally, it reads HEYGEN_API_KEY from the env.

Usage:
    python3 tts_client.py "<text>" <voice_id> [speed]

Prints on success:
    {"audio_url": "...", "duration": 5.22, "voice_id": "...", "word_timestamps": [...]}

API contract (POST /v3/voices/speech):
  request  -> {"text": "...", "voice_id": "...", "speed"?: 1.0, "input_type"?: "text", "language"?: "en"}
  response -> {"data": {"audio_url", "duration", "request_id", "word_timestamps"}}
The voice MUST support the starfish engine (GET /v3/voices?engine=starfish).
"""

from __future__ import annotations

import json
import os
import sys

import requests

API_BASE = os.environ.get("HEYGEN_API_URL", "https://api.heygen.com").rstrip("/")
SPEECH_URL = f"{API_BASE}/v3/voices/speech"


def _auth_headers() -> dict:
    # Optional: set locally; in-sandbox the egress proxy injects x-api-key.
    key = os.environ.get("HEYGEN_API_KEY")
    return {"x-api-key": key} if key else {}


def synthesize(text: str, voice_id: str, speed: float = 1.0) -> dict:
    if not (1 <= len(text) <= 5000):
        raise SystemExit(f"text must be 1-5000 chars (got {len(text)})")
    body = {"text": text, "voice_id": voice_id, "input_type": "text", "speed": speed}
    resp = requests.post(SPEECH_URL, headers=_auth_headers(), json=body, timeout=60)
    if resp.status_code >= 300:
        raise RuntimeError(f"TTS failed ({resp.status_code}): {resp.text[:300]}")
    data = resp.json().get("data", resp.json())
    if not data.get("audio_url"):
        raise RuntimeError(f"TTS returned no audio_url: {json.dumps(data)[:300]}")
    return {
        "audio_url": data["audio_url"],
        "duration": data.get("duration"),
        "voice_id": voice_id,
        "word_timestamps": data.get("word_timestamps"),
    }


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    text, voice_id = argv[1], argv[2]
    speed = float(argv[3]) if len(argv) > 3 else 1.0
    print(json.dumps(synthesize(text, voice_id, speed)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
