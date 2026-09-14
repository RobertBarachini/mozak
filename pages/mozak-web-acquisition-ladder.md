---
title: The web-acquisition ladder — cheapest rung that works
aliases: [web-acquisition-ladder]
type: note
domain: [meta]
tags: [workflow, tooling]
created: 2026-09-09
updated: 2026-09-14
status: growing
---

# The web-acquisition ladder — cheapest rung that works

How to obtain bytes from a host you do not control. [[mozak-ingestion-toolchain]] covers what to
do with a file you already have; this covers getting one. [[mozak-search-gates]] sizes how much
*evidence* a question needs; this sizes how much *traffic* you may generate to get it — a
separate budget with a separate owner, the host itself.

**Vocabulary, deliberately kept apart:** the steps here are **rungs**, `T0`–`T6`. The
**tiers** of [[mozak-search-gates]] are stakes. The scales are independent — a tier-1 question can
honestly cost forty requests to one paginated API, and a tier-3 question can be answered by
three primary PDFs.

## The premise

An agent is a tool, like a browser. Reading a page in Firefox makes the same requests; you
could paste the result in yourself at pure time cost, with an identical outcome. So the
question is not *who typed the URL* but *what is accessed and what is done with it*.

That premise has found judicial support in at least one jurisdiction — narrower than it is
usually quoted, and conditional on the fetch coming from the user's own machine
([[2026-09-09-web-acquisition-research]]). The template does not lean on it. What it takes
from the evidence is a design fact: **user-directed, locally-run retrieval that stops when
told no is the strongest posture available anywhere.** The jurisdiction-specific question
— what is lawful *for you* — is yours to answer, not the template's; see *Your context, your
call* below.

## The rungs

| Rung | What it is | Reach for it when |
|---|---|---|
| **T0** | Don't fetch — official API, bulk dataset, RSS/Atom, sitemap, or the JSON endpoint the page itself calls | **Always first.** Faster, structured, stable, explicitly offered |
| **T1** | Polite HTTP: browser UA, conditional requests, backoff, on-disk cache, boilerplate-stripped extraction | T0 has nothing and the host serves the content |
| **T2** | Archives and mirrors: Wayback CDX, archive.today | T1 is refused or the page is gone; also whenever you want an `archive-url` |
| **T3** | Fingerprint HTTP — TLS/JA3 and HTTP/2 impersonation, no browser | **Amber-red. See the warning below.** Never automatic |
| **T4** | A real browser render — a **disposable, repo-scoped browser**: fresh profile each session, seeded only from your cookie jar, wiped on exit; never your daily browser | The content only exists after JavaScript runs |
| **T5** | Reuse a real logged-in session — a `cookies.txt` you export (stdlib, today), or that same jar loaded into the disposable T4 browser (later): the jar is the only session state that persists, and you control it | The content is behind an account you hold |
| **T6** | Human in the loop: you browse, export a HAR, the agent harvests it | Everything below failed, or a challenge needs a human |

**Escalate on a recorded failure, never on a guess**, and record the rung that produced the
bytes in the capture's `capture-method:`. The policy file's single `advanced_acquisition` toggle
caps how far a session may climb unaided; it ships `false` (rungs T0–T2), so every rung
above is a decision you make.

### Rung T0 — the roster worth checking first

Verified free and keyless on 2026-09-09 unless noted ([[2026-09-09-web-acquisition-research]]).
`web-fetch.py --probe <url>` automates the site-structure half of this.

