#!/usr/bin/env python3
"""Stdlib unit tests for tools/graph.py's shipped-rename machinery — the reserved stem
prefix and the ledger an instance replays with `migrate` (AGENTS `pages/` row, rule 6).
Every test builds its own temp repo; nothing here reads the live graph, so the suite
passes in an instance whose own pages legitimately lack the prefix. The prefix itself
is taken from graph.RESERVED_PREFIX, never spelled out, so a future change of token is
one constant.
"""

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _load_graph():
    spec = importlib.util.spec_from_file_location("graph_under_test", ROOT / "tools" / "graph.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


graph = _load_graph()
P = graph.RESERVED_PREFIX


def _note(root: Path, rel: str, title: str, body: str = ""):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"---\ntitle: {title}\ntype: note\ndomain: [t]\ncreated: 2026-01-01\n"
                 f"updated: 2026-01-01\nstatus: seed\n---\n\n# {title}\n\n{body}\n", encoding="utf-8")
    return p


def _ledger(root: Path, rows):
    p = root / graph.MIGRATIONS
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# comment line\n\n" + "".join(f"{d}\t{o}\t{n}\n" for d, o, n in rows), encoding="utf-8")


def _run(fn, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(*args)
    return rc, buf.getvalue()


class TempRepo(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()


class Prefix(unittest.TestCase):
    def test_prefix_is_a_project_token_not_a_word(self):
        """A reserved prefix must be something no research topic coins: kebab-safe, ending
        in a hyphen, and not the system's own domain name (`meta-` is a company and a
        dictionary prefix — CHANGELOG 2026-09-14)."""
        self.assertTrue(P.endswith("-"))
        self.assertEqual(P[:-1], graph.slugify(P[:-1]))
        self.assertNotEqual(P, "meta-")


class Ledger(TempRepo):
    def test_missing_ledger_is_empty(self):
        self.assertEqual(graph.load_migrations(self.root), [])

    def test_parses_rows_and_skips_comments(self):
        _ledger(self.root, [("2026-09-14", "a", f"{P}a"), ("2026-09-15", "b", f"{P}b")])
        self.assertEqual(graph.load_migrations(self.root),
                         [("2026-09-14", "a", f"{P}a"), ("2026-09-15", "b", f"{P}b")])

    def test_malformed_row_raises(self):
        p = self.root / graph.MIGRATIONS
        p.parent.mkdir(parents=True)
        p.write_text(f"2026-09-14 a {P}a\n", encoding="utf-8")   # spaces, not tabs
        with self.assertRaises(ValueError):
            graph.load_migrations(self.root)

    def test_chain_resolves_to_final_stem(self):
        rows = [("d", "a", "b"), ("d", "b", "c"), ("d", "x", "y")]
        self.assertEqual(graph.resolve_chain(rows), {"a": "c", "b": "c", "x": "y"})

    def test_chain_cycle_terminates(self):
        rows = [("d", "a", "b"), ("d", "b", "a")]
        out = graph.resolve_chain(rows)
        self.assertEqual(set(out), {"a", "b"})

    def test_live_ledger_parses_and_is_kebab(self):
        """The shipped ledger itself must parse; its stems must be valid link targets, and
        every row lands inside the reserved prefix."""
        rows = graph.load_migrations(ROOT)
        self.assertTrue(rows, "template ships a non-empty ledger")
        for _, o, n in rows:
            self.assertEqual(o, graph.slugify(o))
            self.assertEqual(n, graph.slugify(n))
            self.assertTrue(n.startswith(P), n)


class Migrate(TempRepo):
    def _instance_after_pull(self):
        """The template renamed a -> <P>a and the pull brought the new file; the instance's
        own notes still link the old stem in all three link forms."""
        _note(self.root, f"pages/{P}a.md", "A", "Shipped page.")
        _note(self.root, "pages/mine.md", "Mine",
              f"See [[a]] and [[a|shown]] and [[a#sec]] but not [[ab]] nor [[{P}a]].")
        _note(self.root, "journals/2026-01-02.md", "Log", "- touched [[a]]")
        _note(self.root, "pages/ab.md", "AB", "Distinct stem that shares a prefix.")
        _ledger(self.root, [("2026-09-14", "a", f"{P}a")])

    def test_rewrites_all_three_link_forms_only(self):
        self._instance_after_pull()
        rc, out = _run(graph.cmd_migrate, self.root)
        self.assertEqual(rc, 0)
        mine = (self.root / "pages/mine.md").read_text(encoding="utf-8")
        self.assertIn(f"[[{P}a]] and [[{P}a|shown]] and [[{P}a#sec]]", mine)
        self.assertIn("not [[ab]]", mine, "a longer stem sharing the prefix is untouched")
        self.assertNotIn(f"[[{P}{P}a]]", mine, "an already-migrated link is not re-prefixed")
        self.assertIn(f"[[{P}a]]", (self.root / "journals/2026-01-02.md").read_text(encoding="utf-8"))
        self.assertIn("2 file(s) rewritten", out)
        self.assertIn(f"[[a]] -> [[{P}a]]  (4 link(s))", out)

    def test_idempotent(self):
        self._instance_after_pull()
        _run(graph.cmd_migrate, self.root)
        before = {p: p.read_text(encoding="utf-8") for p in graph.md_files(self.root)}
        rc, out = _run(graph.cmd_migrate, self.root)
        self.assertEqual(rc, 0)
        self.assertIn("nothing pending", out)
        self.assertEqual(before, {p: p.read_text(encoding="utf-8") for p in graph.md_files(self.root)})

    def test_local_note_with_old_stem_is_left_alone(self):
        """Both stems exist: the instance authored its own `a` after the template moved
        on, so `[[a]]` means theirs. Nothing is rewritten, and the run says why."""
        self._instance_after_pull()
        _note(self.root, "pages/a.md", "My own A", "Coined locally.")
        rc, out = _run(graph.cmd_migrate, self.root)
        self.assertEqual(rc, 0)
        self.assertIn("[[a]] left alone", out)
        self.assertIn("[[a]] and [[a|shown]]", (self.root / "pages/mine.md").read_text(encoding="utf-8"))

    def test_chain_lands_on_current_stem(self):
        _note(self.root, "pages/c.md", "C", "Final home.")
        _note(self.root, "pages/mine.md", "Mine", "Old link: [[a]]. Middle link: [[b]].")
        _ledger(self.root, [("2026-01-01", "a", "b"), ("2026-02-01", "b", "c")])
        rc, _ = _run(graph.cmd_migrate, self.root)
        self.assertEqual(rc, 0)
        self.assertEqual("Old link: [[c]]. Middle link: [[c]].",
                         [l for l in (self.root / "pages/mine.md").read_text(encoding="utf-8").splitlines()
                          if l.startswith("Old link")][0])

    def test_not_yet_pulled_is_a_noop(self):
        """The ledger arrived (say, via a partial merge) but the renamed file did not:
        the old note is still here, so there is nothing to repoint."""
        _note(self.root, "pages/a.md", "A", "Still the old file.")
        _note(self.root, "pages/mine.md", "Mine", "[[a]]")
        _ledger(self.root, [("2026-09-14", "a", f"{P}a")])
        rc, out = _run(graph.cmd_migrate, self.root)
        self.assertEqual(rc, 0)
        self.assertIn("nothing pending", out)
        self.assertIn("[[a]]", (self.root / "pages/mine.md").read_text(encoding="utf-8"))

    def test_no_ledger_is_a_noop(self):
        _note(self.root, "pages/mine.md", "Mine", "[[a]]")
        rc, out = _run(graph.cmd_migrate, self.root)
        self.assertEqual(rc, 0)
        self.assertIn("no ledger", out)


class CheckHint(TempRepo):
    def test_check_names_migrate_for_stale_shipped_stems(self):
        _note(self.root, f"pages/{P}a.md", "A", "Shipped.")
        _note(self.root, "pages/mine.md", "Mine", "[[a]] and [[truly-missing]]")
        _ledger(self.root, [("2026-09-14", "a", f"{P}a")])
        rc, out = _run(graph.cmd_check, self.root)
        self.assertEqual(rc, 1)
        self.assertIn("BROKEN pages/mine.md -> [[a]]", out)
        self.assertIn("hint: 1 broken target(s) are stems the template renamed (a)", out)
        self.assertIn("graph.py migrate", out)
        self.assertNotIn("truly-missing)", out.split("hint:")[1], "a plain broken link is not blamed on a rename")

    def test_check_green_after_migrate(self):
        _note(self.root, f"pages/{P}a.md", "A", "Shipped, links back to [[mine]].")
        _note(self.root, "pages/mine.md", "Mine", "[[a]]")
        _ledger(self.root, [("2026-09-14", "a", f"{P}a")])
        _run(graph.cmd_migrate, self.root)
        rc, out = _run(graph.cmd_check, self.root)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("hint:", out)

    def test_no_hint_without_ledger(self):
        _note(self.root, "pages/mine.md", "Mine", "[[gone]]")
        rc, out = _run(graph.cmd_check, self.root)
        self.assertEqual(rc, 1)
        self.assertNotIn("hint:", out)


class ReservedPrefix(unittest.TestCase):
    def test_local_prefixed_page_outside_roster_is_flagged(self):
        roster = [f"pages/{P}a.md", "pages/moc-meta.md"]
        local = [f"pages/{P}a.md", f"pages/{P}mine.md", "pages/notes.md", "pages/start-here.md"]
        self.assertEqual(graph.reserved_violations(local, roster), [f"pages/{P}mine.md"])

    def test_birth_seed_and_plain_stems_never_flagged(self):
        """The bare token without its hyphen is an ordinary stem, as is any topic word:
        a note about Meta Platforms or a meta-analysis is nobody's business but the instance's."""
        local = ["pages/start-here.md", f"pages/{P[:-1]}.md", "pages/meta-analysis-methods.md", "pages/meta-llama.md"]
        self.assertEqual(graph.reserved_violations(local, []), [])


class OwnershipCell(unittest.TestCase):
    """The SYNC Ownership cell is parsed at run time: every backticked token becomes an
    owned path glob. The reserved-prefix glob must be there — and a stray `pages/` in
    backticks (the hazard the 2026-09-14 edit nearly shipped) would claim every instance
    page as template-owned."""

    def test_prefix_glob_and_hub_are_owned_and_bare_pages_is_not(self):
        owned, excludes, _ = graph.parse_ownership(ROOT)
        self.assertIn(f"pages/{P}*.md", owned)
        self.assertIn("pages/moc-meta.md", owned)
        self.assertNotIn("pages", owned, "a backticked `pages/` in the cell would own every instance page")
        self.assertIn("pages/start-here.md", excludes, "the birth seed stays instance-owned")


class TemplateConvention(TempRepo):
    def test_clean_template_passes(self):
        _note(self.root, f"pages/{P}a.md", "A", "[[moc-meta]]")
        _note(self.root, "pages/moc-meta.md", "Hub", f"[[{P}a]]")
        _note(self.root, "pages/start-here.md", "Start", "[[moc-meta]]")
        _ledger(self.root, [("2026-09-14", "a", f"{P}a")])
        self.assertEqual(graph.template_convention(self.root), [])
        rc, out = _run(graph.cmd_ownership, self.root, False, "template/main", True, False, True)
        self.assertEqual(rc, 0)
        self.assertIn("0 convention problem(s)", out)

    def test_unprefixed_page_and_bad_ledger_rows_are_named(self):
        _note(self.root, f"pages/{P}a.md", "A")
        _note(self.root, "pages/rogue.md", "Rogue")
        _note(self.root, "pages/b.md", "B still here")
        _ledger(self.root, [("2026-09-14", "b", f"{P}b"), ("2026-09-14", "c", "Not Kebab")])
        problems = graph.template_convention(self.root)
        joined = "\n".join(problems)
        self.assertIn(f"pages/rogue.md: shipped page without the `{P}` prefix", joined)
        self.assertIn(f"pages/b.md: shipped page without the `{P}` prefix", joined)
        self.assertIn(f"b -> {P}b: no note '{P}b' exists", joined)
        self.assertIn(f"b -> {P}b: old stem 'b' still exists", joined)
        self.assertIn("'Not Kebab' is not kebab-case", joined)
        rc, _ = _run(graph.cmd_ownership, self.root, False, "template/main", True, False, True)
        self.assertEqual(rc, 1)

    def test_malformed_ledger_is_a_problem_not_a_crash(self):
        _note(self.root, f"pages/{P}a.md", "A")
        p = self.root / graph.MIGRATIONS
        p.parent.mkdir(parents=True)
        p.write_text("broken row\n", encoding="utf-8")
        problems = graph.template_convention(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("expected date<TAB>old-stem<TAB>new-stem", problems[0])


if __name__ == "__main__":
    unittest.main()
