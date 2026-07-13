---
title: The research flow — gather, capture, distill, link, re-prompt
type: note
domain: [meta]
tags: [workflow]
created: 2026-07-07
updated: 2026-07-09
status: growing
---

# The research flow — gather, capture, distill, link, re-prompt

How a research topic enters this graph and pays off later. One graph holds all
domains; per-domain MOCs (linked from [[start-here]]) scope each session's context,
and derived backlinks keep retrieval cheap — the mechanism argued in
[[plain-text-knowledge-graphs]].

1. **Kick off** — open an agent session in this repo and state the question
   (e.g. "investing strategies for EU individuals"). The constitution loads
   automatically; no per-session setup.
2. **Gather** — web research, transcript fetches (`yt-dlp --skip-download
   --write-auto-subs`, run locally — cloud IPs get blocked), documents — plus
   whatever is already waiting in `raw/`, the anytime dump zone for unstructured
   files. Tool policy and per-format drain recipes: [[ingestion-toolchain]].
   Scale breadth/depth and stop by the gates in [[search-gates]].
3. **Capture** — one file per source into `sources/<date>-<slug>.md` (source
   template): provenance frontmatter + cleaned raw content. Immutable afterwards.
   Drained `raw/` items become captures (binaries move to `assets/`, the
   gitignored binary store; textual verbatim originals worth keeping move to
   tracked `archive/`); the raw original is then removed.
4. **Distill** — atomic, concept-titled notes into `pages/`; update rather than
   duplicate when a note already covers the concept; bump `updated:`, promote
   `status:` on deepening. Every candidate note passes the admission test (AGENTS
   rule 5): your processing, never a transcription — [[store-the-delta]].
   Load-bearing claims carry inline capture anchors, and contradictions with
   existing notes trigger the protocol in [[claim-level-provenance]] — contested
   first, adversarial both ways, losers struck through, never silently replaced.
5. **Link** — weave new notes into the existing graph with stated reasons; update
   the domain MOC (create `moc-<domain>` + link from [[start-here]] if the domain
   is new); cite captures in `## Sources`.
6. **Close** — journal entry, `graph.py check` exits 0, draft commit, human reviews.
7. **Re-prompt** (the payoff) — any later session asks against the graph ("what did
   we conclude about accumulating vs distributing ETFs?"): navigate MOC → links →
   notes, or `graph.py backlinks` / grep. Load only what is followed — never
   bulk-read `pages/`. If the question exposes a gap, that gap is the next research
   task, and the flow repeats.

## Synthesizing outward

Renders of graph knowledge for an audience or a moment — topic reports, HTML
pages, PDFs, slide decks — go to `_generated/presentations/<yyyy-mm-dd>-<slug>/`
(gitignored: disposable renderings, externally backed up). Two rules keep the
graph primary: any **new** synthesis produced while rendering is distilled back
into `pages/` — a render is never an insight's only home — and every render
leaves a journal line naming the notes it drew on, so provenance survives the
render's disposal. A render stays **local** to that folder (or a location the user
explicitly names); publishing it outward — to Claude/Anthropic Artifacts or any external
host — requires the user's explicit authorization (AGENTS rule 10). To turn a reader's
reactions to a render back into graph work, [[report-annotation-loop]] captures
per-passage re-prompts on the rendered HTML and drains them through this same
distill-and-journal cycle.

## Boundary with project repos

Durable, cross-project knowledge lives here; operational how-this-codebase-works
documentation lives in the project's own repo. Rule of thumb: **outlives the
project → this graph; explains a codebase → that repo's docs.** Cross-references
between the two are plain text/URLs, not wikilinks — a stale pointer across that
boundary is cheap, severed in-graph links are not.

## Sources

- [[2026-07-06-founding-research]] — verified sources for the two-pass
  capture→distill shape and the run-locally constraint.
