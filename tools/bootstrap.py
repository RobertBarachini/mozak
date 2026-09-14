#!/usr/bin/env python3
"""Instance birth checklist — SETUP §1–§3 as one idempotent command.

Usage:
  python3 tools/bootstrap.py                          # print the checklist; exit 0 iff ready
  python3 tools/bootstrap.py --json                   # the same, as data (for agents)
  python3 tools/bootstrap.py --attach                 # also perform `git remote rename origin template`
                                                      #   when origin points at the template
  python3 tools/bootstrap.py --personal-context-asked # record that the personal-context questions were asked

The README hands a fresh clone to an agent with one pasted block; this is the command that
block tells the agent to run. It never asks the human anything and never writes a value on
their behalf: it says what is missing, prints the exact next command for each item, and
passes questions through — `policy.py check` renders its own, and `.personal-shared/README.md`
is seeded as an empty skeleton whose facts the agent asks for. Re-run until `ready: yes`.

Nothing here is performed unattended unless it is safe anywhere: the remote rename needs
`--attach` (the template author's own checkout looks exactly like a fresh clone), the
skeleton is only ever created, never overwritten. Core tooling: stdlib only (AGENTS
`tools/` row).
"""

import argparse
import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATE_REPO = "mozak"                              # a fresh clone's `origin` ends in this name
TEMPLATE_MARKER = "This repo is the **template**"    # the template README carries it; an instance README drops it
PERSONAL_README = ".personal-shared/README.md"
PENDING = "personal-context: pending"
ASKED = "personal-context: asked"
STEP_TIMEOUT = 120

SKELETON = """# Personal context — local-only, never committed

This zone holds the personal facts that make the agent's answers concrete, and the personal
documents the graph reasons from but git must not hold (AGENTS `.personal-shared/` row). You
and the agent may both edit it; the agent keeps this index current. Environment truth recorded
here outranks anything the agent probes from its own shell.

<!-- personal-context: pending — the agent asks the facts below one by one, records each
     answer (or leaves `—`: every fact is optional and may stay skipped), then runs
     `python3 tools/bootstrap.py --personal-context-asked`. Nothing here is ever inferred or
     prefilled by a tool. -->

## Facts

| Fact | Value |
|---|---|
| Address me as | — |
| Locale / jurisdiction (optional; `—` = answer jurisdiction-neutrally) | — |
| Preferences the agent should honour (tone, units, languages, formats) | — |
| Environment: is the shell the agent runs in your own machine? (VM, container, remote host?) | — |

## Stored here

| Path | What it is | Added |
|---|---|---|
"""


# ------------------------------------------------------------------ pure helpers

def repo_name(url: str) -> str:
    """Repository name from a remote URL or path: `.../mozak.git`, `git@host:o/mozak`,
    `/local/path/mozak/` all give `mozak`. Lower-cased for comparison."""
    tail = re.split(r"[/:]", url.strip().rstrip("/"))[-1]
    return re.sub(r"\.git$", "", tail).lower()


def remote_state(rem):
    """(ok, detail, action) for the template-remote item from a {name: url} map, or None
    when the folder is not a git repository."""
    if rem is None:
        return (False, "not a git repository",
                "clone the template instead of downloading it — SETUP §1 (a clone keeps the "
                "template attached as upstream, which the SYNC pull ritual depends on)")
    if "template" in rem:
        return (True, f"attached ({rem['template']})", "")
    if "origin" in rem and repo_name(rem["origin"]) == TEMPLATE_REPO:
        return (False, f"origin points at the template ({rem['origin']}) but is not yet named `template`",
                "run: git remote rename origin template   (or: python3 tools/bootstrap.py --attach)")
    if "origin" in rem:
        return (False, f"origin is {rem['origin']} and there is no `template` remote",
                "if that origin IS the template: git remote rename origin template · if it is your own "
                "remote: git remote add template <template-url> && git fetch template")
    return (False, "no remotes — this folder was copied, not cloned",
            "SETUP §1 to start over from a clone, or SYNC 'First stitch' to attach the template to a copy")


def readme_is_template(text: str) -> bool:
    return TEMPLATE_MARKER in text


def journal_state(local, shipped, today: str, changed=()):
    """(ok, detail). `local` = journal filenames here; `shipped` = the template's journal
    paths (from `git ls-tree <template-ref> journals/`) or None when unavailable, in which
    case today's entry stands in for 'an entry of this instance's own'; `changed` = shipped
    names whose local content differs (the instance appended to a same-dated file)."""
    if shipped is not None:
        own = sorted({n for n in local if f"journals/{n}" not in shipped} | set(changed))
        if own:
            return (True, f"{len(own)} entr{'y' if len(own) == 1 else 'ies'} of this instance's own (latest {own[-1]})")
        return (False, "no journal entry of this instance's own yet (only the template's)")
    if f"{today}.md" in local:
        return (True, f"journals/{today}.md present")
    return (False, "no journal entry of this instance's own yet")


