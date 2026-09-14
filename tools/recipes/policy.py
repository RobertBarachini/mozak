#!/usr/bin/env python3
# recipe: policy
# input:  .personal-shared/acquisition-policy.toml — created as a skeleton if absent
# output: `check` gates acquisition on informed consent and prints the open decisions as questions
# needs:  nothing (stdlib; tomllib is 3.11+)
# usage:  python3 tools/recipes/policy.py check [--json] | set key=value… | show [--explain]  [--root DIR]

"""Resolve the effective web-acquisition policy, and gate acquisition on consent.

The template is used from many jurisdictions and knows none of them, so it ships
cautious and does not decide what is lawful for you. One setting,
`advanced_acquisition`, is your own judgement about your own context. The rest are
anonymity and politeness toward hosts — not law.

Three rules this file enforces rather than merely documents:

* **The agent never answers for you.** `check` creates the policy file as a
  commented skeleton when it is absent, and nothing more. Identity, contact and
  the consent date are yours.
* **Nothing acquires until you have consented.** `check` exits non-zero, and every
  fetch recipe refuses, until `[consent].acknowledged` carries a date recorded
  after you have seen each decision — in particular what leaves your machine.
* **Consent is asked, not relayed.** While the gate is closed, `check` prints the
  open decisions as *questions*, each option explained, each with the exact
  `set` command that records it (`--json` gives the same as data). An agent asks
  you those — through its harness's structured-question mechanism when it has
  one, in plain text otherwise — and records your answers with `set key=value`.
  It never pre-answers or infers one. That is what makes the consent informed
  rather than a paragraph that scrolls past.

Run `check` at the start of every session, beside `graph.py check` (AGENTS rule 7).
Every fetch records the effective values it ran under. Overrides govern acquisition
behaviour only: they cannot loosen AGENTS rule 10, the `.private/` never-read rule,
or the two-pass capture toll. Conventions: AGENTS.md.
"""

import argparse
import http.cookiejar
import json
import re
import sys
import tomllib
from datetime import date
from pathlib import Path

REL = ".personal-shared/acquisition-policy.toml"

# The most common browser string on the web, chosen so a fetch blends in. Bump the
# version occasionally — an old UA is itself distinctive.
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
DECLARED_UA = "mozak-research/1.0 (personal research; user-directed agent)"

# Shipped defaults. A top-level scalar is a single knob; a dict is a [section].
DEFAULTS = {
    "advanced_acquisition": False,
    "identity": {"user_agent": "browser", "contact": "",
                 "cookies_file": ".personal-shared/cookies.txt"},
    "budget": {"max_fetches_per_run": 50, "min_delay_seconds": 1.0,
               "max_bytes_per_fetch": 25_000_000},
    "consent": {"acknowledged": ""},
}

