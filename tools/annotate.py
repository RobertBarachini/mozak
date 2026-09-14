#!/usr/bin/env python3
"""Annotate a rendered HTML report and capture per-selection re-prompts to a file.

A capture-and-serve tool, NOT an AI client: it serves a report locally with an
injected annotation overlay and writes highlighted-text + prompt pairs to a plain
`annotations.md` beside the render. Whatever harness you point at that file (Claude
Code, another agent, a script) does the work — see pages/mozak-report-annotation-loop.md.
The served page live-refreshes (polls file mtimes), so an agent's drain — flipped
statuses and appended answers — appears in an open page without a manual reload.
The tool holds no API key, names no model, and binds 127.0.0.1 only (AGENTS rule 10).
Conventions: AGENTS.md. Core tooling: stdlib only (AGENTS `tools/` row).

Usage:
  python3 tools/annotate.py <report.html>              # serve (implicit) + open a browser
  python3 tools/annotate.py serve <report.html> [--port N] [--no-browser] [--open]
  python3 tools/annotate.py list  <report.html> [--status S]   # print the queue (optionally one status), no server
  python3 tools/annotate.py mcp   [report.html]        # optional MCP stdio server (see SETUP.md §5)

Annotations land in the report's directory as `annotations.md` (Markdown with a fenced
JSON anchor per entry). Over VS Code Remote-SSH the localhost port auto-forwards; open
the printed URL in your local browser.
"""

import argparse
import hashlib
import json
import mimetypes
import os
import re
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

DEFAULT_PORT = 8765
SCHEMA = "annotate/2"          # /1 = single prompt+answer; /2 = a thread of turns
STATUS_ORDER = {"pending": 0, "processing": 1, "orphaned": 2, "answered": 3, "distilled": 4, "dismissed": 5}
UPDATABLE = ("status", "selector", "section", "position", "scope")

FRONT_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
HEADING_RE = re.compile(r"^##\s+\d+\.\s+\[(\w+)\]", re.M)
FENCE_RE = re.compile(r"```json\s*(.*?)```", re.S)


# ---------------------------------------------------------------- annotations.md

def slugify(s: str) -> str:
    return "-".join(t for t in re.split(r"[^a-z0-9]+", s.strip().lower()) if t)


def report_title(html_path: Path) -> str:
    """A human label for the annotations file — the render slug, or the file stem."""
    stem = html_path.stem
    if stem in ("index", "report") and html_path.parent.name:
        return html_path.parent.name
    return stem


