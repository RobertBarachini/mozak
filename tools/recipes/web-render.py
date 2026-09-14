#!/usr/bin/env -S uv run --quiet --script
# recipe: web-render
# input:  a URL whose content only exists after JavaScript runs (rung T4; T5 when your cookie jar is used)
# output: rendered DOM extracted to markdown on stdout; bytes/screenshot/HAR + provenance under _generated/fetch/
# needs:  uv (resolves playwright); Chromium once via `--install` (user-level, ~150 MB); advanced_acquisition
# usage:  uv run tools/recipes/web-render.py <url> [--json|--links] [--screenshot] [--har] [--headful] | --install

# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.62,<2"]
# ///
"""Rung T4/T5 — a real browser that belongs to the repo, not to you.

The sandbox contract (pages/web-acquisition-ladder.md), enforced here rather than
described:

* **Playwright's own Chromium**, never your daily browser, never the snap — the
  full build in new-headless mode (`channel="chromium"`), not the stripped shell.
  The User-Agent keeps the browser's real version and platform, with **one edit**:
  headless Chromium announces itself as `HeadlessChrome`, a distinctive automation
  marker and therefore a cross-site correlator, and that word is replaced by
  `Chrome`. The second and last edit is the same kind: Playwright launches with
  `--enable-automation`, which sets `navigator.webdriver = true` — a label saying
  "this session is tool-driven" (the modern form of the old chromedriver `$cdc_`
  tell, which does not exist here because there is no chromedriver). That flag is
  dropped and `--disable-blink-features=AutomationControlled` added, so the flag
  reads `false`. Nothing else is fabricated — engine, version, platform, canvas,
  WebGL and plugins are whatever this browser really has; there is no fingerprint
  injection and no CDP patching, because presenting as *this* browser is the point.
  The row records both edits and the `navigator.webdriver` value the page saw.
* **A fresh profile in a temporary directory, every run, destroyed on exit** —
  in a `finally`, so a crash cannot leave one behind. No history, cache,
  localStorage or service worker survives between runs; nothing accumulates that
  could correlate one research topic with the next.
* **Seeded from your cookie jar and from nothing else**, and only cookies for
  this site's own domain. No `storage_state` is ever written back.
* **Third-party requests are blocked by default** except what a page needs to
  render (scripts, styles, fonts): no XHR, beacons, pings, images, media or
  iframes to other hosts, so a render does not fan out to trackers.
  `--allow-third-party` turns that off for a page that will not render otherwise.
* **Only the rendered outputs persist**, under `_generated/fetch/`: HTML,
  extract, optional screenshot, optional HAR — and the HAR is stripped of
  `Cookie`, `Set-Cookie` and `Authorization` before it is written.

Requires `advanced_acquisition` (T4 is above the cautious ceiling) and consent.
Shares robots recording, pacing, classifier, store and log with web-fetch.
Conventions: AGENTS.md; never writes into the graph.
"""

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import policy as _policy  # noqa: E402

ROOT = HERE.parent.parent
RENDER_ONLY_TYPES = ("script", "stylesheet", "font")
# Playwright adds --enable-automation by default; that alone flips navigator.webdriver.
DROP_DEFAULT_ARGS = ["--enable-automation"]
HYGIENE = ["--disable-blink-features=AutomationControlled",
           "--disable-background-networking", "--disable-component-update",
           "--disable-default-apps", "--disable-extensions", "--disable-sync",
           "--no-first-run", "--no-default-browser-check", "--metrics-recording-only",
           "--disable-breakpad", "--disable-domain-reliability",
           "--disable-client-side-phishing-detection",
           "--disable-features=Translate,OptimizationHints,MediaRouter,DialMediaRouteProvider"]
REDACT_HEADERS = {"cookie", "set-cookie", "authorization", "proxy-authorization"}


