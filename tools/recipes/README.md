# tools/recipes/

Reusable, executable, **typed transformations**: "given input A of type Y, this
produces output B of type X" — so agents run a known-good recipe instead of
re-deriving parsing every session. One file per recipe — Python or plain bash.

## Contract header (required)

Every recipe opens with a machine-scannable header:

```
# recipe: yt-transcript
# input:  YouTube URL (or an existing .vtt file via --vtt)
# output: clean deduplicated transcript text on stdout
# needs:  yt-dlp (only for URL mode)
# usage:  python3 tools/recipes/yt-transcript.py <url> [--lang en] [--keep-timestamps]
```

The catalog is therefore just: `grep -rA4 "^# recipe:" tools/recipes/`.

## Rules

- **Check here before hand-rolling** a transformation (AGENTS ingestion workflow).
- **Rule of two**: the second time the same reusable transformation is derived,
  promote it to a recipe — then upstream it (SYNC.md ritual). **Derivations inside a
  session count**: an inline `python3 -c`, a hand-built `curl | sed` pipeline, or a
  harness's built-in tool used to re-derive the same parsing are hand-rolls too — they
  are simply invisible to a grep of `tools/`, which is why an obviously recurring
  transformation can sit un-promoted for months. Don't write speculative recipes;
  documenting a technique in a page is not writing a recipe.
- Recipes follow the tool policy of the mozak-ingestion-toolchain page: probe deps,
  degrade loudly, never modify inputs in place.
- **A recipe never writes into the graph** — not `pages/`, `sources/`, `journals/`, or
  `archive/`. Recipes write to stdout, to `_generated/`, or to a path given on the
  command line. Authoring a note is a toll paid per item
  ([pages/mozak-store-the-delta.md](../../pages/mozak-store-the-delta.md)); a tool that could pay it
  in bulk would dissolve the two-pass gate, so no tool is given the ability.
- Ownership: this directory is template-owned and public. Instance-local recipes
  (private paths, personal services) live in `tools/recipes/local/` — instance-owned,
  never shipped by the template, never upstreamed automatically.

## Canonical preamble (fixed order)

So the catalog grep (`grep -rA4 "^# recipe:"`) always returns exactly the five contract
lines and nothing else:

1. **Shebang** — `#!/usr/bin/env python3` for a stdlib recipe;
   `#!/usr/bin/env -S uv run --quiet --script` when a PEP 723 block is present.
2. **Contract header** — the five lines `# recipe:` `# input:` `# output:` `# needs:`
   `# usage:`, in that order, contiguous, no blank line between them. Five lines, always:
   the grep window is part of the contract.
3. **Blank line.**
4. **PEP 723 block**, only if needed — `# /// script` … `# ///`. One per file, placed
   after the header so the `-A4` window can never reach it.
5. **Module docstring** — what it does and the gotcha it encapsulates.
6. **Imports** — stdlib at module top; heavy third-party imports go *inside* the function
   that uses them, so the pure functions stay importable and testable under bare `python3`.

There is deliberately **no `# rung:` or `# tier:` field**: which acquisition rung a fetch
used is a property of the invocation, not the file, and it is recorded in the capture's
`capture-method:` frontmatter instead.

## Dependencies (the one home for this rule)

The **core** is zero-install: `tools/graph.py`, `tools/annotate.py`, `tools/hooks/`,
`tools/tests/` and CI import Python stdlib only and run under a bare `python3` (AGENTS
`tools/` row). Recipes are the ring outside that line — they exist so the core never has
to take dependencies on — and may declare what they need, in exactly two forms:

1. **External binaries** — the `# needs:` line of the contract header. Probe with
   `shutil.which`; on absence, exit with the install command and what the tool was for
   (the mozak-ingestion-toolchain tool policy: degrade loudly, never silently).
2. **Python packages** — [PEP 723](https://peps.python.org/pep-0723/) inline script
   metadata: a `# /// script` comment block in the file itself. The runner is
   `uv run <recipe>`, which resolves the packages into a throwaway environment and
   installs nothing globally. **No uv?** `python3 -m venv .venv && .venv/bin/pip install
   <the packages listed in the block> && .venv/bin/python tools/recipes/<name>.py …`.
   The block is the single source of truth for the list either way.

Rules that keep the ring from leaking inward:

- **Dependencies point inward only.** A recipe may import from `tools/`; nothing in
  `tools/` imports or shells out to a recipe. `graph.py check` must pass on a machine with
  neither uv nor any package installed.
- **Preflight, don't traceback.** Guard the heavy import and exit non-zero with the
  `uv run` line and the venv fallback, so `python3 <recipe>` gives a useful message
  instead of an ImportError wall.
- **Never fetch-and-run.** An agent may run a *committed, reviewed* PEP 723 script; it must
  never execute one fetched from elsewhere. `uv run` silently resolves and installs the
  declared packages before executing a line of code — that is the whole convenience, and
  the whole risk.
