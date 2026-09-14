#!/usr/bin/env python3
# recipe: scholar-lookup
# input:  a DOI, an arXiv id, or a quoted title
# output: capture-ready frontmatter + the best open-access full-text URL on stdout (--json for the merged record)
# needs:  nothing (stdlib); every source is keyless. Sends your contact ONLY to Crossref/Unpaywall, only if set
# usage:  python3 tools/recipes/scholar-lookup.py <doi | arxiv:id | "title words"> [--json]

"""Rung T0 for papers: don't scrape the publisher — ask the registries.

Given a DOI, an arXiv id, or a title, this asks Crossref (canonical metadata),
OpenAlex (open-access location, citation count) and arXiv (for preprints) —
all keyless, all verified working in 2026 — and prints a frontmatter block
ready to paste into a `sources/` capture, plus the best open-access URL. It
never touches the publisher's page. Unpaywall, which gives the most precise OA
verdict, *requires* an e-mail; it is queried only when you have set
`identity.contact`, and the output says whether it was. Crossref's polite pool
likewise uses that contact if present. Nothing else leaves your machine.

Each API call runs through web-fetch's `fetch()` — same User-Agent policy, same
per-host pacing, same provenance log (rung T0). OpenAlex meters anonymous use
(~100 title searches a day); id lookups are free. Conventions: AGENTS.md; this
recipe never writes into the graph.
"""

import argparse
import importlib.util
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import policy as _policy  # noqa: E402

ROOT = HERE.parent.parent
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>]+)", re.I)
ARXIV_RE = re.compile(r"(?:arxiv:)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})", re.I)
ATOM = {"a": "http://www.w3.org/2005/Atom"}


