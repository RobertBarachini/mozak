#!/usr/bin/env python3
"""Link integrity + derived-backlink index for a plain-text knowledge repo.

Backlinks are never stored in notes; they are DERIVED from forward [[wikilinks]]
by this script (or plain grep). Conventions: AGENTS.md. Core tooling: stdlib only (AGENTS `tools/` row).

Usage:
  python3 tools/graph.py check                # lint links, write _generated/links.json
  python3 tools/graph.py backlinks <stem>     # who links to <stem>, with context lines
  python3 tools/graph.py rename <old> <new>   # rename a note + rewrite all references
  python3 tools/graph.py migrate              # in an instance, after a pull: repoint your links to stems the template renamed
  python3 tools/graph.py tags [tag]           # all frontmatter tags, or notes carrying one
  python3 tools/graph.py domains [domain]     # derived domain index (frontmatter `domain:`), or one domain's notes
  python3 tools/graph.py ownership            # in an instance: flag locally-authored template-owned files, stem collisions, reserved stems
  python3 tools/graph.py ownership --template # in the template: verify the shipping convention (mozak- prefix, rename ledger)

Notes are the .md files under pages/, journals/, sources/ (README.md excluded).
A wikilink target is a note's filename stem; stems must be unique repo-wide.
Known limitation: wikilinks inside fenced code blocks are counted like any other.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

WIKILINK = re.compile(r"\[\[([^\]\|#\n]+)(#[^\]\|\n]*)?(\|[^\]\n]*)?\]\]")
TITLE_RE = re.compile(r"^title:\s*(.+?)\s*$", re.M)
TAGS_RE = re.compile(r"^tags:\s*\[([^\]]*)\]", re.M)
DOMAIN_RE = re.compile(r"^domain:\s*\[([^\]]*)\]", re.M)
NOTE_DIRS = ("pages", "journals", "sources")
BIRTH_SEEDS = ("pages/start-here.md",)  # template-shipped pages that are instance-owned (SYNC)
RESERVED_PREFIX = "mozak-"  # every shipped page carries it; a token no research topic coins (AGENTS `pages/` row)
MIGRATIONS = "tools/migrations/renames.tsv"  # shipped stem renames, replayed by `migrate` (AGENTS rule 6)


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


def note_domains(text: str) -> list:
    """Frontmatter domains (flow-style `domain: [a, b]` only — the schema's form)."""
    m = DOMAIN_RE.search(text[:600])
    return [d.strip() for d in m.group(1).split(",") if d.strip()] if m else []


def cmd_domains(root: Path, domain=None) -> int:
    """Derived domain lookup (AGENTS Domains section): frontmatter `domain:` lists are
    the mechanical index; the MOC is the curated layer. Never a maintained list."""
    notes, _ = load(root)
    index = {}
    for stem, n in notes.items():
        for d in note_domains(n["text"]):
            index.setdefault(d, []).append(stem)
    if domain is not None:
        stems = sorted(index.get(domain, []))
        if not stems:
            print(f"no notes in domain '{domain}'")
        for s in stems:
            print(f"{notes[s]['path']}  ({notes[s]['title']})")
        return 0
    if not index:
        print("no domains found")
    for d in sorted(index):
        moc = f"moc-{d}"
        hub = notes[moc]["path"] if moc in notes else "NO MOC (create moc-%s + link from start-here)" % d
        print(f"{d}: {len(index[d])} notes  —  hub: {hub}")
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
    if broken:                 # stale links to a stem the template renamed have a one-command fix
        try:
            chain = resolve_chain(load_migrations(root))
            stale = sorted({b["target"] for b in broken
                            if b["target"] not in notes and chain.get(b["target"]) in notes})
        except ValueError:
            stale = []
        if stale:
            print(f"  hint: {len(stale)} broken target(s) are stems the template renamed "
                  f"({', '.join(stale)}) — run `python3 tools/graph.py migrate`, then check again "
                  "(AGENTS rule 6, SYNC pull ritual)")
    for s in sloppy:
        print(f"  note: {s['in']} writes [[{s['wrote']}]] (resolves to [[{s['actual']}]] — normalize)")
    for o in orphans:
        print(f"  orphan (no links in or out): {notes[o]['path']}")
    print("index: _generated/links.json")
    rc = 1 if (broken or dupes) else 0
    try:                       # advisory ownership guard (rule 7 bracket); never wedges check
        cmd_ownership(root, strict=False, verbose=False)
    except Exception:
        pass
    return rc


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


def load_migrations(root: Path):
    """Shipped stem renames, oldest first, as [(date, old, new)] from the ledger
    (tab-separated; blank lines and `#` comments skipped). No ledger ⇒ []. A malformed
    row raises ValueError — callers decide whether that wedges them."""
    p = root / MIGRATIONS
    if not p.is_file():
        return []
    rows = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = [t.strip() for t in s.split("\t")]
        if len(parts) != 3 or not all(parts):
            raise ValueError(f"{MIGRATIONS}:{i}: expected date<TAB>old-stem<TAB>new-stem, got {line!r}")
        rows.append(tuple(parts))
    return rows


def resolve_chain(rows):
    """{old: final} — follow a→b, b→c to c, so a link written before two renames still
    lands on the stem that exists today. Cycles stop at the first repeat."""
    nxt = {o: n for _, o, n in rows}
    out = {}
    for o in nxt:
        cur, seen = o, set()
        while cur in nxt and cur not in seen:
            seen.add(cur)
            cur = nxt[cur]
        out[o] = cur
    return out


def reserved_violations(local_paths, roster):
    """Local `pages/mozak-*.md` outside the template roster: a stem an instance coined
    inside the reserved prefix (AGENTS `pages/` row). Pure, for the ownership guard."""
    return sorted(p for p in local_paths
                  if Path(p).stem.startswith(RESERVED_PREFIX)
                  and p not in roster and p not in BIRTH_SEEDS)


def template_convention(root: Path):
    """Problems with the template's shipping convention, [] when clean: every pages/*.md
    except birth seeds and `moc-*` hubs carries RESERVED_PREFIX; the ledger parses; each
    ledger row's final stem exists and its old stem does not. Run in the template only —
    an instance's own pages legitimately lack the prefix."""
    problems = []
    notes, _ = load(root)
    pages = root / "pages"
    for p in sorted(pages.glob("*.md")) if pages.is_dir() else []:
        rel = f"pages/{p.name}"
        if rel in BIRTH_SEEDS or p.stem.startswith("moc-") or p.stem.startswith(RESERVED_PREFIX):
            continue
        problems.append(f"{rel}: shipped page without the `{RESERVED_PREFIX}` prefix")
    try:
        rows = load_migrations(root)
    except ValueError as e:
        return problems + [str(e)]
    chain = resolve_chain(rows)
    for _, o, n in rows:
        if n != slugify(n):
            problems.append(f"{MIGRATIONS}: '{n}' is not kebab-case")
        if chain[o] not in notes:
            problems.append(f"{MIGRATIONS}: {o} -> {n}: no note '{chain[o]}' exists")
        if o in notes:
            problems.append(f"{MIGRATIONS}: {o} -> {n}: old stem '{o}' still exists")
    return problems


def cmd_migrate(root: Path) -> int:
    """Instance side of a shipped stem rename (AGENTS rule 6, SYNC pull ritual). The pull
    already moved the template's file; what is left stale is the instance's own `[[old]]`
    links, which `rename` cannot fix because the old note is gone. For every ledger row
    whose final stem exists here while the old stem does not, rewrite `[[old]]`,
    `[[old|…]]` and `[[old#…]]` across the note directories. A row whose old stem still
    exists is left alone — that note is the instance's own, and so are links to it.
    Idempotent: a second run rewrites nothing."""
    try:
        rows = load_migrations(root)
    except ValueError as e:
        sys.exit(f"error: {e}")
    if not rows:
        print(f"migrate: no ledger at {MIGRATIONS} — nothing to replay")
        return 0
    notes, _ = load(root)
    chain = resolve_chain(rows)
    todo = [(o, n) for o, n in chain.items() if n in notes and o not in notes and o != n]
    for o, n in sorted(chain.items()):
        if o in notes and n in notes and o != n:
            print(f"migrate: [[{o}]] left alone — a local note with that stem exists, so links "
                  f"to it are yours (the template's page is [[{n}]])")
    if not todo:
        print(f"migrate: nothing pending — {len(rows)} ledger row(s), all applied or not yet pulled")
        return 0
    pats = [(o, n, re.compile(r"\[\[" + re.escape(o) + r"(?=[\]#\|])")) for o, n in todo]
    hits = {o: 0 for o, _ in todo}
    touched = 0
    for p in md_files(root):
        text = p.read_text(encoding="utf-8")
        text2 = text
        for o, n, pat in pats:
            text2, k = pat.subn("[[" + n, text2)
            hits[o] += k
        if text2 != text:
            p.write_text(text2, encoding="utf-8")
            touched += 1
            print(f"rewrote {p.relative_to(root)}")
    for o, n in todo:
        if hits[o]:
            print(f"migrate: [[{o}]] -> [[{n}]]  ({hits[o]} link(s))")
    if not touched:
        print("migrate: nothing pending — no stale links to renamed stems")
        return 0
    print(f"{touched} file(s) rewritten. Now run: python3 tools/graph.py check")
    return 0


def _git(root: Path, *args):
    """Run git in `root`; return stdout str, or None on any failure (git missing, not a
    repo, non-zero exit). Ownership degrades to a no-op rather than erroring."""
    try:
        r = subprocess.run(["git", "-C", str(root), *args],
                           capture_output=True, text=True)
    except (OSError, ValueError):
        return None
    return r.stdout if r.returncode == 0 else None


def _cell_globs(cell: str):
    """(owned, excluded) path globs from one Ownership-table cell: every `backticked`
    token, trailing slash stripped; a token inside an `except ( … )` span is excluded."""
    spans = []
    for m in re.finditer(r"except", cell):
        close = cell.find(")", m.end())
        spans.append((m.end(), close if close != -1 else len(cell)))
    owned, excl = [], []
    for m in re.finditer(r"`([^`]+)`", cell):
        tok = m.group(1).strip().rstrip("/")
        (excl if any(a <= m.start() < b for a, b in spans) else owned).append(tok)
    return owned, excl


def parse_ownership(root: Path):
    """Template-owned + shared-evolving path sets, parsed from SYNC.md's Ownership table
    — the ONE normative home (AGENTS rule 9); never hardcode the list here."""
    owned, excludes, shared = [], [], []
    for line in (root / "SYNC.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("| **Template-owned**"):
            owned, excludes = _cell_globs(line.split("|")[2])
        elif line.startswith("| **Shared-evolving**"):
            shared = [t for t in _cell_globs(line.split("|")[2])[0]
                      if t.endswith(".md") and "*" not in t]
    return owned, excludes, shared


def cmd_ownership(root: Path, strict=False, template_ref="template/main",
                  verbose=True, upstream_reminders=False, template_mode=False) -> int:
    """In an INSTANCE (a repo with a `template` remote), flag template-owned files the
    instance authored locally — a boundary violation (SYNC Ownership table). The
    template-shipped meta pages are covered via a dynamic roster (ls-tree of the
    template ref, minus birth seeds). Detection diffs from the merge-base with the
    template, so being un-pulled never false-positives; content byte-identical to the
    template ref is a sync receipt, never flagged (a pull-in-progress stays clean).
    A flagged roster page absent at the merge-base is reported as STEM-COLLISION
    (rename the local note before merging) rather than OWNED-EDIT.
    A local `pages/mozak-*.md` outside the roster is RESERVED-STEM: the prefix belongs to
    template-shipped pages (AGENTS `pages/` row).
    No-op (exit 0) in the template repo, or when no template baseline is available —
    except with `template_mode`, the template's own check of its shipping convention
    (`template_convention`), which is never inferred: an instance's CI checkout also has
    no `template` remote, so the caller says which repo this is."""
    if template_mode:
        problems = template_convention(root)
        print(f"ownership --template: {len(problems)} convention problem(s)"
              + ("" if problems else f" — every shipped page carries `{RESERVED_PREFIX}`, ledger consistent"))
        for pr in problems:
            print(f"  {pr}")
        return 1 if problems else 0
    remotes = _git(root, "remote")
    if remotes is None:
        if verbose:
            print("ownership: git unavailable — skipping")
        return 0
    if "template" not in remotes.split():
        if verbose:
            print("ownership: not an instance (no `template` remote) — skipping")
        return 0

    owned, excludes, shared = parse_ownership(root)
    if not owned:                       # fail loud: a reworded table must not pass silently
        print("ownership: parsed 0 template-owned paths from SYNC.md — Ownership table "
              "format changed?")
        return 1 if strict else 0

    mb = _git(root, "merge-base", "HEAD", template_ref)
    if mb is None and template_ref == "template/main":
        template_ref = "template/HEAD"          # propagate: roster + receipt diffs below
        mb = _git(root, "merge-base", "HEAD", template_ref)
    if mb is None:
        if verbose:
            print(f"ownership: no merge-base with {template_ref} — run "
                  "`git fetch template`. Skipping.")
        return 0
    mb = mb.strip()

    def changed(spec, *diffargs):
        """File set from `git diff --name-only`; None on git failure (≠ empty diff)."""
        out = _git(root, "diff", "--name-only", *diffargs, "--", *spec)
        return None if out is None else set(out.split())

    # The meta-page roster is dynamic — the template's own pages/ listing (SYNC
    # Ownership: that listing IS the roster; birth seeds are instance-owned).
    ls = _git(root, "ls-tree", "--name-only", template_ref, "pages/")
    meta_pages = [p for p in (ls.split("\n") if ls else []) if p and p not in BIRTH_SEEDS]

    pathspec = owned + meta_pages + [f":(exclude){e}" for e in excludes]
    candidates = (changed(pathspec, mb, "HEAD") or set()) | (changed(pathspec, "HEAD") or set())
    # Sync receipts are not authorship: drop anything byte-identical to the template's
    # content (this keeps a pull-in-progress clean even with the pre-commit hook on).
    # A FAILED receipt diff must skip the filter, never blank the candidate set.
    receipt_diff = changed(pathspec, template_ref)
    if receipt_diff is not None:
        candidates &= receipt_diff
    elif verbose:
        print(f"ownership: cannot diff against {template_ref} — receipt filter skipped")

    def in_tree(ref, path):
        return _git(root, "cat-file", "-e", f"{ref}:{path}") is not None

    # A flagged meta page the merge-base never had is a STEM COLLISION (the instance
    # coined the stem before the template shipped it), not an edit of a template page.
    collisions = sorted(c for c in candidates
                        if c in meta_pages and not in_tree(mb, c) and (root / c).exists())
    # A local pages/mozak-*.md the template does not ship coins a reserved stem — listed
    # from disk, so an uncommitted file is caught too.
    pages_dir = root / "pages"
    local_pages = sorted(f"pages/{p.name}" for p in pages_dir.glob("*.md")) if pages_dir.is_dir() else []
    reserved = reserved_violations(local_pages, meta_pages)
    violations = sorted(candidates - set(collisions) - set(reserved))

    if violations or collisions or reserved or verbose:
        print(f"ownership: {len(violations)} template-owned file(s) authored locally"
              + (f", {len(collisions)} stem collision(s)" if collisions else "")
              + (f", {len(reserved)} reserved stem(s)" if reserved else ""))
    for v in violations:
        print(f"  OWNED-EDIT {v}")
    for r in reserved:
        print(f"  RESERVED-STEM {r} — the `{RESERVED_PREFIX}` prefix is reserved for template-shipped "
              f"pages (AGENTS `pages/` row); rename the local note "
              f"(`python3 tools/graph.py rename {Path(r).stem} <new-stem>`).")
    for c in collisions:
        print(f"  STEM-COLLISION {c} — the template ships this stem; rename the local "
              f"note first (`python3 tools/graph.py rename {Path(c).stem} <new-stem>`), "
              "then merge. The template owns its stems.")
    if violations:
        url = (_git(root, "remote", "get-url", "template") or "template").strip()
        print(f"  → route upstream (do NOT edit here): make the change in the template "
              f"checkout ({url}), generalized; the human commits + pushes; then "
              "`git merge template/main` here. See SYNC 'Instance upstreams an improvement'.")
    if upstream_reminders and shared:
        for s in sorted((changed(shared, mb, "HEAD") or set()) | (changed(shared, "HEAD") or set())):
            print(f"  shared-evolving changed (upstream any generic improvement): {s}")

    return 1 if ((violations or reserved) and strict) else 0


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
    sub.add_parser("migrate")
    p_tags = sub.add_parser("tags")
    p_tags.add_argument("tag", nargs="?", default=None)
    p_dom = sub.add_parser("domains")
    p_dom.add_argument("domain", nargs="?", default=None)
    p_own = sub.add_parser("ownership")
    p_own.add_argument("--strict", action="store_true")
    p_own.add_argument("--template-ref", default="template/main")
    p_own.add_argument("--upstream-reminders", action="store_true")
    p_own.add_argument("--template", action="store_true",
                       help="this checkout IS the template: verify the shipping convention instead")
    args = ap.parse_args()
    if args.cmd == "check":
        return cmd_check(args.root)
    if args.cmd == "migrate":
        return cmd_migrate(args.root)
    if args.cmd == "backlinks":
        return cmd_backlinks(args.root, args.stem)
    if args.cmd == "tags":
        return cmd_tags(args.root, args.tag)
    if args.cmd == "domains":
        return cmd_domains(args.root, args.domain)
    if args.cmd == "ownership":
        return cmd_ownership(args.root, strict=args.strict,
                             template_ref=args.template_ref,
                             upstream_reminders=args.upstream_reminders,
                             template_mode=args.template)
    return cmd_rename(args.root, args.old, args.new)


if __name__ == "__main__":
    sys.exit(main())
