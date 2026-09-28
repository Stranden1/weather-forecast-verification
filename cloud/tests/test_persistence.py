"""Real temporary Git remotes exercise both sides of interrupted publication."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from cloud import persistence, score
from cloud.store import FERNET_PREFIX, State, scored_path
from cloud.tests.crypto_fixture import test_key
from cloud.tests.test_finalization import DAY, NOW, STATIONS, TARGET, observations, pending
from cloud.timeutil import iso


class PersistenceTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        key = test_key(); key.start(); self.addCleanup(key.stop)
        env = patch.dict(os.environ, {"GH_TOKEN": "", "GIT_CONFIG_GLOBAL": os.devnull,
                                     "GIT_CONFIG_NOSYSTEM": "1"})
        env.start(); self.addCleanup(env.stop)
        self.remote = self.base / "origin.git"
        persistence.git(self.base, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.repo = self.base / "runner"
        persistence.git(self.base, "clone", str(self.remote), str(self.repo))
        persistence._identity(self.repo)
        (self.repo / "history").mkdir()
        (self.repo / "history" / ".gitkeep").touch()
        (self.repo / ".gitignore").write_text("state/\n")
        persistence.git(self.repo, "add", ".")
        persistence.git(self.repo, "commit", "-m", "fixture")
        persistence.git(self.repo, "push", "origin", "main")
        self.root = self.repo / "state"

    def seed_state(self):
        persistence.restore(self.repo, self.root)
        st = State(self.root)
        st.add_pending([pending()])
        st.add_obs(observations())
        meta = st.meta(); meta["first_fetch"] = iso(TARGET); st.save_meta(meta)
        persistence.publish_state(self.repo, self.root)
        # A fresh job restores the state it will later compare with its lease.
        return self.new_runner("second")

    def new_runner(self, name):
        repo = self.base / name
        persistence.git(self.base, "clone", str(self.remote), str(repo))
        persistence.restore(repo, repo / "state")
        return repo, State(repo / "state")

    def remote_sha(self, branch):
        return persistence.git(self.base, "--git-dir", str(self.remote), "rev-parse", branch).stdout

    def test_github_auth_resets_inherited_header_without_exposing_token_in_arguments(self):
        with patch.dict(os.environ, {"GH_TOKEN": "dummy-test-token"}), \
                patch("cloud.persistence.subprocess.run", return_value=subprocess.CompletedProcess([], 0, b"")) as run:
            persistence.git(self.repo, "fetch", "origin")
        args, kwargs = run.call_args
        self.assertNotIn("dummy-test-token", " ".join(args[0]))
        env = kwargs["env"]
        last = int(env["GIT_CONFIG_COUNT"]) - 1
        self.assertEqual(env[f"GIT_CONFIG_VALUE_{last - 1}"], "")
        self.assertEqual(env[f"GIT_CONFIG_KEY_{last - 1}"], env[f"GIT_CONFIG_KEY_{last}"])
        self.assertTrue(env[f"GIT_CONFIG_VALUE_{last}"].startswith("AUTHORIZATION: basic "))

    def test_absent_branch_is_the_only_fresh_start(self):
        persistence.restore(self.repo, self.root)
        self.assertEqual((self.root / ".restore-head").read_text(), "")
        self.assertTrue(State(self.root).pending().empty)
        self.assertTrue((self.root / "pending.csv.gz").read_bytes().startswith(FERNET_PREFIX))

    def test_remote_query_failure_never_initializes(self):
        with patch("cloud.persistence.git", side_effect=RuntimeError("network")) as call:
            with self.assertRaises(RuntimeError):
                persistence.restore(self.repo, self.root)
        self.assertFalse(self.root.exists())
        self.assertEqual(call.call_count, 1)

    def test_clone_failure_does_not_become_fresh_state(self):
        real = persistence.git
        def fail(repo, *args, **kwargs):
            if args[0] == "ls-remote":
                return subprocess.CompletedProcess(args, 0, b"abc refs/heads/state\n")
            if args[0] == "clone":
                raise RuntimeError("clone failed")
            return real(repo, *args, **kwargs)
        with patch("cloud.persistence.git", side_effect=fail), self.assertRaises(RuntimeError):
            persistence.restore(self.repo, self.root)
        self.assertFalse((self.root / ".restore-head").exists())

    def test_wrong_key_aborts_restore_before_any_push(self):
        self.seed_state()
        before = self.remote_sha("state")
        with test_key(), self.assertRaises(Exception):
            self.new_runner("wrong-key")
        self.assertEqual(self.remote_sha("state"), before)
        self.assertFalse((self.base / "wrong-key/state/.restore-head").exists())

    def test_missing_or_malformed_state_aborts(self):
        self.seed_state()
        real = persistence.git
        def missing(repo, *args, **kwargs):
            result = real(repo, *args, **kwargs)
            if args[0] == "clone" and "--branch" in args:
                (Path(args[-1]) / "obs.csv.gz").unlink()
            return result
        with patch("cloud.persistence.git", side_effect=missing), self.assertRaises(RuntimeError):
            self.new_runner("missing")
        self.assertFalse((self.base / "missing/state/.restore-head").exists())

    def test_failed_history_push_never_prunes_or_pushes_state(self):
        repo, st = self.seed_state()
        score.finalize(st, now=NOW, root=repo / "history", stations=STATIONS)
        before_state, before_main = self.remote_sha("state"), self.remote_sha("main")
        real = persistence.git
        def fail(where, *args, **kwargs):
            if args[0] == "push" and Path(where).resolve() == repo.resolve():
                raise RuntimeError("history push interrupted")
            return real(where, *args, **kwargs)
        with patch("cloud.persistence.git", side_effect=fail), self.assertRaises(RuntimeError):
            persistence.publish(repo, st.root)
        self.assertEqual(len(st.pending()), 1)
        self.assertEqual(st.meta()["finalized_days"], [])
        self.assertEqual(self.remote_sha("state"), before_state)
        self.assertEqual(self.remote_sha("main"), before_main)

    def test_interruption_between_pushes_recovers_from_old_state_and_remote_history(self):
        repo, st = self.seed_state()
        score.finalize(st, now=NOW, root=repo / "history", stations=STATIONS)
        path = scored_path(DAY, repo / "history")
        original = path.read_bytes()
        record = score.stored_day_record(path)
        before = self.remote_sha("state")
        def interrupt():
            raise RuntimeError("runner stopped after history push")
        with self.assertRaises(RuntimeError):
            persistence.publish(repo, st.root, after_history=interrupt)
        self.assertEqual(self.remote_sha("state"), before)
        self.assertEqual(len(st.pending()), 1)
        retry, recovered = self.new_runner("retry")
        self.assertEqual(len(recovered.pending()), 1)
        score.finalize(recovered, now=NOW, root=retry / "history", stations=STATIONS)
        self.assertEqual(scored_path(DAY, retry / "history").read_bytes(), original)
        persistence.publish(retry, recovered.root)
        _, final = self.new_runner("final")
        self.assertTrue(final.pending().empty)
        self.assertIn(str(DAY), final.meta()["finalized_days"])
        self.assertEqual(final.meta()["days"][str(DAY)]["coverage"], record["coverage"])
        self.assertEqual(final.meta()["days"][str(DAY)]["prepared_at"], record["prepared_at"])

    def test_unpushed_local_file_is_not_remote_confirmation(self):
        repo, st = self.seed_state()
        score.finalize(st, now=NOW, root=repo / "history", stations=STATIONS)
        with self.assertRaises(RuntimeError):
            persistence.confirmed_history(repo, "main")
        self.assertEqual(len(st.pending()), 1)

    def test_stale_state_lease_cannot_replace_newer_remote_state(self):
        repo, st = self.seed_state()
        other_repo, other_st = self.new_runner("concurrent")
        meta = other_st.meta(); meta["marker"] = "newer"; other_st.save_meta(meta)
        persistence.publish_state(other_repo, other_st.root)
        newer = self.remote_sha("state")
        score.finalize(st, now=NOW, root=repo / "history", stations=STATIONS)
        with self.assertRaises(RuntimeError):
            persistence.publish(repo, st.root)
        self.assertEqual(self.remote_sha("state"), newer)
        retry, recovered = self.new_runner("lease-retry")
        self.assertEqual(recovered.meta()["marker"], "newer")
        self.assertEqual(len(recovered.pending()), 1)
        self.assertTrue(scored_path(DAY, retry / "history").exists())


if __name__ == "__main__":
    unittest.main()
