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
