# Frontmatter schema

YAML frontmatter on every note in `pages/` and `sources/` (journals exempt). Extend
this file FIRST before using a new field or enum value — it is the contract agents
validate against. Wikilinks never go in frontmatter (parser support varies); links
live in bodies.

## Common fields (all types)

| Field | Req | Value |
|---|---|---|
| `title` | yes | Human title (filename stays kebab-case) |
| `type` | yes | `note` \| `moc` \| `source` |
| `domain` | yes | List, ≥1 kebab-case domain (`investing`, `music-metadata`, `meta`, …). New domain ⇒ create `moc-<domain>.md` + link it from [[start-here]]. |
| `created` | yes | `YYYY-MM-DD` |
| `updated` | yes | `YYYY-MM-DD` — bump on every substantive edit |
| `tags` | no | List; finer-grained facets than domain (`etf`, `tax`, `mir`) — dimensions you filter BY but would never write ABOUT. **Tag-vs-page rule:** if it deserves prose or accumulates knowledge, it is a page — wikilink it with stated context instead. Frontmatter-only: inline `#hashtags` in bodies are banned (AGENTS rule 3). Query: `python3 tools/graph.py tags [tag]` |
| `aliases` | no | Alternate names a human might search; prefer adding one over renaming |
| `resource` | no | Canonical URI of the entity this note is *about* (repo, product page, `urn:isin:…`, DOI) — for **entity notes** only; omit for concept notes. Distinct from source `url`: `url` = provenance of captured content, `resource` = identity of the note's subject. One canonical URI (alternates go in the body). **Before creating an entity note, grep frontmatter for the URI — same `resource` = same entity, extend the existing note instead.** Adopted from OKF, 2026-07-07. |

## `type: note` extras

| Field | Req | Value |
|---|---|---|
| `status` | yes | `seed` (stub/claim parked) → `growing` (substantiated, some links) → `evergreen` (stable, densely linked, revisited). Plus the alarm state `contested`: conflicting evidence under adversarial review — set FIRST on contradiction, before investigating (AGENTS rule 8); exits back to `growing`/`evergreen` once resolved, with superseded claims struck through, dated, and anchored. |

## `type: source` extras (raw captures — see ingestion workflow)

| Field | Req | Value |
|---|---|---|
| `url` | yes* | Canonical URL. *Omit for internal agent-generated research (e.g. a deep-research run) — provenance then lives in the body (run id, script, artifact paths). |
| `medium` | yes | `video` \| `article` \| `paper` \| `forum` \| `book` \| `podcast` \| `report` (agent-generated research reports / internal runs) |
| `author` | no | Creator/channel |
| `published` | no | `YYYY-MM-DD` if known |
| `retrieved` | yes | `YYYY-MM-DD` the capture was made |

## Examples

```yaml
---
title: UCITS ETF cost drag for EU retail investors
type: note
domain: [investing]
tags: [etf, fees]
created: 2026-07-06
updated: 2026-07-06
status: seed
---
```

```yaml
---
title: "Talk: index investing for Europeans"
type: source
domain: [investing]
url: https://www.youtube.com/watch?v=XXXXXXXXXXX
medium: video
author: Example Channel
retrieved: 2026-07-06
created: 2026-07-06
updated: 2026-07-06
---
```
