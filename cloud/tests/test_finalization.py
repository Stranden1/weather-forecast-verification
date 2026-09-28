"""Observation coverage, bounded retry and write-before-prune guarantees."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from cloud import score
from cloud.store import State, load_scored, scored_path
from cloud.tests.crypto_fixture import test_key
from cloud.timeutil import iso

UTC = timezone.utc
DAY = date(2026, 10, 2)
TARGET = datetime(2026, 10, 2, 12, tzinfo=UTC)
NOW = datetime(2026, 10, 3, 7, tzinfo=UTC)
STATIONS = [{"station_id": "SN1"}]


def pending(target=TARGET):
    return dict(provider="yr", station="SN1", target=iso(target),
                fetched_at=iso(target - timedelta(hours=24)),
                issued_at=iso(target - timedelta(hours=24)), lead_h=24, t=10)


def observations(day=TARGET, count=24):
    return [{"station": "SN1", "time": iso(day.replace(hour=h)), "t": 9, "w": None, "p": None}
            for h in range(count)]


class FinalizationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        key = test_key(); key.start(); self.addCleanup(key.stop)
        self.root = Path(self.tmp.name) / "history"
        self.st = State(Path(self.tmp.name) / "state")
        self.st.add_pending([pending()])
        meta = self.st.meta(); meta["first_fetch"] = iso(TARGET); self.st.save_meta(meta)

    def prepare(self, now=NOW):
        return score.finalize(self.st, now=now, root=self.root, stations=STATIONS)

    def test_missing_day_waits_and_recovers_when_observations_arrive(self):
        self.assertEqual(self.prepare(), [])
        self.assertEqual(len(self.st.pending()), 1)
        self.assertFalse(scored_path(DAY, self.root).exists())
        self.assertEqual(self.st.meta()["days"][str(DAY)]["coverage"], 0)
        self.st.add_obs(observations())
        self.assertEqual(self.prepare(), [str(DAY)])
        self.assertEqual(len(self.st.pending()), 1)
        self.assertEqual(self.st.meta()["finalized_days"], [])

    def test_exact_80_percent_and_duplicates_do_not_inflate(self):
        stations = [f"SN{i}" for i in range(5)]
        rows = [dict(r, station=s) for s in stations for r in observations()]
        before = pd.DataFrame(rows[:95])
        at = pd.DataFrame(rows[:96])
        self.assertLess(score.observation_coverage(before, DAY, stations)["coverage"], .8)
        self.assertEqual(score.observation_coverage(at, DAY, stations)["coverage"], .8)
        irrelevant = pd.DataFrame([dict(rows[0], station="OTHER"),
                                  dict(rows[0], time="2026-10-02T00:30:00Z"),
                                  dict(rows[96], t=float("inf"))])
        inflated = pd.concat([before, before, irrelevant], ignore_index=True)
        self.assertEqual(score.observation_coverage(inflated, DAY, stations)["observed_station_hours"], 95)

    def test_below_threshold_does_not_write(self):
        self.st.add_obs(observations(count=19))
        self.assertEqual(self.prepare(), [])
        self.st.add_obs(observations(count=20))
        self.assertEqual(self.prepare(), [str(DAY)])

    def test_deadline_forces_partial_day_and_preserves_original_metadata(self):
        self.st.add_obs(observations(count=13))
        deadline = datetime(2026, 10, 6, tzinfo=UTC)
        self.assertEqual(self.prepare(deadline - timedelta(seconds=1)), [])
        self.assertIn(str(DAY), self.prepare(deadline))
        record = score.stored_day_record(scored_path(DAY, self.root))
        self.assertTrue(record["late_finalized"])
        self.assertEqual(record["coverage"], 13 / 24)
        self.st.add_obs(observations())
        self.prepare(deadline + timedelta(hours=6))
        self.assertEqual(score.stored_day_record(scored_path(DAY, self.root)), record)
        self.assertEqual(len(self.st.pending()), 1)

    def test_empty_day_at_deadline_is_written_but_not_pruned(self):
        self.prepare(datetime(2026, 10, 6, tzinfo=UTC))
        self.assertTrue(scored_path(DAY, self.root).exists())
        self.assertTrue(load_scored(self.root).empty)
        self.assertEqual(len(self.st.pending()), 1)

    def test_confirm_later_day_keeps_earlier_deferred_forecasts(self):
        later = TARGET + timedelta(days=1)
        self.st.add_pending([pending(later)])
        self.st.add_obs(observations(later))
        prepared = self.prepare(NOW + timedelta(days=1))
        self.assertEqual(prepared, ["2026-10-03"])
        score.confirm_finalized(self.st, {d: self.st.meta()["days"][d] for d in prepared}, now=NOW)
        self.assertEqual(self.st.pending().target.tolist(), [iso(TARGET)])
        self.assertNotIn(str(DAY), self.st.meta()["finalized_days"])

    def test_failed_write_preserves_pending_and_finalized_flags(self):
        self.st.add_obs(observations())
        with patch("cloud.store.write_scored", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.prepare()
        self.assertEqual(len(self.st.pending()), 1)
        self.assertEqual(self.st.meta()["finalized_days"], [])

    def test_sidecar_failure_cannot_leave_a_day_without_coverage_metadata(self):
        self.st.add_obs(observations())
        with patch("cloud.store.atomic_json", side_effect=OSError("sidecar failed")):
            with self.assertRaises(OSError):
                self.prepare()
        self.assertFalse(scored_path(DAY, self.root).exists())
        self.assertEqual(len(self.st.pending()), 1)
        self.prepare()
        record = score.stored_day_record(scored_path(DAY, self.root))
        self.assertEqual(record["coverage"], 1)
        self.assertFalse(record["late_finalized"])

    def test_interrupted_day_write_can_recover_an_orphan_sidecar(self):
        from cloud import store
        self.st.add_obs(observations())
        real = store.atomic_bytes
        def fail(path, data):
            if path.name.endswith(".csv.gz"):
                raise OSError("day write failed")
            return real(path, data)
        with patch("cloud.store.atomic_bytes", side_effect=fail), self.assertRaises(OSError):
            self.prepare()
        path = scored_path(DAY, self.root)
        self.assertFalse(path.exists())
        self.assertTrue(score.day_metadata_path(path).exists())
        self.prepare()
        self.assertEqual(score.stored_day_record(path)["coverage"], 1)

    def test_baseline_survives_three_day_delay(self):
        target = TARGET
        row = pending(target); row["lead_h"] = 243
        row["fetched_at"] = iso(target - timedelta(hours=243))
        self.st.replace_pending(pd.DataFrame([row]))
        self.st.add_obs(observations(count=13) +
                        [dict(observations()[12], time=iso(target - timedelta(days=11)), t=4)])
        self.prepare(datetime(2026, 10, 6, tzinfo=UTC))
        self.assertEqual(load_scored(self.root).query("h == 240").iloc[0].base_t, 4)


if __name__ == "__main__":
    unittest.main()
