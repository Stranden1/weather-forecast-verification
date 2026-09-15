"""Exercise dashboard interactions against fixture data and assert no DB writes."""
import sys
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
        before=list(con.iterdump())
    app=AppTest.from_file(str(root/'app.py'),default_timeout=30).run()
    check(app)
    assert [t.label for t in app.tabs][:3]==['Forecast vs Actual','Station network','Overall accuracy']
    assert app.selectbox(key='forecast_actual_station').value==1
    assert app.selectbox(key='met_run_1').value==2
    assert any(b.label=='Fetch WeatherNext' for b in app.button)
    admin=next(e for e in app.expander if e.label=='Admin / Manual controls')
    assert admin.proto.expanded is False
    assert next(m for m in app.metric if m.label=='Shared observed hours').value=='6'
    app.selectbox(key='met_run_1').set_value(1).run()
    check(app)
    assert app.selectbox(key='met_run_1').value==1
    next(s for s in app.selectbox if s.label=='Chart window').set_value('Full run').run()
    check(app)
    app.selectbox(key='forecast_actual_station').set_value(2).run()
    check(app)
    assert any('No stored' in x.value for x in app.info)
    with database.connect() as con:
        assert before==list(con.iterdump()),'Dashboard changed fixture history'
    print('UI passed: station/latest run, charts, run/window/station changes, future actuals hidden, collapsed admin, no DB writes.')
