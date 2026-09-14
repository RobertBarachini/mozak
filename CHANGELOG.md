# Changelog

Development history of the **template system itself** — the MUST rules, the frontmatter
schema, `tools/`, `templates/`, and root config (`.gitignore` and the rest of the
machinery). This repo's *own* work — ingesting sources, distilling notes, maintenance
such as syncs — is not logged here; that lives in `journals/`. The routing rule has one
home: AGENTS rule 7.

**Template-owned** (see [SYNC.md](SYNC.md)): the template authors this file; instances
receive its entries on `git merge template/main` and never write to it, so it always
fast-forwards cleanly. An instance's generalizable system change is upstreamed (and
returns here via the pull), not logged locally; an instance records *performing* a sync
in its own journal.

Newest first.

## 2026-09-15

- **README gains *What people ask it* — thirteen openers from a live instance's first ten
  weeks.** The handoff block fixed "how do I start"; this answers "what do I even do with it",
  with evidence rather than a feature list: one instance, eight domains, 217 notes, 58
  captures, four rendered briefings, and every domain begun as a single sentence typed into an
  agent. Each entry is the prompt as you would type it and nothing else — a first draft carried
  what each became, with note counts, and the author cut it: the list is there to show what one
  can ask, and the README's *One loop, end to end* already shows one outcome in full.
  Generalised per the SYNC privacy boundary — topics, not particulars: nothing names a place,
  a product, a party or a person. Kept in the README rather than a meta page because the reader who
  needs it has not opened the repo yet. Two closing paragraphs: how the questions compound —
  overlapping ones started from earlier captures rather than from zero, the difference from a
  chat window that forgets when the tab closes — and, for the sceptic, how an answer is
  captured, cited, verified and kept. Also corrected: the SYNC birth-seed exception written
  yesterday called any incoming `start-here.md` change beyond a link retarget "a template
  mistake to report"; it is the template improving the seed for future instances, resolved
  keep-ours as the register already said.

## 2026-09-14

- **The README hands a fresh clone to an agent in one paste, and `tools/bootstrap.py` makes
  the handoff checkable.** People landed on the README and did not know what to do with it;
  once an agent touched the repo it oriented fine. The bottleneck was the human deciding to
  hand it over, so the first screen now does three things in order: a three-row What / How /
  Why table, a fenced block to copy into any agent that runs commands (GitHub's copy button
  makes a fence one click; prose is not copyable), and a plain statement of what happens next
  — clones into a folder you name, installs nothing, asks questions it never answers for you,
  says Ready — plus three example first prompts. The template-versus-instance explanation
  moved below the action under *What this is*; the old *Start an instance* section and its tip
  callout are folded in; a back-link at the foot returns readers who read the Why first. The
  block is a handoff, not a second procedure: it tells the agent to read AGENTS and SETUP,
  which win over the message (rule 9). `tools/bootstrap.py` (stdlib, ring 0) is the command
  the block names — SETUP §1–§3 as an idempotent checklist: tools present, template remote
  attached, both gates green, the personal-context skeleton present and its questions asked, a
  README rewritten for the instance, a journal entry of the instance's own — printing ✓/✗ per
  item with the exact next command, exit 0 only when ready, `--json` for agents. It performs
  only what is safe unattended: `--attach` renames `origin` to `template` when origin points at
  a repo named mozak (never by default — the template author's own checkout looks identical to
  a fresh clone); `.personal-shared/README.md` is written as an *empty* skeleton whose
  `personal-context: pending` marker `--personal-context-asked` flips, recording that the
  questions were asked rather than what was answered (every fact may stay `—`); and
  `policy.py check`'s questions are passed through, never re-rendered. Tests:
  `test_bootstrap.py` (pure functions, then an end-to-end run on a temp clone driven to
  `ready: yes`) and `test_readme_handoff.py`, which parses the pasted block and fails if
  anything it names stops existing or an anchor stops matching its heading.

- **Template-shipped pages carry a reserved `mozak-` stem prefix, and a shipped rename replays
  in instances with one command.** The template's pages share one flat namespace with every
  instance's notes (rule 1), so a page the template shipped later could collide with a stem an
  instance already held, and the only defence was the duplicate-stem failure at pull time. Now
  every shipped page is `mozak-<stem>` — ten renamed today with `graph.py rename`, each keeping
  its old name in `aliases:` — with the hub `moc-meta` and the birth seed `start-here` as the
  two exceptions. The rule lives in the AGENTS `pages/` row; the SYNC ownership cell names
  `pages/mozak-*.md`; `graph.py ownership` flags a locally coined `mozak-` stem as
  RESERVED-STEM. Two alternatives were rejected on the way. A `pages/meta/` folder, because the
  stem *is* the identity: a subfolder would leave the namespace exactly as flat as before,
  contradict the `pages/` row and the never-folders domain rule, and fall out of the
  non-recursive ownership roster. And `meta-` as the token — the system's own domain name, and
  the first draft's choice — because a reserved prefix has to be something no research topic
  will ever coin, and `meta-` fails that test twice: it is a company (an instance researching
  Meta Platforms writes `meta-llama`, `meta-quest`) and a dictionary prefix (`meta-analysis` is
  the commonest note type in evidence-based research). The project's own name is the one token
  with no such life of its own. Ownership, not topic, is what the prefix reserves; topic stays
  in `domain: [meta]` and the `moc-meta` hub, which are shared with instances, not reserved.
  The instance side is the new machinery: after a pull the template's file has moved but the
  instance's own `[[old]]` links have not, and `rename` cannot help because the old note is
  gone. `tools/migrations/renames.tsv` is the append-only ledger of shipped renames (rule 6);
  `graph.py migrate` replays it — rewriting `[[old]]`, `[[old|shown]]` and `[[old#anchor]]` to
  the current stem, following chained renames, leaving a row alone when a local note still
  holds the old stem, idempotent — and `check` names stale targets with a hint pointing at
  `migrate`, so the pull ritual's failure is actionable. `ownership --template` verifies the
  shipping convention (prefix, ledger consistency) and runs in the template's CI only, gated on
  the repository slug because a checkout cannot tell template from instance. One side effect
  is now written down rather than left to inference: the template's own `start-here.md` — the
  birth seed instances own outright — has its wikilinks retargeted by a shipped rename like
  every other note, so a pull can carry a link-only hunk on a file SYNC calls never-updated;
  SYNC's birth-divergences register states the exception and the procedure (take either side,
  run `migrate`, same result; anything else incoming on the seed is a template mistake).
  Path links in the
  root docs, the drain-report skill, `annotate.py` and the recipes were swept; CHANGELOG history
  keeps the old names. Tests: `tools/tests/test_graph.py`, stdlib, on temp repos only, so the
  suite passes in an instance whose own pages legitimately lack the prefix.