| Domain | Reach for | Why it beats fetching |
|---|---|---|
| **Your own country** | your national statistics office and company register | Most statistics offices run PX-Web or SDMX — `<base>/api/v1/en/?config` makes a PX-Web server publish its own limits, `/dataflow` lists an SDMX server's flows; company registers range from free CSV dumps on the national open-data portal (CKAN: `/api/3/action/package_search`) to paid APIs. Check the portal first; record what you find in your instance, not here |
| **EU** | **Eurostat SDMX 3.0**; **data.europa.eu SPARQL** | Eurostat's **bulk TSV store is `410 Gone`** — wildcard SDMX 3.0 queries replaced it. The SPARQL endpoint federates 1.9M dataset descriptions across every member state |
| **Scholarly** | Crossref · Europe PMC · arXiv · PubMed baseline FTP · Unpaywall · OpenAIRE | Europe PMC needs no key *and* no email. **OpenAlex went metered in 2026-02** — prefer its CC0 snapshot to its search API. arXiv's OAI-PMH **moved to `oaipmh.arxiv.org`** |
| **Archives** | **Wayback CDX** · **Common Crawl** | CDX over 30 years, ~0.4 req/s. Never the *availability* API — it 429s after roughly one request. **TimeTravel is NXDOMAIN** |
| **Company/finance** | **SEC** (`data.sec.gov` + nightly bulk zips) · **GLEIF** (CC0, no observed limit) | SEC needs **no key** — "EDGAR API key" sellers are resellers; a declared UA is mandatory. GLEIF is the entity spine everything else joins to |
| **Any site** | `robots.txt` `Sitemap:` lines → feeds → `llms.txt` → JSON-LD → `/.well-known/security.txt` | A sitemap is the publisher's own complete URL inventory with `lastmod`. `security.txt` gives you a human to ask for a dump — the most-skipped move on the ladder |

**The pattern worth internalising: good sources are shaped as bulk snapshot + API for
deltas.** SEC, GLEIF, Crossref, PubMed, OpenSanctions, Common Crawl and Wayback all are.
**Never paginate a search API to build a corpus** — SEC enforces this with a hard
10,000-result wall, and Open Library prohibits it outright.

**The ladder escalates access, not entitlement.** T3–T6 exist for content you are entitled to
read and a machine is refusing to hand you — a subscription you pay for, your own account's
data, a public page behind an overzealous WAF. T5 and T6 operate a real logged-in session:
whatever that account may read, you may read; nothing more.

### The recipes, by rung

- **T0** `web-fetch.py --probe <url>` (what a host declares: robots, signals, sitemaps, feeds,
  `llms.txt`, JSON-LD, `security.txt`) · `scholar-lookup.py <doi|arxiv|"title">` (registries
  instead of publishers: capture-ready frontmatter + the open-access copy).
- **T1** `web-fetch.py <url>` · `--links` surfaces a page's references for the worklist.
- **T2** `web-fetch.py --archive <url>` (Wayback CDX).
- **T3** `web-impersonate.py <url>` — `uv run`; `advanced_acquisition` only.
- **T4** `web-render.py <url>` — `uv run`, `--install` once; `advanced_acquisition` only.
- **T5** your `cookies.txt`, used by every rung above that fetches; `web-render.py` seeds
  its disposable browser from it and from nothing else.
- **T6** `web-har-harvest.py raw/<file>.har` — consent, but no `advanced_acquisition`: the
  agent touches no network; you did the fetching.
- **Multi-page** `web-worklist.py add|show|run` — see *Your context, your call*.

**T2 leaks the URL you are researching** to a third party. AGENTS rule 10 governs sending repo
*content* outward and does not reach this adjacent case, so it is stated here: don't route
sensitive or `.private/`-adjacent research through an archive lookup or a reader proxy.

### Why T3 is never automatic

TLS-fingerprint impersonation is not a User-Agent string. The UA is access-neutral — a
complete Chrome header set over HTTP/2 still draws a 403 where the TLS handshake gives you
away ([[2026-09-09-web-acquisition-research]]). T3 forges that handshake to defeat a
fingerprint-based block: a technical countermeasure against a technical measure, which is a
different act from presenting as a browser. That is why it sits behind `advanced_acquisition`
and is never an automatic escalation. It is also low-value: an independent 31-target benchmark
separates the best evasion tooling from *unmodified* Playwright by four targets, because IP
reputation dominates.

### Rung T5 today — a cookie jar you export

