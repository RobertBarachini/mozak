---
title: The report annotation loop — re-prompt a render, distill back
type: note
domain: [meta]
tags: [workflow]
created: 2026-07-13
updated: 2026-07-13
status: growing
---

# The report annotation loop — re-prompt a render, distill back

A render is a one-way projection of the graph outward ([[research-flow]], its
"Synthesizing outward" section) — useful until you want to talk back to it. This
note is the contract for talking back: highlight passages in a rendered HTML report,
attach a follow-up prompt to each, and drain those prompts into the graph. It is the
"re-prompt" verb of [[research-flow]] step 7 aimed at a *render* instead of the graph,
which closes the loop research → render → sharper research.

## Capture — `tools/annotate.py`

`python3 tools/annotate.py <report.html>` serves the report locally (bound to
`127.0.0.1` only — a local artifact per AGENTS rule 10, never published outward) with
an injected overlay: select text, write a prompt, and each annotation is saved to an
`annotations.md` beside the render. The tool applies **no AI** — it only captures and
serves (why that matters is below). The served page **live-refreshes** (it polls the
file's mtime), so as an agent drains, the reader watches statuses flip to `[answered]`
and answers land in place — no manual reload; a re-render reloads the embedded report and
re-anchors. Flags and endpoints live in the tool's own module docstring, not restated
here (AGENTS rule 9).

## The annotations file (the durable contract)

`_generated/presentations/<slug>/annotations.md` — one Markdown file that sits beside
the render and is gitignored and disposable exactly like it (the AGENTS `_generated/`
layout row). Each entry is a `## N. [status] <label>` heading, an optional `> quote`
blockquote, a `**Prompt:**`, an optional `**Agent:**` reply, and a fenced JSON block.
Authority is split so nothing drifts: **status** lives only in the heading token; the
**fenced JSON** owns the machine anchor; the **prose** owns the prompt and the agent's
answer.

The anchor is a text-quote selector (the quoted `exact` text plus short `prefix`/
`suffix` context and the nearest heading), not a line offset — so it re-attaches by
*content* and survives a re-render that rewrote the surrounding markup. Statuses:
`pending` → `answered` (a reply was enough) or `distilled` (a durable note was
created/updated); `orphaned` (the quoted passage vanished from a re-render — surfaced
loudly in the drawer, never silently dropped); `dismissed`.

## Drain — what the agent does

Draining `annotations.md` is a mini-ingestion pass; it names no provider or model, so
any harness runs it identically:

1. **Read** the `[pending]` entries straight from the file — the capture server need
   not be running.
2. **Work** each prompt (answer, verify a claim, expand a passage, find a
   contradiction) under the usual discipline: scope the effort by [[search-gates]], and
   on any conflict follow [[claim-level-provenance]] (contested first, adversarial both
   ways). The entry's quote and section pin exactly which passage it concerns.
3. **Distill** durable results into `pages/` under the admission test (AGENTS rule 5,
   [[store-the-delta]]), with contextual links (rule 4) and claim anchors (rule 8) —
   never leave an insight only in the disposable `annotations.md`.
4. **Record back**: flip the heading status and append an `**Agent:**` line that
   wikilinks the notes touched, so the file becomes a ledger of what was addressed.
5. **Journal** the pass, naming the notes — the same render-provenance rule that lets a
   disposable render be discarded safely ([[research-flow]], "Synthesizing outward").
6. **Optionally re-render** from the now-richer graph; reopening the tool re-anchors
   surviving annotations by quote and flags any casualties as `orphaned`.
7. **Check** (AGENTS rule 7): only the `pages/` and `journals/` edits are tracked — the
   render and `annotations.md` are gitignored — then the human commits.

**Cadence.** The drain can repeat, not just run once: the file is the queue, so each pass
re-reads whatever is `[pending]`. Trigger it by hand (the `/drain-report` lens) or have
your harness re-run it periodically — e.g. Claude Code `/loop` — so newly-flagged passages
get answered without re-prompting; with the render open, live-refresh shows those answers
landing. Opt-in by design: an unattended loop does real work and spends tokens, so the
user picks the cadence, and it stays agent-agnostic — the loop is just this drain,
repeated.

## Why the tool holds no AI (harness-agnostic by construction)

The capture tool writes a file and serves a page; all intelligence lives in whatever
drains the file. That keeps the AI harness a [[plain-text-knowledge-graphs|replaceable
lens]] just like a viewer or `grep`: swap Claude Code for another agent, a script, or a
local model and neither the tool nor the file format changes, because the seam is data,
not code. Convenience lenses over the same file — a Claude Code `/drain-report` skill,
or an MCP interface for any harness — are optional setup (SETUP.md §5), never
dependencies.

## Sources

- Introduced as a template tool on 2026-07-13 — rationale and change log in
  [CHANGELOG.md](../CHANGELOG.md); mechanics in [tools/annotate.py](../tools/annotate.py).
