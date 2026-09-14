#!/usr/bin/env python3
# recipe: web-fetch
# input:  a URL (http/https)
# output: extracted markdown on stdout; bytes + provenance under _generated/fetch/
# needs:  nothing — stdlib only. Rungs T0-T2; higher rungs are a deliberate decision.
# usage:  python3 tools/recipes/web-fetch.py <url> [--probe|--archive|--links] [--json] [--no-cache]

"""Fetch one URL politely, record how, and extract readable text.

Implements rungs T0-T2 of pages/web-acquisition-ladder.md. `--probe` does T0: it
reports a host's own declared access paths — robots.txt with its Content-Signal
and RSL License lines, sitemaps, feeds, llms.txt, JSON-LD, OpenAPI, security.txt
— so a session can ask "should I even be fetching this?" before it fetches.
`--archive` is T2: the Wayback CDX lookup that recovers pages a live host refuses.

Four things here are deliberate and easy to get wrong:

* **Nothing runs until consent is recorded.** `policy.py check` creates the policy file
  as a skeleton; this recipe refuses until `[consent].acknowledged` carries a date the
  user wrote after reading it. The agent never fills a user field.
* **The client presents as the most common browser and sends no contact.** The UA does
  not decide whether you are blocked — that happens at the TLS layer — so it is chosen
  for anonymity: a distinctive tool string is a cross-site tracking beacon, and
  researchers may have adversaries. `identity.user_agent = "declared"` opts in to being
  identifiable; `contact` is never sent by this recipe in any mode. A cookie jar you
  exported (`identity.cookies_file`) is sent only to its own sites and only under
  `advanced_acquisition` — that is rung T5, and the record says so.
* **robots.txt is parsed here, not by `urllib.robotparser`** (whose reference is the 1996
  Koster draft, lacking longest-match precedence, Crawl-delay, Content-Signal and
  License), and it is **recorded, not a gate**. RFC 9309 governs crawlers; this recipe
  fetches one URL and cannot crawl; a blanket `Disallow: /` read as a gate would forbid
  research outright. `Crawl-delay` is honoured and the verdict is logged on every fetch.
  The host's own answers — 403, 429, a challenge page — are the gate, and are respected.
* **Raw bytes are kept**, content-addressed, because extraction quality improves and a
  stored original makes re-extraction free. This extractor is a stdlib approximation,
  not trafilatura, and says so when it is unsure.

This recipe never writes into the graph (tools/recipes/README.md). Conventions:
AGENTS.md.
"""

import argparse
import gzip
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import policy as _policy  # noqa: E402  (sibling recipe module, stdlib-only)

ROOT = Path(__file__).resolve().parent.parent.parent
STORE = ROOT / "_generated" / "fetch"     # rebound from --root in main()
ROBOTS_MAX = 500_000           # RFC 9309 parse cap
TIMEOUT = 30
VERSION = "web-fetch/0.1"

# Interstitial fingerprints. Body markers are weaker than the CSP/header signals,
# so both are checked and the reason is recorded.
BLOCK_MARKERS = ("just a moment", "checking your browser", "cf-browser-verification",
                 "enable javascript and cookies to continue", "attention required",
                 "session verification", "px-captcha", "/cdn-cgi/challenge-platform")
THIN_MARKERS = ("accept cookies", "sign in", "loading…", "loading...", "enable javascript")
DROP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "form", "noscript",
             "svg", "iframe", "template", "button", "select"}
BLOCK_TAGS = {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5", "h6",
              "blockquote", "pre", "td", "figcaption", "dd", "dt"}
HEADING = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}
# A tiny English stopword set: justext's insight is that boilerplate is
# stopword-poor and link-dense, and that heuristic reaches ~0.86 F1 where naive
# tag-stripping scores below raw HTML.
STOP = set("the of and to a in is it you that he was for on are with as i his they be at "
           "this have from or one had by word but not what all were we when your can said "
           "there use an each which she do how their if will up other about out many then "
           "them these so some her would make like him into time has look two more write go "
           "see number no way could people my than first been call who its now find long "
           "down day did get come made may part is are".split())


