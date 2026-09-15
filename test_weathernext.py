import copy
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import database
from collectors import weathernext as wn

ISSUED = '2026-09-15T00:00:00Z'


class FakeSource:
    def hours(self, collection, issued):
        return list(range(1,361))

    def sample(self, collection, band, scale, issued, hour, locations):
        return [dict(location_id=l['id'], start_time=issued,
                     end_time=(wn.utc(issued)+timedelta(hours=hour)).isoformat(),
                     forecast_hour=hour, asset_id=collection+'/test',
                     **{band+'_'+s: (280.15 if 'temperature' in band else 5.0) for s in wn.STATS})
                for l in locations]


class WeatherNextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = patch.object(database,'DB_PATH',Path(self.tmp.name)/'test.db')
        self.patch.start()
        database.init_db()
        database.seed_locations()
        self.source = FakeSource()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def run_collect(self, **kwargs):
        return wn.collect('test',ISSUED,source=self.source,metrics=('air_temperature','wind_speed'),**kwargs)

    def test_dry_run_has_no_forecasts_or_migration(self):
        self.run_collect()
        with database.connect() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM forecasts').fetchone()[0],0)
            self.assertIsNone(con.execute("SELECT name FROM sqlite_master WHERE name='weathernext_samples'").fetchone())

    def test_units_merge_and_retry_does_not_overwrite(self):
        self.assertEqual(self.run_collect(write=True)['sample_values_added'],12)
        self.assertEqual(self.run_collect(write=True)['sample_values_added'],0)
        with database.connect() as con:
            row = con.execute('SELECT * FROM forecasts').fetchone()
            self.assertAlmostEqual(row['air_temperature'],7)
            self.assertEqual(row['wind_speed'],5)
            self.assertIsNone(row['precipitation_1h'])
            self.assertEqual(con.execute('SELECT COUNT(*) FROM forecasts').fetchone()[0],1)

    def test_missing_hour_fails_before_writes(self):
        self.source.hours = lambda *args: []
        with self.assertRaises(ValueError):
            self.run_collect(write=True)
        with database.connect() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM forecast_runs').fetchone()[0],0)

    def test_missing_pixel_does_not_save_half_batch(self):
        original = self.source.sample
        def missing(*args):
            result = original(*args)
            if 'wind' in args[1]:
                result[0]['wind_speed_10m_mean'] = None
            return result
        self.source.sample = missing
        with self.assertRaises(ValueError):
            self.run_collect(write=True)
        with database.connect() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM forecasts').fetchone()[0],0)

    def test_mixed_run_and_invalid_values_rejected(self):
        loc = dict(id=1,latitude=63.4107,longitude=10.4538)
        col,band,scale = wn.FIELDS['air_temperature']
        row = self.source.sample(col,band,scale,ISSUED,1,[loc])[0]
        row['start_time'] = '2026-09-14T00:00:00Z'
        with self.assertRaises(ValueError):
            wn.normalize(row,'air_temperature',ISSUED,'test',loc)
        row['start_time'] = ISSUED
        row[band+'_mean'] = float('nan')
        with self.assertRaises(ValueError):
            wn.normalize(row,'air_temperature',ISSUED,'test',loc)

    def test_transaction_rolls_back_on_failure(self):
        loc = dict(id=1,latitude=63.4107,longitude=10.4538)
        col,band,scale = wn.FIELDS['air_temperature']
        sample = wn.normalize(self.source.sample(col,band,scale,ISSUED,1,[loc])[0],
                              'air_temperature',ISSUED,'test',loc)
        bad = copy.deepcopy(sample)
        bad['location_id'] = 99999
        with self.assertRaises(sqlite3.IntegrityError):
            wn.save_samples([sample,bad])
        with database.connect() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM forecast_runs').fetchone()[0],0)

    def test_met_and_frost_still_work_with_new_provider(self):
        from collectors.met_forecast import save_forecast
        from collectors.frost_observations import save_observation_rows
        from scoring.scorer import scored_temperature_rows
        payload = {'properties': {'meta': {'updated_at':ISSUED},'timeseries':[
            {'time':'2026-09-15T01:00:00Z','data':{'instant':{'details':{'air_temperature':8,'wind_speed':4}}}}]}}
        save_forecast(1,payload)
        save_observation_rows([{'sourceId':'SN68860:0','referenceTime':'2026-09-15T01:00:00Z',
                               'observations':[{'elementId':'air_temperature','value':6}]}],{'SN68860':1})
        before = scored_temperature_rows()
        self.run_collect(write=True)
        after = scored_temperature_rows()
        self.assertEqual(set(after.provider),{'MET',wn.PROVIDER})
        self.assertEqual(before.iloc[0].abs_error,after[after.provider=='MET'].iloc[0].abs_error)

    def test_interim_horizon_and_timezone_validation(self):
        with self.assertRaises(ValueError):
            wn.collect('test','2026-09-15T01:00:00Z',hours=360,source=self.source)
        with self.assertRaises(ValueError):
            wn.iso('2026-09-15T00:00:00')

    def test_360_hour_run(self):
        result = self.run_collect(hours=360,write=True)
        self.assertEqual(result['batches'],360)
        with database.connect() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM forecasts').fetchone()[0],360)
            self.assertEqual(con.execute('SELECT MAX(lead_hours) FROM forecasts').fetchone()[0],360)

    def test_interrupted_collection_can_resume(self):
        original = self.source.sample
        def interrupted(*args):
            if args[4] == 2:
                raise RuntimeError('Simulated service outage')
            return original(*args)
        self.source.sample = interrupted
        with self.assertRaises(RuntimeError):
            self.run_collect(hours=2,write=True)
        self.source.sample = original
        self.assertEqual(self.run_collect(hours=2,write=True)['sample_values_added'],12)
        with database.connect() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM forecasts').fetchone()[0],2)

    def test_all_variables_units_and_idempotency(self):
        from unittest.mock import Mock
        def sample_batch(collection,metrics,issued,hours,locations):
            result=[]
            for h in hours:
                for l in locations:
                    row=dict(location_id=l['id'],start_time=issued,
                        end_time=(wn.utc(issued)+timedelta(hours=h)).isoformat(),forecast_hour=h,asset_id=collection+'/test')
                    raw={'air_temperature':280.15,'wind_speed':5,'precipitation_1h':0.002,
                         'wind_u':3,'wind_v':4,'air_pressure_at_sea_level':101325}
                    for m in metrics:
                        row.update({wn.FIELDS[m][1]+'_'+s:raw[m] for s in wn.METRIC_STATS[m]})
                    result.append(row)
            return result
        self.source.sample_batch=sample_batch
        result=wn.collect('test',ISSUED,hours=2,write=True,source=self.source)
        self.assertEqual(result['sample_values_added'],42)
        self.assertEqual(wn.collect('test',ISSUED,hours=2,write=True,source=self.source)['sample_values_added'],0)
        with database.connect() as con:
            rows={r['variable']:r for r in con.execute("SELECT * FROM weathernext_values WHERE statistic='mean'")}
            self.assertAlmostEqual(rows['air_temperature']['value'],7)
            self.assertEqual(rows['precipitation_1h']['value'],2)
            self.assertEqual(rows['precipitation_1h']['unit'],'mm')
            self.assertAlmostEqual(rows['air_pressure_at_sea_level']['value'],1013.25)
            self.assertEqual(rows['air_pressure_at_sea_level']['unit'],'hPa')
            self.assertEqual(rows['wind_u']['station_id'],'SN68860')
            self.assertIsNone(con.execute('SELECT precipitation_1h FROM forecasts').fetchone()[0])

    def test_direction_convention(self):
        self.assertEqual(wn.wind_direction(0,-5),0)
        self.assertEqual(wn.wind_direction(-5,0),90)
        self.assertEqual(wn.wind_direction(0,5),180)
        self.assertEqual(wn.wind_direction(5,0),270)
        self.assertIsNone(wn.wind_direction(0,0))

    def test_background_is_opt_in_and_failure_is_reported(self):
        import background_collect as bg
        with patch.dict('os.environ',{'WEATHERNEXT_ENABLED':'0'}),patch.object(wn,'collect_all') as run:
            self.assertTrue(bg._collect_weathernext([]))
            run.assert_not_called()
        messages=[]
        with patch.dict('os.environ',{'WEATHERNEXT_ENABLED':'1'}),patch.object(wn,'collect_all',side_effect=RuntimeError('quota')):
            self.assertFalse(bg._collect_weathernext(messages))
            self.assertIn('quota',messages[0])


if __name__ == '__main__':
    unittest.main()