## 2026-09-09

- **The stdlib-only invariant is rescoped to a zero-install *core*, and recipes gain a
  declared dependency tier.** The invariant as written was already false — `yt-transcript.py`
  has shelled out to `yt-dlp` since the founding commit. What has actually held is a stronger
  and more useful promise: clone the repo, have `git` and `python3`, and the system works with
  nothing installed. That is now the stated rule, with `graph.py`, `annotate.py`, the hooks,
  the tests and CI as ring 0 (stdlib, bare `python3`, never importing ring 1), and
  `tools/recipes/` as the one ring outside it, free to declare external binaries via `# needs:`
  or Python packages via PEP 723 inline metadata run with `uv run`. Dependencies point inward
  only. The invariant's normative home is the AGENTS `tools/` row; the *mechanism* — declaration
  form, runner, venv fallback, and the never-fetch-and-run rule — lives in
  `tools/recipes/README.md`, because probing for "may I depend on this" and "how do I declare
  it" are distinct rules that keep one home each (the same split the 2026-08-23 entry made for
  probing). Rule-9 sweep over all eight live restatements: `SETUP.md`, `CONTRIBUTING.md`,
  `tools/recipes/README.md`, the AGENTS row, the README badge (`tooling` → `core_tooling`,
  one word, so it stays true forever), both tool docstrings, and `annotate.py`'s MCP comment,
  which asserted third-party deps were "disallowed" and would have become a lie. The three
  CHANGELOG hits were deliberately left alone: a changelog records what was true when written.

- **New page `pages/web-acquisition-ladder.md` — seven rungs, T0 to T6.** The repo had no
  position on obtaining bytes from a host it does not control: the whole web surface was one
  roster row deferring to "a full browser fetch" that nothing defined. The ladder runs from
  "don't fetch — use the official API, dataset, feed or sitemap" through polite HTTP, archives,
  fingerprint impersonation, a real browser, a logged-in session, and a human-in-the-loop HAR
  export, escalating only on a recorded failure. **Steps are "rungs" (`T0`–`T6`), never
  "tiers"** — `search-gates` already owns tier 1/2/3 for stakes, the two scales are independent
  (a tier-1 question can honestly cost forty requests to one paginated API), and an agent
  reading "tier 3" must not have to guess which is meant. `search-gates` gains one bullet
  pointing here for fetch volume; `research-flow` step 2 and `moc-meta` link in.
  **Jurisdiction-specific analysis is deliberately not shipped** — neither in the page nor in
  its evidence capture. The author's own EU/national analysis was drafted into the capture and
  then moved to the gitignored personal zone on the author's rule that the template's tracked
  surface carries only what holds everywhere; the shipped capture keeps the measured probes,
  the tooling verdicts, and how the ecosystem treats user-directed agents versus crawlers. The
  T0 roster's national rows became a generic "your own country" row for the same reason.

- **Measured evidence, not received wisdom, set the rung order.** A full Chrome User-Agent
  changed nothing against reuters (401) or g2 (403); a complete Chrome header set over HTTP/2
  still drew 403, because the discriminator is the TLS fingerprint. Stdlib `urllib` with a
  browser UA retrieved 1.28 MB from nytimes.com. Wayback returned a 59 KB 2026 snapshot of a
  Reuters page that answers 401 live. And an independent 31-target benchmark separates the best
  evasion tooling from *unmodified* Playwright by four targets, because IP reputation dominates.
  So archives and official APIs sit above stealth, and rung T3 is documented as never
  automatic rather than as the obvious next step.

