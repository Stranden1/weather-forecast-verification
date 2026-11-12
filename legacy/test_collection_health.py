from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from collection_health import (
    append_source_event,
    health_status,
    load_collection_health,
    read_collection_events,
    yr_stale_warning,
)


class CollectionHealthTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.log_path = Path(self.folder.name) / "background.log"

    def tearDown(self):
        self.folder.cleanup()

    def test_legacy_summary_records_each_success(self):
        self.log_path.write_text(
            "2026-09-17T04:13:08+00:00  OK  "
            "MET={'locations': 50, 'errors': []} | "
            "Frost={'locations': 50, 'errors': []} | "
            "WeatherNext=0 new values; run=2026-09-16T18:00:00Z\n",
            encoding="utf-8",
        )
        health = load_collection_health(
            self.log_path, datetime(2026, 9, 17, 10, tzinfo=timezone.utc)
        )
        self.assertEqual({row["status"] for row in health["sources"].values()}, {"OK"})
        self.assertEqual(len(read_collection_events(self.log_path)), 3)

    def test_timezone_safe_thresholds_and_stale_warning(self):
        self.log_path.write_text(
            "2026-09-16T22:00:00+02:00  SOURCE  MET  OK\n"
            "2026-09-16T16:00:00Z  SOURCE  Frost  OK\n",
            encoding="utf-8",
        )
        health = load_collection_health(
            self.log_path, datetime(2026, 9, 17, 5, tzinfo=timezone.utc)
        )
        self.assertEqual(health["sources"]["MET"]["status"], "Delayed")
        self.assertEqual(health["sources"]["MET"]["age"], "9h 0m")
        self.assertEqual(health["sources"]["Frost"]["status"], "Stale / attention needed")
        self.assertEqual(health["sources"]["WeatherNext"]["status"], "Stale / attention needed")
        self.assertIsNone(yr_stale_warning(health))

        stale = load_collection_health(
            self.log_path, datetime(2026, 9, 17, 9, tzinfo=timezone.utc)
        )
        self.assertIn("may not be recoverable", yr_stale_warning(stale))

    def test_failed_latest_attempt_is_delayed_not_immediately_stale(self):
        self.log_path.write_text(
            "2026-09-17T00:00:00Z  SOURCE  MET  OK\n"
            "2026-09-17T06:00:00Z  SOURCE  MET  ERROR  request failed\n",
            encoding="utf-8",
        )
        health = load_collection_health(
            self.log_path, datetime(2026, 9, 17, 7, tzinfo=timezone.utc)
        )
        self.assertEqual(health["sources"]["MET"]["status"], "Delayed")
        self.assertEqual(health["sources"]["MET"]["last_success"].hour, 0)

    def test_recent_yr_gap_and_writer(self):
        self.log_path.write_text(
            "2026-09-15T00:00:00Z  SOURCE  MET  OK\n"
            "2026-09-15T18:30:00Z  SOURCE  MET  OK\n",
            encoding="utf-8",
        )
        append_source_event(self.log_path, "Frost", "OK", "locations=50")
        health = load_collection_health(
            self.log_path, datetime(2026, 9, 16, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(health["yr_gap"]["hours"], 18.5)
        self.assertTrue(any(event["source"] == "Frost" for event in read_collection_events(self.log_path)))

    def test_status_boundaries(self):
        self.assertEqual(health_status(8), "OK")
        self.assertEqual(health_status(8.01), "Delayed")
        self.assertEqual(health_status(12), "Delayed")
        self.assertEqual(health_status(12.01), "Stale / attention needed")

    def test_background_main_records_each_completed_source(self):
        import background_collect as background
        from collectors import weathernext

        met = {"locations": 50, "rows_added": 100, "errors": []}
        frost = {"locations": 50, "rows_added": 200, "errors": []}
        weather_next = {
            "sample_values_added": 300,
            "issued_at": "2026-09-17T00:00:00Z",
        }
        environment = {
            "WEATHERNEXT_ENABLED": "1",
            "FROST_CLIENT_ID": "fixture",
            "MET_USER_AGENT": "fixture",
            "AUTO_DISCOVER_STATIONS": "0",
        }
        with (
            patch.dict("os.environ", environment),
            patch.object(background, "LOG_PATH", self.log_path),
            patch.object(background, "init_db"),
            patch.object(background, "seed_locations"),
            patch.object(background, "log_collection_start", return_value=1),
            patch.object(background, "log_collection_finish"),
            patch.object(background, "collect_all", return_value=met),
            patch.object(background, "sync_recent", return_value=frost),
            patch.object(weathernext, "collect_all", return_value=weather_next),
        ):
            self.assertEqual(background.main(), 0)

        events = read_collection_events(self.log_path)
        self.assertEqual(
            {(event["source"], event["outcome"]) for event in events},
            {("MET", "OK"), ("Frost", "OK"), ("WeatherNext", "OK")},
        )


if __name__ == "__main__":
    unittest.main()
