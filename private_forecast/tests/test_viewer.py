import http.client
import json
import threading
import unittest
from datetime import datetime, timezone

import pandas as pd

from private_forecast.viewer import make_server, snapshot

NOW = datetime(2026, 10, 12, 14, tzinfo=timezone.utc)
STATIONS = [{"station_id": "SN1", "name": "One"}, {"station_id": "SN2", "name": "Two"}]


def row(provider, target="2026-10-12T17:00:00Z", **extra):
    return {"provider": provider, "station": "SN1", "fetched_at": "2026-10-12T13:00:00Z",
            "issued_at": "2026-10-12T12:00:00Z", "target": target,
            "t": 3, "p": .4, "p_p50": .1, **extra}


class SnapshotTests(unittest.TestCase):
    def test_shared_fetch_never_stitches_older_or_newer_single_provider(self):
        d = pd.DataFrame([row('yr'), row('wn'), row('yr', fetched_at='2026-10-12T13:30:00Z', t=9),
                          row('wn', '2026-10-12T18:00:00Z', fetched_at='2026-10-12T10:00:00Z')])
        data = snapshot(d, STATIONS, NOW)
        self.assertEqual(data['collected'], '2026-10-12T13:00:00Z')
        points = data['stations'][0]['points']
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]['yr']['t'], 3)
        self.assertEqual(data['stations'][1]['points'], [])

    def test_future_window_missing_counterpart_and_rain_end_time_preserved(self):
        d = pd.DataFrame([row('yr'), row('wn'), row('wn', '2026-10-12T23:00:00Z'),
                          row('wn', '2026-10-12T14:00:00Z'), row('yr', '2026-10-15T17:00:00Z')])
        data = snapshot(d, STATIONS, NOW)
        points = data['stations'][0]['points']
        self.assertEqual([p['time'] for p in points], ['2026-10-12T17:00:00Z','2026-10-12T23:00:00Z'])
        self.assertNotIn('yr', points[1])
        self.assertEqual(points[0]['wn']['p_p50'], .1)
        self.assertEqual(points[0]['wn']['p'], .4)

    def test_nonfinite_values_and_missing_issue_are_null(self):
        d = pd.DataFrame([row('yr', t=float('inf'), issued_at=None), row('wn', w=float('nan'))])
        data = snapshot(d, STATIONS, NOW)
        json.dumps(data, allow_nan=False)
        point = data['stations'][0]['points'][0]
        self.assertIsNone(point['yr']['t'])
        self.assertIsNone(point['yr']['issued'])
        self.assertIsNone(point['wn']['w'])

    def test_inactive_stations_ignored_and_input_unmodified(self):
        d = pd.DataFrame([row('yr'), row('wn'), row('wn', station='RETIRED', t=10)])
        before = d.copy(deep=True)
        snapshot(d, STATIONS, NOW)
        pd.testing.assert_frame_equal(d, before)

    def test_duplicate_and_no_shared_fetch_fail(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            snapshot(pd.DataFrame([row('yr'), row('wn'), row('wn')]), STATIONS, NOW)
        with self.assertRaisesRegex(ValueError, 'shared'):
            snapshot(pd.DataFrame([row('yr')]), STATIONS, NOW)


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.data = snapshot(pd.DataFrame([row('yr'), row('wn')]), STATIONS, NOW)
        self.server = make_server(lambda: self.data, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def get(self, path, **headers):
        conn = http.client.HTTPConnection(*self.server.server_address)
        conn.request('GET', path, headers=headers)
        response = conn.getresponse()
        body = response.read()
        result = response.status, dict(response.getheaders()), body
        conn.close()
        return result

    def test_loopback_api_no_cache_or_cross_origin_access(self):
        self.assertEqual(self.server.server_address[0], '127.0.0.1')
        status, headers, body = self.get('/api/forecasts')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        self.assertEqual(json.loads(body)['collected'], self.data['collected'])
        self.assertEqual(self.get('/api/forecasts', Origin='https://other.example')[0], 403)
        self.assertEqual(self.get('/api/forecasts', Host='other.example')[0], 403)

    def test_only_explicit_assets_served(self):
        for path in ('/.env', '/../.env', '/history/', '/viewer.py', '/%2e%2e/.env'):
            self.assertEqual(self.get(path)[0], 404)

    def test_loader_error_does_not_expose_exception(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        def fail():
            raise RuntimeError('EXAMPLE_SECRET_MUST_NOT_APPEAR')
        self.server = make_server(fail, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        status, _, body = self.get('/api/forecasts')
        self.assertEqual(status, 503)
        self.assertNotIn(b'EXAMPLE_SECRET', body)
