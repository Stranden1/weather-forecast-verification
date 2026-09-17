import sqlite3
import unittest

import pandas as pd

from forecast_comparison import (
    MET_PROVIDER,
    WEATHERNEXT_PROVIDER,
    comparison_stations,
    load_temperature_timeline,
    mae_by_lead_bucket,
    past_temperature_rows,
    recent_runs,
)


class ForecastComparisonTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.con.row_factory = sqlite3.Row
        self.con.executescript(
            """
            CREATE TABLE locations (
                id INTEGER PRIMARY KEY, name TEXT, station_id TEXT,
                station_name TEXT, active INTEGER
            );
            CREATE TABLE forecast_runs (
                id INTEGER PRIMARY KEY, provider TEXT, location_id INTEGER,
                issued_at TEXT, retrieved_at TEXT
            );
            CREATE TABLE forecasts (
                id INTEGER PRIMARY KEY, run_id INTEGER, valid_at TEXT,
                lead_hours REAL, air_temperature REAL
            );
            CREATE TABLE weathernext_samples (
                run_id INTEGER, valid_at TEXT, metric TEXT,
                statistic TEXT, value REAL
            );
            CREATE TABLE observations (
                location_id INTEGER, observed_at TEXT, air_temperature REAL
            );

            INSERT INTO locations VALUES
                (1, 'Oslo', 'SN18700', 'OSLO - BLINDERN', 1),
                (2, 'Trondheim', 'SN68860', 'TRONDHEIM - VOLL', 1);
            INSERT INTO forecast_runs VALUES
                (10, 'MET', 2, '2026-09-15T00:00:00Z', '2026-09-15T00:05:00Z'),
                (11, 'WeatherNext3-mean', 2, '2026-09-15T00:00:00Z', '2026-09-15T01:00:00Z');
            INSERT INTO forecasts VALUES
                (1, 10, '2026-09-15T01:00:00Z', 1, 8),
                (2, 10, '2026-09-15T02:00:00Z', 2, 10),
                (3, 11, '2026-09-15T01:00:00Z', 1, 7),
                (4, 11, '2026-09-15T02:00:00Z', 2, 11);
            INSERT INTO weathernext_samples VALUES
                (11, '2026-09-15T01:00:00Z', 'air_temperature', 'p10', 5),
                (11, '2026-09-15T01:00:00Z', 'air_temperature', 'p90', 9),
                (11, '2026-09-15T02:00:00Z', 'air_temperature', 'p10', 8),
                (11, '2026-09-15T02:00:00Z', 'air_temperature', 'p90', 13);
            INSERT INTO observations VALUES
                (2, '2026-09-15T01:00:00Z', 6),
                (2, '2026-09-15T01:10:00Z', 8),
                (2, '2026-09-15T02:00:00Z', 12);
            """
        )

    def tearDown(self):
        self.con.close()

    def test_station_and_run_defaults_are_newest_and_trondheim_first(self):
        stations = comparison_stations(self.con)
        self.assertEqual(stations[0]["station_id"], "SN68860")
        self.assertEqual(recent_runs(self.con, 2, MET_PROVIDER)[0]["id"], 10)
        self.assertEqual(recent_runs(self.con, 2, WEATHERNEXT_PROVIDER)[0]["id"], 11)

    def test_timeline_exact_time_actual_errors_and_mae(self):
        timeline = load_temperature_timeline(self.con, 2, 10, 11)
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline.iloc[0].actual_temperature, 6)
        self.assertEqual(timeline.iloc[0].wn_p10, 5)

        past = past_temperature_rows(timeline, pd.Timestamp("2026-09-15T03:00:00Z"))
        self.assertEqual(past.met_abs_error.tolist(), [2, 2])
        self.assertEqual(past.wn_abs_error.tolist(), [1, 1])

        mae = mae_by_lead_bucket(past).set_index("provider")
        self.assertEqual(mae.loc["Yr/MET", "MAE"], 2.0)
        self.assertEqual(mae.loc["WeatherNext", "MAE"], 1.0)


if __name__ == "__main__":
    unittest.main()
