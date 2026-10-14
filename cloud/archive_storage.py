"""Private Git repository transport for the simplified Yr archive.

Disabled by default. Tests use disposable local remotes; never test publishing
against the production repository. There is no upload spool or force push.
"""
from __future__ import annotations

import base64
import os
import re
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path

import requests

from .archive import ARCHIVE_PATH, SUFFIX, Capture, read_object
from .store import _fernet
from .timeutil import parse


class GitStore:
    def __init__(self, remote: str, token: str = ""):
        self.temporary = tempfile.TemporaryDirectory(prefix="wx-yr-archive-")
        self.repo = Path(self.temporary.name) / "repo"
        self.token = token
        try:
            self.git(Path(self.temporary.name), "clone", "--depth", "1", "--single-branch",
                     "--branch", "main", "--", remote, str(self.repo))
            self.git(self.repo, "config", "user.name", "weather-bot")
            self.git(self.repo, "config", "user.email", "weather-bot@users.noreply.github.com")
        except Exception:
            self.close()
            raise

    @property
    def root(self) -> Path:
        return self.repo / ARCHIVE_PATH

    def git(self, repo: Path, *args: str):
        env = os.environ.copy()
        # Reset inherited public-repository credentials. This token is archive-only.
        n = int(env.get("GIT_CONFIG_COUNT", "0"))
        auth = base64.b64encode(("x-access-token:" + self.token).encode()).decode()
        env.update({"GH_TOKEN": "", "GIT_TERMINAL_PROMPT": "0",
                    "GIT_CONFIG_COUNT": str(n + 2),
                    f"GIT_CONFIG_KEY_{n}": "http.https://github.com/.extraheader",
                    f"GIT_CONFIG_VALUE_{n}": "",
                    f"GIT_CONFIG_KEY_{n + 1}": "http.https://github.com/.extraheader",
                    f"GIT_CONFIG_VALUE_{n + 1}": "AUTHORIZATION: basic " + auth if self.token else ""})
        try:
            result = subprocess.run(["git", *args], cwd=repo, env=env,
                                    capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            raise RuntimeError("Yr archive: Git operation unavailable or timed out") from None
        if result.returncode:
            raise RuntimeError("Yr archive: Git operation failed")
        return result.stdout

    def publish(self) -> bool:
        """Only add new encrypted objects; confirm exact bytes after a normal push."""
        prefix = ARCHIVE_PATH.as_posix() + "/"
        changed = self.git(self.repo, "diff", "--name-only", "HEAD", "--", ARCHIVE_PATH.as_posix())
        if changed:
            raise RuntimeError("Yr archive: existing tracked files changed")
        self.git(self.repo, "add", "--", ARCHIVE_PATH.as_posix())
        staged = self.git(self.repo, "diff", "--cached", "--name-status").decode().splitlines()
        if not staged:
            return False
        expected = {}
        for row in staged:
            mode, name = row.split("\t", 1)
            if mode != "A" or not name.startswith(prefix) or not name.endswith(SUFFIX):
                raise RuntimeError("Yr archive: refusing non-additive publication")
            path = self.repo / name
            read_object(path)  # refuses plaintext, symlinks, unknown schema and bad key
            expected[name] = path.read_bytes()
        self.git(self.repo, "commit", "-m", "Retain encrypted Yr responses and slot manifests")
        self.git(self.repo, "push", "origin", "HEAD:refs/heads/main")
        self.git(self.repo, "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main")
        for name, content in expected.items():
            if self.git(self.repo, "show", "origin/main:" + name) != content:
                raise RuntimeError("Yr archive: remote readback mismatch")
        return True

    def close(self):
        self.temporary.cleanup()


class ArchiveSession:
    def __init__(self, store: GitStore, start_day: date, stations: list[dict], at: datetime,
                 not_before: datetime | None = None):
        self.store = store
        try:
            self.capture = Capture(store.root, start_day, stations, at,
                                   revision=os.getenv("GITHUB_SHA") or None,
                                   job_id=os.getenv("GITHUB_RUN_ID") or None, not_before=not_before)
        except Exception:
            store.close()
            raise

    @property
    def sink(self):
        # Outside a window no raw responses need to be copied/timestamped.
        return self.capture.sink if self.capture.slot else None

    def finish(self, at: datetime) -> dict:
        summary = {"enabled": True, "status": "error", "captured_stations": 0,
                   "closed_slots": 0, "incomplete_slots": 0, "errors": 1, "published": False}
        try:
            summary = self.capture.finish(at)
            self.store.publish()
            summary["published"] = True  # new objects confirmed, or nothing new to publish
        except Exception:
            summary.update(status="error", captured_stations=0, published=False,
                           errors=max(1, summary["errors"]))
        finally:
            try:
                self.store.close()
            except OSError:
                summary.update(status="error", errors=max(1, summary["errors"]))
        return summary


def from_env(stations: list[dict], at: datetime) -> ArchiveSession | None:
    """A missing/off flag performs no archive IO, key access or network requests."""
    if os.getenv("WX_YR_ARCHIVE_ENABLED", "0") != "1":
        return None
    repo = os.getenv("WX_YR_ARCHIVE_REPO", "")
    token = os.getenv("WX_YR_ARCHIVE_TOKEN", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not token:
        raise ValueError("Yr archive: private repository and credential required")
    if repo.casefold() == os.getenv("GITHUB_REPOSITORY", "Stranden1/weather-forecast-verification").casefold():
        raise ValueError("Yr archive: repository must differ from the public project")
    start_at = parse(os.environ["WX_YR_ARCHIVE_START_AT"])
    _fernet(required=True)
    response = requests.get("https://api.github.com/repos/" + repo,
                            headers={"Authorization": "Bearer " + token,
                                     "Accept": "application/vnd.github+json"},
                            timeout=20, allow_redirects=False)
    if response.status_code != 200:
        raise RuntimeError("Yr archive: private repository verification failed")
    info = response.json()
    if info.get("private") is not True or info.get("full_name", "").casefold() != repo.casefold():
        raise ValueError("Yr archive: destination is not the configured private repository")
    if info.get("default_branch") != "main" or info.get("archived"):
        raise ValueError("Yr archive: initialize an active main branch first")
    return ArchiveSession(GitStore("https://github.com/" + repo + ".git", token),
                          start_at.date(), stations, at, not_before=start_at)
