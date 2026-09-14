#!/usr/bin/env -S uv run --quiet --script
# recipe: web-impersonate
# input:  a URL that answers 403 to an honest client because of TLS fingerprinting (rung T3)
# output: extracted markdown on stdout; bytes + provenance (rung T3) under _generated/fetch/
# needs:  uv — resolves curl_cffi from the inline block on first run; requires advanced_acquisition
# usage:  uv run tools/recipes/web-impersonate.py <url> [--json] [--links] [--target chrome]

# /// script
# requires-python = ">=3.11"
# dependencies = ["curl_cffi>=0.13"]
# ///
"""Rung T3 — present a browser's TLS handshake, not just its User-Agent string.

Changing the UA is provably useless against a fingerprinting WAF: the block is
decided from the TLS ClientHello and HTTP/2 settings. `curl_cffi` replays a real
browser's handshake, and sets the matching UA itself so the fingerprint stays
consistent — this is the one recipe where the UA is not the policy string, and
the record says so.

It is a technical countermeasure against a technical measure, which is why it
sits behind `advanced_acquisition`, is never an automatic escalation, and is for
content you are plainly entitled to read. Everything else is shared with
web-fetch: robots recorded, per-host pacing, the same classifier (a bot wall is
still never captured as content), the same store and log. Your cookie jar, if
present, is sent only to this site's own domain. Conventions: AGENTS.md; never
writes into the graph.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import policy as _policy  # noqa: E402

ROOT = HERE.parent.parent


def _load_webfetch():
    spec = importlib.util.spec_from_file_location("web_fetch", HERE / "web-fetch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _need():
    try:
        import curl_cffi
        from curl_cffi import requests as cffi_requests
        return curl_cffi, cffi_requests
    except ImportError:
        sys.exit("error: curl_cffi unavailable. Run this recipe with uv:\n"
                 "    uv run tools/recipes/web-impersonate.py <url>\n"
                 "  or use the venv fallback in tools/recipes/README.md (packages are listed in "
                 "this file's `# /// script` block). (Tool policy: degrade loudly.)")


def _domain_cookies(jar, host: str) -> dict:
    if jar is None:
        return {}
    host = host.lower()
    out = {}
    for c in jar:
        d = c.domain.lower().lstrip(".")
        if host == d or host.endswith("." + d):
            out[c.name] = c.value
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--target", default="chrome",
                    help="browser to impersonate (curl_cffi alias; `chrome` tracks the newest)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--links", action="store_true", help="list outbound links instead of text")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()

    cfg, prov = _policy.load(args.root)
    refusal = _policy.gate(cfg)
    if refusal:
        print(refusal, file=sys.stderr)
        return 2
    if not cfg["advanced_acquisition"]:
        print("error: rung T3 is above the cautious ceiling (T2). It impersonates a browser's TLS "
              "handshake to get past a fingerprinting block — a deliberate decision, never an "
              "automatic one. Set `advanced_acquisition = true` in "
              ".personal-shared/acquisition-policy.toml if that is right for your context.",
              file=sys.stderr)
        return 3
    curl_cffi, cffi_requests = _need()
    wf = _load_webfetch()
    wf.STORE = args.root / "_generated" / "fetch"

    url = args.url
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https"):
        sys.exit(f"error: only http/https URLs (got {p.scheme!r}).")
    print("note: rung T3 — impersonating a browser's TLS handshake. For content you are plainly "
          "entitled to read; recorded as T3.", file=sys.stderr)

    rob = wf.robots_for(url, cfg)
    par = rob["parsed"] or {}
    disallowed = rob["verdict"] in ("disallow", "disallow-all")
    if disallowed:
        print(f"note: robots.txt disallows this path for crawlers ({rob['reason']}); single "
              f"user-directed read — proceeding, recorded.", file=sys.stderr)
    wf.rate_limit(p.netloc, max(cfg["budget"]["min_delay_seconds"], par.get("crawl_delay") or 0))
    jar, jar_status = _policy.cookie_jar(cfg, args.root)
    cookies = _domain_cookies(jar, p.netloc)

    t0 = time.monotonic()
    rec = {"url_requested": url, "fetched_at": wf._now(), "fetcher": "web-impersonate/0.1",
           "user_agent": f"curl_cffi impersonate={args.target} (browser-consistent UA set by curl_cffi)"}
    try:
        r = cffi_requests.get(url, impersonate=args.target, cookies=cookies or None, timeout=30,
                              allow_redirects=True, headers={"Accept-Language": "en-US,en;q=0.9"},
                              max_recv_speed=cfg["budget"]["max_bytes_per_fetch"])
    except Exception as e:
        rec.update(http_status=None, error_kind=type(e).__name__.lower(), error_detail=str(e)[:300],
                   elapsed_ms=int((time.monotonic() - t0) * 1000))
        print(f"error: {rec['error_kind']} — {rec['error_detail']}", file=sys.stderr)
        wf.log_append({**rec, "verdict": "error", "rung": "T3", "policy": prov})
        return 4
    body = r.content[: cfg["budget"]["max_bytes_per_fetch"]]
    h = {k.lower(): v for k, v in r.headers.items()}
    rec.update(http_status=r.status_code, url_final=str(r.url),
               elapsed_ms=int((time.monotonic() - t0) * 1000),
               content_length=len(body), wire_length=None,      # curl decompressed; no wire count
               media_type=(h.get("content-type") or "").split(";")[0].strip().lower(),
               etag=h.get("etag"), last_modified=h.get("last-modified"),
               content_sha256=hashlib.sha256(body).hexdigest(), cookies_sent=len(cookies),
               declared_length=None)
    rec["_body"] = body
    rec["text"] = r.text if r.text else body.decode("utf-8", errors="replace")

    ext = wf.extract(rec["text"]) if rec["text"] else wf._empty_ext()
    verdict, reason = wf.classify(rec, ext)
    row = {k: v for k, v in rec.items() if not k.startswith("_") and k not in ("text",)}
    row.update(verdict=verdict, verdict_reason=reason, policy=prov, rung="T3",
               tool=f"curl_cffi/{getattr(curl_cffi, '__version__', '?')}", impersonate=args.target,
               cookies=jar_status, extract_chars=ext["chars"], kept_ratio=ext["kept_ratio"],
               title=ext["title"], from_cache=0, robots_verdict=rob["verdict"],
               robots_reason=rob["reason"], robots_action="proceeded-single-read" if disallowed else "allowed",
               content_signal=par.get("content_signal"), license_rsl=par.get("license"))
    row.update(wf.store_put(rec, ext))
    wf.log_append(row)

    if verdict != "ok":
        print("\n".join(wf.explain_failure(row, cfg)), file=sys.stderr)
        return 4
    links = wf.links_from(ext, row.get("url_final") or url)
    if args.json:
        print(json.dumps({**row, "jsonld": ext.get("jsonld", []), "links": links}, indent=2, sort_keys=True))
    elif args.links:
        for l in links:
            print(f"[{'same' if l['same_site'] else 'ext '}] {l['kind']:5} {l['url']}  — {l['text'] or '(no text)'}")
    else:
        print(ext["markdown"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
