# assets/

The **binary store**: images, PDFs, audio/video, and other opaque payloads that
notes reference by relative path. Durable — but **gitignored** (only this README
is tracked): git tracks text, which diffs, merges, and greps; binaries only
bloat append-only history. Disk backups (rsync-class) are the durability layer
for this directory.

Owned consequence: a fresh clone renders broken embeds until backup restore —
therefore **notes must survive their images** (the prose carries the insight; an
embed is enhancement, never an insight's only home). Textual verbatim originals
belong in tracked `archive/` instead. See AGENTS.md §Layout.
