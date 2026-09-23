"""Exercise dashboard interactions against fixture data and assert no DB writes."""
import sys
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
import database
from collectors.weathernext import migrate
from streamlit.testing.v1 import AppTest

def check(app):
    assert not app.exception,[e.message for e in app.exception]

with tempfile.TemporaryDirectory() as folder:
    database.DB_PATH=Path(folder)/'ui-test.db'
    database.init_db()
    database.seed_locations()
    now=datetime.now(timezone.utc).replace(minute=0,second=0,microsecond=0)
    init=now-timedelta(hours=6)
    iso=lambda x:x.isoformat().replace('+00:00','Z')
    health_log=Path(folder)/'background.log'
    health_log.write_text(
        f"{iso(now-timedelta(hours=36))}  SOURCE  MET  OK\n"
        f"{iso(now-timedelta(hours=2))}  OK  MET={{'locations': 50, 'errors': []}} | "
        f"Frost={{'locations': 50, 'errors': []}} | WeatherNext=0 new values; run={iso(init)}\n",
        encoding='utf-8')
    os.environ['WEATHERAPP_BACKGROUND_LOG_PATH']=str(health_log)
    with database.connect() as con:
        migrate(con)
        for run_id,provider,issued in [(1,'MET',init-timedelta(hours=6)),(2,'MET',init),(3,'WeatherNext3-mean',init)]:
            con.execute('INSERT INTO forecast_runs VALUES (?,?,?,?,?)',(run_id,provider,1,iso(issued),iso(issued)))
            for hour in range(1,10):
                valid=init+timedelta(hours=hour)
                con.execute('INSERT INTO forecasts(run_id,valid_at,lead_hours,air_temperature) VALUES (?,?,?,?)',
                    (run_id,iso(valid),(valid-issued).total_seconds()/3600,8+hour/10))
                if run_id==3:
                    for stat,value in [('p10',6),('p90',11)]:
                        con.execute('INSERT INTO weathernext_samples VALUES (?,?,?,?,?,?,?,?,?,?)',
                            (run_id,iso(valid),'air_temperature',stat,value,'fixture',63.4107,10.4538,iso(init),'degC'))
        for hour in range(1,10):
            con.execute('INSERT INTO observations(location_id,source_id,observed_at,air_temperature) VALUES (?,?,?,?)',
                        (1,'SN68860',iso(init+timedelta(hours=hour)),8))
    with database.connect() as con:
        con.execute('UPDATE forecasts SET wind_speed=air_temperature/2')
        con.execute('UPDATE observations SET wind_speed=air_temperature/2')
        con.execute("INSERT INTO weathernext_samples SELECT run_id,valid_at,'wind_speed',statistic,value/2,asset_id,latitude,longitude,retrieved_at,'m/s' FROM weathernext_samples WHERE metric='air_temperature'")
    with database.connect() as con:
        # A station with two individually available runs but no <=3h fair pair.
        for run_id,provider,issued in [(20,'MET',now-timedelta(hours=1)),(21,'WeatherNext3-mean',now-timedelta(hours=12))]:
            con.execute('INSERT INTO forecast_runs VALUES(?,?,?,?,?)',(run_id,provider,3,iso(issued),iso(issued)))
            con.execute('INSERT INTO forecasts(run_id,valid_at,lead_hours,air_temperature) VALUES(?,?,?,9)',
                        (run_id,iso(now),(now-issued).total_seconds()/3600))
        con.execute('INSERT INTO observations(location_id,source_id,observed_at,air_temperature) VALUES(?,?,?,7)',(3,'SN50540',iso(now)))
    # Historical points retrieved today are eligible only through verified evidence.
    from backfill_weathernext_temperature import backfill
    from test_weathernext_backfill import Source, metadata
    long_init=(now-timedelta(days=10)).replace(hour=0)
    backfill({iso(long_init):[72,120,168,216]},Source(),write=True,metadata_loader=metadata)
    with database.connect() as con:
        run=con.execute('INSERT INTO forecast_runs(provider,location_id,issued_at,retrieved_at) VALUES(?,?,?,?)',
                        ('MET',1,iso(long_init),iso(long_init))).lastrowid
        for hour in [72,120,168,216]:
            valid=iso(long_init+timedelta(hours=hour))
            con.execute('INSERT INTO forecasts(run_id,valid_at,lead_hours,air_temperature) VALUES(?,?,?,?)',(run,valid,hour,8))
            con.execute('INSERT INTO observations(location_id,source_id,observed_at,air_temperature) VALUES(?,?,?,?)',(1,'SN68860',valid,6))
        # Rainfall is stored at different raw timestamps, but the same physical hour.
        for run_id,provider,age in [(200,'MET',56),(201,'WeatherNext3-mean',54),
                                    (202,'MET',18),(203,'WeatherNext3-mean',16)]:
            issue=now-timedelta(hours=age)
            con.execute('INSERT INTO forecast_runs VALUES(?,?,?,?,?)',(run_id,provider,1,iso(issue),iso(issue)))
            for ago,value in [(3,0.0),(2,0.8)]:
                end=now-timedelta(hours=ago)
                valid=end-timedelta(hours=1) if provider=='MET' else end
                con.execute('INSERT INTO forecasts(run_id,valid_at,lead_hours,precipitation_1h) VALUES(?,?,?,?)',
                            (run_id,iso(valid),(valid-issue).total_seconds()/3600,value if provider=='MET' else None))
                if provider!='MET':
                    con.execute('INSERT INTO weathernext_samples VALUES(?,?,?,?,?,?,?,?,?,?)',
                                (run_id,iso(valid),'precipitation_1h','mean',value+0.2,'rain-fixture',63,10,iso(issue),'mm'))
        for ago,value in [(3,0.0),(2,1.0)]:
            con.execute('UPDATE observations SET precipitation_1h=? WHERE location_id=1 AND observed_at=?',
                        (value,iso(now-timedelta(hours=ago))))
        before=list(con.iterdump())
    app=AppTest.from_file(str(root/'app.py'),default_timeout=30).run()
    check(app)
    assert [t.label for t in app.tabs][:3]==['Forecast vs Actual','Station network','Overall accuracy']
    assert app.selectbox(key='forecast_actual_station').value==1
    assert app.selectbox(key='comparison_mode').value=='Automatic fair pair'
    assert any('Chart window starts at the selected runs’ earliest forecast time' in c.value for c in app.caption)
    assert app.selectbox(key='met_run_1').disabled
    assert app.selectbox(key='met_run_1').value==2
    assert any(b.label=='Fetch WeatherNext' for b in app.button)
    admin=next(e for e in app.expander if e.label=='Admin / Manual controls')
    assert admin.proto.expanded is False
    health=next(d.value for d in app.dataframe if list(d.value.columns)==['Source','Last success (UTC)','Age','Status'])
    assert health['Source'].tolist()==['Yr/MET','WeatherNext','Frost']
    assert health['Status'].tolist()==['OK','OK','OK']
    assert next(e for e in app.expander if e.label=='Collection health details').proto.expanded is False
    assert next(e for e in app.expander if e.label=='Advanced / Manual run selection').proto.expanded is False
    assert any('All collectors OK' in c.value for c in app.caption)
    assert any('Recent Yr collection gap:' in c.value for c in app.caption)
    assert not app.warning
    stale=now-timedelta(hours=13)
    health_log.write_text(
        f"{iso(stale)}  OK  MET={{'locations': 50, 'errors': []}} | "
        f"Frost={{'locations': 50, 'errors': []}} | WeatherNext=0 new values; run={iso(stale)}\n",
        encoding='utf-8')
    app.run()
    check(app)
    assert any('Historical long-range forecasts missed' in w.value for w in app.warning)
    health_log.write_text(
        f"{iso(now-timedelta(hours=2))}  OK  MET={{'locations': 50, 'errors': []}} | "
        f"Frost={{'locations': 50, 'errors': []}} | WeatherNext=0 new values; run={iso(init)}\n",
        encoding='utf-8')
    app.run()
    check(app)
    healthy_text=health_log.read_text(encoding='utf-8')
    health_log.write_text(healthy_text+f"{iso(now-timedelta(hours=1))}  SOURCE  MET  ERROR\n",encoding='utf-8')
    app.run()
    check(app)
    assert any('Yr/MET: Delayed' in w.value for w in app.warning)
    assert not any('All collectors OK' in c.value for c in app.caption)
    health_log.write_text(healthy_text,encoding='utf-8')
    app.run()
    assert next(m for m in app.metric if m.label=='Shared observed hours').value=='6'
    app.selectbox(key='comparison_mode').set_value('Manual runs').run()
    assert not app.selectbox(key='met_run_1').disabled
    app.selectbox(key='met_run_1').set_value(1).run()
    check(app)
    assert app.selectbox(key='met_run_1').value==1
    assert any('These manual runs are 6.0 h apart' in i.value for i in app.info)
    next(s for s in app.selectbox if s.label=='Chart window').set_value('Full run').run()
    check(app)
    app.selectbox(key='comparison_mode').set_value('Automatic fair pair').run()
    app.selectbox(key='forecast_actual_station').set_value(3).run()
    check(app)
    assert any('No fair run pair' in i.value and '11.0 h' in i.value for i in app.info)
    assert any('inspection only' in c.value for c in app.caption)
    app.selectbox(key='forecast_actual_station').set_value(2).run()
    check(app)
    assert any('No stored' in x.value for x in app.info)
    app.selectbox(key='forecast_actual_station').set_value(1).run()
    app.selectbox(key='comparison_mode').set_value('Automatic fair pair').run()
    assert app.selectbox(key='met_run_1').value==2
    app.selectbox(key='forecast_variable').set_value('wind_speed').run()
    check(app)
    assert any('m/s' in m.value for m in app.metric)
    # AppTest does not serialize stateful tab selection between widget reruns.
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.run()
    check(app)
    assert next(m for m in app.metric if m.label=='Shared samples').value=='6'
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.selectbox(key='accuracy_variable').set_value('wind_speed').run()
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.selectbox(key='accuracy_period').set_value('24 h').run()
    check(app)
    assert any('m/s' in m.value for m in app.metric)
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.selectbox(key='accuracy_horizon').set_value('9d+').run()
    check(app)
    assert any('No shared' in x.value for x in app.info)
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.selectbox(key='accuracy_horizon').set_value('All buckets').run()
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.selectbox(key='accuracy_station').set_value(2).run()
    check(app)
    assert any('No shared' in x.value for x in app.info)
    app.session_state['dashboard_tabs']='Long-range temperature'
    app.run()
    check(app)
    long_table=next(d.value for d in app.dataframe if 'Ahead' in d.value.columns)
    assert long_table['Ahead'].tolist()==['3 days','5 days','7 days','9 days']
    assert long_table['Shared samples'].tolist()==[1,1,1,1]
    assert (long_table['Yr MAE °C']==2).all()
    assert any('Evaluation period (matched targets, UTC)' in c.value for c in app.caption)
    assert any('4 shared comparisons use verified historical forecasts' in c.value for c in app.caption)
    app.session_state['dashboard_tabs']='Long-range temperature'
    app.selectbox(key='long_range_station').set_value(2).run()
    check(app)
    assert any('No shared long-range' in i.value for i in app.info)
    empty=next(d.value for d in app.dataframe if 'Ahead' in d.value.columns)
    assert empty['Shared samples'].tolist()==[0,0,0,0]
    assert empty['Yr MAE °C'].isna().all()
    app.session_state['dashboard_tabs']='Long-range temperature'
    app.selectbox(key='long_range_station').set_value(None).run()
    app.session_state['dashboard_tabs']='Long-range temperature'
    app.selectbox(key='long_range_period').set_value('24 h').run()
    check(app)
    filtered=next(d.value for d in app.dataframe if 'Ahead' in d.value.columns)
    assert filtered['Shared samples'].iloc[:3].sum()==0
    app.session_state['dashboard_tabs']='Model disagreement'
    app.run()
    check(app)
    app.session_state['dashboard_tabs']='Model disagreement'
    app.selectbox(key='disagreement_variable').set_value('wind_speed').run()
    check(app)
    app.session_state['dashboard_tabs']='Model disagreement'
    next(b for b in app.button if b.label=='Inspect in Forecast vs Actual').click().run()
    check(app)
    assert app.selectbox(key='forecast_actual_station').value==1
    assert app.selectbox(key='forecast_variable').value=='wind_speed'
    assert app.selectbox(key='met_run_1').value==2
    assert app.selectbox(key='wn_run_1').value==3
    assert app.selectbox(key='comparison_mode').value=='Manual runs'
    app.selectbox(key='forecast_variable').set_value('precipitation_1h').run()
    app.selectbox(key='comparison_mode').set_value('Automatic fair pair').run()
    check(app)
    assert app.selectbox(key='met_run_1').value==202
    assert app.selectbox(key='wn_run_1').value==203
    assert any(m.label=='Yr event skill · CSI' for m in app.metric)
    assert any('2 shared samples' in c.value and 'Evaluation period' in c.value for c in app.caption)
    amounts=next(d.value for d in app.dataframe if 'Wet-hour MAE' in d.value.columns)
    assert abs(amounts.loc['Yr/MET','Wet-hour MAE']-0.2)<1e-9
    assert any('all-hour MAE can reward' in c.value for c in app.caption)
    assert any('Event skill · CSI %' in d.value.index for d in app.dataframe)
    app.selectbox(key='comparison_mode').set_value('Manual runs').run()
    app.selectbox(key='met_run_1').set_value(200).run()
    check(app)
    assert any('These manual runs' in i.value for i in app.info)
    assert any('No fair shared hourly precipitation' in i.value for i in app.info)
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.run()
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.selectbox(key='accuracy_variable').set_value('precipitation_1h').run()
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.selectbox(key='accuracy_station').set_value(None).run()
    check(app)
    assert app.selectbox(key='rain_horizon').value=='12–24h'
    assert any('2 shared samples' in c.value and '1 stations' in c.value for c in app.caption)
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.selectbox(key='rain_horizon').set_value('48–72h').run()
    check(app)
    assert any('partial coverage' in c.value and '54.0' in c.value and '52.0' in c.value for c in app.caption)
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.selectbox(key='rain_horizon').set_value('0–12h').run()
    check(app)
    assert any('0 shared samples' in c.value for c in app.caption)
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.selectbox(key='rain_horizon').set_value('12–24h').run()
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.selectbox(key='accuracy_station').set_value(2).run()
    check(app)
    assert any('No fair shared hourly precipitation' in i.value for i in app.info)
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.selectbox(key='accuracy_station').set_value(None).run()
    assert app.selectbox(key='rain_accumulation').value=='1h'
    for accumulation in ('6h','24h'):
        app.session_state['dashboard_tabs']='Overall accuracy'
        app.selectbox(key='rain_accumulation').set_value(accumulation).run()
        check(app)
        assert any('No fair shared complete' in i.value for i in app.info)
    app.session_state['dashboard_tabs']='Overall accuracy'
    app.selectbox(key='rain_horizon').set_value('All buckets').run()
    check(app)
    with database.connect() as con:
        assert before==list(con.iterdump()),'Dashboard changed fixture history'
    print('Expanded UI passed: automatic/manual/no-fair pairing, collapsed healthy state, resolved gaps, active Yr failures, verified retrospective horizons/periods/counts/empty filters, wind, shared accuracy filters/empty states, disagreement drill-through, zero DB writes; station/latest run, charts, run/window/station changes, future actuals hidden, collapsed admin, no DB writes.')
