# Local-render spike — findings (2026-06-08)

Branch `feat/local-chrome-cli-spike` (unpushed). Tries the external team's
approach: install Chrome + the `hyperframes` CLI in the Gemini sandbox and
render **locally**, vs our default **cloud** render (`POST /v3/hyperframes/renders`).
Reference: Thor's `thorwebdev/gemini-managed-hyperframes-agent`.

## What worked

- **Local render is feasible.** Chrome runs under the gVisor sandbox
  (`--no-sandbox --headless`); the base-env (Chrome 149 + chrome-headless-shell +
  hyperframes 0.6.81 + ffmpeg + GSAP cache + all 18 skills) installs in one
  interaction (~25 min, one-time) and is snapshotted to a reusable `env_id`.
- **2 of 3 test renders completed** (silent, focus on render not TTS):
  - `local_stillpoint.mp4` (9:16, 6s) — starter render, **on par with cloud**.
  - `local_trace.mp4` (16:9, 12s) — **the win**: a *free-authored* composition
    with an actual animated UI mockup (tilted app window, "Brain Map" canvas with
    connected nodes, sidebar, Live Sync) + feature bullets + gradient. Cloud mode
    for the same prompt rendered "Animated UI Mockups" as plain bullet *text* —
    it can't author novel HTML. Local mode let the agent write + lint + validate
    + render custom GSAP/CSS. This is the qualitative lift the spike was testing.

## What broke / blocked

- **3rd render (Voxel free-composition) hit a Gemini quota 429** ("not enough
  quota") — James's account was exhausted after the two heavy local renders.
  Voxel didn't render. (Trace already demonstrates free-authoring, so the core
  hypothesis is evidenced; Voxel would be a second data point.)
- An API gotcha cost a run: passing `tools=[...]` when reusing a saved `env_id`
  → server 500. The base agent has code-execution natively; don't re-pass tools
  on env reuse.

## The real cost — local is much heavier

| | Cloud (prior builds) | Local (this spike) |
|---|---|---|
| Stillpoint | ~265k tok · ~100s | **507k tok · 890s (~15 min)** |
| Trace | ~600k tok · ~130s | **3.2M tok · 1730s (~29 min)** |

Local render is ~**7–13× the wall-clock** and ~**2–5× the tokens**. Free-authoring
(Trace) is the expensive end — author + lint + validate + render iterations burned
3.2M tokens. Plus a one-time ~25-min base-env install (amortized over the env's
~7-day TTL).

## Other limitations

- **Wildcard `"*"` network allowlist** — needed for the installs (npmjs,
  dl.google.com, storage.googleapis.com, github). This is a **yellow flag for
  Google's template-gallery review**. For production it should be narrowed to the
  specific install hosts + (if used) the GCS bucket.
- **Local render produces a sandbox file, not a shareable URL** (cloud returns a
  CDN URL directly). Added an optional GCS upload to `render_local.py`
  (`GCS_BUCKET` env → public URL; else `file://` fallback). HeyGen `/v3/assets`
  upload is an alternative route.
- Headless Chrome rejects CDN TLS under the mitmproxy → GSAP must be local (our
  starters already vendor it; the base-env caches GSAP for free-authored comps).

## Recommendation — keep dual-mode; cloud stays default

The dual-mode design is the right answer, and the data supports it:

- **Cloud = default** for the ~95% starter-based case: fast (<1 min), cheap, a
  shareable URL, and only `api.heygen.com` allowlisted. Lite users never touch
  the heavy base-env.
- **Local = opt-in** (the heavy base-env) for **free-composition / website-capture**,
  where authoring novel HTML is worth the 10× cost. The runtime routing already
  built (user-override → free-composition → env-capability → default cloud)
  selects correctly.
- **Gallery ships ONE template.** Downstream users who want free-authoring create
  the base-env snapshot; everyone else gets cloud by default.

Net: local mode is a real capability unlock (free-authoring), not a replacement —
it's a slow, expensive, broad-allowlist path you reach for only when the prompt
needs more than a starter. Worth shipping behind the dual-mode routing; not worth
making the default.
