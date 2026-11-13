"""The pipeline installs exact, tested versions (DECISIONS.md, 13 Nov 2026)."""
from __future__ import annotations

import re
import unittest
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "cloud" / "requirements-lock.txt"


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _lines(path: Path) -> list[str]:
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.lstrip().startswith("#")]


def lock() -> dict[str, str]:
    out = {}
    for line in _lines(LOCK):
        m = re.fullmatch(r"([A-Za-z0-9_.\-]+)==([A-Za-z0-9_.+\-]+)", line)
        if not m:
            raise AssertionError(f"not an exact pin: {line}")
        out[_norm(m[1])] = m[2]
    return out


class LockFileTest(unittest.TestCase):
    def test_every_line_is_an_exact_pin(self):
        self.assertGreater(len(lock()), 10)

    def test_every_direct_requirement_is_pinned(self):
        pinned = lock()
        for line in _lines(ROOT / "cloud" / "requirements.txt"):
            name = _norm(re.split(r"[<>=!~;\[ ]", line, maxsplit=1)[0])
            self.assertIn(name, pinned, f"{name} is in requirements.txt but not locked")

    def test_workflows_install_the_lock_file(self):
        for wf in ("collect.yml", "tests.yml"):
            text = (ROOT / ".github" / "workflows" / wf).read_text(encoding="utf-8")
            self.assertIn("pip install -r cloud/requirements-lock.txt", text, wf)
            self.assertNotIn("pip install -r cloud/requirements.txt", text, wf)

    def test_tests_run_on_the_locked_versions(self):
        """Fails when the environment drifted from the lock, so a pass means these versions."""
        drift = {}
        for name, want in lock().items():
            try:
                got = version(name)
            except PackageNotFoundError:
                got = None
            if got != want:
                drift[name] = (want, got)
        self.assertEqual(drift, {}, "installed versions differ from requirements-lock.txt")


if __name__ == "__main__":
    unittest.main()
