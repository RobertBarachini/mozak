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
