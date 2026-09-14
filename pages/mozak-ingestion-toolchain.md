---
title: Ingestion toolchain — tool policy and raw/ drain recipes
aliases: [ingestion-toolchain]
type: note
domain: [meta]
tags: [workflow, tooling]
created: 2026-07-07
updated: 2026-09-09
status: growing
---

# Ingestion toolchain — tool policy and raw/ drain recipes

Operational knowledge for the gather/capture steps of [[mozak-research-flow]]: what to
reach for when draining `raw/`, and how to behave when a tool is missing. Agents
already know these tools — this note encodes the house policy and the nudge, so
sessions behave consistently instead of each rediscovering an approach.

## Tool policy (MUST)

1. **Probe before use** — `command -v <tool>` (or `<tool> --version`). Never assume. A probe
   describes the shell the session runs in, which may not be the user's machine — environment
   facts come from `.personal-shared/` (its AGENTS layout row), not from probing.
2. **Missing tool: degrade loudly, never silently.** If installing is within the
   session's granted privileges, offer it with the exact command (`sudo apt install
   ffmpeg`, `uv tool install yt-dlp`, …). If not, tell the human what is missing
   and what it was needed for, and take a degraded path only if one exists —
   stating so in the capture and journal. Never fake or skip a result quietly.
3. **Run fetches locally** — YouTube and friends block cloud/datacenter IPs.
4. **Never modify raw originals in place** — conversions produce new files; the
   raw item is removed only after its capture is complete (per [[mozak-research-flow]]).
5. **Fetch politely, escalate deliberately.** Getting bytes off a host you don't control
   is its own discipline with its own budget — start at the cheapest rung, escalate only
   on a recorded failure, treat the host's answers as answers, and record which rung produced
   the capture.
   The rungs, the budget and the legal line live in [[mozak-web-acquisition-ladder]]; this page
   picks up once a file exists.

## Roster — when to reach for what

| Tool | Use for |
|---|---|
| `yt-dlp` | Transcripts without the video (`--skip-download --write-subs --write-auto-subs --sub-format json3`; **prefer `json3` — YouTube's native timed-text JSON has none of VTT's rolling duplicates**); audio for Whisper (`-x --audio-format wav`); metadata (`--dump-json`). **Needs a JavaScript runtime for full YouTube support as of 2026** — without one it degrades silently, so probe for `deno`/`node` and say so ([[2026-09-09-web-acquisition-research]]). `yt-transcript.py` passes `.personal-shared/cookies.txt` through when present and `advanced_acquisition` is set — for age-restricted or members-only content; public captions need no cookies, and a daily-profile export risks the Google account |
| `ffmpeg` / `ffprobe` | Inspect (`ffprobe -v error -show_format -show_streams`) and convert media — e.g. downmix to 16 kHz mono WAV before Whisper |
| `whisper` | ASR when no captions exist (feed it ffmpeg-prepared audio) |
| `pdftotext` (poppler) | PDF → text (`-layout` preserves columns); scanned PDFs need OCR (`tesseract`) instead |
| `pandoc` | docx / epub / html → clean Markdown for captures. Use `-t gfm --wrap=none --extract-media=assets/<slug>`: the default hard-wrap turns every later one-word edit into a whole-paragraph diff, and plain `-t markdown` emits fenced-div syntax that renders as literal noise in Obsidian. **Distro packages lag 1–3 years — install the release `.deb`** |
| `file`, `iconv` | Identify unknown raw items; fix text encodings (Windows-125x exports and similar) |
| `jq`, `unzip` / `tar` | Explore JSON dumps; unpack archives (then recurse the drain over the contents) |
| `curl` / `wget` | One-off fetches and probing. For anything that should leave provenance, prefer the recipe below |
| `tools/recipes/web-fetch.py` | URL → extracted markdown + a provenance record, recording robots and honouring the fetch budget; `--probe` reports a host's official access paths instead of fetching. Rungs T0–T2, stdlib, no installs ([[mozak-web-acquisition-ladder]]) |
| `tools/recipes/scholar-lookup.py` | DOI / arXiv id / title → capture-ready frontmatter + the open-access copy, from Crossref, OpenAlex, arXiv (and Unpaywall if you set a contact). Rung T0 for papers: registries, never the publisher's page |
| `tools/recipes/web-worklist.py` | Multi-page work without a crawler: `add <url> --why`, `show`, `run --yes` — the agent's chosen references become targeted pulls, capped by the budget, each row carrying its reason |
| `tools/recipes/web-har-harvest.py` | A HAR you exported (`raw/`) → document responses into the store, credentials discarded by construction. Rung T6; consent only |
| `tools/recipes/web-impersonate.py` | `uv run`; rung T3 — a browser's TLS handshake for a fingerprinting WAF. `advanced_acquisition` only |
| `tools/recipes/web-render.py` | `uv run`; rung T4/T5 — a disposable, repo-scoped Chromium: fresh profile per run, seeded only from your cookie jar, third parties blocked, redacted HAR. `--install` once. `advanced_acquisition` only |
| `tools/recipes/policy.py` | Prints the effective acquisition policy (shipped defaults + `.personal-shared/` overrides) and the provenance string stamped into every fetch |

## Executable recipes (`tools/recipes/`)

Known-good typed transformations ("input A of type Y → output B of type X") live
as runnable scripts with contract headers — catalog via
`grep -rA4 "^# recipe:" tools/recipes/`. **Check there before hand-rolling; on the
second hand-roll of the same transformation, promote it to a recipe** (rule of
two) and upstream it so every instance pulls it. Instance-private ones go in
`tools/recipes/local/`. Seed recipe: `yt-transcript.py` (YouTube URL or existing
`--vtt` file → clean deduplicated transcript text — encapsulates the VTT
rolling-duplicate cleanup below).

## raw/ drain recipes

- **Unknown item** → `file <item>` first, then the matching recipe below.
- **Video/audio** → if it has a source URL, prefer yt-dlp captions; else ffmpeg →
  WAV → whisper. De-duplicate VTT auto-caption line repeats before capturing.
- **PDF** → `pdftotext -layout`; scans → tesseract. Text goes into the `sources/`
  capture; keep the PDF itself in `assets/` only if its fidelity matters.
- **A live URL** → don't hand-roll it: `python3 tools/recipes/web-fetch.py <url>` (rung
  T0–T2 — checks official access paths first, records robots, caches, records provenance).
  Escalate rungs only per [[mozak-web-acquisition-ladder]].
- **Saved HTML / office docs** → pandoc to Markdown with the flags in the roster; strip
  navigation boilerplate. A saved page keeps its own chrome, so extraction still applies.
- **Archives** → unpack inside `raw/`, recurse per extracted item.
- **Images / screenshots** → move to `assets/`; describe the content in the
  capture (agents can read images directly while capturing).
- **Structured data (JSON/CSV/db)** → summarize the shape (`jq`, `head`), capture
  the relevant extract rather than the whole dump; the original goes to `assets/`
  only when full fidelity matters.

## Sources

- [[2026-07-06-founding-research]] — verified the yt-dlp subtitle behaviors, the
  Whisper fallback pattern, and the cloud-IP blocking behind the run-locally
  rule. Recipes and the missing-tool policy come from operational practice.
- [[2026-09-09-web-acquisition-research]] — the `json3` subtitle finding, the 2026
  JavaScript-runtime requirement in `yt-dlp`, the pandoc flag set, and the two gaps this
  page's roster had drifted into (a named tool that was not installed, and a silent
  degradation nobody had probed for).
