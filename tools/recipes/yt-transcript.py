#!/usr/bin/env python3
# recipe: yt-transcript
# input:  YouTube URL, or an existing .json3/.vtt subtitle file via --sub
# output: clean transcript text on stdout (VTT rolling repeats collapsed; json3 has none)
# needs:  URL mode: yt-dlp + a JS runtime + yt-dlp-ejs (SETUP §6, no sudo); --sub: nothing
# usage:  python3 tools/recipes/yt-transcript.py <url> [--lang en] [--keep-timestamps]
#         python3 tools/recipes/yt-transcript.py --sub path/to/file.json3
"""Fetch and/or clean a YouTube transcript into capture-ready plain text.

Prefers **json3**, YouTube's native timed-text JSON: one event per caption group,
no rolling duplicates, no inline markup. VTT is the fallback for everything else,
and it is the format that needs the work — auto-caption VTT re-emits the previous
rolling line in every cue and embeds timing tags like <00:00:01.319><c> word</c>,
so this recipe collapses the repeats and strips the markup. That parsing is the
thing nobody should re-derive per session.

Human-authored subtitles beat ASR, so both --write-subs and --write-auto-subs are
requested and yt-dlp prefers the former. Run locally: cloud/datacenter IPs get
blocked. Full YouTube support needs a JavaScript runtime *and* the yt-dlp-ejs
challenge solver; the recipe asks yt-dlp itself whether both are present (its
offline `-v` header), because a runtime on PATH proves neither — see the
mozak-ingestion-toolchain page for why, SETUP §6 for the install.

URL mode is web acquisition, so it is gated on `[consent].acknowledged` like every
fetch recipe, and it hands `.personal-shared/cookies.txt` to yt-dlp when the jar is
present and `advanced_acquisition` is set (rung T5 — age-restricted or members-only
content; public captions need no cookies). `--sub` mode is offline and ungated.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import policy as _policy  # noqa: E402  (sibling recipe module, stdlib-only)

ROOT = Path(__file__).resolve().parent.parent.parent

INLINE_TAG = re.compile(r"<[^>]+>")
CUE_TIME = re.compile(r"^(\d{2}):(\d{2}):(\d{2})[.,]\d{3}\s+-->")
HEADER_BLOCK = re.compile(r"^(WEBVTT|Kind:|Language:|NOTE|STYLE|REGION)")


def clean_vtt(text: str, keep_timestamps: bool = False) -> str:
    """VTT -> deduplicated plain text (one line per surviving cue line)."""
    out, last = [], None
    stamp = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or HEADER_BLOCK.match(line) or line.isdigit():
            continue
        m = CUE_TIME.match(line)
        if m:
            h, mnt, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
            stamp = f"[{h * 60 + mnt:02d}:{s:02d}] " if keep_timestamps else ""
            continue
        line = INLINE_TAG.sub("", line).strip()
        if not line or line == last:
            continue
        out.append(stamp + line)
        last = line
    return "\n".join(out)


def clean_json3(text: str, keep_timestamps: bool = False) -> str:
    """json3 -> plain text. No dedup needed: events do not overlap by construction."""
    data = json.loads(text)
    out = []
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs:                      # window/position events carry no text
            continue
        line = "".join(s.get("utf8", "") for s in segs).strip()
        if not line:                      # bare newline segments
            continue
        if keep_timestamps:
            s = int(ev.get("tStartMs", 0)) // 1000
            line = f"[{s // 60:02d}:{s % 60:02d}] " + line
        out.append(line)
    return "\n".join(out)


def clean_sub(path: Path, keep_timestamps: bool = False) -> str:
    """Dispatch on suffix, falling back to sniffing the first byte."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json3" or text.lstrip()[:1] == "{":
        return clean_json3(text, keep_timestamps)
    return clean_vtt(text, keep_timestamps)


SETUP_FIX = "Fix: SETUP.md §6, the yt-dlp block (user-level, no sudo)."


def parse_debug_header(text: str):
    """Read yt-dlp's own `-v` debug header: (usable, listed, has_ejs), or None when the
    header carries no "JS runtimes" line (a yt-dlp from before the 2025.11 EJS change).

    The line reads like `[debug] JS runtimes: deno-2.9.8, node-20.19.2 (unsupported)`, or
    `none` / `none (disabled)`. yt-dlp marks a runtime below its minimum "(unsupported)"
    and one it could not probe "(unknown)". The challenge solver is the `yt_dlp_ejs`
    module, which yt-dlp lists under "Optional libraries" whenever it can import it."""
    listed = libs = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[debug] JS runtimes:"):
            val = line.split(":", 1)[1].strip()
            listed = [] if val.startswith("none") else [v.strip() for v in val.split(",") if v.strip()]
        elif line.startswith("[debug] Optional libraries:"):
            libs = line.split(":", 1)[1]
    if listed is None:
        return None
    usable = [v for v in listed if not v.endswith(("(unsupported)", "(unknown)"))]
    return usable, listed, bool(libs) and "yt_dlp_ejs" in libs