Drop a Netscape-format `cookies.txt` — what the "cookies.txt" browser extensions write, and
what `yt-dlp` reads — into `.personal-shared/`. When it exists and `advanced_acquisition` is
true, `web-fetch.py` and `web-impersonate.py` send each cookie only to the site it belongs to
and record the capture as T5, `web-render.py` seeds its disposable browser from it, and
`yt-transcript.py` hands the file to `yt-dlp`. In cautious mode a present jar is
reported and not sent, so nobody is deanonymised by a file they dropped without reading.

The practice that makes this safe: **export from a private window logged into only the
sites the work needs — never from your daily profile.** The jar holds live session tokens
for every site in it. Tools read it in place, never copy it into `_generated/`, never log a
value, and never write it back; when a session goes stale, re-export. It lives inside the
repo by your explicit choice, gitignored, knowing that guarantee is negative — the one
deliberate exception to the credentials-outside rule in SYNC's *Gitignored ⇒ instance-local*.

**The browser tier, `web-render.py`, enforces this rather than describing it.** The browser
is a sandbox that belongs to the repo, not to you: Playwright's own Chromium (never the snap,
never your daily browser), a fresh profile in a temporary directory for each run, seeded from
this jar and from nothing else, destroyed in a `finally` when the run ends. It keeps only the
rendered bytes it was asked for — HTML, extract, optional screenshot, optional HAR with
`Cookie`/`Set-Cookie`/`Authorization` stripped before writing — under `_generated/fetch/`.
Third-party requests are blocked except what a page needs to render (scripts, styles, fonts),
so a render does not fan out to trackers; the row records how many were refused and which
Chromium build did the rendering. No history, cache, localStorage or fingerprint state
survives between runs, so nothing accumulates that could correlate one research topic with
the next. The User-Agent keeps the browser's real version and platform, with one edit: headless
Chromium announces itself as `HeadlessChrome` — an automation marker, and so a cross-site
correlator — and that word is replaced by `Chrome`. The second and last edit is the same kind:
Playwright launches Chromium with `--enable-automation`, which sets `navigator.webdriver = true`
— a label saying "this session is tool-driven", the modern form of the old chromedriver `$cdc_`
tell — and that flag is dropped so the value reads `false`. Nothing else is fabricated: engine,
version, platform, canvas, WebGL and plugins are whatever this browser really has, with no
fingerprint injection and no CDP patching, because presenting as *this* browser is the point.
Both edits and the `navigator.webdriver` value the page saw are recorded in the row.

## Your context, your call

The template is used from many jurisdictions and knows none of them. It ships cautious —
rungs T0–T2 — and one setting in `.personal-shared/acquisition-policy.toml`,
`advanced_acquisition = true`, is your own determination that more is fine where you are. It
is not a legal opinion either way. **Nothing acquires until your consent is recorded in that file.** `policy.py check` creates
the skeleton at session start and, while consent is unrecorded, prints the decisions that need
you as questions — posture, identity, contact, then consent — each option explained, each with
the command that records it. The agent asks you those (a structured prompt where its harness
has one, plain text otherwise), records your answers with `policy.py set`, and never answers
for you. Once consent is recorded, `check` prints the file's absolute location, so you know
where your answers live (local-only, gitignored). Identity, contact and consent are yours; being asked is what makes the consent
informed rather than a message that scrolls past.

Three positions are jurisdiction-neutral and shaped the tooling:

- **Anonymity by default.** The User-Agent does not decide whether you are blocked — that
  happens at the TLS layer — so it is free to serve a different goal, and the goal is not
  being tracked. A distinctive tool string is a cross-site correlator; researchers and
  journalists may have adversaries. The recipes therefore present as the most common
  browser, send no contact and no locale-revealing headers, and record what they sent.
  `identity.user_agent = "declared"` exists for people who *want* to be identifiable;
  `contact` exists because a few registries ask a client to name someone an operator can
  e-mail instead of blocking — that reachability is what a polite pool trades for. Empty (the
  default) means nothing identifying leaves the machine and Unpaywall is skipped; a real
  address — ideally a dedicated research alias you actually read — is sent only by the
  source-specific recipes that require or reward one, each saying so, never by the general
  fetch and never logged by value; a fake or no-reply address is refused, since it fabricates
  identity and shares one rate-limit bucket with everyone who typed the same fake.
