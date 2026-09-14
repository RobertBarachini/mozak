#!/usr/bin/env python3
# recipe: web-worklist
# input:  URLs the agent chose to follow, each with a stated reason (--why); or `show` / `run`
# output: manages _generated/fetch/worklist.jsonl; `run --yes` performs pending entries as targeted pulls
# needs:  nothing (stdlib)
# usage:  python3 tools/recipes/web-worklist.py add <url> --why "..." [--from <url>] | show | run --yes [--max N]

"""Multi-page work without a crawler: an agent-curated worklist of targeted pulls.

Nothing here follows a link on its own. The agent fetches a page
(`web-fetch.py --links` surfaces its references), decides which are worth
following *and why*, adds them — a reason is mandatory — and `run` performs
those as ordinary single reads through web-fetch's `perform()`: same
politeness, same provenance, same rung logic. This is what a researcher does
with a bibliography, made recordable.

Sensible limits, all structural: `run` caps at `budget.max_fetches_per_run`; a
host that answers 403/429 or a challenge page is skipped for the rest of the run
(its answer was heard); `run` prints its plan and needs `--yes` — the documented
protocol is that the agent shows the user that plan first. Every pull's row
carries `why` and the parent URL, so the log reads as reasoning, not traffic.
Record the sweep and the stop gate in the journal, per search-gates.
Conventions: AGENTS.md; this recipe never writes into the graph.
"""

import argparse
import importlib.util
import json
import sys
import urllib.parse
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import policy as _policy  # noqa: E402

ROOT = HERE.parent.parent
STOP_VERDICTS = ("blocked", "interstitial")


def _load_webfetch():
    spec = importlib.util.spec_from_file_location("web_fetch", HERE / "web-fetch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _path(root: Path) -> Path:
    return root / "_generated" / "fetch" / "worklist.jsonl"


def load_list(root: Path) -> list[dict]:
    p = _path(root)
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def save_list(root: Path, entries: list[dict]) -> None:
    p = _path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".jsonl.tmp")
    tmp.write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in entries), encoding="utf-8")
    tmp.replace(p)


def cmd_add(root: Path, url: str, why: str, parent: str | None) -> int:
    why = (why or "").strip()
    if not why:
        sys.exit("error: a reason is mandatory — `--why \"...\"`. The worklist records judgement, "
                 "not traffic; an entry without a reason is a crawl.")
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        sys.exit(f"error: not an http(s) URL: {url}")
    entries = load_list(root)
    for e in entries:
        if e["url"] == url and e["status"] in ("pending", "done"):
            print(f"already listed ({e['status']}): {url}")
            return 0
    entries.append({"url": url, "why": why, "from": parent, "added_at": _now(),
                    "status": "pending", "result": None})
    save_list(root, entries)
    print(f"added: {url}\n  why: {why}")
    return 0


def cmd_show(root: Path) -> int:
    entries = load_list(root)
    if not entries:
        print("worklist is empty")
        return 0
    for e in entries:
        res = e.get("result") or {}
        tail = f" → {res.get('verdict')} {res.get('rung', '')}".rstrip() if res else ""
        print(f"[{e['status']:>7}] {e['url']}{tail}\n          why: {e['why']}"
              + (f"\n          from: {e['from']}" if e.get("from") else ""))
    pend = sum(e["status"] == "pending" for e in entries)
    print(f"\n{len(entries)} entries, {pend} pending")
    return 0


def cmd_run(root: Path, cfg: dict, prov: str, yes: bool, max_n: int | None, perform=None) -> int:
    entries = load_list(root)
    pending = [e for e in entries if e["status"] == "pending"]
    cap = max_n or cfg["budget"]["max_fetches_per_run"]
    plan = pending[:cap]
    if not plan:
        print("nothing pending")
        return 0
    hosts = {}
    for e in plan:
        h = urllib.parse.urlsplit(e["url"]).netloc
        hosts[h] = hosts.get(h, 0) + 1
    print(f"# plan: {len(plan)} targeted pull(s) of {len(pending)} pending (cap {cap}), "
          f"{len(hosts)} host(s): " + ", ".join(f"{h}×{n}" for h, n in hosts.items()))
    for e in plan:
        print(f"  - {e['url']}\n      why: {e['why']}")
    if not yes:
        print("\nnot running: re-run with --yes once the user has seen this plan "
              "(the protocol in pages/web-acquisition-ladder.md).", file=sys.stderr)
        return 3

    if perform is None:
        wf = _load_webfetch()
        wf.STORE = root / "_generated" / "fetch"
        perform = wf.perform
    run_id = uuid.uuid4().hex[:8]
    blocked_hosts: set[str] = set()
    done = failed = skipped = 0
    print()
    for e in plan:
        host = urllib.parse.urlsplit(e["url"]).netloc
        if host in blocked_hosts:
            e.update(status="skipped", result={"verdict": "skipped", "run": run_id,
                                               "reason": f"{host} answered no earlier in this run"})
            skipped += 1
            print(f"[ skipped] {e['url']} — {host} already said no this run")
            save_list(root, entries)                  # every status change is persisted
            continue
        try:
            row, ext, notes = perform(e["url"], cfg, prov, root,
                                      extra={"why": e["why"], "from": e.get("from"),
                                             "worklist_run": run_id})
        except ValueError as ex:
            e.update(status="failed", result={"verdict": "error", "reason": str(ex), "run": run_id})
            failed += 1
            print(f"[  failed] {e['url']} — {ex}")
            save_list(root, entries)
            continue
        for n in notes:
            print(n, file=sys.stderr)
        v = row["verdict"]
        e.update(status="done" if v == "ok" else "failed",
                 result={"verdict": v, "rung": row.get("rung"), "blob_ref": row.get("blob_ref"),
                         "extract_chars": row.get("extract_chars"), "run": run_id})
        if v == "ok":
            done += 1
            print(f"[      ok] {row.get('rung')} {e['url']}  ({row.get('extract_chars')} chars) — {e['why']}")
        else:
            failed += 1
            print(f"[{v:>8}] {e['url']} — {row.get('verdict_reason', '')[:80]}")
            if v in STOP_VERDICTS:
                blocked_hosts.add(host)
        save_list(root, entries)                      # progress survives an interruption

    save_list(root, entries)
    print(f"\n# run {run_id}: {done} ok, {failed} failed, {skipped} skipped; "
          f"{len(pending) - len(plan)} still pending. Journal the sweep and which stop gate fired.")
    return 0 if done else 4


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=ROOT)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="queue a URL the agent decided is worth a targeted pull")
    a.add_argument("url")
    a.add_argument("--why", required=True, help="the reason this reference matters (mandatory)")
    a.add_argument("--from", dest="parent", help="the page it was found on")
    sub.add_parser("show", help="list the worklist with reasons and results")
    r = sub.add_parser("run", help="perform pending entries as targeted pulls")
    r.add_argument("--yes", action="store_true", help="actually run (after the user has seen the plan)")
    r.add_argument("--max", type=int, help="cap for this run (default: budget.max_fetches_per_run)")
    args = ap.parse_args()

    cfg, prov = _policy.load(args.root)
    if args.cmd == "show":
        return cmd_show(args.root)
    refusal = _policy.gate(cfg)
    if refusal:
        print(refusal, file=sys.stderr)
        return 2
    if args.cmd == "add":
        return cmd_add(args.root, args.url, args.why, args.parent)
    return cmd_run(args.root, cfg, prov, args.yes, args.max)


if __name__ == "__main__":
    sys.exit(main())