def _load_webfetch():
    spec = importlib.util.spec_from_file_location("web_fetch", HERE / "web-fetch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _need():
    try:
        import playwright
        from playwright.sync_api import Error as PWError, sync_playwright
        return playwright, sync_playwright, PWError
    except ImportError:
        sys.exit("error: playwright unavailable. Run this recipe with uv:\n"
                 "    uv run tools/recipes/web-render.py --install     # once: fetch Chromium\n"
                 "    uv run tools/recipes/web-render.py <url>\n"
                 "  or use the venv fallback in tools/recipes/README.md. (Tool policy: degrade loudly.)")


def cmd_install() -> int:
    """Download Playwright's full Chromium into ~/.cache/ms-playwright (user-level, no sudo).

    `--no-shell` fetches the full browser rather than only the stripped headless
    shell, so `channel="chromium"` can run new-headless mode — closer to a real
    Chrome than the shell. (Both still say `HeadlessChrome` in their UA; that one
    marker is handled at launch, see `anonymise_ua`.)"""
    r = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium", "--no-shell"])
    if r.returncode == 0:
        print("chromium installed for playwright. If a launch later fails on missing system "
              "libraries, that step needs sudo — ask the human to run: "
              f"`{sys.executable} -m playwright install-deps chromium`.", file=sys.stderr)
    return r.returncode


def _domain_cookies(jar, host: str) -> list[dict]:
    if jar is None:
        return []
    host = host.lower()
    out = []
    for c in jar:
        d = c.domain.lower()
        if host == d.lstrip(".") or host.endswith("." + d.lstrip(".")):
            out.append({"name": c.name, "value": c.value, "domain": c.domain, "path": c.path or "/",
                        "expires": float(c.expires) if c.expires else -1, "secure": bool(c.secure),
                        "httpOnly": False, "sameSite": "Lax"})
    return out


def anonymise_ua(ua: str) -> str:
    """Drop the one word that marks automation; keep engine, version and platform real."""
    return ua.replace("HeadlessChrome/", "Chrome/")


def browser_ua(pw, headful: bool) -> tuple[str | None, str]:
    """The UA this Chromium would send, with the headless marker removed. A bare launch
    (no profile, no page) is the cheapest way to learn the installed version."""
    if headful:
        return None, "browser's own (headful: no marker to remove)"
    try:
        probe = pw.chromium.launch(channel="chromium", headless=True)
    except Exception:
        try:
            probe = pw.chromium.launch(headless=True)
        except Exception:
            return None, "browser's own (version probe failed)"
    try:
        major = probe.version.split(".")[0]
    finally:
        probe.close()
    ua = (f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
          f"Chrome/{major}.0.0.0 Safari/537.36")
    return ua, "HeadlessChrome marker removed; version and platform are the browser's own"


def redact_har(src: Path, dst: Path) -> int:
    """Drop credential-bearing headers and cookie arrays from every entry. Returns count."""
    har = json.loads(src.read_text(encoding="utf-8"))
    n = 0
    for e in har.get("log", {}).get("entries", []):
        for side in ("request", "response"):
            part = e.get(side, {})
            before = len(part.get("headers", []))
            part["headers"] = [h for h in part.get("headers", []) if h.get("name", "").lower() not in REDACT_HEADERS]
            n += before - len(part["headers"])
            if part.get("cookies"):
                n += len(part["cookies"])
                part["cookies"] = []
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(har), encoding="utf-8")
    return n


