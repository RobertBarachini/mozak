#!/usr/bin/env python3
"""Stdlib unit tests for tools/ — no network, no third-party imports.

Runs on a bare clone with nothing installed, which is the point: it is the
executable proof of the zero-install core (AGENTS `tools/` row). Network tests are
deliberately absent — they would be flaky and would hammer third parties from CI,
violating the politeness rule the fetch layer exists to encode. Remote drift is
caught at run time by loud failure instead.

  python3 -m unittest discover -s tools/tests
"""

import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RECIPES = ROOT / "tools" / "recipes"
HEADER = ("recipe", "input", "output", "needs", "usage")


def load(path: Path):
    """Recipe filenames are hyphenated, so import them by location."""
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def recipe_files():
    return sorted(p for p in RECIPES.glob("*.py") if not p.name.startswith("_"))


# ------------------------------------------------------------ contract conformance

class ContractHeader(unittest.TestCase):
    """Derived by glob, so it can never rot as recipes are added."""

    def test_recipes_exist(self):
        self.assertTrue(recipe_files(), "no recipes found — did the glob break?")

    def test_five_contract_lines_contiguous_and_ordered(self):
        for p in recipe_files():
            with self.subTest(recipe=p.name):
                lines = p.read_text(encoding="utf-8").splitlines()
                starts = [i for i, l in enumerate(lines) if l.startswith("# recipe:")]
                self.assertEqual(len(starts), 1, "exactly one '# recipe:' line")
                i = starts[0]
                self.assertTrue(lines[i - 1].startswith("#!"), "header follows the shebang")
                # The catalog is `grep -rA4`, so the five fields must fit that window,
                # allowing continuation lines that are not new fields.
                fields, j = [], i
                while j < len(lines) and lines[j].startswith("#"):
                    m = re.match(r"# (\w+):", lines[j])
                    if m and m.group(1) in HEADER:
                        fields.append(m.group(1))
                    j += 1
                self.assertEqual(fields, list(HEADER),
                                 "the five contract fields, in canonical order")
                # The catalog is literally `grep -rA4`, so all five fields must land
                # inside that window — a wrapped field pushes `# usage:` out of it.
                window = lines[i:i + 5]
                self.assertTrue(any(l.startswith("# usage:") for l in window),
                                f"'# usage:' fell outside the -A4 window: {window}")

    def test_pep723_block_is_after_the_header_and_parses(self):
        for p in recipe_files():
            with self.subTest(recipe=p.name):
                text = p.read_text(encoding="utf-8")
                has_block = "# /// script" in text
                shebang = text.splitlines()[0]
                self.assertEqual(has_block, "uv run" in shebang,
                                 "uv shebang iff a PEP 723 block is present")
                if has_block:
                    self.assertGreater(text.index("# /// script"), text.index("# usage:"),
                                       "the block must sit outside the -A4 grep window")
                    body = text.split("# /// script", 1)[1].split("# ///", 1)[0]
                    toml = "\n".join(l.removeprefix("# ").removeprefix("#")
                                     for l in body.splitlines())
                    try:
                        import tomllib
                    except ModuleNotFoundError:      # pragma: no cover
                        self.skipTest("tomllib needs 3.11+")
                    data = tomllib.loads(toml)
                    self.assertIn("dependencies", data)

    def test_help_exits_zero_under_bare_python(self):
        for p in recipe_files():
            if "# /// script" in p.read_text(encoding="utf-8"):
                continue                              # needs uv; covered statically above
            with self.subTest(recipe=p.name):
                r = subprocess.run([sys.executable, str(p), "--help"],
                                   capture_output=True, text=True, timeout=60)
                self.assertEqual(r.returncode, 0, r.stderr[-400:])

    def test_no_recipe_writes_into_the_graph(self):
        """The structural anti-hoarding gate — see tools/recipes/README.md."""
        graph = re.compile(r'["\'](?:pages|sources|journals|archive)/')
        for p in recipe_files():
            with self.subTest(recipe=p.name):
                for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                    if line.lstrip().startswith("#") or '"""' in line:
                        continue
                    self.assertIsNone(graph.search(line),
                                      f"{p.name}:{n} references a graph directory")


# ------------------------------------------------------------ robots (RFC 9309)

class Robots(unittest.TestCase):
    def setUp(self):
        self.wf = load(RECIPES / "web-fetch.py")

    def test_longest_match_wins_not_first_match(self):
        """The precedence rule urllib.robotparser gets wrong."""
        p = self.wf.parse_robots("User-agent: *\nDisallow: /a/\nAllow: /a/b/\n", "x")
        self.assertFalse(self.wf.robots_allows(p, "/a/c"))
        self.assertTrue(self.wf.robots_allows(p, "/a/b/page"))

    def test_allow_wins_ties(self):
        p = self.wf.parse_robots("User-agent: *\nDisallow: /x\nAllow: /x\n", "x")
        self.assertTrue(self.wf.robots_allows(p, "/x"))

    def test_wildcard_and_anchor(self):
        p = self.wf.parse_robots("User-agent: *\nDisallow: /*.pdf$\n", "x")
        self.assertFalse(self.wf.robots_allows(p, "/docs/a.pdf"))
        self.assertTrue(self.wf.robots_allows(p, "/docs/a.pdf.html"))

    def test_empty_disallow_means_allow_all(self):
        p = self.wf.parse_robots("User-agent: *\nDisallow:\n", "x")
        self.assertTrue(self.wf.robots_allows(p, "/anything"))

    def test_specific_agent_group_beats_star(self):
        txt = "User-agent: *\nDisallow: /\n\nUser-agent: mozak-research\nAllow: /\n"
        p = self.wf.parse_robots(txt, "mozak-research/1.0 (personal research)")
        self.assertEqual(p["matched_agent"], "specific")
        self.assertTrue(self.wf.robots_allows(p, "/x"))

    def test_consent_signals_are_file_level(self):
        txt = ("Sitemap: https://e.com/s1.xml\n"
               "Content-signal: search=no, ai-train=no\n"
               "License: https://e.com/license.xml\n"
               "User-agent: *\nCrawl-delay: 7\nDisallow: /p\n"
               "Sitemap: https://e.com/s2.xml\n")
        p = self.wf.parse_robots(txt, "x")
        self.assertEqual(p["sitemaps"], ["https://e.com/s1.xml", "https://e.com/s2.xml"])
        self.assertEqual(p["content_signal"], "search=no, ai-train=no")
        self.assertEqual(p["license"], "https://e.com/license.xml")
        self.assertEqual(p["crawl_delay"], 7.0)

    def test_comments_stripped(self):
        p = self.wf.parse_robots("User-agent: *  # all\nDisallow: /q  # nope\n", "x")
        self.assertFalse(self.wf.robots_allows(p, "/q"))


