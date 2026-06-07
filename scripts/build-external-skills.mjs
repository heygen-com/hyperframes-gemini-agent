#!/usr/bin/env node
/**
 * Build the agent's skill set from the pinned `hyperframes` submodule.
 *
 * Walks `external-skills/hyperframes/skills/`, classifies each skill's
 * portability to the Gemini managed-agent sandbox, symlinks the usable ones
 * (portable + partial) into `skills/<name>/`, and writes
 * `skills-compat-manifest.json`. The four hand-authored core skills
 * (pick-composition, generate-script, customize-composition, render-and-return)
 * are real directories and are never touched.
 *
 *   node scripts/build-external-skills.mjs            # rebuild from current submodule SHA
 *   node scripts/build-external-skills.mjs --update   # bump submodule to origin/main first
 *
 * (Runs under `bun run` too — see package.json. Plain Node so it's testable
 * without bun installed.)
 *
 * Classification (v1 heuristics — superseded per-skill by a future
 * `platform-compat: { gemini: portable|partial|incompatible }` frontmatter
 * field, which wins when present):
 *   incompatible — explicit override (Chrome / out-of-scope) OR Claude-platform
 *                  tooling in the body (mcp__, $ARGUMENTS, CronCreate). Excluded.
 *   partial      — CLI-centric: assumes `npx hyperframes` (not in the sandbox).
 *                  Knowledge is usable; CLI steps fail with informative errors.
 *   portable     — pure authoring/reference knowledge, no Claude/CLI core dep.
 */