def render(url: str, cfg: dict, prov: str, root: Path, args) -> tuple[dict, dict, list[str]]:
    playwright, sync_playwright, PWError = _need()
    wf = _load_webfetch()
    wf.STORE = root / "_generated" / "fetch"
    notes: list[str] = []
    p = urllib.parse.urlsplit(url)
    site = p.netloc.lower().removeprefix("www.")

    rob = wf.robots_for(url, cfg)
    par = rob["parsed"] or {}
    disallowed = rob["verdict"] in ("disallow", "disallow-all")
    if disallowed:
        notes.append(f"note: robots.txt disallows this path for crawlers ({rob['reason']}); single "
                     f"user-directed read — proceeding, recorded.")
    wf.rate_limit(p.netloc, max(cfg["budget"]["min_delay_seconds"], par.get("crawl_delay") or 0))
    jar, jar_status = _policy.cookie_jar(cfg, root)
    cookies = _domain_cookies(jar, p.netloc)

    blocked: list[str] = []
    def route(r, request):
        host = urllib.parse.urlsplit(request.url).netloc.lower().removeprefix("www.")
        same = host == site or host.endswith("." + site)
        if same or args.allow_third_party or request.resource_type in RENDER_ONLY_TYPES:
            r.continue_()
        else:
            blocked.append(f"{request.resource_type}:{host}")
            r.abort()

    tmp = Path(tempfile.mkdtemp(prefix="mozak-render-"))
    har_tmp = tmp / "capture.har" if args.har else None
    rec = {"url_requested": url, "fetched_at": wf._now(), "fetcher": "web-render/0.1"}
    t0 = time.monotonic()
    html, status, final, headers, version, used = "", None, url, {}, "?", "chromium"
    ua, ua_note, webdriver_seen = None, "browser's own", "unknown"
    try:
        pw_version = importlib.metadata.version("playwright")
    except importlib.metadata.PackageNotFoundError:
        pw_version = "?"
    try:
        with sync_playwright() as pw:
            ua, ua_note = browser_ua(pw, args.headful)
            kw = dict(user_data_dir=str(tmp), headless=not args.headful, args=HYGIENE,
                      ignore_default_args=DROP_DEFAULT_ARGS,
                      viewport={"width": 1280, "height": 900}, locale="en-US", accept_downloads=False)
            if ua:
                kw["user_agent"] = ua
            if har_tmp:
                kw.update(record_har_path=str(har_tmp), record_har_content="embed")
            used = "chromium"
            try:
                ctx = pw.chromium.launch_persistent_context(channel="chromium", **kw)
            except PWError:
                ctx = pw.chromium.launch_persistent_context(**kw)   # headless shell fallback
                used = "headless-shell"
                notes.append("note: full Chromium is not installed, so the stripped headless shell "
                             "rendered this page. `uv run tools/recipes/web-render.py --install` "
                             "fetches the full build for new-headless mode.")
            try:
                version = ctx.browser.version if ctx.browser else "?"
                ctx.route("**/*", route)
                if cookies:
                    ctx.add_cookies(cookies)
                page = ctx.new_page()
                resp = page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                try:
                    page.wait_for_load_state("networkidle", timeout=10_000)
                except PWError:
                    pass
                html, final = page.content(), page.url
                try:
                    webdriver_seen = page.evaluate("navigator.webdriver")
                except PWError:
                    webdriver_seen = "unknown"
                if resp is not None:
                    status, headers = resp.status, {k.lower(): v for k, v in resp.headers.items()}
                shot = None
                if args.screenshot:
                    shot = tmp / "shot.png"
                    page.screenshot(path=str(shot), full_page=True)
            finally:
                ctx.close()
    except PWError as e:
        msg = str(e).split("\n", 1)[0][:300]
        rec.update(http_status=None, error_kind="playwright", error_detail=msg,
                   elapsed_ms=int((time.monotonic() - t0) * 1000))
        shutil.rmtree(tmp, ignore_errors=True)
        if "install" in msg.lower() or "executable doesn't exist" in msg.lower():
            notes.append("error: Chromium is not installed for playwright — run "
                         "`uv run tools/recipes/web-render.py --install` (user-level, no sudo). If it "
                         "then fails on missing system libraries, that step needs sudo: ask the human "
                         "to run `playwright install-deps chromium`.")
        return {**rec, "verdict": "error", "verdict_reason": msg, "rung": "T4", "policy": prov}, wf._empty_ext(), notes

    body = html.encode("utf-8")
    sha = hashlib.sha256(body).hexdigest()
    rec.update(http_status=status, url_final=final, elapsed_ms=int((time.monotonic() - t0) * 1000),
               content_length=len(body), wire_length=None, declared_length=None,
               media_type="text/html", etag=headers.get("etag"), last_modified=headers.get("last-modified"),
               content_sha256=sha, cookies_sent=len(cookies),
               user_agent=f"chromium {version} — {ua_note}", ua_sent=ua or "browser default",
               navigator_webdriver=webdriver_seen,
               automation_labels="removed: HeadlessChrome UA marker, --enable-automation; nothing else touched")
    rec["_body"], rec["text"] = body, html
    ext = wf.extract(html) if html else wf._empty_ext()
    verdict, reason = wf.classify(rec, ext)
    row = {k: v for k, v in rec.items() if not k.startswith("_") and k != "text"}
    row.update(verdict=verdict, verdict_reason=reason, policy=prov,
               rung="T5" if cookies else "T4", tool=f"playwright/{pw_version}", browser=used,
               cookies=jar_status, third_party_blocked=len(blocked), extract_chars=ext["chars"],
               kept_ratio=ext["kept_ratio"], title=ext["title"], from_cache=0,
               robots_verdict=rob["verdict"], robots_reason=rob["reason"],
               robots_action="proceeded-single-read" if disallowed else "allowed",
               content_signal=par.get("content_signal"), license_rsl=par.get("license"))
    row.update(wf.store_put(rec, ext))
    out_dir = wf.STORE / "render"
    if args.screenshot and (tmp / "shot.png").is_file():
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp / "shot.png"), out_dir / f"{sha}.png")
        row["screenshot_ref"] = f"render/{sha}.png"
    if har_tmp and har_tmp.is_file():
        row["har_ref"], row["har_redacted"] = f"render/{sha}.har", redact_har(har_tmp, out_dir / f"{sha}.har")
    shutil.rmtree(tmp, ignore_errors=True)                     # the profile dies with the run
    wf.log_append(row)
    return row, ext, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?")
    ap.add_argument("--install", action="store_true", help="download Chromium for playwright (once)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--links", action="store_true", help="list outbound links instead of text")
    ap.add_argument("--screenshot", action="store_true", help="also keep a full-page PNG")
    ap.add_argument("--har", action="store_true", help="also keep a redacted HAR of the render")
    ap.add_argument("--headful", action="store_true", help="show the window (needs a display)")
    ap.add_argument("--allow-third-party", action="store_true",
                    help="let the page reach other hosts beyond scripts/styles/fonts")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()
    if args.install:
        _need()
        return cmd_install()
    if not args.url:
        ap.error("give a URL, or --install")

    cfg, prov = _policy.load(args.root)
    refusal = _policy.gate(cfg)
    if refusal:
        print(refusal, file=sys.stderr)
        return 2
    if not cfg["advanced_acquisition"]:
        print("error: rung T4 (a real browser) is above the cautious ceiling (T2). Set "
              "`advanced_acquisition = true` in .personal-shared/acquisition-policy.toml if that is "
              "right for your context.", file=sys.stderr)
        return 3
    p = urllib.parse.urlsplit(args.url)
    if p.scheme not in ("http", "https"):
        sys.exit(f"error: only http/https URLs (got {p.scheme!r}).")

    row, ext, notes = render(args.url, cfg, prov, args.root, args)
    for n in notes:
        print(n, file=sys.stderr)
    if row["verdict"] != "ok":
        wf = _load_webfetch()
        if row.get("error_kind") == "playwright":
            print(f"error: {row['verdict_reason']}", file=sys.stderr)
        else:
            print("\n".join(wf.explain_failure(row, cfg)), file=sys.stderr)
        return 4
    wf = _load_webfetch()
    links = wf.links_from(ext, row.get("url_final") or args.url)
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
