# mozak

*Mozak* ("brain") — a **template for agent-maintained, program-agnostic knowledge
graphs**. Plain Markdown is the single source of truth; every tool (Claude Code,
other agents, Obsidian, Logseq, grep) is a replaceable lens. Forward links are
double-bracket wikilinks in note bodies; **backlinks are derived, never stored**
(`python3 tools/graph.py check` materializes `_generated/links.json`; plain grep
works too).

This repo is the **template**: the constitution, schema, note templates, link
tooling, and the meta-domain pages that document the system. Living **instances**
(your actual knowledge bases) are born from it and stay connected — pulling system
updates down and upstreaming generalizable improvements — per the contract in
[SYNC.md](SYNC.md).

## Start an instance

```bash
git clone <this-repo> mybrain && cd mybrain
git remote rename origin template     # the template stays attached as upstream
python3 tools/graph.py check          # smoke test: 0 broken links, exit 0
```

Then follow [SETUP.md](SETUP.md) (viewers, optional MCP, ingestion toolchain) and
write your instance's first journal entry.

## Orientation

| Who | Where |
|---|---|
| Humans | [pages/start-here.md](pages/start-here.md) — the root map of content |
| Agents | [AGENTS.md](AGENTS.md) — the constitution (Claude Code loads it via [CLAUDE.md](CLAUDE.md)) |
| Ops | [SETUP.md](SETUP.md) · [SYNC.md](SYNC.md) |
| Why it's shaped this way | the meta pages: design rationale, lineage, research flow |

Designed 2026-07 from an adversarially-verified deep-research run over the
agentic-PKM landscape (MCP servers, evergreen notes/Zettelkasten/digital-garden
methodology, Logseq-vs-Obsidian authoring tradeoffs); the rationale lives in-graph
under the `meta` domain.

## Why

I've always wanted to systematically gather, organize, categorize, and retrieve
knowledge. After years of research, abstraction-building, and trial and error, I
landed on outliner tools - especially Logseq, which kicked off my interest in
outliners, ontology, epistemics, and everything adjacent. The problem I kept
hitting, even while following solid, established frameworks, was **retrieval and
drift**: knowledge went in, but finding it later - and keeping it true - didn't
scale.

From the first LLMs onward I wanted to leverage them for retrieval and knowledge
synthesis; only recently has the ecosystem matured enough for agents to act as
the brain of a full, end-to-end integrated research system - one that builds and
maintains the second brain rather than merely querying it.

This repository is my current iteration of that attempt: a system for knowledge
synthesis with a thin ontology and thick epistemics - and a meta-tool meant to
evolve into ever more integrated systems for human knowledge augmentation.
