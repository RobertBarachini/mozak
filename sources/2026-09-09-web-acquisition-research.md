---
title: "Research: web-acquisition landscape — tooling, law, and measured probes"
type: source
domain: [meta]
medium: report
author: agent research run (21 subagents, Claude Opus 5)
retrieved: 2026-09-09
created: 2026-09-09
updated: 2026-09-09
tags: [founding]
---

# Research: web-acquisition landscape — tooling, law, and measured probes

Internal agent-generated research, so no `url:` (schema exception for `medium: report`).
Provenance: a 21-subagent run on 2026-09-09 covering browser automation and stealth,
HTTP-level tooling, proxy/capture, structured access, document and media extraction,
anti-bot reality, the legal landscape, and operational patterns. Distilled into
[[mozak-web-acquisition-ladder]].

**Reliability envelope, inherited by everything citing this capture.** Findings are graded
where the underlying reports graded them: **[V]** verified against a primary source this
run, **[V-2°]** verified secondary, **[T]** from model knowledge, not re-verified. Tool
versions and legal positions are a **2026-09 snapshot** and move fast. Several subagents
exhausted their search budgets mid-run and said so; the unverified list at the end is not
decoration.

## Method

- Shape: 21 subagents; 7 reported into the synthesis directly, 13 completed but were
  orphaned by a quota interruption and were recovered from disk afterwards, 1 coordinator
  produced a stub and lost nothing recoverable of its own.
- Live probes were run from the author's own machine, and are the strongest evidence here
  because they are first-hand rather than cited.
- The consequence of the orphaning, recorded honestly: the structured-access strand (rung
  T0) and the author's own-jurisdiction legal strand were written into the first draft from a
  second-hand summary, and were corrected only after recovery. That jurisdiction strand is
  deliberately **not** in this shipped capture — it is one author's context, kept in the
  private zone; what follows is confined to what holds everywhere. The corrections were material
  — see *Corrections made on recovery* below.

## Measured probes (first-hand, 2026-09-09) [V]

- **Network egress is a residential IP**, not datacenter. → Do not add
  proxies: residential reputation is the input commercial proxies sell, and a datacenter VPS
  would make results *worse*. This is also the mechanism behind the existing run-fetches-locally
  rule in [[mozak-ingestion-toolchain]].
- **User-Agent spoofing changes nothing.** `curl` with its default UA and with a full Chrome
  141 UA got identical results: reuters.com 401 both ways, g2.com 403 both ways.
- **The block is at the TLS/HTTP-2 fingerprint layer.** g2.com still returned 403 with a
  complete Chrome header set including `sec-ch-ua` and `Sec-Fetch-*` over HTTP/2. The JA4
  fingerprint identifies curl regardless of headers.
- **The harness's own `WebFetch` also returned 403** on g2.com — the friction is real and
  reproducible, not a misconfiguration.
- **Stdlib `urllib` with a browser UA already handles most of the web**: example.com 200,
  news.ycombinator.com 200, **nytimes.com 200 (1.28 MB)**, g2.com 403, reuters.com 401. The
  failures carry *distinguishable* codes (403 WAF vs 401 auth) that escalation logic can
  branch on. → The T1 rung needs no dependencies.
- **The blocked set is commercial news paywalls and lead-gen sites**, not research sources.
  200 OK: arxiv.org, jstor.org, statista.com, semiconductors.org, news.ycombinator.com.
  403: ft.com, economist.com, bloomberg.com, g2.com, zillow.com. → That is a subscription
  problem, not a technical one.
- **Archives recover hard-blocked content.** Wayback CDX returned 2026 snapshots of
  `reuters.com/world` at 200 and 59 KB while the live site returned 401. → Rung T2 is both
  the politest path and a genuine capability, not a consolation prize.
- **Reader proxies are not an anti-bot rung.** `r.jina.ai` on g2.com returned HTTP 200 with an
  empty body and a captcha warning; on a normal page it served a *cached snapshot* by default.
- **robots.txt AI directives are declarative, not enforced.** nytimes.com, theguardian.com and
  g2.com all carry `Disallow: /` for `anthropic-ai` / `ClaudeBot` / `GPTBot`; the NYT server
  nonetheless returned 200 to an ordinary request.
