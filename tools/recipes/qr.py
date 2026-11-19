#!/usr/bin/env -S uv run --quiet --script
# recipe: qr
# input:  short text or a URL (argument, or stdin) for a device that shares no clipboard or network with this one
# output: a QR code drawn in the terminal, nothing written; or an image at the path given by --out (.png/.svg)
# needs:  uv, which resolves segno (pure Python) from the inline block; nothing is installed globally
# usage:  uv run tools/recipes/qr.py [<text> | - < file] [--out file.png] [--allow-secret] [--style auto|wide|compact]

# /// script
# requires-python = ">=3.11"
# dependencies = ["segno>=1.6"]
# ///
"""Hand a few hundred bytes to a device that shares nothing with this one.

A phone, a phone profile kept isolated, a fresh install with no accounts: when
there is no clipboard, sync or network path, the camera still works. A QR code
moves a URL, a public key or a short config one way, opens no channel, and needs
nothing installed on the receiving side.

Two outputs, chosen by who will see the code:

- Terminal (the default). Nothing is written to disk. For a person running the
  command in their own terminal, and the only mode for a secret.
- Image (`--out file.png` or `.svg`). An agent's shell output seldom reaches the
  person, so an agent writes the image to a path it chooses and gives them that
  path to open. When stdout is not a terminal, the recipe says so.

Gotchas it encapsulates:

- Secrets stay off disk. Text that looks like a private key (PEM, OpenSSH, PGP),
  a WireGuard PrivateKey or PresharedKey line, a one-time-password seed
  (otpauth://) or a Wi-Fi password (WIFI:...P:) is refused with `--out` unless
  `--allow-secret` is given: an image outlives the scan, lands in caches and
  backups, and is exactly as readable as the text. For a secret, an agent hands
  the person the terminal command, with the secret piped from its file
  (`- < file`) so it stays out of shell history. A public key is not a secret.
- Never a Micro QR. segno's `make()` picks Micro QR for short input, which many
  phone scanners cannot read; this calls `make_qr()`.
- Fixed black and white in the terminal. segno's own terminal writer paints dark
  modules in the terminal's background colour, so on a light theme the code comes
  out inverted. This draws with the 256-colour palette's pure black (16) and pure
  white (231), which colour themes leave alone in practice. Where two stacked
  modules share a colour it prints a space on that background rather than a glyph,
  because some terminals (VS Code's, by default) lighten a foreground that matches
  its background.
- Size. An image reads at every size: at 10 px per module, codes up to version 40,
  the QR maximum (about 2.3 KB at level M), scanned off a laptop screen with a
  phone camera (one phone, 2026-11-19; version 40 took half a second to focus).
  The terminal draws a module in one or two character cells, so there the recipe
  still warns past version 25 (about 1 KB), a threshold no scan has tested yet.
  Past the QR maximum it exits 1. For more, move a file instead: a cable, or a
  one-shot local web server whose URL this recipe can encode.

Conventions: AGENTS.md; this recipe never writes into the graph.
"""

import argparse
import math
import re
import shutil
import sys
from pathlib import Path

BORDER = 4            # the quiet zone the QR standard asks for, in modules
IMAGE_SCALE = 10      # pixels per module in --out images
DENSE_VERSION = 25    # above this (about 1 KB at error level M), warn in the terminal

