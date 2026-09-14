---
title: Search gates — how broadly, how deeply, when to stop
aliases: [search-gates]
type: note
domain: [meta]
tags: [workflow]
created: 2026-07-07
updated: 2026-09-09
status: growing
---

# Search gates — how broadly, how deeply, when to stop

Unbounded research is the collector's fallacy with extra steps; first-hit
research is worse. Effort is set **by stakes, before searching**, and stopping is
a **recorded decision**, not exhaustion.

## Scale by stakes (choose the tier at kickoff)

| Tier | The answer gates… | Budget |
|---|---|---|
| 1 — context | curiosity, background, low-cost reversible choices | 1–2 sources, single pass, no verification beyond plausibility |
| 2 — decision | a real but cheaply-reversible decision | 3–5 **independent** sources, breadth sweep first, one adversarial pass on the load-bearing claim |
| 3 — commitment | money, health, legal, publishing, irreversible moves | multi-angle sweep, primary sources required, adversarial verification of EVERY load-bearing claim, contradictions resolved per [[mozak-claim-level-provenance]] |

## Rules of engagement

- **Breadth before depth** — a quick multi-angle sweep (different phrasings,
  source types, viewpoints) before deep-reading anything; never deep-dive the
  first hit.
- **Independence counts, copies don't** — three articles citing the same origin
  are ONE source; trace to the origin and anchor the origin.
- **Adversarial minimum** — before any claim is promoted toward `evergreen`, at
  least one deliberate disconfirmation search ("X is wrong / criticism /
  debunked"). Cheap, and it is what catches echo chambers.
- **Effort is not traffic.** These gates size the *evidence* a question needs. How many
  pages you may *fetch* to get it — page count, depth, domain scope, request rate — is a
  separate budget with a separate owner: the host you are fetching from. It lives in
  [[mozak-web-acquisition-ladder]], whose steps are **rungs** (`T0`–`T6`), not tiers — the tiers
  on this page are stakes, and the two scales are independent. A tier-1 question can
  honestly cost forty requests against one paginated API; a tier-3 one can be answered by
  three primary PDFs. Set both budgets at kickoff and record both stops.

## Stop signals (any one fires → stop)

1. **Saturation** — the last 2–3 sources added no new claims (dry-source count,
   not elapsed effort).
2. **Convergence** — independent sources agree AND a deliberate search for
   dissent found none credible.
3. **Decision sufficiency** — the question that triggered the search is
   answerable at the confidence its tier needs. Search serves questions, not
   completeness.
4. **Budget** — the tier's cap, set at kickoff, is reached; escalating the tier
   mid-search is allowed but must be journaled as a decision. (The fetch
   budget is separate and stops independently — [[mozak-web-acquisition-ladder]].)

## Record the stop

State in the note or journal **which gate fired** and on what basis ("stopped at
convergence: 4 independent sources, dissent search dry, as of 2026-07") — future
sessions inherit the confidence basis instead of re-searching or over-trusting.

## Re-open triggers

Contradicting evidence (protocol in [[mozak-claim-level-provenance]]); staleness of
as-of-scoped claims; the stakes tier of a dependent decision going up.

## Sources

- Operational practice, distilled from the shape of
  [[2026-07-06-founding-research]] (angle decomposition → saturation-bounded
  sweep → 3-vote adversarial verification) and from the admission stance of
  [[mozak-store-the-delta]].
