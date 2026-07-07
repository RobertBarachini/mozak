# tools/recipes/

Reusable, executable, **typed transformations**: "given input A of type Y, this
produces output B of type X" — so agents run a known-good recipe instead of
re-deriving parsing every session. Stdlib-only Python or plain bash, one file per
recipe.

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
- **Rule of two**: the second time you hand-roll something reusable, promote it to
  a recipe — then upstream it (SYNC.md ritual). Don't write speculative recipes.
- Recipes follow the tool policy of the ingestion-toolchain page: probe deps,
  degrade loudly, never modify inputs in place.
- Ownership: this directory is template-owned and public. Instance-local recipes
  (private paths, personal services) live in `tools/recipes/local/` — instance-owned,
  never shipped by the template, never upstreamed automatically.