def _rel(p: Path, root: Path) -> str:
    try:
        return str(p.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(p.resolve())


def annotations_path(html_path: Path, root: Path) -> Path:
    """Sidecar beside the report (the presentations/<slug>/ case); else a keyed store
    under _generated/annotations/ for reports outside a writable render dir."""
    html_path = html_path.resolve()
    parent = html_path.parent
    inside = root.resolve() in html_path.parents
    if inside and os.access(parent, os.W_OK):
        return parent / "annotations.md"
    key = hashlib.sha1(str(html_path).encode("utf-8")).hexdigest()[:8]
    slug = slugify(html_path.stem) or "report"
    return root / "_generated" / "annotations" / f"{slug}-{key}" / "annotations.md"


def _turns(body: str):
    """Parse the ordered conversation turns from an entry body. Each `**Prompt:**`
    opens a turn; the next `**Agent:**` fills that turn's answer; a stray `**Agent:**`
    with no open turn gets its own. A trailing prompt with answer=None is an open turn
    (⟺ the entry is `[pending]`). A single old prompt/answer pair reads as one turn —
    so `annotate/1` files parse unchanged (backward-compatible)."""
    turns = []
    for m in re.finditer(r"\*\*(Prompt|Agent):\*\*[ \t]*(.*?)"
                         r"(?=\n\*\*(?:Prompt|Agent):\*\*|\Z)", body, re.S):
        kind, text = m.group(1), m.group(2).strip()
        if kind == "Prompt":
            turns.append({"prompt": text, "answer": None})
        elif turns and turns[-1]["answer"] is None:
            turns[-1]["answer"] = text            # Agent fills the open turn
        else:
            turns.append({"prompt": "", "answer": text})
    return turns


def _parse_entry(chunk: str):
    mh = HEADING_RE.search(chunk)
    if not mh:
        return None
    mj = FENCE_RE.search(chunk)
    try:
        data = json.loads(mj.group(1)) if mj else {}
    except json.JSONDecodeError:
        data = {}
    body = chunk[mh.end():(mj.start() if mj else len(chunk))]
    return {
        "id": data.get("id"),
        "status": mh.group(1),
        "scope": data.get("scope", "selection"),
        "section": data.get("section"),
        "selector": data.get("selector"),
        "position": data.get("position"),
        "turns": _turns(body),
    }


def load_annotations(path: Path):
    """Return (meta: dict, items: list[dict]). Status lives only in the heading token;
    the fenced JSON owns the machine anchor; prose owns the conversation turns."""
    if not path.exists():
        return {}, []
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    mf = FRONT_RE.match(text)
    if mf:
        for line in mf.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = text[mf.end():]
    items = []
    for chunk in re.split(r"(?m)^(?=##\s+\d+\.\s+\[)", body):
        if not chunk.lstrip().startswith("##"):
            continue
        rec = _parse_entry(chunk)
        if rec and rec.get("id"):
            items.append(rec)
    return meta, items


def raw_entry(text: str, tid: str):
    """The verbatim Markdown block for one annotation id (heading → fence), for a
    'View raw' peek — the file itself, not a re-serialization."""
    body = text
    mf = FRONT_RE.match(text)
    if mf:
        body = text[mf.end():]
    for chunk in re.split(r"(?m)^(?=##\s+\d+\.\s+\[)", body):
        if not chunk.lstrip().startswith("##"):
            continue
        mj = FENCE_RE.search(chunk)
        if mj:
            try:
                if json.loads(mj.group(1)).get("id") == tid:
                    return chunk.strip() + "\n"
            except json.JSONDecodeError:
                pass
    return None


def _label(a: dict) -> str:
    if a.get("scope") == "document":
        return "whole document"
    sec = a.get("section")
    return 'under "%s"' % sec if sec else "(no section)"


def dump_annotations(path: Path, meta: dict, items: list) -> None:
    """Regenerate the whole file, then swap atomically. Serialization is tool-managed;
    the drain contract (mozak-report-annotation-loop) documents the shape agents append to."""
    out = ["---", "report: %s" % meta.get("report", ""),
           "created: %s" % meta.get("created", "")]
    if meta.get("title"):
        out.append("title: %s" % meta["title"])
    if meta.get("flushed"):
        out.append("flushed: %s" % meta["flushed"])
    out += ["schema: %s" % SCHEMA, "---", "",
            "# Annotations — %s" % meta.get("title", "report"), ""]
    for i, a in enumerate(items, 1):
        out.append("## %d. [%s] %s" % (i, a.get("status", "pending"), _label(a)))
        out.append("")
        sel = a.get("selector") or {}
        if a.get("scope") == "selection" and sel.get("exact"):
            out += ["> %s" % sel["exact"].replace("\n", " "), ""]
        for t in a.get("turns") or []:
            out += ["**Prompt:** %s" % (t.get("prompt") or "").strip(), ""]
            if t.get("answer"):
                out += ["**Agent:** %s" % t["answer"].strip(), ""]
        data = {"id": a.get("id"), "scope": a.get("scope", "selection"),
                "section": a.get("section"), "selector": a.get("selector"),
                "position": a.get("position")}
        out += ["```json", json.dumps(data, ensure_ascii=False), "```", ""]
    text = "\n".join(out).rstrip() + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _next_id(items: list) -> str:
    mx = 0
    for a in items:
        m = re.match(r"a(\d+)$", a.get("id") or "")
        if m:
            mx = max(mx, int(m.group(1)))
    return "a%d" % (mx + 1)


def _normalize_new(data: dict) -> dict:
    return {"id": data.get("id"), "status": data.get("status", "pending"),
            "scope": data.get("scope", "selection"), "section": data.get("section"),
            "selector": data.get("selector"), "position": data.get("position"),
            "turns": [{"prompt": (data.get("prompt") or "").strip(),
                       "answer": data.get("answer")}]}


# ------------------------------------------------------------------- the client

ANNOT_CSS = r"""
:root{--bg:#fff;--fg:#1a1a1a;--mut:#6b6b6b;--line:#e3e3e3;--card:#f6f6f6;--accent:#2563eb}
@media (prefers-color-scheme:dark){:root{--bg:#1d1d1d;--fg:#e9e9e9;--mut:#9a9a9a;--line:#343434;--card:#262626;--accent:#6ea8ff}}
*{box-sizing:border-box}
html,body{margin:0;height:100%;font-family:system-ui,-apple-system,sans-serif;color:var(--fg);background:var(--bg)}
#mzk-bar{position:fixed;top:0;left:0;right:0;height:46px;display:flex;align-items:center;gap:10px;padding:0 12px;background:var(--card);border-bottom:1px solid var(--line);z-index:10;font-size:13px}
#mzk-title{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:38vw}
#mzk-count{color:var(--mut);white-space:nowrap}
.mzk-spacer{flex:1}
#mzk-bar button{font:inherit;padding:6px 11px;border:1px solid var(--line);background:var(--bg);color:var(--fg);border-radius:6px;cursor:pointer}
#mzk-bar button:hover{border-color:var(--accent)}
/* iframe is a REPLACED element: top/right/bottom/left do NOT stretch it (that only
   works for non-replaced blocks) and width/height:auto would collapse to the intrinsic
   ~300x150 — so size it explicitly with calc against the fixed containing block. */
#mzk-report{position:fixed;top:46px;left:0;width:100%;height:calc(100% - 46px);border:0;background:#fff}
body.mzk-open #mzk-report{width:calc(100% - var(--drawer-w,360px))}
#mzk-drawer{position:fixed;top:46px;right:0;bottom:0;width:var(--drawer-w,360px);background:var(--card);border-left:1px solid var(--line);overflow-y:auto;transform:translateX(100%);transition:transform .15s;z-index:9}
body.mzk-open #mzk-drawer{transform:none}
#mzk-grip{position:fixed;top:46px;bottom:0;right:var(--drawer-w,360px);width:7px;margin-right:-3px;cursor:ew-resize;z-index:11;display:none}
#mzk-grip:hover,#mzk-grip.mzk-drag{background:var(--accent);opacity:.55}
body.mzk-open #mzk-grip{display:block}
#mzk-view{position:fixed;top:46px;left:0;width:100%;height:calc(100% - 46px);background:var(--bg);z-index:8;display:none;flex-direction:column}
body.mzk-open #mzk-view{width:calc(100% - var(--drawer-w,360px))}
body.mzk-viewing #mzk-view{display:flex}
#mzk-view-bar{flex:0 0 auto;display:flex;align-items:center;gap:8px;padding:8px 12px;background:var(--card);border-bottom:1px solid var(--line)}
#mzk-view-bar button{font:inherit;font-size:12px;padding:5px 11px;border:1px solid var(--line);background:var(--bg);color:var(--fg);border-radius:6px;cursor:pointer}
#mzk-view-bar button:hover{border-color:var(--accent)}
#mzk-view-title{font-weight:600;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}
#mzk-view-body{flex:1;overflow:auto;padding:22px 30px;line-height:1.62}
#mzk-view-body>*{max-width:780px}
#mzk-view-body h1{font-size:1.5em}#mzk-view-body h2{font-size:1.25em}#mzk-view-body h3{font-size:1.08em}
#mzk-view-body h1,#mzk-view-body h2,#mzk-view-body h3{line-height:1.25;margin:1.1em 0 .4em}
#mzk-view-body ul,#mzk-view-body ol{padding-left:22px}#mzk-view-body li{margin:3px 0}
#mzk-view-body p,#mzk-view-body li{text-align:justify;hyphens:auto}
#mzk-view-body a{color:var(--accent)}
#mzk-view-body blockquote{border-left:3px solid var(--line);margin:8px 0;padding-left:12px;color:var(--mut)}
#mzk-view-body pre.mzk-code{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:10px;overflow:auto;font-size:12.5px}
#mzk-view-body pre.mzk-raw{white-space:pre-wrap;word-break:break-word;text-align:left;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;line-height:1.5}
.mzk-card{border:1px solid var(--line);background:var(--bg);border-radius:8px;margin:10px;padding:10px;font-size:13px;cursor:pointer}
.mzk-card .sec{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px}
.mzk-card blockquote{margin:6px 0;padding-left:8px;border-left:3px solid #f5c518;color:var(--fg);font-style:italic}
.mzk-card .prompt{margin:8px 0;white-space:pre-wrap;padding:2px 0 2px 8px;border-left:3px solid #8b5cf6}
.mzk-card .agent{margin:6px 0;color:var(--fg);border-top:1px dashed var(--line);padding-top:6px}
.mzk-card .agent p{margin:6px 0}.mzk-card .agent p:first-child{margin-top:0}
.mzk-card .agent ul{margin:6px 0;padding-left:18px}.mzk-card .agent li{margin:2px 0}
.mzk-card .agent code{background:var(--card);padding:1px 4px;border-radius:3px;font-size:12px}
.mzk-card .agent a{color:var(--accent)}
.mzk-wl{color:var(--accent);border-bottom:1px dotted var(--accent);text-decoration:none;cursor:pointer}
.mzk-wl::after{content:"📝";font-size:.82em;margin-left:3px;border-bottom:0;cursor:default}
.mzk-wl.mzk-missing{opacity:.55;cursor:help;border-bottom-style:dashed}
.mzk-chip{display:inline-block;font-size:11px;padding:1px 8px;border-radius:10px;background:var(--line);text-transform:capitalize}
.mzk-chip.pending{background:#f59e0b;color:#241a04}
.mzk-chip.processing{background:#6366f1;color:#fff;animation:mzk-pulse 1.1s ease-in-out infinite}
@keyframes mzk-pulse{0%,100%{opacity:1}50%{opacity:.4}}
.mzk-chip.orphaned{background:#ef4444;color:#fff}
.mzk-chip.answered,.mzk-chip.distilled{background:#10b981;color:#04231a}
.mzk-chip.dismissed{background:var(--line);color:var(--mut)}
.mzk-card pre.mzk-raw{white-space:pre-wrap;word-break:break-word;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:8px;margin:6px 0;font-size:11.5px;font-family:ui-monospace,Menlo,Consolas,monospace;max-height:360px;overflow:auto}
.mzk-rowbtns{margin-top:8px;display:flex;flex-wrap:wrap;gap:6px}
.mzk-rowbtns button{font:inherit;font-size:11px;padding:2px 8px;border:1px solid var(--line);background:var(--bg);color:var(--fg);border-radius:5px;cursor:pointer}
#mzk-float{position:fixed;z-index:20;transform:translate(-50%,6px)}
#mzk-float button{font:inherit;font-size:12px;padding:6px 12px;border:0;background:var(--accent);color:#fff;border-radius:16px;cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.3)}
.mzk-pop{position:fixed;z-index:21;width:310px;max-width:92vw;background:var(--bg);border:1px solid var(--line);border-radius:9px;box-shadow:0 8px 30px rgba(0,0,0,.35);padding:11px}
.mzk-pop .q{font-size:12px;color:var(--mut);margin-bottom:6px;max-height:60px;overflow:auto}
.mzk-pop textarea{width:100%;min-height:74px;font:inherit;font-size:13px;padding:7px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);resize:vertical}
.mzk-pop .actions{display:flex;justify-content:flex-end;gap:6px;margin-top:8px}
.mzk-pop button{font:inherit;padding:6px 13px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--fg);cursor:pointer}
.mzk-pop button.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
.mzk-modal{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:30;display:flex;align-items:center;justify-content:center}
.mzk-modal .box{background:var(--bg);border:1px solid var(--line);border-radius:11px;padding:20px;max-width:540px;font-size:13px;line-height:1.5}
.mzk-modal code{background:var(--card);padding:2px 6px;border-radius:4px;word-break:break-all}
.mzk-modal .actions{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}
.mzk-modal button{font:inherit;padding:7px 14px;border-radius:7px;border:1px solid var(--line);background:var(--bg);color:var(--fg);cursor:pointer}
.mzk-modal button.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
.mzk-empty{color:var(--mut);padding:18px;font-size:13px;text-align:center}
#mzk-search{position:sticky;top:0;background:var(--card);padding:8px 10px;border-bottom:1px solid var(--line);z-index:1}
#mzk-q{width:100%;font:inherit;font-size:13px;padding:6px 9px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}
.mzk-follow{margin-top:8px;display:flex;flex-direction:column;gap:6px}
.mzk-follow textarea{width:100%;font:inherit;font-size:12px;padding:6px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);resize:vertical}
.mzk-follow button{align-self:flex-end;font:inherit;font-size:11px;padding:3px 10px;border:1px solid var(--accent);background:var(--accent);color:#fff;border-radius:5px;cursor:pointer}
"""

# Injected into the report's OWN document (the iframe) — non-destructive highlight,
# zero DOM change to the report; see mozak-report-annotation-loop for why this is safe.
IFRAME_STYLE = ("::highlight(mzk){background-color:rgba(245,197,24,.45)}"
                "::highlight(mzk-active){background-color:rgba(245,150,0,.8)}")

ANNOT_JS = r"""
(function(){
'use strict';
var CTX=32;
var iframe=document.getElementById('mzk-report');
var listEl=document.getElementById('mzk-list');
var countEl=document.getElementById('mzk-count');
var DATA={meta:{},items:[]};
var NOTES=NOTES_JSON;       // {stem: repo-relative note path} — injected at render time
var RAW=new Set(), RAWTEXT={};   // per-card "view raw" toggle state + fetched raw block
var CURNOTE=null, NAV=[], CURMD='', VIEWRAW=false;   // in-pane note viewer: stem, back-stack, raw md, raw-toggle
var idoc=null, iwin=null;
var RANGES=new Map();       // id -> Range (into the iframe document)
var floatEl=null, popEl=null;
var norm=function(s){return (s||'').replace(/\s+/g,' ');};

function api(method,path,body){
  return fetch(path,{method:method,headers:{'Content-Type':'application/json'},
    body:body?JSON.stringify(body):undefined}).then(function(r){return r.json();});
}
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}

// ---- minimal, self-contained markdown for agent answers (escape FIRST, then mark up) ----
function wlink(target,shown){
  // a real anchor to the note file when the stem resolves (so right-click can copy the
  // path/text and left-click peeks it — handled in the card click listener); the 📝 marker
  // (a CSS ::after) distinguishes it from a web link. Unresolved stems stay inert.
  var stem=(target||'').trim(), path=NOTES[stem];
  if(path) return '<a class=mzk-wl href="'+path+'" data-note="'+stem+'" title="'+path+'">'+shown+'</a>';
  return '<span class="mzk-wl mzk-missing" title="unresolved note: '+stem+'">'+shown+'</span>';
}
function mdInline(s){
  // [[target|shown]] / [[target]] -> a link to the note file (see wlink)
  s=s.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g,function(m,target,shown){return wlink(target,shown);});
  s=s.replace(/\[\[([^\]]+)\]\]/g,function(m,target){return wlink(target,target);});
  s=s.replace(/`([^`]+)`/g,'<code>$1</code>');
  // [text](url) -> anchor only for http(s); anything else renders as plain text
  s=s.replace(/\[([^\]]+)\]\(([^)\s"']+)\)/g,function(m,t,u){
    return /^https?:\/\//.test(u)?'<a href="'+u+'" target=_blank rel=noopener>'+t+'</a>':t;});
  s=s.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
  s=s.replace(/(^|[^*])\*([^*\n]+)\*/g,'$1<em>$2</em>');
  return s;
}
function mdToHtml(src){
  var blocks=esc(src||'').split(/\n{2,}/), out=[];
  blocks.forEach(function(b){
    if(!b.trim()) return;
    var lines=b.split(/\n/);
    if(/^\s*[-*]\s+/.test(lines[0])){
      out.push('<ul>'+lines.filter(function(l){return l.trim();}).map(function(l){
        return '<li>'+mdInline(l.replace(/^\s*[-*]\s+/,''))+'</li>';}).join('')+'</ul>');
    } else {
      out.push('<p>'+mdInline(b.replace(/\n/g,'<br>'))+'</p>');
    }
  });
  return out.join('');
}
// block-level markdown for a whole note (headings/lists/code/quote + inline). Basic by
// design — enough to read a note in-pane; wikilinks stay clickable via mdInline/wlink.
function mdDoc(src){
  src=String(src||'').replace(/\r\n/g,'\n').replace(/^---\n[\s\S]*?\n---\n/,'');  // drop frontmatter
  var lines=src.split('\n'), out=[], para=[], i=0;
  function flush(){ if(para.length){out.push('<p>'+mdInline(esc(para.join(' ')))+'</p>');para=[];} }   // single newlines are soft wraps → spaces, not <br>
  function items(re,tag){ var b=[]; while(i<lines.length&&re.test(lines[i])){b.push('<li>'+mdInline(esc(lines[i].replace(re,'')))+'</li>');i++;} out.push('<'+tag+'>'+b.join('')+'</'+tag+'>'); }
  while(i<lines.length){
    var ln=lines[i], h=/^(#{1,6})\s+(.*)$/.exec(ln);
    if(/^```/.test(ln)){ flush(); var c=[]; i++; while(i<lines.length&&!/^```/.test(lines[i])){c.push(lines[i]);i++;} i++; out.push('<pre class=mzk-code>'+esc(c.join('\n'))+'</pre>'); }
    else if(h){ flush(); out.push('<h'+h[1].length+'>'+mdInline(esc(h[2]))+'</h'+h[1].length+'>'); i++; }
    else if(/^\s*[-*]\s+/.test(ln)){ flush(); items(/^\s*[-*]\s+/,'ul'); }
    else if(/^\s*\d+\.\s+/.test(ln)){ flush(); items(/^\s*\d+\.\s+/,'ol'); }
    else if(/^\s*>\s?/.test(ln)){ flush(); var q=[]; while(i<lines.length&&/^\s*>\s?/.test(lines[i])){q.push(lines[i].replace(/^\s*>\s?/,''));i++;} out.push('<blockquote>'+mdInline(esc(q.join(' ')))+'</blockquote>'); }
    else if(!ln.trim()){ flush(); i++; }
    else { para.push(ln); i++; }
  }
  flush();
  return out.join('\n');
}

// ---- drawer search filter ----
var FILTER='';
function idNum(id){var m=/(\d+)/.exec(id||'');return m?parseInt(m[1],10):0;}
function matchFilter(a){
  if(!FILTER) return true;
  var hay=[a.section||'',(a.selector&&a.selector.exact)||''];
  (a.turns||[]).forEach(function(t){hay.push(t.prompt||'');hay.push(t.answer||'');});
  return hay.join('\n').toLowerCase().indexOf(FILTER)>=0;
}

// ---- text model of the iframe doc (nodes + raw concatenation) ----
function collectText(doc){
  var walker=doc.createTreeWalker(doc.body,NodeFilter.SHOW_TEXT,{acceptNode:function(n){
    var p=n.parentNode?n.parentNode.nodeName:'';
    if(p==='SCRIPT'||p==='STYLE') return NodeFilter.FILTER_REJECT;
    return NodeFilter.FILTER_ACCEPT;}});
  var nodes=[],starts=[],raw='',n;
  while((n=walker.nextNode())){starts.push(raw.length);nodes.push(n);raw+=n.data;}
  return {nodes:nodes,starts:starts,raw:raw};
}
function buildNorm(raw){
  var nrm='',map=[],prevSpace=false,i,c;
  for(i=0;i<raw.length;i++){c=raw[i];
    if(/\s/.test(c)){if(prevSpace)continue;nrm+=' ';map.push(i);prevSpace=true;}
    else{nrm+=c;map.push(i);prevSpace=false;}}
  return {nrm:nrm,map:map};
}
function locate(t,off){
  var i,s,e;
  for(i=0;i<t.nodes.length;i++){s=t.starts[i];e=s+t.nodes[i].data.length;
    if(off<e) return [t.nodes[i],Math.max(0,off-s)];}
  var last=t.nodes[t.nodes.length-1];
  return last?[last,last.data.length]:[t.nodes[0],0];
}
function rawRange(doc,t,a,b){
  var r=doc.createRange(),s=locate(t,a),e=locate(t,b);
  try{r.setStart(s[0],s[1]);r.setEnd(e[0],e[1]);}catch(err){return null;}
  return r;
}
function rawOffset(t,container,offset){
  var i;
  for(i=0;i<t.nodes.length;i++) if(t.nodes[i]===container) return t.starts[i]+offset;
  // element container: offset counts child nodes — approximate to node start
  for(i=0;i<t.nodes.length;i++) if(container.contains&&container.contains(t.nodes[i])) return t.starts[i];
  return 0;
}
function sectionOf(node){
  var el=node.nodeType===3?node.parentElement:node;
  while(el){
    if(/^H[1-6]$/.test(el.nodeName)) return norm(el.textContent).trim();
    var p=el.previousElementSibling;
    while(p){
      var h=(p.matches&&p.matches('h1,h2,h3,h4,h5,h6'))?p:null;
      if(!h&&p.querySelectorAll){var hs=p.querySelectorAll('h1,h2,h3,h4,h5,h6');if(hs.length)h=hs[hs.length-1];}
      if(h) return norm(h.textContent).trim();
      p=p.previousElementSibling;
    }
    el=el.parentElement;
  }
  return null;
}
function findRange(doc,ann){
  var sel=ann.selector; if(!sel||!sel.exact) return null;
  var t=collectText(doc), nb=buildNorm(t.raw);
  var ex=norm(sel.exact), pre=norm(sel.prefix||''), suf=norm(sel.suffix||'');
  var whole=pre+ex+suf, idx=nb.nrm.indexOf(whole), nStart;
  if(idx>=0){ nStart=idx+pre.length; }
  else {
    // fall back to exact-only, disambiguated by nearest advisory position
    var from=0,best=-1,pos=(ann.position&&ann.position.start)||0,bestd=Infinity,at;
    while((at=nb.nrm.indexOf(ex,from))>=0){var d=Math.abs(nb.map[at]-pos);if(d<bestd){bestd=d;best=at;}from=at+1;}
    if(best<0) return null; nStart=best;
  }
  var rs=nb.map[nStart], re=nb.map[Math.min(nStart+ex.length-1,nb.map.length-1)]+1;
  return rawRange(doc,t,rs,re);
}
function buildAnchor(range){
  var t=collectText(idoc);
  var rs=rawOffset(t,range.startContainer,range.startOffset);
  var re=rawOffset(t,range.endContainer,range.endOffset);
  return {selector:{exact:norm(range.toString()),
    prefix:norm(t.raw.slice(Math.max(0,rs-CTX),rs)),
    suffix:norm(t.raw.slice(re,re+CTX))},
    section:sectionOf(range.startContainer), position:{start:rs,end:re}};
}

// ---- highlight painting (CSS Custom Highlight API, non-destructive) ----
var FALLBACK_WARNED=false;
function paint(activeId){
  var open=document.body.classList.contains('mzk-open');
  if(iwin&&iwin.CSS&&iwin.CSS.highlights&&iwin.Highlight){
    iwin.CSS.highlights.delete('mzk'); iwin.CSS.highlights.delete('mzk-active');
    if(!open) return;                       // drawer closed → no highlights, for a clean read
    var reg=[],act=[];
    RANGES.forEach(function(r,id){(id===activeId?act:reg).push(r);});
    if(reg.length) iwin.CSS.highlights.set('mzk',newHL(reg));
    if(act.length) iwin.CSS.highlights.set('mzk-active',newHL(act));
    return;
  }
  if(!open) return;                         // fallback path: don't add <mark>s when closed
  if(!FALLBACK_WARNED){FALLBACK_WARNED=true;
    console.warn('[annotate] CSS Custom Highlight API unavailable — falling back to <mark> wrapping (degraded).');}
  RANGES.forEach(function(r){try{var m=idoc.createElement('mark');m.style.background='rgba(245,197,24,.45)';r.surroundContents(m);}catch(e){}});
}
function newHL(ranges){var h=new iwin.Highlight();ranges.forEach(function(r){h.add(r);});return h;}

function anchorAll(){
  if(!idoc) return;
  RANGES.clear();
  var orphans=[];
  DATA.items.forEach(function(a){
    if(a.scope!=='selection'||!a.selector) return;
    if(a.status==='dismissed') return;
    var r=findRange(idoc,a);
    if(r) RANGES.set(a.id,r);
    else if(a.status==='pending'){
      // Only orphan a FRESH pending item whose quote can't be found — a genuine
      // re-render casualty. A follow-up on a thread that was already answered stays
      // reachable (a live question outranks a shifted anchor), so it isn't evicted
      // from the [pending] drain trigger.
      var answeredBefore=(a.turns||[]).some(function(t){return t.answer;});
      if(!answeredBefore) orphans.push(a.id);
    }
  });
  paint();
  renderDrawer();
  orphans.forEach(function(id){setStatus(id,'orphaned',true);});
}

// ---- drawer ----
function renderDrawer(){
  var RANK={pending:0,processing:1,orphaned:2,answered:3,distilled:4,dismissed:5};
  var rank=function(s){return s in RANK?RANK[s]:9;};   // NB: not `RANK[s]||9` — pending is 0 (falsy)
  var all=DATA.items.slice().sort(function(a,b){
    return (rank(a.status)-rank(b.status))||(idNum(b.id)-idNum(a.id));});   // status group, then newest first
  var pending=DATA.items.filter(function(a){return a.status==='pending';}).length;
  var items=all.filter(matchFilter);
  var base=pending+' pending'+(DATA.items.length?(' · '+DATA.items.length+' total'):'');
  countEl.textContent=FILTER?(items.length+' shown · '+base):base;
  if(!all.length){listEl.innerHTML='<div class=mzk-empty>No annotations yet.<br>Select text in the report to add one.</div>';return;}
  if(!items.length){listEl.innerHTML='<div class=mzk-empty>Nothing matches “'+esc(FILTER)+'”.</div>';return;}
  listEl.innerHTML='';
  items.forEach(function(a){
    var sel=a.selector||{}, raw=RAW.has(a.id);
    var card=document.createElement('div');card.className='mzk-card';card.dataset.id=a.id;
    var html='<div class=sec><span class="mzk-chip '+a.status+'">'+esc(a.status)+'</span> &nbsp;'+esc(_label(a))+'</div>';
    if(raw){
      html+='<pre class=mzk-raw>'+esc(RAWTEXT[a.id]||'loading…')+'</pre>';
    } else {
      if(a.scope==='selection'&&sel.exact) html+='<blockquote>'+esc(sel.exact)+'</blockquote>';
      (a.turns||[]).forEach(function(t){
        html+='<div class=prompt>'+esc(t.prompt||'(no prompt)')+'</div>';
        if(t.answer) html+='<div class=agent>'+mdToHtml(t.answer)+'</div>';
      });
    }
    html+='<div class=mzk-rowbtns>'
      +'<button data-act=resolve>Resolve</button>'
      +'<button data-act=dismiss>Dismiss</button>'
      +'<button data-act=reopen>Reopen</button>'
      +'<button data-act=raw>'+(raw?'View rendered':'View raw')+'</button>'
      +'<button data-act=delete>Delete</button></div>';
    if(!raw && a.status!=='dismissed')
      html+='<div class=mzk-follow>'
        +'<textarea rows=2 placeholder="Ask a follow-up on this passage…"></textarea>'
        +'<button data-act=followup class=primary>Ask follow-up</button></div>';
    card.innerHTML=html;
    card.addEventListener('click',function(e){
      var lnk=e.target&&e.target.closest?e.target.closest('a'):null;
      if(lnk){
        if(lnk.dataset&&lnk.dataset.note){   // note link → open in the report pane (fresh nav)
          e.preventDefault();e.stopPropagation();
          NAV=[];CURNOTE=null;showNote(lnk.dataset.note);}
        return;                              // web link → normal navigation; either way, don't focus
      }
      var act=e.target&&e.target.dataset?e.target.dataset.act:null;
      if(act==='followup'){
        e.stopPropagation();
        var ta=card.querySelector('.mzk-follow textarea');
        var v=ta&&ta.value.trim();
        if(!v){if(ta)ta.focus();return;}
        api('POST','/annotations/followup',{id:a.id,prompt:v}).then(reload);
        return;
      }
      if(act==='raw'){                       // toggle raw markdown ⇄ rendered for this card
        e.stopPropagation();
        if(RAW.has(a.id)){RAW.delete(a.id);renderDrawer();}
        else fetch('/annotations/raw/'+encodeURIComponent(a.id)).then(function(r){return r.text();})
          .then(function(t){RAWTEXT[a.id]=t;RAW.add(a.id);renderDrawer();}).catch(function(){});
        return;
      }
      if(act){e.stopPropagation();rowAction(a.id,act);return;}
      if(e.target&&e.target.tagName==='TEXTAREA') return;   // typing a follow-up, don't scroll
      focusAnnotation(a.id);
    });
    listEl.appendChild(card);
  });
}
function _label(a){
  if(a.scope==='document') return 'whole document';
  return a.section?('under “'+a.section+'”'):'(no section)';
}
function focusAnnotation(id){
  var r=RANGES.get(id); if(!r) return;
  try{var el=r.startContainer.nodeType===3?r.startContainer.parentElement:r.startContainer;
    if(el&&el.scrollIntoView) el.scrollIntoView({block:'center',behavior:'smooth'});}catch(e){}
  paint(id); setTimeout(function(){paint();},1400);
}
function rowAction(id,act){
  if(act==='delete'){ if(!confirm('Delete this annotation?'))return;
    api('POST','/annotations/delete',{id:id}).then(reload); return; }
  var map={resolve:'answered',dismiss:'dismissed',reopen:'pending'};
  setStatus(id,map[act]);
}
function setStatus(id,status,silent){
  var a=DATA.items.filter(function(x){return x.id===id;})[0];
  if(a) a.status=status;
  if(!silent) renderDrawer();
  return api('POST','/annotations',{id:id,status:status}).then(function(){if(silent)renderDrawer();});
}

// ---- selection -> ask button -> popover ----
function hideFloat(){if(floatEl){floatEl.remove();floatEl=null;}}
function hidePop(){if(popEl){popEl.remove();popEl=null;}}
function onSelect(){
  var s=iwin.getSelection();
  if(!s||s.isCollapsed||!s.toString().trim()){hideFloat();return;}
  var range=s.getRangeAt(0), rect=range.getBoundingClientRect(), off=iframe.getBoundingClientRect();
  hideFloat();
  floatEl=document.createElement('div');floatEl.id='mzk-float';
  floatEl.style.left=(off.left+rect.left+rect.width/2)+'px';
  floatEl.style.top=(off.top+rect.bottom)+'px';
  var b=document.createElement('button');b.textContent='+ Ask / Note';
  b.addEventListener('mousedown',function(e){e.preventDefault();});
  b.addEventListener('click',function(){var a=buildAnchor(range);hideFloat();openPopover(a,rect,off);});
  floatEl.appendChild(b);document.body.appendChild(floatEl);
}
function openPopover(anchor,rect,off){
  hidePop();
  popEl=document.createElement('div');popEl.className='mzk-pop';
  var top=off.top+(rect?rect.bottom:60), left=off.left+(rect?rect.left:60);
  popEl.style.top=Math.min(top,window.innerHeight-230)+'px';
  popEl.style.left=Math.min(left,window.innerWidth-320)+'px';
  var q=anchor&&anchor.selector?('“'+anchor.selector.exact.slice(0,140)+'”'):'Whole document';
  popEl.innerHTML='<div class=q>'+esc(q)+'</div><textarea placeholder="Ask a follow-up, request an expansion, flag a claim…"></textarea>'
    +'<div class=actions><button data-x=cancel>Cancel</button><button class=primary data-x=save>Save</button></div>';
  var ta=popEl.querySelector('textarea');
  popEl.querySelector('[data-x=cancel]').onclick=hidePop;
  popEl.querySelector('[data-x=save]').onclick=function(){
    var prompt=ta.value.trim(); if(!prompt){ta.focus();return;}
    var body=anchor?{scope:'selection',selector:anchor.selector,section:anchor.section,position:anchor.position,prompt:prompt}
                   :{scope:'document',prompt:prompt};
    api('POST','/annotations',body).then(function(){hidePop();reload();});
  };
  document.body.appendChild(popEl);ta.focus();
}

// ---- top bar ----
function docPrompt(){openPopover(null,null,{top:60,left:window.innerWidth-380});}
function flush(){
  api('POST','/annotations/flush',{}).then(function(res){
    var m=document.createElement('div');m.className='mzk-modal';
    m.innerHTML='<div class=box><b>Annotations saved.</b><p>Hand off to your agent — tell it:</p>'
      +'<p><code>'+esc(res.instruction)+'</code></p>'
      +'<p style="color:var(--mut)">File: <code>'+esc(res.path)+'</code><br>'
      +'The file is the source of truth — any agent can drain it (Claude Code /drain-report, MCP, or by hand).</p>'
      +'<div class=actions><button data-x=copy class=primary>Copy instruction</button><button data-x=close>Close</button></div></div>';
    m.querySelector('[data-x=close]').onclick=function(){m.remove();};
    m.querySelector('[data-x=copy]').onclick=function(){
      try{navigator.clipboard.writeText(res.instruction);}catch(e){}
      m.querySelector('[data-x=copy]').textContent='Copied ✓';};
    m.addEventListener('click',function(e){if(e.target===m)m.remove();});
    document.body.appendChild(m);
  });
}
function toggleDrawer(){document.body.classList.toggle('mzk-open');paint();}

// ---- in-pane note viewer (renders a note over the report; its wikilinks drill deeper) ----
function renderView(){
  var body=document.getElementById('mzk-view-body');
  body.innerHTML=VIEWRAW?('<pre class=mzk-raw>'+esc(CURMD)+'</pre>'):mdDoc(CURMD);
  body.scrollTop=0;
  document.getElementById('mzk-view-raw').textContent=VIEWRAW?'View rendered':'View raw';
}
function showNote(stem,push){
  fetch('/note/'+encodeURIComponent(stem)).then(function(r){if(!r.ok)throw 0;return r.text();}).then(function(md){
    if(push!==false && CURNOTE) NAV.push(CURNOTE);
    CURNOTE=stem; CURMD=md; VIEWRAW=false;   // new note always opens rendered (so its links work)
    renderView();
    document.getElementById('mzk-view-title').textContent=stem;
    document.getElementById('mzk-view-back').style.visibility=NAV.length?'visible':'hidden';
    document.body.classList.add('mzk-viewing');
  }).catch(function(){});
}
function toggleViewRaw(){VIEWRAW=!VIEWRAW;renderView();}
function closeNote(){document.body.classList.remove('mzk-viewing');NAV=[];CURNOTE=null;}
function backNote(){ if(NAV.length) showNote(NAV.pop(),false); else closeNote(); }

// ---- boot ----
function reload(){return api('GET','/annotations').then(function(d){DATA=d;anchorAll();});}
function iframeReady(){
  try{idoc=iframe.contentDocument;iwin=iframe.contentWindow;}catch(e){
    console.error('[annotate] cannot access report document (cross-origin?)',e);return;}
  try{var st=idoc.createElement('style');st.textContent=IFRAME_STYLE_TEXT;
    (idoc.head||idoc.documentElement).appendChild(st);}catch(e){}
  idoc.addEventListener('mouseup',function(){setTimeout(onSelect,0);});
  idoc.addEventListener('scroll',hideFloat,true);
  anchorAll();
}
document.getElementById('mzk-doc').onclick=docPrompt;
document.getElementById('mzk-flush').onclick=flush;
document.getElementById('mzk-toggle').onclick=toggleDrawer;
var qEl=document.getElementById('mzk-q');
if(qEl) qEl.addEventListener('input',function(){FILTER=qEl.value.trim().toLowerCase();renderDrawer();});
// resizable drawer: drag the grip on the seam; width persists across reloads
try{var sw=localStorage.getItem('mzk-drawer-w'); if(sw) document.documentElement.style.setProperty('--drawer-w',sw);}catch(e){}
var grip=document.getElementById('mzk-grip'), dragging=false;
if(grip){
  grip.addEventListener('mousedown',function(e){e.preventDefault();dragging=true;grip.classList.add('mzk-drag');
    document.body.style.userSelect='none';iframe.style.pointerEvents='none';});   // let the parent see mousemove over the iframe
  window.addEventListener('mousemove',function(e){
    if(!dragging)return;
    var w=Math.max(260,Math.min(window.innerWidth-e.clientX,Math.round(window.innerWidth*0.72)));
    document.documentElement.style.setProperty('--drawer-w',w+'px');});
  window.addEventListener('mouseup',function(){
    if(!dragging)return; dragging=false;grip.classList.remove('mzk-drag');
    document.body.style.userSelect='';iframe.style.pointerEvents='';
    try{localStorage.setItem('mzk-drawer-w',document.documentElement.style.getPropertyValue('--drawer-w'));}catch(e){}});
}
document.getElementById('mzk-view-report').onclick=closeNote;
document.getElementById('mzk-view-back').onclick=backNote;
document.getElementById('mzk-view-raw').onclick=toggleViewRaw;
document.getElementById('mzk-view-body').addEventListener('click',function(e){
  var lnk=e.target&&e.target.closest?e.target.closest('a'):null;
  if(lnk&&lnk.dataset&&lnk.dataset.note){e.preventDefault();showNote(lnk.dataset.note);}   // drill into the linked note
});
document.body.classList.add('mzk-open');
window.addEventListener('resize',hideFloat);
iframe.addEventListener('load',iframeReady);
// live refresh: poll /version; reflect an agent's drain / re-render without a manual reload
var VER=null, POLLING=false;
function pollVersion(){
  if(POLLING||document.hidden) return;
  POLLING=true;
  api('GET','/version').then(function(v){
    POLLING=false;
    if(!VER){VER=v;return;}
    var annChanged=v.ann!==VER.ann, repChanged=v.report!==VER.report;
    VER=v;
    if(repChanged){ reload().then(function(){ iframe.src='/report?v='+v.report; }); }
    else if(annChanged){ reload(); }
  },function(){POLLING=false;});
}
setInterval(pollVersion,1500);
reload();
})();
"""


def note_index(root: Path) -> dict:
    """Map wikilink stem -> repo-relative note path, so `[[links]]` in answers can render
    as real anchors. Stems are unique across pages/journals/sources (AGENTS rule 1); if a
    stem somehow appears twice, pages/ wins (globbed first, setdefault keeps the first)."""
    idx = {}
    for sub in ("pages", "journals", "sources"):
        d = root / sub
        if d.is_dir():
            for p in sorted(d.glob("*.md")):
                idx.setdefault(p.stem, "%s/%s" % (sub, p.name))
    return idx


def render_page(title: str, root: Path) -> str:
    body = (
        '<div id=mzk-bar>'
        '<span id=mzk-title>%s</span>'
        '<span id=mzk-count>…</span>'
        '<span class=mzk-spacer></span>'
        '<button id=mzk-doc title="Add a prompt about the whole report">+ Doc prompt</button>'
        '<button id=mzk-flush title="Save + show the drain instruction">Flush to agent</button>'
        '<button id=mzk-toggle>Annotations</button>'
        '</div>'
        '<iframe id=mzk-report src="/report"></iframe>'
        '<div id=mzk-view>'
        '<div id=mzk-view-bar>'
        '<button id=mzk-view-report>&larr; Report</button>'
        '<button id=mzk-view-back>&larr; Back</button>'
        '<span id=mzk-view-title></span>'
        '<span class=mzk-spacer></span>'
        '<button id=mzk-view-raw>View raw</button>'
        '</div>'
        '<div id=mzk-view-body></div>'
        '</div>'
        '<aside id=mzk-drawer>'
        '<div id=mzk-search><input id=mzk-q type=search autocomplete=off '
        'placeholder="Search annotations…"></div>'
        '<div id=mzk-list></div></aside>'
        '<div id=mzk-grip title="Drag to resize"></div>'
    ) % _html_escape(title)
    js = (ANNOT_JS.replace("IFRAME_STYLE_TEXT", json.dumps(IFRAME_STYLE))
                  .replace("NOTES_JSON", json.dumps(note_index(root))))
    return (
        "<!doctype html>\n<html lang=en>\n<head>\n<meta charset=utf-8>\n"
        "<meta name=viewport content='width=device-width,initial-scale=1'>\n"
        "<title>Annotate — %s</title>\n<style>%s</style>\n</head>\n<body>\n%s\n"
        "<script>%s</script>\n</body>\n</html>\n"
    ) % (_html_escape(title), ANNOT_CSS, body, js)


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


# ------------------------------------------------------------------- the server

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    html_path = None            # set by cmd_serve before serve_forever
    ann_path = None
    root = None
    lock = threading.Lock()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s %s\n" % (self.command, self.path))

    def _send(self, code, body, ctype):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def _read_json(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            return json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return {}

    def _fresh_meta(self):
        return {"report": _rel(self.html_path, self.root),
                "created": datetime.now().strftime("%Y-%m-%d"),
                "title": report_title(self.html_path)}

    def _version(self):
        # cheap change-signal for the client poller: mtimes of the two files it mirrors,
        # so an agent's out-of-band write to annotations.md (or a re-render) is noticed
        def mt(p):
            try:
                return os.stat(p).st_mtime_ns
            except OSError:
                return 0
        return {"ann": mt(self.ann_path), "report": mt(self.html_path)}

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, render_page(report_title(self.html_path), self.root), "text/html; charset=utf-8")
        elif path == "/report":
            self._send(200, self.html_path.read_bytes(), "text/html; charset=utf-8")
        elif path.startswith("/note/"):
            # peek a linked note (raw markdown, new tab) — resolved strictly through the
            # note index, so only real note stems are servable (no path traversal)
            rel = note_index(self.root).get(unquote(path[len("/note/"):]))
            if rel:
                self._send(200, (self.root / rel).read_bytes(), "text/plain; charset=utf-8")
            else:
                self._send(404, b"unknown note", "text/plain")
        elif path.startswith("/annotations/raw/"):
            text = self.ann_path.read_text(encoding="utf-8") if self.ann_path.exists() else ""
            block = raw_entry(text, unquote(path[len("/annotations/raw/"):]))
            if block:
                self._send(200, block, "text/plain; charset=utf-8")
            else:
                self._send(404, b"unknown annotation", "text/plain")
        elif path == "/annotations":
            meta, items = load_annotations(self.ann_path)
            self._json({"meta": meta, "items": items})
        elif path == "/version":
            self._json(self._version())
        elif path == "/favicon.ico":
            self._send(204, b"", "text/plain")
        else:
            self._static(unquote(path.lstrip("/")))

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/annotations":
            self._upsert()
        elif path == "/annotations/followup":
            self._followup()
        elif path == "/annotations/delete":
            self._delete()
        elif path == "/annotations/flush":
            self._flush()
        else:
            self._send(404, b"not found", "text/plain")

    def _static(self, relpath):
        base = self.html_path.parent.resolve()
        target = (base / relpath).resolve()
        if target != base and base not in target.parents:
            self._send(403, b"forbidden", "text/plain")
            return
        if not target.is_file():
            self._send(404, b"not found", "text/plain")
            return
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self._send(200, target.read_bytes(), ctype)

    def _upsert(self):
        data = self._read_json()
        with self.lock:
            meta, items = load_annotations(self.ann_path)
            if not meta:
                meta = self._fresh_meta()
            rec = None
            if data.get("id"):
                for a in items:
                    if a["id"] == data["id"]:
                        for k in UPDATABLE:
                            if k in data:
                                a[k] = data[k]
                        rec = a
                        break
            if rec is None:
                data["id"] = data.get("id") or _next_id(items)
                rec = _normalize_new(data)
                items.append(rec)
            dump_annotations(self.ann_path, meta, items)
        self._json(rec)

    def _followup(self):
        # Append a new conversation turn to an existing annotation and re-open it to
        # `pending` — a new unanswered turn — so it re-enters the drain loop (the
        # emit-on-rise pending-count watcher fires). The drain fills the open turn.
        data = self._read_json()
        tid = data.get("id")
        prompt = (data.get("prompt") or "").strip()
        if not tid or not prompt:
            self._json({"ok": False, "error": "id and non-empty prompt required"}, 400)
            return
        rec = None
        with self.lock:
            meta, items = load_annotations(self.ann_path)
            for a in items:
                if a.get("id") == tid:
                    a.setdefault("turns", []).append({"prompt": prompt, "answer": None})
                    a["status"] = "pending"
                    rec = a
                    break
            if rec is not None:
                dump_annotations(self.ann_path, meta or self._fresh_meta(), items)
        if rec is None:
            self._json({"ok": False, "error": "unknown id: %s" % tid}, 404)
        else:
            self._json(rec)

    def _delete(self):
        tid = self._read_json().get("id")
        with self.lock:
            meta, items = load_annotations(self.ann_path)
            items = [a for a in items if a.get("id") != tid]
            dump_annotations(self.ann_path, meta or self._fresh_meta(), items)
        self._json({"ok": True, "id": tid})

    def _flush(self):
        with self.lock:
            meta, items = load_annotations(self.ann_path)
            meta = meta or self._fresh_meta()
            meta["flushed"] = datetime.now().astimezone().isoformat(timespec="seconds")
            dump_annotations(self.ann_path, meta, items)
        rel = _rel(self.ann_path, self.root)
        self._json({"path": str(self.ann_path), "rel": rel,
                    "instruction": "drain %s per the mozak-report-annotation-loop" % rel})


def is_headless_remote() -> bool:
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"):
        return True
    if any(os.environ.get(v) for v in ("VSCODE_IPC_HOOK_CLI", "REMOTE_CONTAINERS", "CODESPACES")):
        return True
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return True
    return False


def open_browser(url, force=False, suppress=False):
    if suppress:
        return
    if force or not is_headless_remote():
        try:
            webbrowser.open(url)
        except Exception:
            pass


def _bind(port):
    """Bind 127.0.0.1 ONLY — local artifact, never outward (AGENTS rule 10).
    Walk a small range if the preferred port is busy, then fall back to ephemeral."""
    for p in (list(range(port, port + 11)) if port else [0]):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            return srv, srv.server_address[1]
        except OSError:
            continue
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    return srv, srv.server_address[1]


def cmd_serve(root: Path, html: str, port: int, browser: str) -> int:
    html_path = Path(html).resolve()
    if not html_path.is_file():
        sys.exit("error: not a file: %s" % html)
    ann = annotations_path(html_path, root)
    ann.parent.mkdir(parents=True, exist_ok=True)
    if not ann.exists():
        dump_annotations(ann, {"report": _rel(html_path, root),
                               "created": datetime.now().strftime("%Y-%m-%d"),
                               "title": report_title(html_path)}, [])
    else:
        # single-owner recovery: this server is the sole process, and nothing is mid-drain
        # at startup, so any leftover `processing` is stale (a drain that died) — requeue it.
        meta0, items0 = load_annotations(ann)
        stale = [a for a in items0 if a.get("status") == "processing"]
        if stale:
            for a in stale:
                a["status"] = "pending"
            dump_annotations(ann, meta0, items0)
            print("  reset %d stale 'processing' → pending" % len(stale))
    Handler.html_path, Handler.ann_path, Handler.root = html_path, ann, root
    srv, bound = _bind(port)
    url = "http://127.0.0.1:%d/" % bound
    print("\n  ▶ %s\n" % url)
    if is_headless_remote():
        print("  remote/VM detected — open that URL in your LOCAL browser.")
        print("  VS Code Remote-SSH auto-forwards the localhost port (Ports panel → forward %d)." % bound)
    print("  report:      %s" % html_path)
    print("  annotations: %s" % ann)
    print("  Ctrl-C to stop.\n")
    open_browser(url, force=(browser == "force"), suppress=(browser == "no"))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped.")
    finally:
        srv.server_close()
    return 0


def cmd_list(root: Path, html: str, status: str = None) -> int:
    """Print the annotation queue. `status` filters to one lifecycle state — e.g.
    `--status pending` dumps only open items, so a drain reads just the working set
    (its token cost scales with active work, not total history)."""
    ann = annotations_path(Path(html).resolve(), root)
    if not ann.exists():
        print("no annotations yet: %s" % ann)
        return 0
    _, items = load_annotations(ann)
    if status:
        items = [a for a in items if a.get("status") == status]
    for a in sorted(items, key=lambda a: STATUS_ORDER.get(a["status"], 9)):
        turns = a.get("turns") or []
        unans = sum(1 for t in turns if not t.get("answer"))
        print("[%s] %s  %s  (%d turn%s%s)" % (
            a["status"], a["id"], _label(a), len(turns),
            "" if len(turns) == 1 else "s",
            ", %d unanswered" % unans if unans else ""))
        sel = a.get("selector") or {}
        if sel.get("exact"):
            print("    “%s”" % sel["exact"][:90])
        for j, t in enumerate(turns, 1):
            if t.get("prompt"):
                print("    %d. prompt: %s" % (j, t["prompt"][:200].replace("\n", " ")))
            if t.get("answer"):
                print("       agent:  %s" % t["answer"][:200].replace("\n", " "))
    label = "%d %s annotation(s)" % (len(items), status) if status else "%d annotation(s)" % len(items)
    print("\n%s — %s" % (label, ann))
    return 0


# --------------------------------------------------------------- optional MCP lens

# A minimal JSON-RPC-2.0-over-stdio MCP server in pure stdlib (the official SDK is a
# third-party dep, and this is core tooling — stdlib only). Read-only: it exposes the queue to any MCP harness
# (Claude Code, Cursor, Cline…) without the tool ever becoming a dependency — the file
# stays the source of truth. Register per SETUP.md §5. stdout is the protocol channel;
# everything human goes to stderr.

MCP_TOOLS = [
    {"name": "list_annotations",
     "description": "List annotations on the served report (status, section, quoted text, "
                    "opening prompt, and turn/unanswered counts).",
     "inputSchema": {"type": "object", "properties": {
         "status": {"type": "string",
                    "description": "optional filter: pending|processing|answered|distilled|orphaned|dismissed"}}}},
    {"name": "get_annotation",
     "description": "Get one annotation by id, including its text-quote anchor and the "
                    "full conversation thread (turns, each a prompt + optional agent answer).",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}},
                     "required": ["id"]}},
]