# ----------------------------------------------------------------- http

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _decode_body(raw: bytes, enc: str) -> bytes:
    enc = (enc or "").lower().strip()
    try:
        if enc == "gzip":
            return gzip.decompress(raw)
        if enc == "deflate":
            try:
                return zlib.decompress(raw)
            except zlib.error:
                return zlib.decompress(raw, -zlib.MAX_WBITS)
        if enc == "zstd":
            from compression import zstd          # stdlib since 3.14
            return zstd.decompress(raw)
    except Exception:
        return raw                                 # keep the bytes; note it upstream
    return raw


def _charset(headers, body: bytes) -> tuple[str, str]:
    """Return (declared, used). Servers lie, so the declaration is a hint."""
    declared = ""
    ctype = headers.get("Content-Type", "")
    m = re.search(r"charset=([\w\-]+)", ctype, re.I)
    if m:
        declared = m.group(1).lower()
    if not declared:
        m = re.search(rb'charset=["\']?([\w\-]+)', body[:2048], re.I)
        if m:
            declared = m.group(1).decode("ascii", "ignore").lower()
    for cand in [declared, "utf-8", "cp1252"]:
        if not cand:
            continue
        try:
            body.decode(cand)
            return declared, cand
        except (UnicodeDecodeError, LookupError):
            continue
    return declared, "utf-8/replace"


def _cookies_sent(req) -> int:
    """How many cookies the jar attached — a count for the record, never the header."""
    v = req.get_header("Cookie")
    return len([c for c in v.split(";") if c.strip()]) if v else 0


