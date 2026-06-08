---
name: render-and-return
description: Render the staged composition and return the playable video. Picks between HeyGen cloud render (default) and local in-sandbox render at runtime. Use as the final step, after customize-composition.
---

# Render and return the video

Two render paths, chosen at runtime:

- **Cloud** (default) — `render_client.py` POSTs to HeyGen's render API and gets
  back a CDN video URL. Fast (<1 min), no install, only `api.heygen.com` needed,
  the user gets a shareable URL directly.
- **Local** — `render_local.py` runs the `hyperframes` CLI with headless Chrome
  in the sandbox. Only available in the heavy "base environment" (Chrome + CLI
  installed). Slower (minutes, sandbox CPU) and produces a sandbox *file* (not a
  shareable URL on its own), but it can render compositions you authored from
  scratch (free composition), not just the starters.

## Inputs (from customize-composition)

- `/.agents/workspace/output/composition/` — the staged composition directory
  (voiceover already baked in).
- `/.agents/workspace/output/variables.json` — validated variable values (cloud
  path passes these via the API; for local, they're already substituted/used).
- The chosen composition's aspect ratio (from its manifest).

## Routing — pick the path

Detect the environment first:

```bash
# Local is possible only if BOTH binaries resolve to a real, executable target.
# `command -v` alone passes a dangling symlink — dereference + test -x.
local_ok=yes
for bin in hyperframes chrome-headless-shell; do
  p=$(command -v "$bin" 2>/dev/null) && [ -x "$(readlink -f "$p" 2>/dev/null)" ] || local_ok=no
done
echo "local render available: $local_ok"
```

Then decide, in priority order:

1. **User override** — prompt says "render locally" / "use local" → local (only
   if the env supports it; if not, say so and fall back to cloud). Prompt says
   "use cloud" / "cloud render" → cloud, always.
2. **Free composition** — decided by the explicit classification below (not a
   keyword guess). If free-composition is required AND the env supports local →
   local. If required but the env lacks Chrome+CLI → cloud with a degradation
   warning (a freely-authored composition may not render exactly right without
   local Chrome).
3. **Default → cloud.** Fast, no broad allowlist, shareable URL. The path for
   every normal starter-based video.

### Classify: is free-composition required? (explicit, not keyword-matching)

Substring matching is wrong here — "kinetic-text social promo" sounds
authoring-heavy but the social-promo starter already does kinetic text (no
free-auth), while "animate the React useState hook with code samples" sounds
simple but needs custom code-block animation (free-auth). So **make the call
explicitly**: answer this in one line before routing —

> *"Does this prompt require free-form HTML/CSS/GSAP authoring beyond what a
> starter + its variables can express? Answer yes/no with one sentence of
> reasoning."*

`yes` → free-composition. `no` → a starter fits; use it (cloud). Record the
answer + reasoning (it goes in the render result for debugging).

Decision tree (after the classification):
- user "local" AND env has Chrome+CLI → **local**
- user "cloud" → **cloud**
- free-composition = yes AND env has Chrome+CLI → **local**
- free-composition = yes AND env missing Chrome+CLI → **cloud** + degradation warning
- otherwise → **cloud**

### Token budget

Local + free-composition renders are token-expensive (free-auth can burn
millions of tokens — author + lint + validate + render iterations). Respect a
budget: read `MAX_TOKENS_PER_RENDER` (default 4,000,000). Keep a rough running
count of tokens spent. This is **enforced, not advisory**: once the count
crosses the ceiling, **abort the render with a clean error** — do not keep
going. Return: "Stopped at the token budget (`MAX_TOKENS_PER_RENDER`). Increase
it or simplify the prompt (free-composition is the expensive path)." Surface
whatever partial work exists, but do not silently run to exhaustion. Always
report total tokens spent in your final summary so the user sees the cost (local
is far pricier than cloud — see docs/local-mode.md).

## Cloud path

```bash
set +x
ASPECT=$(jq -r '.aspect_ratio' /.agents/workspace/compositions/<chosen-id>/manifest.json)
RESULT=$(python3 /.agents/workspace/scripts/render_client.py \
  /.agents/workspace/output/composition \
  /.agents/workspace/output/variables.json \
  "{\"resolution\":\"1080p\",\"aspect_ratio\":\"$ASPECT\"}")
VIDEO_URL=$(echo "$RESULT" | jq -r '.video_url')
```

The egress proxy injects the HeyGen key; you pass no credential. Returns a
HeyGen-CDN URL — give it straight to the user.

## Local path

```bash
set +x
RESULT=$(python3 /.agents/workspace/scripts/render_local.py \
  /.agents/workspace/output/composition \
  /.agents/workspace/output/video.mp4)
VIDEO_URL=$(echo "$RESULT" | jq -r '.video_url')      # gs/public URL if GCS_BUCKET set, else file://…
RENDER_SECONDS=$(echo "$RESULT" | jq -r '.render_seconds')
```

`render_local.py` runs `hyperframes render` at the composition's native
resolution with `HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell`, then
publishes the file: if `GCS_BUCKET` is set it uploads to GCS and returns a
public URL; otherwise it returns a `file://` path (sandbox-local) with a note.
So a deploy that wants shareable local-render URLs sets `GCS_BUCKET` (+ GCP
auth). If `video_url` is a `file://`, tell the user it rendered locally and the
file lives in the sandbox. Note the render time (local is slower than cloud).

## When local render fails

`render_local.py` raises on a nonzero exit / timeout / missing output. Handle by
failure mode — **the general rule is: fall back to cloud render when the failure
is environmental, surface + fix when it's the composition.**

| Failure | What it means | Do |
|---|---|---|
| Chrome crashes mid-render | Environmental (sandbox/Chrome) | Retry local **once**; if it crashes again, **fall back to cloud render** and tell the user it rendered on the cloud instead. |
| `hyperframes lint` fails on your authored HTML | The composition is malformed (your bug) | **Fix the HTML** per the lint message and re-render. Don't fall back — cloud would fail the same way. |
| GSAP runtime error at page-init | Composition bug (bad selector, non-deterministic code, CDN GSAP) | Fix it — most commonly: load GSAP from the local cache (`/workspace/.cache/libs/gsap.min.js`), not a CDN; remove `Math.random()`/`Date.now()`. Re-render. |
| Local render exceeds its timeout (20 min) | Too-heavy composition or a stuck Chrome | Fall back to cloud if the composition is starter-based; if it's free-auth, simplify and retry, and warn the user. |
| Token budget approached | Free-auth ran long | Stop gracefully, return what you have or fall back to cloud, and warn (see Token budget above). |

Always prefer returning *something* (a cloud-rendered video + a note) over
returning nothing. Never paste a raw stack trace.

## Returning the result

Lead with the playable URL (cloud) or the uploaded URL (local). Mention the
duration. If you rendered locally, it's fine to note it took longer. If you fell
back from local to cloud, say so briefly. On a failure, show the API/CLI
`failure_message` plainly — never a raw stack trace.
