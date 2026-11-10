---
title: "Research: yt-dlp's JavaScript runtime, how to install it, and GitHub reads without a login"
type: source
domain: [meta]
medium: report
author: interactive agent session (Claude Opus 5.5), measurements on an Ubuntu 26.04 machine
retrieved: 2026-11-07
created: 2026-11-07
updated: 2026-11-07
tags: [founding, tooling]
---

# Research: yt-dlp's JavaScript runtime, how to install it, and GitHub reads without a login

Internal agent-generated research, so no `url:` (schema exception for `medium: report`). It
started when a transcript fetch on an Ubuntu 26.04 machine printed `yt-dlp`'s "No supported
JavaScript runtime could be found" warning, and SETUP's fix (`pip install`) turned out not to run
there. Everything below is either quoted from a primary source (URL given) or measured in the
session (command given). Distilled into [[mozak-ingestion-toolchain]] (rule 2, the `yt-dlp` row
and its subsection) and [[mozak-web-acquisition-ladder]] (the code-hosting T0 row).

## 1. What `yt-dlp` needs for YouTube, as of 2026-11

- **Two pieces beyond `yt-dlp` itself.** The Debian package's `NEWS.Debian` (2025-11-17): "As of
  yt-dlp 2025.11.12, downloading YouTube videos requires an external JavaScript engine (such as
  Deno, Nodejs, or QuickJS) and the yt-dlp-ejs module (not packaged yet.)"
- **Runtimes, from the `yt-dlp` EJS wiki page** (https://github.com/yt-dlp/yt-dlp/wiki/EJS, read
  raw 2026-11-07): Deno "(recommended)", "Enabled by default", minimum 2.3.0; Node "Enable with
  `--js-runtimes node`", minimum 22.0.0, "Runs code with *some* permissions restricted";
  QuickJS / QuickJS-NG enabled with `--js-runtimes quickjs`, older builds "missing optimizations
  which can lead to execution times of several minutes"; Bun "(deprecated)", "Versions after
  `1.3.14` are not supported, and support may be dropped entirely in the future."
- **Where the solver comes from (same page, step 2):** official PyInstaller executables and the
  official zipimport binary bundle `yt-dlp-ejs` ("No additional action required"); the PyPI
  package needs the `default` dependency group (`pip install -U "yt-dlp[default]"`); for
  third-party packages it "will depend on if your third-party package repository ships or bundles
  the EJS script package".