- **robots.txt is crawler guidance — recorded on every fetch, not a gate for a single read.**
  RFC 9309 is the Robots *Exclusion* Protocol; it governs automated traversal. A
  user-directed read of one page from your own machine is what a browser does, and a blanket
  `Disallow: /` is a statement about crawlers that, read as a gate, forbids research
  outright. So `web-fetch.py`, which cannot crawl, parses robots.txt, honours `Crawl-delay`,
  logs the verdict, and proceeds. **There is no crawler in this toolchain.** Multi-page work
  is `web-worklist.py`: the agent surfaces a page's references (`web-fetch.py --links`),
  decides which are worth following *and states why* — a reason is mandatory — and those
  become ordinary targeted pulls under the same rules: capped by `budget.max_fetches_per_run`,
  each row carrying its reason and parent, any host that answers no skipped for the rest of
  the run, and `run` showing its plan before `--yes`. Nothing follows a link on its own; the
  protocol is that the agent shows the user the plan first.
- **The host's answers are the gate, and they are respected.** 403, 429 and a challenge page
  mean stop: honour `Retry-After`, do not retry from elsewhere. **Captcha solvers, proxy
  rotation to evade a block, paywall circumvention, credential sharing and fake accounts are
  outside this toolchain** — not knobs, not rungs; `advanced_acquisition` does not reach them.
  That is the line Perplexity crossed in 2025 — not user-direction and not a browser UA, but
  rotating IPs to keep going after being told no.

Jurisdiction-specific analysis is deliberately *not* shipped with the template — in this page
or its capture — because it is one author's context, not policy for yours. Do your own where
you are and keep it in your instance or `.personal-shared/`, never in a template-owned page.
The shipped evidence ([[2026-09-09-web-acquisition-research]]) is confined to what holds
everywhere: the measured probes, the tooling verdicts, and how the ecosystem — courts,
vendors, infrastructure — treats user-directed agents versus crawlers.

### Machine-readable signals to check and log

`--probe` reads these, and every fetch records what each said **and what we did** — the
contemporaneous record is the defence.

| Signal | Where | Status as of 2026-09 |
|---|---|---|
| `robots.txt` (RFC 9309) | `/robots.txt` | Universally recognised; the one signal whose disregard makes everything else look bad |
| Cloudflare **Content Signals** | `Content-Signal:` line in `robots.txt` | **Shipped.** `search` / `ai-input` / `ai-train`; applied by default to 3.8M+ domains as `search=yes, ai-train=no`, with `ai-input` deliberately unspecified. Cloudflare asserts these are Art. 4(3) reservations. **Reading a page to answer your own question is not `ai-train`** — but write that reasoning down |
| **RSL** (Really Simple Licensing) | `License:` line in `robots.txt` → XML licence | **Shipped**, Recommendation 10 Dec 2025. The most legally consequential: an RSL licence is an *offer of terms*, so fetching after being served them starts to look like contract, not preference |
| **TDMRep** | `/.well-known/tdmrep.json`, `tdm-reservation` header | W3C CG Final Report; the most EU-legally-precise Art. 4(3) vehicle |
| IETF **AIPREF** `Content-Usage` | response header or `robots.txt` rule | **Draft, no RFC.** Only two categories (`train-ai`, `search`), default "unknown", no agent category, core sections lack consensus |
| `llms.txt` | `/llms.txt` | **Not an opt-out mechanism** — a curated index for LLM consumption. ~10% adoption, Google declined to support it. Irrelevant to access |

Cloudflare **pay-per-crawl** (HTTP 402) is **still beta** as of 2026-09; claims that it reached
general availability are contradicted by Cloudflare's own changelog.

## Acquisition budget

This budget binds the **session, not a tool** — it applies equally to a recipe, a hand-typed
`curl`, and a harness's built-in fetch, exactly as [[mozak-search-gates]] binds the session
regardless of which search tool it uses. Defaults live in `tools/recipes/policy.py` and are
overridable per-instance; the effective values are recorded in every fetch.