- **Live machine-readable signals in the wild**: `Content-signal: search=no, ai-train=no` in
  stackoverflow.com/robots.txt; `License: https://theguardian.com/license.xml` in
  theguardian.com/robots.txt.
- **Local toolchain gaps**: `pandoc` is named in the [[mozak-ingestion-toolchain]] roster but is not
  installed, and **no JavaScript runtime is present**, which silently degrades `yt-dlp`'s
  YouTube path.

## Tooling findings

- **Stealth tooling is the low-leverage end of the problem** (independent 31-target benchmark,
  3 sweeps, one residential IP) [V-2°]: nodriver 28/31, curl_cffi 26/31 (HTTP only),
  Patchright 25/31, Camoufox 25/31, **vanilla Playwright 24/31**. Four targets separate the
  best evasion tool from an unmodified browser; the benchmark's author attributes the spread
  to IP reputation.
- **Dead, despite still being widely recommended** [V]: `undetected-chromedriver` (last release
  2024-02), `puppeteer-extra-stealth` (2024-07), `rebrowser-patches` (superseded — the
  `Runtime.enable` leak it patched is closed), `newspaper3k` (2018), `nougat` (2023),
  `insanely-fast-whisper` (2024), `waybackpy` (2022). **`playwright-stealth`'s own README says
  not to rely on it.** **Camoufox's own README** discloses "a year gap in maintenance."
- **Live picks** [V]: `patchright` 1.62.3 with *real* Chrome and a persistent profile (its own
  documented best practice is to fabricate nothing); `curl_cffi` 0.16.3 for TLS impersonation
  where justified; `trafilatura` 2.2.0 for extraction (F1 0.924, Apache-2.0 since 1.8);
  `mitmproxy` 12.2.3, whose Linux eBPF local-capture mode needs kernel ≥6.8; `hishel` /
  `requests-cache` for conditional-request caching; `uv` + PEP 723 for recipe dependencies.
- **`httpx` stable has not shipped since 2024-12**; maintenance continues as `httpx2` under the
  Pydantic organisation [V].
- **Distro traps**: apt `mitmproxy` is 8.1.1 (2022-era); distro `pandoc` lags 1–3 years — install
  the release `.deb`.
- **`yt-dlp`** now requires an external JavaScript runtime for full YouTube support, and
  **`--sub-format json3`** returns YouTube's native timed-text JSON, which has **no rolling
  duplicates** — the problem `yt-transcript.py` exists to clean up after.
- **Scheduling at n=1 machine**: a SQLite frontier plus a systemd timer beats every broker;
  graduate to `huey` with `SqliteHuey` only if retries and priorities get hand-rolled twice.
  Scrapy is not recommended for fresh adoption in 2026; `crawlee-python` if a framework is
  ever wanted.

## Legal and ecosystem findings (jurisdiction-neutral)

Grading matters here more than anywhere else. **Not legal advice.** Jurisdiction-specific
analysis is deliberately omitted from this shipped capture.

- **US, *Amazon v. Perplexity*, No. 26-1444 (9th Cir. 4 Aug 2026)** [V — full opinion read]:
  "It is the user who 'accesses' Amazon's computers"; the agent "is a tool, not a person for
  statutory purposes." **Limits, all express**: a preliminary-injunction appeal; confined to
  "access" under the CFAA and CDAFA; footnote 5 preserves the site's ability to regulate
  access "via private terms of service"; tort claims and different architectures reserved.
  The holding is architecture-conditional — the fetch came from the user's own browser and
  "Perplexity's servers never directly access Amazon's servers." → **Contract, not
  computer-misuse law, is the live weapon** — and the finding is about one jurisdiction.