- **Bun's deprecation, from `yt-dlp` issue 16766** ("[Announcement] Bun support is now limited and
  deprecated", closed 2026-05-24): supported range narrowed to 1.2.11–1.3.14, the floor because
  building `ejs` with older Bun ignores its lockfile ("a significant security concern… considering
  all of the recent npm supply chain attacks"), the ceiling because "Bun was recently rewritten in
  Rust", 1.3.14 being "the last release built from the original zig codebase". GitHub's release API
  dates 1.3.14 to 2026-05-13 and 1.4.0 to 2026-08-20; the repository's language breakdown read 77%
  Rust on 2026-11-07. The installed source's own comment lists "No sandboxing options available"
  among Bun's known issues.
- **How `yt-dlp` sandboxes Deno** (installed source, `jsc/_builtin/deno.py`): `--ext=js
  --no-code-cache --no-prompt --no-remote --no-lock --node-modules-dir=none --no-config`, plus
  `--no-npm --cached-only` as observed in a verbose run. For Node it adds `--permission`
  (`--experimental-permission` below Node 23.5).
- **Release channel:** the `yt-dlp` README calls `nightly` "the **recommended channel for regular
  users** of yt-dlp" — which `uv tool install --pre` selects.

## 2. Why not the distribution, and why not pip

- **Solver packaging (Repology API, 2026-11-07):** of Ubuntu 24.04/26.04, Debian 13, Fedora 43/44,
  Arch and openSUSE Tumbleweed, only Arch packages `yt-dlp-ejs` (0.8.0).
- **Distribution Node vs `yt-dlp`'s minimum of 22 (Repology, same day):** Ubuntu 24.04 18.19.1;
  Debian 13 20.19.2; Ubuntu 26.04 22.22.1; Fedora 43/44 ship `nodejs20`, `nodejs22` and `nodejs24`;
  Arch 26.13.0. So `apt install nodejs` gives an unsupported runtime on Ubuntu 24.04 and Debian 13.
- **Deno in distributions:** not in Debian ("it's not in Debian (#961337)", same `NEWS.Debian`).
- **pip:** the Ubuntu 26.04 machine had no `pip`, and Debian-family Pythons refuse system-wide
  installs since PEP 668 (`externally-managed-environment`), so SETUP's previous line could not
  run.

## 3. The install that works, measured

- **Dry run first:** `uv pip install --dry-run --pre "yt-dlp[default,deno]"` into a throwaway
  venv resolved `deno==2.9.8`, `yt-dlp-ejs==0.8.0` and `yt-dlp==2026.11.4.232659.dev0`.
- **Install:** `uv tool install --pre "yt-dlp[default,deno]" --with-executables-from deno` put
  `yt-dlp` and `deno` in `~/.local/bin`, ahead of the distribution's `/usr/bin/yt-dlp` on PATH. No
  sudo. Without `--with-executables-from`, `yt-dlp` would still find Deno (its runtime lookup
  checks its own environment's scripts directory before PATH, `utils/_jsruntime.py`), but a PATH
  probe would not.
- **Verified:** the verbose log showed `JS runtimes: deno-2.9.8`, the solver loaded "source:
  python package", and "Solving JS challenges using deno".
- **What the degraded path had cost** on one test video: one format (18, progressive 360p) of 54.
  The distribution build fell back to YouTube's visionOS client, which still served formats
  without a challenge. The margin is YouTube's to withdraw.

## 4. Checking it: ask `yt-dlp`, not PATH

- `yt-dlp -v` with no URL prints its debug header and exits 2 with a usage message, offline. The
  header carries `[debug] Optional libraries: …` (which lists `yt_dlp_ejs-<version>` whenever the
  module imports, per `yt_dlp/dependencies`) and `[debug] JS runtimes: …`, formatted in
  `YoutubeDL.py` as `name-version`, with " (unsupported)" appended below the minimum, "(unknown)"
  when unprobed, and `none` or `none (disabled)` otherwise.
- **The case a PATH check misses, measured:** with Deno on PATH, the distribution build reported
  `JS runtimes: deno-2.9.8` but no `yt_dlp_ejs` among its libraries, so it still could not solve
  challenges. The previous recipe check (a runtime binary on PATH) would have passed it. The
  reverse case also occurred: Deno inside the tool environment, none on PATH, and the old check
  warned although `yt-dlp` was whole.

## 5. GitHub reads without a login

- **`gh` 2.103.3 with an empty config and no token** (unpacked to a scratch directory, never
  installed): `gh issue view`, `gh api` and `gh release list` against public repositories each
  answered "To get started with GitHub CLI, please run: gh auth login… Alternatively, populate the
  GH_TOKEN environment variable". So `gh` offers no anonymous reads; a login grants an agent the
  human's write access.
- **Anonymous REST API:** `GET https://api.github.com/rate_limit` reported a core limit of 60 per
  hour (search 10 per minute). Issues, releases and repository language statistics read cleanly
  with `curl -H "Accept: application/vnd.github+json"`. Wiki pages are plain Markdown at
  `https://raw.githubusercontent.com/wiki/<owner>/<repo>/<Page>.md` (HTTP 200 for the EJS page),
  outside the API limit.

## 6. Distribution package names for the sudo-level tools (Repology, 2026-11-07)

`poppler` and `tesseract` source packages exist on every distribution checked (Repology lists
tesseract under the project `tesseract-ocr`); `ffmpeg` too, with Fedora's official build reduced
and the full one in RPM Fusion. The binary package names in SETUP's table (`poppler-utils`,
`tesseract-ocr`, `ffmpeg-free`, `tesseract-data-<lang>`, …) are the distributions' established
names; Repology's API returned source names only for most of them, so the table points readers to
repology.org for anything else.

## Stop record

Stopped at decision sufficiency: every claim the docs make is either a primary-source quote
above or a measurement on the machine. Not checked: whether the official PyInstaller build's
`-v` header lists `yt_dlp_ejs` (the dependency table says it would), Windows and macOS install
paths, and Whisper's install.

## Distilled into

- [[mozak-ingestion-toolchain]] — tool-policy rule 2 (user-level first, sudo only for system
  plumbing, with the user's distribution's command), the `yt-dlp` and `pandoc` roster rows, and
  the subsection *`yt-dlp` and its JavaScript runtime*.
- [[mozak-web-acquisition-ladder]] — the code-hosting row of the T0 roster.
