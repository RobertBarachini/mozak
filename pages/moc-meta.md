---
title: Meta — map of content
type: moc
domain: [meta]
created: 2026-07-07
updated: 2026-07-07
---

# Meta — map of content

The system's knowledge about itself: why it is shaped this way and how work flows
through it. Binding rules live in [AGENTS.md](../AGENTS.md); these notes carry the
reasoning behind them.

## Design

- [[plain-text-knowledge-graphs]] — the core argument: plain text + derived
  backlinks outlive any tool.
- [[system-lineage]] — which system each convention was inherited from, and what
  was deliberately rejected.
- [[open-knowledge-format]] — adjacent industry format (Google, 2026-06):
  convergent validation of the plain-text bet; watched as an interchange bridge,
  not adopted.
- [[store-the-delta]] — what earns storage: the graph holds the delta between the
  world's knowledge and yours (the anti-collector's-fallacy admission test).

## Operating

- [[research-flow]] — the end-to-end loop from research question to re-promptable
  knowledge, and the boundary with project repos.
- [[report-annotation-loop]] — the talk-back verb for renders: annotate a rendered
  report, then drain the prompts back into the graph (research-flow step 7, aimed at a
  render).
- [[ingestion-toolchain]] — tool policy (probe first, offer-install, degrade
  loudly) and per-format recipes for draining `raw/`.
- [[claim-level-provenance]] — cite at the claim, repair surgically; the
  contradiction protocol (contested first → adversarial both ways →
  struck-through losers, titles never assert falsehoods).
- [[search-gates]] — stakes-tiered breadth/depth, source independence, and the
  recorded stop signals.
