---
title: Lineage — where each convention of this system comes from
aliases: [system-lineage]
type: note
domain: [meta]
tags: [design]
created: 2026-07-07
updated: 2026-07-07
status: evergreen
---

# Lineage — where each convention of this system comes from

Nothing here was invented for this repo, and almost nothing is app-specific: each
convention is an inherited standard chosen because at least two independent
ecosystems already parse it — the survivability argument made in
[[mozak-plain-text-knowledge-graphs]]. What looks "Obsidian-flavored" is really the set of
pre-existing standards Obsidian itself adopted.

| Convention | Lineage | Why kept |
|---|---|---|
| Markdown | Gruber 2004 → CommonMark | Universal substrate |
| Wikilinks (double-bracket links) | Wiki software (MediaWiki-style, early 2000s) → Roam Research (2019) → Obsidian + Logseq | Terse, name-keyed, parsed by both viewers and by exporters; app-specific extensions (block refs, embeds, `key::` properties) are banned. Note: quoting live link syntax in a note creates a link — `graph.py` counts double-brackets anywhere, so write around it (as this row does) |
| YAML frontmatter | Jekyll (2008) → static-site-generator standard → Obsidian properties, pandoc | Machine-parseable metadata, readable with a stdlib regex |
| `pages/` `journals/` `assets/` layout | Logseq graph root | The one app-shaped choice; costs nothing because Obsidian is layout-agnostic |
| Daily journals | Roam daily notes → Logseq `journals/` | Activity/provenance log, not primary capture |
| Derived (never stored) backlinks | What Roam/Obsidian/Logseq compute in-app at runtime | Reified into `tools/graph.py` + grep so no app is load-bearing |
| Rename-rewrites-references | mcp-logseq's `rename_page` semantics | Reimplemented locally; mitigates name-keyed link rot |
| Atomic, concept-oriented notes | Luhmann's Zettelkasten → Matuschak's evergreen notes | As guideline — the strict one-idea-per-note dogma was refuted in the source research |
| "Every link states why" | zettelkasten.de school | Quality bar against mechanical link spam |
| MOC hub notes | Nick Milo's LYT (Obsidian community) | Curated human entry points; replaces folders |
| `seed/growing/evergreen` status | Digital-garden epistemic-status practice | Honest maturity signaling |
| Kebab-case stems | Web URL-slug practice | Agent-friendly, unique link targets |
| `AGENTS.md` + `CLAUDE.md` shim | agents.md standard (2025) | Agent-agnostic constitution, tool-specific entry shims |
| Template ↔ instance split | Dotfiles-framework practice (develop in the living copy, upstream the generalizable) | The system evolves through real use; SYNC.md carries the contract |

Deliberately rejected: PARA-as-folders and Johnny.Decimal numbering (hierarchy
walls off cross-domain links — the associative principle in
[[mozak-plain-text-knowledge-graphs]] wins); Logseq outliner authoring (block model
resists flat-markdown agents); storing backlinks in prose (churn + staleness);
inline hash-tag syntax (a hash-tag is a page reference in Logseq but a separate
tag entity in Obsidian — same text, divergent graph semantics; facets stay in
frontmatter `tags:`, and anything worth prose is a page, not a tag).

## Sources

- [[2026-07-06-founding-research]] — carries the verified citation (and the one
  refutation) behind each lineage row.
