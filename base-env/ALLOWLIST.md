# Base-env network allowlist (local-render mode)

The spike used a wildcard `"*"` egress allowlist. That's an exfiltration vector
and a yellow flag for Google's gallery review, so local mode ships a **closed
allowlist**. This list is **derived by static analysis of the setup scripts +
the render paths** (each host below maps to a specific line). The hosts marked
⚠️ still need a fresh end-to-end run to confirm exact names (blocked on Gemini
quota at time of writing — see SPIKE_FINDINGS.md).

| Host | Why | Source |
|---|---|---|
| `dl.google.com` | Chrome `.deb` | setup_1 `wget` |
| ⚠️ `archive.ubuntu.com`, `security.ubuntu.com` | Chrome's apt deps (`apt-get download`) | setup_1 — exact mirror depends on the sandbox's `sources.list`; confirm at runtime |
| `googlechromelabs.github.io` | `LATEST_RELEASE_STABLE` lookup | setup_2 `curl` |
| `storage.googleapis.com` | chrome-headless-shell zip (`chrome-for-testing-public/*`) **and** the GCS upload bucket (if `GCS_BUCKET` set) | setup_2 `curl`, render_local GCS |
| `registry.npmjs.org` | hyperframes CLI + its tarball deps | setup_2 `npm install` |
| ⚠️ `github.com`, `objects.githubusercontent.com` | onnxruntime-node native binary (release asset) | setup_2 onnxruntime postinstall — confirm whether it's needed (the CLI works without onnxruntime for our skills) |
| `cdn.jsdelivr.net` | GSAP cache (free-authored comps) | setup_3 `curl` — or self-host GSAP to drop this |
| ⚠️ `pypi.org`, `files.pythonhosted.org` | `google-cloud-storage` pip (only if GCS upload is used) | setup_3 `pip install` |
| `api.heygen.com` | cloud render + TTS | render_client.py, tts_client.py |

Notes:
- **Skills are mounted** (inline sources), not `skills add`-installed, so this
  template does NOT need GitHub for skills (unlike Thor's reference, which does).
  The only GitHub need is onnxruntime's binary — and that's used by skills we
  don't exercise, so dropping it (and onnxruntime entirely) may let us remove
  `github.com`/`objects.githubusercontent.com` from the list. Confirm in the
  verify run.
- `generativelanguage.googleapis.com` (the Gemini Interactions API) is the
  platform's own control plane, not sandbox egress — not in this list.
- The egress proxy IP (`10.100.x.1:8081`) varies per sandbox and is the
  transport, not an allowlist entry.

## Verify step (do when Gemini quota is available)

Run a fresh base-env setup with this closed allowlist (snapshot.py uses it) and
confirm every step still succeeds. If a step fails on a blocked host, add that
host here with its purpose. To enumerate definitively, run
`ss -tnp` / parse the mitmproxy access log during setup and diff against this
list. Narrowing further (e.g. path-scoping `storage.googleapis.com` to
`chrome-for-testing-public/*` + the bucket) is a follow-up if the platform
supports path-level rules.
