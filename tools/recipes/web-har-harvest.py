#!/usr/bin/env python3
# recipe: web-har-harvest
# input:  a HAR file you exported from your browser's DevTools (dropped into raw/)
# output: each matching response stored under _generated/fetch/ with redacted provenance; a table on stdout
# needs:  nothing (stdlib)
# usage:  python3 tools/recipes/web-har-harvest.py raw/<file>.har [--url-glob '*host/*'] [--all] [--json]

"""Rung T6 — the human handoff. You browsed; the agent harvests what you saw.

The one path that needs no rung above T2 and no `advanced_acquisition`: the agent
touches no network. You solved whatever the site asked, then DevTools → Network →
Export HAR, dropped into `raw/`. This recipe lifts the document responses out of
it into the same content-addressed store and provenance log every other rung
uses, so the capture you author afterwards records `capture-method: T6 har`.

**A HAR is a credential-bearing file.** It carries `Cookie`, `Set-Cookie` and
`Authorization` verbatim, plus your browser's exact fingerprint. So this recipe
keeps a short allowlist of response headers and nothing else, never records your
browser's request headers, never copies the HAR anywhere, and reminds you to delete
it once drained (the `raw/` contract). Conventions: AGENTS.md; the recipe never
writes into the graph.
"""

import argparse
import base64
import fnmatch
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import policy as _policy  # noqa: E402


def _load_webfetch():
    spec = importlib.util.spec_from_file_location("web_fetch", HERE / "web-fetch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ROOT = HERE.parent.parent
DOC_TYPES = ("text/html", "application/xhtml+xml", "application/json", "text/plain",
             "application/pdf", "application/xml", "text/xml")
# The only response headers that survive into provenance. Everything else in the HAR —
# cookies, auth, the browser's fingerprint — is discarded by construction.
KEEP_RESPONSE_HEADERS = ("content-type", "content-length", "date", "last-modified", "etag", "link")


def _body(entry: dict) -> tuple[bytes, str]:
    c = entry.get("response", {}).get("content", {}) or {}
    text, mime = c.get("text") or "", (c.get("mimeType") or "").split(";")[0].strip().lower()
    if c.get("encoding") == "base64":
        try:
            return base64.b64decode(text), mime
        except Exception:
            return b"", mime
    return text.encode("utf-8", errors="replace"), mime


def harvest_entry(wf, entry: dict, har_name: str, prov: str) -> dict | None:
    """One HAR entry → store + log row (redacted). None when nothing was stored."""
    req, res = entry.get("request", {}), entry.get("response", {})
    url, status = req.get("url", ""), int(res.get("status") or 0)
    body, mime = _body(entry)
    if not body:
        return None
    text = body.decode("utf-8", errors="replace")
    ext = wf.extract(text) if mime in ("text/html", "application/xhtml+xml") else wf._empty_ext()
    if not ext["markdown"] and mime not in ("application/pdf",) and mime.startswith(("text/", "application/json", "application/xml")):
        ext["markdown"] = text                     # JSON/plain/xml: the body is the text
        ext["chars"] = len(text)
    rec = {"_body": body, "content_sha256": hashlib.sha256(body).hexdigest(),
           "http_status": status, "content_length": len(body), "wire_length": len(body),
           "text": text}
    verdict, reason = wf.classify(rec, ext)
    kept = {h["name"].lower(): h["value"] for h in res.get("headers", [])
            if h.get("name", "").lower() in KEEP_RESPONSE_HEADERS}
    row = {"url_requested": url, "url_final": url, "http_status": status,
           "fetched_at": entry.get("startedDateTime"),        # when YOU fetched it
           "harvested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
           "media_type": mime, "content_length": len(body),
           "content_sha256": rec["content_sha256"], "headers_kept": kept,
           "verdict": verdict, "verdict_reason": reason, "rung": "T6",
           "tool": "web-har-harvest", "har": Path(har_name).name, "policy": prov,
           "user_agent": "your browser (not recorded)", "from_cache": 0,
           "extract_chars": ext["chars"], "kept_ratio": ext["kept_ratio"], "title": ext["title"]}
    row.update(wf.store_put(rec, ext))
    wf.log_append(row)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("har", type=Path, help="the exported .har file (keep it in raw/)")
    ap.add_argument("--url-glob", default="*", help="only entries whose URL matches (fnmatch)")
    ap.add_argument("--all", action="store_true",
                    help="every 2xx entry, not just document types (html/json/text/pdf/xml)")
    ap.add_argument("--json", action="store_true", help="emit the rows as JSON")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()

    cfg, prov = _policy.load(args.root)
    refusal = _policy.gate(cfg)
    if refusal:
        print(refusal, file=sys.stderr)
        return 2
    wf = _load_webfetch()
    wf.STORE = args.root / "_generated" / "fetch"

    try:
        har = json.loads(args.har.read_text(encoding="utf-8"))
        entries = har["log"]["entries"]
    except Exception as e:
        sys.exit(f"error: {args.har} is not a readable HAR (log.entries): {e}")

    rows, skipped = [], 0
    for e in entries:
        url = e.get("request", {}).get("url", "")
        status = int(e.get("response", {}).get("status") or 0)
        mime = (e.get("response", {}).get("content", {}) or {}).get("mimeType", "").split(";")[0].strip().lower()
        if not fnmatch.fnmatch(url, args.url_glob) or not (200 <= status < 300):
            skipped += 1
            continue
        if not args.all and not any(mime.startswith(t) for t in DOC_TYPES):
            skipped += 1
            continue
        row = harvest_entry(wf, e, str(args.har), prov)
        if row:
            rows.append(row)
        else:
            skipped += 1

    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
    else:
        print(f"# harvested {len(rows)} of {len(entries)} entries from {args.har.name} "
              f"({skipped} skipped: non-document, non-2xx, or outside --url-glob)")
        for r in rows:
            print(f"[{r['verdict']:>8}] {r['http_status']} {r['media_type']:<22} "
                  f"{r['content_length']:>8} B  {r['extract_chars']:>6} chars  {r['url_requested']}")
        if rows:
            print(f"\nStored under _generated/fetch/ as rung T6 (capture-method: T6 har).")
    print(f"\nreminder: {args.har} holds live session cookies and tokens. Author the capture, "
          f"then delete it — raw/ is drained, never kept.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