- **Anonymity by default; contact only with informed consent.** The probes showed the
  User-Agent is access-neutral — blocks happen at the TLS layer — so it is free to serve a
  different goal, and the goal is not being tracked: a distinctive tool string is a cross-site
  correlator, and researchers and journalists may have adversaries. The fetch recipe therefore
  presents as the most common browser, sends no `From:` header and no locale-revealing
  `Accept-Language`, and records exactly what it sent. `identity.user_agent = "declared"`
  exists for people who want to be identifiable; `contact` is never sent by the general fetch
  in any mode, only by future source-specific recipes that require it (EDGAR mandates one;
  Crossref's polite pool keys on one), each saying so. A first draft had the opposite default,
  reading Cloudflare's "Agent" bot category as *honesty buys access*; that category is for
  registered, signed vendor agents, not a solo local tool, and the draft conflated access with
  anonymity. The ethical line is the one Perplexity actually crossed in 2025 — not
  user-direction, not a browser UA, but **rotating IPs to keep going after being told no** —
  and that is what stays absolute: no evasion after a block, no solvers, no fake accounts.
  Source-level tests enforce the no-`From:`, no-contact, generic-language invariants.

- **One personal setting decides posture; the template does not decide what is lawful for
  you.** `tools/recipes/policy.py` merges `.personal-shared/acquisition-policy.toml` over
  shipped defaults with stdlib `tomllib`. The template ships cautious — rungs T0–T2 — and a
  single `advanced_acquisition = true` is the user's own determination that more is fine in
  their context, unlocking every rung as its recipe lands. A
  first draft shipped ten separate knobs (robots mode, content-signal respect, rung ceiling,
  session reuse, UA mode, …) and an EU-anchored legal argument for their defaults; both were
  cut before commit on the author's call that the template is used worldwide, jurisdiction is
  the user's determination, and a template has no business encoding one country's analysis as
  everyone's policy. What remains besides the toggle is not law: an optional `contact`
  (functional — it unlocks Crossref's polite pool and satisfies EDGAR's mandatory contact, at
  the cost of the user's address in every request header, so it is empty by default), a
  `budget` (politeness toward hosts, safety for the disk). Unknown keys and wrong types fail loudly; the
  effective values and a provenance string naming only the knobs that actually deviate are
  recorded on every fetch. Scope boundary stated in the page: overrides govern acquisition
  behaviour only and cannot loosen rule 10, the `.private/` never-read rule, or the two-pass
  toll.

- **Rule 7 gains a consent gate beside `check`: `policy.py check`.** Instances are set up by
  agents, and an agent must never prefill a human's identity, contact or consent. So the
  policy file is created only as a commented skeleton, and `policy.py check` — run at session
  start beside `graph.py check` — exits non-zero, and every fetch recipe refuses, until the
  human has recorded `[consent].acknowledged`. The skeleton and the shipped defaults are
  asserted equal by a test so they cannot drift. **A stderr paragraph is exactly the consent
  that scrolls past**, so — on the author's call — the gate *asks*: while closed, `check`
  prints the open decisions as questions (posture, identity, contact, then consent), every
  option explained, each with the `policy.py set key=value` command that records it; `--json`
  gives the same as data. The agent's duty, now in rule 7, is to put those questions to the
  human through its harness's structured-question mechanism when it has one and in plain text
  otherwise, record the answers with `set`, and never pre-answer or infer one. `set` preserves
  the file's comments, validates by reloading, and restores the previous content on any error;
  the questions live once, beside the defaults, and a test asserts every key resolves and that
  consent is asked last. Also removed from
  the personal-context README: an inferred locale from the egress IP's ASN, recorded in the
  first draft as `[probed]` — a machine probe was allowed to stand in for a user fact, which is
  the exact thing the gate exists to prevent. Machine facts stay probed and dated; user facts
  are left empty for the user.

- **Rung T5 in stdlib: a cookie jar the user exports.** `identity.cookies_file` (default
  `.personal-shared/cookies.txt`) names a Netscape-format jar — what the cookies.txt browser
  extensions write and what `yt-dlp` reads. When it exists and `advanced_acquisition` is true,
  `web-fetch.py` sends each cookie only to its own site through `http.cookiejar` and records the
  capture as T5; `yt-transcript.py` passes the same file to `yt-dlp`. In cautious mode a present
  jar is reported and not sent — a user who drops a file without reading is told, not silently
  deanonymised. Tools read the jar in place, never copy it into `_generated/`, never log a value
  (a test loads a jar with a known secret and asserts it appears in no status or provenance
  string), and never write it back. The documented practice is a private-window export of only
  the sites the work needs, never the daily profile. This is the one deliberate exception to
  SYNC's "credentials live outside the repo": a credential the user exports *for* this purpose,
  placed gitignored by their explicit choice — SYNC's placement paragraph now says so.

- **A contact must be reachable, and the file announces where it lives.** Two follow-ups from
  the author. A fake or no-reply address for `identity.contact` is refused by `set`, and
  `scholar-lookup` will not send one even if hand-edited in: the field exists so a source can
  reach you, a fake is the one place the toolchain would fabricate identity, Crossref keys its
  polite pool on the address so everyone typing the same fake shares one rate-limit bucket, and
  Unpaywall rejects placeholders anyway. The skeleton comment and the walkthrough question now
  explain it the same way, in three states — *what it is for* (an operator can e-mail you
  instead of blocking you), then **empty** (nothing leaves; Unpaywall skipped; Crossref public
  pool), **a real address** (sent only by the recipes that need one, each saying so; a
  dedicated alias such as a Proton or forwarding address is the ideal), **a fake** (refused, and
  why) — so a user deciding elsewhere knows exactly what each choice does. And once consent is recorded,
  `check` prints the file's absolute path (also on creation, in the closed-state walkthrough,
  and as `path` in `--json`), marked local-only and gitignored, so the human knows where their
  answers live. Locale, meanwhile, is confirmed *not* a policy input: it is an optional,
  skippable row in the personal-context README that nothing parses.

- **New recipe `tools/recipes/web-fetch.py` — rungs T0–T2, stdlib, ~500 lines.** `--probe`
  reports a host's own declared access paths (robots.txt with its `Content-Signal` and RSL
  `License:` lines, sitemaps, feed autodiscovery, `llms.txt`, JSON-LD, OpenAPI,
  `/.well-known/security.txt`) so a session can ask whether to fetch at all; a bare invocation
  fetches with conditional revalidation, per-host rate limiting, a content-addressed blob store
  and an append-only JSONL provenance log; `--archive` is the Wayback CDX lookup. Four
  decisions worth recording. **robots.txt is parsed here rather than by
  `urllib.robotparser`**, whose reference is the 1996 Koster draft: it lacks longest-match
  precedence and never sees `Crawl-delay`, `Content-Signal` or `License`. **robots.txt is recorded on every fetch, never a gate for a single read**: RFC 9309 governs
  crawlers, this recipe fetches one URL and cannot crawl, and a blanket `Disallow: /` read as a
  gate would forbid research outright — `Crawl-delay` is honoured, the verdict is logged, and
  the host's own response decides. There is no crawler to treat it otherwise — multi-page work
  is the agent-curated worklist below, whose pulls are single reads. **A 401/403/418/429 on robots.txt itself is recorded as a block, not as RFC 9309's
  "4xx ⇒ allow-all"** — that rule assumes no robots file exists (found because Stack Overflow's
  WAF answers 418). **`Content-Length` is compared against the
  pre-decompression byte count**, since comparing it to the decoded size flags every gzipped
  page as truncated. And **a bot wall is never captured as content**: an interstitial, an empty
  200, or a JS shell is classified, logged, and refused, with the archive rung offered instead.

- **Extraction is a documented approximation, and the raw bytes are kept because of it.** A
  naive tag-stripper scores *below raw HTML* on extraction benchmarks, so the extractor
  classifies blocks by link density and stopword ratio — justext's insight, which reaches
  roughly 0.86 F1 against trafilatura's 0.924 — and warns when it kept too little. Keeping the
  gzipped original content-addressed makes re-extraction with a better tool free later, which
  is claim-level provenance applied to ingestion.