# ------------------------------------------------------------ extraction + classification

class Extract(unittest.TestCase):
    def setUp(self):
        self.wf = load(RECIPES / "web-fetch.py")

    def test_drops_chrome_keeps_prose(self):
        prose = ("This is a reasonably long paragraph of ordinary prose that has the "
                 "kind of stopword density you would expect from real writing, and it "
                 "should therefore survive the block classifier without any trouble. ")
        page = (f"<html><head><title>T</title></head><body>"
                f"<nav><a href=/1>One</a><a href=/2>Two</a></nav>"
                f"<script>var x=1;</script><h1>Heading</h1><p>{prose}</p>"
                f"<footer><a href=/p>Privacy</a></footer></body></html>")
        e = self.wf.extract(page)
        self.assertEqual(e["title"], "T")
        self.assertIn("# Heading", e["markdown"])
        self.assertIn("ordinary prose", e["markdown"])
        self.assertNotIn("Privacy", e["markdown"])
        self.assertNotIn("var x", e["markdown"])

    def test_link_dense_block_is_dropped(self):
        links = "".join(f'<a href=/{i}>Link number {i} here</a> ' for i in range(40))
        e = self.wf.extract(f"<html><body><div>{links}</div></body></html>")
        self.assertEqual(e["markdown"], "")

    def test_jsonld_is_captured(self):
        page = ('<html><body><script type="application/ld+json">'
                '{"@type":"NewsArticle","headline":"H"}</script></body></html>')
        self.assertEqual(self.wf.extract(page)["jsonld"], [{"@type": "NewsArticle", "headline": "H"}])

    def test_malformed_html_does_not_raise(self):
        self.wf.extract("<html><body><p>unclosed <div><span>x</body>")


class Classify(unittest.TestCase):
    def setUp(self):
        self.wf = load(RECIPES / "web-fetch.py")

    def _e(self, chars=0, md=""):
        return {"chars": chars, "markdown": md, "kept_ratio": 0.0}

    def test_interstitial_detected(self):
        rec = {"http_status": 200, "content_length": 900, "wire_length": 900,
               "text": "<title>Just a moment...</title>"}
        self.assertEqual(self.wf.classify(rec, self._e(20))[0], "interstitial")

    def test_js_shell_detected(self):
        rec = {"http_status": 200, "content_length": 90_000, "wire_length": 20_000, "text": "x"}
        self.assertEqual(self.wf.classify(rec, self._e(120))[0], "js-shell")

    def test_gzipped_page_is_not_flagged_truncated(self):
        """Content-Length is the wire length; comparing it to the decoded size
        would flag every compressed page."""
        rec = {"http_status": 200, "content_length": 1_085_539, "wire_length": 243_442,
               "declared_length": 243_442, "text": "y"}
        self.assertEqual(self.wf.classify(rec, self._e(9000))[0], "ok")

    def test_real_truncation_still_caught(self):
        rec = {"http_status": 200, "content_length": 5000, "wire_length": 5000,
               "declared_length": 900_000, "text": "y"}
        self.assertEqual(self.wf.classify(rec, self._e(4000))[0], "truncated")

    def test_zero_length_200_is_empty(self):
        rec = {"http_status": 200, "content_length": 0, "wire_length": 0, "text": ""}
        self.assertEqual(self.wf.classify(rec, self._e(0))[0], "empty")

    def test_403_is_an_answer(self):
        rec = {"http_status": 403, "content_length": 500, "wire_length": 500, "text": "no"}
        self.assertEqual(self.wf.classify(rec, self._e(10))[0], "blocked")

    def test_401_is_an_answer_that_names_rung_t5(self):
        rec = {"http_status": 401, "content_length": 500, "wire_length": 500, "text": "no"}
        verdict, reason = self.wf.classify(rec, self._e(10))
        self.assertEqual(verdict, "blocked")
        self.assertIn("T5", reason)

    def test_unexpected_status_reads_as_a_sentence(self):
        rec = {"http_status": 418, "content_length": 50, "wire_length": 50, "text": "teapot"}
        verdict, reason = self.wf.classify(rec, self._e(5))
        self.assertEqual(verdict, "error")
        self.assertEqual(reason, "unexpected HTTP 418")


# ------------------------------------------------------------ policy

