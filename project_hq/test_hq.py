"""Safety boundaries and read-only UI integration; no production DB access."""
import builtins
from contextlib import ExitStack
import hashlib
import io
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HQ = Path(__file__).resolve().parent
sys.path.insert(0, str(HQ))
from readers import (ROOT, discover, read_document, sections, latest_section,
                     display_markdown, context_text, MAX_BYTES)


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "PROJECT_STATUS.md").write_text(
            "# Status\n\n## Old — 2026-01-01\nOld\n\n## New — 2026-09-26\n- [x] Done\n", encoding="utf-8")
        (self.root / ".env").write_text("SECRET=not-for-hq", encoding="utf-8")
        (self.root / "data").mkdir()
        (self.root / "data" / "private.md").write_text("excluded", encoding="utf-8")
        (self.root / "work").mkdir()
        (self.root / "work" / "REPORT.md").write_text("# Research", encoding="utf-8")
        (self.root / "work" / ".private").mkdir()
        (self.root / "work" / ".private" / "hidden.md").write_text("hidden", encoding="utf-8")

    def test_catalog_and_arbitrary_paths(self):
        catalog = discover(self.root)
        self.assertEqual(set(catalog), {"PROJECT_STATUS.md", "work/REPORT.md"})
        for name in (".env", "data/private.md", "../PROJECT_STATUS.md", str(self.root / ".env"), "%2e%2e/.env"):
            with self.assertRaises(ValueError):
                read_document(name, catalog, self.root)
        self.assertIn("Status", read_document("PROJECT_STATUS.md", catalog, self.root).text)

    def test_oversized_and_missing_sources(self):
        path = self.root / "LARGE.md"
        path.write_bytes(b"x" * (MAX_BYTES + 1))
        self.assertNotIn("LARGE.md", discover(self.root))
        catalog = discover(self.root)
        (self.root / "PROJECT_STATUS.md").unlink()
        with self.assertRaises(OSError):
            read_document("PROJECT_STATUS.md", catalog, self.root)

    def test_linked_paths_are_rejected(self):
        try:
            (self.root / "linked.md").symlink_to(self.root / "PROJECT_STATUS.md")
        except OSError:
            self.skipTest("Creating symlinks requires Windows developer mode/privileges")
        self.assertNotIn("linked.md", discover(self.root))
        with self.assertRaises(ValueError):
            read_document("linked.md", {"linked.md": self.root / "linked.md"}, self.root)

    def test_sections_ignore_code_and_sort_by_date(self):
        text = "# Test\n\n## New — 2026-09-26\nnew\n```md\n## fake — 2099-01-01\n```\n## Old — 2026-01-01\nold\n"
        self.assertEqual(len(sections(text)), 3)
        self.assertEqual(latest_section(text)[0], "New — 2026-09-26")

    def test_link_rejection_without_symlink_privileges(self):
        catalog = discover(self.root)
        original = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda path: path.name == "PROJECT_STATUS.md" or original(path)):
            self.assertNotIn("PROJECT_STATUS.md", discover(self.root))
            with self.assertRaises(ValueError):
                read_document("PROJECT_STATUS.md", catalog, self.root)
        original_junction = Path.is_junction
        with patch.object(Path, "is_junction", lambda path: path.name == "work" or original_junction(path)):
            self.assertNotIn("work/REPORT.md", discover(self.root))
            with self.assertRaises(ValueError):
                read_document("work/REPORT.md", catalog, self.root)

    def test_links_and_images_do_not_expose_files(self):
        catalog = discover(self.root)
        text = "[status](../PROJECT_STATUS.md)\n[secret](../.env)\n![external](https://example.org/a.png)\n[x](javascript:alert)\n```md\n![code](literal)\n```\n"
        shown = display_markdown(text, "work/REPORT.md", catalog)
        self.assertIn("[status](?doc=PROJECT_STATUS.md)", shown)
        self.assertNotIn("[secret](", shown)
        self.assertNotIn("[x](", shown)
        self.assertNotIn("![external]", shown)
        self.assertIn("![code](literal)", shown)

    def test_context_preserves_sources_without_writes(self):
        catalog = discover(self.root)
        doc = read_document("PROJECT_STATUS.md", catalog, self.root)
        context = context_text([doc])
        self.assertIn(doc.text.rstrip(), context)
        self.assertIn("Source: PROJECT_STATUS.md", context)
        self.assertEqual(doc.text, read_document(doc.id, catalog, self.root).text)


class UiSafetyTests(unittest.TestCase):
    def test_all_pages_without_project_writes_or_sqlite(self):
        from streamlit.testing.v1 import AppTest
        tracked = [ROOT / name for name in ("AGENTS.md", "PROJECT_STATUS.md", "NEXT_STEPS.md", "DECISIONS.md", "WORK_STATUS.md")]
        before = {p: hashlib.sha256(p.read_bytes()).digest() for p in tracked}

        def guard(original):
            def checked(file, mode="r", *args, **kwargs):
                if isinstance(file, (str, bytes, os.PathLike)):
                    path = Path(os.fsdecode(file)).resolve()
                    writing = (bool(mode & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
                               if isinstance(mode, int) else any(c in mode for c in "wax+"))
                    if writing and path.is_relative_to(ROOT) and not path.is_relative_to(HQ):
                        raise AssertionError(f"Attempted write outside HQ: {path}")
                return original(file, mode, *args, **kwargs)
            return checked

        with ExitStack() as stack:
            stack.enter_context(patch("sqlite3.connect", side_effect=AssertionError("HQ must not open SQLite")))
            stack.enter_context(patch("builtins.open", guard(builtins.open)))
            stack.enter_context(patch("io.open", guard(io.open)))
            stack.enter_context(patch("os.open", guard(os.open)))
            app = AppTest.from_file(str(HQ / "app.py"), default_timeout=30).run()
            self.assertFalse(app.exception, [e.message for e in app.exception])
            for page in ("Project Status", "Next Steps", "Decisions", "Work Status",
                         "Research / Documentation", "System / Collection Health", "Copy AI Context"):
                app.sidebar.radio[0].set_value(page).run()
                self.assertFalse(app.exception, [e.message for e in app.exception])
            self.assertEqual(len(app.checkbox), 4)
            self.assertIn("Source: PROJECT_STATUS.md", app.code[0].value)
            self.assertNotIn("Source: WORK_STATUS.md", app.code[0].value)
            app.checkbox[3].check().run()
            self.assertIn("Source: WORK_STATUS.md", app.code[0].value)
            app.sidebar.radio[0].set_value("Research / Documentation").run()
            app.text_input[0].set_value("zzzz-no-match-987").run()
            self.assertIn("No documents match", app.info[0].value)
            app.text_input[0].set_value("sampling").run()
            self.assertGreater(len(app.selectbox[0].options), 0)
            app.query_params["doc"] = "../.env"
            app.run()
            self.assertTrue(any("not in the allowed catalog" in w.value for w in app.warning))
            app.query_params["doc"] = "AGENTS.md"
            app.text_input[0].set_value("").run()
            self.assertEqual(app.selectbox[0].value, "AGENTS.md")
            self.assertFalse(app.exception, [e.message for e in app.exception])
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).digest() for p in tracked})


if __name__ == "__main__":
    unittest.main()
