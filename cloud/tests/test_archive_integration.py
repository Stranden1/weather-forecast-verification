import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from cloud import archive_storage, health, run, score, yr
from cloud.archive import ARCHIVE_PATH, SUFFIX, read_object, write_object
from cloud.archive_storage import ArchiveSession, GitStore
from cloud.store import State
from cloud.tests.crypto_fixture import test_key
from cloud.tests.test_archive import BODY, NOW, START, STATIONS, metadata


def response():
    r = requests.Response()
    r.status_code = 200
    r._content = BODY
    r.headers = {"Content-Type": "application/json", "ETag": '"test"',
                 "Set-Cookie": "secret-cookie", "Authorization": "secret-auth"}
    return r


class CollectorHookTest(unittest.TestCase):
    def setUp(self):
        key = test_key(); key.start(); self.addCleanup(key.stop)

    def test_hook_has_identical_rows_scores_station_network_and_request_count(self):
        from cloud.archive import Capture
        with tempfile.TemporaryDirectory() as tmp:
            capture = Capture(Path(tmp), START, STATIONS, NOW)
            fake = Mock(); fake.get.side_effect = lambda *a, **kw: response()
            with patch("cloud.yr.requests.Session", return_value=fake), patch("cloud.yr.now_utc", return_value=NOW):
                plain, errors = yr.collect(STATIONS, "Fixture/1.0 contact@invalid.test", NOW, pause=0)
                kept, archived_errors = yr.collect(STATIONS, "Fixture/1.0 contact@invalid.test", NOW, pause=0,
                                                   raw_sink=capture.sink)
            self.assertEqual(errors, archived_errors)
            self.assertEqual(plain, kept)
            self.assertGreater(len(plain), 0)
            self.assertEqual(fake.get.call_count, len(STATIONS) * 2)
            self.assertEqual(set(capture.received), {s["station_id"] for s in STATIONS})
            # Same selected rows, with the archive completely separate from scoring.
            import pandas as pd
            obs = pd.DataFrame([{"station": "SN1", "time": "2026-10-14T15:00:00Z", "t": 0, "w": 1, "p": 0}])
            pd.testing.assert_frame_equal(score.score_targets(pd.DataFrame(plain), obs),
                                          score.score_targets(pd.DataFrame(kept), obs))
            self.assertGreater(len(score.score_targets(pd.DataFrame(kept), obs)), 0)
            obj = read_object(capture.station_path(capture.slot, "SN1"))
            self.assertNotIn("secret-", json.dumps(obj))
            self.assertEqual(obj["request"]["query"], {"lat": 60.1235, "lon": 10.5679})

    def test_failed_hook_does_not_lose_yr_rows(self):
        fake = Mock(); fake.get.return_value = response()
        archive_errors = []
        with patch("cloud.yr.requests.Session", return_value=fake):
            expected, _ = yr.collect(STATIONS, "Fixture/1.0 contact@invalid.test", NOW, pause=0)
            got, errors = yr.collect(STATIONS, "Fixture/1.0 contact@invalid.test", NOW, pause=0,
                                    raw_sink=Mock(side_effect=RuntimeError("secret")), archive_errors=archive_errors)
        self.assertEqual(got, expected)
        self.assertEqual(errors, [])
        self.assertEqual(archive_errors, ["Yr archive: response hook failed"] * 2)

    def test_disabled_feature_has_no_archive_io_or_metadata_changes(self):
        with patch.dict(os.environ, {"WX_YR_ARCHIVE_ENABLED": "0", "WX_STATE_KEY": ""}), \
                patch("cloud.archive_storage.requests.get") as get, patch("cloud.archive_storage.GitStore") as store:
            self.assertIsNone(archive_storage.from_env(STATIONS, NOW))
            get.assert_not_called(); store.assert_not_called()

    def test_repository_must_be_private_separate_and_initialized(self):
        settings = {"WX_YR_ARCHIVE_ENABLED": "1", "WX_YR_ARCHIVE_REPO": "owner/archive",
                    "WX_YR_ARCHIVE_TOKEN": "test-only-token", "WX_YR_ARCHIVE_START_AT": NOW.isoformat(),
                    "GITHUB_REPOSITORY": "owner/public"}
        for info in ({"private": False, "full_name": "owner/archive", "default_branch": "main"},
                     {"private": True, "full_name": "owner/other", "default_branch": "main"},
                     {"private": True, "full_name": "owner/archive", "default_branch": None}):
            with patch.dict(os.environ, settings), patch("cloud.archive_storage.requests.get") as get, \
                    patch("cloud.archive_storage.GitStore") as store:
                get.return_value.status_code = 200; get.return_value.json.return_value = info
                with self.assertRaises(ValueError):
                    archive_storage.from_env(STATIONS, NOW)
                store.assert_not_called()
        with patch.dict(os.environ, {**settings, "WX_YR_ARCHIVE_REPO": "owner/public"}), \
                patch("cloud.archive_storage.requests.get") as get:
            with self.assertRaises(ValueError):
                archive_storage.from_env(STATIONS, NOW)
            get.assert_not_called()

    def test_valid_private_configuration_uses_declared_cutoff(self):
        settings = {"WX_YR_ARCHIVE_ENABLED": "1", "WX_YR_ARCHIVE_REPO": "owner/archive",
                    "WX_YR_ARCHIVE_TOKEN": "test-only-token", "WX_YR_ARCHIVE_START_AT": "2026-10-14T20:30:00Z"}
        with patch.dict(os.environ, settings), patch("cloud.archive_storage.requests.get") as get, \
                patch("cloud.archive_storage.GitStore") as store, patch("cloud.archive_storage.ArchiveSession") as session:
            get.return_value.status_code = 200
            get.return_value.json.return_value = {"private": True, "full_name": "owner/archive", "default_branch": "main"}
            archive_storage.from_env(STATIONS, NOW)
            store.assert_called_once_with("https://github.com/owner/archive.git", "test-only-token")
            self.assertEqual(session.call_args.kwargs["not_before"].isoformat(), "2026-10-14T20:30:00+00:00")

    def test_check_reports_archive_failure_after_main_data_saved(self):
        state = Mock()
        state.meta.return_value = {"runs": [{"sources": {"yr": {"errors": 0}}, "yr_archive": {"errors": 1}}]}
        with patch("cloud.run.State", return_value=state):
            self.assertEqual(run.main(["check"]), 1)
        state.meta.return_value["runs"][0]["yr_archive"]["errors"] = 0
        with patch("cloud.run.State", return_value=state):
            self.assertEqual(run.main(["check"]), 0)

    def test_archive_failure_does_not_change_main_gate_or_successful_collection(self):
        rows = [{"provider": "yr", "station": "SN1", "fetched_at": NOW.isoformat(),
                 "target": (NOW + timedelta(hours=24)).isoformat(), "lead_h": 24, "t": 1}]
        with tempfile.TemporaryDirectory() as tmp:
            state = State(Path(tmp))
            with patch.dict(os.environ, {"WEATHERNEXT_ENABLED": "0", "OPENMETEO_ENABLED": "0"}), \
                    patch("cloud.run.load_stations", return_value=STATIONS), patch("cloud.run.now_utc", return_value=NOW), \
                    patch("cloud.run.yr.collect", return_value=(rows, [])) as collect, \
                    patch("cloud.run.frost.collect", return_value=([], [])), \
                    patch("cloud.run.archive_storage.from_env", side_effect=RuntimeError("secret")), redirect_stdout(io.StringIO()) as output:
                errors = run.collect(state)
            self.assertEqual(len(state.pending()), 1)
            self.assertNotIn("secret", output.getvalue())
            record = state.meta()["runs"][-1]
            self.assertEqual(record["sources"]["yr"]["errors"], 0)
            self.assertEqual(record["yr_archive"]["status"], "error")
            self.assertFalse(health.failed(record))
            self.assertFalse(health.due(state.meta(), NOW + timedelta(minutes=30))[0])
            self.assertEqual(health.build(state.meta(), NOW)["yr_archive"]["status"], "error")
            self.assertEqual(len(errors), 1)
            collect.assert_called_once_with(STATIONS, os.getenv("MET_USER_AGENT", ""), NOW)