def _load_webfetch():
    spec = importlib.util.spec_from_file_location("web_fetch", HERE / "web-fetch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def classify_query(q: str) -> tuple[str, str]:
    q = q.strip()
    m = DOI_RE.search(q)
    if m:
        return "doi", m.group(1).rstrip(".,;)")
    m = ARXIV_RE.fullmatch(q) or (ARXIV_RE.search(q) if "arxiv" in q.lower() else None)
    if m:
        return "arxiv", m.group(1)
    return "title", q.strip('"\'')


# ----------------------------------------------------------------- parsers (pure, tested)

def parse_crossref(msg: dict) -> dict:
    d = msg.get("message", msg)
    authors = [" ".join(x for x in (a.get("given"), a.get("family")) if x) for a in d.get("author", [])]
    parts = (d.get("issued") or d.get("published") or {}).get("date-parts", [[None]])[0]
    published = "-".join(f"{x:02d}" if i else str(x) for i, x in enumerate(parts) if x is not None) or None
    lic = [l.get("URL") for l in d.get("license", []) if l.get("URL")]
    return {"title": (d.get("title") or [""])[0], "authors": authors, "published": published,
            "venue": (d.get("container-title") or [""])[0] or d.get("publisher"),
            "doi": d.get("DOI"), "url": d.get("URL"), "type": d.get("type"),
            "license": lic[0] if lic else None, "source": "crossref"}


def parse_openalex(d: dict) -> dict:
    oa = d.get("open_access") or {}
    best = d.get("best_oa_location") or {}
    prim = d.get("primary_location") or {}
    return {"title": d.get("title") or d.get("display_name"),
            "authors": [a.get("author", {}).get("display_name") for a in d.get("authorships", [])],
            "published": d.get("publication_date"),
            "venue": (prim.get("source") or {}).get("display_name"),
            "doi": (d.get("doi") or "").replace("https://doi.org/", "") or None,
            "oa_status": oa.get("oa_status"), "oa_url": oa.get("oa_url") or best.get("pdf_url"),
            "pdf_url": best.get("pdf_url"), "license": best.get("license"),
            "cited_by": d.get("cited_by_count"), "openalex_id": d.get("id"),
            "landing": prim.get("landing_page_url"), "source": "openalex"}


def parse_unpaywall(d: dict) -> dict:
    best = d.get("best_oa_location") or {}
    return {"oa_status": d.get("oa_status"), "is_oa": d.get("is_oa"),
            "pdf_url": best.get("url_for_pdf"), "oa_url": best.get("url"),
            "license": best.get("license"), "host_type": best.get("host_type"),
            "source": "unpaywall"}


def parse_arxiv(atom_xml: str) -> dict | None:
    root = ET.fromstring(atom_xml)
    e = root.find("a:entry", ATOM)
    if e is None or e.find("a:id", ATOM) is None:
        return None
    pdf = next((l.get("href") for l in e.findall("a:link", ATOM) if l.get("title") == "pdf"), None)
    doi = e.find("{http://arxiv.org/schemas/atom}doi")
    aid = (e.findtext("a:id", default="", namespaces=ATOM) or "").rsplit("/abs/", 1)[-1]
    return {"title": re.sub(r"\s+", " ", e.findtext("a:title", default="", namespaces=ATOM)).strip(),
            "authors": [a.findtext("a:name", default="", namespaces=ATOM) for a in e.findall("a:author", ATOM)],
            "published": (e.findtext("a:published", default="", namespaces=ATOM) or "")[:10] or None,
            "arxiv_id": aid, "doi": doi.text if doi is not None else None,
            "pdf_url": pdf, "oa_url": pdf, "oa_status": "green", "license": "arXiv",
            "url": f"https://arxiv.org/abs/{aid}", "venue": "arXiv", "source": "arxiv"}


def parse_openalex_search(d: dict) -> list[dict]:
    return [{"title": r.get("title") or r.get("display_name"), "year": r.get("publication_year"),
             "doi": (r.get("doi") or "").replace("https://doi.org/", "") or None,
             "cited_by": r.get("cited_by_count")} for r in d.get("results", [])]


# ----------------------------------------------------------------- lookups (network)

def _get_json(wf, cfg, url: str, host_delay: float = 1.0):
    wf.rate_limit(urllib.parse.urlsplit(url).netloc, host_delay)
    rec = wf.fetch(url, cfg, {"Accept": "application/json"})
    wf.log_append({k: v for k, v in rec.items() if not k.startswith("_") and k not in ("text", "headers")}
                  | {"rung": "T0", "tool": "scholar-lookup", "verdict": "ok" if rec.get("http_status") == 200 else "error"})
    if rec.get("http_status") != 200:
        return None, rec.get("http_status")
    try:
        return json.loads(rec["text"]), 200
    except Exception:
        return None, "non-json"


def lookup(wf, cfg, kind: str, q: str, contact: str) -> dict:
    out = {"query": q, "kind": kind, "queried": [], "skipped": [], "candidates": []}
    doi = q if kind == "doi" else None

    if kind == "title":
        d, st = _get_json(wf, cfg, "https://api.openalex.org/works?"
                          + urllib.parse.urlencode({"search": q, "per-page": 3}))
        out["queried"].append(f"openalex search ({st}; anonymous use is metered ~100/day)")
        if d:
            out["candidates"] = parse_openalex_search(d)
            doi = next((c["doi"] for c in out["candidates"] if c.get("doi")), None)
            if not doi:
                return out

    if kind == "arxiv":
        rec_url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode({"id_list": q})
        wf.rate_limit("export.arxiv.org", 3.0)                # arXiv TOU: 1 req / 3 s
        rec = wf.fetch(rec_url, cfg, {"Accept": "application/atom+xml"})
        wf.log_append({k: v for k, v in rec.items() if not k.startswith("_") and k not in ("text", "headers")}
                      | {"rung": "T0", "tool": "scholar-lookup", "verdict": "ok" if rec.get("http_status") == 200 else "error"})
        out["queried"].append(f"arxiv ({rec.get('http_status')})")
        ax = parse_arxiv(rec["text"]) if rec.get("http_status") == 200 else None
        if ax:
            out["arxiv"] = ax
            doi = ax.get("doi")

    if doi:
        cr_url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='/')}"
        if contact:
            cr_url += "?" + urllib.parse.urlencode({"mailto": contact})
        d, st = _get_json(wf, cfg, cr_url)
        out["queried"].append(f"crossref ({st}; polite pool: {'yes — your contact was sent' if contact else 'no'})")
        if d:
            out["crossref"] = parse_crossref(d)
        d, st = _get_json(wf, cfg, f"https://api.openalex.org/works/https://doi.org/{doi}")
        out["queried"].append(f"openalex ({st})")
        if d:
            out["openalex"] = parse_openalex(d)
        if contact:
            d, st = _get_json(wf, cfg, f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi, safe='/')}?"
                              + urllib.parse.urlencode({"email": contact}))
            out["queried"].append(f"unpaywall ({st}; your contact was sent — it is mandatory there)")
            if d:
                out["unpaywall"] = parse_unpaywall(d)
        else:
            out["skipped"].append("unpaywall — requires an e-mail; set identity.contact to enable")
        out["doi"] = doi
    return out


