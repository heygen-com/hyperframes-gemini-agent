#!/usr/bin/env python3
"""Pack this agent (AGENTS.md + skills/ + workspace/) into a Gemini Managed
Agents Interactions API request payload.

Mirrors the packer that ships with Google's own templates in
`google-gemini/gemini-managed-agents-templates`: it walks the agent files and
uploads each as an `inline` environment source, rooted under `/.agents/` in the
sandbox, then assembles the interaction request.

    python3 generate_payload.py --prompt "make a 15s social promo for Brew, dark theme"

Prints the payload JSON to stdout.

File mounting (verified against Google's template packer + docs):
  AGENTS.md            -> /.agents/AGENTS.md            (system instructions)
  skills/<name>/...    -> /.agents/skills/<name>/...    (auto-discovered skills)
  workspace/...        -> /.agents/workspace/...        (seed files)

Inline-source limits (per the Environments doc): 1 MB per file, 2 MB total. If
the packed agent ever exceeds that (e.g. larger vendored libs or real assets),
switch the heavy directory to a `gcs` (2 GB) or `repository` (500 MB) source
instead of inline.

------------------------------------------------------------------------------
PARTIALLY UNVERIFIED — the file-mounting shape (inline sources under /.agents/)
is confirmed from Google's template packer source. The request *envelope* below
(the exact top-level prompt field, and the network / HeyGen-key injection shape)
is from the preview docs and SHOULD be confirmed against a live call in Phase 0a
/ Phase 4. Update BASE_AGENT, the prompt field, and the network block once the
live schema is known.
------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

# Base agent for the managed-agents preview.
BASE_AGENT = "antigravity-preview-05-2026"

# The only host the sandbox must reach: api.heygen.com for the render API.
# (No npm registry — the direct-API render path needs no install.) The egress
# proxy injects the HeyGen `x-api-key` on this domain via `transform`, so the
# in-sandbox code holds no credential. The key value is read from the
# HEYGEN_API_KEY env at pack time and placed in the transform; the deployer
# provides it (it is not stored in the repo).
RENDER_HOST = "api.heygen.com"

# Directories/files packed into the sandbox, each rooted under /.agents/.
_PACK_ROOTS = ["AGENTS.md", "skills", "workspace"]

# Inline-source caps from the Environments doc.
_MAX_FILE_BYTES = 1 * 1024 * 1024
_MAX_TOTAL_BYTES = 2 * 1024 * 1024

# Extensions treated as text (inlined as UTF-8); everything else is base64.
_TEXT_EXTS = {".md", ".py", ".sh", ".json", ".html", ".css", ".js", ".txt", ".yaml", ".yml"}

# Runtime scratch the agent writes to — never packed as a seed source.
_SKIP_DIR_NAMES = {"output", "last_composition", "__pycache__", ".git"}


def _iter_files(root_rel: str):
    abs_root = os.path.join(REPO_ROOT, root_rel)
    if os.path.isfile(abs_root):
        yield abs_root
        return
    # followlinks=True so the external-skill symlinks under skills/ (created by
    # scripts/build-external-skills.mjs, pointing into the submodule) are packed.
    for dirpath, dirnames, filenames in os.walk(abs_root, followlinks=True):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIR_NAMES]
        for name in filenames:
            if name == ".DS_Store":
                continue
            yield os.path.join(dirpath, name)


def _make_source(abs_path: str) -> dict:
    rel = os.path.relpath(abs_path, REPO_ROOT)
    target = f"/.agents/{rel}"
    data = open(abs_path, "rb").read()
    if len(data) > _MAX_FILE_BYTES:
        raise SystemExit(
            f"{rel} is {len(data)} bytes, over the 1 MB inline-source cap. "
            "Move it to a gcs/repository source."
        )
    ext = os.path.splitext(abs_path)[1].lower()
    if ext in _TEXT_EXTS:
        return {"type": "inline", "target": target, "content": data.decode("utf-8")}
    # Binary inline source: base64 content + encoding (per the verified schema).
    return {
        "type": "inline",
        "target": target,
        "content": base64.b64encode(data).decode("ascii"),
        "encoding": "base64",
    }


def collect_sources() -> list[dict]:
    sources: list[dict] = []
    total = 0
    for root in _PACK_ROOTS:
        for abs_path in _iter_files(root):
            src = _make_source(abs_path)
            total += len(src.get("content", ""))
            sources.append(src)
    if total > _MAX_TOTAL_BYTES:
        raise SystemExit(
            f"Packed agent is ~{total} bytes, over the 2 MB total inline cap. "
            "Move the workspace (vendored libs / assets) to a gcs or repository source."
        )
    return sources


def _render_allowlist_entry() -> dict:
    # Allow the render host; if a HeyGen key is in the env at pack time, inject
    # it as the `x-api-key` header on that host via the proxy `transform` so the
    # sandbox code needs no credential. The key is never written to the repo.
    entry: dict = {"domain": RENDER_HOST}
    key = os.environ.get("HEYGEN_API_KEY")
    if key:
        entry["transform"] = [{"x-api-key": key}]
    return entry


def build_payload(prompt: str, environment_id: str | None) -> dict:
    payload: dict = {
        "input": prompt,
        "agent": BASE_AGENT,
        "environment": {
            "type": "remote",
            "sources": collect_sources(),
            "network": {"allowlist": [_render_allowlist_entry()]},
        },
    }
    # Reuse a persistent sandbox across turns for multi-turn iteration.
    if environment_id:
        payload["environment_id"] = environment_id
    return payload


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True, help="The user request to send to the agent")
    parser.add_argument(
        "--environment-id",
        default=None,
        help="Reuse an existing sandbox environment for multi-turn iteration",
    )
    args = parser.parse_args(argv)
    print(json.dumps(build_payload(args.prompt, args.environment_id), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
