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
blockquote, then a **conversation thread** — one or more `**Prompt:**` / `**Agent:**`
pairs in order — and a fenced JSON block. A trailing `**Prompt:**` with no following
`**Agent:**` is an *open turn*: it means the entry is `[pending]` (a reader added a
follow-up that hasn't been answered yet). A single prompt+answer is just the one-turn
case. Authority is split so nothing drifts: **status** lives only in the heading token;
the **fenced JSON** owns the machine anchor; the **prose** owns the conversation turns.

The anchor is a text-quote selector (the quoted `exact` text plus short `prefix`/
`suffix` context and the nearest heading), not a line offset — so it re-attaches by
*content* and survives a re-render that rewrote the surrounding markup. Statuses:
`pending` → `answered` (a reply was enough) or `distilled` (a durable note was
created/updated); `orphaned` (the quoted passage vanished from a re-render — surfaced
loudly in the drawer, never silently dropped); `dismissed`.

## Drain — what the agent does

Draining `annotations.md` is a mini-ingestion pass; it names no provider or model, so
any harness runs it identically:

1. **Read** the `[pending]` entries — fetch just that slice, not the whole file, so the
   pass's token cost scales with open work, not total history (`annotate.py list --status
   pending`, the MCP `list_annotations status=pending`, or a `grep`). The capture server
   need not be running.
2. **Work** each prompt (answer, verify a claim, expand a passage, find a
   contradiction) under the usual discipline: scope the effort by [[search-gates]], and
   on any conflict follow [[claim-level-provenance]] (contested first, adversarial both
   ways). The entry's quote and section pin exactly which passage it concerns.
3. **Distill** durable results into `pages/` under the admission test (AGENTS rule 5,
   [[store-the-delta]]), with contextual links (rule 4) and claim anchors (rule 8) —
   never leave an insight only in the disposable `annotations.md`.
4. **Record back**: append the `**Agent:**` line *immediately after the open
   `**Prompt:**`* it answers (so the pair folds correctly), wikilinking the notes touched;
   flip the heading status to `[answered]`/`[distilled]` only once **no open turn remains**
   (a multi-turn thread with a later unanswered follow-up stays `[pending]`). The file
   becomes a ledger of the whole conversation, not just the last exchange.
5. **Journal** the pass, naming the notes — the same render-provenance rule that lets a
   disposable render be discarded safely ([[research-flow]], "Synthesizing outward").
6. **Optionally re-render** from the now-richer graph; reopening the tool re-anchors
   surviving annotations by quote and flags any casualties as `orphaned`. **Re-render vs.
   edit in place:** re-rendering is the default — the render is disposable and regenerable
   from the graph, so there is nothing to "back up" (the graph is the source of truth). A
   *surgical inline edit* of the render is safe too, as long as it does not alter any
   quoted `exact` span: anchoring keys on the quoted text plus its `prefix`/`suffix`, so
   edits elsewhere leave anchors intact, and it degrades gracefully when nearby (not
   quoted) text moves. If you must change a quoted passage, expect that annotation to
   `orphan` and re-anchor/update it — the reopen→reload→orphan-detection surfaces the
   breakage loudly rather than silently dropping it.
7. **Check** (AGENTS rule 7): only the `pages/` and `journals/` edits are tracked — the
   render and `annotations.md` are gitignored — then the human commits.

**Cadence — how to re-run it, and how to auto-drive the loop.** The drain can repeat, not
just run once: the file is the queue, so each pass re-reads whatever is `[pending]`. Three
triggers, in increasing autonomy:

1. **On demand** (attended) — the user says "drain", or runs a lens like `/drain-report`.
2. **Event-driven, in-session** (the live loop) — watch `annotations.md` and drain the
   moment it gains a `[pending]` entry, so newly-flagged passages get answered without
   re-prompting; with the render open, live-refresh shows the answers landing. **Drive this
   off a file-change *event*, not a wall-clock timer.** An interactive agent session
   typically has no between-turn scheduler — a fixed-interval job (an in-session cron, a
   `/loop 5m`) never fires while the session sits idle — but it *does* have an
   event/completion wake channel: the same one that notifies the agent when a background
   task finishes. So arm a **persistent watcher that emits only when the pending count
   *rises*** (emit-on-rise, so the agent's own drain writes — which lower the count — don't
   re-trigger it, which would be a self-feeding loop); each emission wakes the agent to
   drain, then it re-arms. This is **session-lived** — it dies when the session closes,
   which is exactly right for interactive report investigation. *(Claude Code: the
   `Monitor` tool running a persistent `grep -c '\[pending\]'` poll. Shell gotcha:
   `grep -c … || echo 0` double-counts — `grep -c` prints `0` **and** exits non-zero on no
   match, so the `||` appends a second `0` and corrupts the integer compare; default empty
   with `${x:-0}` instead of the `||` idiom.)*
3. **Unattended, session-independent** (walk away) — only an **OS/host-level scheduler
   invoking the agent headless** (e.g. cron → `claude -p`) survives the session closing. It
   needs its own credentials (an interactive subscription login won't authenticate
   headless — use an API key or a minted long-lived token), a **least-privilege tool
   allowlist**, and **answer-only scoping**: write only the gitignored sidecar — never
   auto-distill into `pages/` or auto-commit, which stay human-reviewed (rule 7).

Opt-in by design: any loop does real work and spends tokens, so the user picks the trigger
and cadence. It stays agent-agnostic — the loop is just this drain, repeated; the seam is
still the file, not an API.

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
