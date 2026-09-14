# Knowledge repo — constitution

Agent-agnostic operating rules (per the [agents.md](https://agents.md) standard;
Claude Code loads this via `CLAUDE.md`). **Plain Markdown in this repo is the single
source of truth.** Every app — Claude Code, other agents, Obsidian, Logseq, grep — is
a replaceable lens. Nothing here may depend on any app to stay meaningful.

The core value is **connectedness**: forward links are written in note bodies as
`[[wikilinks]]`; backlinks are **derived, never stored** — via `tools/graph.py`
(materializes `_generated/links.json`) or plain `grep -rF '[[stem' pages/ journals/ sources/`. Preserving
back-linking therefore reduces to two invariants: links stay greppable, names stay
stable.

## Layout

Each row is a path's contract. Three independent axes run through the table — **sync
ownership** (can upstream overwrite it? — [SYNC.md](SYNC.md)), **agent access** (no-read
`.private/` · read-only · read-write), and **durability** (source-of-truth vs.
disposable). They compose: `_generated/presentations/`, for instance, is
agent-generated, disposable, and — being gitignored — instance-local, so it stays
user-visible yet is never shipped or overwritten by upstream (SYNC).

| Path | Role |
|---|---|
| `pages/` | Atomic evergreen notes — THE graph. Flat, no subfolders. One namespace, split ownership (SYNC): template-shipped meta pages are template-owned — instances annotate them by linking from their own notes, never by editing bodies; `start-here` and every other page are instance-owned. **Reserved stem prefix:** every page the template ships is named `mozak-<stem>` (the hub `moc-meta` and the birth seed `start-here` excepted) — the project's own name, a token no research topic will coin — so a page the template ships later can never collide with a note an instance already holds; an instance never coins a `mozak-` stem, and `graph.py ownership` flags one. |
| `journals/` | `YYYY-MM-DD.md` activity log of **this repo's own work**: what was ingested/distilled/changed in the graph (and maintenance such as syncs performed), and why. Changes to the template system itself log to `CHANGELOG.md` instead — rule 7. |
| `sources/` | Raw captures (transcripts, articles). Immutable after distillation (append-only exceptions per ingestion step 3). |
| `raw/` | Anytime dump zone: humans and agents drop unstructured files here with zero ceremony. NOT part of the graph — not link-indexed, no schema, and **contents are gitignored** (may hold huge blobs; transient by contract — disk backups cover the window until ingestion; only the README is tracked). Ingestion drains it (text → a proper `sources/` capture or `archive/`; binaries → `assets/`, the gitignored binary store; then the raw item is removed). Trends toward empty; `sources/` is the durable raw layer. |
| `assets/` | The **binary store** — images, PDFs, media that notes reference by relative path. Durable but **gitignored** (only its README is tracked): binaries don't diff or merge, they only bloat append-only history — git tracks text; disk backups are the binary durability layer. Consequence, owned explicitly: a fresh clone shows broken embeds until backup restore — so **notes must survive their images**: the prose carries the insight, an embed is enhancement. |
| `archive/` | Tracked home for **textual verbatim originals** (byte-faithful documents, fronted by a thin `sources/` note). Text only, by total policy; not link-indexed, so literal double-bracket syntax inside archived text is safe. **Naming:** each entry is a directory (always, even for one file) named exactly after its fronting note's stem — `archive/<yyyy-mm-dd>-<slug>/` — so uniqueness, chronology, and note↔archive pairing are inherited from the sources naming rule. |
| `README.md`, `SETUP.md`, `SYNC.md`, `CHANGELOG.md`, `ROADMAP.md` | Root docs: human landing page; bootstrap/ops (viewers, MCP, ingestion toolchain); template↔instance sync contract; template-system development log (rule 7); considered-and-deferred queue with the gate that re-opens each item — the changelog's forward-looking sibling, whose own header holds its entry/exit rule. |
| `templates/` | Copy on note creation; delete the guidance comments. |
| `conventions/` | [frontmatter-schema.md](conventions/frontmatter-schema.md) — extend it BEFORE using new fields/enums. |
| `tools/` | `graph.py` — check / backlinks / rename / migrate / tags / domains / ownership. `migrations/` — the append-only ledger of shipped stem renames that `migrate` replays (rule 6). `bootstrap.py` — instance birth as a checklist (SETUP §1–§3): template remote, both gates, the empty personal-context skeleton and whether its questions were asked, an instance README, a journal of its own; prints ✓/✗ with the exact next command, exits 0 only when ready, asks nothing and prefills nothing itself. `annotate.py` — serve a render locally with a live-refreshing annotation overlay + capture per-passage re-prompts to `annotations.md` ([pages/mozak-report-annotation-loop.md](pages/mozak-report-annotation-loop.md)). `recipes/` — executable typed transformations with contract headers (catalog: `grep -rA4 "^# recipe:" tools/recipes/`); check there before hand-rolling, promote on second hand-roll (rule of two). **Zero-install core:** `graph.py`, `annotate.py`, `bootstrap.py`, the hooks, the tests and CI import Python **stdlib only** and run under a bare `python3` — a fresh clone works with nothing installed, and that must stay true. Recipes are the one ring outside that line: they may declare dependencies (external binaries, or Python packages via inline script metadata), are opt-in and standalone, and are never imported or invoked by the core — declaration mechanism, runner and fallback in [tools/recipes/README.md](tools/recipes/README.md). |
| `_generated/` | Derived artifacts — **all gitignored**, nothing here is source-of-truth. `links.json`: the mechanical index, never hand-edit; `check` rebuilds it before and after edits (rule 7), pulls (SYNC ritual), and clones (SETUP smoke test). `presentations/<yyyy-mm-dd>-<slug>/`: agent-rendered outputs synthesized FROM the graph (reports, HTML, PDF) — disposable renderings; any new insight they contain is distilled back into `pages/` first (a render is never an insight's only home) and every render leaves a journal line naming its source notes. |
| `.private/` | Local-only **private zone** — the user's own notes and files. **Hard rule: the agent never reads, opens, or greps anything here unless the user explicitly approves access for that request** (it holds material the user chose to withhold from the agent). Only an empty `.gitkeep` is tracked (so the zone exists in a fresh clone); every real file is gitignored — never tracked, never in history — and nothing readable ever ships, keeping the never-read rule absolute. |
| `.personal-shared/` | Local-only **personal context** — personal facts (name, measurements, preferences, locale) that make answers concrete, and the **personal documents** the graph reasons from but git must not hold (a contract, a letter, a statement: `archive/` is tracked, so those land here instead, fronted by a thin `sources/` capture that carries the analysis, not the specifics). **Both the user and the agent may view AND edit it**, and the agent reads/uses it freely; it maintains a top-level index of what's stored in `.personal-shared/README.md`, generating that README if absent. **Environment truth lives here and outranks probing:** the shell an agent runs in may not be the user's machine (VM, container, remote host), so `lsb_release`, package and hardware queries describe *that shell* only — read this zone before any environment-dependent claim or recommendation and treat it as authoritative, report a probe as a probe of wherever the session runs, and when the fact is missing here, ask rather than infer it from the shell. But it is **never committed**: only an empty `.gitkeep` is tracked; the README and all content stay local. The complement to `.private/`: shared with the agent, withheld from git. |

## Authoring rules (MUST)

1. **Filename = kebab-case stem = wikilink target**, unique across `pages/`,
   `journals/`, `sources/`, ASCII `a-z0-9-` only (diacritics belong in `title:` /
   `aliases:` — e.g. `mozgani.md` carrying `title: Možgani`). Human title goes in
   frontmatter `title:` and the H1.
2. **Frontmatter** per [conventions/frontmatter-schema.md](conventions/frontmatter-schema.md)
   on every note (journals exempt).
3. **Portable syntax only:** `[[target]]` and `[[target|shown text]]`, in bodies only
   (never in frontmatter). Banned: `((block refs))`, `{{embeds}}`, `key:: value`
   properties, `![[transclusion]]`, and inline hash-tags — both `#[[tags]]` and bare
   `#sometag` (a hash-tag is a page reference in Logseq but a separate tag entity in
   Obsidian: same text, divergent graph semantics; and `graph.py` sees neither).
   Facets live in frontmatter `tags:` only — see the schema's tag-vs-page rule;
   query with `python3 tools/graph.py tags [tag]`.
4. **Every link states why.** A wikilink appears inside a sentence expressing the
   relation ("…contradicts [[x]] because…", "…is the EU-specific case of [[y]]…").
   No bare link dumps. MOCs may be lists, but each entry carries a clause saying what
   the target contributes. This is the quality bar that keeps agent-authored links
   from becoming noise.
5. **Concept-oriented, atomic-ish notes.** One concept per note as a guideline (not
   dogma — split when a note serves two masters, don't shred ideas). Title notes by
   concept ("index-fund cost drag"), not by source ("video X notes").
   **Admission test** — all three, before creating any note: (a) the content is
   YOUR processing — a claim, decision, judgment, connection, or verified finding —
   never a transcription of reference material; if the web or an encyclopedia
   already holds it, store the pointer (`resource:`/URL) plus your take, not the
   copy ([pages/mozak-store-the-delta.md](pages/mozak-store-the-delta.md)); (b) it has a
   plausible re-retrieval path — it links into the existing graph with stated
   context, or serves a named open question; (c) time-bound content is scoped in
   the text ("as of 2026-07" — never "currently").
6. **Never rename by hand.** `python3 tools/graph.py rename <old> <new>` rewrites
   every reference, then re-run `check`. Prefer adding `aliases:` over renaming.
   A shipped stem the template renames is also appended to `tools/migrations/renames.tsv`,
   and an instance replays that ledger with `python3 tools/graph.py migrate` after each
   pull (SYNC ritual): the pull moves the file, `migrate` repoints the instance's own
   links, and `check` names the stale ones until it runs.
   Deleting a note: re-point or remove every reference first (a dangling link
   fails `check`), then journal what was deleted and why.
7. **Bracket the session with `check`.** `python3 tools/graph.py check` regenerates the
   gitignored index `_generated/links.json`, so **run it first**, at the start of a
   task, to refresh (or materialize) an index that may be stale or absent when edits
   landed outside a checked session — then work against a current graph. Beside it run
   `python3 tools/recipes/policy.py check`: it creates `.personal-shared/acquisition-policy.toml`
   as a skeleton if absent and, until the human has recorded `[consent].acknowledged`, exits
   non-zero and prints the decisions that need a human — each option explained, each with the
   command that records it (`--json` gives the same as data). **The agent asks those questions
   rather than relaying the message** — through the harness's structured-question mechanism
   when it has one (options with explanations), in plain text otherwise — records each answer
   with `policy.py set key=value`, and never pre-answers or infers one; consent is asked last,
   after the rest. Web acquisition waits until `check` exits 0. Asked, not relayed, is what
   makes the consent informed rather than quietly skipped. **Definition
   of done** for any session that changed the repo: `check` exits 0 again (no broken
   links, no duplicate stems), plus a log entry for substantive changes — routed by
   kind: **this repo's own work** (notes ingested/distilled/edited, contested-claim
   episodes, content sweeps, syncs performed) → a `journals/` entry; **changes to the
   template system itself** (these MUST rules, the schema, `tools/`, `templates/`, root
   config such as `.gitignore`) → a [CHANGELOG.md](CHANGELOG.md) entry, which is
   template-owned (the template authors it; instances only read it). Then draft a
   commit message and stop — the human commits (unless they've explicitly opted this
   repo into autonomous commits).
   In an instance (a repo with a `template` remote) never author a template-owned file
   (SYNC Ownership table); a generalizable improvement is routed upstream, not edited
   locally — per SYNC's *Instance upstreams an improvement* ritual. `python3
   tools/graph.py ownership` flags any local edit (advisory in the bracket above; an
   opt-in pre-commit hook — SETUP — blocks it).
8. **Provenance & contradiction discipline.** Load-bearing factual claims carry
   their origin inline — "…claim ([[capture-stem]])" — so backlinks + anchors make
   repair surgical when a source proves partially wrong
   ([pages/mozak-claim-level-provenance.md](pages/mozak-claim-level-provenance.md)). On
   contradicting evidence: set `status: contested` FIRST, adversarially search
   both sides, then rewrite so the title and opening state the best current
   understanding — superseded claims stay, struck through with date + refuting
   anchor; never silently delete the loser, never let a title assert a falsehood.
   Captures are never edited — flaws get an appended dated `## Reliability notes`
   (the step-3 append-only regime). Journal the episode. Scale and stop searches
   by the gates in [pages/mozak-search-gates.md](pages/mozak-search-gates.md).
9. **Conventions have one home each.** Every rule and decision is stated
   normatively in exactly ONE place (an AGENTS rule, a schema row, a SYNC
   section); everywhere else points — "per rule 8", "per ingestion step 3" —
   never restates freely, so dependents stay greppable from their authority.
   When a convention changes, sweep: grep both repos for the authority's name and
   the concept's key terms; update or consciously confirm every hit; log the sweep
   where rule 7 routes it. Avoid enumerations a directory listing can answer (an example list rots
   the moment the next item lands); prefer deleting a copy over maintaining one.
   This is [pages/mozak-claim-level-provenance.md](pages/mozak-claim-level-provenance.md)
   applied to the system's own rules.
10. **Never publish outward without explicit authorization.** Renders — presentations,
   reports, HTML/PDF, slide decks — are LOCAL artifacts: they belong in `_generated/`
   (per its layout row) or a location the user explicitly names, nowhere else. The agent
   MUST NOT send them, or any repo content, to Claude/Anthropic Artifacts, gists,
   pastebins, hosted pages, or any other external, outward-facing destination without
   the user's explicit per-request authorization — publishing exfiltrates private
   knowledge and can be cached or indexed beyond deletion. Rendering is local by default;
   sharing is a separate, authorized act.

## Ingestion workflow (two-pass — never skip the raw layer)

1. **Capture** → `sources/<YYYY-MM-DD>-<slug>.md` (source template): provenance
   frontmatter + raw content (cleaned transcript, article text). Fetch transcripts
   locally (`yt-dlp --skip-download --write-auto-subs`; Whisper when no captions).
   Drain `raw/` first — anything dumped there becomes a capture (or is discarded
   with a journal note), then the raw item is removed. Tool policy (probe first,
   offer-install, degrade loudly) and per-format drain recipes:
   [pages/mozak-ingestion-toolchain.md](pages/mozak-ingestion-toolchain.md).
2. **Distill** → create/update `pages/` notes. Update `updated:`; promote `status:`
   when a revisit deepens a note (seed → growing → evergreen).
3. **Link** — weave new notes into the existing graph contextually (rule 4), update
   the domain MOC, cite sources with wikilinks in a `## Sources` section. After
   distillation the source file is immutable except appending a `## Distilled into`
   list or a dated `## Reliability notes` section (rule 8).
4. **Log** → `journals/YYYY-MM-DD.md`: bullets of what/why, linking touched notes.
5. **Check** → rule 7.

## Domains

One graph, many domains (`investing`, `music-metadata`, `meta`, …). Domain membership
is the frontmatter `domain:` list + a `moc-<domain>.md` hub linked from
[[start-here]] — never folders. Cross-domain links are encouraged; they're the point.
The MOC is the curated human layer; the mechanical index is derived, never maintained:
`python3 tools/graph.py domains` (rule 9 — no list to rot).

## Viewers

Obsidian: open repo as vault — native. Logseq: open as graph — usable, degraded
(`sources/` not indexed; flat paragraphs = single blocks); **read-mostly** — Logseq
rewrites files it edits. Never adopt viewer-specific syntax to improve rendering.

## Upstream sync (template ↔ instance)

This system lives in two kinds of repo: the public **template** (the generic
system) and private **instances** (living graphs born from it). Ownership of every
path, the merge protocol, and the upstream/downstream rituals are defined in
[SYNC.md](SYNC.md) — read it before resolving any merge conflict or editing
system files. Short version: tool and template files are template-owned; graph
content is instance-owned; the constitution, schema, and system-documenting meta
pages are shared-evolving — a generalizable improvement made in an instance MUST be
upstreamed (with personal facts stripped), and instances pull with
`git fetch template && git merge template/main`.
