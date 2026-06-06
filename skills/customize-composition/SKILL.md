---
name: customize-composition
description: Validate the generated content against the composition's real variable schema and stage it for rendering. Use after generate-script and before render-and-return.
---

# Customize the composition

Turn the content you wrote into a validated, render-ready bundle. This step
catches mistakes (wrong color format, a value that doesn't match a declared
variable) locally, so the render API never sees a bad payload.

You don't edit the composition's HTML. HyperFrames injects your variable values
at render time — the composition reads them with
`window.__hyperframes.getVariables()`. So "customizing" means producing a clean
`variables.json` and staging the composition directory.

## Steps

1. Make sure your generated content is at `/.agents/workspace/output/proposed.json`
   (from generate-script).
2. Validate it against the chosen composition and write the clean variables:

   ```bash
   python3 /.agents/workspace/scripts/customize.py \
     /.agents/workspace/compositions/<chosen-id> \
     /.agents/workspace/output/proposed.json \
     /.agents/workspace/output/variables.json
   ```

   - On success it writes `/.agents/workspace/output/variables.json` (your values plus
     declared defaults for anything you left out) and exits 0.
   - On failure it exits non-zero and prints exactly what's wrong (unknown
     variable, wrong type, a color that isn't a hex value, a number out of
     range). **Read the message, fix `proposed.json`, and run it again.** Do not
     skip ahead to rendering with an invalid file.
3. Copy the chosen composition into the output area so the render step has a
   self-contained directory:

   ```bash
   rm -rf /.agents/workspace/output/composition
   cp -r /.agents/workspace/compositions/<chosen-id> /.agents/workspace/output/composition
   ```

## Multi-turn edits

On a follow-up ("make the headline punchier", "switch to a dark background"),
you don't need to start over:

- Edit only the changed keys in `/.agents/workspace/output/proposed.json`.
- Re-run `customize.py` to re-validate and rewrite `variables.json`.
- Keep the same staged composition unless the user wants a different starter.

## Output of this step

- `/.agents/workspace/output/variables.json` — validated values.
- `/.agents/workspace/output/composition/` — the staged composition directory.

Then move to **render-and-return**.