# The skeleton `check` writes when the file is absent. One home for the wording: this
# instance's file is an instance of it, and a test asserts its keys match DEFAULTS.
TEMPLATE = '''# Web-acquisition policy — read by tools/recipes/policy.py.
# Local-only, gitignored, never upstreamed. The agent created this skeleton and will
# never fill a user field in it. Rationale for each knob: pages/mozak-web-acquisition-ladder.md
#
# Scope: these govern ACQUISITION BEHAVIOUR ONLY. They cannot loosen AGENTS rule 10
# (never publish outward), the .private/ never-read rule, or the two-pass capture toll.

# Your judgement about your own context. The template ships cautious because it is
# used from many jurisdictions and knows none of them; it does not decide what is
# lawful for you.
#   false — rungs T0-T2: official sources, polite fetch, archives
#   true  — every rung is available as its recipe lands, including TLS-fingerprint
#           impersonation, a real browser, and reuse of your own logged-in session
advanced_acquisition = false

[identity]
# "browser" (default) — present as the most common browser. This is for ANONYMITY, not
#   access: the User-Agent does not affect whether you are blocked (that is decided at
#   the TLS layer), but a distinctive one is a cross-site tracking beacon, and
#   researchers and journalists may have adversaries. Blend in by default.
# "declared" — identify as this tool. For people who prefer to be identifiable to site
#   operators. Consciously traceable across every site you touch.
# any other string — sent verbatim, for a source that mandates a specific format.
user_agent = "browser"
# Optional e-mail. WHAT IT IS FOR: a few scholarly/government registries ask a client to
# name a contact so an operator can e-mail you if it misbehaves, instead of blocking your
# address. That reachability is what a "polite pool" trades for. Three states:
#   empty (default) — nothing identifying leaves your machine. Unpaywall is skipped (it
#       requires an address); Crossref serves you from its public pool (5 req/s — plenty
#       for a person). Nothing else changes.
#   a real address — sent ONLY by source-specific recipes that require or reward one
#       (today: Crossref's polite pool and Unpaywall, via scholar-lookup; SEC EDGAR, which
#       mandates one, if a recipe for it lands), each saying so when it does. Never by the
#       general page fetch, never to ordinary sites, never logged by value. Ideal: a
#       dedicated research alias you actually read (Proton, a forwarding address) —
#       reachable, and your primary inbox stays out of third-party logs.
#   a fake or no-reply address — refused by `set`, and not sent even if hand-edited in: it
#       fabricates identity, takes the courtesy under false pretences, shares one rate-limit
#       bucket with everyone who typed the same fake (Crossref keys on the address), and
#       Unpaywall rejects placeholders anyway.
contact = ""
# Optional Netscape-format cookie jar — what the "cookies.txt" browser extensions export,
# and the same format yt-dlp reads. If the file exists AND advanced_acquisition is true,
# its cookies are sent to the sites they belong to: rung T5, your own logged-in session,
# for research behind your own accounts. Export it from a PRIVATE WINDOW logged into only
# the sites the work needs — never from your daily profile: the jar holds live session
# tokens for every site in it, and gitignore is a negative guarantee. Tools read it in
# place, never copy it into _generated/, never log a value, never write it back (re-export
# when sessions go stale). Relative paths are from the repo root; "" disables it.
cookies_file = ".personal-shared/cookies.txt"

[budget]
# Politeness toward hosts and safety for your disk — not law.
min_delay_seconds = 1.0
max_fetches_per_run = 50
max_bytes_per_fetch = 25000000

[consent]
# Informed consent. Until a date (YYYY-MM-DD) is recorded here, no web acquisition runs.
# `policy.py check` presents each decision above as a question with its options explained;
# your agent asks you those and records your answers with `policy.py set` — consent last —
# and never answers for you. Or answer them yourself: `policy.py set consent.acknowledged=today`.
acknowledged = ""
'''

RUNGS = ("T0", "T1", "T2", "T3", "T4", "T5", "T6")