- **The agentic/crawler distinction is real in three layers and absent from every standard**
  [V]: courts (above); vendor policy (OpenAI's docs state that for `ChatGPT-User`, "because
  these actions are initiated by a user, robots.txt rules may not apply," while Anthropic
  honours robots.txt for `Claude-User` regardless — the two largest vendors openly disagree);
  and infrastructure (Cloudflare's signed agents, Aug 2025, defining agents as "generally
  directed by an end user"). The IETF **AIPREF** drafts encode no agent category and carry
  "this section does not yet have consensus."
- **The boundary case** [V-2°]: Cloudflare de-listed Perplexity as a verified bot in Aug 2025
  over undeclared crawlers spoofing a generic Chrome UA with rotating IPs to evade robots.txt
  blocks. Allegation and partial denial. → The agentic defence survives only if you are honest
  about being an agent; the sin was impersonation and evasion after a block.
- **A CAPTCHA or JS challenge is an access control**, at least in one jurisdiction: *Reddit v.
  SerpApi* (S.D.N.Y. 31 Jul 2026) held Google's SearchGuard qualifies under DMCA §1201(a)
  [V-2°]. Conversely *Ziff Davis v. OpenAI* (S.D.N.Y. Dec 2025) held ignoring robots.txt is
  not circumvention — "more akin to a sign than a barrier" [V-2°]. → The toolchain excludes
  solvers and treats a challenge page as an answer, everywhere.
- **Signals** [V]: Cloudflare **Content Signals** shipped 24 Sep 2025 (`search` / `ai-input` /
  `ai-train`; default `search=yes, ai-train=no` on 3.8M+ domains, `ai-input` deliberately
  unspecified). **RSL** reached Recommendation 10 Dec 2025 and is the most legally
  consequential, because an RSL licence is an *offer of terms*. **TDMRep**
  (`/.well-known/tdmrep.json`) exists as a machine-readable reservation vehicle. **AIPREF has
  no RFC.** **`llms.txt` is not an opt-out mechanism** (~10% adoption; Google declined to
  support it). Cloudflare **pay-per-crawl is still beta** — GA claims are contradicted by its
  own changelog.
- **Machine-readable opt-outs carry real legal weight in some jurisdictions and none in
  others** — which is why the template ships honouring nothing by law, recording everything,
  and leaves posture to the user's own judgement of their context.

## Corrections made on recovery

The orphaned reports corrected the first draft on four points. One is jurisdiction-neutral
and instructive: *Amazon v. Perplexity* had been stated far too broadly — the PI posture, the
CFAA/CDAFA-only scope, footnote 5, and the architecture condition were all missing. The other
three concerned the author's own jurisdiction and moved with that analysis to the private zone.

## Reliability notes

- **2026-09-09** — Several subagents exhausted their WebSearch budgets mid-run and fell back to
  direct fetches; each said so. Explicitly **not verified** by this run: the current force of
  the May 2022 US DOJ CFAA charging policy; RFC 9309's publication metadata; RSL adoption
  figures; `ai.txt`/Spawning's status; DMCA §1201 TDM exemption conditions (eCFR was blocked);
  and the post-trial fate of *Ryanair v. Booking*. Per-vendor anti-bot internals (DataDome,
  Kasada, HUMAN, Akamai, Imperva) rest on vendor and practitioner blogs, not primary sources.
  Jurisdiction-specific unverified items travelled with that analysis to the private zone.
- **2026-09-09** — The full 509 KB of recovered subagent reports was drained from `raw/` after
  distillation, per the ingestion workflow. This capture is the durable residue; the reports
  themselves were transient by contract.

- **2026-09-14** — Interpretive correction, not a factual one. The first distillation read
  Cloudflare's "Agent" bot category as meaning *an honest User-Agent buys access*. It does
  not, for this use: the category is for registered, cryptographically signed vendor agents
  (Web Bot Auth), not a solo local tool, and the probes above already showed the UA is
  access-neutral — blocks happen at the TLS layer. The findings stand; the design consequence
  reversed: because the UA is access-neutral it is chosen for **anonymity** (the most common
  browser string, no contact, no locale header), since a distinctive tool string is a cross-site
  tracking beacon. The agentic/crawler distinction the three layers recognise is about
  *conduct* — user-direction, and not evading after a block — not about the UA string.
  Likewise robots.txt: RFC 9309 governs crawlers, and the single-URL recipe records it rather
  than treating a blanket `Disallow: /` as a gate on research reads.

## Distilled into

- [[mozak-web-acquisition-ladder]] — the rungs, the jurisdiction-neutral *Your context, your call*
  section, the acquisition budget, the store contract, and the T6 handoff. Jurisdiction-specific
  analysis is deliberately in neither the page nor this capture.
- [[mozak-ingestion-toolchain]] — the two measured local gaps (`pandoc` absent, no JS runtime) and
  the live-URL drain path.
