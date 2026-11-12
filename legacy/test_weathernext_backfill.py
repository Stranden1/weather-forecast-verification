import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import database
from collectors import weathernext as wn
from backfill_weathernext_temperature import backfill, validate_plan, validate_metadata

ISSUED='2026-09-05T12:00:00Z'

class Source:
    def sample_batch(self,collection,metrics,issued,hours,locations):
        return [dict(location_id=l['id'],start_time=issued,
                     end_time=(wn.utc(issued)+timedelta(hours=h)).isoformat(),forecast_hour=h,
                     asset_id=collection+'/test'+str(h),
                     **{wn.FIELDS['air_temperature'][1]+'_'+s:280.15 for s in wn.STATS})
                for h in hours for l in locations]

def metadata(source,issued,hours):
    return [dict(start_time=issued,end_time=(wn.utc(issued)+timedelta(hours=h)).isoformat(),
                 forecast_hour=h,ingestion_time_utc=wn.utc(issued).timestamp()+3600,
                 **{'system:index':'test'+str(h)}) for h in hours]

class HistoricalBackfillTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patch=patch.object(database,'DB_PATH',Path(self.tmp.name)/'test.db');self.patch.start()
        database.init_db();database.seed_locations()
    def tearDown(self):
        self.patch.stop();self.tmp.cleanup()
    def collect(self,**kw):
        return backfill({ISSUED:[72,216]},Source(),metadata_loader=metadata,**kw)
    def test_temperature_only_idempotency_and_truthful_retrieval(self):
        first=self.collect(write=True)
        self.assertEqual(first['sample_values_added'],60)
        with database.connect() as con:
            before=[line for line in con.iterdump() if '"sqlite_sequence"' not in line]
            self.assertEqual(con.execute('SELECT COUNT(*) FROM forecasts').fetchone()[0],10)
            self.assertEqual(con.execute('SELECT COUNT(wind_speed) FROM forecasts').fetchone()[0],0)
            self.assertGreater(con.execute('SELECT min(retrieved_at) FROM forecast_runs').fetchone()[0],ISSUED)
        second=self.collect(write=True)
        self.assertEqual(second['sample_values_added'],0)
        with database.connect() as con:
            self.assertEqual(before,[line for line in con.iterdump() if '"sqlite_sequence"' not in line])
    def test_read_only_analysis_joins_bare_and_full_asset_ids(self):
        from analyze_historical_temperature import analyze
        manifest=self.collect(write=True)
        with database.connect() as con:
            # Cover the operational bare system:index and older full asset paths.
            con.execute("UPDATE weathernext_samples SET asset_id='test72' WHERE valid_at LIKE '2026-09-08%' ")
            for location in con.execute('SELECT id,station_id FROM locations').fetchall():
                run=con.execute('INSERT INTO forecast_runs(provider,location_id,issued_at,retrieved_at) VALUES (?,?,?,?)',
                                ('MET',location['id'],ISSUED,ISSUED)).lastrowid
                for hour in [72,216]:
                    valid=wn.iso((wn.utc(ISSUED)+timedelta(hours=hour)).isoformat())
                    con.execute('INSERT INTO forecasts(run_id,valid_at,lead_hours,air_temperature) VALUES (?,?,?,?)',
                                (run,valid,hour,8))
                    con.execute('INSERT INTO observations(location_id,source_id,observed_at,air_temperature) VALUES (?,?,?,?)',
                                (location['id'],location['station_id'],valid,6))
            before=list(con.iterdump())
        result=analyze(manifest,'2026-09-30T00:00:00Z',Path(self.tmp.name)/'analysis')
        self.assertEqual([r['shared_samples'] for r in result['horizons']],[5,0,0,5])
        for result_row in [result['horizons'][0],result['horizons'][3]]:
            self.assertEqual(result_row['operational_samples'],0)
            self.assertAlmostEqual(result_row['yr_mae'],2)
            self.assertAlmostEqual(result_row['weathernext_mae'],1)
        with database.connect() as con:
            self.assertEqual(before,list(con.iterdump()))

    def test_dry_run_has_no_writes(self):
        with database.connect() as con: before=[line for line in con.iterdump() if '"sqlite_sequence"' not in line]
        self.collect()
        with database.connect() as con: self.assertEqual(before,[line for line in con.iterdump() if '"sqlite_sequence"' not in line])
    def test_missing_metadata_prevents_all_writes(self):
        with self.assertRaises(ValueError):
            backfill({ISSUED:[72]},Source(),write=True,metadata_loader=lambda *args:[])
        with database.connect() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM forecasts').fetchone()[0],0)
    def test_availability_and_time_validation(self):
        rows=metadata(None,ISSUED,[72])
        rows[0]['ingestion_time_utc']=wn.utc(rows[0]['end_time']).timestamp()+1
        with self.assertRaises(ValueError): validate_metadata(ISSUED,[72],rows)
        rows=metadata(None,ISSUED,[72]);rows[0]['forecast_hour']=73
        with self.assertRaises(ValueError): validate_metadata(ISSUED,[72],rows)
        with self.assertRaises(ValueError): validate_plan({'2026-09-05T13:00:00Z':[72]})
    def test_bad_station_coverage_has_no_partial_batch(self):
        source=Source();original=source.sample_batch
        source.sample_batch=lambda *args:original(*args)[:-1]
        with self.assertRaises(ValueError):
            backfill({ISSUED:[72]},source,write=True,metadata_loader=metadata)
        with database.connect() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM forecasts').fetchone()[0],0)