def runtime_warnings(report) -> list:
    """parse_debug_header() result -> warning lines; empty when YouTube support is whole."""
    if report is None:
        return ["warning: yt-dlp printed no JavaScript-runtime report, so it predates the "
                "2025.11 change that made a runtime necessary for YouTube. " + SETUP_FIX]
    usable, listed, has_ejs = report
    out = []
    if not usable:
        out.append(f"warning: yt-dlp sees no usable JavaScript runtime (found: "
                   f"{', '.join(listed) or 'none'}), so YouTube's challenges go unsolved and "
                   "formats can go missing. " + SETUP_FIX)
    if not has_ejs:
        out.append("warning: this yt-dlp lacks the yt-dlp-ejs challenge solver (distribution "
                   "packages usually do), so a runtime alone is not enough unless your yt-dlp "
                   "config sets --remote-components. " + SETUP_FIX)
    return out


def check_runtime() -> None:
    """Ask yt-dlp itself, offline: `-v` with no URL prints its header and exits 2. A
    runtime on PATH proves neither that yt-dlp accepts its version nor that the solver
    is installed, so PATH is not consulted. Degrades loudly, never blocks: captions
    often still arrive on the degraded path."""
    try:
        r = subprocess.run(["yt-dlp", "-v"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return
    warnings = runtime_warnings(parse_debug_header(r.stderr + "\n" + r.stdout))
    for w in warnings:
        print(w, file=sys.stderr)
    if warnings:
        print("Continuing on the degraded path.", file=sys.stderr)


def fetch_sub(url: str, lang: str) -> Path:
    """Fetch subtitles into a temp dir, preferring json3. Returns a path that outlives
    the temp dir by being copied to a second one the caller never has to clean up."""
    cfg, _prov = _policy.load(ROOT)
    refusal = _policy.gate(cfg)
    if refusal:
        print(refusal, file=sys.stderr)
        sys.exit(2)
    if shutil.which("yt-dlp") is None:
        sys.exit("error: yt-dlp not found. " + SETUP_FIX + " Or pass an existing "
                 "subtitle file via --sub. (Tool policy: degrade loudly.)")
    jar_path, jar_status = _policy.cookies_path(cfg, ROOT)
    if jar_path or "present" in jar_status:
        print(f"note: {jar_status}" + (" — passed to yt-dlp." if jar_path else "."), file=sys.stderr)
    check_runtime()
    td = Path(tempfile.mkdtemp(prefix="yt-transcript-"))
    cmd = ["yt-dlp", "--skip-download", "--write-subs", "--write-auto-subs",
           "--sub-langs", lang, "--sub-format", "json3/srv3/vtt",
           "-o", str(td / "sub")]
    if jar_path:
        cmd += ["--cookies", str(jar_path)]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    for pat in ("*.json3", "*.srv3", "*.vtt"):
        hits = sorted(td.glob(pat))
        if hits:
            return hits[0]
    sys.exit(f"error: no subtitles retrieved for lang '{lang}'.\n"
             f"yt-dlp said: {r.stderr.strip()[-500:] or r.stdout.strip()[-500:]}\n"
             "No captions may exist — fall back to audio + whisper "
             "(see the mozak-ingestion-toolchain page).")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?", help="YouTube URL (omit when using --sub)")
    ap.add_argument("--sub", type=Path,
                    help="clean an existing .json3/.srv3/.vtt file instead of fetching")
    ap.add_argument("--vtt", type=Path, help=argparse.SUPPRESS)   # pre-json3 alias
    ap.add_argument("--lang", default="en", help="subtitle language (default: en)")
    ap.add_argument("--keep-timestamps", action="store_true",
                    help="prefix lines with [mm:ss] cue starts")
    args = ap.parse_args()
    sub = args.sub or args.vtt
    if not sub and not args.url:
        ap.error("give a URL or --sub FILE")
    path = sub if sub else fetch_sub(args.url, args.lang)
    print(clean_sub(path, keep_timestamps=args.keep_timestamps))
    return 0


if __name__ == "__main__":
    sys.exit(main())
