#!/usr/bin/env python3
"""Stdlib tests for tools/bootstrap.py — the instance birth checklist the README's pasted
block tells an agent to run. Pure functions first; then one end-to-end run on a temp clone
of this repo, driven to `ready: yes` the way an agent would drive it. No network.
"""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem + "_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bs = _load(ROOT / "tools" / "bootstrap.py")
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]


class RepoName(unittest.TestCase):
    def test_forms(self):
        for url in ("https://github.com/RobertBarachini/mozak.git", "https://github.com/x/mozak",
                    "git@github.com:x/mozak.git", "/home/me/git/mozak", "/home/me/git/mozak/", "MOZAK"):
            self.assertEqual(bs.repo_name(url), "mozak", url)
        self.assertEqual(bs.repo_name("https://github.com/x/mojmozak.git"), "mojmozak")


class RemoteState(unittest.TestCase):
    def test_not_a_repo(self):
        ok, _, action = bs.remote_state(None)
        self.assertFalse(ok); self.assertIn("SETUP §1", action)

    def test_attached(self):
        ok, detail, action = bs.remote_state({"template": "u", "origin": "mine"})
        self.assertTrue(ok); self.assertEqual(action, "")

    def test_fresh_clone_names_the_rename(self):
        ok, detail, action = bs.remote_state({"origin": "https://github.com/x/mozak.git"})
        self.assertFalse(ok)
        self.assertIn("git remote rename origin template", action)
        self.assertIn("--attach", action)

    def test_foreign_origin_explains_both_cases(self):
        ok, _, action = bs.remote_state({"origin": "git@github.com:me/brain.git"})
        self.assertFalse(ok)
        self.assertIn("git remote add template", action)

    def test_copied_not_cloned(self):
        ok, detail, action = bs.remote_state({})
        self.assertFalse(ok); self.assertIn("copied", detail); self.assertIn("First stitch", action)


class Markers(unittest.TestCase):
    def test_live_template_readme_carries_the_marker(self):
        """The template's own README must keep the sentence bootstrap keys on."""
        self.assertTrue(bs.readme_is_template((ROOT / "README.md").read_text(encoding="utf-8")))

    def test_instance_readme_drops_it(self):
        self.assertFalse(bs.readme_is_template("# My brain\n\nMy notes about X."))

    def test_journal_state(self):
        shipped = {"journals/2026-09-09.md", "journals/2026-09-14.md"}
        self.assertFalse(bs.journal_state(["2026-09-09.md", "2026-09-14.md"], shipped, "2026-10-01")[0])
        ok, detail = bs.journal_state(["2026-09-09.md", "2026-10-01.md"], shipped, "2026-10-02")
        self.assertTrue(ok); self.assertIn("2026-10-01.md", detail)
        self.assertTrue(bs.journal_state(["2026-10-02.md"], None, "2026-10-02")[0], "no template listing: today's entry counts")
        self.assertFalse(bs.journal_state(["2026-09-09.md"], None, "2026-10-02")[0])
        ok, detail = bs.journal_state(["2026-09-14.md"], shipped, "2026-09-14", changed=["2026-09-14.md"])
        self.assertTrue(ok, "a same-dated shipped file the instance appended to is its own")


