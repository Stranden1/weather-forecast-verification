"""Ephemeral encryption keys for tests; never read the user's .env."""
import os
from unittest.mock import patch

from cryptography.fernet import Fernet


def test_key():
    return patch.dict(os.environ, {"WX_STATE_KEY": Fernet.generate_key().decode()})
