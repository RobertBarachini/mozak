# Changelog

Development history of the **template system itself** — the MUST rules, the frontmatter
schema, `tools/`, `templates/`, and root config (`.gitignore` and the rest of the
machinery). This repo's *own* work — ingesting sources, distilling notes, maintenance
such as syncs — is not logged here; that lives in `journals/`. The routing rule has one
home: AGENTS rule 7.

**Template-owned** (see [SYNC.md](SYNC.md)): the template authors this file; instances
receive its entries on `git merge template/main` and never write to it, so it always
fast-forwards cleanly. An instance's generalizable system change is upstreamed (and
returns here via the pull), not logged locally; an instance records *performing* a sync
in its own journal.

Newest first.

## 2026-08-05

- **Logo re-homed to `.github/mozak.png` — a tracked path — so it renders on GitHub.**
  Follow-up to the facelift below: `assets/` is gitignored by contract, so the logo would
  have shown broken on any push/clone. Rather than carve a gitignore exception into the
  `assets/` contract, the image moved to `.github/` — already template-owned and tracked
  (SYNC Ownership table), and the de facto GitHub home for README imagery; repo machinery,
  not graph content, so the binary store's rules don't apply. Downscaled 1080→840 px
  (2× its 420 px display width), 312K→188K, to respect append-only history.

- **README facelift — logo, badges, quick-nav.** The template README now opens with a
  centered logo, a tagline, static shields.io badges (license, plain-Markdown,
  derived-backlinks, stdlib-only), and in-page navigation links; sections gained emoji
  headers and the design-provenance paragraph became a blockquote. **Content unchanged** —
  same prose, same claims.
  Badges are external images (shields.io) — they render on GitHub, not offline; they carry
  no repo content.

## 2026-08-02

- **Personal documents get a home: `.personal-shared/`, fronted by `medium: document`.**
  Upstreamed from an instance that needed to ingest a signed contract: a primary document
  the graph reasons *from* fitted no source `medium`, and no zone could hold its verbatim
  text (`archive/` is tracked git — wrong for a lease or a letter; `.private/` is
  agent-unreadable; `raw/` is transient). Two coordinated changes: the schema gains
  `medium: document` (contract, letter, invoice, official decision — the note fronts it;
  the verbatim text lives in `archive/`, or in `.personal-shared/` when the document is
  too personal to track) with the `url` exemption widened to match (such documents have
  no public address); and the AGENTS `.personal-shared/` layout row now names personal
  **documents** alongside personal facts — held untracked, fronted by a thin `sources/`
  capture that carries the analysis, not the specifics, so the tracked graph survives
  its documents.

## 2026-07-14 (later)

- **`annotate.py` — a transient `processing` status.** Between `pending` and
  `answered`/`distilled`, an agent may flip an entry to `[processing]` when it picks up a
  slow drain (a verification, a long synthesis) so a watched live page shows work in flight
  (pulsing chip). It is **transient, not durable**: the sole difference from every other
  status, which are properties of the annotation. Stuck-state is impossible by construction
  — `cmd_serve` **sweeps any `processing` → `pending` on startup** (single-owner: the server
  is the only process and nothing is mid-drain at boot, so leftover `processing` is a
  died-mid-drain artifact), and the Reopen button also requeues it. Optional and
  agent-agnostic: a quick drain skips straight to `answered`; the Monitor still keys on
  `[pending]`, so `processing` neither re-triggers the loop nor is counted. Documented in
  `pages/report-annotation-loop.md` (status list + drain step 2).

## 2026-07-14

- **`annotate.py` — threaded conversations per annotation (schema `annotate/1` → `annotate/2`).**
  An annotation is now a **thread**: one or more `**Prompt:**` / `**Agent:**` pairs in the
  prose (greppable, hand-editable, backward-compatible — an old single pair reads as one
  turn). A trailing unanswered `**Prompt:**` ⟺ `[pending]`. New `POST /annotations/followup`
  appends a turn from the drawer and **re-opens the entry to `pending`**, so a follow-up
  auto-re-enters the drain loop (the emit-on-rise watcher fires) and gets answered in place
  with no re-prompting. Parser (`_turns`), serializer, `_mcp_view`, and `cmd_list` all move
  to turns; the drain contract's "Record back" step is updated (append the `**Agent:**`
  after the open prompt; flip the heading only when no open turn remains).
