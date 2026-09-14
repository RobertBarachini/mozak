#!/usr/bin/env python3
"""The README's first screen hands a fresh clone to an agent with one pasted block. These
tests keep that handoff from rotting: everything the block names must exist, the anchors it
links must match their headings, and the template marker bootstrap keys on must stay.
"""

import importlib.util
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
HEADING = "## 🤝 Hand it to your agent"


def _anchor(heading: str) -> str:
    """GitHub-style anchor: lower-case, drop everything but word chars/spaces/hyphens, spaces
    → hyphens. An emoji becomes a leading hyphen, which is what GitHub emits."""
    text = heading.lstrip("#").strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)          # the emoji goes; the space after it stays → leading hyphen
    return "#" + re.sub(r"\s+", "-", text)


def _block_after(heading: str) -> str:
    i = README.index(heading)
    m = re.search(r"```text\n(.*?)\n```", README[i:], re.S)
    assert m, "no fenced text block after the handoff heading"
    return m.group(1)


class FirstScreen(unittest.TestCase):
    def test_tldr_table_precedes_the_handoff(self):
        for row in ("| **What** |", "| **How** |", "| **Why** |"):
            self.assertIn(row, README)
            self.assertLess(README.index(row), README.index(HEADING))

    def test_handoff_comes_before_the_explanation(self):
        self.assertLess(README.index(HEADING), README.index("## What this is"))

    def test_nav_and_footer_link_to_the_handoff(self):
        anchor = _anchor(HEADING)
        self.assertEqual(anchor, "#-hand-it-to-your-agent")
        self.assertGreaterEqual(README.count(f"]({anchor})"), 2, "nav link at the top and back-link at the foot")
        self.assertGreater(README.rindex(f"]({anchor})"), README.index("## 🧠 Why"), "back-link sits after the Why")

    def test_every_nav_anchor_has_a_heading(self):
        headings = {_anchor(h) for h in re.findall(r"^## .+$", README, re.M)}
        for a in re.findall(r"\]\((#[^)]+)\)", README):
            self.assertIn(a, headings, a)


class PastedBlock(unittest.TestCase):
    def setUp(self):
        self.block = _block_after(HEADING)

    def test_everything_it_names_exists(self):
        for rel in ("AGENTS.md", "SETUP.md", "tools/bootstrap.py", "tools/graph.py", "README.md",
                    "pages/start-here.md", ".personal-shared", "journals"):
            self.assertIn(rel.rstrip("/"), self.block, f"block no longer mentions {rel}")
            self.assertTrue((ROOT / rel).exists(), f"{rel} named in the block does not exist")

    def test_clone_url_matches_the_citation(self):
        cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        url = re.search(r'repository-code:\s*"([^"]+)"', cff).group(1)
        self.assertIn(url, self.block)

    def test_block_defers_to_the_repo_and_never_prefills(self):
        self.assertIn("They win over this message", self.block)
        self.assertIn("never", self.block.lower())
        self.assertIn("I commit", self.block)

    def test_named_commands_run(self):
        for cmd in re.findall(r"`(python3 tools/[\w./-]+)`", self.block):
            r = subprocess.run([sys.executable, *cmd.split()[1:], "--help"], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(r.returncode, 0, cmd)


class Openers(unittest.TestCase):
    """`What people ask it` answers "what do I even do with this" between the handoff and the
    explanation: bold-led bullets, each carrying a quoted prompt and what it became."""

    HEADING = "## 💡 What people ask it"

    def test_sits_between_handoff_and_explanation(self):
        self.assertLess(README.index(HEADING), README.index(self.HEADING))
        self.assertLess(README.index(self.HEADING), README.index("## What this is"))
        self.assertIn(f"]({_anchor(self.HEADING)})", README, "nav links to it")

    def test_each_opener_is_a_bare_typeable_prompt(self):
        """One quoted prompt per line — no labels, no outcome clauses, no counts (author's
        call: list examples, not what each produced)."""
        section = README[README.index(self.HEADING):README.index("## What this is")]
        lines = [l for l in section.splitlines() if l.startswith("- ")]
        self.assertGreaterEqual(len(lines), 8)
        for l in lines:
            m = re.fullmatch(r'- \*"(.+)"\*', l)
            self.assertIsNotNone(m, f"not a bare quoted prompt: {l[:60]}")
            self.assertGreater(len(m.group(1)), 40, "a prompt you could actually type")
            self.assertNotRegex(l, r"\d+\s+notes|→", "outcome clauses were dropped by design")


class TemplateMarker(unittest.TestCase):
    def test_marker_survives_in_the_template_readme(self):
        spec = importlib.util.spec_from_file_location("bs", ROOT / "tools" / "bootstrap.py")
        bs = importlib.util.module_from_spec(spec); spec.loader.exec_module(bs)
        self.assertIn(bs.TEMPLATE_MARKER, README)
        self.assertGreater(README.index(bs.TEMPLATE_MARKER), README.index("## What this is"),
                           "the marker lives in the explanation, below the handoff")


if __name__ == "__main__":
    unittest.main()