- **`_generated/fetch/` is the store, and no recipe may write into the graph.** Machine fetches
  are derived, disposable and carry no drain obligation: a cache changes dereference latency,
  not admission, which is `store-the-delta`'s own sentence. Routing them through `raw/` instead
  would have manufactured a growing backlog whose only relief is authoring captures — pressure
  toward exactly the hoarding the two-pass toll exists to prevent. The structural gate is a new
  general rule in `tools/recipes/README.md`: **no recipe writes to `pages/`, `sources/`,
  `journals/` or `archive/`**, and there is no `--capture` flag on any fetch tool, ever. Five
  hundred cache entries produce zero graph files because nothing can convert them. A test
  enforces it by grepping every recipe.

- **Schema: `medium` gains `dataset`; `archive-url` and `capture-method` added.** `dataset`
  closes a *pre-existing* hole — the ingestion page already documented a JSON/CSV drain path
  with no valid `medium` value for its output. **`webpage` was refused deliberately**, with the
  reason written into the row: the field names what an artifact *is*, not the pipe it arrived
  through, and `article` vs `webpage` would be an unresolvable coin-flip on every web capture.
  `archive-url` is a URL and named so — among four `YYYY-MM-DD` neighbours an `-at` suffix would
  collect a date — and it is the mechanical enabler of surgical repair after a source 404s.
  `capture-method` is required at rung T2 and above, because from there up the bytes are a
  mirror, a fingerprinted client, a rendered DOM or a logged-in session, and a bot-blocked stub
  reads exactly like a thin page once the session ends. A content hash was **deferred**: nothing
  consumes it, and the capture already stores the content verbatim.

- **web-fetch's pipeline is one function, `perform()`, and pages surface their links.** The
  fetch → robots → pace → conditional GET → classify → store → log sequence was factored out of
  the CLI so that every other recipe performing a targeted pull calls the same code; `run()` is
  now only printing and exit codes, and `explain_failure()` names the next rung from the one
  that failed. The HTML parser collects every `<a href>` with its anchor text and whether it sat
  in nav/footer chrome, and `--links` prints them resolved, deduplicated and labelled (pdf, doi,
  arxiv, feed, page; same-site or external) so an agent can *choose* which references deserve
  a pull. Nothing follows them.

- **Multi-page work is an agent-curated worklist, not a crawler: `web-worklist.py`.** The plan
  had sketched a resumable SQLite frontier; the author's design replaced it, and it is the
  better one: "pull a page, let the agent decide which links are worthwhile, then those are
  targeted pulls again." `add <url> --why "…"` refuses an entry without a reason — the list
  records judgement, not traffic; `show` lists reasons and results; `run` prints its plan
  (count, hosts, every reason) and does nothing without `--yes`, the documented protocol being
  that the agent shows the user that plan first. Limits are structural: capped at
  `budget.max_fetches_per_run`, a host that answers 403/429 or a challenge is skipped for the
  rest of the run, progress is saved after every pull, and each provenance row carries `why`,
  the parent URL and the run id, so the log reads as reasoning. Verified live: ok / blocked /
  skipped across two hosts, exactly as designed. robots.txt is recorded, not gated, for these
  pulls as for single reads — the author's call that approved multi-page work behaves the same
  — and the ladder page no longer promises a crawler that would treat it otherwise, because
  there is none.

- **Rung T6 in stdlib: `web-har-harvest.py`.** You browse and export a HAR into `raw/`; the
  recipe lifts the document responses into the same store and log as every other rung, stamped
  T6. Credentials are discarded by construction: six response headers are allowlisted and
  nothing else survives — no request headers, no cookies, no browser fingerprint, never a copy
  of the HAR — and a test harvests a fixture carrying `Cookie`, `Set-Cookie`, `Authorization`
  and a unique UA, then greps the entire store for each. It needs consent but not
  `advanced_acquisition`: the agent touches no network; the human did the fetching, which makes
  this the *most* conservative rung, not the least.

- **Rung T0 for papers: `scholar-lookup.py`.** A DOI, arXiv id or title → Crossref, OpenAlex
  and arXiv (all keyless, all verified live) → capture-ready frontmatter with
  `capture-method: T0 scholar-lookup` plus the best open-access copy — never the publisher's
  page. Unpaywall, the most precise OA verdict, *requires* an e-mail, so it is queried only
  when `identity.contact` is set and the output says whether it was; Crossref's polite pool
  uses that contact the same way. Every registry call goes through `perform()`'s `fetch()` and
  is logged as T0. Verified: a 2015 Nature DOI resolved to its HAL green copy and 84 k
  citations; an arXiv id to its PDF.

- **Rung T3: `web-impersonate.py`, the first PEP 723 recipe.** `curl_cffi` replays a real
  browser's TLS handshake and sets the matching UA itself — the one place the UA is not the
  policy string, and the row says so. Behind `advanced_acquisition`, never automatic, with the
  entitlement reminder printed on every run. Verified against the target that motivated the
  whole ladder: the handshake gets past g2.com's TLS layer, meets a JavaScript challenge, and
  the classifier refuses to call it content — offering the Wayback snapshot instead. Honest
  result: T3 alone does not beat a JS wall; the message now says T4 would.

- **Rung T4/T5: `web-render.py`, a browser that belongs to the repo.** The author's constraint
  — repo-sandboxed, separate from the user's browser, nuked across sessions, keep only
  what is needed — enforced in code: Playwright's own Chromium in a `tempfile.mkdtemp()`
  profile destroyed in a `finally`; seeded from `cookies.txt` and nothing else, only cookies
  for the target's domain; third-party XHR, beacons, images, media and iframes aborted (scripts,
  styles, fonts allowed so pages render); no `storage_state` ever written; optional screenshot
  and HAR under `_generated/fetch/render/`, the HAR stripped of `Cookie`/`Set-Cookie`/
  `Authorization` before writing. The UA keeps the browser's real version and platform
  with one edit: even the full Chromium build announces `HeadlessChrome` in headless mode —
  found by reading the render's own HAR, after a first draft had assumed `--no-shell` would
  avoid it — and that marker is a cross-site correlator, so it is replaced by `Chrome`. The author
  then pointed at the other label of the same kind — the old chromedriver `$cdc_` / webdriver
  tell — and its modern form is Playwright's default `--enable-automation`, which sets
  `navigator.webdriver = true`; that flag is dropped and `AutomationControlled` disabled, so
  the value the page sees is `false`. That is where it stops: no fingerprint injection, no CDP
  patching, no canvas/WebGL/plugin spoofing — a test pins the boundary — because the benchmark
  put that entire tier at four targets in thirty-one, and presenting as *this* browser is the
  point. The row records both edits, the build used, and the `navigator.webdriver` value. `uv` was installed user-level for this (rc files untouched), and Chromium
  landed under `~/.cache/ms-playwright` with no sudo. Verified on a real news page: 27
  third-party requests blocked, 11 k characters and 250 links extracted, a 103-entry HAR with
  2,471 headers kept and **zero** credential headers or cookies remaining, and no profile left
  on disk.