class HistoricalPairingTests(unittest.TestCase):
    def test_retrospective_vs_operational_and_target_deduplication(self):
        import pandas as pd
        from analyze_historical_temperature import horizon_pairs
        valid=pd.Timestamp('2026-09-10T12:00:00Z')
        def row(run,provider,lead,value,location=1):
            issued=valid-pd.Timedelta(hours=lead)
            return dict(run_id=run,provider=provider,location_id=location,station_id='S'+str(location),station='Station',
                        valid_at=valid,issued_at=issued,retrieved_at=valid+pd.Timedelta(days=1) if provider!='MET' else issued,
                        available_at=issued+pd.Timedelta(hours=6),lead_hours=lead,value=value)
        rows=pd.DataFrame([row(1,'MET',71,8),row(2,'MET',70,6),row(3,'WeatherNext3-mean',72,5),row(4,'MET',71,100,2)])
        observed=pd.DataFrame([dict(location_id=1,valid_at=valid,actual=6),dict(location_id=2,valid_at=valid,actual=6)])
        pairs=horizon_pairs(rows,observed,72,valid)
        self.assertEqual(len(pairs),1)
        self.assertEqual(pairs.met_run_id.iloc[0],1) # Closest lead, not the smallest error.
        self.assertEqual(pairs.met_abs_error.iloc[0],2)
        self.assertEqual(pairs.wn_abs_error.iloc[0],1)
        self.assertTrue(horizon_pairs(rows,observed,72,valid,operational=True).empty)
        rows.loc[rows.provider!='MET','available_at']=valid+pd.Timedelta(seconds=1)
        self.assertTrue(horizon_pairs(rows,observed,72,valid).empty)

    def test_both_nominal_window_and_three_hour_lead_gap_are_required(self):
        import pandas as pd
        from analyze_historical_temperature import horizon_pairs
        valid=pd.Timestamp('2026-09-10T12:00:00Z')
        rows=pd.DataFrame([dict(run_id=i,provider=p,location_id=1,station_id='S',station='S',valid_at=valid,
                                issued_at=valid-pd.Timedelta(hours=lead),retrieved_at=valid-pd.Timedelta(hours=lead),
                                available_at=valid-pd.Timedelta(hours=lead),lead_hours=float(lead),value=5)
                           for i,p,lead in [(1,'MET',213),(2,'WeatherNext3-mean',216)]])
        obs=pd.DataFrame([dict(location_id=1,valid_at=valid,actual=6)])
        self.assertEqual(len(horizon_pairs(rows,obs,216,valid)),1)
        rows.loc[0,'lead_hours']=212.99
        self.assertTrue(horizon_pairs(rows,obs,216,valid).empty)
        rows.loc[0,'lead_hours']=213
        rows.loc[1,'lead_hours']=219
        self.assertTrue(horizon_pairs(rows,obs,216,valid).empty)