# The decisions a human makes before anything fetches. One home for the wording; an
# agent presents these (structured prompt if its harness has one, plain text otherwise)
# and records the answer with `set`. Order matters: consent comes last, after the rest.
QUESTIONS = [
    {"key": "advanced_acquisition",
     "question": "How far may the agent climb the acquisition ladder without asking you each time?",
     "options": [
         {"value": False, "label": "Cautious — rungs T0–T2 (shipped default)",
          "explain": "Official sources and APIs, polite plain fetches, web archives. No TLS impersonation, "
                     "no browser automation, no use of your logins. The template ships this because it is "
                     "used from many jurisdictions and knows none of them — it does not decide what is "
                     "lawful for you."},
         {"value": True, "label": "Advanced — every rung as its recipe exists",
          "explain": "Adds TLS-handshake impersonation (T3), a disposable sandboxed browser (T4), and your "
                     "own cookie jar for logged-in sessions (T5, if you drop one at "
                     ".personal-shared/cookies.txt). Your judgement that this is fine in your context. "
                     "The toolchain still treats a host's 403/429/challenge as an answer and never uses "
                     "solvers, fake accounts or IP rotation."}]},
    {"key": "identity.user_agent",
     "question": "How should fetches present themselves to the sites they read?",
     "options": [
         {"value": "browser", "label": "Blend in as the most common browser (shipped default)",
          "explain": "The User-Agent does not affect whether you are blocked — that is decided at the TLS "
                     "layer — but a distinctive one is a cross-site tracking beacon, and researchers and "
                     "journalists may have adversaries."},
         {"value": "declared", "label": "Identify as this research tool",
          "explain": "For people who prefer site operators to know a research tool is reading. Consciously "
                     "traceable across every site you touch."}]},
    {"key": "identity.contact",
     "question": "Provide a contact e-mail for the few registries that ask for one?",
     "context": "What it is for: a few scholarly/government registries ask a client to name a contact "
                "so an operator can e-mail you if it misbehaves, instead of blocking your address. "
                "That reachability is what a \"polite pool\" trades for. It is never sent by the "
                "general page fetch, never to ordinary sites, and never logged by value.",
     "free_text": True, "example": "research-alias@proton.me",
     "options": [
         {"value": "", "label": "No — leave it empty (shipped default)",
          "explain": "Nothing identifying leaves your machine. Unpaywall is skipped (it requires an "
                     "address); Crossref serves you from its public pool — 5 req/s, plenty for a person. "
                     "Nothing else changes."},
         {"value": "<your e-mail>", "label": "Yes — a real address you actually read",
          "explain": "Sent only by the source-specific recipes that require or reward one — today "
                     "Crossref's polite pool and Unpaywall via scholar-lookup; SEC EDGAR, which mandates "
                     "one, if a recipe for it lands — each saying so when it does. Ideal: a dedicated "
                     "research alias (Proton, a forwarding address) — reachable, with your primary inbox "
                     "out of third-party logs. A fake or no-reply address is refused: it fabricates "
                     "identity, shares one rate-limit bucket with everyone who typed the same fake, and "
                     "Unpaywall rejects placeholders anyway."}]},
    {"key": "consent.acknowledged",
     "question": "You have now seen each setting and what leaves your machine; until consent is "
                 "recorded, no recipe fetches. Record your informed consent?",
     "options": [
         {"value": "today", "label": "Yes — record today's date",
          "explain": "Any setting can be changed later; the date records that you reviewed them."},
         {"value": None, "label": "Not yet",
          "explain": "Leave the file as it is; edit it yourself, or come back to this later. Acquisition "
                     "stays deferred."}]},
]


# A contact exists so a source can reach you. These read as "nobody is home".
_NOREPLY_LOCALS = ("noreply", "no-reply", "no_reply", "donotreply", "do-not-reply", "nobody",
                   "null", "none", "fake", "invalid", "example")
_PLACEHOLDER_DOMAINS = ("example.com", "example.org", "example.net", "localhost")
_PLACEHOLDER_SUFFIXES = (".example", ".invalid", ".test", ".localhost", ".local")


def looks_reachable(addr: str) -> tuple[bool, str]:
    """(ok, why-not). Empty is a valid answer — it means no contact. The check is a
    guard against placeholders, not a deliverability test."""
    a = (addr or "").strip().lower()
    if not a:
        return True, ""
    if a.count("@") != 1 or " " in a:
        return False, "not an e-mail address"
    local, domain = a.split("@")
    if not local or "." not in domain:
        return False, "not an e-mail address"
    if domain in _PLACEHOLDER_DOMAINS or domain.endswith(_PLACEHOLDER_SUFFIXES):
        return False, f"'{domain}' is a reserved or placeholder domain"
    base = local.split("+", 1)[0]
    if base in _NOREPLY_LOCALS:
        return False, f"'{local}@' reads as a no-reply address"
    return True, ""


def _get(cfg: dict, dotted: str):
    s, _, k = dotted.partition(".")
    return cfg[s][k] if k else cfg[s]


def questions(cfg: dict) -> list[dict]:
    """The open decisions with their current values and the command that records each."""
    out = []
    for q in QUESTIONS:
        cur = _get(cfg, q["key"])
        opts = []
        for o in q["options"]:
            v = o["value"]
            shown = ("today" if q["key"] == "consent.acknowledged" and v == "today"
                     else v if isinstance(v, str) else json.dumps(v))
            apply = (None if v is None
                     else f"python3 tools/recipes/policy.py set {q['key']}={shown}")
            opts.append({**o, "current": (v == cur) if v is not None else False, "apply": apply})
        out.append({**q, "current": cur, "options": opts})
    return out


