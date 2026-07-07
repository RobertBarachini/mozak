#!/usr/bin/env python3
# recipe: yt-transcript
# input:  YouTube URL (or an existing .vtt file via --vtt)
# output: clean deduplicated transcript text on stdout (auto-caption rolling
#         repeats collapsed, inline timing/markup tags stripped)
# needs:  yt-dlp (only for URL mode; --vtt mode is dependency-free)
# usage:  python3 tools/recipes/yt-transcript.py <url> [--lang en] [--keep-timestamps]
#         python3 tools/recipes/yt-transcript.py --vtt path/to/file.vtt
"""Fetch and/or clean a YouTube transcript into capture-ready plain text.

YouTube auto-captions duplicate content across overlapping cues (each cue
re-emits the previous rolling line) and embed inline timing tags like
<00:00:01.319><c> word</c>. This recipe collapses the repeats and strips the
markup — the exact parsing nobody should re-derive per session. Run locally:
cloud/datacenter IPs get blocked (see the ingestion-toolchain page).
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

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


def fetch_vtt(url: str, lang: str) -> str:
    if shutil.which("yt-dlp") is None:
        sys.exit("error: yt-dlp not found. Install it (e.g. `uv tool install yt-dlp`) "
                 "or pass an existing file via --vtt. (Tool policy: degrade loudly.)")
    with tempfile.TemporaryDirectory(prefix="yt-transcript-") as td:
        cmd = ["yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs",
               "--sub-langs", lang, "--sub-format", "vtt",
               "-o", str(Path(td) / "sub"), url]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        vtts = sorted(Path(td).glob("*.vtt"))
        if not vtts:
            sys.exit(f"error: no subtitles retrieved for lang '{lang}'.\n"
                     f"yt-dlp said: {r.stderr.strip()[-500:] or r.stdout.strip()[-500:]}\n"
                     "No captions may exist — fall back to audio + whisper "
                     "(see the ingestion-toolchain page).")
        return vtts[0].read_text(encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?", help="YouTube URL (omit when using --vtt)")
    ap.add_argument("--vtt", type=Path, help="clean an existing .vtt file instead of fetching")
    ap.add_argument("--lang", default="en", help="subtitle language (default: en)")
    ap.add_argument("--keep-timestamps", action="store_true",
                    help="prefix lines with [mm:ss] cue starts")
    args = ap.parse_args()
    if not args.vtt and not args.url:
        ap.error("give a URL or --vtt FILE")
    text = args.vtt.read_text(encoding="utf-8") if args.vtt else fetch_vtt(args.url, args.lang)
    print(clean_vtt(text, keep_timestamps=args.keep_timestamps))
    return 0


if __name__ == "__main__":
    sys.exit(main())
