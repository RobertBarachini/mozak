---
name: drain-report
description: Drain a rendered report's annotations.md — process the user's per-passage re-prompts (captured by tools/annotate.py) and distill the results back into the graph.
disable-model-invocation: true
---

Process the report annotations captured by `tools/annotate.py`. This skill is a thin
Claude Code lens over an agent-agnostic contract; the contract itself lives in
`pages/report-annotation-loop.md`.

1. **Locate the target `annotations.md`.** If the user named a report or a path, use it.
   Otherwise pick the most recently modified `_generated/presentations/*/annotations.md`
   (fall back to `_generated/annotations/*/annotations.md`), and confirm the choice with
   the user if more than one is plausible. `python3 tools/annotate.py list <report.html>`
   prints a queue if you want to preview without opening the server.

2. **Run the drain contract in `pages/report-annotation-loop.md` (the "Drain" section).**
   In short: read the `[pending]` entries, do the work each prompt asks for under the
   normal research discipline, distill durable results into `pages/`, flip each entry's
   status and append an `**Agent:**` line naming the notes you touched, journal the pass,
   and finish with `python3 tools/graph.py check`.

The file is the source of truth. Do **not** restate the contract here — read
`pages/report-annotation-loop.md` and follow it, so this skill never drifts from it.
