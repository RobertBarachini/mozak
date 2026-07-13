# SETUP — bootstrap an instance

Prerequisites: `git`, `python3` (stdlib only — the core system has zero installs).

## 1. Born by clone (keeps the template attached as upstream)

```bash
git clone <template-repo> <instance-name> && cd <instance-name>
git remote rename origin template
```

Cloning (not copying) means every future `git merge template/main` is a clean
three-way merge — see [SYNC.md](SYNC.md) for the ownership contract and rituals.
Point the instance at its own private remote (or none at all) as `origin`.

## 2. Smoke test

```bash
python3 tools/graph.py check        # expect: broken: 0, duplicate stems: 0 → exit 0
python3 tools/graph.py backlinks start-here   # who links to the front door
```

`check` also materializes the derived index `_generated/links.json` — it is
gitignored, so fresh clones don't ship it; this step creates it.

Optional — enforce the ownership boundary locally: `git config core.hooksPath tools/hooks`
installs the shipped pre-commit hook, which blocks a commit that edits a template-owned
file in this instance (`python3 tools/graph.py ownership`; bypass with `--no-verify`). To
gate in CI too, add a step that sets up the template remote first — `git remote add
template <url> && git fetch template && python3 tools/graph.py ownership --strict` — since
`actions/checkout` doesn't configure it.

## 3. Make it yours

- Rewrite `README.md` to describe the instance (instance-owned per SYNC.md).
- Write the founding `journals/<today>.md` entry; commit (the human commits —
  agents draft messages and stop).
- Good first agent task, end-to-end: "Ingest one YouTube video on <topic>: fetch
  the transcript, capture under sources/ per the source template, distill into
  evergreen pages, link contextually, create the domain MOC, journal, run
  `python3 tools/graph.py check`, draft a commit message."

## 4. Viewers (optional, read-mostly)

- **Obsidian:** open the folder as a vault — wikilinks, backlink pane, graph view
  all native. `.obsidian/` is gitignored (viewer state is not knowledge).
- **Logseq:** add as graph. Degraded: `sources/` not indexed, flat paragraphs render
  as single blocks; set `:journal/file-name-format "yyyy-MM-dd"`. **Caution:**
  Logseq rewrites files it edits (bullets, `::` properties) — view, don't author.
  `/logseq/` is gitignored.

## 5. MCP servers (optional — agents work on files directly and don't need these)

Re-verify each repo README first; this landscape shifted during 2025–2026.

```bash
# Obsidian (Local REST API plugin ships a built-in MCP server):
claude mcp add --transport http obsidian https://127.0.0.1:27124/mcp/ \
  --header "Authorization: Bearer <api-key-from-plugin-settings>"
# Self-signed cert: trust it, or use the plaintext http://127.0.0.1:27123 endpoint.

# Logseq (ergut/mcp-logseq): enable Settings → Features → HTTP APIs server,
# generate a token, then follow that repo's README.

# Report annotations (this repo's own tools/annotate.py — a read-only stdio server
# exposing the latest render's annotation queue to any MCP harness). Optional: the
# annotations.md file is the source of truth, so an agent can drain it without this.
# See pages/report-annotation-loop.md; the /drain-report skill is the Claude Code path.
claude mcp add --transport stdio annotate -- python3 tools/annotate.py mcp
```

## 6. Ingestion toolchain (install when a task first needs it)

Usage policy and per-format `raw/` drain recipes live in-graph:
[pages/ingestion-toolchain.md](pages/ingestion-toolchain.md). Install side:

```bash
# Transcript without downloading the video (run LOCALLY — YouTube blocks cloud IPs):
yt-dlp --skip-download --write-auto-subs --sub-format vtt \
  -o "raw/%(upload_date)s-%(id)s" "<url>"
# VTT keeps timestamps + duplicated auto-caption lines — clean during capture.
# No captions? yt-dlp the audio, transcribe with Whisper.
# Optional: danielmiessler/fabric for ready-made extract_wisdom/summarize patterns.
```

## 7. Definition of done (every writing session)

`python3 tools/graph.py check` exits 0 → log the change (a `journals/` entry, or `CHANGELOG.md` for template-system
changes — AGENTS rule 7) → draft commit message →
human commits. Never push without being asked.