- **Agent answers render as Markdown** in the drawer (a small self-contained renderer —
  bold/italic/code/links/lists), escaped-first for safety. `[[wikilinks]]` render as real,
  copyable note links with a 📝 marker; web links open in a new tab.
- **In-pane note viewer.** Clicking a `[[note]]` opens it **rendered in the report pane**
  (block-level Markdown: headings/lists/quotes/code + inline), with a **← Report / ← Back**
  bar; the note's own wikilinks drill deeper (back-stack). A **View raw ⇄ View rendered**
  toggle shows the note source. Backed by a new **`GET /note/<stem>`** route that serves a
  note resolved strictly through a stem→path index (`note_index`, globbing
  `pages/ journals/ sources/`) — 127.0.0.1-only, no path traversal.
- **Filtered reads — `list --status <state>`** (and the drain contract now says read the
  `[pending]` slice, not the whole file), so a drain's token cost scales with open work, not
  total history. MCP `list_annotations status=` already filtered.
- **Drawer polish:** live **search/filter** box (matches section/quote/prompts/answers);
  **newest-first** ordering within status groups; **per-card View raw ⇄ View rendered**
  toggle (`GET /annotations/raw/<id>`); a **resizable** drawer (drag the seam, width
  persisted in `localStorage`); toggling the drawer now **also toggles the report
  highlights** for a clean read; user prompts get a distinct left-border accent.
- **Fixes:** drawer sort dropped pending to the bottom via a falsy-`0` bug (`o[s]||9` where
  `pending`=0); clicks on links inside answers were swallowed by the card's focus handler;
  the note viewer preserved hard-wrap source newlines as `<br>` (now soft-wrapped per
  Markdown); justified text in the viewer (not the narrow drawer).
- Rationale: a render was answerable one-shot; now it's a **threaded, searchable,
  navigable** reading surface — and the graph became browsable from inside an annotation —
  while the seam stays a plain gitignored `annotations.md` any harness can drain.

## 2026-07-13 (later)

- **`annotate.py` serve now live-refreshes — answers land in an open render without a
  reload.** The served page polls a new cheap `GET /version` (mtimes of `annotations.md`
  + the report) every ~1.5s and, on change, calls the existing `reload()` (re-pull →
  re-anchor → re-render the drawer, which already shows the `**Agent:**` answer); a
  changed report reloads the embedded iframe and re-anchors by quote. So an agent's drain
  — flipped statuses, appended answers — appears in place while the reader watches. This
  is **client polling**, not SSE/WebSocket/MCP: fewer moving parts, no long-lived
  connections, still stdlib-only and `127.0.0.1`-only (rule 10); the file stays the seam
  (the poll reflects file state, it adds no API the agent must speak).
- **Drain cadence documented** in `pages/report-annotation-loop.md`: the drain can be
  re-run periodically (the file is the queue) — by hand or via a harness loop (e.g. Claude
  Code `/loop`), opt-in and agent-agnostic — so with live-refresh a reader sees
  freshly-flagged passages answered as the agent works.
