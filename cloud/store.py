"""Small file-based storage: working state plus permanent daily score files."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from .config import OBS_COLUMNS, PENDING_COLUMNS, SCORED_DIR, STATE_DIR


def _read(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    df = pd.read_csv(path, dtype={"station": str, "provider": str})
    for c in columns:
        if c not in df:
            df[c] = pd.NA
    return df[columns]


def _write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False, float_format="%.3f", compression="gzip")
    tmp.replace(path)  # atomic: a crash never leaves half a file


class State:
    def __init__(self, root: Path = STATE_DIR):
        self.root = Path(root)
        self.pending_path = self.root / "pending.csv.gz"
        self.obs_path = self.root / "obs.csv.gz"
        self.meta_path = self.root / "meta.json"

    def pending(self) -> pd.DataFrame:
        return _read(self.pending_path, PENDING_COLUMNS)

    def obs(self) -> pd.DataFrame:
        return _read(self.obs_path, OBS_COLUMNS)

    def meta(self) -> dict:
        if self.meta_path.exists():
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        return {"finalized_days": [], "first_fetch": None, "runs": []}

    def add_pending(self, rows: list[dict]) -> int:
        if not rows:
            return 0
        new = pd.DataFrame(rows).reindex(columns=PENDING_COLUMNS)
        df = pd.concat([self.pending(), new], ignore_index=True)
        # Re-running the same fetch never duplicates rows.
        df = df.drop_duplicates(["provider", "station", "fetched_at", "target"], keep="first")
        _write(df, self.pending_path)
        return len(new)

    def add_obs(self, rows: list[dict]) -> int:
        if not rows:
            return 0
        new = pd.DataFrame(rows).reindex(columns=OBS_COLUMNS)
        df = pd.concat([self.obs(), new], ignore_index=True)
        # Newest delivery wins for the same station/hour, but never erase a value.
        df = df.groupby(["station", "time"], as_index=False).agg(
            {c: "last" for c in ("t", "w", "p")})
        _write(df, self.obs_path)
        return len(new)

    def replace_pending(self, df: pd.DataFrame) -> None:
        _write(df, self.pending_path)

    def replace_obs(self, df: pd.DataFrame) -> None:
        _write(df, self.obs_path)

    def save_meta(self, meta: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        meta["runs"] = meta.get("runs", [])[-60:]
        self.meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")


def scored_path(day: date, root: Path = SCORED_DIR) -> Path:
    return Path(root) / f"{day:%Y}" / f"{day:%Y-%m-%d}.csv.gz"


def write_scored(day: date, df: pd.DataFrame, root: Path = SCORED_DIR) -> Path:
    path = scored_path(day, root)
    if path.exists():
        raise FileExistsError(f"{path} already exists; scored days are written once")
    _write(df, path)
    return path


def load_scored(root: Path = SCORED_DIR) -> pd.DataFrame:
    files = sorted(Path(root).glob("*/*.csv.gz"))
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(f, dtype={"station": str}) for f in files], ignore_index=True)
