import sqlite3
import unittest
from contextlib import closing
import pandas as pd
from dashboard_scores import load_accuracy_rows


class DashboardScoresTests(unittest.TestCase):
    def test_matches_original_join_including_duplicate_hour_observations(self):
        with closing(sqlite3.connect(':memory:')) as con:
            con.executescript('''
                CREATE TABLE locations(id, name, station_id);
                CREATE TABLE forecast_runs(id, location_id, provider, issued_at);
                CREATE TABLE forecasts(run_id, valid_at, lead_hours, air_temperature, wind_speed);
                CREATE TABLE observations(location_id, observed_at, air_temperature, wind_speed);
                INSERT INTO locations VALUES(1,'Voll','SN68860'),(2,'Other','SN1');
                INSERT INTO forecast_runs VALUES(1,1,'MET','2026-09-15T00:00:00Z');
                INSERT INTO forecasts VALUES(1,'2026-09-15T01:00:00Z',1,10,5),(1,'2026-09-15T02:00:00Z',2,NULL,4);
                INSERT INTO observations VALUES
                  (1,'2026-09-15T01:00:00Z',8,3),(1,'2026-09-15T01:10:00Z',9,4),
                  (2,'2026-09-15T01:00:00Z',20,20),(1,'2026-09-15T02:00:00Z',7,NULL);
            ''')
            for metric in ('air_temperature','wind_speed'):
                original=pd.read_sql_query(f'''SELECT l.name AS location,l.station_id,r.provider,r.issued_at,
                    f.valid_at,f.lead_hours,f.{metric} AS forecast_value,o.{metric} AS observed_value,
                    ABS(f.{metric}-o.{metric}) AS abs_error,f.{metric}-o.{metric} AS signed_error
                    FROM forecasts f JOIN forecast_runs r ON r.id=f.run_id JOIN locations l ON l.id=r.location_id
                    JOIN observations o ON o.location_id=r.location_id
                    AND strftime('%Y-%m-%dT%H:00:00Z',o.observed_at)=strftime('%Y-%m-%dT%H:00:00Z',f.valid_at)
                    WHERE f.{metric} IS NOT NULL AND o.{metric} IS NOT NULL''',con)
                optimized=load_accuracy_rows(con,metric)
                pd.testing.assert_frame_equal(original.sort_values('observed_value').reset_index(drop=True),
                                              optimized.sort_values('observed_value').reset_index(drop=True))
