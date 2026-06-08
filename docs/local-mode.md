# Local render mode (opt-in)

By default this agent renders on HeyGen's cloud (`POST /v3/hyperframes/renders`)
— fast, cheap, returns a shareable URL, needs only `api.heygen.com`. That's the
right path for the ~95% of prompts that a starter + variables can express.

**Local mode** installs Chrome + the `hyperframes` CLI *inside* the Gemini
sandbox and renders there. Its one real advantage: the agent can **author novel
compositions** (custom HTML/CSS/GSAP) beyond the starters and render them — e.g.
a bespoke animated UI mockup or a code-walkthrough. The tradeoff is steep.

## When to opt in

Opt into local mode only if your prompts genuinely need **free-form authoring**
(custom animation a starter can't express) or **website capture**. For
starter-based videos (social promos, app trailers, explainers), stay on cloud.

The agent routes automatically (see `base-env/ROUTING.md`): it uses local only
when free-composition is required *and* the base env is present, or when you
explicitly say "render locally".

## Setup

Local mode requires the heavy base environment. Build + snapshot it once:

```bash
GEMINI_API_KEY=... python3 base-env/snapshot.py   # ~25 min one-time; saves base-env/env_id.txt
```

This installs Chrome, chrome-headless-shell, the hyperframes CLI, ffmpeg, and a
local GSAP cache, then snapshots the environment (reuse the saved `env_id` for
~7 days — no reinstall per render).

## Environment variables

| Var | Purpose | Default |
|---|---|---|
| `GCS_BUCKET` | Upload local renders to GCS + return a public URL. Without it, local renders produce a sandbox `file://` path only (not user-shareable). | unset → file path |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP auth for the GCS upload (service-account JSON), or workload identity. | — |
| `MAX_TOKENS_PER_RENDER` | Graceful token-budget ceiling; the agent stops + warns as it approaches. | 4,000,000 |
| `HYPERFRAMES_BROWSER_PATH` | Headless Chrome path (set by setup). | `/usr/bin/chrome-headless-shell` |

## Cost + latency expectations

Local render is **much heavier than cloud** (measured on the spike):

| | Cloud | Local |
|---|---|---|
| Wall-clock | <1 min | **~15–30 min** per render |
| Tokens | ~250k–600k | **~0.5M–3M+** (free-auth is the high end) |
| Network | `api.heygen.com` only | broad install allowlist (see `ALLOWLIST.md`) |
| Output | CDN URL | sandbox file (or GCS URL if configured) |

Budget accordingly: a free-composition local render can take half an hour and
burn millions of tokens. The `MAX_TOKENS_PER_RENDER` guard prevents silent
runaway. If you're on a metered Gemini plan, watch the cost.

## Security note

The base-env install needs a broader egress allowlist than cloud mode (the
package/CDN hosts in `ALLOWLIST.md`). The spike used a wildcard `"*"`; that's
narrowed to a closed host list for the gallery template. If you extend the
setup, add new hosts to `ALLOWLIST.md`.
