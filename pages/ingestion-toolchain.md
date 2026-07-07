---
title: Ingestion toolchain — tool policy and raw/ drain recipes
type: note
domain: [meta]
tags: [workflow, tooling]
created: 2026-07-07
updated: 2026-07-07
status: growing
---

# Ingestion toolchain — tool policy and raw/ drain recipes

Operational knowledge for the gather/capture steps of [[research-flow]]: what to
reach for when draining `raw/`, and how to behave when a tool is missing. Agents
already know these tools — this note encodes the house policy and the nudge, so
sessions behave consistently instead of each rediscovering an approach.

## Tool policy (MUST)

1. **Probe before use** — `command -v <tool>` (or `<tool> --version`). Never assume.
2. **Missing tool: degrade loudly, never silently.** If installing is within the
   session's granted privileges, offer it with the exact command (`sudo apt install
   ffmpeg`, `uv tool install yt-dlp`, …). If not, tell the human what is missing
   and what it was needed for, and take a degraded path only if one exists —
   stating so in the capture and journal. Never fake or skip a result quietly.
3. **Run fetches locally** — YouTube and friends block cloud/datacenter IPs.
4. **Never modify raw originals in place** — conversions produce new files; the
   raw item is removed only after its capture is complete (per [[research-flow]]).

## Roster — when to reach for what

| Tool | Use for |
|---|---|
| `yt-dlp` | Transcripts without the video (`--skip-download --write-auto-subs --sub-format vtt`); audio for Whisper (`-x --audio-format wav`); metadata (`--dump-json`) |
| `ffmpeg` / `ffprobe` | Inspect (`ffprobe -v error -show_format -show_streams`) and convert media — e.g. downmix to 16 kHz mono WAV before Whisper |
| `whisper` | ASR when no captions exist (feed it ffmpeg-prepared audio) |
| `pdftotext` (poppler) | PDF → text (`-layout` preserves columns); scanned PDFs need OCR (`tesseract`) instead |
| `pandoc` | docx / epub / html → clean Markdown for captures |
| `file`, `iconv` | Identify unknown raw items; fix text encodings (Windows-125x exports and similar) |
| `jq`, `unzip` / `tar` | Explore JSON dumps; unpack archives (then recurse the drain over the contents) |
| `curl` / `wget` | Plain fetches when a full browser fetch is unnecessary |

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
- **HTML / office docs** → pandoc to Markdown; strip navigation boilerplate.
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
