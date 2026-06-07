---
name: render-and-return
description: Render the staged composition on HeyGen's cloud and return the playable video URL to the user. Use as the final step, after customize-composition.
---

# Render and return the video

The last step. Submit the staged composition plus its variables to HeyGen's
cloud render and give the user a URL they can play.

You do **not** render locally — the sandbox has no Chrome or ffmpeg. A small
Python helper POSTs the composition to HeyGen's render API over HTTPS and polls
for the finished video.

## Inputs (from customize-composition)

- `/.agents/workspace/output/composition/` — the staged composition directory.
- `/.agents/workspace/output/variables.json` — validated variable values.

You also need the composition's **aspect ratio**, which must match the
composition's authored dimensions (the renderer supersamples to a matching
ratio, it can't reshape). Read it from the chosen composition's manifest:

```bash
ASPECT=$(jq -r '.aspect_ratio' /.agents/workspace/compositions/<chosen-id>/manifest.json)
```

`<chosen-id>` is whatever you picked in pick-composition (`social-promo` →
`9:16`, `app-trailer` / `explainer` → `16:9`). Getting it wrong is the most
common render failure for the vertical starter.

## The HeyGen API key — nothing to do

You don't handle the key. The sandbox's egress proxy injects the HeyGen
`x-api-key` header automatically on requests to `api.heygen.com`. The helper
sends no credential itself. Never try to read, set, or print a key.

## Render

```bash
set +x
RESULT=$(python3 /.agents/workspace/scripts/render_client.py \
  /.agents/workspace/output/composition \
  /.agents/workspace/output/variables.json \
  "{\"resolution\":\"1080p\",\"aspect_ratio\":\"$ASPECT\"}")

VIDEO_URL=$(echo "$RESULT" | jq -r '.video_url')
THUMB_URL=$(echo "$RESULT" | jq -r '.thumbnail_url')
DURATION=$(echo "$RESULT" | jq -r '.duration')
```

`render_client.py` zips the composition directory, submits it to
`POST /v3/hyperframes/renders`, polls until the render finishes, and prints a
JSON object: `{"render_id","video_url","thumbnail_url","duration","format"}`.
Output is flat — parse `.video_url`, not `.render.video_url`.

## Returning the result

Once you have `VIDEO_URL`:

- Lead your reply with the playable URL. Add one short line of context
  ("Here's your 30-second app trailer:").
- Mention the duration if you have it.
- The URL is a HeyGen-CDN link; the rendered video is already hosted there.

## When the render fails

`render_client.py` exits non-zero and prints the API's `failure_message` on a
failed render. Show the user a plain, useful message ("The render failed:
<reason>. Want me to try again or adjust the composition?") — never a raw stack
trace. Common causes: an aspect ratio that doesn't match the composition, or an
invalid variable that slipped past validation. If it's the aspect ratio,
re-check the manifest value.