- **New root doc `ROADMAP.md`: considered and deferred, with re-open gates.** The session
  produced a dozen decisions of the form "weighed, not built, here is what would change that"
  — a PDF tier, a crawl frontier, Save Page Now, a feed store, `protego`, a content hash — and
  they lived only in a harness-specific plan file, which nothing in the repo may depend on.
  Now they live beside the changelog as its forward-looking sibling: CHANGELOG records what
  landed, ROADMAP records what was deliberately not built and the gate that re-opens it. It
  also carries a *rejected — not to be re-proposed* list (solvers, fingerprint injection, a
  persistent browser profile, `webpage`, `--force`, contact-in-every-request), so the next
  session does not re-litigate them. Template-owned; its header holds the entry/exit rule
  (one home, rule 9); AGENTS's root-docs row and SYNC's ownership cell name it; CONTRIBUTING
  points at it. Prompted by dropping `security.allow_mitm_capture`: a policy knob nothing read
  — the mitmproxy path it reserved had been rejected in favour of HAR export — is exactly the
  kind of reserved slot that rots, so the knob went and the path became the roadmap's first row.

- **First tests in the repo, and a CI step to run them.** `tools/tests/test_recipes.py`, stdlib
  `unittest`, inline fixtures, 66 tests, **no network** (the T6 and worklist tests run the real recipes on fixtures in a temp root) — network tests would be flaky and would
  hammer third parties from CI, violating the politeness rule the fetch layer exists to encode.
  The highest-value test is derived by glob rather than enumerated, so it cannot rot: every
  recipe's five contract lines exist, contiguous and ordered; any PEP 723 block parses as TOML
  and sits outside the `-A4` window; the uv shebang appears iff a block does; `--help` exits 0.
  It also covers the robots precedence rules, the classifier's failure modes, the policy loader,
  and — deliberately — `graph.py`'s `parse_ownership`, the repo's most fragile code, twice
  bug-fixed and until now at zero coverage; that test earns its keep even if the web layer were
  reverted. CI gains one step, not a job, and **installs nothing**: running on a bare checkout
  is what proves the core is zero-install. `tools/tests/` sits under `tools/` rather than at the
  root precisely so the SYNC Ownership table needs no amendment.

- **SYNC gains a third placement class: outside the repo.** A gitignored path is still *inside*
  the tree — a backup copies it, a `grep -r` walks it, one `.gitignore` edit tracks it — so live
  credentials and authenticated browser profiles live in the environment, the OS keyring or an
  XDG state dir, with `.personal-shared/` holding only the pointer. Tools that resolve such a
  path refuse one inside the repo root. Recorded in the *Gitignored ⇒ instance-local* section,
  which already owns "where a thing lives relative to git"; the Ownership table itself is
  unchanged, since `tools/` already globs every new path this release adds. One deliberate exception is
  carved out for a research cookie jar the user exports for this purpose — see the T5 bullet.

- **`tools/recipes/local/` now exists.** It was specified in three places and present in none,
  so the first agent to need it would have had to invent whether it was tracked. A bare
  `.gitkeep`, following the `.private/` and `.personal-shared/` precedent — deliberately not a
  README, which at that path would fall inside the Ownership exclusion and become
  un-updatable by the template.

- **Rule of two amended: derivations inside a session count.** Fetching a page is the most
  repeated acquisition act in this repo's history, yet the counter never tripped, because those
  hand-rolls happened inside agent tool calls where a grep of `tools/` cannot see them. That is
  a gap in the rule rather than a loophole, and it is now stated. The clause also says plainly
  that documenting a technique in a page is not writing a recipe — which is why the ladder
  describes all seven rungs while only one recipe ships.

- **`yt-transcript` prefers `json3`, and the AGENTS grep advert got scoped.** YouTube's native
  timed-text JSON carries no rolling duplicates, so the recipe's original purpose — collapsing
  repeated VTT cues — becomes its fallback path; a missing JavaScript runtime, now required for
  full YouTube support, warns loudly instead of silently degrading. Separately, AGENTS line 10
  advertised an unscoped `grep -rF '[[stem'`, which a fetch cache would pollute; it is now
  scoped to `pages/ journals/ sources/`, matching `graph.py`'s own `NOTE_DIRS` and more correct
  regardless. `yt-transcript`'s URL mode is now gated on `[consent].acknowledged` like every
  fetch recipe, and hands `.personal-shared/cookies.txt` to `yt-dlp` when present under
  `advanced_acquisition`; `--sub` mode is offline and ungated.

## 2026-08-23

- **`.personal-shared/` is the authority for environment facts, and outranks probing.** Its
  layout row gains a read-before-claim duty: the shell an agent runs in may not be the user's
  machine (VM, container, remote host), so `lsb_release`, package and hardware queries describe
  *that shell* only — the zone is read first and treated as authoritative, a probe is reported as
  a probe of wherever the session runs, and a fact missing from the zone is asked for rather than
  inferred. Upstreamed from an instance where an agent repeatedly reported a VM's OS release and
  package versions as the user's own, and was about to recommend a package version the user's
  actual release does not ship. The instance had already documented the VM correctly, so the gap
  was **ordering** — probing before reading — not missing information, which is why the fix is a
  duty in the constitution rather than more content in the zone. `pages/ingestion-toolchain.md`'s
  "Probe before use" rule gains a pointer to it: per rule 9, probing for *whether a tool exists*
  and probing for *whose machine you are on* are distinct rules and keep one home each.

## 2026-08-06

