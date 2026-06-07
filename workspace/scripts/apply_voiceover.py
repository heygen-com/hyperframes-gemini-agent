#!/usr/bin/env python3
"""Inject the synthesized voiceover URL into a staged composition's <audio> src.

The HeyGen renderer reads the `<audio>` `src` as a static HTML attribute at
parse time — a src set later from JS / getVariables() is NOT picked up. So the
voiceover URL can't be a runtime composition variable; it has to be baked into
the HTML before the composition is zipped. Starters ship with a placeholder
`src="__VOICEOVER_URL__"`; this replaces it with the real URL (or strips the
`<audio>` element entirely when there's no narration).

Usage:
    python3 apply_voiceover.py <staged_composition_dir> "<voiceover_url>"

Pass an empty string for no narration (the silent case) — the voiceover
`<audio>` element is removed so the render doesn't try to load the placeholder.
"""

from __future__ import annotations

import os
import re
import sys

PLACEHOLDER = "__VOICEOVER_URL__"
# The voiceover audio element (single line in the starters), matched by its id.
_AUDIO_RE = re.compile(r"[ \t]*<audio\b[^>]*\bid=\"voiceover\"[^>]*>\s*</audio>\s*\n?", re.IGNORECASE)


def apply(comp_dir: str, voiceover_url: str) -> str:
    index = os.path.join(comp_dir, "index.html")
    if not os.path.isfile(index):
        raise SystemExit(f"No index.html in {comp_dir}")
    html = open(index, encoding="utf-8").read()

    url = (voiceover_url or "").strip()
    if url:
        if PLACEHOLDER not in html:
            raise SystemExit(
                f"{index} has no {PLACEHOLDER} placeholder — the starter is missing its "
                "voiceover <audio> slot."
            )
        html = html.replace(PLACEHOLDER, url)
        action = f"injected voiceover URL ({url[:48]}…)"
    else:
        # No narration: remove the voiceover <audio> element so the renderer
        # doesn't try to fetch the literal placeholder.
        html, n = _AUDIO_RE.subn("", html)
        action = "removed voiceover <audio> (no narration)" if n else "no voiceover element to remove"

    open(index, "w", encoding="utf-8").write(html)
    return action


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    comp_dir = argv[1]
    url = argv[2] if len(argv) > 2 else ""
    print(apply(comp_dir, url))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
