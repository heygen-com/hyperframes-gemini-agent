#!/usr/bin/env python3
"""Render a HyperFrames composition LOCALLY in the sandbox via the hyperframes CLI.

The opt-in "local" render path (vs render_client.py's cloud API). Requires the
heavy base environment: Chrome / chrome-headless-shell / the hyperframes CLI
must be installed (see base-env/setup_*.sh). Runs Chrome + ffmpeg in-sandbox —
no HeyGen render API call, but slow (sandbox CPU, no GPU) and needs the broad
network/base-env that the cloud path doesn't.

Usage:
    python3 render_local.py <composition_dir> <output.mp4> [resolution]

Prints: {"local_path", "render_seconds", "duration", "returncode"}

Note: this produces a FILE inside the sandbox — not a shareable URL. To return
something the user can open, the caller must upload it (production: a HeyGen
asset upload; the cloud path returns a CDN URL directly, which is one reason
cloud is the default). render_seconds lets the routing compare against cloud.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

BROWSER_PATH = os.environ.get("HYPERFRAMES_BROWSER_PATH", "/usr/bin/chrome-headless-shell")


def _duration(path: str):
    if not shutil.which("ffprobe"):
        return None
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nk=1:nw=1", path],
            capture_output=True, text=True, timeout=30,
        )
        return float(out.stdout.strip()) if out.stdout.strip() else None
    except Exception:
        return None


def render(comp_dir: str, output: str, resolution: str = "1080p") -> dict:
    if not shutil.which("hyperframes"):
        raise SystemExit("hyperframes CLI not found — this sandbox isn't a local-render base-env.")
    os.makedirs(os.path.dirname(os.path.abspath(output)) or ".", exist_ok=True)
    env = {**os.environ, "HYPERFRAMES_BROWSER_PATH": BROWSER_PATH}
    # Render at the composition's authored dimensions. Do NOT force --resolution:
    # the resolution presets supersample by an integer DPR, and a comp whose
    # native size isn't an integer fraction of the preset (e.g. 720p→1080p = 1.5x)
    # is rejected. Our starters are authored at native 1080p (1080x1920 / 1920x1080).
    cmd = ["hyperframes", "render", comp_dir, "--output", output, "--format", "mp4", "--workers", "1"]
    t0 = time.monotonic()
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=20 * 60)
    secs = round(time.monotonic() - t0, 1)
    if proc.returncode != 0 or not os.path.isfile(output):
        tail = (proc.stderr or proc.stdout or "")[-600:]
        raise RuntimeError(f"local render failed (rc={proc.returncode}) after {secs}s:\n{tail}")
    return {
        "local_path": os.path.abspath(output),
        "render_seconds": secs,
        "duration": _duration(output),
        "returncode": 0,
    }


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    res = argv[3] if len(argv) > 3 else "1080p"
    print(json.dumps(render(argv[1], argv[2], res)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
