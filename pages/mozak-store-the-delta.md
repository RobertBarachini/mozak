---
title: Store the delta, not the encyclopedia
aliases: [store-the-delta]
type: note
domain: [meta]
tags: [design]
created: 2026-07-07
updated: 2026-07-07
status: growing
---

# Store the delta, not the encyclopedia

The failure mode this graph must avoid has a name — the **collector's fallacy**
(Zettelkasten school): copying information feels like knowledge work but isn't,
and produces a worse Wikipedia with bad retrieval. The antidote is consensus
across serious PKM schools: **store transformations, not transcriptions**.
Luhmann's slip-box was never an encyclopedia — it stored his thinking; references
lived separately. This note complements [[mozak-plain-text-knowledge-graphs]]: that one
argues *where* knowledge lives, this one argues *what deserves to live there*.

**The counterfactual test**: imagine a full local Wikipedia dump (Kiwix) beside
this repo. Everything it makes redundant was never worth storing. What remains is
the graph's actual job — what an encyclopedia structurally cannot hold:

1. **Position** — encyclopedias are neutral by policy; this graph is opinionated
   by design.
2. **Decisions and rationale**, including rejected alternatives.
3. **Cross-domain connections unique to this graph's owner and projects.**
4. **Provenance-weighted verification** — what was checked, when, against what,
   at what confidence (`status:`, Sources sections).
5. **Local, ephemeral-but-load-bearing facts**, scoped with as-of dates.
6. **Synthesis deltas** — the contradiction, comparison, or pattern *across*
   sources: the delta itself.

One line: **store the delta between the world's knowledge and yours.**

Consequences:

- Reference-shaped knowledge is **pointed at, never copied** (`resource:`, URLs);
  summarize only the slice you actually use, in your own words, with why it
  matters here. A local dump or the live web is an external resource like a
  project repo — referenced, never imported; connectivity changes dereference
  latency, not admission.
- **Transient vs foundational**: foundational = verified claims plus reasoning,
  decisions, mental models, hard-won procedural gotchas. Transient = anything
  with an implicit "currently" — admissible only when scoped in the text
  ("as of 2026-07", never "currently") AND load-bearing for a decision.
- **The LLM-era twist** (honestly unsettled, and the reason this note is
  `growing`): models compress the encyclopedia layer into their weights and can
  regenerate summaries on demand from `sources/` — so stored summaries lose
  value, and what keeps value is exactly what cannot be regenerated: your
  verification acts, decisions, local facts, and cross-links.
- The margins remain debated between schools: capture-liberal (Forte's CODE —
  capture freely, organize by actionability) vs process-first (Zettelkasten —
  distill immediately or discard). This system deliberately sits between:
  verbatim capture is allowed only into `sources/` and only for material actually
  processed (the two-pass toll is the structural anti-hoarding gate); knowledge
  enters `pages/` exclusively through distillation, gated by the admission test
  (AGENTS rule 5) that this note grounds — enforced at the Distill step of
  [[mozak-research-flow]].

## Sources

- [[2026-07-06-founding-research]] — the verified zettelkasten.de and Matuschak
  citations this note builds on
  ([introduction](https://zettelkasten.de/introduction/),
  [evergreen notes](https://notes.andymatuschak.org/Evergreen_notes)).