SECRET_PATTERNS = (
    (re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY"), "a private key"),
    (re.compile(r"(?im)^\s*(?:PrivateKey|PresharedKey)\s*="), "a WireGuard private or preshared key"),
    (re.compile(r"(?i)^otpauth(?:-migration)?://"), "a one-time-password seed"),
    (re.compile(r"(?is)^WIFI:(?:.*;)?P:[^;]"), "a Wi-Fi password"),
)

# 256-colour cube corners: pure black and pure white, outside the themed 16.
FG = {True: "\033[38;5;16m", False: "\033[38;5;231m"}
BG = {True: "\033[48;5;16m", False: "\033[48;5;231m"}
RESET = "\033[0m"
UPPER_HALF = "▀"


def secret_kind(text: str) -> str | None:
    """What kind of secret the text looks like, or None. Errs towards caution."""
    stripped = text.strip()
    for rx, kind in SECRET_PATTERNS:
        if rx.search(stripped):
            return kind
    return None


def too_dense(version: int, image: bool) -> bool:
    """Whether to warn that a phone may not read the code. Terminal only (see Size)."""
    return not image and version > DENSE_VERSION


def choose_style(width: int, height: int, cols: int, lines: int) -> tuple[str, bool]:
    """Wide (two columns per module) when it fits the terminal, else compact.

    Returns (style, fits). One line is kept free for the prompt.
    """
    room = max(lines - 1, 1)
    if 2 * width <= cols and height <= room:
        return "wide", True
    return "compact", width <= cols and math.ceil(height / 2) <= room


def render(rows: list[list[bool]], style: str) -> str:
    """ANSI drawing of a module grid (True = dark), quiet zone already included."""
    out = []
    if style == "wide":
        for row in rows:
            line, prev = [], None
            for dark in row:
                if dark != prev:
                    line.append(BG[dark])
                    prev = dark
                line.append("  ")
            out.append("".join(line) + RESET)
        return "\n".join(out)
    if len(rows) % 2:                                   # pad with a light half-row
        rows = rows + [[False] * len(rows[0])]
    for top, bottom in zip(rows[0::2], rows[1::2]):
        line, prev = [], None
        for t, b in zip(top, bottom):
            # Same colour: a space on that background, so no terminal can
            # "fix" a foreground that matches its background.
            cell = (BG[t], " ") if t == b else (FG[t] + BG[b], UPPER_HALF)
            if cell[0] != prev:
                line.append(cell[0])
                prev = cell[0]
            line.append(cell[1])
        out.append("".join(line) + RESET)
    return "\n".join(out)


def read_input(arg: str | None) -> str:
    if arg is not None and arg != "-":
        return arg
    if sys.stdin.isatty():
        sys.exit("error: give the text as an argument, or pipe it in: qr.py - < file")
    return sys.stdin.read().rstrip("\r\n")


def _need():
    try:
        import segno
        return segno
    except ImportError:
        sys.exit("error: segno unavailable. Run this recipe with uv:\n"
                 "    uv run tools/recipes/qr.py <text>\n"
                 "  or use the venv fallback in tools/recipes/README.md (packages are listed in "
                 "this file's `# /// script` block). (Tool policy: degrade loudly.)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("text", nargs="?", help="the text or URL; omit or '-' to read stdin")
    ap.add_argument("--out", type=Path, help="write an image here instead (.png or .svg)")
    ap.add_argument("--allow-secret", action="store_true",
                    help="write an image even when the text looks like a secret")
    ap.add_argument("--style", choices=("auto", "wide", "compact"), default="auto",
                    help="terminal drawing: wide = two columns per module; compact = half blocks")
    args = ap.parse_args(argv)

    text = read_input(args.text)
    if not text:
        sys.exit("error: nothing to encode")
    kind = secret_kind(text)
    if kind and args.text not in (None, "-"):
        print(f"note: this looks like {kind}, and as an argument it is now in your shell "
              "history. Next time pipe it from its file: qr.py - < file", file=sys.stderr)
    if kind and args.out and not args.allow_secret:
        print(f"refused: this looks like {kind}. An image file outlives the scan. Show it in "
              "your own terminal instead (run without --out), or pass --allow-secret and "
              "delete the image after scanning.", file=sys.stderr)
        return 2

    segno = _need()
    try:
        qr = segno.make_qr(text, error="m")
    except segno.DataOverflowError:
        print(f"error: {len(text.encode())} bytes is more than a QR code holds; move a file "
              "instead.", file=sys.stderr)
        return 1
    size = qr.symbol_size(scale=1, border=0)[0]
    print(f"QR {qr.designator}: {size}x{size} modules, {len(text.encode())} bytes",
          file=sys.stderr)
    if too_dense(qr.version, image=bool(args.out)):
        print("warning: a code this dense may not read off a terminal. Zoom in, or for text "
              "that is not a secret write an image with --out, which reads at every size.",
              file=sys.stderr)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        try:
            qr.save(str(args.out), scale=IMAGE_SCALE, border=BORDER)
        except ValueError as e:
            print(f"error: {e} (use .png or .svg)", file=sys.stderr)
            return 2
        print(args.out.resolve())
        if kind:
            print("note: delete the image once it is scanned.", file=sys.stderr)
        return 0

    rows = [[bool(m) for m in r] for r in qr.matrix_iter(scale=1, border=BORDER)]
    term = shutil.get_terminal_size(fallback=(80, 24))
    style, fits = choose_style(len(rows[0]), len(rows), term.columns, term.lines)
    if args.style != "auto":
        style = args.style
    print(render(rows, style))
    if not sys.stdout.isatty():
        print("note: stdout is not a terminal. If an agent ran this, the person probably cannot "
              "see the code: write an image with --out and give them its path, or hand them this "
              "command to run in their own terminal.", file=sys.stderr)
    elif not fits:
        print(f"note: the code is larger than this {term.columns}x{term.lines} terminal; enlarge "
              "the window or zoom out before scanning.", file=sys.stderr)
    if kind:
        print("note: after scanning, clear the screen and scrollback (`clear`).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