def fetch(url: str, cfg: dict, extra_headers: dict | None = None, jar=None) -> dict:
    """One HTTP GET. Never raises on HTTP status; returns a record."""
    # Advertise only what stdlib can decode — never `br`, which needs a wheel.
    hdrs = {"User-Agent": _policy.user_agent(cfg),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, zstd"}
    hdrs.update(extra_headers or {})
    rec = {"url_requested": url, "fetched_at": _now(), "fetcher": VERSION,
           "user_agent": hdrs["User-Agent"]}
    req = urllib.request.Request(url, headers=hdrs)
    opener = (urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
              if jar is not None else urllib.request.build_opener())
    t0 = time.monotonic()
    try:
        with opener.open(req, timeout=TIMEOUT) as r:
            raw = r.read(cfg["budget"]["max_bytes_per_fetch"] + 1)
            rec.update(http_status=r.status, url_final=r.url,
                       headers={k.lower(): v for k, v in r.headers.items()})
    except urllib.error.HTTPError as e:
        raw = e.read(cfg["budget"]["max_bytes_per_fetch"] + 1)
        rec.update(http_status=e.code, url_final=e.url,
                   headers={k.lower(): v for k, v in e.headers.items()},
                   error_kind="http")
    except Exception as e:                                    # dns/tls/timeout
        rec.update(http_status=None, error_kind=type(e).__name__.lower(),
                   error_detail=str(e)[:300], elapsed_ms=int((time.monotonic() - t0) * 1000),
                   cookies_sent=_cookies_sent(req))
        return rec
    rec["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
    rec["cookies_sent"] = _cookies_sent(req)
    h = rec["headers"]
    rec["wire_length"] = len(raw)          # bytes as received, BEFORE decompression
    body = _decode_body(raw, h.get("content-encoding", ""))
    declared, used = _charset(h, body)
    rec.update(content_length=len(body), declared_length=int(h.get("content-length") or 0) or None,
               content_encoding=h.get("content-encoding"), media_type=(h.get("content-type") or "").split(";")[0].strip().lower(),
               charset_declared=declared, charset_used=used,
               etag=h.get("etag"), last_modified=h.get("last-modified"),
               content_sha256=hashlib.sha256(body).hexdigest())
    rec["_body"] = body
    rec["text"] = body.decode(used.split("/")[0], errors="replace")
    return rec


# ----------------------------------------------------------------- robots (RFC 9309)

def _match(pattern: str, path: str) -> int:
    """Return match length if `pattern` matches `path`, else -1. Supports * and $."""
    rx = "".join(".*" if c == "*" else (r"\Z" if c == "$" else re.escape(c)) for c in pattern)
    m = re.match(rx, path)
    return len(pattern) if m else -1


def parse_robots(text: str, agent: str) -> dict:
    """RFC 9309 with the de-facto extensions that matter, and the consent signals.

    Longest-match precedence (Allow wins ties) — the thing urllib.robotparser gets
    wrong. Sitemap/Content-Signal/License are file-level, independent of groups.
    """
    out = {"sitemaps": [], "content_signal": None, "license": None,
           "crawl_delay": None, "rules": [], "groups_seen": [], "matched_agent": None}
    groups, cur, star, mine = [], None, [], []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "user-agent":
            if cur is None or cur["started"]:
                cur = {"agents": [], "rules": [], "delay": None, "started": False}
                groups.append(cur)
            cur["agents"].append(value.lower())
            out["groups_seen"].append(value.lower())
        elif field in ("allow", "disallow") and cur is not None:
            cur["started"] = True
            cur["rules"].append((field, value))
        elif field == "crawl-delay" and cur is not None:
            cur["started"] = True
            try:
                cur["delay"] = float(value)
            except ValueError:
                pass
        elif field == "sitemap":
            out["sitemaps"].append(value)
        elif field == "content-signal":
            out["content_signal"] = value
        elif field == "license":
            out["license"] = value
    a = agent.lower()
    for g in groups:
        if any(x != "*" and x in a for x in g["agents"]):
            mine.append(g)
        elif "*" in g["agents"]:
            star.append(g)
    chosen = mine or star
    if chosen:
        out["matched_agent"] = "specific" if mine else "*"
        for g in chosen:
            out["rules"] += g["rules"]
            if g["delay"] is not None:
                out["crawl_delay"] = g["delay"]
    return out


def robots_allows(parsed: dict, path: str) -> bool:
    best_len, best_allow = -1, True
    for field, pattern in parsed["rules"]:
        if pattern == "" and field == "disallow":
            continue                                   # empty Disallow == allow all
        n = _match(pattern, path)
        if n > best_len or (n == best_len and field == "allow"):
            best_len, best_allow = n, (field == "allow")
    return best_allow


def robots_for(url: str, cfg: dict) -> dict:
    p = urllib.parse.urlsplit(url)
    r = fetch(f"{p.scheme}://{p.netloc}/robots.txt", cfg)
    st = r.get("http_status")
    if st is None or 500 <= st < 600:
        return {"verdict": "disallow-all", "reason": f"robots {st or 'unreachable'} (RFC 9309: 5xx ⇒ disallow)",
                "parsed": None}
    # RFC 9309 says 4xx ⇒ allow-all, but that rule assumes "no robots.txt exists".
    # A 401/403/418/429 is the host refusing *us*, and reading that as blanket
    # permission is exactly backwards — so those are treated as a block instead.
    if st in (401, 403, 418, 429):
        return {"verdict": "disallow-all",
                "reason": f"robots.txt itself returned {st} — the host is refusing this "
                          f"client, which is a block, not an absent robots file",
                "parsed": None}
    if st >= 400:
        return {"verdict": "allow-all", "reason": f"robots {st} (RFC 9309: 4xx ⇒ allow)", "parsed": None}
    parsed = parse_robots(r["text"][:ROBOTS_MAX], _policy.user_agent(cfg))
    allowed = robots_allows(parsed, p.path or "/")
    return {"verdict": "allow" if allowed else "disallow", "reason": "robots.txt", "parsed": parsed}


# ----------------------------------------------------------------- extraction

class _Doc(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.jsonld, self.links, self.title = [], [], [], ""
        self.anchors = []                       # every <a href>, for links_from()
        self._skip, self._buf, self._tag, self._a, self._alen = 0, [], None, 0, 0
        self._ld, self._in_title = False, False
        self._href, self._atext, self._a_chrome = None, [], False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "script" and (d.get("type") or "").lower() == "application/ld+json":
            self._ld = True
            return
        if tag in DROP_TAGS:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "a":
            self._a += 1
            self._href, self._atext, self._a_chrome = d.get("href"), [], self._skip > 0
        elif tag in BLOCK_TAGS:
            self._flush()
            self._tag = tag
        elif tag == "link":
            self.links.append(d)

    def handle_endtag(self, tag):
        if tag == "script" and self._ld:
            self._ld = False
            return
        if tag in DROP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag == "title":
            self._in_title = False
        elif tag == "a":
            self._a = max(0, self._a - 1)
            if self._href:
                self.anchors.append({"href": self._href, "chrome": self._a_chrome,
                                     "text": re.sub(r"\s+", " ", "".join(self._atext)).strip()[:120]})
            self._href, self._atext = None, []
        elif tag in BLOCK_TAGS:
            self._flush()

    def handle_data(self, data):
        if self._ld:
            try:
                self.jsonld.append(json.loads(data))
            except Exception:
                pass
            return
        if self._in_title:
            self.title += data.strip()
            return
        if self._a:
            self._atext.append(data)            # anchor text is kept even inside chrome
        if self._skip or not data.strip():
            return
        self._buf.append(data)
        if self._a:
            self._alen += len(data.strip())

    def _flush(self):
        text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        if text:
            self.blocks.append({"tag": self._tag or "p", "text": text, "linked": self._alen})
        self._buf, self._alen, self._tag = [], 0, None

    def close(self):
        super().close()
        self._flush()


def extract(page_html: str) -> dict:
    """Block classification by link density + stopword ratio (justext's insight).

    A naive tag-stripper scores below *raw HTML* on extraction benchmarks; the
    density heuristic is what makes the difference. Still well short of
    trafilatura — hence `confidence`.
    """
    d = _Doc()
    try:
        d.feed(page_html)
        d.close()
    except Exception:
        pass
    kept = []
    for b in d.blocks:
        t, n = b["text"], len(b["text"])
        link_density = b["linked"] / n if n else 1.0
        words = re.findall(r"[a-zA-Z']+", t.lower())
        stop_ratio = (sum(w in STOP for w in words) / len(words)) if words else 0.0
        good = (n >= 180 and link_density < 0.4) or \
               (n >= 60 and link_density < 0.25 and stop_ratio >= 0.20) or \
               b["tag"] in HEADING
        if good:
            kept.append(b)
    md = []
    for b in kept:
        if b["tag"] in HEADING:
            md.append(f"{HEADING[b['tag']]} {b['text']}")
        elif b["tag"] == "li":
            md.append(f"- {b['text']}")
        elif b["tag"] == "blockquote":
            md.append(f"> {b['text']}")
        else:
            md.append(b["text"])
    text = "\n\n".join(md).strip()
    total = sum(len(b["text"]) for b in d.blocks) or 1
    return {"title": html.unescape(d.title).strip(), "markdown": text,
            "chars": len(text), "kept_ratio": round(sum(len(b['text']) for b in kept) / total, 3),
            "jsonld": d.jsonld, "links": d.links, "anchors": d.anchors}


def _empty_ext() -> dict:
    return {"title": "", "markdown": "", "chars": 0, "kept_ratio": 0.0,
            "jsonld": [], "links": [], "anchors": []}


def links_from(ext: dict, base_url: str) -> list[dict]:
    """Resolve, dedupe and label a page's outbound links so an agent can decide which
    references deserve a targeted pull (web-worklist.py). Never follows anything."""
    bp = urllib.parse.urlsplit(base_url)
    site = bp.netloc.lower().removeprefix("www.")
    seen, out = set(), []
    for a in ext.get("anchors", []):
        href = (a.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            continue
        u, _ = urllib.parse.urldefrag(urllib.parse.urljoin(base_url, href))
        p = urllib.parse.urlsplit(u)
        if p.scheme not in ("http", "https") or u in seen:
            continue
        seen.add(u)
        host = p.netloc.lower().removeprefix("www.")
        low = u.lower()
        kind = ("pdf" if low.endswith(".pdf") else "doi" if "doi.org/" in low
                else "arxiv" if "arxiv.org/" in low
                else "feed" if low.endswith((".xml", ".rss", "/feed", "/feed/", ".atom")) else "page")
        out.append({"url": u, "text": a.get("text", ""), "kind": kind,
                    "same_site": host == site or host.endswith("." + site),
                    "chrome": bool(a.get("chrome"))})
    return out


def classify(rec: dict, ext: dict) -> tuple[str, str]:
    """(verdict, reason) — is this real content, a bot wall, or a JS shell?"""
    st, n = rec.get("http_status"), rec.get("content_length") or 0
    low = (rec.get("text") or "")[:20000].lower()
    if st == 200 and n == 0:
        return "empty", "HTTP 200 with a zero-length body — often UA rejection"
    if any(m in low for m in BLOCK_MARKERS):
        return "interstitial", "bot-challenge marker in body"
    if st == 401:
        return "blocked", ("HTTP 401 — authentication required. If you hold an account for this "
                           "site, that is rung T5 (your own logged-in session); otherwise stop")
    if st in (403, 429, 503):
        return "blocked", f"HTTP {st} — treat as an answer, not an obstacle"
    # Content-Length describes the ON-THE-WIRE body, so it must be compared against
    # the pre-decompression byte count — comparing it to the decoded size flags every
    # gzipped page as truncated.
    wire = rec.get("wire_length")
    if rec.get("declared_length") and wire is not None \
            and abs(rec["declared_length"] - wire) > 512:
        return "truncated", (f"Content-Length {rec['declared_length']} != {wire} bytes "
                             f"received on the wire")
    if st == 200 and ext["chars"] < 500 and n > 50_000:
        return "js-shell", f"{n} bytes of HTML yielded {ext['chars']} chars of text"
    if st == 200 and ext["chars"] < 200 and ext["markdown"].strip().lower() in THIN_MARKERS:
        return "js-shell", "extracted text is a cookie/sign-in stub"
    if st and 200 <= st < 300:
        return "ok", ""
    return "error", f"unexpected HTTP {st}"


# ----------------------------------------------------------------- store

def store_put(rec: dict, ext: dict) -> dict:
    sha = rec["content_sha256"]
    blob = STORE / "blobs" / sha[:2] / sha[2:4] / f"{sha}.gz"
    blob.parent.mkdir(parents=True, exist_ok=True)
    if not blob.exists():
        tmp = blob.with_suffix(".gz.tmp")
        tmp.write_bytes(gzip.compress(rec["_body"]))
        tmp.replace(blob)                                     # atomic, same dir
    txt = STORE / "extract" / f"{sha}.md"
    txt.parent.mkdir(parents=True, exist_ok=True)
    txt.write_text(ext["markdown"], encoding="utf-8")         # uncompressed: greppable
    return {"blob_ref": str(blob.relative_to(STORE)), "extract_ref": str(txt.relative_to(STORE))}


def log_append(row: dict) -> None:
    p = STORE / "fetch.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")


def log_lookup(url: str) -> dict | None:
    """Most recent successful row for this URL — supplies the conditional validators."""
    p = STORE / "fetch.jsonl"
    if not p.is_file():
        return None
    hit = None
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("url_requested") == url and r.get("verdict") == "ok":
            hit = r
    return hit


def rate_limit(host: str, delay: float) -> None:
    stamp = STORE / "hosts" / f"{re.sub(r'[^a-z0-9.-]', '_', host.lower())}.stamp"
    stamp.parent.mkdir(parents=True, exist_ok=True)
    if stamp.exists():
        wait = delay - (time.time() - stamp.stat().st_mtime)
        if wait > 0:
            time.sleep(wait)
    stamp.touch()


# ----------------------------------------------------------------- T0 probe / T2 archive

PROBE_PATHS = ["/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml", "/llms.txt",
               "/llms-full.txt", "/.well-known/security.txt", "/.well-known/tdmrep.json",
               "/openapi.json", "/v1/openapi.json", "/feed", "/rss.xml", "/index.xml"]


def probe(url: str, cfg: dict) -> dict:
    p = urllib.parse.urlsplit(url)
    base = f"{p.scheme}://{p.netloc}"
    rob = robots_for(base + "/", cfg)
    par = rob["parsed"] or {}
    found = []
    for path in PROBE_PATHS:
        rate_limit(p.netloc, cfg["budget"]["min_delay_seconds"])
        r = fetch(base + path, cfg)
        if r.get("http_status") == 200 and (r.get("content_length") or 0) > 0:
            found.append({"path": path, "bytes": r["content_length"], "type": r.get("media_type")})
    page = fetch(url, cfg)
    ext = extract(page.get("text", "")) if page.get("text") else {"jsonld": [], "links": []}
    feeds = [l.get("href") for l in ext.get("links", [])
             if "alternate" in (l.get("rel") or "").lower()
             and any(t in (l.get("type") or "") for t in ("rss", "atom", "feed+json"))]
    return {"url": url, "robots": {"verdict": rob["verdict"], "reason": rob["reason"],
                                   "crawl_delay": par.get("crawl_delay"),
                                   "content_signal": par.get("content_signal"),
                                   "license_rsl": par.get("license"),
                                   "sitemaps": par.get("sitemaps", [])},
            "well_known": found, "feeds_autodiscovered": feeds,
            "jsonld_blocks": len(ext.get("jsonld", []))}


CDX_DELAY = 2.5      # ~0.4 req/s: the Wayback client's own documented ceiling


def archive_lookup(url: str, cfg: dict) -> dict:
    """T2 — Wayback CDX.

    Two behaviours worth encoding rather than rediscovering. The *availability*
    API 429s after roughly one request and stays there for minutes, so it is never
    used. And CDX signals over-rate by stalling the connection or returning 5xx
    rather than a clean 429 — so a failure here means "slow down", not "no
    snapshots", and must not be reported as the latter.
    """
    q = urllib.parse.urlencode({"url": url, "output": "json", "limit": "-3",
                                "filter": "statuscode:200", "fl": "timestamp,original,length"})
    target = f"https://web.archive.org/cdx/search/cdx?{q}"
    last = None
    for attempt in range(3):
        rate_limit("web.archive.org", CDX_DELAY * (attempt + 1))
        r = fetch(target, cfg)
        last = r
        st = r.get("http_status")
        if st == 200:
            try:
                rows = json.loads(r["text"])
            except Exception:
                return {"snapshots": [], "note": "CDX returned a non-JSON body"}
            snaps = [{"timestamp": ts, "url": f"https://web.archive.org/web/{ts}/{o}",
                      "length": ln} for ts, o, ln in rows[1:]] if len(rows) > 1 else []
            return {"snapshots": snaps}
        if st is not None and st < 500:
            break                                  # a real answer, not throttling
    return {"snapshots": [],
            "note": f"CDX throttled or unreachable ({last.get('http_status') or last.get('error_kind')}) "
                    f"after 3 attempts — this means slow down, not that no snapshot exists"}


# ----------------------------------------------------------------- main

def perform(url: str, cfg: dict, prov: str, root: Path, *, use_cache: bool = True,
            extra: dict | None = None) -> tuple[dict, dict, list[str]]:
    """The whole fetch pipeline for one URL, without printing: (row, ext, notes).

    `notes` are human-facing lines the caller may show. web-fetch's CLI and
    web-worklist's targeted pulls both call this, so there is exactly one
    implementation of politeness, provenance and classification.
    """
    notes: list[str] = []
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https"):
        raise ValueError(f"only http/https URLs (got {p.scheme!r})")
    jar, jar_status = _policy.cookie_jar(cfg, root)
    if jar is None and "present" in jar_status:
        notes.append(f"note: {jar_status}.")
    rob = robots_for(url, cfg)
    par = rob["parsed"] or {}
    disallowed = rob["verdict"] in ("disallow", "disallow-all")
    if disallowed:
        notes.append(f"note: robots.txt disallows this path for crawlers ({rob['reason']}). This is "
                     f"a single user-directed read, not a crawl — proceeding; the verdict is "
                     f"recorded. The host's own response is what decides.")
    delay = max(cfg["budget"]["min_delay_seconds"], par.get("crawl_delay") or 0)
    rate_limit(p.netloc, delay)

    prev = log_lookup(url) if use_cache else None
    cond = {}
    if prev:
        if prev.get("etag"):
            cond["If-None-Match"] = prev["etag"]
        if prev.get("last_modified"):
            cond["If-Modified-Since"] = prev["last_modified"]   # replay verbatim
    rec = fetch(url, cfg, cond, jar)

    if rec.get("http_status") == 304 and prev:
        cached = STORE / prev["extract_ref"] if prev.get("extract_ref") else None
        row = dict(prev, fetched_at=_now(), from_cache=1, http_status=304, policy=prov)
        row.pop("_body", None)
        if extra:
            row.update(extra)
        log_append(row)
        ext = _empty_ext()
        ext.update(title=prev.get("title", ""), kept_ratio=prev.get("kept_ratio", 0.0),
                   markdown=cached.read_text(encoding="utf-8") if cached and cached.is_file() else "")
        ext["chars"] = len(ext["markdown"])
        return row, ext, notes

    ext = extract(rec.get("text", "")) if rec.get("text") else _empty_ext()
    verdict, reason = classify(rec, ext)
    row = {k: v for k, v in rec.items() if not k.startswith("_") and k not in ("text", "headers")}
    row.update(verdict=verdict, verdict_reason=reason, policy=prov,
               rung="T5" if rec.get("cookies_sent") else "T1", cookies=jar_status,
               extract_chars=ext["chars"], kept_ratio=ext["kept_ratio"],
               title=ext["title"], from_cache=0,
               robots_verdict=rob["verdict"], robots_reason=rob["reason"],
               robots_action="proceeded-single-read" if disallowed else "allowed",
               content_signal=par.get("content_signal"), license_rsl=par.get("license"))
    if extra:
        row.update(extra)
    if rec.get("_body") is not None:
        row.update(store_put(rec, ext))
    log_append(row)
    return row, ext, notes


NEXT_RUNG = {
    "T1": "T3+ — a deliberate, recorded decision, not an automatic escalation",
    "T3": "T4 (a real browser executing the page's JavaScript)",
    "T4": "T5 (your own logged-in session via cookies.txt) or T6 (browse it yourself, export a HAR)",
    "T5": "T6 (browse it yourself, export a HAR)",
    "T6": "none — this was the human handoff; the host has answered",
}


def explain_failure(row: dict, cfg: dict) -> list[str]:
    """Stderr lines for a non-ok verdict: what happened, where the archive has it, and
    which rung would come next — as a decision, never an automatic escalation."""
    verdict, reason, url = row["verdict"], row.get("verdict_reason", ""), row["url_requested"]
    head = f"error: {reason}" if verdict == "error" else f"error: {verdict} — {reason}"
    note = [head, f"  {url}"]
    if verdict in ("interstitial", "blocked", "js-shell"):
        arch = archive_lookup(url, cfg)
        if arch["snapshots"]:
            note.append(f"  Rung T2 has it: {arch['snapshots'][-1]['url']}")
        cur = row.get("rung", "T1")
        if verdict == "js-shell" and cur in ("T1", "T3"):
            nxt = "T4 (a real browser executing the page's JavaScript)"
        else:
            nxt = NEXT_RUNG.get(cur, NEXT_RUNG["T1"])
        note.append(f"  Next rung would be {nxt}; ladder: pages/web-acquisition-ladder.md")
    note.append("  Recorded in _generated/fetch/fetch.jsonl. Not treated as content.")
    return note


def run(url: str, cfg: dict, prov: str, args) -> int:
    try:
        row, ext, notes = perform(url, cfg, prov, args.root,
                                  use_cache=not (args.no_cache or args.links))
    except ValueError as e:
        sys.exit(f"error: {e}")
    for n in notes:
        print(n, file=sys.stderr)
    if row["verdict"] != "ok":
        print("\n".join(explain_failure(row, cfg)), file=sys.stderr)
        return 4
    links = links_from(ext, row.get("url_final") or url)
    if args.json:
        print(json.dumps({**row, "jsonld": ext.get("jsonld", []), "links": links},
                         indent=2, sort_keys=True))
    elif args.links:
        print(f"# {len(links)} links on {url} — choose which deserve a targeted pull, and say why")
        for l in links:
            where = "same" if l["same_site"] else "ext "
            chrome = " (nav/footer)" if l["chrome"] else ""
            print(f"[{where}] {l['kind']:5} {l['url']}  — {l['text'] or '(no text)'}{chrome}")
    else:
        print(ext["markdown"])
        # A genuinely short page is not a failure; a page whose text was mostly
        # discarded is. The js-shell classifier already catches "big HTML, no text".
        if ext["kept_ratio"] < 0.15 and ext["chars"] < 400:
            print(f"\nwarning: low-confidence extraction ({ext['chars']} chars, "
                  f"kept {ext['kept_ratio']:.0%} of block text). The stdlib extractor is an "
                  f"approximation; raw bytes are kept at {row.get('blob_ref')} so re-extraction "
                  f"with a better tool is free.", file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--probe", action="store_true",
                    help="rung T0: report the host's declared access paths, don't fetch content")
    ap.add_argument("--archive", action="store_true",
                    help="rung T2: look the URL up in the Wayback CDX index")
    ap.add_argument("--links", action="store_true",
                    help="list the page's outbound links (for web-worklist) instead of its text")
    ap.add_argument("--json", action="store_true", help="emit the provenance record as JSON")
    ap.add_argument("--no-cache", action="store_true", help="skip conditional revalidation")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()
    global STORE
    STORE = args.root / "_generated" / "fetch"
    cfg, prov = _policy.load(args.root)
    refusal = _policy.gate(cfg)
    if refusal:
        print(refusal, file=sys.stderr)
        return 2
    if args.probe:
        print(json.dumps(probe(args.url, cfg), indent=2))
        return 0
    if args.archive:
        print(json.dumps(archive_lookup(args.url, cfg), indent=2))
        return 0
    return run(args.url, cfg, prov, args)


if __name__ == "__main__":
    sys.exit(main())
