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
command -v hyperframes && command -v chrome-headless-shell   # both present ⇒ local is possible
```

Then decide, in priority order:

1. **User override** — prompt says "render locally" / "use local" → local (only
   if the env supports it; if not, say so and fall back to cloud). Prompt says
   "use cloud" / "cloud render" → cloud, always.
2. **Free composition** — you authored net-new HTML beyond a starter (custom
   animation the starters can't express). That needs local Chrome to lint /
   render. If the env supports local → local. If not → cloud render with a
   warning that a freely-authored composition may not render exactly right
   without local Chrome.
3. **Default → cloud.** Fast, no broad allowlist, shareable URL. The path for
   every normal starter-based video.

Decision tree:
- user "local" AND env has Chrome+CLI → **local**
- user "cloud" → **cloud**
- free-composition needed AND env has Chrome+CLI → **local**
- free-composition needed AND env missing Chrome+CLI → **cloud** + degradation warning
- otherwise → **cloud**

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
  /.agents/workspace/output/video.mp4 1080p)
LOCAL_PATH=$(echo "$RESULT" | jq -r '.local_path')
RENDER_SECONDS=$(echo "$RESULT" | jq -r '.render_seconds')
```

`render_local.py` runs `hyperframes render` with
`HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell`. It produces a file in
the sandbox. To give the user something playable you must then make it
reachable — upload it (e.g. a HeyGen asset upload) and return that URL. Note the
local file path and render time so the user knows it ran locally.

## Returning the result

Lead with the playable URL (cloud) or the uploaded URL (local). Mention the
duration. If you rendered locally, it's fine to note it took longer. On a
failure, show the API/CLI `failure_message` plainly — never a raw stack trace.
