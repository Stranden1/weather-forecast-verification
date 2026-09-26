"""Working state is encrypted when WX_STATE_KEY is set; old plain files stay readable."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cryptography.fernet import Fernet

from cloud.store import FERNET_PREFIX, State

ROW = {"provider": "wn", "station": "SN1", "fetched_at": "2026-10-01T00:00:00Z",
       "issued_at": "2026-10-01T00:00:00Z", "target": "2026-10-02T00:00:00Z", "lead_h": 24, "t": 5.0}


class StateCryptoTest(unittest.TestCase):
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
