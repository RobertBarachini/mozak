---
title: Claim-level provenance — cite at the claim, repair surgically
type: note
domain: [meta]
tags: [design, workflow]
created: 2026-07-07
updated: 2026-07-07
status: growing
---

# Claim-level provenance — cite at the claim, repair surgically

Sources are routinely *partially* wrong or incomplete. A note-level `## Sources`
roster tells you a note drew on a capture; it cannot tell you **which claims**
fall if that capture falls. So provenance lives at two grains:

- **Note grain**: the `## Sources` section — every cited capture with a clause
  saying what it contributed (existing rule).
- **Claim grain**: every **load-bearing factual claim** carries its origin inline
  — "…claim (double-bracket link to the capture's stem)". Reasoning and synthesis
  flow freely between anchors; only facts the note *stands on* need them.

The payoff is **surgical repair**: when a capture proves flawed,
`graph.py backlinks <capture-stem>` lists every citing note, and the inline
anchors mark exactly which sentences depend on it. Fix those; leave the rest.
(For entity identity the anchor is the `resource:` field instead — captures
anchor claims, resources anchor entities.)

## Contradiction protocol

When new evidence contradicts an existing note:

1. **Alarm first** — set `status: contested` on the affected note(s) immediately,
   before investigating, so no concurrent session consumes them as settled.
2. **Adversarial search, both ways** — deliberately seek DISconfirming evidence
   for the old claim AND for the newcomer (validating only the challenger swaps
   one bias for another). Capture findings into `sources/` as usual; scale the
   effort by [[search-gates]].
3. **Resolve in place** — rewrite so the title and opening paragraph state the
   best current understanding. Superseded claims are never silently deleted:
   they stay, struck through, dated, and anchored —
   ~~the old claim~~ — disproved 2026-07-07 by (anchor to refuting capture).
   Negative knowledge is knowledge: it prevents re-deriving or re-believing.
4. **Titles never assert falsehoods** — a refuted note is retitled
   (`graph.py rename`) so grep and link-followers meet the truth first.
5. **Captures stay immutable** — a flawed source gains an appended, dated
   `## Reliability notes` section; the captured bytes are never edited.
6. **Journal the episode** — what contradicted, what was searched on both sides,
   the verdict — then sweep dependents via backlinks + inline anchors.

The struck-through + `contested` conventions exist so partial truth can live in
the graph **without corrupting context**: an agent reading a contested note or a
struck claim cannot mistake either for settled fact. This governs the lifecycle
of what [[store-the-delta]] admits, and is enforced at the Distill step of
[[research-flow]]. The same discipline applies to the system's own rules —
conventions have one authoritative home and dependents cite it (AGENTS rule 9),
because a restated rule drifts exactly like an unanchored claim.

## Sources

- Operational practice; the adversarial-both-ways pattern mirrors the 3-vote
  refutation verification of [[2026-07-06-founding-research]], where one
  plausible claim out of 25 died under deliberate disconfirmation.
