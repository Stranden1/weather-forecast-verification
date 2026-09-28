"""Working state is encrypted when WX_STATE_KEY is set; old plain files stay readable."""
import os
import gzip
from datetime import date
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cryptography.fernet import Fernet

import pandas as pd
from cloud.store import FERNET_PREFIX, State, load_scored, write_scored
from cloud.history_crypto import encrypt_history
from cloud.tests.crypto_fixture import test_key

ROW = {"provider": "wn", "station": "SN1", "fetched_at": "2026-10-01T00:00:00Z",
       "issued_at": "2026-10-01T00:00:00Z", "target": "2026-10-02T00:00:00Z", "lead_h": 24, "t": 5.0}


class StateCryptoTest(unittest.TestCase):
    def test_history_conversion_preserves_exact_bytes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp, test_key():
            root = Path(tmp)
            path = root / "2026" / "2026-09-27.csv.gz"
            path.parent.mkdir()
            original = gzip.compress(b"station,wn_t\nSN1,1.234567890\n")
            path.write_bytes(original)
            self.assertEqual(encrypt_history(root), 1)
            encrypted = path.read_bytes()
            self.assertEqual(Fernet(os.environ["WX_STATE_KEY"].encode()).decrypt(encrypted), original)
            self.assertAlmostEqual(load_scored(root).iloc[0].wn_t, 1.23456789)
            self.assertEqual(encrypt_history(root), 0)
            self.assertEqual(path.read_bytes(), encrypted)

    def test_history_requires_key_and_wrong_key_cannot_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.dict(os.environ, {"WX_STATE_KEY": ""}):
                with self.assertRaises(RuntimeError):
                    write_scored(date(2026, 9, 27), pd.DataFrame([{"station": "SN1", "wn_t": 2}]), root)
                self.assertEqual(list(root.rglob("*.gz")), [])
            with test_key():
                path = write_scored(date(2026, 9, 27), pd.DataFrame([{"station": "SN1", "wn_t": 2}]), root)
                self.assertTrue(path.read_bytes().startswith(FERNET_PREFIX))
            with test_key(), self.assertRaises(Exception):
                load_scored(root)

    def test_plain_then_encrypted(self):
        key = Fernet.generate_key().decode()
        with tempfile.TemporaryDirectory() as tmp:
            st = State(Path(tmp))
            with mock.patch.dict(os.environ, {"WX_STATE_KEY": ""}):
                st.add_pending([ROW])                      # old behaviour: plain gzip
            self.assertFalse(st.pending_path.read_bytes().startswith(FERNET_PREFIX))
            with mock.patch.dict(os.environ, {"WX_STATE_KEY": key}):
                self.assertEqual(len(st.pending()), 1)     # plain file still readable
                st.add_pending([dict(ROW, station="SN2")])  # now written encrypted
                self.assertTrue(st.pending_path.read_bytes().startswith(FERNET_PREFIX))
                self.assertEqual(sorted(st.pending().station), ["SN1", "SN2"])
                st.add_obs([{"station": "SN1", "time": "2026-10-01T00:00:00Z", "t": 1.0}])
                self.assertTrue(st.obs_path.read_bytes().startswith(FERNET_PREFIX))
            with mock.patch.dict(os.environ, {"WX_STATE_KEY": ""}):
                with self.assertRaises(RuntimeError):      # never silently start empty
                    st.pending()


if __name__ == "__main__":
    unittest.main()
