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
| `url` | yes* | Canonical URL. *Omit when the capture has no public address: internal agent-generated research (e.g. a deep-research run) or a `medium: document` private primary document — provenance then lives in the body (run id, script, artifact paths; or issuer, date, `archive/` path). |
| `medium` | yes | `video` \| `article` \| `paper` \| `forum` \| `book` \| `podcast` \| `report` (agent-generated research reports / internal runs) \| `dataset` (structured data captured *as data* — a CSV/JSON extract, an API response, a bulk-download slice; the capture holds the query and the slice actually used, never the whole dump) \| `document` (a primary document the graph reasons *from* — contract, letter, invoice, official decision; the note fronts it, the verbatim text lives in `archive/`, or in `.personal-shared/` when the document is too personal to track) |
| `author` | no | Creator/channel |
| `published` | no | `YYYY-MM-DD` if known |
| `retrieved` | yes | `YYYY-MM-DD` the capture was made |
| `archive-url` | no | Snapshot URL at a public archive (Wayback, archive.today) for a `url` that can rot. `url` is where it lived; `archive-url` is where it still lives. Record one whenever a snapshot is taken or found — it is what keeps the surgical repair of [claim-level provenance](../pages/mozak-claim-level-provenance.md) possible after the original 404s. A URL, never a date (that is `retrieved`). |
| `capture-method` | no* | How the bytes were obtained: a rung token from the acquisition ladder plus the tool — `T1 urllib`, `T2 wayback`, `T4 playwright`, `T6 har`. *Required at rung `T2` and above, omitted below: from T2 up the bytes are a mirror, a fingerprinted client, a rendered DOM or a logged-in session, and a bot-blocked stub or an empty JS shell reads exactly like a thin page once the session ends. Makes "which captures need re-verification" a one-grep sweep. Rungs: [web acquisition ladder](../pages/mozak-web-acquisition-ladder.md). |

**No `webpage` value in `medium`, deliberately:** the field names what the artifact *is*,
not the pipe it arrived through — a fetched news page is an `article`, a fetched statute a
`document`, a fetched JSON endpoint a `dataset`.

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