- **Auto-drain loop guidance corrected — event, not timer** (`pages/report-annotation-loop.md`
  Cadence section, rewritten to three autonomy tiers). Field-tested finding: an in-session
  fixed-interval trigger (cron / `/loop 5m`) **does not fire** in an interactive agent
  session — there's no between-turn wall-clock scheduler — but an **event/completion wake
  channel does work** (the same one that reports a finished background task). So the live
  loop must be driven by a **file-change event**: a persistent watcher on `annotations.md`
  that **emits only when the `[pending]` count rises** (emit-on-rise — the agent's own drain
  writes lower the count, so they don't self-retrigger the loop), which wakes the agent to
  drain, then re-arms. Session-lived by nature (dies with the session — the right fit for
  interactive report investigation). True unattended draining instead needs an OS-level
  scheduler running the agent headless (cron → `claude -p`) with its own credentials, a
  least-privilege allowlist, and answer-only scoping. Also recorded: the
  `grep -c … || echo 0` double-count gotcha that silently breaks such a watcher.

## 2026-07-13

- **New tool `tools/annotate.py` — the report annotation loop.** A stdlib-only
  capture-and-serve tool: `python3 tools/annotate.py <report.html>` serves a render on
  `127.0.0.1` only (a local artifact, rule 10) inside a same-origin iframe with an injected
  overlay; the user highlights passages and attaches follow-up prompts, saved to an
  `annotations.md` beside the render. The tool applies **no AI** — no SDK, key, or model —
  so the AI harness stays a replaceable lens (`pages/plain-text-knowledge-graphs.md`): any
  agent drains the file, and swapping harness/model/provider changes neither the tool nor
  the file format. Highlights are non-destructive (CSS Custom Highlight API) and anchored by
  a text-quote selector (exact + prefix/suffix + nearest heading), so they re-attach by
  content and survive a re-render; a passage that vanishes surfaces as `orphaned`, never
  silently lost.
- **Fix — the report iframe rendered as a ~300×150 box.** The `#mzk-report` iframe was
  sized by `top/right/bottom/left` offsets with `width/height:auto`, but an `<iframe>` is a
  *replaced* element: those offsets don't stretch it and `auto` collapses to the intrinsic
  ~300×150. Now sized explicitly with `height:calc(100% - 46px)` and (drawer-open)
  `width:calc(100% - 360px)`. Reproduced in Firefox and Brave; surfaced on the loop's first
  live shakedown.
- **Drain contract in one home — `pages/report-annotation-loop.md`** (a new template-owned
  meta page): the mini-ingestion loop an agent runs over `annotations.md` (read pending →
  work → distill into `pages/` → record status + an `**Agent:**` line → journal → re-render
  → check). Linked from `pages/research-flow.md` ("Synthesizing outward" — the render's
  talk-back verb) and `pages/moc-meta.md`; the AGENTS `tools/` row points to the tool.
- **Two optional lenses over the file, never dependencies:** a Claude Code `/drain-report`
  skill (`.claude/skills/drain-report/` — a thin pointer to the contract, like `CLAUDE.md`
  is a thin shim), and a read-only MCP stdio interface (`annotate.py mcp` — a minimal
  hand-rolled JSON-RPC server, since the official SDK is a third-party dep — registered
  optionally per SETUP.md §5, defaulting to the latest render).
- **Ownership plumbing for the shipped skill:** `.claude/skills/` joins the SYNC
  Template-owned set (the guard's table parser picks up the new token, no manifest to
  maintain — rule 9); `.gitignore` ships `.claude/skills/` but keeps per-machine Claude
  state local (`.claude/*` + `!.claude/skills/`, mirroring the `raw/*` idiom).
- Rationale: a render was a one-way projection of the graph until now — this closes
  research → render → sharper research without leaving the plain-text substrate, and the
  genericity comes from the tool doing zero AI: the seam is a file, not an API.

## 2026-07-09 (later)

- **File-grain ownership replaces the two designated zones** (SYNC Ownership table).
  `pages/start-here.md` is now a **birth seed** — template-shipped at instantiation,
  instance-owned outright from then on (the `## Domains` index grows there; template-side
  edits reach only future instances; conflicts resolve keep-ours). The other
  template-shipped **meta pages move from shared-evolving to template-owned**: instances
  never edit their bodies — they annotate by *linking from their own notes*; backlinks
  are derived, so the connection surfaces without touching the shared file, and the
  in-file `## Sources` zone is gone. Shared-evolving shrinks to the four contract docs
  (`AGENTS.md`, `SYNC.md`, schema, `SETUP.md` body). Rationale: zones made ownership
  section-grained, which no tool can check; file-grain is machine-checkable, and the
  zones were solving a problem the link graph already solves.
- **`graph.py ownership` learned the new boundary.** The meta-page roster is resolved
  dynamically (ls-tree of the template ref, minus birth seeds — no maintained list,
  rule 9). Content byte-identical to the template ref is a **sync receipt**, never
  flagged — a pull-in-progress stays clean even with the pre-commit hook installed
  (fixes the mid-merge false positive an instance reported on 2026-07-09). A flagged
  roster page absent at the merge-base reports as **STEM-COLLISION** (the instance
  coined a stem the template now ships): rename the local note, then merge; collisions
  stay advisory even under `--strict`, since the authoring commit was innocent. Also
  hardened: the `template/HEAD` fallback now propagates to the roster/receipt diffs,
  and a failed receipt diff skips the filter loudly instead of blanking the candidate
  set.
- **`graph.py domains`** — derived domain lookup: frontmatter `domain:` lists → note
  count + MOC hub per domain; `domains <name>` lists that domain's notes. The MOC stays
  the curated layer; the mechanical index is derivable, so no enumeration can rot
  (rule 9). AGENTS' Domains section and `tools/` row point to it.

## 2026-07-09

- **Ownership guard — `graph.py ownership` enforces the template-owned boundary.** New
  subcommand that, in an instance (a repo with a `template` remote), flags any
  template-owned file (SYNC Ownership table) the instance authored locally — detected via
  `git diff` from the merge-base with `template/main`, so being un-pulled never
  false-positives, and birth divergences (`SETUP.md`, `README.md`) are structurally out
  of scope since they aren't template-owned. No-op in the template itself. Surfaces:
  - **advisory** inside the rule-7 `check` bracket (never changes `check`'s exit code);
  - **opt-in hard gate** via a shipped `tools/hooks/pre-commit`
    (`git config core.hooksPath tools/hooks` — SETUP);
  - an **AGENTS rule-7 clause**: in an instance, route generalizable improvements upstream
    (SYNC *Instance upstreams an improvement*), never author template-owned files locally.
  The template-owned path set is **parsed from the SYNC.md Ownership table** — the one
  normative home (rule 9), no duplicate manifest — failing loud if the parse yields zero
  paths. CI stays link-check only (a bare checkout has no `template` remote); the
  ownership-in-CI recipe is documented, not wired.
- **Gitignore Python bytecode** (`__pycache__/`, `*.pyc`): surfaced by the guard's own
  test — `graph.py` is now importable, so caches must never be committed and would
  otherwise trip the ownership guard as stray files under `tools/`.
- **New MUST rule 10 — never publish outward without authorization.** Renders
  (presentations, reports, HTML/PDF, slide decks) stay in `_generated/` or a location the
  user explicitly names; the agent must not push them, or any repo content, to
  Claude/Anthropic Artifacts or any other external destination without the user's
  explicit per-request authorization. `pages/research-flow.md` ("Synthesizing outward")
  points to it.

## 2026-07-08

- **Local-only privacy zones: `.private/` and `.personal-shared/`.** Two zones whose
  contents never enter git — each ships only an empty `.gitkeep` so a fresh clone shows
  the zone exists and is usable — documented in one home, the [AGENTS.md](AGENTS.md)
  Layout table:
  - `.private/` — the user's own notes; the agent must not read, open, or grep it
    without explicit per-request approval. Nothing readable ever ships, keeping the
    never-read rule absolute.
  - `.personal-shared/` — personal facts (name, measurements, preferences) that both the
    user and the agent may view and edit; the agent uses them to make answers concrete
    and keeps a top-level index in a local `.personal-shared/README.md` (gitignored,
    generated if absent). Never committed.
- **Introduced this `CHANGELOG.md` and split the done-log by kind (AGENTS rule 7):**
  template-system changes are recorded here; this repo's own knowledge work and
  maintenance stay in `journals/`. Before this, rule 7 sent *every* substantive change
  to a journal — which dropped template-development history into the instance-owned
  journal namespace, where it clashed with users' own dated entries on pull.
- **Made the zone model explicit** (AGENTS Layout preamble + a SYNC "gitignored ⇒
  instance-local" principle): the repo's folders sort along three independent axes —
  sync ownership, agent access, and durability — and any gitignored path is
  user-visible yet untouchable by upstream. Documents an existing guarantee (e.g.
  `_generated/presentations/`); no new directory.
- **`check` now brackets a session, not just ends it (AGENTS rule 7):** run
  `graph.py check` at the *start* of a task too — to refresh or materialize the
  gitignored `_generated/links.json` before working (notes may have been edited
  outside a checked session) — not only at done.