def render_questions(qs: list[dict]) -> str:
    lines = [f"Decisions that need you — {len(qs)} of them. Answer each; the command after every",
             "option records that answer. Nothing fetches until the last one is recorded.", ""]
    for i, q in enumerate(qs, 1):
        lines.append(f"{i}. {q['question']}")
        if q.get("context"):
            lines.append(f"   {q['context']}")
        for o in q["options"]:
            mark = " (current)" if o["current"] else ""
            lines.append(f"   - {o['label']}{mark}")
            lines.append(f"       {o['explain']}")
            if o["apply"]:
                lines.append(f"       → {o['apply']}")
        if q.get("free_text"):
            lines.append(f"   (free text: e.g. `python3 tools/recipes/policy.py set {q['key']}={q['example']}`)")
        lines.append("")
    return "\n".join(lines)


def _render_toml(val) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return repr(val)
    return json.dumps(val)                    # TOML basic strings accept JSON-style escapes


def set_values(root: Path, assignments: list[str]) -> list[str]:
    """Record answers in the policy file, preserving its comments. Creates the skeleton
    if absent. Validates by reloading; on any error the previous content is restored."""
    path = root / REL
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(TEMPLATE, encoding="utf-8")
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines()
    changed = []
    for a in assignments:
        if "=" not in a:
            raise PolicyError(f"error: expected key=value, got {a!r}.")
        dotted, _, raw = a.partition("=")
        dotted, raw = dotted.strip(), raw.strip()
        section, _, key = dotted.partition(".")
        default = DEFAULTS.get(section) if not key else (DEFAULTS.get(section) or {}).get(key)
        if default is None or (key and section not in DEFAULTS) or (not key and isinstance(DEFAULTS.get(section), dict)):
            raise PolicyError(f"error: unknown policy key '{dotted}'.")
        if dotted == "consent.acknowledged" and raw.lower() in ("today", "now"):
            raw = date.today().isoformat()
        if isinstance(default, bool):
            if raw.lower() not in ("true", "false"):
                raise PolicyError(f"error: {dotted} must be true or false, got {raw!r}.")
            val = raw.lower() == "true"
        elif isinstance(default, int):
            val = int(raw)
        elif isinstance(default, float):
            val = float(raw)
        else:
            val = raw.strip("\"'")
        if dotted == "identity.contact":
            ok, why = looks_reachable(val)
            if not ok:
                raise PolicyError(f"error: identity.contact={val!r} — {why}. The field exists so a "
                                  f"source can reach you; use a real, dedicated alias, or leave it empty.")
        rendered = f"{key or section} = {_render_toml(val)}"
        target_section = section if key else None
        cur_section, done = None, False
        for i, line in enumerate(lines):
            m = re.match(r"^\s*\[(\w+)\]\s*$", line)
            if m:
                cur_section = m.group(1)
                continue
            if cur_section == target_section and re.match(rf"^\s*{re.escape(key or section)}\s*=", line):
                lines[i], done = rendered, True
                break
        if not done:
            if target_section is None:
                first = next((i for i, l in enumerate(lines) if re.match(r"^\s*\[", l)), len(lines))
                lines.insert(first, rendered)
            else:
                hdr = next((i for i, l in enumerate(lines) if re.match(rf"^\s*\[{target_section}\]", l)), None)
                if hdr is None:
                    lines += ["", f"[{target_section}]", rendered]
                else:
                    lines.insert(hdr + 1, rendered)
        changed.append(f"{dotted} = {_render_toml(val)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        load(root)
    except SystemExit:
        path.write_text(original, encoding="utf-8")
        raise
    return changed
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class PolicyError(SystemExit):
    pass


def _coerce(default, val, where: str):
    want, got = type(default), type(val)
    if want is float and got is int:
        return float(val)
    if want is not got:
        raise PolicyError(f"error: {where} must be {want.__name__}, got {got.__name__} in {REL}.")
    return val


def _merge(base: dict, over: dict) -> dict:
    """Merge overrides onto defaults. Unknown keys are an error, not a silent no-op."""
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for key, val in over.items():
        if key not in out:
            raise PolicyError(f"error: unknown policy key '{key}' in {REL}. "
                              f"Known: {', '.join(sorted(base))}.")
        if isinstance(out[key], dict):
            if not isinstance(val, dict):
                raise PolicyError(f"error: [{key}] must be a table in {REL}.")
            for k2, v2 in val.items():
                if k2 not in out[key]:
                    raise PolicyError(f"error: unknown key '{k2}' in [{key}] of {REL}. "
                                      f"Known: {', '.join(sorted(base[key]))}.")
                out[key][k2] = _coerce(out[key][k2], v2, f"[{key}].{k2}")
        else:
            if isinstance(val, dict):
                raise PolicyError(f"error: '{key}' is a single value, not a table, in {REL}.")
            out[key] = _coerce(out[key], val, key)
    return out


def _validate(cfg: dict) -> None:
    b = cfg["budget"]
    if b["min_delay_seconds"] < 0:
        raise PolicyError("error: [budget].min_delay_seconds must be >= 0.")
    if b["max_fetches_per_run"] < 1:
        raise PolicyError("error: [budget].max_fetches_per_run must be >= 1.")
    if b["max_bytes_per_fetch"] < 1024:
        raise PolicyError("error: [budget].max_bytes_per_fetch must be >= 1024.")
    ack = cfg["consent"]["acknowledged"].strip()
    if ack and not DATE.fullmatch(ack):
        raise PolicyError(f"error: [consent].acknowledged must be a date, YYYY-MM-DD, in {REL}.")


def _deviations(cfg: dict) -> list[str]:
    out = []
    for k, v in cfg.items():
        if k == "consent":
            continue                       # the date is consent, not a deviation
        if isinstance(v, dict):
            out += [f"{k}.{k2}={'<set>' if k2 == 'contact' and v[k2] else v[k2]}"
                    for k2 in v if v[k2] != DEFAULTS[k][k2]]
        elif v != DEFAULTS[k]:
            out.append(f"{k}={v}")
    return sorted(out)


def load(root: Path) -> tuple[dict, str]:
    """Return (effective policy, provenance string stamped into every fetch record).
    The contact address itself never appears in the provenance string."""
    path = root / REL
    if not path.is_file():
        cfg = _merge(DEFAULTS, {})
        _validate(cfg)
        return cfg, "defaults (no acquisition-policy.toml)"
    try:
        over = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise PolicyError(f"error: {REL} is not valid TOML: {e}")
    cfg = _merge(DEFAULTS, over)
    _validate(cfg)
    dev = _deviations(cfg)
    if not dev:
        return cfg, f"defaults ({REL} present, no deviations)"
    return cfg, f"defaults + {REL}: " + ", ".join(dev)


def gate(cfg: dict) -> str | None:
    """None when acquisition may proceed; otherwise the message to show and stop."""
    if DATE.fullmatch(cfg["consent"]["acknowledged"].strip()):
        return None
    return (f"error: web acquisition is deferred until consent is recorded in {REL}.\n"
            f"  Run `python3 tools/recipes/policy.py check` — it lists the decisions that need you,\n"
            f"  each option explained. Your agent should ask you those and record your answers with\n"
            f"  `policy.py set key=value`; it must never answer them for you.")


def user_agent(cfg: dict) -> str:
    """Never includes the contact address, in any mode."""
    mode = cfg["identity"]["user_agent"]
    if mode == "browser":
        return BROWSER_UA
    if mode == "declared":
        return DECLARED_UA
    return mode


def cookies_path(cfg: dict, root: Path):
    """(path | None, status). The status string is safe to log: it names the file and
    the gate, never a cookie. A jar is rung T5 and so needs `advanced_acquisition`."""
    rel = cfg["identity"]["cookies_file"].strip()
    if not rel:
        return None, "cookies disabled"
    path = Path(rel) if Path(rel).is_absolute() else root / rel
    if not path.is_file():
        return None, "no cookie jar"
    if not cfg["advanced_acquisition"]:
        return None, (f"cookie jar present at {rel} but advanced_acquisition=false — not sent; "
                      f"your logins are rung T5, which that setting unlocks")
    return path, f"cookie jar {rel}"


def cookie_jar(cfg: dict, root: Path):
    """(MozillaCookieJar | None, status) — loaded, expired entries kept (sites lie about
    expiry, and the user decides what to export)."""
    path, status = cookies_path(cfg, root)
    if path is None:
        return None, status
    jar = http.cookiejar.MozillaCookieJar(str(path))
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except Exception as e:
        raise PolicyError(f"error: could not read cookie jar {path}: {e}\n"
                          f"  Expected Netscape format — the file a cookies.txt extension exports.")
    domains = {c.domain.lstrip(".") for c in jar}
    return jar, f"{status} ({len(jar)} cookies, {len(domains)} domains)"


def rung_ceiling(cfg: dict) -> str:
    return "T6" if cfg["advanced_acquisition"] else "T2"


def rung_allowed(cfg: dict, rung: str) -> bool:
    return RUNGS.index(rung) <= RUNGS.index(rung_ceiling(cfg))


def cmd_check(root: Path, as_json: bool = False) -> int:
    path = root / REL
    created = False
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(TEMPLATE, encoding="utf-8")
        created = True
    cfg, prov = load(root)
    closed = gate(cfg)
    qs = questions(cfg)
    _, jar_status = cookies_path(cfg, root)
    where = f"{path.resolve()} (local-only, gitignored — never committed)"
    summary = (f"acquisition policy: consent {cfg['consent']['acknowledged'] or 'not recorded'} — {prov}; "
               f"identity {cfg['identity']['user_agent']}; rungs up to {rung_ceiling(cfg)}; {jar_status}")
    if as_json:
        print(json.dumps({"gate": "closed" if closed else "open", "created": created, "file": REL,
                          "path": str(path.resolve()), "summary": summary, "questions": qs}, indent=2))
        return 2 if closed else 0
    if closed:
        if created:
            print(f"created {where} — cautious defaults, no user fields filled.\n", file=sys.stderr)
        print(f"file: {where}\n")
        print(render_questions(qs))
        print(f"deferred: web acquisition waits until consent is recorded in\n"
              f"  {path.resolve()}\n"
              f"  An agent asks the questions above and records the answers with `policy.py set`;\n"
              f"  it never answers them itself.", file=sys.stderr)
        return 2
    print(summary)
    print(f"your answers live in: {where}")
    return 0


def cmd_set(root: Path, assignments: list[str]) -> int:
    changed = set_values(root, assignments)
    for c in changed:
        print(f"set {c}")
    return cmd_check(root)


def cmd_show(root: Path, explain: bool) -> int:
    cfg, prov = load(root)
    if explain:
        cfg = {"policy": cfg, "provenance": prov, "user_agent": user_agent(cfg),
               "rung_ceiling": rung_ceiling(cfg), "gate": gate(cfg)}
    print(json.dumps(cfg, indent=2, sort_keys=True))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path,
                    default=Path(__file__).resolve().parent.parent.parent)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ck = sub.add_parser("check", help="create the skeleton if absent; while consent is unrecorded, "
                                      "print the open decisions as questions and exit 2")
    ck.add_argument("--json", action="store_true", help="the same as data, for an agent to present")
    st = sub.add_parser("set", help="record an answer: key=value (e.g. advanced_acquisition=true, "
                                    "identity.contact=you@x.org, consent.acknowledged=today)")
    st.add_argument("assignments", nargs="+", metavar="key=value")
    sp = sub.add_parser("show", help="print the effective policy as JSON")
    sp.add_argument("--explain", action="store_true",
                    help="also print provenance, the User-Agent, the rung ceiling and the gate")
    args = ap.parse_args()
    if args.cmd == "check":
        return cmd_check(args.root, args.json)
    if args.cmd == "set":
        return cmd_set(args.root, args.assignments)
    return cmd_show(args.root, args.explain)


if __name__ == "__main__":
    sys.exit(main())