- **Publish preparation — the template goes public at `github.com/RobertBarachini/mozak`.**
  New community files: `CONTRIBUTING.md` (a rule-9 pointer to SYNC's Ownership table and
  upstream ritual, and rule 7's definition of done) and `CITATION.cff` (researchers get
  GitHub's "Cite this repository"). README: live CI badge for the `check` workflow, the
  real clone URL, and a warning that GitHub's "Use this template" button severs the
  shared history the SYNC pull ritual needs — clone-then-rename is the sanctioned birth.
  Images: logo replaced with the corrected 1080×694 export (shipped at 840 px, the
  smaller encode); new `mozak-social-preview.png` (1280×640, for Settings → Social
  preview — GitHub ignores in-repo images for link cards). The VS Code screenshot's
  first browser tab ("Drive visualization loop…") stays visible **by design**: it is
  the agent session driving the loop beside the render — the all-in-one story the
  caption tells, not a leak (owner-confirmed).
  Consciously accepted after a full-history audit: one commit body (`43861dd`)
  names the founding instance's directory — rewriting history would invalidate every
  instance's merge-base with the template, which the SYNC contract can't survive; the
  name leaks no content. The audit found nothing else: no private-zone file was ever
  tracked, no absolute paths/emails/instance references in any tracked file, and CI
  passes on a bare clone (the ownership guard no-ops without a `template` remote).
  Post-publish, once `v1.0.0` was tagged and released: `CITATION.cff` gained
  `version: 1.0.0` + `date-released`.

- **README polish (owner additions, reworded):** the agent-bootstrap line under *Start
  an instance* became a `[!TIP]` callout, and the *Why* section's provenance sentence
  now links the owner's master's thesis in Markdown and states concretely what it
  tested (news mining of the chip shortage, iterative search-term expansion,
  occurrence trends as early-warning signals, LLMs proposed as the analysts) —
  replacing a nested-parentheses run-on with a bare URL.

- **README gains "🔬 One loop, end to end" — a worked example between Orientation and
  Why.** An 8-step walkthrough of one real research loop (scope by stakes → five-angle
  sweep → per-claim adversarial verification with a triple-lens pass on the
  highest-stakes angle → a 2-vs-1 lens split resolved by adversarially searching both
  sides, dissent kept as negative knowledge → distill/link → local render → annotation
  loop → distill-back), each step pointing at the meta page that owns the convention
  (rule 9: the section shows, the pages define). The trace is a real instance run
  **generalized per the SYNC privacy boundary**: no country/tax specifics, no amounts,
  no broker names, no instance note stems; counts (5 captures, 64 claims, 78 verdicts,
  25 notes, 14 annotations/18 exchanges, 2 distilled) are safe aggregates. Three
  owner-captured screenshots of the live loop ship in `.github/` (template-owned):
  the served render + drawer, the all-in-one VS Code view, and the in-pane note
  viewer. The screenshots show the real briefing and were **explicitly authorized by
  the owner** — the visible content (jurisdiction label, worked bps examples) is the
  owner's accepted disclosure, not covered by the prose generalization; a `[!NOTE]`
  callout under the screenshots marks them as a dated method sample — not financial
  advice, amounts illustrative — since rule 8 corrects notes but cannot reach pixels
  frozen in append-only history. Quick-nav line gained the section's anchor.

- **Logo re-homed to `.github/mozak.png` — a tracked path — so it renders on GitHub.**
  Follow-up to the facelift below: `assets/` is gitignored by contract, so the logo would
  have shown broken on any push/clone. Rather than carve a gitignore exception into the
  `assets/` contract, the image moved to `.github/` — already template-owned and tracked
  (SYNC Ownership table), and the de facto GitHub home for README imagery; repo machinery,
  not graph content, so the binary store's rules don't apply. Downscaled 1080→840 px
  (2× its 420 px display width), 312K→188K, to respect append-only history.

- **README facelift — logo, badges, quick-nav.** The template README now opens with a
  centered logo, a tagline, static shields.io badges (license, plain-Markdown,
  derived-backlinks, stdlib-only), and in-page navigation links; sections gained emoji
  headers and the design-provenance paragraph became a blockquote. **Content unchanged** —
  same prose, same claims.
  Badges are external images (shields.io) — they render on GitHub, not offline; they carry
  no repo content.

## 2026-08-02

- **Personal documents get a home: `.personal-shared/`, fronted by `medium: document`.**
  Upstreamed from an instance that needed to ingest a signed contract: a primary document
  the graph reasons *from* fitted no source `medium`, and no zone could hold its verbatim
  text (`archive/` is tracked git — wrong for a lease or a letter; `.private/` is
  agent-unreadable; `raw/` is transient). Two coordinated changes: the schema gains
  `medium: document` (contract, letter, invoice, official decision — the note fronts it;
  the verbatim text lives in `archive/`, or in `.personal-shared/` when the document is
  too personal to track) with the `url` exemption widened to match (such documents have
  no public address); and the AGENTS `.personal-shared/` layout row now names personal
  **documents** alongside personal facts — held untracked, fronted by a thin `sources/`
  capture that carries the analysis, not the specifics, so the tracked graph survives
  its documents.

## 2026-07-14 (later)

- **`annotate.py` — a transient `processing` status.** Between `pending` and
  `answered`/`distilled`, an agent may flip an entry to `[processing]` when it picks up a
  slow drain (a verification, a long synthesis) so a watched live page shows work in flight
  (pulsing chip). It is **transient, not durable**: the sole difference from every other
  status, which are properties of the annotation. Stuck-state is impossible by construction
  — `cmd_serve` **sweeps any `processing` → `pending` on startup** (single-owner: the server
  is the only process and nothing is mid-drain at boot, so leftover `processing` is a
  died-mid-drain artifact), and the Reopen button also requeues it. Optional and
  agent-agnostic: a quick drain skips straight to `answered`; the Monitor still keys on
  `[pending]`, so `processing` neither re-triggers the loop nor is counted. Documented in
  `pages/report-annotation-loop.md` (status list + drain step 2).

## 2026-07-14

- **`annotate.py` — threaded conversations per annotation (schema `annotate/1` → `annotate/2`).**
  An annotation is now a **thread**: one or more `**Prompt:**` / `**Agent:**` pairs in the
  prose (greppable, hand-editable, backward-compatible — an old single pair reads as one
  turn). A trailing unanswered `**Prompt:**` ⟺ `[pending]`. New `POST /annotations/followup`
  appends a turn from the drawer and **re-opens the entry to `pending`**, so a follow-up
  auto-re-enters the drain loop (the emit-on-rise watcher fires) and gets answered in place
  with no re-prompting. Parser (`_turns`), serializer, `_mcp_view`, and `cmd_list` all move
  to turns; the drain contract's "Record back" step is updated (append the `**Agent:**`
  after the open prompt; flip the heading only when no open turn remains).
