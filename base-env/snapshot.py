#!/usr/bin/env python3
"""Build + snapshot the local-render base environment, and save its env id.

Mounts this agent's files (AGENTS.md + skills/ + workspace/) plus the three
setup scripts, runs the setup in one interaction (installs Chrome +
chrome-headless-shell + the hyperframes CLI), and records the resulting
`environment_id`. That id is the snapshot: later interactions reuse it via
`interactions.create(agent=..., environment="<env_id>")` so the heavy install
is paid once (env TTL ~7 days), not per render.

    GEMINI_API_KEY=... python3 base-env/snapshot.py
    # → writes base-env/env_id.txt

(Pattern from Thor's reference, thorwebdev/gemini-managed-hyperframes-agent.)
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import generate_payload as gp  # noqa: E402
from google import genai  # noqa: E402

SETUP_SCRIPTS = ["setup_1_chrome.sh", "setup_2_headless_and_cli.sh", "setup_3_gsap_and_verify.sh"]


def main() -> int:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    sources = gp.collect_sources()  # AGENTS.md + skills/ + workspace/ under /.agents/
    for name in SETUP_SCRIPTS:
        content = open(os.path.join(os.path.dirname(__file__), name), encoding="utf-8").read()
        sources.append({"type": "inline", "target": f"/workspace/{name}", "content": content})

    prompt = (
        "You are setting up a base environment for local HyperFrames rendering. The sandbox "
        "runs gVisor as root behind an MITM egress proxy. FIRST discover the proxy: run "
        "`env | grep -i proxy` and test reachability (the proxy IP VARIES per sandbox — e.g. "
        "10.100.0.1 or 10.100.3.1 on :8081; use whichever responds). Export "
        "GLOBAL_AGENT_HTTP_PROXY / HTTP_PROXY / HTTPS_PROXY to the working proxy and "
        "NODE_TLS_REJECT_UNAUTHORIZED=0. Then run these three scripts in order, one at a "
        "time, with bash, and paste each one's full output:\n"
        "1. bash /workspace/setup_1_chrome.sh\n"
        "2. bash /workspace/setup_2_headless_and_cli.sh\n"
        "3. bash /workspace/setup_3_gsap_and_verify.sh\n\n"
        "After all three finish, confirm the final verification block shows Chrome, "
        "chrome-headless-shell, hyperframes, ffmpeg, and the GSAP cache all present."
    )

    it = client.interactions.create(
        agent="antigravity-preview-05-2026",
        tools=[{"type": "code_execution"}, {"type": "google_search"}],
        environment={"type": "remote", "sources": sources, "network": {"allowlist": [{"domain": "*"}]}},
        input=prompt,
        timeout=2400,
    )
    env_id = getattr(it, "environment_id", None)
    print("status:", getattr(it, "status", "?"), "| steps:", len(getattr(it, "steps", []) or []))
    print("environment_id:", env_id)
    print("OUTPUT TAIL:\n", (getattr(it, "output_text", None) or "")[-1500:])
    if env_id and getattr(it, "status", "") == "completed":
        out = os.path.join(os.path.dirname(__file__), "env_id.txt")
        open(out, "w").write(env_id)
        print("saved", out)
        return 0
    print("setup did not complete cleanly — env_id not saved")
    return 1


if __name__ == "__main__":
    sys.exit(main())