import { execFileSync } from "node:child_process";
import { existsSync, lstatSync, mkdirSync, readdirSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SUBMODULE = join(REPO_ROOT, "external-skills", "hyperframes");
const SRC_SKILLS = join(SUBMODULE, "skills");
const DEST_SKILLS = join(REPO_ROOT, "skills");
const MANIFEST = join(REPO_ROOT, "skills-compat-manifest.json");

// Hand-authored skills that drive the agent pipeline — real dirs, never managed here.
const CORE_SKILLS = new Set(["pick-composition", "generate-script", "generate-voiceover", "customize-composition", "render-and-return"]);

// Known-incompatible skills the heuristics can't infer from signals alone.
const INCOMPATIBLE_OVERRIDES = {
  "website-to-hyperframes":
    "requires headless Chrome for site capture; needs a HeyGen cloud-side capture endpoint to be portable",
  "contribute-catalog":
    "upstream-PR / catalog-contribution workflow (needs repo write access); not video authoring — out of scope for the agent",
};

// Body tokens that mean the skill drives Claude-only harness features.
const CLAUDE_PLATFORM_RE = /(\bmcp__|\$ARGUMENTS\b|\bCronCreate\b|\bCronList\b)/;
// HyperFrames CLI invocations. High density ⇒ the skill's subject IS the CLI.
const CLI_RE = /(npx hyperframes\b|hyperframes (init|lint|inspect|preview|render|add|cloud|transcribe|tts|doctor|browser|info|upgrade|compositions|docs|benchmark)\b)/g;
const CLI_PARTIAL_THRESHOLD = 10;
const CLI_CENTRIC_NAME_RE = /^hyperframes-(cli|media|registry)$/;

function git(args) {
  return execFileSync("git", args, { cwd: REPO_ROOT, encoding: "utf8" }).trim();
}

function readSkillMd(name) {
  const p = join(SRC_SKILLS, name, "SKILL.md");
  return existsSync(p) ? readFileSync(p, "utf8") : null;
}

/** Pull the YAML frontmatter block (between the first pair of `---`). */
function frontmatter(md) {
  const m = md.match(/^---\n([\s\S]*?)\n---/);
  return m ? m[1] : "";
}

/** Authoritative compat field if a maintainer has set it. */
function declaredCompat(fm) {
  // platform-compat:\n  gemini: <tier>
  const block = fm.match(/platform-compat:\s*\n([\s\S]*?)(?:\n\S|$)/);
  const scope = block ? block[1] : fm;
  const m = scope.match(/\bgemini:\s*(portable|partial|incompatible)\b/);
  return m ? m[1] : null;
}

function classify(name, md) {
  const fm = frontmatter(md);
  const declared = declaredCompat(fm);
  if (declared) return { tier: declared, reason: `declared via platform-compat.gemini: ${declared}` };

  if (INCOMPATIBLE_OVERRIDES[name]) return { tier: "incompatible", reason: INCOMPATIBLE_OVERRIDES[name] };

  const body = md.slice(fm.length);
  if (CLAUDE_PLATFORM_RE.test(body)) {
    return { tier: "incompatible", reason: "references Claude-only harness tooling (mcp__ / $ARGUMENTS / Cron) absent in the Gemini sandbox" };
  }

  const cliHits = (body.match(CLI_RE) || []).length;
  if (cliHits >= CLI_PARTIAL_THRESHOLD || CLI_CENTRIC_NAME_RE.test(name)) {
    return { tier: "partial", reason: `CLI-centric (${cliHits} \`hyperframes\` CLI references); knowledge usable but CLI steps fail — the sandbox renders via render_client.py, not the CLI` };
  }
  return { tier: "portable", reason: "pure authoring/reference knowledge; no Claude-platform or CLI core dependency" };
}

function clearStaleSymlinks() {
  if (!existsSync(DEST_SKILLS)) {
    mkdirSync(DEST_SKILLS, { recursive: true });
    return;
  }
  for (const entry of readdirSync(DEST_SKILLS)) {
    if (CORE_SKILLS.has(entry)) continue; // never touch core (also: core are dirs, not symlinks)
    const p = join(DEST_SKILLS, entry);
    if (lstatSync(p).isSymbolicLink()) rmSync(p);
  }
}

function main() {
  const update = process.argv.includes("--update");
  if (update) {
    console.log("→ Updating submodule to origin/main…");
    git(["-C", SUBMODULE, "fetch", "origin", "main", "--quiet"]);
    git(["-C", SUBMODULE, "checkout", "--quiet", "origin/main"]);
    git(["-C", SUBMODULE, "sparse-checkout", "set", "skills"]); // keep the working tree lean
  }

  if (!existsSync(SRC_SKILLS)) {
    console.error(`Submodule skills not found at ${SRC_SKILLS}. Run: git submodule update --init`);
    process.exit(1);
  }

  const sha = git(["-C", SUBMODULE, "rev-parse", "HEAD"]);
  const names = readdirSync(SRC_SKILLS, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .sort();

  clearStaleSymlinks();

  const skills = [];
  for (const name of names) {
    const md = readSkillMd(name);
    if (md === null) {
      skills.push({ name, tier: "incompatible", reason: "no SKILL.md", symlinked: false });
      continue;
    }
    const { tier, reason } = classify(name, md);
    let symlinked = false;
    if (tier !== "incompatible") {
      if (CORE_SKILLS.has(name)) {
        // A submodule skill colliding with a core skill name: never overwrite core.
        skills.push({ name, tier, reason: `${reason} (NOT linked — name collides with a core skill)`, symlinked: false });
        continue;
      }
      const linkPath = join(DEST_SKILLS, name);
      const target = join("..", "external-skills", "hyperframes", "skills", name); // relative to skills/
      if (existsSync(linkPath)) rmSync(linkPath, { recursive: true, force: true });
      symlinkSync(target, linkPath);
      symlinked = true;
    }
    skills.push({ name, tier, reason, symlinked });
  }

  const counts = skills.reduce((a, s) => ((a[s.tier] = (a[s.tier] || 0) + 1), a), {});
  const manifest = {
    generated_by: "scripts/build-external-skills.mjs",
    generated_at: new Date().toISOString(),
    submodule: { url: git(["config", "--file", ".gitmodules", "submodule.external-skills/hyperframes.url"]), sha },
    classification_note:
      "v1 heuristics (override list + CLI-reference density + Claude-tooling scan). A `platform-compat: { gemini: ... }` frontmatter field, when present, overrides the heuristic. portable+partial are symlinked into skills/; incompatible are excluded.",
    summary: { total: skills.length, ...counts, symlinked: skills.filter((s) => s.symlinked).length },
    skills,
  };
  writeFileSync(MANIFEST, JSON.stringify(manifest, null, 2) + "\n");

  console.log(`✓ ${skills.length} external skills classified @ ${sha.slice(0, 10)}`);
  console.log(`  portable: ${counts.portable || 0}  partial: ${counts.partial || 0}  incompatible: ${counts.incompatible || 0}`);
  console.log(`  symlinked into skills/: ${manifest.summary.symlinked}`);
  console.log(`  manifest: ${relative(REPO_ROOT, MANIFEST)}`);
}

main();
