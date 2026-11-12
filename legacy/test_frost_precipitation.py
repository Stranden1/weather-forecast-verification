from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import database
from collectors import frost_observations as frost
from precipitation_alignment import frost_interval, met_interval, weathernext_interval


class FrostPrecipitationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, "DB_PATH", Path(self.tmp.name) / "test.db")
        self.db_patch.start()
        database.init_db()
        with database.connect() as con:
            con.execute(
                "INSERT INTO locations(id,name,latitude,longitude,station_id,active) "
                "VALUES(1,'Dry',60,10,'SN1',1),(2,'Wet',61,11,'SN2',1)"
            )
            con.execute(
                """
                INSERT INTO observation_sources(
                    location_id,element,source_id,checked_at
                ) VALUES(2,'precipitation_1h','SN2','2026-09-16T00:00:00Z')
                """
            )

    def tearDown(self):
        self.db_patch.stop()
        self.tmp.cleanup()

    @staticmethod
    def precipitation_row(value=1.2, **metadata):
        observation = {
            "elementId": frost.PRECIPITATION_ELEMENT,
            "value": value,
            "unit": frost.PRECIPITATION_UNIT,
            "timeOffset": frost.PRECIPITATION_TIME_OFFSET,
            "timeResolution": frost.PRECIPITATION_TIME_RESOLUTION,
            "timeSeriesId": 0,
        }
        observation.update(metadata)
        return {
            "sourceId": "SN2:0",
            "referenceTime": "2026-09-16T01:00:00Z",
            "observations": [observation],
        }

    def test_precipitation_merges_without_overwriting_or_duplicates(self):
        with database.connect() as con:
            con.execute(
                """
                INSERT INTO observations(
                    location_id,source_id,observed_at,air_temperature,wind_speed
                ) VALUES(2,'SN2','2026-09-16T01:00:00Z',7,4)
                """
            )
        frost.save_observation_rows([self.precipitation_row()], {"SN2": 2})
        frost.save_observation_rows([self.precipitation_row()], {"SN2": 2})
        with database.connect() as con:
            rows = con.execute("SELECT * FROM observations").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["air_temperature"], 7)
        self.assertEqual(rows[0]["wind_speed"], 4)
        self.assertEqual(rows[0]["precipitation_1h"], 1.2)
        self.assertEqual(rows[0]["observed_at"], "2026-09-16T01:00:00Z")

    def test_interval_alignment_uses_common_end_time(self):
        frost_window = frost_interval("2026-09-16T01:00:00Z")
        met_window = met_interval("2026-09-16T00:00:00Z")
        weathernext_window = weathernext_interval("2026-09-16T01:00:00Z")
        self.assertEqual(frost_window, met_window)
        self.assertEqual(frost_window, weathernext_window)

    def test_rejects_wrong_interval_metadata_atomically(self):
        bad = self.precipitation_row(timeResolution="PT10M")
        with self.assertRaisesRegex(ValueError, "metadata"):
            frost.save_observation_rows([bad], {"SN2": 2})
        with database.connect() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 0)

    def test_sync_requests_precipitation_only_for_supported_sources(self):
        calls = []

        def fake_fetch(source_ids, start, end, client_id, elements=frost.ELEMENTS):
            calls.append((source_ids, elements))
            return []

        with patch.object(frost, "fetch_observations", side_effect=fake_fetch):
            result = frost.sync_recent("test", days=1)
        self.assertEqual(calls[0], (["SN1", "SN2"], frost.ELEMENTS))
        self.assertEqual(calls[1], (["SN2"], frost.PRECIPITATION_ELEMENT))
        self.assertEqual(result["precipitation_locations"], 1)


if __name__ == "__main__":
    unittest.main()
