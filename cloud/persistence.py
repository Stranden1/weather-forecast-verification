"""Fail-closed restore and history-first publication, shared by CI and git tests.

Never invoke publish against production during local validation; tests use bare
temporary repositories. Git errors omit arguments/output so credentials stay private.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
from pathlib import Path
import subprocess
import uuid

import pandas as pd

from .config import OBS_COLUMNS, PENDING_COLUMNS, ROOT, STATE_DIR
from .history_crypto import encrypt_history
from .score import confirm_finalized, day_metadata_path, stored_day_record
from .store import FERNET_PREFIX, State, _fernet, plaintext_bytes


def git(repo: Path, *args: str, allowed=(0,)):
    env = os.environ.copy()
    # Checkout's token is provided through environment, never command arguments or logs.
    if env.get("GH_TOKEN"):
        n = int(env.get("GIT_CONFIG_COUNT", "0"))
        token = base64.b64encode(("x-access-token:" + env["GH_TOKEN"]).encode()).decode()
        env.update({"GIT_CONFIG_COUNT": str(n + 2),
                    f"GIT_CONFIG_KEY_{n}": "http.https://github.com/.extraheader",
                    f"GIT_CONFIG_VALUE_{n}": "",
                    f"GIT_CONFIG_KEY_{n + 1}": "http.https://github.com/.extraheader",
                    f"GIT_CONFIG_VALUE_{n + 1}": "AUTHORIZATION: basic " + token})
    result = subprocess.run(["git", *args], cwd=repo, env=env, capture_output=True)
    if result.returncode not in allowed:
        raise RuntimeError(f"git {args[0]} failed (exit {result.returncode}); no further publication attempted")
    return result


def validate_state(root: Path) -> None:
    _fernet(required=True)
    required = {"pending.csv.gz": {"provider", "station", "target", "fetched_at", "lead_h"},
                "obs.csv.gz": set(OBS_COLUMNS)}
    for name, columns in required.items():
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"State restore missing regular file: {name}")
        data = plaintext_bytes(path.read_bytes())  # supports the pre-encryption state upgrade
        frame = pd.read_csv(io.BytesIO(data), compression="gzip")
        if not columns.issubset(frame.columns):
            raise RuntimeError(f"Invalid state schema: {name}")
    path = root / "meta.json"
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("State restore missing meta.json")
    meta = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(meta, dict) or not isinstance(meta.get("finalized_days"), list) \
            or not isinstance(meta.get("runs"), list) or "first_fetch" not in meta:
        raise RuntimeError("Invalid state metadata")
    from datetime import date
    for day in meta["finalized_days"]:
        date.fromisoformat(day)
    if meta["first_fetch"] is not None:
        from .timeutil import parse
        parse(meta["first_fetch"])


def restore(repo: Path = ROOT, root: Path = STATE_DIR) -> None:
    repo, root = Path(repo).resolve(), Path(root).resolve()
    _fernet(required=True)
    if root.exists():
        raise FileExistsError("Restore needs a fresh state directory; existing state was left untouched")
    result = git(repo, "ls-remote", "--exit-code", "--heads", "origin", "refs/heads/state", allowed=(0, 2))
    if result.returncode == 2:  # ONLY absence of a matching ref permits first-run initialization
        root.mkdir(parents=True)
        st = State(root)
        st.replace_pending(pd.DataFrame(columns=PENDING_COLUMNS))
        st.replace_obs(pd.DataFrame(columns=OBS_COLUMNS))
        st.save_meta(st.meta())
        head = ""
    else:
        remote = git(repo, "remote", "get-url", "origin").stdout.decode().strip()
        git(repo, "clone", "--depth", "1", "--single-branch", "--branch", "state", remote, str(root))
        validate_state(root)  # any clone/decryption/schema failure stops before collection
        head = git(root, "rev-parse", "HEAD").stdout.decode().strip()
    (root / ".restore-head").write_text(head, encoding="ascii")


def _identity(repo: Path):
    git(repo, "config", "user.name", "weather-bot")
    git(repo, "config", "user.email", "weather-bot@users.noreply.github.com")


def _commit_history(repo: Path):
    encrypt_history(repo / "history")  # also catches legacy day files arriving from origin
    git(repo, "add", "--", "history")
    staged = git(repo, "diff", "--cached", "--name-only").stdout.decode().splitlines()
    if any(not name.startswith("history/") for name in staged):
        raise RuntimeError("Refusing to commit unrelated staged files")
    if staged:
        git(repo, "commit", "-m", "Store encrypted scored days")


def confirmed_history(repo: Path, branch: str) -> dict[str, dict]:
    """Verify exact encrypted files and sidecars in freshly fetched origin."""
    git(repo, "fetch", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}")
    records = {}
    for path in sorted((repo / "history").glob("*/*.csv.gz")):
        local = path.read_bytes()
        if not local.startswith(FERNET_PREFIX):
            raise RuntimeError("Refusing to confirm plaintext history")
        relative = path.relative_to(repo).as_posix()
        remote = git(repo, "show", f"origin/{branch}:{relative}").stdout
        if remote != local:
            raise RuntimeError(f"History not confirmed in origin: {path.name}")
        sidecar = day_metadata_path(path)
        if sidecar.exists():
            relative_meta = sidecar.relative_to(repo).as_posix()
            remote_meta = git(repo, "show", f"origin/{branch}:{relative_meta}").stdout
            if json.loads(remote_meta) != json.loads(sidecar.read_bytes()):
                raise RuntimeError(f"History metadata not confirmed in origin: {path.name}")
        records[path.name.removesuffix(".csv.gz")] = stored_day_record(path)
    return records


def publish_state(repo: Path, root: Path) -> None:
    validate_state(root)
    for name in ("pending.csv.gz", "obs.csv.gz"):
        if not (root / name).read_bytes().startswith(FERNET_PREFIX):
            raise RuntimeError("Refusing to publish plaintext working state")
    expected = (root / ".restore-head").read_text(encoding="ascii").strip()
    remote = git(repo, "remote", "get-url", "origin").stdout.decode().strip()
    if not (root / ".git").exists():
        git(root, "init", "-q")
    _identity(root)
    # An orphan commit keeps remote state compact; an explicit lease protects newer state.
    git(root, "checkout", "--orphan", "snapshot-" + uuid.uuid4().hex)
    git(root, "rm", "-r", "-f", "--cached", "--ignore-unmatch", ".")
    git(root, "add", "--", "pending.csv.gz", "obs.csv.gz", "meta.json")
    git(root, "commit", "-m", "Encrypted working state")
    git(root, "push", f"--force-with-lease=refs/heads/state:{expected}",
        remote, "HEAD:refs/heads/state")


def publish(repo: Path = ROOT, root: Path = STATE_DIR, branch: str = "main",
            after_history=None) -> None:
    """Publish history -> verify origin -> prune exact days -> publish leased state.

    after_history is a failure-injection hook for recovery tests, never used in CI.
    """
    repo, root = Path(repo).resolve(), Path(root).resolve()
    _fernet(required=True)
    validate_state(root)
    if not (root / ".restore-head").is_file():
        raise RuntimeError("State must be restored successfully before publication")
    if not branch or branch == "state":
        raise ValueError("History branch must differ from the state branch")
    _identity(repo)
    _commit_history(repo)
    git(repo, "fetch", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}")
    git(repo, "rebase", f"origin/{branch}")
    _commit_history(repo)
    git(repo, "push", "origin", f"HEAD:refs/heads/{branch}")  # never force main
    confirmed = confirmed_history(repo, branch)
    if after_history:
        after_history()
    confirm_finalized(State(root), confirmed)
    publish_state(repo, root)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["restore", "publish"])
    p.add_argument("--branch", default=os.getenv("GITHUB_REF_NAME", "main"))
    args = p.parse_args(argv)
    if args.action == "restore":
        restore()
    else:
        publish(branch=args.branch)


if __name__ == "__main__":
    main()