class GitArchiveTest(unittest.TestCase):
    def setUp(self):
        key = test_key(); key.start(); self.addCleanup(key.stop)
        env = patch.dict(os.environ, {"GH_TOKEN": "", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
        env.start(); self.addCleanup(env.stop)
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.remote = self.base / "archive.git"
        self.command("init", "--bare", "--initial-branch=main", str(self.remote))
        seed = self.base / "seed"
        self.command("clone", str(self.remote), str(seed))
        self.command("-C", str(seed), "config", "user.name", "fixture")
        self.command("-C", str(seed), "config", "user.email", "fixture@invalid.test")
        (seed / "README.md").write_text("private archive fixture\n")
        self.command("-C", str(seed), "add", "README.md")
        self.command("-C", str(seed), "commit", "-m", "fixture")
        self.command("-C", str(seed), "push", "origin", "main")
        self.readme = self.command("--git-dir", str(self.remote), "show", "main:README.md")

    def command(self, *args):
        return subprocess.run(["git", *args], cwd=self.base, check=True, capture_output=True).stdout

    def session(self, at=NOW):
        return ArchiveSession(GitStore(str(self.remote)), START, STATIONS, at)

    def test_two_collections_upload_readback_and_first_response_is_retained(self):
        first = self.session()
        first.sink(STATIONS[0], BODY, metadata())
        result = first.finish(NOW + timedelta(minutes=1))
        self.assertTrue(result["published"])
        self.assertEqual(result["captured_stations"], 1)
        later = NOW + timedelta(hours=3)
        second = self.session(later)
        before = second.capture.station_path(second.capture.slot, "SN1").read_bytes()
        second.sink(STATIONS[0], BODY.replace(b'0.03', b'9.99'), metadata(later))
        second.sink(STATIONS[1], BODY, metadata(later))
        self.assertEqual(second.capture.station_path(second.capture.slot, "SN1").read_bytes(), before)
        self.assertTrue(second.finish(later + timedelta(minutes=1))["published"])
        closed = self.session(NOW.replace(hour=13))
        self.assertEqual(closed.finish(NOW.replace(hour=13))["incomplete_slots"], 0)
        reader = GitStore(str(self.remote)); self.addCleanup(reader.close)
        objects = list(reader.root.rglob("yr/*" + SUFFIX))
        self.assertEqual(len(objects), 2)
        self.assertTrue(all(read_object(p)["response_json"].encode() == BODY for p in objects))
        self.assertEqual(self.command("--git-dir", str(self.remote), "show", "main:README.md"), self.readme)

    def test_failed_upload_loses_runner_payload_next_slot_attempt_can_retry(self):
        first = self.session()
        first.sink(STATIONS[0], BODY, metadata())
        original = first.store.git
        def failing(repo, *args):
            if args[0] == "push":
                raise RuntimeError("private-token")
            return original(repo, *args)
        with patch.object(first.store, "git", side_effect=failing):
            result = first.finish(NOW + timedelta(minutes=1))
        self.assertFalse(result["published"])
        self.assertEqual(result["captured_stations"], 0)
        self.assertFalse(first.store.repo.exists())  # explicitly no durable spool
        retry = self.session(NOW + timedelta(hours=3))
        retry.sink(STATIONS[0], BODY, metadata(NOW + timedelta(hours=3)))
        self.assertTrue(retry.finish(NOW + timedelta(hours=3, minutes=1))["published"])

    def test_readback_failure_is_not_reported_as_success(self):
        session = self.session(); original = session.store.git
        def corrupt(repo, *args):
            if args[0] == "show":
                return b"bad readback"
            return original(repo, *args)
        with patch.object(session.store, "git", side_effect=corrupt):
            result = session.finish(NOW)
        self.assertFalse(result["published"])
        self.assertEqual(result["status"], "error")

    def test_existing_objects_cannot_be_replaced_or_deleted(self):
        self.assertTrue(self.session().finish(NOW)["published"])
        for mutate in (lambda p: p.write_bytes(b"replacement"), lambda p: p.unlink()):
            store = GitStore(str(self.remote)); self.addCleanup(store.close)
            mutate(store.root / ("policy" + SUFFIX))
            with self.assertRaises(RuntimeError):
                store.publish()

    def test_plaintext_and_unrelated_staged_files_are_rejected(self):
        store = GitStore(str(self.remote)); self.addCleanup(store.close)
        (store.root).mkdir(parents=True)
        (store.root / "oops.json").write_text("plaintext")
        with self.assertRaises(RuntimeError):
            store.publish()

    def test_git_auth_is_scoped_and_absent_from_arguments_and_errors(self):
        store = GitStore(str(self.remote)); self.addCleanup(store.close)
        store.token = "private-token"
        with patch("cloud.archive_storage.subprocess.run", return_value=subprocess.CompletedProcess([], 1, b"private-token")) as call:
            with self.assertRaisesRegex(RuntimeError, "operation failed"):
                store.git(store.repo, "fetch", "origin")
        args, kw = call.call_args
        self.assertNotIn("private-token", " ".join(args[0]))
        self.assertEqual(kw["env"]["GH_TOKEN"], "")
