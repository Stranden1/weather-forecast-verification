import gzip
import json
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet, InvalidToken

from cloud.archive import Capture, SUFFIX, read_object, write_object
from cloud.archive_policy import Slot, active_slot, closed_slots
from cloud.tests.crypto_fixture import test_key

UTC = timezone.utc
START = date(2026, 10, 14)
NOW = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)
STATIONS = [{"station_id": "SN1", "latitude": 60.123456, "longitude": 10.567891, "elevation_m": 20},
            {"station_id": "SN2", "latitude": 61.2, "longitude": 11.5, "elevation_m": None}]
# Preserve lexical precision as well as 1h/6h/12h fields, nulls and unknown future fields.
BODY = b'{"properties":{"meta":{"updated_at":"2026-10-14T08:45:00Z"},"timeseries":[{"time":"2026-10-14T09:00:00Z","data":{"instant":{"details":{"air_temperature":1.123456789123456789,"dew_point_temperature":null}},"next_1_hours":{"details":{"precipitation_amount":0.03}},"next_6_hours":{"details":{"precipitation_amount":1.23}},"next_12_hours":{"details":{"precipitation_amount":2.34}},"unknown":{"hello":true}}}]}}'


def metadata(at=NOW):
    return {"endpoint": "https://api.met.no/weatherapi/locationforecast/2.0/complete",
            "query": {"lat": 60.1235, "lon": 10.5679, "token": "private-query"},
            "request_started_at": at.isoformat(),
            "response_received_at": (at + timedelta(seconds=1)).isoformat(),
            "status": 200, "headers": {"Date": "Wed, 14 Oct 2026 09:00:00 GMT",
                                         "Authorization": "private-auth", "User-Agent": "private-contact",
                                         "Set-Cookie": "private-cookie"}}


