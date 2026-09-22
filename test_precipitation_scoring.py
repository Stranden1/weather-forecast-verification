"""Regression coverage for physical-hour rainfall verification and event metrics."""
import sqlite3
import unittest
import pandas as pd
from database import SCHEMA
from collectors.weathernext import migrate
from dashboard_scores import load_shared_pairs, automatic_run_pair, selected_run_pairs, shared_accuracy
from forecast_comparison import load_timeline
from precipitation_alignment import frost_interval, met_interval, weathernext_interval
from scoring.precipitation import METRIC, WET_THRESHOLD, metrics, summary, load_rows


class PrecipitationScoringTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(':memory:')
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA); migrate(self.con)
        self.con.execute("INSERT INTO locations(id,name,station_id,latitude,longitude) VALUES(1,'Test','SN1',60,10)")
        self.now = pd.Timestamp('2026-09-22T18:00:00Z')
        self.add_run(1,'MET','2026-09-22T00:30:00Z')
        self.add_run(2,'WeatherNext3-mean','2026-09-22T00:00:00Z')
        for hour,actual,met,wn in [(13,0,.1,0),(14,.1,.2,.1),(15,.2,0,.3),(16,1,2,0)]:
            target = pd.Timestamp(f'2026-09-22T{hour}:00:00Z')
            self.point(1,target,met); self.point(2,target,wn)
            self.con.execute('INSERT INTO observations(location_id,source_id,observed_at,precipitation_1h) VALUES(1,?,?,?)',('SN1',target.isoformat(),actual))

    def tearDown(self):
        self.con.close()

    def add_run(self,run,provider,issue):
        self.con.execute('INSERT INTO forecast_runs VALUES(?,?,?,?,?)',(run,provider,1,issue,issue))

    def point(self,run,target,value):
        r = self.con.execute('SELECT * FROM forecast_runs WHERE id=?',(run,)).fetchone()
        stored = target-pd.Timedelta(hours=1) if r['provider']=='MET' else target
        lead = (stored-pd.Timestamp(r['issued_at'])).total_seconds()/3600
        self.con.execute('INSERT INTO forecasts(run_id,valid_at,lead_hours,precipitation_1h) VALUES(?,?,?,?)',
                         (run,stored.isoformat(),lead,value if r['provider']=='MET' else None))
        if r['provider']!='MET':
            self.con.execute('INSERT INTO weathernext_samples VALUES(?,?,?,?,?,?,?,?,?,?)',
                             (run,stored.isoformat(),METRIC,'mean',value,'fixture',60,10,r['retrieved_at'],'mm'))

    def pairs(self,**kw):
        return load_shared_pairs(self.con,METRIC,now=self.now,**kw)

    def test_exact_interval_end_and_derived_leads(self):
        pairs=self.pairs()
        self.assertEqual(len(pairs),4)
        self.assertEqual(pairs.horizon.astype(str).unique().tolist(),['12–24h'])
        rows=load_rows(self.con)
        for r in rows.itertuples():
            interval=met_interval(r.stored_time.isoformat()) if r.provider=='MET' else weathernext_interval(r.stored_time.isoformat())
            self.assertEqual(interval,frost_interval(r.valid_at.isoformat()))
        self.assertEqual(pairs.met_lead_hours.tolist(),[12.5,13.5,14.5,15.5])
        self.assertEqual(pairs.wn_lead_hours.tolist(),[13,14,15,16])
        self.assertTrue((pairs.lead_gap<=3).all())

    def test_period_boundary_is_canonical_end_not_native_yr_start(self):
        boundary=pd.Timestamp('2026-09-22T13:00:00Z')
        rows=load_rows(self.con,start=boundary,end=boundary)
        self.assertEqual(len(rows),2)
        self.assertTrue((rows.valid_at==boundary).all())

    def test_amounts_threshold_and_event_accounting(self):
        p=self.pairs()
        pd.testing.assert_frame_equal(shared_accuracy(p,METRIC),summary(p))
        s=metrics(p).set_index('provider')
        self.assertEqual(WET_THRESHOLD,.1)
        for provider,mae,wet,bias,counts,rates in [
            ('Yr/MET',.35,.6,.25,[1,1,1,1],[.5,.5,1/3]),
            ('WeatherNext',.275,.55,-.225,[1,1,0,2],[.5,0,.5])]:
            r=s.loc[provider]
            self.assertAlmostEqual(r.mae,mae); self.assertAlmostEqual(r.wet_mae,wet);self.assertAlmostEqual(r.bias,bias)
            self.assertEqual(r[['hits','misses','false_alarms','correct_dry']].tolist(),counts)
            self.assertEqual(sum(counts),r.samples)
            for name,value in zip(['POD','FAR','CSI'],rates):self.assertAlmostEqual(r[name],value)

    def test_undefined_event_rates_and_empty_buckets(self):
        p=self.pairs().iloc[:1]
        s=metrics(p)
        self.assertTrue(s[['POD','FAR','CSI','wet_mae']].isna().all().all())
        empty=summary(p.iloc[:0])
        self.assertEqual(len(empty),8)
        self.assertTrue((empty.samples==0).all())
        self.assertTrue(empty[['mae','wet_mae','POD','FAR','CSI']].isna().all().all())
        wet=self.pairs().iloc[-1:]
        wn=metrics(wet).iloc[1]
        self.assertEqual(wn.POD,0);self.assertEqual(wn.CSI,0);self.assertTrue(pd.isna(wn.FAR))

    def test_duplicate_runs_ignore_errors_and_observation_copies(self):
        self.add_run(3,'MET','2026-09-22T00:15:00Z')
        for hour in range(13,17):self.point(3,pd.Timestamp(f'2026-09-22T{hour}:00:00Z'),99)
        p=self.pairs()
        self.assertEqual(p.met_run_id.tolist(),[3]*4) # closer even though wrong
        self.assertFalse(p.duplicated(['location_id','valid_at','horizon']).any())
        self.con.execute("INSERT INTO observations(location_id,source_id,observed_at,precipitation_1h) SELECT location_id,'copy',observed_at,precipitation_1h FROM observations")
        self.assertEqual(len(self.pairs()),4)
        self.con.execute("UPDATE observations SET precipitation_1h=77 WHERE source_id='copy'")
        self.assertTrue(self.pairs().empty)

    def test_sample_retrieval_not_run_retrieval_and_strict_interval_start(self):
        self.con.execute("UPDATE weathernext_samples SET retrieved_at=datetime(valid_at,'-1 hour')")
        self.assertTrue(self.pairs().empty) # equal start is not before start
        self.con.execute("UPDATE weathernext_samples SET retrieved_at='2026-09-22T12:00:01Z'")
        self.assertEqual(len(self.pairs()),3)
        self.assertTrue(automatic_run_pair(self.con,1,METRIC,now=self.now)['pair'])
        tl=load_timeline(self.con,1,1,2,METRIC)
        runs={r['id']:dict(r) for r in self.con.execute('SELECT * FROM forecast_runs')}
        self.assertEqual(len(selected_run_pairs(tl,runs[1],runs[2],self.now,METRIC)),3)

    def test_invalid_forecasts_observations_units_and_leads_excluded(self):
        for column,table,bad in [('precipitation_1h','forecasts',-1),('value','weathernext_samples',float('inf')),
                                 ('precipitation_1h','observations',-1)]:
            with self.subTest(table=table):
                self.con.execute('SAVEPOINT bad')
                self.con.execute(f'UPDATE {table} SET {column}=?',(bad,))
                self.assertTrue(self.pairs().empty)
                self.con.execute('ROLLBACK TO bad');self.con.execute('RELEASE bad')
        self.con.execute("UPDATE weathernext_samples SET unit='m'")
        self.assertTrue(self.pairs().empty)
        self.con.execute("UPDATE weathernext_samples SET unit='mm'")
        self.con.execute('UPDATE forecasts SET lead_hours=lead_hours+1')
        self.assertTrue(self.pairs().empty)

    def test_same_requested_and_existing_buckets_and_gap(self):
        for target,met_issue,wn_issue in [
            ('2026-09-22T12:00:00Z','2026-09-22T00:30:00Z','2026-09-22T00:00:00Z'), # requested edge
            ('2026-09-22T18:00:00Z','2026-09-22T00:30:00Z','2026-09-22T00:00:00Z'), # existing edge
            ('2026-09-22T16:00:00Z','2026-09-22T04:00:00Z','2026-09-22T00:00:00Z')]: # >3h gap
            with self.subTest(target=target):
                self.con.execute('SAVEPOINT boundary')
                self.con.execute('DELETE FROM forecasts');self.con.execute('DELETE FROM weathernext_samples');self.con.execute('DELETE FROM observations')
                for run,issue in [(1,met_issue),(2,wn_issue)]:self.con.execute('UPDATE forecast_runs SET issued_at=?,retrieved_at=? WHERE id=?',(issue,issue,run))
                self.point(1,pd.Timestamp(target),1);self.point(2,pd.Timestamp(target),1)
                self.con.execute('INSERT INTO observations(location_id,source_id,observed_at,precipitation_1h) VALUES(1,?,?,1)',('SN1',target))
                self.assertTrue(self.pairs().empty)
                self.con.execute('ROLLBACK TO boundary');self.con.execute('RELEASE boundary')

    def test_offhour_and_future_observations_no_flooring(self):
        self.con.execute("UPDATE observations SET observed_at=datetime(observed_at,'+10 minutes')")
        self.assertTrue(self.pairs().empty)
        self.con.execute("UPDATE observations SET observed_at=datetime(observed_at,'-10 minutes')")
        self.now=pd.Timestamp('2026-09-22T12:59:00Z')
        self.assertTrue(self.pairs().empty)

    def test_filters_auto_selected_and_read_only(self):
        before=list(self.con.iterdump());self.con.execute('PRAGMA query_only=ON')
        auto=automatic_run_pair(self.con,1,METRIC,now=self.now)
        self.assertEqual(auto['pair']['shared_samples'],4)
        tl=load_timeline(self.con,1,1,2,METRIC)
        p=selected_run_pairs(tl,auto['pair']['met'],auto['pair']['wn'],self.now,METRIC)
        pd.testing.assert_frame_equal(metrics(p),metrics(self.pairs()))
        self.assertTrue(self.pairs(location_id=99).empty)
        self.assertTrue(load_shared_pairs(self.con,METRIC,days=1,now='2026-09-24T18:00:00Z').empty)
        self.assertEqual(before,list(self.con.iterdump()))


if __name__=='__main__':unittest.main()
