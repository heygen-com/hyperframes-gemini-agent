---
name: generate-script
description: Decide the actual content (headline copy, feature lines, colors, etc.) for the chosen composition's variables. Use after pick-composition and before customize-composition.
---

# Generate the content

You've chosen a starter. Now decide what goes into it. Every starter declares a
set of **variables** — the text and colors a user can change. Your job is to
produce a value for each one based on the user's prompt.

## Steps

1. Open the chosen composition's `manifest.json`. The `variables` array lists
   every variable: its `id`, `type`, `label`, and `default`. (The authoritative
   declaration also lives in `index.html`'s `data-composition-variables`, but
   the manifest mirror is easier to read.)
2. For each variable, write a value that reflects the user's prompt:
   - **string** variables (headlines, taglines, feature lines, CTAs): write
     real copy. Keep it tight — respect any `maxLength`. These render as
     on-screen text, so punchy beats wordy. A headline is a few words, not a
     sentence.
   - **color** variables: choose hex colors (`#rrggbb`) that match the mood the
     user described. If they said "calm pastel", pick soft, low-saturation
     tones. If they said "bold" or "dark", go high-contrast. Make sure text
     color reads clearly against the background color.
   - **enum** variables: pick one of the declared `options` values.
   - **number** / **boolean**: stay within any declared `min`/`max`.
3. If the user didn't give you something for a particular variable, make a
   sensible choice that fits the overall brief rather than leaving the default
   — the default is generic placeholder content.

## Writing good on-screen copy

- Lead with the benefit, not the feature name.
- One idea per line. The feature lines in `app-trailer` and the steps in
  `explainer` each get a single short phrase.
- Match the user's tone. A playful app and an enterprise tool should not sound
  the same.
- Don't invent claims the user didn't make (no fake stats, no "#1" superlatives
  unless they asked).

## Output of this step

A plain JSON object mapping each variable `id` to your chosen value, e.g.:

```json
{
  "app_name": "Strand",
  "tagline": "Notes that think with you.",
  "feature_1": "Capture ideas in a tap",
  "accent_color": "#7c9cff"
}
```

Write this to `/.agents/workspace/output/proposed.json`. Then move to
**customize-composition**, which validates it against the composition's real
schema before rendering.