- **Agent answers render as Markdown** in the drawer (a small self-contained renderer —
  bold/italic/code/links/lists), escaped-first for safety. `[[wikilinks]]` render as real,
  copyable note links with a 📝 marker; web links open in a new tab.
- **In-pane note viewer.** Clicking a `[[note]]` opens it **rendered in the report pane**
  (block-level Markdown: headings/lists/quotes/code + inline), with a **← Report / ← Back**
  bar; the note's own wikilinks drill deeper (back-stack). A **View raw ⇄ View rendered**
  toggle shows the note source. Backed by a new **`GET /note/<stem>`** route that serves a
  note resolved strictly through a stem→path index (`note_index`, globbing
  `pages/ journals/ sources/`) — 127.0.0.1-only, no path traversal.
- **Filtered reads — `list --status <state>`** (and the drain contract now says read the
  `[pending]` slice, not the whole file), so a drain's token cost scales with open work, not
  total history. MCP `list_annotations status=` already filtered.
- **Drawer polish:** live **search/filter** box (matches section/quote/prompts/answers);
  **newest-first** ordering within status groups; **per-card View raw ⇄ View rendered**
  toggle (`GET /annotations/raw/<id>`); a **resizable** drawer (drag the seam, width
  persisted in `localStorage`); toggling the drawer now **also toggles the report
  highlights** for a clean read; user prompts get a distinct left-border accent.
- **Fixes:** drawer sort dropped pending to the bottom via a falsy-`0` bug (`o[s]||9` where
  `pending`=0); clicks on links inside answers were swallowed by the card's focus handler;
  the note viewer preserved hard-wrap source newlines as `<br>` (now soft-wrapped per
  Markdown); justified text in the viewer (not the narrow drawer).
- Rationale: a render was answerable one-shot; now it's a **threaded, searchable,
  navigable** reading surface — and the graph became browsable from inside an annotation —
  while the seam stays a plain gitignored `annotations.md` any harness can drain.

## 2026-07-13 (later)

- **`annotate.py` serve now live-refreshes — answers land in an open render without a
  reload.** The served page polls a new cheap `GET /version` (mtimes of `annotations.md`
  + the report) every ~1.5s and, on change, calls the existing `reload()` (re-pull →
  re-anchor → re-render the drawer, which already shows the `**Agent:**` answer); a
  changed report reloads the embedded iframe and re-anchors by quote. So an agent's drain
  — flipped statuses, appended answers — appears in place while the reader watches. This
  is **client polling**, not SSE/WebSocket/MCP: fewer moving parts, no long-lived
  connections, still stdlib-only and `127.0.0.1`-only (rule 10); the file stays the seam
  (the poll reflects file state, it adds no API the agent must speak).
- **Drain cadence documented** in `pages/report-annotation-loop.md`: the drain can be
  re-run periodically (the file is the queue) — by hand or via a harness loop (e.g. Claude
  Code `/loop`), opt-in and agent-agnostic — so with live-refresh a reader sees
  freshly-flagged passages answered as the agent works.
