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
  (CI enforces this on every push and PR, plus the stdlib tests and — in the template
  only — `graph.py ownership --template`: a shipped page carries the reserved `mozak-`
  stem prefix per the AGENTS `pages/` row, and a renamed one has its row in
  `tools/migrations/renames.tsv` per rule 6), and template-system changes get a
  [CHANGELOG.md](CHANGELOG.md) entry; a change weighed and deliberately *not* made gets a
  [ROADMAP.md](ROADMAP.md) row with the gate that would re-open it.
- **Conventions** — [AGENTS.md](AGENTS.md) is the constitution;
  [conventions/frontmatter-schema.md](conventions/frontmatter-schema.md) is
  extended *before* new fields are used; the **core tooling stays stdlib-only**
  (AGENTS `tools/` row), and a recipe that needs more declares it per
  [tools/recipes/README.md](tools/recipes/README.md).

Agents draft commits and stop; humans review, commit, and push.