class PolicyTest(unittest.TestCase):
    def test_boundaries_and_cross_midnight(self):
        for hour, minute, expected in [(8, 29, None), (8, 30, "am"), (12, 59, "am"),
                                        (13, 0, None), (20, 29, None), (20, 30, "pm")]:
            slot = active_slot(NOW.replace(hour=hour, minute=minute), START)
            self.assertEqual(slot.name if slot else None, expected)
        midnight = NOW.replace(day=15, hour=0, minute=30)
        self.assertEqual(active_slot(midnight, START), Slot(START, "pm"))
        self.assertIsNone(active_slot(midnight.replace(hour=1, minute=0), START))
        self.assertEqual(list(closed_slots(START, midnight.replace(hour=1, minute=0))),
                         [Slot(START, "am"), Slot(START, "pm")])

    def test_timezone_and_no_pre_activation_missing(self):
        oslo = timezone(timedelta(hours=2))
        self.assertEqual(active_slot(NOW.astimezone(oslo), START), Slot(START, "am"))
        self.assertIsNone(active_slot(NOW - timedelta(days=1), START))
        self.assertEqual(list(closed_slots(START, NOW)), [])
        with self.assertRaises(ValueError):
            active_slot(NOW.replace(tzinfo=None), START)


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        key = test_key(); key.start(); self.addCleanup(key.stop)
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "archive"

    def capture(self, now=NOW):
        return Capture(self.root, START, STATIONS, now)

    def test_full_response_roundtrip_and_secret_filter(self):
        c = self.capture()
        c.sink(STATIONS[0], BODY, metadata())
        path = c.station_path(c.slot, "SN1")
        obj = read_object(path)
        self.assertEqual(obj["response_json"].encode("utf-8"), BODY)
        self.assertEqual(obj["request"]["query"], {"lat": 60.1235, "lon": 10.5679})
        serialized = json.dumps(obj)
        self.assertNotIn("private-", serialized)
        self.assertEqual(set(obj["request"]["headers"]), {"date"})
        self.assertNotIn(BODY, path.read_bytes())
        self.assertEqual(obj["station"], STATIONS[0])

    def test_identical_write_reuses_bytes_conflict_never_replaces(self):
        p = self.root / ("object" + SUFFIX)
        original = {"schema_version": 1, "value": 1.123456789}
        write_object(p, original)
        before = p.read_bytes()
        write_object(p, original)
        self.assertEqual(p.read_bytes(), before)
        with self.assertRaises(ValueError):
            write_object(p, {**original, "value": 2})
        self.assertEqual(p.read_bytes(), before)

    def test_partial_retry_preserves_first_and_closes(self):
        first = self.capture()
        first.sink(STATIONS[0], BODY, metadata())
        summary = first.finish(NOW + timedelta(minutes=1))
        self.assertGreater(summary["errors"], 0)
        p = first.station_path(first.slot, "SN1"); original = p.read_bytes()
        later = NOW + timedelta(hours=3)
        second = self.capture(later)
        second.sink(STATIONS[0], BODY.replace(b'0.03', b'9.99'), metadata(later))
        second.sink(STATIONS[1], BODY, metadata(later))
        self.assertEqual(p.read_bytes(), original)
        second.finish(later + timedelta(minutes=1))
        closing = self.capture(NOW.replace(hour=13))
        result = closing.finish(NOW.replace(hour=13))
        self.assertEqual(result["incomplete_slots"], 0)
        manifest = read_object(closing.slot_path(first.slot) / ("manifest" + SUFFIX))
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(len(manifest["objects"]), 2)
        self.assertEqual(len(list(self.root.rglob("yr/*" + SUFFIX))), 2)

    def test_closed_missing_slots_are_immutable(self):
        at = NOW.replace(day=15, hour=2)
        c = self.capture(at)
        self.assertEqual(c.finish(at)["incomplete_slots"], 2)
        manifests = list(self.root.rglob("manifest" + SUFFIX))
        before = {p: p.read_bytes() for p in manifests}
        self.assertTrue(all(read_object(p)["status"] == "missing" for p in manifests))
        self.capture(at + timedelta(hours=1)).finish(at + timedelta(hours=1))
        self.assertEqual({p: p.read_bytes() for p in manifests}, before)
        with self.assertRaises(ValueError):
            self.capture()  # clock rollback cannot reopen a closed slot

    def test_late_receipt_never_fills_slot(self):
        at = NOW.replace(hour=12, minute=59, second=59)
        c = self.capture(at)
        c.sink(STATIONS[0], BODY, metadata(at))
        self.assertEqual(c.late, ["SN1"])
        self.assertFalse(c.station_path(c.slot, "SN1").exists())
        c.finish(NOW.replace(hour=13, minute=1))
        self.assertEqual(c.closed[0]["status"], "missing")

    def test_partial_closure_does_not_invent_missing_values(self):
        c = self.capture()
        c.sink(STATIONS[0], BODY, metadata())
        c.finish(NOW.replace(hour=13))
        m = c.closed[0]
        self.assertEqual(m["status"], "partial")
        self.assertEqual(m["missing_station_ids"], ["SN2"])

    def test_interrupted_attempt_can_be_finished_next_collection(self):
        c = self.capture()
        c.sink(STATIONS[0], BODY, metadata())
        # No finish: only the authenticated per-station object exists.
        later = self.capture(NOW + timedelta(hours=1))
        later.sink(STATIONS[1], BODY, metadata(NOW + timedelta(hours=1)))
        later.finish(NOW.replace(hour=13))
        self.assertEqual(later.closed[0]["status"], "complete")

    def test_sink_failure_is_sanitized_and_does_not_escape(self):
        c = self.capture()
        with patch("cloud.archive.write_object", side_effect=OSError("private-secret")):
            c.sink(STATIONS[0], BODY, metadata())
        self.assertEqual(c.errors, ["Yr archive: response capture failed"])

    def test_write_interruption_never_leaves_truncated_final_object(self):
        p = self.root / ("object" + SUFFIX)
        with patch("cloud.archive.os.link", side_effect=OSError("interrupt")):
            with self.assertRaises(OSError):
                write_object(p, {"schema_version": 1})
        self.assertFalse(p.exists())
        self.assertEqual(list(p.parent.glob("*.tmp")), [])

    def test_key_corruption_and_schema_fail_closed(self):
        p = self.root / ("object" + SUFFIX)
        write_object(p, {"schema_version": 1})
        for key in ("", Fernet.generate_key().decode()):
            with patch.dict(os.environ, {"WX_STATE_KEY": key}):
                with self.assertRaises((RuntimeError, InvalidToken)):
                    read_object(p)
        original = p.read_bytes(); p.write_bytes(original[:-4] + b"oops")
        with self.assertRaises(InvalidToken):
            read_object(p)
        f = Fernet(os.environ["WX_STATE_KEY"].encode())
        p.write_bytes(f.encrypt(gzip.compress(b'{"schema_version":99}')))
        with self.assertRaises(ValueError):
            read_object(p)
        p.write_bytes(f.encrypt(b"not gzip"))
        with self.assertRaises(gzip.BadGzipFile):
            read_object(p)

    def test_policy_and_network_changes_fail_closed(self):
        self.capture()
        with self.assertRaises(ValueError):
            Capture(self.root, START - timedelta(days=1), STATIONS, NOW)
        with self.assertRaises(ValueError):
            Capture(self.root, START, STATIONS[:1], NOW)

    def test_no_capture_outside_windows_and_unknown_station_rejected(self):
        c = self.capture(NOW.replace(hour=14))
        c.sink(STATIONS[0], BODY, metadata(NOW.replace(hour=14)))
        self.assertEqual(c.received, [])
        c = self.capture()
        c.sink({"station_id": "other"}, BODY, metadata())
        self.assertEqual(len(c.errors), 1)
