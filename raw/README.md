# raw/

The anytime dump zone: humans and agents drop unstructured files here (text, PDFs,
exports, screenshots) with zero ceremony. Nothing in `raw/` is part of the graph —
it is not link-indexed and carries no schema. Ingestion drains it: text becomes a
proper `sources/` capture, binaries move to `assets/`, and the raw item is removed
(or discarded with a journal note). `raw/` trends toward empty; `sources/` is the
durable raw layer. See [AGENTS.md](../AGENTS.md) §Ingestion workflow.

Contents of this directory are **gitignored** (transient by contract, possibly
huge binaries; disk backups cover the window until ingestion) — only this README
is tracked.
