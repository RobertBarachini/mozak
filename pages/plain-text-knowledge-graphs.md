---
title: Plain-text knowledge graphs outlive their tools
type: note
domain: [meta]
tags: [design]
created: 2026-07-06
updated: 2026-07-07
status: evergreen
---

# Plain-text knowledge graphs outlive their tools

A knowledge graph survives tool churn when its connectedness is carried by the text
itself rather than by an application's database: forward links written inline as
wikilinks, names kept stable, and backlinks *derived* on demand (grep, or
`tools/graph.py`) instead of stored. Any app — Obsidian, Logseq, a future agent —
then becomes a replaceable lens over the same files, which is why this repo's
constitution bans tool-specific syntax and treats [[start-here]] as a curated map
rather than an app feature.

The failure mode this defends against is name-keyed link rot: renaming a note
silently orphans every reference to it, which is why renames go through
`tools/graph.py rename` and why check runs before every commit.

## Sources

- [[2026-07-06-founding-research]] — the derived-backlink decision and the
  link-context rule trace to its verified Zettelkasten and evergreen-notes
  citations.
