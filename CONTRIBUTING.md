# Contributing

Improvements are welcome — this template evolves through the same contract its
instances live by, so this file only points at the authorities (AGENTS rule 9):

- **What you may change where** — the Ownership table in [SYNC.md](SYNC.md):
  tool and template files are template-owned, the constitution/schema are
  shared-evolving, graph content is instance-owned.
- **How a change flows in** — SYNC.md § *Instance upstreams an improvement*:
  generalize first (the privacy boundary is a hard rule — no personal facts, no
  instance content), re-apply in a template checkout, keep commits small and
  single-purpose.
- **Definition of done** — AGENTS rule 7: `python3 tools/graph.py check` exits 0
  (CI enforces this on every push and PR), and template-system changes get a
  [CHANGELOG.md](CHANGELOG.md) entry.
- **Conventions** — [AGENTS.md](AGENTS.md) is the constitution;
  [conventions/frontmatter-schema.md](conventions/frontmatter-schema.md) is
  extended *before* new fields are used; tools stay Python stdlib-only.

Agents draft commits and stop; humans review, commit, and push.