class Policy(unittest.TestCase):
    def setUp(self):
        self.p = load(RECIPES / "policy.py")

    def _root(self, tmp, body=None):
        t = Path(tmp)
        if body is not None:
            (t / ".personal-shared").mkdir(parents=True, exist_ok=True)
            (t / ".personal-shared" / "acquisition-policy.toml").write_text(body, encoding="utf-8")
        return t

    def test_defaults_are_cautious_and_anonymous(self):
        cfg, prov = self.p.load(Path("/nonexistent-root"))
        self.assertFalse(cfg["advanced_acquisition"])
        self.assertEqual(cfg["identity"]["user_agent"], "browser")
        self.assertEqual(cfg["identity"]["contact"], "")
        self.assertEqual(cfg["consent"]["acknowledged"], "")
        self.assertIn("defaults", prov)

    def test_skeleton_and_defaults_cannot_drift_apart(self):
        import tomllib
        skel = tomllib.loads(self.p.TEMPLATE)
        flat = lambda d: {k if not isinstance(v, dict) else f"{k}.{k2}"
                          for k, v in d.items() for k2 in (v if isinstance(v, dict) else [None])}
        self.assertEqual(flat(skel), flat(self.p.DEFAULTS))
        self.assertEqual(skel["consent"]["acknowledged"], "", "the agent never pre-consents")
        self.assertEqual(skel["identity"]["contact"], "", "the agent never prefills contact")

    def test_user_agent_defaults_to_a_common_browser(self):
        """Anonymity: the UA is access-neutral (blocks are TLS-layer), so it is chosen
        to blend in. A distinctive tool string is a cross-site tracking beacon."""
        cfg, _ = self.p.load(Path("/nonexistent-root"))
        ua = self.p.user_agent(cfg)
        self.assertIn("Mozilla/5.0", ua)
        self.assertNotIn("mozak", ua)

    def test_user_agent_modes(self):
        cfg, _ = self.p.load(Path("/nonexistent-root"))
        cfg["identity"]["user_agent"] = "declared"
        self.assertIn("mozak-research", self.p.user_agent(cfg))
        cfg["identity"]["user_agent"] = "MyTool/2.0 (required-format)"
        self.assertEqual(self.p.user_agent(cfg), "MyTool/2.0 (required-format)")

    def test_contact_never_enters_the_user_agent_in_any_mode(self):
        cfg, _ = self.p.load(Path("/nonexistent-root"))
        cfg["identity"]["contact"] = "secret@example.org"
        for mode in ("browser", "declared", "Literal/1.0"):
            cfg["identity"]["user_agent"] = mode
            self.assertNotIn("secret@example.org", self.p.user_agent(cfg), mode)

    def test_contact_never_enters_the_provenance_string(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = self._root(d, '[identity]\ncontact = "secret@example.org"\n')
            _, prov = self.p.load(t)
            self.assertNotIn("secret@example.org", prov)
            self.assertIn("identity.contact=<set>", prov)

    def test_gate_holds_until_a_date_is_written(self):
        cfg, _ = self.p.load(Path("/nonexistent-root"))
        self.assertIsNotNone(self.p.gate(cfg), "unacknowledged must be refused")
        cfg["consent"]["acknowledged"] = "2026-09-14"
        self.assertIsNone(self.p.gate(cfg))

    def test_malformed_consent_fails_loudly(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = self._root(d, '[consent]\nacknowledged = "yes"\n')
            with self.assertRaises(SystemExit):
                self.p.load(t)

    def test_check_creates_the_skeleton_then_defers_then_passes(self):
        """The session-start gate, end to end, under bare python3."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            run = lambda: subprocess.run([sys.executable, str(RECIPES / "policy.py"),
                                          "--root", str(t), "check"],
                                         capture_output=True, text=True, timeout=60)
            r = run()
            self.assertEqual(r.returncode, 2, r.stderr)
            f = t / ".personal-shared" / "acquisition-policy.toml"
            self.assertTrue(f.is_file(), "skeleton must be created")
            self.assertIn("created", r.stderr)
            self.assertEqual(f.read_text(encoding="utf-8"), self.p.TEMPLATE)
            r = run()
            self.assertEqual(r.returncode, 2, "still deferred until consent is written")
            self.assertIn("deferred", r.stderr)
            f.write_text(f.read_text(encoding="utf-8").replace(
                'acknowledged = ""', 'acknowledged = "2026-09-14"'), encoding="utf-8")
            r = run()
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("consent 2026-09-14", r.stdout)

    def test_one_toggle_sets_the_rung_ceiling(self):
        cfg, _ = self.p.load(Path("/nonexistent-root"))
        self.assertEqual(self.p.rung_ceiling(cfg), "T2")
        self.assertFalse(self.p.rung_allowed(cfg, "T3"))
        cfg["advanced_acquisition"] = True
        self.assertEqual(self.p.rung_ceiling(cfg), "T6")

    def test_override_is_reported_precisely(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = self._root(d, "advanced_acquisition = true\n")
            cfg, prov = self.p.load(t)
            self.assertTrue(cfg["advanced_acquisition"])
            self.assertIn("advanced_acquisition=True", prov)
            self.assertNotIn("budget", prov)

    def test_restating_a_default_is_not_an_override(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = self._root(d, 'advanced_acquisition = false\n[consent]\nacknowledged = "2026-09-14"\n')
            _, prov = self.p.load(t)
            self.assertIn("no deviations", prov, "consent is consent, not a deviation")

    def test_bad_input_fails_loudly(self):
        import tempfile
        cases = {"unknown top-level key": "robots = true\n",
                 "unknown section": "[nope]\nx = 1\n",
                 "unknown key in section": "[budget]\nbogus = 1\n",
                 "wrong type for the toggle": 'advanced_acquisition = "yes"\n',
                 "table where a scalar goes": "[advanced_acquisition]\nx = 1\n",
                 "scalar where a table goes": "budget = 5\n",
                 "out-of-range budget": "[budget]\nmax_fetches_per_run = 0\n",
                 "invalid TOML": "advanced_acquisition = \n"}
        for name, body in cases.items():
            with tempfile.TemporaryDirectory() as d, self.subTest(case=name):
                t = self._root(d, body)
                with self.assertRaises(SystemExit):
                    self.p.load(t)


class Questions(unittest.TestCase):
    """The consent gate asks; it does not relay. The questions live once, beside DEFAULTS."""

    def setUp(self):
        self.p = load(RECIPES / "policy.py")

    def test_every_question_resolves_to_a_real_key_and_consent_is_last(self):
        cfg, _ = self.p.load(Path("/nonexistent-root"))
        keys = [q["key"] for q in self.p.QUESTIONS]
        for k in keys:
            self.p._get(cfg, k)                              # KeyError would fail the test
        self.assertEqual(keys[-1], "consent.acknowledged", "consent is asked after everything else")
        self.assertEqual(len(set(keys)), len(keys))

    def test_every_option_is_explained_and_recordable(self):
        cfg, _ = self.p.load(Path("/nonexistent-root"))
        for q in self.p.questions(cfg):
            self.assertTrue(q["question"].endswith("?"))
            self.assertGreaterEqual(len(q["options"]), 2)
            for o in q["options"]:
                self.assertTrue(o["label"] and o["explain"], q["key"])
                if o["value"] is not None:
                    self.assertIn("policy.py set " + q["key"] + "=", o["apply"])
            self.assertEqual(sum(o["current"] for o in q["options"]), 1 if q["key"] != "consent.acknowledged" else 0,
                             f"{q['key']}: exactly one option marks the current value (none for unset consent)")

    def test_check_json_and_text_while_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            r = subprocess.run([sys.executable, str(RECIPES / "policy.py"), "--root", str(t), "check", "--json"],
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 2)
            data = json.loads(r.stdout)
            self.assertEqual(data["gate"], "closed"); self.assertTrue(data["created"])
            self.assertEqual([q["key"] for q in data["questions"]],
                             ["advanced_acquisition", "identity.user_agent", "identity.contact", "consent.acknowledged"])
            r = subprocess.run([sys.executable, str(RECIPES / "policy.py"), "--root", str(t), "check"],
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 2)
            self.assertIn("Decisions that need you", r.stdout)
            self.assertIn("policy.py set consent.acknowledged=today", r.stdout)
            self.assertIn("What it is for:", r.stdout, "the contact question explains its purpose")
            contact_q = next(q for q in data["questions"] if q["key"] == "identity.contact")
            self.assertIn("polite pool", contact_q["context"])
            self.assertIn("proton", contact_q["example"])
            self.assertIn("never answers them itself", r.stderr)


class SetCommand(unittest.TestCase):
    def setUp(self):
        self.p = load(RECIPES / "policy.py")

    def test_set_records_answers_and_preserves_comments(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            changed = self.p.set_values(t, ["advanced_acquisition=true", "identity.user_agent=declared",
                                            "identity.contact=x@y.z"])
            self.assertEqual(len(changed), 3)
            f = t / ".personal-shared" / "acquisition-policy.toml"
            self.assertEqual(f.read_text().count("\n#"), self.p.TEMPLATE.count("\n#"), "comments preserved")
            cfg, prov = self.p.load(t)
            self.assertTrue(cfg["advanced_acquisition"])
            self.assertEqual(cfg["identity"]["user_agent"], "declared")
            self.assertEqual(cfg["identity"]["contact"], "x@y.z")
            self.assertIn("identity.contact=<set>", prov, "the address itself never enters provenance")
            self.assertIsNotNone(self.p.gate(cfg), "still closed: consent not yet recorded")

    def test_consent_today_opens_the_gate(self):
        import tempfile
        from datetime import date
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            self.p.set_values(t, ["consent.acknowledged=today"])
            cfg, _ = self.p.load(t)
            self.assertEqual(cfg["consent"]["acknowledged"], date.today().isoformat())
            self.assertIsNone(self.p.gate(cfg))

    def test_bad_input_is_rejected_and_the_file_is_untouched(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            self.p.set_values(t, ["advanced_acquisition=false"])
            f = t / ".personal-shared" / "acquisition-policy.toml"
            before = f.read_text()
            for bad in ("bogus=1", "advanced_acquisition=maybe", "consent.acknowledged=yesterday",
                        "budget.max_fetches_per_run=0", "identity=5", "noequals"):
                with self.subTest(bad=bad), self.assertRaises(SystemExit):
                    self.p.set_values(t, [bad])
                self.assertEqual(f.read_text(), before, bad)

    def test_set_never_pre_answers(self):
        """`set` records exactly what it is given; creating the skeleton records nothing."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            self.p.set_values(t, ["budget.min_delay_seconds=2"])
            cfg, _ = self.p.load(t)
            self.assertEqual(cfg["consent"]["acknowledged"], "")
            self.assertEqual(cfg["identity"]["contact"], "")
            self.assertEqual(cfg["budget"]["min_delay_seconds"], 2.0)


class ReachableContact(unittest.TestCase):
    """A contact exists so a source can reach you; placeholders are refused, real aliases pass."""

    def setUp(self):
        self.p = load(RECIPES / "policy.py")

    def test_empty_is_a_valid_answer(self):
        self.assertEqual(self.p.looks_reachable(""), (True, ""))

    def test_real_addresses_pass_including_dedicated_aliases(self):
        for a in ("research.alias@fastmail.com", "r+mozak@example-lab.org", "me@sub.university.edu", "Nobody.Real@company.io"):
            with self.subTest(a=a):
                self.assertTrue(self.p.looks_reachable(a)[0], a)

    def test_placeholders_and_noreply_are_refused(self):
        for a in ("noreply@gmail.com", "no-reply+tag@x.org", "donotreply@x.org", "nobody@x.org",
                  "test@example.com", "a@example.org", "a@b.invalid", "a@host.test", "a@localhost",
                  "not-an-address", "two@@x.org", "a b@x.org", "a@nodot"):
            with self.subTest(a=a):
                ok, why = self.p.looks_reachable(a)
                self.assertFalse(ok, a); self.assertTrue(why)

    def test_set_refuses_a_fake_and_leaves_the_file_untouched(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            self.p.set_values(t, ["advanced_acquisition=false"])
            f = t / ".personal-shared" / "acquisition-policy.toml"; before = f.read_text()
            with self.assertRaises(SystemExit):
                self.p.set_values(t, ["identity.contact=noreply@example.com"])
            self.assertEqual(f.read_text(), before)
            self.p.set_values(t, ["identity.contact=alias@fastmail.com"])
            self.assertEqual(self.p.load(t)[0]["identity"]["contact"], "alias@fastmail.com")

    def test_check_announces_the_absolute_path(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            r = subprocess.run([sys.executable, str(RECIPES / "policy.py"), "--root", str(t), "check", "--json"],
                               capture_output=True, text=True, timeout=60)
            data = json.loads(r.stdout)
            self.assertTrue(Path(data["path"]).is_absolute())
            self.assertTrue(data["path"].endswith("acquisition-policy.toml"))
            r = subprocess.run([sys.executable, str(RECIPES / "policy.py"), "--root", str(t), "check"],
                               capture_output=True, text=True, timeout=60)
            self.assertIn(str(t.resolve()), r.stdout, "closed state names the file's absolute location")
            self.p.set_values(t, ["consent.acknowledged=today"])
            r = subprocess.run([sys.executable, str(RECIPES / "policy.py"), "--root", str(t), "check"],
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0)
            self.assertIn("your answers live in:", r.stdout)
            self.assertIn(str(t.resolve()), r.stdout)
            self.assertIn("gitignored", r.stdout)


class Cookies(unittest.TestCase):
    """Rung T5 in stdlib: a user-exported Netscape jar, sent only under advanced mode,
    and never logged by value."""

    JAR = ("# Netscape HTTP Cookie File\n"
           ".example.com\tTRUE\t/\tFALSE\t2000000000\tsession\tSECRETVALUE123\n"
           "example.com\tFALSE\t/\tFALSE\t2000000000\tpref\tdark\n")

    def setUp(self):
        self.p = load(RECIPES / "policy.py")

    def _root(self, tmp, policy_body, jar=True):
        t = Path(tmp)
        (t / ".personal-shared").mkdir(parents=True, exist_ok=True)
        (t / ".personal-shared" / "acquisition-policy.toml").write_text(policy_body, encoding="utf-8")
        if jar:
            (t / ".personal-shared" / "cookies.txt").write_text(self.JAR, encoding="utf-8")
        return t

    def test_absent_jar(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = self._root(d, "advanced_acquisition = true\n", jar=False)
            cfg, _ = self.p.load(t)
            self.assertEqual(self.p.cookies_path(cfg, t), (None, "no cookie jar"))

    def test_present_but_cautious_is_reported_not_sent(self):
        """A user who drops a jar without reading is told, not silently deanonymised."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = self._root(d, "advanced_acquisition = false\n")
            cfg, _ = self.p.load(t)
            path, status = self.p.cookies_path(cfg, t)
            self.assertIsNone(path)
            self.assertIn("present", status)
            self.assertIn("T5", status)
            jar, status2 = self.p.cookie_jar(cfg, t)
            self.assertIsNone(jar)

    def test_present_and_advanced_loads(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = self._root(d, "advanced_acquisition = true\n")
            cfg, _ = self.p.load(t)
            jar, status = self.p.cookie_jar(cfg, t)
            self.assertIsNotNone(jar)
            self.assertEqual(len(jar), 2)
            self.assertIn("2 cookies", status)
            self.assertIn("1 domains", status)

    def test_cookie_value_never_appears_in_any_status(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = self._root(d, "advanced_acquisition = true\n")
            cfg, prov = self.p.load(t)
            _, status = self.p.cookie_jar(cfg, t)
            for s in (status, prov):
                self.assertNotIn("SECRETVALUE123", s)
                self.assertNotIn("dark", s)

    def test_disabled_even_if_the_file_exists(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = self._root(d, 'advanced_acquisition = true\n[identity]\ncookies_file = ""\n')
            cfg, _ = self.p.load(t)
            self.assertEqual(self.p.cookies_path(cfg, t), (None, "cookies disabled"))

    def test_absolute_path_is_honoured(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as e:
            outside = Path(e) / "jar.txt"
            outside.write_text(self.JAR, encoding="utf-8")
            t = self._root(d, f'advanced_acquisition = true\n[identity]\ncookies_file = "{outside}"\n', jar=False)
            cfg, _ = self.p.load(t)
            jar, _ = self.p.cookie_jar(cfg, t)
            self.assertEqual(len(jar), 2)

    def test_garbage_jar_fails_loudly(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = self._root(d, "advanced_acquisition = true\n", jar=False)
            (t / ".personal-shared" / "cookies.txt").write_text("not a cookie jar", encoding="utf-8")
            cfg, _ = self.p.load(t)
            with self.assertRaises(SystemExit):
                self.p.cookie_jar(cfg, t)

    def test_skeleton_points_at_the_conventional_slot(self):
        import tomllib
        self.assertEqual(tomllib.loads(self.p.TEMPLATE)["identity"]["cookies_file"],
                         ".personal-shared/cookies.txt")


class Anonymity(unittest.TestCase):
    """Source-level invariants: the fetch recipe must not leak identity by construction."""

    def setUp(self):
        self.src = (RECIPES / "web-fetch.py").read_text(encoding="utf-8")

    def test_no_from_header_and_no_contact_use(self):
        self.assertNotIn('"From"', self.src)
        self.assertNotIn("['contact']", self.src)
        self.assertNotIn('["contact"]', self.src)

    def test_no_locale_revealing_language_header(self):
        m = re.search(r'"Accept-Language":\s*"([^"]+)"', self.src)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "en-US,en;q=0.9", "generic, not the author's locale")

    def test_cookie_header_is_counted_never_stored(self):
        for m in re.finditer(r'"Cookie"', self.src):
            self.assertIn("get_header", self.src[max(0, m.start() - 30):m.start()],
                          "the only use of the Cookie header is reading it to count")
        self.assertNotIn("cookie_header", self.src)

    def test_consent_gate_runs_before_any_network_action(self):
        main = self.src[self.src.index("def main()"):]
        self.assertLess(main.index("_policy.gate(cfg)"), main.index("if args.probe"),
                        "gate must precede probe/archive/fetch dispatch")


# ------------------------------------------------------------ links + worklist + T6 + T0

ACK = 'advanced_acquisition = false\n[consent]\nacknowledged = "2026-09-14"\n'


def _ack_root(tmp, body=ACK):
    t = Path(tmp)
    (t / ".personal-shared").mkdir(parents=True, exist_ok=True)
    (t / ".personal-shared" / "acquisition-policy.toml").write_text(body, encoding="utf-8")
    return t


class Links(unittest.TestCase):
    def setUp(self):
        self.wf = load(RECIPES / "web-fetch.py")

    PAGE = ('<html><body><nav><a href="/about">About</a></nav>'
            '<p>See <a href="paper.pdf">the paper</a>, <a href="https://doi.org/10.1/x">the DOI</a>, '
            '<a href="https://arxiv.org/abs/1706.03762">arXiv</a>, <a href="#top">top</a>, '
            '<a href="mailto:a@b.c">mail</a>, <a href="javascript:void(0)">js</a>, '
            '<a href="https://sub.example.com/q?x=1#frag">sub</a>, <a href="https://other.org/">ext</a>, '
            '<a href="/about">About again</a></p></body></html>')

    def test_anchors_are_collected_with_text_and_chrome_flag(self):
        e = self.wf.extract(self.PAGE)
        by = {}
        for a in e["anchors"]:
            by.setdefault(a["href"], a)             # first occurrence: the nav one
        self.assertEqual(by["/about"]["text"], "About")
        self.assertTrue(by["/about"]["chrome"], "nav anchors are flagged as chrome")
        self.assertFalse(by["paper.pdf"]["chrome"])

    def test_links_from_resolves_dedupes_and_labels(self):
        e = self.wf.extract(self.PAGE)
        links = self.wf.links_from(e, "https://www.example.com/dir/page.html")
        urls = [l["url"] for l in links]
        self.assertIn("https://www.example.com/dir/paper.pdf", urls)
        self.assertEqual(urls.count("https://www.example.com/about"), 1, "deduped")
        self.assertNotIn("https://www.example.com/dir/page.html#top", urls)
        self.assertFalse(any(u.startswith(("mailto:", "javascript:")) for u in urls))
        self.assertIn("https://sub.example.com/q?x=1", urls, "fragment dropped, query kept")
        kinds = {l["url"]: l["kind"] for l in links}
        self.assertEqual(kinds["https://www.example.com/dir/paper.pdf"], "pdf")
        self.assertEqual(kinds["https://doi.org/10.1/x"], "doi")
        self.assertEqual(kinds["https://arxiv.org/abs/1706.03762"], "arxiv")
        same = {l["url"]: l["same_site"] for l in links}
        self.assertTrue(same["https://sub.example.com/q?x=1"], "subdomain counts as same site")
        self.assertFalse(same["https://other.org/"])

    def test_explain_failure_reads_as_a_sentence(self):
        row = {"verdict": "error", "verdict_reason": "unexpected HTTP 418", "url_requested": "https://x/"}
        lines = self.wf.explain_failure(row, {})
        self.assertEqual(lines[0], "error: unexpected HTTP 418")
        self.assertTrue(any("Recorded in" in l for l in lines))


class Worklist(unittest.TestCase):
    """add/show/run-plan under bare python3; `run --yes` needs network and is not tested here."""

    def _run(self, root, *args):
        return subprocess.run([sys.executable, str(RECIPES / "web-worklist.py"), "--root", str(root), *args],
                              capture_output=True, text=True, timeout=60)

    def test_reason_is_mandatory(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = _ack_root(d)
            r = self._run(t, "add", "https://example.com/a")
            self.assertNotEqual(r.returncode, 0)
            r = self._run(t, "add", "https://example.com/a", "--why", "   ")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("reason", r.stderr.lower())

    def test_add_show_dedupe_and_plan_without_yes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = _ack_root(d)
            r = self._run(t, "add", "https://example.com/a", "--why", "cited as the primary source", "--from", "https://example.com/")
            self.assertEqual(r.returncode, 0, r.stderr)
            r = self._run(t, "add", "https://example.com/a", "--why", "again")
            self.assertIn("already listed", r.stdout)
            r = self._run(t, "add", "https://example.com/b", "--why", "table 3 has the numbers")
            self.assertEqual(r.returncode, 0)
            r = self._run(t, "show")
            self.assertIn("2 entries, 2 pending", r.stdout)
            self.assertIn("cited as the primary source", r.stdout)
            r = self._run(t, "run")
            self.assertEqual(r.returncode, 3, "no --yes ⇒ plan only")
            self.assertIn("2 targeted pull(s)", r.stdout)
            self.assertIn("--yes", r.stderr)
            r = self._run(t, "run", "--max", "1")
            self.assertIn("1 targeted pull(s) of 2 pending (cap 1)", r.stdout)

    def test_gate_holds_for_add_and_run_but_show_is_free(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = _ack_root(d, "advanced_acquisition = false\n")     # no consent
            self.assertEqual(self._run(t, "add", "https://example.com/", "--why", "x").returncode, 2)
            self.assertEqual(self._run(t, "run").returncode, 2)
            self.assertEqual(self._run(t, "show").returncode, 0)


class WorklistRun(unittest.TestCase):
    """`run --yes` with an injected perform(): statuses — including *skipped* — must be
    persisted, so a second run does not re-pull a host that already said no."""

    def test_skipped_and_failed_are_persisted_and_not_repulled(self):
        import tempfile
        wl = load(RECIPES / "web-worklist.py")
        calls = []
        def fake_perform(url, cfg, prov, root, *, use_cache=True, extra=None):
            calls.append(url)
            v = "blocked" if "reuters" in url else "ok"
            return ({"verdict": v, "rung": "T1", "blob_ref": "x", "extract_chars": 5,
                     "verdict_reason": "HTTP 401" if v == "blocked" else ""}, {}, [])
        with tempfile.TemporaryDirectory() as d:
            t = _ack_root(d)
            p = load(RECIPES / "policy.py"); cfg, prov = p.load(t)
            for u, w in (("https://example.com/", "a"), ("https://www.reuters.com/world/", "b"),
                         ("https://www.reuters.com/business/", "c")):
                wl.cmd_add(t, u, w, None)
            rc = wl.cmd_run(t, cfg, prov, yes=True, max_n=None, perform=fake_perform)
            self.assertEqual(rc, 0)
            self.assertEqual(calls, ["https://example.com/", "https://www.reuters.com/world/"],
                             "the second reuters URL must not be fetched")
            statuses = {e["url"]: e["status"] for e in wl.load_list(t)}
            self.assertEqual(statuses["https://example.com/"], "done")
            self.assertEqual(statuses["https://www.reuters.com/world/"], "failed")
            self.assertEqual(statuses["https://www.reuters.com/business/"], "skipped",
                             "skipped must be persisted, not left pending")
            calls.clear()
            rc = wl.cmd_run(t, cfg, prov, yes=True, max_n=None, perform=fake_perform)
            self.assertEqual(calls, [], "nothing pending ⇒ nothing fetched")

    def test_cap_leaves_the_rest_pending(self):
        import tempfile
        wl = load(RECIPES / "web-worklist.py")
        fake = lambda url, cfg, prov, root, *, use_cache=True, extra=None: (
            {"verdict": "ok", "rung": "T1", "blob_ref": "x", "extract_chars": 1, "verdict_reason": ""}, {}, [])
        with tempfile.TemporaryDirectory() as d:
            t = _ack_root(d)
            p = load(RECIPES / "policy.py"); cfg, prov = p.load(t)
            for i in range(3):
                wl.cmd_add(t, f"https://e{i}.example/", "why", None)
            wl.cmd_run(t, cfg, prov, yes=True, max_n=2, perform=fake)
            statuses = [e["status"] for e in wl.load_list(t)]
            self.assertEqual(statuses, ["done", "done", "pending"])


class RenderPure(unittest.TestCase):
    """web-render's pure helpers under bare python3 (playwright is imported lazily)."""

    def setUp(self):
        self.r = load(RECIPES / "web-render.py")

    def test_anonymise_ua_drops_only_the_headless_marker(self):
        ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/151.0.0.0 Safari/537.36"
        out = self.r.anonymise_ua(ua)
        self.assertNotIn("Headless", out)
        self.assertIn("Chrome/151.0.0.0", out)
        self.assertIn("X11; Linux x86_64", out, "platform untouched")
        self.assertEqual(self.r.anonymise_ua(out), out, "idempotent")

    def test_only_the_two_automation_labels_are_touched(self):
        """The line the recipe holds: drop the labels that say 'tool-driven', fabricate nothing."""
        self.assertIn("--enable-automation", self.r.DROP_DEFAULT_ARGS)
        self.assertIn("--disable-blink-features=AutomationControlled", self.r.HYGIENE)
        src = (RECIPES / "web-render.py").read_text(encoding="utf-8")
        for forbidden in ("add_init_script", "webgl", "canvas", "Runtime.enable", "plugins"):
            self.assertNotIn(forbidden.lower(), src.lower().replace("no fingerprint", "").replace("canvas,\n  webgl and plugins", ""),
                             f"{forbidden}: fingerprint injection is out of scope by design")

    def test_redact_har_strips_every_credential(self):
        import tempfile
        har = {"log": {"entries": [{"request": {"headers": [{"name": "Cookie", "value": "s=SECRET"},
                                                            {"name": "Authorization", "value": "Bearer T"},
                                                            {"name": "User-Agent", "value": "ua"}],
                                                "cookies": [{"name": "s", "value": "SECRET"}]},
                                    "response": {"headers": [{"name": "Set-Cookie", "value": "x=Y"},
                                                             {"name": "Content-Type", "value": "text/html"}],
                                                 "cookies": [{"name": "x", "value": "Y"}]}}]}}
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / "in.har", Path(d) / "out" / "o.har"
            src.write_text(json.dumps(har))
            n = self.r.redact_har(src, dst)
            self.assertEqual(n, 5, "3 headers + 2 cookie arrays")
            out = dst.read_text()
            for secret in ("SECRET", "Bearer T", "x=Y"):
                self.assertNotIn(secret, out)
            self.assertIn("text/html", out); self.assertIn('"ua"', out, "non-credential headers survive")


class HarHarvest(unittest.TestCase):
    """Rung T6: credentials in the HAR must be discarded by construction."""

    HAR = {"log": {"version": "1.2", "entries": [
        {"startedDateTime": "2026-09-14T10:00:00.000Z",
         "request": {"method": "GET", "url": "https://example.com/article",
                     "headers": [{"name": "Cookie", "value": "session=SECRETHAR"},
                                 {"name": "Authorization", "value": "Bearer SECRETTOKEN"},
                                 {"name": "User-Agent", "value": "Mozilla/5.0 UNIQUEFINGERPRINT"}],
                     "cookies": [{"name": "session", "value": "SECRETHAR"}]},
         "response": {"status": 200,
                      "headers": [{"name": "Content-Type", "value": "text/html; charset=utf-8"},
                                  {"name": "Set-Cookie", "value": "sid=SECRETSET; HttpOnly"},
                                  {"name": "ETag", "value": "W/\"abc\""}],
                      "content": {"mimeType": "text/html; charset=utf-8",
                                  "text": "<html><head><title>T</title></head><body><h1>Headline</h1><p>" + "harvested body text that is long enough to be kept by the classifier. " * 5 + "</p></body></html>"}}},
        {"startedDateTime": "2026-09-14T10:00:01.000Z",
         "request": {"method": "GET", "url": "https://example.com/logo.png", "headers": []},
         "response": {"status": 200, "headers": [], "content": {"mimeType": "image/png", "encoding": "base64", "text": "iVBORw0KGgo="}}},
        {"startedDateTime": "2026-09-14T10:00:02.000Z",
         "request": {"method": "GET", "url": "https://example.com/forbidden", "headers": []},
         "response": {"status": 403, "headers": [], "content": {"mimeType": "text/html", "text": "<html>no</html>"}}},
    ]}}

    def _run(self, root, har, *args):
        return subprocess.run([sys.executable, str(RECIPES / "web-har-harvest.py"), str(har), "--root", str(root), *args],
                              capture_output=True, text=True, timeout=60)

    def test_documents_harvested_credentials_gone_non_docs_skipped(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = _ack_root(d)
            har = t / "raw" / "session.har"; har.parent.mkdir()
            har.write_text(json.dumps(self.HAR), encoding="utf-8")
            r = self._run(t, har)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("harvested 1 of 3", r.stdout)
            self.assertIn("delete it", r.stderr)
            store = t / "_generated" / "fetch"
            rows = [json.loads(l) for l in (store / "fetch.jsonl").read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["rung"], "T6")
            self.assertEqual(rows[0]["tool"], "web-har-harvest")
            self.assertEqual(rows[0]["fetched_at"], "2026-09-14T10:00:00.000Z", "when the human fetched it")
            self.assertEqual(rows[0]["headers_kept"].get("etag"), 'W/"abc"')
            everything = "".join(p.read_text(errors="ignore") for p in store.rglob("*") if p.is_file() and not p.suffix == ".gz")
            for secret in ("SECRETHAR", "SECRETTOKEN", "SECRETSET", "UNIQUEFINGERPRINT"):
                self.assertNotIn(secret, everything, secret)
            extract = (store / rows[0]["extract_ref"]).read_text()
            self.assertIn("harvested body text", extract)
            self.assertFalse(any(p.suffix == ".har" for p in store.rglob("*")), "the HAR is never copied")

    def test_all_and_glob(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = _ack_root(d)
            har = t / "s.har"; har.write_text(json.dumps(self.HAR), encoding="utf-8")
            r = self._run(t, har, "--all")
            self.assertIn("harvested 2 of 3", r.stdout, "png included, 403 still skipped")
            r = self._run(t, har, "--url-glob", "*/nothing*")
            self.assertIn("harvested 0 of 3", r.stdout)

    def test_gate_holds(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = _ack_root(d, "advanced_acquisition = false\n")
            har = t / "s.har"; har.write_text(json.dumps(self.HAR), encoding="utf-8")
            self.assertEqual(self._run(t, har).returncode, 2)


class Scholar(unittest.TestCase):
    """Rung T0 parsers, offline."""

    def setUp(self):
        self.s = load(RECIPES / "scholar-lookup.py")

    def test_classify_query(self):
        c = self.s.classify_query
        self.assertEqual(c("https://doi.org/10.1038/nature14539"), ("doi", "10.1038/nature14539"))
        self.assertEqual(c("10.1038/nature14539."), ("doi", "10.1038/nature14539"))
        self.assertEqual(c("arxiv:1706.03762"), ("arxiv", "1706.03762"))
        self.assertEqual(c("1706.03762v5"), ("arxiv", "1706.03762v5"))
        self.assertEqual(c('"Attention is all you need"'), ("title", "Attention is all you need"))

    def test_parsers(self):
        cr = self.s.parse_crossref({"message": {"title": ["Deep learning"], "DOI": "10.1038/nature14539",
                                                "author": [{"given": "Yann", "family": "LeCun"}],
                                                "issued": {"date-parts": [[2015, 5, 27]]},
                                                "container-title": ["Nature"], "URL": "https://doi.org/10.1038/nature14539"}})
        self.assertEqual(cr["authors"], ["Yann LeCun"]); self.assertEqual(cr["published"], "2015-05-27")
        oa = self.s.parse_openalex({"title": "Deep learning", "open_access": {"oa_status": "green", "oa_url": "https://h/x.pdf"},
                                    "best_oa_location": {"pdf_url": "https://h/x.pdf", "license": "cc-by"},
                                    "authorships": [{"author": {"display_name": "Yann LeCun"}}],
                                    "cited_by_count": 42, "doi": "https://doi.org/10.1038/nature14539"})
        self.assertEqual(oa["doi"], "10.1038/nature14539"); self.assertEqual(oa["cited_by"], 42)
        up = self.s.parse_unpaywall({"oa_status": "gold", "is_oa": True,
                                     "best_oa_location": {"url_for_pdf": "https://u/p.pdf", "license": "cc-by-nc"}})
        self.assertEqual(up["pdf_url"], "https://u/p.pdf")
        atom = ('<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom"><entry>'
                '<id>http://arxiv.org/abs/1706.03762v7</id><published>2017-06-12T17:57:34Z</published>'
                '<title>Attention Is All\n  You Need</title><author><name>Ashish Vaswani</name></author>'
                '<link title="pdf" href="http://arxiv.org/pdf/1706.03762v7" rel="related"/>'
                '<arxiv:doi>10.5555/x</arxiv:doi></entry></feed>')
        ax = self.s.parse_arxiv(atom)
        self.assertEqual(ax["title"], "Attention Is All You Need"); self.assertEqual(ax["arxiv_id"], "1706.03762v7")
        self.assertEqual(ax["pdf_url"], "http://arxiv.org/pdf/1706.03762v7"); self.assertEqual(ax["doi"], "10.5555/x")

    def test_merge_prefers_unpaywall_then_arxiv_then_openalex_and_render_has_frontmatter(self):
        res = {"doi": "10.1/x", "queried": ["crossref (200; polite pool: no)"], "skipped": ["unpaywall — requires an e-mail"],
               "crossref": {"title": "T", "authors": ["A B"], "published": "2020-01-01", "venue": "V", "source": "crossref"},
               "openalex": {"pdf_url": "https://oa/p.pdf", "oa_url": "https://oa/l", "oa_status": "green", "source": "openalex", "cited_by": 3}}
        m = self.s.merge(res)
        self.assertEqual(m["oa_url"], "https://oa/p.pdf")
        out = self.s.render(m, res)
        for needle in ("type: source", "medium: paper", "url: https://doi.org/10.1/x", "capture-method: T0 scholar-lookup",
                       "## Open access", "https://oa/p.pdf", "Skipped: unpaywall"):
            self.assertIn(needle, out)
        res["unpaywall"] = {"pdf_url": "https://up/p.pdf", "oa_status": "gold", "source": "unpaywall"}
        self.assertEqual(self.s.merge(res)["oa_url"], "https://up/p.pdf")


# ------------------------------------------------------------ yt-transcript

class Transcript(unittest.TestCase):
    def setUp(self):
        self.yt = load(RECIPES / "yt-transcript.py")

    def test_json3_needs_no_dedup(self):
        doc = json.dumps({"events": [
            {"tStartMs": 0, "dDurationMs": 10},
            {"tStartMs": 1000, "segs": [{"utf8": "hello "}, {"utf8": "world"}]},
            {"tStartMs": 2000, "segs": [{"utf8": "\n"}]},
            {"tStartMs": 65000, "segs": [{"utf8": "second"}]}]})
        self.assertEqual(self.yt.clean_json3(doc), "hello world\nsecond")
        self.assertTrue(self.yt.clean_json3(doc, True).startswith("[00:01] "))

    def test_vtt_rolling_duplicates_collapse(self):
        vtt = ("WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n<00:00:01.3><c>rolling</c> line\n\n"
               "00:00:03.000 --> 00:00:05.000\nrolling line\n\n"
               "00:00:05.000 --> 00:00:07.000\nnext bit\n")
        self.assertEqual(self.yt.clean_vtt(vtt), "rolling line\nnext bit")


# ------------------------------------------------------------ graph.py ownership parser

class OwnershipParser(unittest.TestCase):
    """The repo's most fragile code and, until now, its least covered: it parses the
    SYNC.md Ownership table at run time, so a reworded table silently changes the
    guard's behaviour."""

    def setUp(self):
        self.g = load(ROOT / "tools" / "graph.py")

    def test_parses_the_real_sync_table(self):
        owned, excludes, shared = self.g.parse_ownership(ROOT)
        self.assertIn("tools", owned)          # globs are stored slash-less
        self.assertIn("templates", owned)
        self.assertIn("tools/recipes/local", excludes,
                      "the instance-owned escape hatch must stay excluded")
        self.assertIn("AGENTS.md", shared)
        self.assertIn("SYNC.md", shared)

    def test_new_tool_paths_are_covered_without_a_table_amendment(self):
        """tools/ already globs tools/tests/ and tools/recipes/* — which is why this
        phase needed no Ownership-table edit."""
        owned, excludes, _ = self.g.parse_ownership(ROOT)
        self.assertIn("tools", owned)
        self.assertNotIn("tools/tests", excludes)
        self.assertEqual(excludes, ["tools/recipes/local", "pages/start-here.md"],
                         "the only carve-outs from tools/ and pages/")

    def test_reworded_table_fails_loudly_rather_than_silently_empty(self):
        """A table the parser cannot read must not read as 'nothing is owned'."""
        owned, _, shared = self.g.parse_ownership(ROOT)
        self.assertTrue(owned and shared,
                        "empty path sets mean the SYNC table format drifted")


if __name__ == "__main__":
    unittest.main(verbosity=2)
