---
name: generate-voiceover
description: Synthesize a spoken voiceover for the video from the narration script via HeyGen TTS. Use after generate-script and before customize-composition. Runs by default for every video unless the user asked for no narration.
---

# Generate the voiceover

Every video gets a spoken voiceover **by default** — it's the single biggest
lift in perceived quality. You turn the narration script into audio with
HeyGen's text-to-speech, then hand the audio URL to the composition.

**Skip this step only if** the user's prompt explicitly asks for no narration —
"no voiceover", "silent", "ambient only", "music only", "text only". When you
skip, leave `voiceover_url` empty and tell the user the video is silent.

## Inputs

- The **narration script** from generate-script (a short spoken line or two,
  sized to the starter's duration — distinct from the on-screen copy).
- The chosen composition's `manifest.json`, which carries a
  `recommended_voice_id` (the default voice for that starter).

## Steps

1. **Pick a voice.** Use the starter's `recommended_voice_id` unless the user's
   prompt gives tone direction — then override from the catalog below.
2. **Synthesize** with the TTS helper:

   ```bash
   set +x
   RESULT=$(python3 /.agents/workspace/scripts/tts_client.py \
     "<narration script>" "<voice_id>")
   AUDIO_URL=$(echo "$RESULT" | jq -r '.audio_url')
   DURATION=$(echo "$RESULT" | jq -r '.duration')
   ```

   `tts_client.py` calls `POST /v3/voices/speech` and prints
   `{audio_url, duration, voice_id, word_timestamps}`. The sandbox proxy injects
   the HeyGen key — you pass no credential. (Dev test: prefix with
   `HEYGEN_API_URL=https://api.dev.heygen.com`.)
3. **Check the duration against the starter.** Compare `DURATION` to the
   starter's `duration_seconds` (from its manifest). The audio must fit:
   - `DURATION` ≤ starter duration → good, use it.
   - `DURATION` > starter duration → **do not truncate.** Trim the narration
     script (fewer words / shorter sentences) and re-synthesize until it fits,
     with ~0.3s of headroom. A tight, punchy line beats a rushed or cut-off one.
4. **Save the audio URL** for customize-composition:

   ```bash
   echo -n "$AUDIO_URL" > /.agents/workspace/output/voiceover_url.txt
   ```

   (If you skipped narration, write an empty file or skip this — customize will
   strip the audio element.)

## Voice catalog (starfish engine)

Pick by tone. Tones are a starting point — the per-starter `recommended_voice_id`
is the default; override only on explicit prompt direction.

| Voice | `voice_id` | Tone — use for |
|---|---|---|
| Luna Bright (f) | `2b0124724e144eedba61ecb590d6c266` | Bright, friendly — consumer apps, social promos |
| Smooth Dev (m) | `07d2ba65847541feb97abc9b60181555` | Smooth, confident — product trailers, narration |
| Marcus – Professional (m) | `0f50a7a5577e4cd583ba738094956899` | Warm, clear, professional — explainers, how-it-works, B2B |
| Peaceful Paige (f) | `035ec8f52ec247cdbed5f3bf9f7991ef` | Calm, soft, soothing — wellness, meditation, premium calm |
| Energetic Mikey (m) | `25a40947b46942c1a8e5bd329074bba2` | Upbeat, punchy, high-energy — launches, hype, social |

Override cues: "calm / relaxing / meditative / soothing" → Peaceful Paige ·
"energetic / exciting / hype / launch / punchy" → Energetic Mikey · "friendly /
fun / approachable" → Luna Bright · "professional / corporate / clear" →
Marcus · "smooth / cinematic / confident" → Smooth Dev.

(These are public starfish-engine voices; if a `voice_id` ever fails, list
current options with `GET /v3/voices?engine=starfish`.)

## Output of this step

- `/.agents/workspace/output/voiceover_url.txt` — the synthesized audio URL.

The renderer reads the `<audio>` `src` as a static HTML attribute, so this URL
isn't a runtime variable — customize-composition bakes it into the staged
composition's HTML (via `apply_voiceover.py`). Then move to
**customize-composition**.
