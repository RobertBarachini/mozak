---
title: "Research: founding deep-research run — public evidence core"
type: source
domain: [meta]
medium: report
author: deep-research workflow (104 agents, Claude Opus 4.8)
retrieved: 2026-07-06
created: 2026-07-07
updated: 2026-07-07
tags: [founding]
---

# Research: founding deep-research run — public evidence core

The evidence behind this system's design claims, distilled for every instance:
method, verdicts, and the external citations the meta pages lean on. `url`
omitted per the schema's internal-research rule. The personal layer of the same
run (requirement statement, tailored recommendations, raw per-agent outputs)
is not part of the template — it remains in the founding instance's private
archive, per the privacy boundary in SYNC.md.

## Method

- Shape: 6 search angles → 21 sources fetched → 97 claims extracted → 25
  adversarially verified (3 independent refutation votes each) → 24 confirmed,
  1 refuted.
- Honest caveats, inherited by everything citing this capture: confirmed claims
  rest on primary sources (project READMEs, canonical methodology sites) —
  documented behavior, not benchmarked reliability; parts of the tool landscape
  were corroborated from Jan-2026 model knowledge during a search-API outage;
  tool-tier facts are a mid-2026 snapshot and shift fast.

## Verified findings that shaped this design

- **Evergreen-notes principles** (3-0): atomic, concept-oriented, densely linked,
  associative-over-hierarchical, written for yourself —
  <https://notes.andymatuschak.org/Evergreen_notes>. → flat `pages/`, links over
  folders, concept-oriented titles.
- **Link-context bar** (3-0, quote verified verbatim): "to collect connections
  without an explicit intention, captured meaning, or statement of relevance is
  not knowledge production" — <https://zettelkasten.de/introduction/>.
  → AGENTS rule 4.
- **REFUTED (1-2): strict "exactly one idea per note"** — the one claim killed by
  adversarial verification. → atomicity is a guideline, not dogma (rule 5).
- **Logseq's block model resists flat-markdown agents**: ergut/mcp-logseq ships a
  markdown→block converter precisely because of this (3-0), and its
  `rename_page` rewrites references — <https://github.com/ergut/mcp-logseq>.
  → no outliner authoring; `graph.py rename` reimplements reference-rewriting.
- **Obsidian MCP consolidation** (3-0): the Local REST API plugin ships a
  built-in MCP server — <https://github.com/coddingtonbear/obsidian-local-rest-api>;
  the older bridge is optional — <https://github.com/MarkusPfundstein/mcp-obsidian>.
  → viewers/MCP are optional lenses, not dependencies.
- **Dual-backend file-level access** (3-0): graphthulhu reads Obsidian vaults as
  plain files, no plugin — <https://github.com/skridlevsky/graphthulhu>.
  → plain files suffice; apps are replaceable.
- **Transcript pipeline** (all 3-0): yt-dlp `--skip-download --write-auto-subs`
  fetches transcripts without video — <https://github.com/yt-dlp/yt-dlp>;
  youtube-transcript-api needs no API key —
  <https://github.com/jdepoix/youtube-transcript-api>; Whisper is the
  caption-less fallback — <https://github.com/openai/whisper>; **YouTube blocks
  cloud/datacenter IPs** (verified) → the run-locally rule.
- **Pattern library precedent** (3-0): Fabric's reusable patterns + dated-markdown
  capture — <https://github.com/danielmiessler/fabric>. → recipes with contracts.
- **Convention-file pattern** (3-0): vault-level agent constitutions + central
  frontmatter schema — <https://github.com/heyitsnoah/claudesidian>,
  <https://deepwiki.com/productory/obsidian-claude-code-template/6.2-frontmatter-schema>.
  → AGENTS.md + conventions/frontmatter-schema.md.
- **Rejected organizers** (3-0 each, as descriptions): PARA —
  <https://fortelabs.com/blog/para/>; Johnny.Decimal — <https://johnnydecimal.com/>;
  digital-garden maturity practice — <https://maggieappleton.com/garden-history>.
  → hierarchy rejected, `seed/growing/evergreen` adopted.
- Practitioner corroboration: <https://okhlopkov.com/second-brain-obsidian-claude-code/>,
  <https://www.stefanimhoff.de/writing/agentic-note-taking-obsidian-claude-code/>,
  <https://eferro.substack.com/p/how-i-use-claude-code-to-maintain>,
  <https://github.com/AgriciDaniel/claude-obsidian>.

## Distilled into

- [[mozak-plain-text-knowledge-graphs]] — the survivability argument.
- [[mozak-system-lineage]] — the per-convention genealogy (each row's citation is above).
- [[mozak-research-flow]] — the two-pass shape and run-locally constraint.
- [[mozak-ingestion-toolchain]] — the verified transcript-pipeline behaviors.
- [[mozak-store-the-delta]] — the admission stance's Zettelkasten/evergreen grounding.
- Methodological mirror for [[mozak-claim-level-provenance]] and [[mozak-search-gates]]
  (the 3-vote refutation protocol and saturation-bounded sweep).
