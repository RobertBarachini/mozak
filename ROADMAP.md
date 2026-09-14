# Roadmap — considered and deferred

The forward-looking sibling of [CHANGELOG.md](CHANGELOG.md): the changelog records what
landed and why; this file records what was weighed and **deliberately not built**, each with
the gate that would re-open it. It is a gated queue, not a promise. **Template-owned**
([SYNC.md](SYNC.md)) — the template authors it; an instance that wants an item sooner upstreams
the case rather than editing here.

An item enters when a change is weighed and deferred — the CHANGELOG entry for that session
names the deferral. It leaves when it lands (the CHANGELOG records the landing) or when the
reason it was considered is gone, in which case the removing commit says so. Nothing here is
derivable from a directory listing (AGENTS rule 9): every row is a decision. Instance-setup
gaps (a JavaScript runtime for `yt-dlp`, `pandoc`) are [SETUP.md](SETUP.md) §6's business, not
this file's.

## Deferred

| Item | Why not now | Re-opens when | Weighed |
|---|---|---|---|
| **mitmproxy local-capture as a T6 alternative** — its Linux eBPF `--mode local:chrome` records a human's real session with no proxy configuration | HAR export does the same job with no CA in the system trust store and no CA private key beside a knowledge repo; the policy knob that reserved it (`security.allow_mitm_capture`) was dropped because nothing read it | a capture that a HAR export cannot make — WebSocket or streaming traffic — *and* the user accepts installing a CA | 2026-09-09, 2026-09-14 |
| **Save Page Now — minting an `archive-url`** rather than finding one | `web-fetch --archive` looks up Wayback snapshots; SPN2 now requires a free archive.org S3 key for every save, and a key is a credential (outside the repo; pointer in `.personal-shared/`) | the user supplies a key; then `--archive --save` | 2026-09-14 |
| **Content hash on captures** (`content-sha256`) | the capture stores the content verbatim, so a hash pays only when something consumes it; likely a `_generated/` sidecar rather than frontmatter | a drift-check sweep over `capture-method: T2+` captures exists | 2026-09-09 |
| **`# rung:` recipe-header field** | the rung is a property of the invocation, not the file (`web-fetch` can be T1 or T5); a sixth header line forces an `-A4`→`-A5` sweep across three documents. Five `web-*` recipes exist and the catalog is still readable because each `# input:` names its rung | the catalog grep becomes hard to read | 2026-09-09 |
| **PDF tier beyond `pdftotext`/`tesseract`** — `ocrmypdf` for scans (searchable PDF/A, then extract as digital), `pymupdf4llm` for markdown, `MinerU` for math + tables; `pdftotext -layout` as the 50 ms text-layer probe first | the roster covers today's PDFs; verdicts and licences are in the research capture | a corpus `pdftotext` mangles, or a scan-heavy leg | 2026-09-09 |
| **Crawl-scale frontier** — SQLite `UPDATE … RETURNING` claim, `systemd --user` timer with `flock`; graduate to `huey`+`SqliteHuey` only if retries/priorities get hand-rolled twice | `web-worklist.py` covers multi-page work as agent-chosen targeted pulls; a frontier is for resumable multi-day sweeps. **There, robots.txt is a real gate** — that is automated traversal | a sweep the worklist cannot finish in one run and that must survive interruption | 2026-09-14 |
| **Feed store** — stdlib RSS/Atom/JSON-Feed fetcher with conditional GETs (research's pick if deps were allowed: `reader`) | `--probe` already discovers feeds; nothing yet follows a source over time | a leg that tracks a source's updates rather than reading it once | 2026-09-14 |
| **Sitemap walker in `--probe`** — parse `sitemap.xml` indexes for URLs and `lastmod` | sitemaps are listed, not parsed | a site whose sitemap is the right T0 path to a corpus | 2026-09-14 |
| **Statistical-registry recipes** — a national statistics office's PX-Web (`?config` publishes its own limits), Eurostat SDMX 3.0, data.europa.eu SPARQL, SEC bulk zips, GLEIF | the T0 roster documents them; each is a typed transformation waiting for a second hand-roll | a leg that pulls tables, not pages | 2026-09-14 |
| **HAR redaction beyond headers and cookie arrays** — `postData` bodies and URL query strings can also carry tokens | today's only kept HAR is `web-render --har`, which the sandbox produced itself; the T6 harvester never copies request bodies | a kept HAR that carries such tokens; fix is stripping `postData` and known token query parameters | 2026-09-14 |
| **`protego` for RFC 9309** | the hand-rolled parser exists because the core is stdlib; `protego` replaces it 1:1 and adds `Request-rate`/`Visit-time` | a robots.txt the hand-rolled parser misreads | 2026-09-09 |
| **`tools/_env.py`** — share `is_headless_remote()` between `annotate.py` and a browser tool | headless renders need no display, so no second consumer appeared | a second tool must decide whether a human's browser can be opened | 2026-09-14 |
| **Web Bot Auth** — RFC 9421 signed-agent identity | it identifies a *server-side* agent; a local user-directed tool has nothing to sign for | anything in this system runs server-side | 2026-09-09 |

## Rejected — not to be re-proposed

Decided against, with the reason, so the question is not re-litigated by the next session.

- **Captcha solvers, proxy/IP rotation to evade a block, paywall circumvention, credential
  sharing, fake accounts** — the line the whole ladder rests on: a host's answer is an answer.
  Not knobs, not rungs; `advanced_acquisition` does not reach them. (2026-09-09)
- **Fingerprint injection, CDP patching, canvas/WebGL/plugin spoofing** — the browser rung is
  a real browser presenting as itself; only the two labels that say "tool-driven" are
  removed. An independent benchmark put the entire stealth tier at four targets in
  thirty-one. A test pins the boundary. (2026-09-14)
- **A persistent research browser profile** — the author's constraint: the sandbox is
  ephemeral, seeded only from the user's cookie jar, destroyed on exit. (2026-09-14)
- **A browser-UA "chrome" mode as a knob** — the User-Agent is access-neutral; presenting as
  a browser is now the default for anonymity, so the knob had nothing to select. (2026-09-14)
- **A `webpage` value for `medium`** — the field names what an artifact *is*, not the pipe it
  came through. (2026-09-09)
- **`--force` on `web-fetch`** — robots.txt is recorded, never a gate, for a single read; there
  was nothing left to force. (2026-09-14)
- **A fake or no-reply contact address** — the field exists so a source can reach you; a
  fake defeats that, shares one rate-limit bucket with everyone using the same fake (Crossref
  keys its polite pool on the address), and is rejected by Unpaywall. `set` refuses it and
  `scholar-lookup` will not send one; a real dedicated alias is the anonymity-preserving
  answer. (2026-09-14)
- **Contact in every request** — a deanonymiser; sent only by source-specific recipes that
  require it, only if set, each saying so. (2026-09-14)