- **Auto-drain loop guidance corrected — event, not timer** (`pages/report-annotation-loop.md`
  Cadence section, rewritten to three autonomy tiers). Field-tested finding: an in-session
  fixed-interval trigger (cron / `/loop 5m`) **does not fire** in an interactive agent
  session — there's no between-turn wall-clock scheduler — but an **event/completion wake
  channel does work** (the same one that reports a finished background task). So the live
  loop must be driven by a **file-change event**: a persistent watcher on `annotations.md`
  that **emits only when the `[pending]` count rises** (emit-on-rise — the agent's own drain
  writes lower the count, so they don't self-retrigger the loop), which wakes the agent to
  drain, then re-arms. Session-lived by nature (dies with the session — the right fit for
  interactive report investigation). True unattended draining instead needs an OS-level
  scheduler running the agent headless (cron → `claude -p`) with its own credentials, a
  least-privilege allowlist, and answer-only scoping. Also recorded: the
  `grep -c … || echo 0` double-count gotcha that silently breaks such a watcher.

## 2026-07-13

- **New tool `tools/annotate.py` — the report annotation loop.** A stdlib-only
  capture-and-serve tool: `python3 tools/annotate.py <report.html>` serves a render on
  `127.0.0.1` only (a local artifact, rule 10) inside a same-origin iframe with an injected
  overlay; the user highlights passages and attaches follow-up prompts, saved to an
  `annotations.md` beside the render. The tool applies **no AI** — no SDK, key, or model —
  so the AI harness stays a replaceable lens (`pages/plain-text-knowledge-graphs.md`): any
  agent drains the file, and swapping harness/model/provider changes neither the tool nor
  the file format. Highlights are non-destructive (CSS Custom Highlight API) and anchored by
  a text-quote selector (exact + prefix/suffix + nearest heading), so they re-attach by
  content and survive a re-render; a passage that vanishes surfaces as `orphaned`, never
  silently lost.
- **Fix — the report iframe rendered as a ~300×150 box.** The `#mzk-report` iframe was
  sized by `top/right/bottom/left` offsets with `width/height:auto`, but an `<iframe>` is a
  *replaced* element: those offsets don't stretch it and `auto` collapses to the intrinsic
  ~300×150. Now sized explicitly with `height:calc(100% - 46px)` and (drawer-open)
  `width:calc(100% - 360px)`. Reproduced in Firefox and Brave; surfaced on the loop's first
  live shakedown.
- **Drain contract in one home — `pages/report-annotation-loop.md`** (a new template-owned
  meta page): the mini-ingestion loop an agent runs over `annotations.md` (read pending →
  work → distill into `pages/` → record status + an `**Agent:**` line → journal → re-render
  → check). Linked from `pages/research-flow.md` ("Synthesizing outward" — the render's
  talk-back verb) and `pages/moc-meta.md`; the AGENTS `tools/` row points to the tool.
- **Two optional lenses over the file, never dependencies:** a Claude Code `/drain-report`
  skill (`.claude/skills/drain-report/` — a thin pointer to the contract, like `CLAUDE.md`
  is a thin shim), and a read-only MCP stdio interface (`annotate.py mcp` — a minimal
  hand-rolled JSON-RPC server, since the official SDK is a third-party dep — registered
  optionally per SETUP.md §5, defaulting to the latest render).
- **Ownership plumbing for the shipped skill:** `.claude/skills/` joins the SYNC
  Template-owned set (the guard's table parser picks up the new token, no manifest to
  maintain — rule 9); `.gitignore` ships `.claude/skills/` but keeps per-machine Claude
  state local (`.claude/*` + `!.claude/skills/`, mirroring the `raw/*` idiom).
- Rationale: a render was a one-way projection of the graph until now — this closes
  research → render → sharper research without leaving the plain-text substrate, and the
  genericity comes from the tool doing zero AI: the seam is a file, not an API.

## 2026-07-09 (later)

- **File-grain ownership replaces the two designated zones** (SYNC Ownership table).
  `pages/start-here.md` is now a **birth seed** — template-shipped at instantiation,
  instance-owned outright from then on (the `## Domains` index grows there; template-side
  edits reach only future instances; conflicts resolve keep-ours). The other
  template-shipped **meta pages move from shared-evolving to template-owned**: instances
  never edit their bodies — they annotate by *linking from their own notes*; backlinks
  are derived, so the connection surfaces without touching the shared file, and the
  in-file `## Sources` zone is gone. Shared-evolving shrinks to the four contract docs
  (`AGENTS.md`, `SYNC.md`, schema, `SETUP.md` body). Rationale: zones made ownership
  section-grained, which no tool can check; file-grain is machine-checkable, and the
  zones were solving a problem the link graph already solves.
- **`graph.py ownership` learned the new boundary.** The meta-page roster is resolved
  dynamically (ls-tree of the template ref, minus birth seeds — no maintained list,
  rule 9). Content byte-identical to the template ref is a **sync receipt**, never
  flagged — a pull-in-progress stays clean even with the pre-commit hook installed
  (fixes the mid-merge false positive an instance reported on 2026-07-09). A flagged
  roster page absent at the merge-base reports as **STEM-COLLISION** (the instance
  coined a stem the template now ships): rename the local note, then merge; collisions
  stay advisory even under `--strict`, since the authoring commit was innocent. Also
  hardened: the `template/HEAD` fallback now propagates to the roster/receipt diffs,
  and a failed receipt diff skips the filter loudly instead of blanking the candidate
  set.
- **`graph.py domains`** — derived domain lookup: frontmatter `domain:` lists → note
  count + MOC hub per domain; `domains <name>` lists that domain's notes. The MOC stays
  the curated layer; the mechanical index is derivable, so no enumeration can rot
  (rule 9). AGENTS' Domains section and `tools/` row point to it.

## 2026-07-09

- **Ownership guard — `graph.py ownership` enforces the template-owned boundary.** New
  subcommand that, in an instance (a repo with a `template` remote), flags any
  template-owned file (SYNC Ownership table) the instance authored locally — detected via
  `git diff` from the merge-base with `template/main`, so being un-pulled never
  false-positives, and birth divergences (`SETUP.md`, `README.md`) are structurally out
  of scope since they aren't template-owned. No-op in the template itself. Surfaces:
  - **advisory** inside the rule-7 `check` bracket (never changes `check`'s exit code);
  - **opt-in hard gate** via a shipped `tools/hooks/pre-commit`
    (`git config core.hooksPath tools/hooks` — SETUP);
  - an **AGENTS rule-7 clause**: in an instance, route generalizable improvements upstream
    (SYNC *Instance upstreams an improvement*), never author template-owned files locally.
  The template-owned path set is **parsed from the SYNC.md Ownership table** — the one
  normative home (rule 9), no duplicate manifest — failing loud if the parse yields zero
  paths. CI stays link-check only (a bare checkout has no `template` remote); the
  ownership-in-CI recipe is documented, not wired.
- **Gitignore Python bytecode** (`__pycache__/`, `*.pyc`): surfaced by the guard's own
  test — `graph.py` is now importable, so caches must never be committed and would
  otherwise trip the ownership guard as stray files under `tools/`.
- **New MUST rule 10 — never publish outward without authorization.** Renders
  (presentations, reports, HTML/PDF, slide decks) stay in `_generated/` or a location the
  user explicitly names; the agent must not push them, or any repo content, to
  Claude/Anthropic Artifacts or any other external destination without the user's
  explicit per-request authorization. `pages/research-flow.md` ("Synthesizing outward")
  points to it.

## 2026-07-08

- **Local-only privacy zones: `.private/` and `.personal-shared/`.** Two zones whose
  contents never enter git — each ships only an empty `.gitkeep` so a fresh clone shows
  the zone exists and is usable — documented in one home, the [AGENTS.md](AGENTS.md)
  Layout table:
  - `.private/` — the user's own notes; the agent must not read, open, or grep it
    without explicit per-request approval. Nothing readable ever ships, keeping the
    never-read rule absolute.
  - `.personal-shared/` — personal facts (name, measurements, preferences) that both the
    user and the agent may view and edit; the agent uses them to make answers concrete
    and keeps a top-level index in a local `.personal-shared/README.md` (gitignored,
    generated if absent). Never committed.
- **Introduced this `CHANGELOG.md` and split the done-log by kind (AGENTS rule 7):**
  template-system changes are recorded here; this repo's own knowledge work and
  maintenance stay in `journals/`. Before this, rule 7 sent *every* substantive change
  to a journal — which dropped template-development history into the instance-owned
  journal namespace, where it clashed with users' own dated entries on pull.
- **Made the zone model explicit** (AGENTS Layout preamble + a SYNC "gitignored ⇒
  instance-local" principle): the repo's folders sort along three independent axes —
  sync ownership, agent access, and durability — and any gitignored path is
  user-visible yet untouchable by upstream. Documents an existing guarantee (e.g.
  `_generated/presentations/`); no new directory.
- **`check` now brackets a session, not just ends it (AGENTS rule 7):** run
  `graph.py check` at the *start* of a task too — to refresh or materialize the
  gitignored `_generated/links.json` before working (notes may have been edited
  outside a checked session) — not only at done.
