# HyperFrames Video Studio — a Gemini Managed Agent

Turn a text prompt into a finished, playable video.

You describe what you want ("a 30-second trailer for my note-taking app, calm
pastel palette") and the agent writes the copy, picks the colors, and renders a
real MP4 on HeyGen's cloud. It hands back a URL you can play right away.

Built on the [Gemini Managed Agents API](https://ai.google.dev/gemini-api/docs/managed-agents-quickstart).
The agent runs in Google's hosted sandbox; the video render runs on HeyGen's
infrastructure. No Chrome, ffmpeg, or render farm of your own required.

## How it works

The agent is a thin authoring-and-dispatch layer. It runs four steps:

1. **Pick a starter** — choose one of three built-in compositions based on what
   you asked for (a vertical social promo, a landscape app trailer, or a
   step-by-step explainer).
2. **Write the content** — decide the headline, the feature lines, the
   voiceover copy, and the colors from your prompt.
3. **Customize** — fill those values into the chosen starter's variables and
   validate them.
4. **Render and return** — send it to HeyGen's render API and give you back the
   video URL.

By default the heavy lifting (browser, encoding, hosting) happens on HeyGen's
cloud — fast, cheap, and it returns a shareable URL. That's the path for almost
every video.

There's also an **opt-in local render mode** for advanced use (free-form
composition authoring beyond the starters, or website capture): it installs
Chrome + the `hyperframes` CLI into a heavy "base environment" and renders
in-sandbox. It's much slower and pricier (~15–30 min, far more tokens) and needs
a broader network allowlist, so it's strictly opt-in — see
[docs/local-mode.md](docs/local-mode.md). The agent picks cloud vs local at
runtime; cloud is the default and the only path in a normal environment.

## Starter compositions

| Starter | Aspect | Length | Best for |
|---|---|---|---|
| `social-promo` | 9:16 | ~6s | Short vertical social ad or teaser |
| `app-trailer` | 16:9 | ~12s | Product / feature trailer for an app or SaaS |
| `explainer` | 16:9 | ~14s | How-it-works, onboarding, tutorials |

Each starter lives in `workspace/compositions/<id>/` as a self-contained
HyperFrames project. The parts you can change (text, colors) are declared as
[composition variables](https://hyperframes.heygen.com) on the composition's
`<html>` element via `data-composition-variables`, and mirrored in a
`manifest.json` the agent reads when routing.

Each starter **vendors GSAP locally** (`vendor/gsap.min.js`) rather than loading
it from a CDN. On the cloud-render path a parser-blocking `<script src="https://…">`
in `<head>` fails open if the CDN is slow or down, which can stall the render
(`window.__hf not ready`). Bundling the library in the zip removes that network
dependency. Keep it this way — don't switch starters back to a CDN `<script>`.

## Setup

### 1. A HeyGen API key

The render step calls HeyGen's API, so the sandbox needs a HeyGen key, injected
as the `HEYGEN_API_KEY` environment variable. Two ways to provide it:

- **Bring your own key (recommended)** — paste your own HeyGen API key.
  Renders bill to your HeyGen account. Don't have one? Sign up at
  [app.heygen.com](https://app.heygen.com).
- **Shared demo key** — for launch-week trials only, with a hard per-day cap.

The key is read from the environment at render time and never printed or logged.

### 2. A Gemini API key

Invoking the agent uses your Gemini API key (`x-goog-api-key`). Google bills the
interaction tokens; HeyGen bills the render.

## Using it

### From the AI Studio Playground

Open AI Studio → Agents, pick **HyperFrames Video Studio**, set your HeyGen key,
and type a prompt.

### From the Interactions API

```bash
python3 generate_payload.py --prompt "make a 15s social promo for Brew, dark theme" \
  | curl -sS -X POST https://generativelanguage.googleapis.com/v1beta/interactions \
      -H "x-goog-api-key: $GEMINI_API_KEY" \
      -H "Content-Type: application/json" \
      -d @-
```

> The exact Interactions API endpoint and response shape are being confirmed
> against the live preview API — see the note in `generate_payload.py`.

## Repository layout

```
hyperframes-gemini-agent/
├── AGENTS.md                       # Agent persona + the four-step pipeline
├── skills/                         # 4 core skills (real dirs) + symlinked external skills
│   ├── pick-composition/SKILL.md
│   ├── generate-script/SKILL.md
│   ├── customize-composition/SKILL.md
│   ├── render-and-return/SKILL.md
│   └── <external>  ->  ../external-skills/hyperframes/skills/<name>   (generated symlinks)
├── external-skills/hyperframes/    # git submodule (sparse: skills/ only), pinned SHA
├── scripts/build-external-skills.mjs   # classify + symlink external skills, write manifest
├── skills-compat-manifest.json     # generated: each external skill + compat tier + reason
├── package.json                    # `bun run build-external-skills` / `update-external-skills`
├── workspace/                      # Packed into the sandbox at /.agents/workspace
│   ├── compositions/               # The three starters (HTML + manifest.json)
│   │   ├── social-promo/
│   │   ├── app-trailer/
│   │   └── explainer/
│   └── scripts/
│       ├── customize.py            # Validate variable values vs the schema
│       └── render_client.py        # Zip + submit to the render API, return the URL
├── probers/probe-render.sh         # Smoke test: prompt → playable URL
├── generate_payload.py             # Build an Interactions API request body
└── LICENSE                         # MIT
```

## Skills

The agent's four core skills (`pick-composition`, `generate-script`,
`customize-composition`, `render-and-return`) are hand-authored and drive the
pipeline. On top of those, it dynamically loads HyperFrames' own authoring
skills (GSAP, Anime.js, CSS, Lottie, Three.js, captions, etc.) from the
`hyperframes` repo, vendored as a pinned git submodule under `external-skills/`.

`scripts/build-external-skills.mjs` walks the submodule's skills, classifies
each for the Gemini sandbox, and symlinks the usable ones into `skills/`:

- **portable** — pure authoring/reference knowledge → symlinked.
- **partial** — assumes the `hyperframes` CLI (absent in the sandbox); the
  knowledge is usable, CLI steps fail informatively → symlinked.
- **incompatible** — needs headless Chrome or is out of scope → excluded.

The tiering + reasons are written to `skills-compat-manifest.json`. A future
`platform-compat: { gemini: ... }` SKILL.md frontmatter field overrides the
heuristic per skill when present.

```bash
git submodule update --init        # fetch the pinned skills
bun run build-external-skills      # classify + symlink + write the manifest
bun run update-external-skills     # bump the submodule to origin/main, then rebuild
```

(`bun run` is the documented entrypoint; the scripts are plain Node, so
`node scripts/build-external-skills.mjs` works too.)

## Rendering

The render step runs `render_client.py` on the staged composition directory. It
zips the directory, submits it to HeyGen's `POST /v3/hyperframes/renders`
endpoint over plain HTTPS (`requests`, pre-installed in the sandbox — no npm
install, no Chrome), polls to completion, and returns a HeyGen-CDN video URL.
Inside the managed-agent sandbox the egress proxy injects the HeyGen `x-api-key`
header automatically, so the script holds no credential.

## Local development

The helpers run anywhere with Python 3.8+ (the sandbox ships 3.11):

```bash
# Validate generated content against a starter's schema
echo '{"headline":"See clearly.","accent_color":"#22aaff"}' > /tmp/proposed.json
python3 workspace/scripts/customize.py \
  workspace/compositions/social-promo /tmp/proposed.json /tmp/variables.json

# Render it (needs a real HeyGen key locally; the sandbox injects one via the proxy)
HEYGEN_API_KEY=... python3 workspace/scripts/render_client.py \
  workspace/compositions/social-promo /tmp/variables.json \
  '{"resolution":"1080p","aspect_ratio":"9:16"}'
```

You can also lint a composition with the `hyperframes` CLI before rendering
(local dev only — the CLI is not used in the sandbox):

```bash
npx hyperframes lint workspace/compositions/social-promo
```

## Status

Preview. Built against HeyGen's `POST /v3/hyperframes/renders` API and the
Gemini Managed Agents preview. The render contract is verified; the exact
Interactions API request/response shape is being confirmed against the live
preview before launch.

## License

MIT. See [LICENSE](./LICENSE).
