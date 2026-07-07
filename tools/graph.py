#!/usr/bin/env python3
"""Link integrity + derived-backlink index for a plain-text knowledge repo.

Backlinks are never stored in notes; they are DERIVED from forward [[wikilinks]]
by this script (or plain grep). Conventions: AGENTS.md. Stdlib only.

Usage:
  python3 tools/graph.py check                # lint links, write _generated/links.json
  python3 tools/graph.py backlinks <stem>     # who links to <stem>, with context lines
  python3 tools/graph.py rename <old> <new>   # rename a note + rewrite all references
  python3 tools/graph.py tags [tag]           # all frontmatter tags, or notes carrying one

Notes are the .md files under pages/, journals/, sources/ (README.md excluded).
A wikilink target is a note's filename stem; stems must be unique repo-wide.
Known limitation: wikilinks inside fenced code blocks are counted like any other.
"""

import argparse
import json
import re
import sys
from pathlib import Path

WIKILINK = re.compile(r"\[\[([^\]\|#\n]+)(#[^\]\|\n]*)?(\|[^\]\n]*)?\]\]")
TITLE_RE = re.compile(r"^title:\s*(.+?)\s*$", re.M)
TAGS_RE = re.compile(r"^tags:\s*\[([^\]]*)\]", re.M)
NOTE_DIRS = ("pages", "journals", "sources")


def md_files(root: Path):
    for d in NOTE_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.md")):
            if p.name == "README.md":
                continue
            yield p


def slugify(s: str) -> str:
    return "-".join(t for t in re.split(r"[^a-z0-9]+", s.strip().lower()) if t)


def load(root: Path):
    """Return ({stem: {path, title, text}}, [(stem, kept_path, dupe_path)])."""
    notes, dupes = {}, []
    for p in md_files(root):
        rel = str(p.relative_to(root))
        if p.stem in notes:
            dupes.append((p.stem, notes[p.stem]["path"], rel))
            continue
        text = p.read_text(encoding="utf-8")
        m = TITLE_RE.search(text[:400])
        notes[p.stem] = {"path": rel, "title": m.group(1).strip('"') if m else p.stem, "text": text}
    return notes, dupes


def note_tags(text: str) -> list:
    """Frontmatter tags (flow-style `tags: [a, b]` only — the schema's form)."""
    m = TAGS_RE.search(text[:600])
    return [t.strip() for t in m.group(1).split(",") if t.strip()] if m else []


def cmd_tags(root: Path, tag=None) -> int:
    notes, _ = load(root)
    index = {}
    for stem, n in notes.items():
        for t in note_tags(n["text"]):
            index.setdefault(t, []).append(stem)
    if tag is not None:
        stems = sorted(index.get(tag, []))
        if not stems:
            print(f"no notes tagged '{tag}'")
        for s in stems:
            print(f"{notes[s]['path']}  ({notes[s]['title']})")
        return 0
    if not index:
        print("no tags found")
    for t in sorted(index):
        print(f"{t}: {len(index[t])}  —  {', '.join(sorted(index[t]))}")
    return 0


def cmd_check(root: Path) -> int:
    notes, dupes = load(root)
    by_slug = {slugify(s): s for s in notes}
    out = {s: [] for s in notes}
    back = {s: [] for s in notes}
    broken, sloppy = [], []
    for stem, n in notes.items():
        for m in WIKILINK.finditer(n["text"]):
            target = m.group(1).strip()
            r = target if target in notes else by_slug.get(slugify(target))
            if r is None:
                broken.append({"in": n["path"], "target": target})
                continue
            if r != target:
                sloppy.append({"in": n["path"], "wrote": target, "actual": r})
            if r not in out[stem]:
                out[stem].append(r)
            if stem not in back[r]:
                back[r].append(stem)
    orphans = sorted(
        s for s, n in notes.items()
        if not out[s] and not back[s] and not n["path"].startswith("journals/")
    )

    gen = root / "_generated"
    gen.mkdir(exist_ok=True)
    index = {
        "note_count": len(notes),
        "notes": {
            s: {"path": n["path"], "title": n["title"],
                "outlinks": sorted(out[s]), "backlinks": sorted(back[s])}
            for s, n in notes.items()
        },
        "broken": broken,
        "orphans": orphans,
    }
    (gen / "links.json").write_text(
        json.dumps(index, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"notes: {len(notes)}  links: {sum(len(v) for v in out.values())}  "
          f"broken: {len(broken)}  duplicate stems: {len(dupes)}  orphans: {len(orphans)}")
    for stem, kept, dupe in dupes:
        print(f"  DUPLICATE stem '{stem}': {kept} vs {dupe}")
    for b in broken:
        print(f"  BROKEN {b['in']} -> [[{b['target']}]]")
    for s in sloppy:
        print(f"  note: {s['in']} writes [[{s['wrote']}]] (resolves to [[{s['actual']}]] — normalize)")
    for o in orphans:
        print(f"  orphan (no links in or out): {notes[o]['path']}")
    print("index: _generated/links.json")
    return 1 if (broken or dupes) else 0


def cmd_backlinks(root: Path, stem: str) -> int:
    notes, _ = load(root)
    pat = re.compile(r"\[\[" + re.escape(stem) + r"(?=[\]#\|])")
    hits = 0
    for n in notes.values():
        for i, line in enumerate(n["text"].splitlines(), 1):
            if pat.search(line):
                print(f"{n['path']}:{i}: {line.strip()}")
                hits += 1
    if not hits:
        print(f"no notes link to [[{stem}]]")
    return 0


def cmd_rename(root: Path, old: str, new: str) -> int:
    notes, _ = load(root)
    if old not in notes:
        sys.exit(f"error: no note with stem '{old}'")
    if new in notes:
        sys.exit(f"error: '{new}' already exists")
    if new != slugify(new):
        sys.exit(f"error: '{new}' is not kebab-case (want '{slugify(new)}')")
    pat = re.compile(r"\[\[" + re.escape(old) + r"(?=[\]#\|])")
    touched = 0
    for p in md_files(root):
        text = p.read_text(encoding="utf-8")
        text2 = pat.sub("[[" + new, text)
        if text2 != text:
            p.write_text(text2, encoding="utf-8")
            touched += 1
            print(f"rewrote {p.relative_to(root)}")
    src = root / notes[old]["path"]
    dst = src.with_name(new + ".md")
    src.rename(dst)
    print(f"renamed {notes[old]['path']} -> {dst.relative_to(root)}")
    print(f"{touched} file(s) rewritten. Now run: python3 tools/graph.py check")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                    help="repo root (default: parent of tools/)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    p_back = sub.add_parser("backlinks")
    p_back.add_argument("stem")
    p_ren = sub.add_parser("rename")
    p_ren.add_argument("old")
    p_ren.add_argument("new")
    p_tags = sub.add_parser("tags")
    p_tags.add_argument("tag", nargs="?", default=None)
    args = ap.parse_args()
    if args.cmd == "check":
        return cmd_check(args.root)
    if args.cmd == "backlinks":
        return cmd_backlinks(args.root, args.stem)
    if args.cmd == "tags":
        return cmd_tags(args.root, args.tag)
    return cmd_rename(args.root, args.old, args.new)


if __name__ == "__main__":
    sys.exit(main())