def _rpc_ok(mid, result):
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def _rpc_err(mid, code, message):
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def _mcp_content(obj, is_error=False):
    r = {"content": [{"type": "text", "text": json.dumps(obj, ensure_ascii=False, indent=2)}]}
    if is_error:
        r["isError"] = True
    return r


def _mcp_view(a):
    sel = a.get("selector") or {}
    turns = a.get("turns") or []
    return {"id": a["id"], "status": a["status"], "scope": a.get("scope"),
            "section": a.get("section"), "quote": sel.get("exact"),
            "prompt": (turns[0]["prompt"] if turns else ""),
            "turns": len(turns),
            "unanswered": sum(1 for t in turns if not t.get("answer")),
            "answered": bool(turns) and all(t.get("answer") for t in turns)}


def _latest_annotations(root: Path):
    cands = list((root / "_generated" / "presentations").glob("*/annotations.md"))
    cands += list((root / "_generated" / "annotations").glob("*/annotations.md"))
    cands = [p for p in cands if p.is_file()]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def cmd_mcp(root: Path, html=None) -> int:
    fixed = annotations_path(Path(html).resolve(), root) if html else None
    sys.stderr.write("annotate mcp: %s\n"
                     % (fixed if fixed else "latest render under _generated/ (dynamic)"))

    def current():
        return fixed if fixed else _latest_annotations(root)

    def handle(msg):
        mid, method, params = msg.get("id"), msg.get("method"), (msg.get("params") or {})
        if method == "initialize":
            return _rpc_ok(mid, {"protocolVersion": params.get("protocolVersion", "2025-06-18"),
                                 "capabilities": {"tools": {}},
                                 "serverInfo": {"name": "annotate", "version": "2"}})
        if method in ("notifications/initialized", "initialized") or method is None:
            return None                              # a notification / a response — no reply
        if method == "ping":
            return _rpc_ok(mid, {})
        if method == "tools/list":
            return _rpc_ok(mid, {"tools": MCP_TOOLS})
        if method == "resources/list":
            return _rpc_ok(mid, {"resources": []})
        if method == "prompts/list":
            return _rpc_ok(mid, {"prompts": []})
        if method == "tools/call":
            name, args = params.get("name"), (params.get("arguments") or {})
            ann = current()                          # re-resolve each call — reflects live edits
            _, items = load_annotations(ann) if ann else ({}, [])
            report = _rel(ann, root) if ann else None
            if name == "list_annotations":
                st = args.get("status")
                view = [_mcp_view(a) for a in items if not st or a["status"] == st]
                return _rpc_ok(mid, _mcp_content(
                    {"report": report, "count": len(view), "annotations": view}))
            if name == "get_annotation":
                a = next((x for x in items if x["id"] == args.get("id")), None)
                if a is None:
                    return _rpc_ok(mid, _mcp_content(
                        {"error": "no annotation with id %r" % args.get("id"), "report": report},
                        is_error=True))
                return _rpc_ok(mid, _mcp_content(a))
            return _rpc_err(mid, -32602, "unknown tool: %s" % name)
        return _rpc_err(mid, -32601, "method not found: %s" % method)

    def emit(resp):
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(msg, list):                    # JSON-RPC batch
            for m in msg:
                emit(handle(m))
        else:
            emit(handle(msg))
    return 0


KNOWN_CMDS = ("serve", "list", "mcp")


def main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] not in KNOWN_CMDS and not argv[0].startswith("-"):
        argv = ["serve"] + argv                     # bare-path shim: `annotate.py <file>`
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                    help="repo root (default: parent of tools/)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_serve = sub.add_parser("serve")
    p_serve.add_argument("html")
    p_serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    p_serve.add_argument("--no-browser", action="store_true", help="never open a browser")
    p_serve.add_argument("--open", action="store_true", help="open a browser even on a remote/VM")
    p_list = sub.add_parser("list")
    p_list.add_argument("html")
    p_list.add_argument("--status", default=None,
                        help="only show this status (pending|processing|answered|distilled|orphaned|dismissed)")
    p_mcp = sub.add_parser("mcp")
    p_mcp.add_argument("html", nargs="?", default=None)
    args = ap.parse_args(argv)
    if args.cmd == "list":
        return cmd_list(args.root, args.html, args.status)
    if args.cmd == "mcp":
        return cmd_mcp(args.root, args.html)
    browser = "no" if args.no_browser else ("force" if args.open else "auto")
    return cmd_serve(args.root, args.html, args.port, browser)


if __name__ == "__main__":
    sys.exit(main())
