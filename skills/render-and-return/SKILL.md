---
name: render-and-return
description: Render the staged composition on HeyGen's cloud and return the playable video URL to the user. Use as the final step, after customize-composition.
---

# Render and return the video

The last step. Send the staged composition plus its variables to HeyGen's
cloud render and give the user a URL they can play.

You do **not** render locally — the sandbox has no Chrome or ffmpeg. The
`hyperframes cloud render` command uploads the composition and renders it on
HeyGen's side, then hands back a video URL.

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
`9:16`, `app-trailer` / `explainer` → `16:9`). The CLI also auto-detects the
ratio from the composition, so passing it is belt-and-suspenders, but getting
it wrong is the most common render failure for the vertical starter.

## The HeyGen API key

The key arrives as the `HEYGEN_API_KEY` environment variable. The CLI reads it
from the environment on its own — you don't pass it on the command line.
**Never print it or echo the environment.** Start shell steps with `set +x` so
it can't leak into the transcript.

## Render

```bash
set +x
RESULT=$(hyperframes cloud render /.agents/workspace/output/composition \
  --variables-file /.agents/workspace/output/variables.json \
  --aspect-ratio "$ASPECT" \
  --resolution 1080p \
  --json)

VIDEO_URL=$(echo "$RESULT" | jq -r '.render.video_url')
THUMB_URL=$(echo "$RESULT" | jq -r '.render.thumbnail_url')
DURATION=$(echo "$RESULT" | jq -r '.render.duration')
```

Notes:

- `hyperframes cloud render` takes the composition **directory** directly. It
  zips it (with the same ignore rules as `hyperframes publish`), uploads it,
  submits the render, polls to completion, and downloads the result. You don't
  bundle a zip yourself.
- `--json` nests the result under `.render` — note the `.render.video_url`
  path.
- If the `hyperframes` CLI isn't on the path yet, install it once (it's cached
  for the life of the environment):

  ```bash
  set +x
  npm install -g hyperframes
  ```

  This installs the CLI but does **not** download Chrome — that only happens on
  a local `hyperframes render`, which you never run. The cloud render needs no
  browser in the sandbox.

## Returning the result

Once you have `VIDEO_URL`:

- Lead your reply with the playable URL. Add one short line of context
  ("Here's your 30-second app trailer:").
- Mention the duration if you have it.
- The URL is a HeyGen-CDN link; the rendered video is already hosted there.

## When the render fails

The CLI prints a `failure_message` from the API on a failed render. Show the
user a plain, useful message ("The render failed: <reason>. Want me to try
again or adjust the composition?") — never a raw stack trace or the command
output. Common causes: an aspect ratio that doesn't match the composition, or
an invalid variable that slipped past validation. If it's the aspect ratio,
re-check the manifest value.