| Knob | Default | Escalation |
|---|---|---|
| **pages** | 1 | more than one goes through `web-worklist.py`, each with its reason, and the sweep is journaled |
| **depth** | 0 — no link-following | 1 is a decision; 2+ is a crawl and needs a named reason |
| **scope** | the exact URL | at most one registrable domain; never "the open web" |
| **rate** | ≥1 s per host, serial, with jitter | never parallel against one host; jitter is for load-spreading, not disguise |

**Cache-first is the budget's main lever:** re-reading an already-fetched URL costs zero
requests, and a conditional request that returns 304 costs the origin almost nothing.

**Stop fetching** when the pages budget is spent, when three consecutive fetches add no new
claims, when the host returns 429/403 (back off, then escalate a rung deliberately or stop —
never retry harder), or when the question is answerable. Record which gate fired, per
[[mozak-search-gates]]'s recorded-stop rule.

## Where fetched bytes live

Every machine fetch lands in `_generated/fetch/` — gitignored, derived, disposable, with **no
drain obligation**. That is the point: the live web is an external resource, referenced and
never imported ([[mozak-store-the-delta]]), and **a cache changes dereference latency, not
admission**. Delete the directory at any time and nothing is lost; the URL is the source of
truth.

`raw/` stays what it is — the zero-ceremony drop zone for artifacts a *human* produced, such
as a HAR export, drained once and then removed. The line between the two is who produced it.

**Nothing in this layer can write into the graph.** No recipe may author `pages/`, `sources/`,
`journals/` or `archive/` — the rule lives in `tools/recipes/README.md`. `sources/` stays the
only door, and passing through it is still one authored capture per source: the two-pass toll
of [[mozak-store-the-delta]], untouched by making fetching cheap. `archive/` is closed the same way
by an existing rule, since every entry must be named after its fronting note's stem.

Volume that does happen is on the record: `_generated/fetch/fetch.sqlite` logs every attempt
with the signals seen and the policy in force, and the per-host delay makes bulk fetching cost
wall-clock time. Neither is a hard gate and neither pretends to be — **the gate is that the
graph's door is narrow, not that the cache is.**

## Rung T6 — the human handoff

1. **You** browse normally, logged in, solving whatever challenge exists. DevTools → Network →
   **Export HAR** → save into `raw/`.
2. **`web-har-harvest.py raw/<file>.har`** lifts the document responses into
   `_generated/fetch/`, stamped `T6 har`, keeping six response headers (`content-type`,
   `content-length`, `date`, `last-modified`, `etag`, `link`) and nothing else — no request
   headers, no cookies, no browser fingerprint, never a copy of the HAR. It needs consent but
   not `advanced_acquisition`: the agent touches no network; you did the fetching.
3. **The agent** authors one `sources/` capture (the toll is unchanged), then you delete the
   HAR per the `raw/` drain rule — the recipe reminds you.

**A HAR is a credential-bearing file** — it carries `Cookie` and `Authorization` verbatim and
your browser's exact fingerprint. It lives only in gitignored `raw/` until it is deleted.

*Rejected alternatives, with reasons.* A **recording proxy** (mitmproxy) sees HTTPS only by
installing a CA in your system trust store, which is a permanent machine-wide change and
creates a CA private key living next to a knowledge repo; its Linux eBPF local-capture mode is
genuinely excellent, so it is tracked in [ROADMAP.md](../ROADMAP.md) for the day a capture
needs it, rather than wired in unused. **DevTools "Copy as cURL"** puts session cookies on a command line, into shell
history and process tables — never use it.

## Sources

- [[2026-09-09-web-acquisition-research]] — the measured probes behind the "UA spoofing is
  useless" and "archives recover blocked pages" claims, the anti-bot benchmark, and the legal
  citations with their per-claim evidence grading and unverified list.
- [[mozak-ingestion-toolchain]] — the tool policy this page's rungs obey (probe first, degrade
  loudly, run fetches locally) and the drain recipes that take over once bytes exist.
- [[mozak-store-the-delta]] — the admission doctrine that makes the cache disposable and keeps the
  two-pass toll on the graph's door rather than on fetching.
