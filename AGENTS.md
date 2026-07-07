# Knowledge repo — constitution

Agent-agnostic operating rules (per the [agents.md](https://agents.md) standard;
Claude Code loads this via `CLAUDE.md`). **Plain Markdown in this repo is the single
source of truth.** Every app — Claude Code, other agents, Obsidian, Logseq, grep — is
a replaceable lens. Nothing here may depend on any app to stay meaningful.

The core value is **connectedness**: forward links are written in note bodies as
`[[wikilinks]]`; backlinks are **derived, never stored** — via `tools/graph.py`
(materializes `_generated/links.json`) or plain `grep -rF '[[stem'`. Preserving
back-linking therefore reduces to two invariants: links stay greppable, names stay
stable.

## Layout

| Path | Role |
|---|---|
| `pages/` | Atomic evergreen notes — THE graph. Flat, no subfolders. |
| `journals/` | `YYYY-MM-DD.md` activity log: what was ingested/changed and why. |
| `sources/` | Raw captures (transcripts, articles). Immutable after distillation (append-only exceptions per ingestion step 3). |
| `raw/` | Anytime dump zone: humans and agents drop unstructured files here with zero ceremony. NOT part of the graph — not link-indexed, no schema, and **contents are gitignored** (may hold huge blobs; transient by contract — disk backups cover the window until ingestion; only the README is tracked). Ingestion drains it (text → a proper `sources/` capture or `archive/`; binaries → `assets/`, the gitignored binary store; then the raw item is removed). Trends toward empty; `sources/` is the durable raw layer. |
| `assets/` | The **binary store** — images, PDFs, media that notes reference by relative path. Durable but **gitignored** (only its README is tracked): binaries don't diff or merge, they only bloat append-only history — git tracks text; disk backups are the binary durability layer. Consequence, owned explicitly: a fresh clone shows broken embeds until backup restore — so **notes must survive their images**: the prose carries the insight, an embed is enhancement. |
| `archive/` | Tracked home for **textual verbatim originals** (byte-faithful documents, fronted by a thin `sources/` note). Text only, by total policy; not link-indexed, so literal double-bracket syntax inside archived text is safe. **Naming:** each entry is a directory (always, even for one file) named exactly after its fronting note's stem — `archive/<yyyy-mm-dd>-<slug>/` — so uniqueness, chronology, and note↔archive pairing are inherited from the sources naming rule. |
| `README.md`, `SETUP.md`, `SYNC.md` | Root docs: human landing page; bootstrap/ops (viewers, MCP, ingestion toolchain); template↔instance sync contract. |
| `templates/` | Copy on note creation; delete the guidance comments. |
| `conventions/` | [frontmatter-schema.md](conventions/frontmatter-schema.md) — extend it BEFORE using new fields/enums. |
| `tools/` | `graph.py` — check / backlinks / rename / tags. `recipes/` — executable typed transformations with contract headers (catalog: `grep -rA4 "^# recipe:" tools/recipes/`); check there before hand-rolling, promote on second hand-roll (rule of two). Stdlib only. |
| `_generated/` | Derived artifacts — **all gitignored**, nothing here is source-of-truth. `links.json`: the mechanical index, never hand-edit; `check` rebuilds it after edits (rule 7), pulls (SYNC ritual), and clones (SETUP smoke test). `presentations/<yyyy-mm-dd>-<slug>/`: agent-rendered outputs synthesized FROM the graph (reports, HTML, PDF) — disposable renderings; any new insight they contain is distilled back into `pages/` first (a render is never an insight's only home) and every render leaves a journal line naming its source notes. |

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
   copy ([pages/store-the-delta.md](pages/store-the-delta.md)); (b) it has a
   plausible re-retrieval path — it links into the existing graph with stated
   context, or serves a named open question; (c) time-bound content is scoped in
   the text ("as of 2026-07" — never "currently").
6. **Never rename by hand.** `python3 tools/graph.py rename <old> <new>` rewrites
   every reference, then re-run `check`. Prefer adding `aliases:` over renaming.
   Deleting a note: re-point or remove every reference first (a dangling link
   fails `check`), then journal what was deleted and why.
7. **Definition of done** for any session that touched notes:
   `python3 tools/graph.py check` exits 0 (no broken links, no duplicate stems), plus
   a journal entry for substantive changes. Then draft a commit message and stop —
   the human commits (unless they've explicitly opted this repo into autonomous
   commits).
8. **Provenance & contradiction discipline.** Load-bearing factual claims carry
   their origin inline — "…claim ([[capture-stem]])" — so backlinks + anchors make
   repair surgical when a source proves partially wrong
   ([pages/claim-level-provenance.md](pages/claim-level-provenance.md)). On
   contradicting evidence: set `status: contested` FIRST, adversarially search
   both sides, then rewrite so the title and opening state the best current
   understanding — superseded claims stay, struck through with date + refuting
   anchor; never silently delete the loser, never let a title assert a falsehood.
   Captures are never edited — flaws get an appended dated `## Reliability notes`
   (the step-3 append-only regime). Journal the episode. Scale and stop searches
   by the gates in [pages/search-gates.md](pages/search-gates.md).
9. **Conventions have one home each.** Every rule and decision is stated
   normatively in exactly ONE place (an AGENTS rule, a schema row, a SYNC
   section); everywhere else points — "per rule 8", "per ingestion step 3" —
   never restates freely, so dependents stay greppable from their authority.
   When a convention changes, sweep: grep both repos for the authority's name and
   the concept's key terms; update or consciously confirm every hit; journal the
   sweep. Avoid enumerations a directory listing can answer (an example list rots
   the moment the next item lands); prefer deleting a copy over maintaining one.
   This is [pages/claim-level-provenance.md](pages/claim-level-provenance.md)
   applied to the system's own rules.

## Ingestion workflow (two-pass — never skip the raw layer)

1. **Capture** → `sources/<YYYY-MM-DD>-<slug>.md` (source template): provenance
   frontmatter + raw content (cleaned transcript, article text). Fetch transcripts
   locally (`yt-dlp --skip-download --write-auto-subs`; Whisper when no captions).
   Drain `raw/` first — anything dumped there becomes a capture (or is discarded
   with a journal note), then the raw item is removed. Tool policy (probe first,
   offer-install, degrade loudly) and per-format drain recipes:
   [pages/ingestion-toolchain.md](pages/ingestion-toolchain.md).
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
