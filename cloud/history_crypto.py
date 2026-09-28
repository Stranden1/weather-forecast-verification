"""Encrypt existing day files without changing their original compressed bytes.

Local decrypt writes only to ignored outputs/, never to history/ or site/.
"""
from __future__ import annotations

import argparse
import gzip
from pathlib import Path

from .config import ROOT, SCORED_DIR
from .store import FERNET_PREFIX, _fernet, atomic_bytes, plaintext_bytes, read_scored


def encrypt_history(root: Path = SCORED_DIR) -> int:
    f = _fernet(required=True)
    files = sorted(Path(root).glob("*/*.csv.gz"))
    # Preflight every file before converting any; a wrong key aborts the whole pass.
    for path in files:
        gzip.decompress(plaintext_bytes(path.read_bytes()))
        read_scored(path)
    changed = 0
    for path in files:
        original = path.read_bytes()
        if original.startswith(FERNET_PREFIX):
            continue
        encrypted = f.encrypt(original)
        if f.decrypt(encrypted) != original:
            raise RuntimeError("History encryption round-trip failed")
        atomic_bytes(path, encrypted)
        changed += 1
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["encrypt", "decrypt", "verify"])
    parser.add_argument("--env-file", type=Path, help="Load a local .env without printing secrets")
    parser.add_argument("--root", type=Path, default=SCORED_DIR)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "decrypted-history")
    args = parser.parse_args(argv)
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file, override=False)
    _fernet(required=True)
    if args.action == "encrypt":
        print(f"Encrypted {encrypt_history(args.root)} day files; original gzip bytes preserved.")
        return
    files = sorted(args.root.glob("*/*.csv.gz"))
    for path in files:
        if not path.read_bytes().startswith(FERNET_PREFIX):
            raise RuntimeError(f"Unencrypted history: {path.name}")
        read_scored(path)  # authentication + gzip/CSV validation
    if args.action == "verify":
        print(f"Verified {len(files)} encrypted day files.")
        return
    out = args.out.resolve()
    if not out.is_relative_to((ROOT / "outputs").resolve()):
        raise ValueError("Decrypted copies must stay inside the ignored outputs/ directory")
    targets = [(p, out / p.relative_to(args.root)) for p in files]
    if any(dest.exists() for _, dest in targets):
        raise FileExistsError("Choose a fresh outputs/ subdirectory; existing copies are not overwritten")
    for path, dest in targets:
        atomic_bytes(dest, plaintext_bytes(path.read_bytes()))
    print(f"Decrypted {len(files)} local copies into {out}; do not publish them.")


if __name__ == "__main__":
    main()
