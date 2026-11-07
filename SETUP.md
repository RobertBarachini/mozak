# SETUP — bootstrap an instance

Prerequisites: `git`, `python3`. Nothing else, ever — the core is zero-install (AGENTS
`tools/` row). An individual `tools/recipes/` script may ask for more; each declares what
it needs and degrades loudly without it.

## 1. Born by clone (keeps the template attached as upstream)

```bash
git clone <template-repo> <instance-name> && cd <instance-name>
git remote rename origin template
```

Cloning (not copying) means every future `git merge template/main` is a clean
three-way merge — see [SYNC.md](SYNC.md) for the ownership contract and rituals.
Point the instance at its own private remote (or none at all) as `origin`.

Or let the checklist drive — it is the command the README's pasted block names:

```bash
python3 tools/bootstrap.py            # §1–§3 as ✓/✗ items, each with its exact next command; exit 0 iff ready
python3 tools/bootstrap.py --attach   # also perform the origin → template rename on a fresh clone
python3 tools/bootstrap.py --json     # the same as data, for agents
```

It performs only what is safe unattended (the rename needs `--attach` — the template
author's own checkout looks exactly like a fresh clone), asks nothing itself, and prints the
questions your agent must ask you: the acquisition consent of §2 and the personal-context
facts of §3. Re-run it until it prints `ready: yes`.

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

Then `python3 tools/recipes/policy.py check`. On a fresh instance it creates
`.personal-shared/acquisition-policy.toml` as a commented skeleton and exits 2, printing four
decisions as questions with every option explained: how far the agent may climb the ladder, how
fetches present themselves, whether to provide a contact, and — last — your consent. Your agent
asks you these and records each answer with `python3 tools/recipes/policy.py set key=value`
(`set consent.acknowledged=today` is the final one); or answer them yourself with the same
commands, or by editing the file. Until consent is recorded no web acquisition runs, and the
agent never answers for you.

## 3. Make it yours

- Personal context: `bootstrap.py` leaves `.personal-shared/README.md` as an empty skeleton.
  Your agent asks you the facts in it — how to address you, locale, preferences, whether the
  shell it runs in is your own machine — each optional (`—` skips), records what you give, then
  runs `python3 tools/bootstrap.py --personal-context-asked`. Nothing there is ever inferred
  (AGENTS `.personal-shared/` row).
- Make `pages/start-here.md` yours — the birth seed you own outright (SYNC): its front-door
  text and `## Domains` list describe this instance.
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
# See pages/mozak-report-annotation-loop.md; the /drain-report skill is the Claude Code path.
claude mcp add --transport stdio annotate -- python3 tools/annotate.py mcp
```

## 6. Ingestion toolchain (install when a task first needs it)

Usage policy and per-format `raw/` drain recipes live in-graph:
[pages/mozak-ingestion-toolchain.md](pages/mozak-ingestion-toolchain.md); how to *get* bytes off a
host you don't control is [pages/mozak-web-acquisition-ladder.md](pages/mozak-web-acquisition-ladder.md).
Install side:

```bash
# Once per instance: answer the four decisions `check` prints, then record consent (see §2).
python3 tools/recipes/policy.py check
python3 tools/recipes/policy.py set advanced_acquisition=false identity.user_agent=browser  # your answers
python3 tools/recipes/policy.py set consent.acknowledged=today                             # last
# Optional — your logins for research behind your own accounts (rung T5): export a Netscape
# cookies.txt from a PRIVATE WINDOW logged into only the sites you need, never your daily
# profile, to .personal-shared/cookies.txt. Used only when advanced_acquisition = true.

# Fetch a page with provenance — needs nothing installed (rungs T0-T2, stdlib):
python3 tools/recipes/web-fetch.py --probe https://example.com/   # what does this host offer?
python3 tools/recipes/web-fetch.py https://example.com/           # fetch, extract, record
python3 tools/recipes/web-fetch.py --archive https://example.com/ # Wayback, when live is blocked
python3 tools/recipes/web-fetch.py --links https://example.com/   # its references, for the worklist
python3 tools/recipes/scholar-lookup.py 10.1038/nature14539        # papers: registries, not publishers
python3 tools/recipes/web-worklist.py add <url> --why "..."       # then `show`, then `run --yes`
python3 tools/recipes/web-har-harvest.py raw/session.har          # rung T6: a HAR you exported

# uv: the user-level installer most of this block relies on (no sudo, any distribution, rc
# files untouched; not in Ubuntu's apt). User-level first is the tool policy: why, and when
# sudo is the right call instead, is in pages/mozak-ingestion-toolchain.md.
curl -LsSf https://astral.sh/uv/install.sh | sh -s -- --no-modify-path

# Rungs T3/T4:
~/.local/bin/uv run tools/recipes/web-render.py --install         # once: full Chromium, ~115 MB, user-level
~/.local/bin/uv run tools/recipes/web-render.py <url>             # T4: disposable sandboxed browser
~/.local/bin/uv run tools/recipes/web-impersonate.py <url>        # T3: browser TLS handshake
# Both refuse unless advanced_acquisition = true. If Chromium fails to launch on missing system
# libraries, that one step needs sudo: `playwright install-deps chromium`.

# yt-dlp: install it with uv, NOT from your distribution. As of 2026 YouTube needs three pieces:
# a current yt-dlp, a JavaScript runtime, and the yt-dlp-ejs challenge solver. Distribution
# packages lag, most ship no solver, and their Node is often below yt-dlp's minimum; this one
# line brings all three on any distribution (Deno arrives as a Python wheel; the last flag puts
# `deno` on PATH too). Why each piece: pages/mozak-ingestion-toolchain.md, the yt-dlp row.
~/.local/bin/uv tool install --pre "yt-dlp[default,deno]" --with-executables-from deno
~/.local/bin/uv tool upgrade yt-dlp       # YouTube breaks old versions: upgrade before blaming a video
yt-dlp -v 2>&1 | grep -E "JS runtimes|Optional libraries"   # want deno-<version>, and yt_dlp_ejs listed
# Transcript without downloading the video (run LOCALLY — YouTube blocks cloud IPs).
# json3 is YouTube's native timed-text JSON: no rolling duplicates to clean up.
python3 tools/recipes/yt-transcript.py "<url>"   # warns when yt-dlp reports a missing piece
# No captions? yt-dlp the audio, transcribe with Whisper.

# pandoc: user-level too. Distribution packages lag 1-3 years and predate the pptx/xlsx
# readers; the release tarball is one self-contained binary (amd64 shown, arm64 exists).
V=3.13   # latest as of 2026-11: github.com/jgm/pandoc/releases
curl -fsSL "https://github.com/jgm/pandoc/releases/download/$V/pandoc-$V-linux-amd64.tar.gz" \
  | tar -xz -C ~/.local --strip-components=1     # -> ~/.local/bin/pandoc, plus its man pages
```

The policy file is where your judgement lives: `advanced_acquisition` (rungs beyond T2),
`identity.user_agent` (`browser` by default — for anonymity, since the UA does not affect
blocking but a distinctive one is a tracking beacon), an optional `contact` that the general
fetch never sends, and the fetch budget. `python3 tools/recipes/policy.py show --explain`
prints the effective values. The shipped defaults are cautious and anonymous.

Recipes that declare Python packages (`web-render.py`, `web-impersonate.py`) run under
`uv run` — PEP 723 inline metadata, resolved into a throwaway environment on first run, nothing
installed globally; the venv fallback is in [tools/recipes/README.md](tools/recipes/README.md).
The core never needs uv, and `graph.py check` passes on a clone with nothing installed.

### System tools: the one place sudo is right

Codecs and native libraries are what distributions maintain well, so these come from your
package manager. Install only what a task needs. An agent proposes the line for **your**
distribution and waits for you to run it (the tool policy in
[pages/mozak-ingestion-toolchain.md](pages/mozak-ingestion-toolchain.md)); it never holds the
password.

| Tool | Needed for | Debian / Ubuntu | Fedora | Arch |
|---|---|---|---|---|
| `ffmpeg` | audio for Whisper, `ffprobe` | `ffmpeg` | `ffmpeg-free` (full codecs: RPM Fusion's `ffmpeg`) | `ffmpeg` |
| `pdftotext` | a PDF's text layer | `poppler-utils` | `poppler-utils` | `poppler` |
| `tesseract` | OCR of scans | `tesseract-ocr` (+ `tesseract-ocr-<lang>`) | `tesseract` (+ `tesseract-langpack-<lang>`) | `tesseract` + `tesseract-data-<lang>` |

```bash
sudo apt install ffmpeg poppler-utils tesseract-ocr            # Debian / Ubuntu
sudo dnf install ffmpeg-free poppler-utils tesseract           # Fedora
sudo pacman -S ffmpeg poppler tesseract tesseract-data-eng     # Arch
```

Another distribution: look the tool up on [repology.org](https://repology.org), which lists
every distribution's package name and version for it.

## 7. Definition of done (every writing session)

`python3 tools/graph.py check` exits 0 → log the change (a `journals/` entry, or `CHANGELOG.md` for template-system
changes — AGENTS rule 7) → draft commit message →
human commits. Never push without being asked.
