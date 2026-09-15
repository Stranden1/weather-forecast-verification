import sqlite3
import tempfile
import unittest
from pathlib import Path

from weathernext_status import load_weathernext_status


class WeatherNextStatusTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.con.executescript(
            """
            CREATE TABLE locations (id INTEGER PRIMARY KEY, active INTEGER);
            CREATE TABLE forecast_runs (
                id INTEGER PRIMARY KEY, provider TEXT, location_id INTEGER,
                issued_at TEXT, retrieved_at TEXT
            );
            CREATE TABLE forecasts (id INTEGER PRIMARY KEY, run_id INTEGER);
            CREATE TABLE weathernext_samples (
                run_id INTEGER, retrieved_at TEXT
            );
            INSERT INTO locations VALUES (1, 1), (2, 1), (3, 0);
            INSERT INTO forecast_runs VALUES
                (1, 'WeatherNext3-mean', 1, '2026-09-15T06:00:00Z', '2026-09-15T09:00:00Z'),
                (2, 'MET', 1, '2026-09-15T07:00:00Z', '2026-09-15T07:05:00Z');
            INSERT INTO forecasts VALUES (1, 1), (2, 1), (3, 2);
            INSERT INTO weathernext_samples VALUES
                (1, '2026-09-15T09:00:00Z'), (1, '2026-09-15T09:00:01Z');
            """
        )
        self.folder = tempfile.TemporaryDirectory()
        self.log_path = Path(self.folder.name) / "background.log"

    def tearDown(self):
        self.con.close()
        self.folder.cleanup()

    def test_database_counts_and_log_outcomes(self):
        self.log_path.write_text(
            "2026-09-15T10:00:00+00:00  OK  WeatherNext disabled\n"
            "2026-09-15T11:00:00+00:00  OK  WeatherNext=42 new values; run=2026-09-15T06:00:00Z\n",
            encoding="utf-8",
        )
        status, entries = load_weathernext_status(self.con, self.log_path)
        self.assertEqual(status["latest_run"], "2026-09-15T06:00:00Z")
        self.assertEqual(status["active_stations"], 2)
        self.assertEqual(status["forecast_points"], 2)
        self.assertEqual(status["statistic_values"], 2)
        self.assertEqual(status["new_values"], 42)
        self.assertEqual(status["collector_status"], "up to date")
        self.assertEqual(len(entries), 2)

    def test_latest_error_clears_new_value_count(self):
        self.log_path.write_text(
            "2026-09-15T11:00:00+00:00  OK  WeatherNext=0 new values; run=2026-09-15T06:00:00Z\n"
            "2026-09-15T12:00:00+00:00  PARTIAL ERROR  WeatherNext ERROR RuntimeError: quota\n",
            encoding="utf-8",
        )
        status, _ = load_weathernext_status(self.con, self.log_path)
        self.assertEqual(status["collector_status"], "error")
        self.assertIsNone(status["new_values"])
        self.assertEqual(status["last_success"], "2026-09-15T11:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
