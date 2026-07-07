---
title: Open Knowledge Format (OKF) — convergent, adjacent, not adopted
type: note
domain: [meta]
tags: [design, interop]
created: 2026-07-07
updated: 2026-07-07
status: seed
---

# Open Knowledge Format (OKF) — convergent, adjacent, not adopted

Google's OKF (v0.1, announced 2026-06-12) is an open format for "human- and
agent-friendly" knowledge: directories of Markdown files with YAML frontmatter
(required `type`; recommended title/description/resource/tags/timestamp),
maintained like code in version control, linked into a graph, consumed by agents
that parse frontmatter, traverse links, and tolerate unknown fields. That is the
same bet this system makes — independent industry convergence that validates
[[plain-text-knowledge-graphs]].

Why it is not our foundation:

- Links are bundle-relative **paths** in standard Markdown, and per the spec
  "cross-links may be broken without violating conformance" — the opposite of our
  name-keyed wikilinks with check-enforced integrity (a broken link fails check).
- No backlink concept; we derive backlinks as a first-class query.
- Organizes by typed directory taxonomy (`tables/`, `metrics/`, an `index.md` per
  directory) — the hierarchy-first shape [[system-lineage]] records us deliberately
  rejecting in favor of associative flatness.
- Its domain is organizational data-asset knowledge (datasets, tables, metrics,
  playbooks; BigQuery/Dataplex ecosystem), not personal multi-domain research.

What it is good for here:

- **Interchange bridge (watched, not built).** Consuming a shared OKF bundle is
  ordinary ingestion (Markdown + frontmatter → capture → distill). Exporting a
  domain as an OKF-ish bundle is a mechanical transform: wikilinks → relative
  links, add index files — the required `type` field we already carry. Revisit if
  a real bundle ever needs to flow either way.
- Its `resource:` field (canonical URI of the described entity) was **adopted into
  our schema (2026-07-07)** for entity notes: it gives agents a machine-checkable
  identity key (grep the URI before creating — prevents the same entity forking
  under two names) and a dereference target for re-verifying a note against
  reality. Once entity notes exist, `graph.py` should grow a duplicate-`resource`
  lint, mirroring the duplicate-stem check.
- Its "producers may add fields; consumers must tolerate unknown keys" principle
  matches our schema-evolution stance — reassuring convergence on the details, not
  just the substrate.

## Sources

- [OKF SPEC.md](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
  — the v0.1 specification (fetched 2026-07-07).
- [How the Open Knowledge Format can improve data sharing](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)
  — Google Cloud blog announcement, 2026-06-12 (fetched 2026-07-07).