class Skeleton(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory(); self.root = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_created_empty_once_and_never_overwritten(self):
        self.assertTrue(bs.ensure_skeleton(self.root))
        p = self.root / bs.PERSONAL_README
        text = p.read_text(encoding="utf-8")
        self.assertIn(bs.PENDING, text)
        self.assertEqual(bs.skeleton_values(text), [], "the tool writes no value on the user's behalf")
        for fact in ("Address me as", "Locale", "Preferences", "Environment"):
            self.assertIn(fact, text)
        p.write_text(text.replace("| Address me as | — |", "| Address me as | Sam |"), encoding="utf-8")
        self.assertFalse(bs.ensure_skeleton(self.root))
        self.assertEqual(bs.skeleton_values(p.read_text(encoding="utf-8")), ["Sam"], "a user's value survives")

    def test_mark_asked_flips_once_and_is_idempotent(self):
        msg = bs.mark_asked(self.root, "2026-09-14")
        self.assertIn("skeleton created first", msg)
        text = (self.root / bs.PERSONAL_README).read_text(encoding="utf-8")
        self.assertNotIn(bs.PENDING, text)
        self.assertIn(f"{bs.ASKED} 2026-09-14", text)
        self.assertEqual(bs.skeleton_values(text), [], "asked ≠ answered: every fact may stay skipped")
        self.assertIn("already marked asked", bs.mark_asked(self.root, "2026-09-15"))


@unittest.skipUnless(shutil.which("git"), "git required")
class EndToEnd(unittest.TestCase):
    """A temp clone of this repo's working tree, driven from fresh clone to ready."""

    def setUp(self):
        """A working tree like a fresh clone: one commit, `origin` pointing at a bare repo
        named mozak, `origin/main` fetched — exactly what `git clone` leaves behind."""
        self._td = tempfile.TemporaryDirectory(); self.root = Path(self._td.name) / "clone"
        self.root.mkdir()
        for d in ("tools", "pages", "journals", "sources", "conventions", "templates"):
            shutil.copytree(ROOT / d, self.root / d, ignore=shutil.ignore_patterns("__pycache__"))
        for f in ("AGENTS.md", "SYNC.md", "README.md", "SETUP.md", ".gitignore"):
            shutil.copy(ROOT / f, self.root / f)
        subprocess.run([*GIT, "-C", str(self.root), "init", "-q", "-b", "main"], check=True)
        subprocess.run([*GIT, "-C", str(self.root), "add", "-A"], check=True)
        subprocess.run([*GIT, "-C", str(self.root), "commit", "-qm", "clone"], check=True)
        bare = Path(self._td.name) / "mozak.git"
        subprocess.run([*GIT, "clone", "-q", "--bare", str(self.root), str(bare)], check=True)
        subprocess.run([*GIT, "-C", str(self.root), "remote", "add", "origin", str(bare)], check=True)
        subprocess.run([*GIT, "-C", str(self.root), "fetch", "-q", "origin"], check=True)

    def tearDown(self):
        self._td.cleanup()

    def run_bs(self, *args):
        r = subprocess.run([sys.executable, str(self.root / "tools" / "bootstrap.py"), "--json", *args],
                           capture_output=True, text=True, timeout=300)
        payload = r.stdout[r.stdout.index("{"):] if "{" in r.stdout else "{}"
        return r.returncode, json.loads(payload), r.stdout

    def test_fresh_clone_to_ready(self):
        rc, res, _ = self.run_bs()
        self.assertEqual(rc, 2)
        self.assertFalse(res["ready"])
        by = {s["id"]: s for s in res["steps"]}
        self.assertEqual(list(by), ["tools", "template-remote", "graph-check", "acquisition-policy",
                                    "personal-context", "instance-readme", "founding-journal"])
        self.assertTrue(by["tools"]["ok"])
        self.assertFalse(by["template-remote"]["ok"]); self.assertEqual(res["next"], "template-remote")
        self.assertTrue(by["graph-check"]["ok"], by["graph-check"])
        self.assertFalse(by["acquisition-policy"]["ok"])
        self.assertIn("advanced_acquisition", by["acquisition-policy"]["output"], "questions pass through")
        self.assertFalse(by["personal-context"]["ok"])
        self.assertTrue((self.root / bs.PERSONAL_README).exists(), "skeleton seeded")
        self.assertFalse(by["instance-readme"]["ok"])
        self.assertFalse(by["founding-journal"]["ok"])

        # the agent does what each line says
        rc, res, _ = self.run_bs("--attach")
        by = {s["id"]: s for s in res["steps"]}
        self.assertTrue(by["template-remote"]["ok"]); self.assertIn("renamed", by["template-remote"]["detail"])
        rem = subprocess.run(["git", "-C", str(self.root), "remote"], capture_output=True, text=True).stdout.split()
        self.assertEqual(rem, ["template"])
        subprocess.run([sys.executable, str(self.root / "tools/recipes/policy.py"), "--root", str(self.root), "set",
                        "advanced_acquisition=false", "identity.user_agent=browser", "consent.acknowledged=today"],
                       check=True, capture_output=True)
        self.run_bs("--personal-context-asked")
        readme = self.root / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8").replace(bs.TEMPLATE_MARKER, "This is my instance"),
                          encoding="utf-8")
        import datetime as dt
        today = self.root / "journals" / f"{dt.date.today().isoformat()}.md"
        if today.exists():                       # the template journaled today too: append, like a real instance would
            today.write_text(today.read_text(encoding="utf-8") + "\n- Born from the template; links [[start-here]].\n",
                             encoding="utf-8")
        else:
            today.write_text("# founding\n\n- Born from the template; links [[start-here]].\n", encoding="utf-8")

        rc, res, out = self.run_bs()
        self.assertEqual(rc, 0, out)
        self.assertTrue(res["ready"]); self.assertIsNone(res["next"])
        rc2, res2, _ = self.run_bs()
        self.assertEqual((rc2, res2["ready"]), (0, True), "idempotent")
        self.assertEqual(res2["steps"], res["steps"])

    def test_text_render_and_help(self):
        r = subprocess.run([sys.executable, str(self.root / "tools" / "bootstrap.py")],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 2)
        self.assertIn("✗ template remote", r.stdout)
        self.assertIn("ready: no — next: template remote", r.stdout)
        self.assertRegex(r.stdout, r"→ run: git remote rename origin template")
        h = subprocess.run([sys.executable, str(ROOT / "tools" / "bootstrap.py"), "--help"],
                           capture_output=True, text=True)
        self.assertEqual(h.returncode, 0)

    def test_copied_folder_points_at_first_stitch(self):
        subprocess.run(["git", "-C", str(self.root), "remote", "remove", "origin"], check=True)
        rc, res, _ = self.run_bs()
        by = {s["id"]: s for s in res["steps"]}
        self.assertIn("copied", by["template-remote"]["detail"])
        self.assertIn("First stitch", by["template-remote"]["action"])


if __name__ == "__main__":
    unittest.main()
