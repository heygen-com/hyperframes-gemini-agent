# Render-mode routing — decision table

The agent classifies each prompt (explicit yes/no, *not* keyword matching — see
render-and-return/SKILL.md) then routes: user-override → free-composition →
env-capability → default cloud. Below: the adversarial test set with the
*expected* route + reasoning. ⚠️ "Expected" — runtime verification is pending
Gemini quota; this table is the spec the agent should satisfy and the regression
matrix to run once quota is available.

| # | Prompt | Free-comp? | Env | Expected route | Why |
|---|---|---|---|---|---|
| 1 | "social promo for a coffee app, dark theme" | no | local | **cloud** | plain starter fill — default cloud even in a local-capable env (fast/cheap) |
| 2 | "make a *kinetic-text* social promo for an app called X" | **no** | local | **cloud** | looks authoring-heavy, but the social-promo starter already does kinetic text — no free-auth needed (the trap James called out) |
| 3 | "30s walkthrough of how the React useState hook works, with code samples *animating in*" | **yes** | local | **local** | needs custom code-block animation no starter expresses → free-auth → local |
| 4 | "...$prompt... *render this with cloud mode*" | (any) | local | **cloud** | explicit user override wins over everything |
| 5 | "...$prompt... *render locally*" | (any) | local | **local** | explicit user override (env supports it) |
| 6 | "animated logo reveal for Voxel: pixel-art, neon, arcade vibes" | **yes** | local | **local** | pure free-composition — bespoke animation, no starter fits |
| 7 | "30s React useState walkthrough with animated code" | **yes** | **lite** (no Chrome) | **cloud + degradation warning** | free-auth needed but env can't render it locally → cloud, warn it may not render exactly right |
| 8 | "social promo for a coffee app" | no | **lite** | **cloud** | starter + no local capability → cloud (the default, unaffected) |

Key cases this guards against:
- #2 false-positive: authoring-*sounding* words that a starter already covers → must NOT route local (would pay 10× for nothing).
- #3/#7 false-negative: simple-*sounding* prompt that genuinely needs custom HTML → must route local (or cloud-with-warning in a lite env).
- #4/#5: explicit override always wins.

Verification: run prompts 1–8 against a local-capable base-env (and 7–8 against a
lite env) and record the actual route + the agent's one-line classification
reasoning; diff against "Expected". Add any miss as a tuning note in
render-and-return/SKILL.md.