def merge(res: dict) -> dict:
    """Best value per field, most authoritative source first."""
    srcs = [res.get(k) for k in ("crossref", "arxiv", "openalex", "unpaywall") if res.get(k)]
    def first(field):
        return next((s[field] for s in srcs if s.get(field)), None)
    oa = res.get("unpaywall") or {}
    best_pdf = oa.get("pdf_url") or (res.get("arxiv") or {}).get("pdf_url") or (res.get("openalex") or {}).get("pdf_url")
    best_url = best_pdf or oa.get("oa_url") or (res.get("openalex") or {}).get("oa_url")
    return {"title": first("title"), "authors": first("authors") or [], "published": first("published"),
            "venue": first("venue"), "doi": res.get("doi"), "arxiv_id": (res.get("arxiv") or {}).get("arxiv_id"),
            "url": f"https://doi.org/{res['doi']}" if res.get("doi") else first("url"),
            "oa_status": oa.get("oa_status") or first("oa_status"), "oa_url": best_url,
            "license": oa.get("license") or first("license"),
            "cited_by": (res.get("openalex") or {}).get("cited_by")}


def render(m: dict, res: dict) -> str:
    today = date.today().isoformat()
    authors = ", ".join(a for a in m["authors"] if a) or "<author>"
    t = (m["title"] or "<title>").replace('"', "'")
    lines = ["---", f'title: "Paper: {t}"', "type: source", "domain: [<domain>]",
             f"url: {m['url'] or '<url>'}", "medium: paper", f"author: {authors}"]
    if m["published"]:
        lines.append(f"published: {m['published']}")
    lines += [f"retrieved: {today}", f"created: {today}", f"updated: {today}",
              "capture-method: T0 scholar-lookup", "---", "", f"# {m['title'] or '<title>'}", "",
              "## Open access", ""]
    if m["oa_url"]:
        lines.append(f"- **Full text:** {m['oa_url']}  (status: {m['oa_status'] or '?'}"
                     f"{', license: ' + m['license'] if m['license'] else ''})")
    else:
        lines.append(f"- No open-access copy found (status: {m['oa_status'] or 'unknown'}). "
                     f"Rung T2 (Wayback) or your own institutional access is next — not the paywall.")
    if m["venue"]:
        lines.append(f"- Venue: {m['venue']}")
    if m["cited_by"] is not None:
        lines.append(f"- Cited by (OpenAlex): {m['cited_by']}")
    if res.get("candidates") and len(res["candidates"]) > 1:
        lines += ["", "## Other title matches (verify you have the right one)", ""]
        lines += [f"- {c['title']} ({c['year']}) — doi:{c['doi'] or '?'}, cited {c['cited_by']}"
                  for c in res["candidates"][1:]]
    lines += ["", "## Provenance", "", f"- Queried: {'; '.join(res['queried']) or 'nothing'}"]
    if res["skipped"]:
        lines.append(f"- Skipped: {'; '.join(res['skipped'])}")
    lines.append("- Every call is logged under _generated/fetch/ as rung T0.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", help='a DOI, "arxiv:2301.01234", or a "quoted title"')
    ap.add_argument("--json", action="store_true", help="emit the merged record and raw source fields")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()
    cfg, prov = _policy.load(args.root)
    refusal = _policy.gate(cfg)
    if refusal:
        print(refusal, file=sys.stderr)
        return 2
    wf = _load_webfetch()
    wf.STORE = args.root / "_generated" / "fetch"
    kind, q = classify_query(args.query)
    contact = (cfg["identity"]["contact"] or "").strip()
    ok, why = _policy.looks_reachable(contact)
    if contact and not ok:
        print(f"note: identity.contact {contact!r} not sent — {why}. The field exists so a source can "
              f"reach you; proceeding as if empty.", file=sys.stderr)
        contact = ""
    res = lookup(wf, cfg, kind, q, contact)
    if not ok and (cfg["identity"]["contact"] or "").strip():
        res["skipped"].append(f"contact not sent — {why}")
    m = merge(res)
    if args.json:
        print(json.dumps({"merged": m, **res}, indent=2, sort_keys=True))
    else:
        print(render(m, res))
    if not (m["title"] or res.get("candidates")):
        print(f"\nerror: nothing found for {kind} {q!r} — {'; '.join(res['queried'])}", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