def skeleton_values(text: str):
    """The Value column of the Facts table — [] means every fact still `—`/empty."""
    vals = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*(?P<fact>[^|]+?)\s*\|\s*(?P<val>[^|]*?)\s*\|\s*$", line)
        if m and m.group("fact") not in ("Fact", "---", "Path"):
            v = m.group("val")
            if v and v != "—" and not set(v) <= {"-"}:
                vals.append(v)
    return vals


# ------------------------------------------------------------------ side effects (each safe)

def git(root: Path, *args):
    if shutil.which("git") is None:
        return 127, "git not found"
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=STEP_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return r.returncode, (r.stdout + r.stderr).strip()


def remotes(root: Path):
    rc, out = git(root, "remote", "-v")
    if rc != 0:
        return None
    rem = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and (len(parts) < 3 or parts[2] == "(fetch)"):
            rem.setdefault(parts[0], parts[1])
    return rem


def run_tool(root: Path, rel: str, *args):
    try:
        r = subprocess.run([sys.executable, str(root / rel), "--root", str(root), *args],
                           capture_output=True, text=True, timeout=STEP_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return r.returncode, (r.stdout + r.stderr).strip()


def ensure_skeleton(root: Path) -> bool:
    """Create the empty personal-context skeleton if absent. Returns True if created."""
    p = root / PERSONAL_README
    if p.exists():
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(SKELETON, encoding="utf-8")
    return True


def mark_asked(root: Path, today: str) -> str:
    """Flip the pending marker: records that the questions were ASKED (not what was
    answered — every fact may stay `—`). Idempotent."""
    p = root / PERSONAL_README
    created = ensure_skeleton(root)
    text = p.read_text(encoding="utf-8")
    if PENDING not in text:
        return f"{PERSONAL_README}: already marked asked" if ASKED in text else \
               f"{PERSONAL_README}: no pending marker found — nothing to flip"
    new = re.sub(r"<!--\s*personal-context: pending.*?-->",
                 f"<!-- {ASKED} {today} — re-ask any fact the user wants to change; `—` means "
                 "skipped by choice, never unknown to the tool. -->", text, count=1, flags=re.S)
    p.write_text(new, encoding="utf-8")
    return f"{PERSONAL_README}: marked asked {today}" + (" (skeleton created first)" if created else "")


# ------------------------------------------------------------------ the checklist

def checklist(root: Path, attach: bool = False, today: str | None = None) -> dict:
    today = today or _dt.date.today().isoformat()
    steps = []

    def step(sid, label, ok, detail, action="", output=""):
        steps.append({"id": sid, "label": label, "ok": bool(ok), "detail": detail,
                      "action": action, "output": output})

    # 1. tools
    git_ok = shutil.which("git") is not None
    py_ok = sys.version_info >= (3, 11)
    gitv = git(root, "--version")[1].replace("git version ", "") if git_ok else "missing"
    step("tools", "tools", git_ok and py_ok,
         f"git {gitv} · python {sys.version_info.major}.{sys.version_info.minor}",
         "" if git_ok and py_ok else "install git and Python ≥ 3.11 — the only prerequisites (SETUP)")

    # 2. template remote
    rem = remotes(root)
    renamed = False
    if attach and rem and "template" not in rem and "origin" in rem and repo_name(rem["origin"]) == TEMPLATE_REPO:
        rc, _ = git(root, "remote", "rename", "origin", "template")
        renamed = rc == 0
        rem = remotes(root)
    ok, detail, action = remote_state(rem)
    if renamed:
        detail = "attached — renamed origin → template"
    step("template-remote", "template remote", ok, detail, action)

    # 3. graph check
    rc, out = run_tool(root, "tools/graph.py", "check")
    first = out.splitlines()[0] if out else "(no output)"
    step("graph-check", "graph check", rc == 0, first,
         "" if rc == 0 else "fix what `python3 tools/graph.py check` lists (broken links, duplicate stems)",
         "" if rc == 0 else out)

    # 4. acquisition policy (consent gate) — its questions pass through, never re-rendered
    rc, out = run_tool(root, "tools/recipes/policy.py", "check")
    first = out.splitlines()[0] if out else "(no output)"
    step("acquisition-policy", "acquisition policy", rc == 0,
         first if rc == 0 else "consent not recorded",
         "" if rc == 0 else "ask the user the questions below, record each with `python3 tools/recipes/policy.py "
                            "set key=value`, consent last (AGENTS rule 7)",
         "" if rc == 0 else out)

    # 5. personal context — skeleton created empty; readiness = the questions were asked
    created = ensure_skeleton(root)
    text = (root / PERSONAL_README).read_text(encoding="utf-8")
    if PENDING in text:
        step("personal-context", "personal context", False,
             f"{PERSONAL_README} " + ("created as an empty skeleton" if created else "present, questions not yet asked"),
             "ask the user the facts in it one by one (each optional; `—` skips), record them, then: "
             "python3 tools/bootstrap.py --personal-context-asked")
    else:
        step("personal-context", "personal context", True, f"{PERSONAL_README} present, questions asked")

    # 6. instance README
    readme = root / "README.md"
    is_tpl = readme.exists() and readme_is_template(readme.read_text(encoding="utf-8"))
    step("instance-readme", "instance README", not is_tpl,
         "README.md still describes the template" if is_tpl else "README.md describes this instance",
         "rewrite README.md to describe this instance — what it is for, whose it is (SETUP §3)" if is_tpl else "")

    # 7. founding journal — an entry that is not one of the template's
    jdir = root / "journals"
    local = sorted(p.name for p in jdir.glob("*.md")) if jdir.is_dir() else []
    shipped, changed, note = None, [], ""
    ref = ("template/main" if rem and "template" in rem
           else "origin/main" if rem and "origin" in rem and repo_name(rem["origin"]) == TEMPLATE_REPO
           else None)
    if ref:
        rc, out = git(root, "ls-tree", "--name-only", ref, "journals/")
        if rc == 0:
            shipped = set(out.split())
            for n in local:                      # a same-dated file the instance appended to counts as its own
                if f"journals/{n}" in shipped:
                    rc2, blob = git(root, "show", f"{ref}:journals/{n}")
                    if rc2 == 0 and blob.strip() != (jdir / n).read_text(encoding="utf-8").strip():
                        changed.append(n)
        else:
            note = f" (template not fetched — `git fetch {ref.split('/')[0]}` makes this exact)"
    ok, detail = journal_state(local, shipped, today, changed)
    detail += note
    step("founding-journal", "founding journal", ok, detail,
         "" if ok else f"write journals/{today}.md — what this instance is for and what was set up (SETUP §3)")

    optional = []
    if rem and "origin" in rem and "template" not in rem and repo_name(rem["origin"]) == TEMPLATE_REPO:
        own_origin = "none yet (origin is the template until renamed)"
    elif rem and "origin" in rem:
        own_origin = rem["origin"]
    else:
        own_origin = "none (fine; add one when you want a backup)"
    optional.append("own `origin` remote — " + own_origin)
    rc, hooks = git(root, "config", "--get", "core.hooksPath")
    optional.append("pre-commit ownership guard — " + ("on" if rc == 0 and hooks.strip() == "tools/hooks"
                                                         else "off (`git config core.hooksPath tools/hooks`)"))
    optional.append("viewers, MCP — SETUP §4–§5, when wanted")

    ready = all(s["ok"] for s in steps)
    nxt = next((s["id"] for s in steps if not s["ok"]), None)
    return {"ready": ready, "steps": steps, "optional": optional, "next": nxt, "root": str(root)}


def render(res: dict) -> str:
    lines = ["bootstrap: instance readiness — SETUP §1–§3 as a checklist; re-run until `ready: yes`"]
    for s in res["steps"]:
        mark = "✓" if s["ok"] else "✗"
        lines.append(f"  {mark} {s['label']:<19} {s['detail']}")
        if s["action"]:
            lines.append(f"      → {s['action']}")
        if s["output"]:
            lines.extend("        " + l for l in s["output"].splitlines())
    lines.append("  later, optional: " + " · ".join(res["optional"]))
    if res["ready"]:
        lines.append(f'ready: yes — tell the user: "Ready. Open {res["root"]} in your agent and ask it to '
                     'research something."')
    else:
        label = next(s["label"] for s in res["steps"] if s["id"] == res["next"])
        lines.append(f"ready: no — next: {label}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                    help="repo root (default: parent of tools/)")
    ap.add_argument("--json", action="store_true", help="print the checklist as JSON")
    ap.add_argument("--attach", action="store_true",
                    help="perform `git remote rename origin template` when origin points at the template")
    ap.add_argument("--personal-context-asked", action="store_true",
                    help="record that the personal-context questions were asked (flips the pending marker)")
    args = ap.parse_args()
    root = args.root.resolve()
    today = _dt.date.today().isoformat()
    if args.personal_context_asked:
        print(mark_asked(root, today))
    res = checklist(root, attach=args.attach, today=today)
    print(json.dumps(res, indent=1, ensure_ascii=False) if args.json else render(res))
    return 0 if res["ready"] else 2


if __name__ == "__main__":
    sys.exit(main())
