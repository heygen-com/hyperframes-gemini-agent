---
name: pick-composition
description: Choose the best starter composition for the user's request. Use this first, at the start of every new video request, before generating any content.
---

# Pick a starter composition

Your first step for any new video. Read the user's prompt and choose one
starter from `/.agents/workspace/compositions/`. Don't author HTML — every starter is
already a working HyperFrames project; you only pick one and (later) fill in
its variables.

## How to choose

1. List the available starters: each directory under `/.agents/workspace/compositions/`
   has a `manifest.json`. Read all of them.
2. Match the user's intent against each manifest's `use_case`, `aspect_ratio`,
   `duration_seconds`, and `tags`.
3. Pick the single best fit.

Rules of thumb:

- **Vertical / social / short / "for TikTok or Reels" / "a quick teaser"** →
  `social-promo` (9:16, ~6s).
- **"Trailer", "product video", "show off my app", "promo for my SaaS"** →
  `app-trailer` (16:9, ~12s, three scenes).
- **"Explain", "how it works", "walk through", "onboarding", "tutorial"** →
  `explainer` (16:9, ~14s, numbered steps).

If the user names an aspect ratio (portrait vs landscape), let that override the
vibe match — a portrait request should land on `social-promo` even if the
content is product-y.

If the user explicitly names a starter ("use the explainer"), use it.

## Output of this step

Decide on one composition id (`social-promo`, `app-trailer`, or `explainer`)
and remember it for the rest of the pipeline. Tell the user briefly what you
picked and why ("I'll use the app trailer — landscape, three scenes, good for
showing features"). Then move to **generate-script**.
