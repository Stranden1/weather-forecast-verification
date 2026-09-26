"""Model-cell height vs station height, for the height-adjusted WeatherNext line.

WeatherNext's station-head temperature is valid at the terrain height of its grid
cell, not at our station (INVESTIGATION_COLD_BIAS_2026-09-26.md). Google does not
publish its grid heights, so the cell height here is the GMTED2010 mean over the
0.05° cell (the elevation model the paper names), read the same way each sampling
method reads temperature:

- `nn5km`: the cell the old scale=5000 sampling returned (sometimes a neighbour),
- `bilinear`: the four surrounding cells, bilinearly weighted.

    python -m cloud.heights     # read-only Earth Engine queries; rewrites config/wn_heights.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import ROOT, WN_SAMPLING, WN_SAMPLING_OLD, load_stations

HEIGHTS_FILE = ROOT / "config" / "wn_heights.json"
LAPSE_C_PER_KM = 6.5
FLAG_DZ_M = 100
# Stations whose cold bias is mostly NOT explained by height (night-time warmth the
# 5 km grid cannot resolve). From the 2026-09-26 investigation, not computed.
NOTES = {
    "SN12590": "Next to Lake Mjøsa, which keeps nights warmer than the model's cell.",
    "SN63420": "At sea level at a fjord head; nights are warmer than the model's cell.",
    "SN18700": "In the city; urban warmth at night is not in the model's cell.",
}
T_COLLECTION = "projects/gcp-public-data-weathernext/assets/weathernext_3_0_0_0p05deg"


def load_heights(path: Path = HEIGHTS_FILE) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"stations": {}}


def height_diff(station: str, sampling: str | None, heights: dict) -> float | None:
    """Model cell height minus station height (m) for one sampling method.

    None for offshore stations, unknown stations or missing heights.
    """
    s = heights.get("stations", {}).get(station)
    if not s or s.get("offshore") or s.get("elev") is None:
        return None
    key = "cell_bilinear" if sampling == WN_SAMPLING else "cell_nn5km"
    cell = s.get(key)
    return None if cell is None else cell - s["elev"]


def adjusted_t(df: pd.DataFrame, heights: dict, column: str = "wn_t") -> pd.Series:
    """WeatherNext temperature moved from the cell's height to the station's height.

    Standard lapse rate, no fitted parameters. Rows without a known height
    difference (offshore, unknown) keep the published value, so no station is lost.
    """
    sampling = df["wn_sampling"] if "wn_sampling" in df else pd.Series(np.nan, index=df.index)
    sampling = sampling.where(sampling.notna(), WN_SAMPLING_OLD)
    dz = pd.Series([height_diff(s, m, heights) for s, m in zip(df["station"], sampling)],
                   index=df.index, dtype=float).fillna(0.0)
    return pd.to_numeric(df[column], errors="coerce") + LAPSE_C_PER_KM / 1000 * dz


def flags(heights: dict) -> dict[str, dict]:
    """Page flags: a large height difference under either sampling method, and notes.

    `dz` is for the current (bilinear) sampling, `dz_old` for the earlier method,
    which most of the history still uses.
    """
    out = {}
    for sid, s in heights.get("stations", {}).items():
        dz = height_diff(sid, WN_SAMPLING, heights)
        old = height_diff(sid, WN_SAMPLING_OLD, heights)
        f = {}
        if dz is not None and max(abs(dz), abs(old or 0)) >= FLAG_DZ_M:
            f["dz"] = round(dz)
            f["expected"] = round(-LAPSE_C_PER_KM / 1000 * dz, 1)
            f["dz_old"] = round(old) if old is not None else None
        if s.get("note"):
            f["note"] = s["note"]
        if f:
            out[sid] = f
    return out


def compute(stations=None) -> dict:
    """Read-only Earth Engine queries for every active station."""
    from .weathernext import EarthEngineSource
    ee = EarthEngineSource().ee  # EARTH_ENGINE_PROJECT / EE_SERVICE_ACCOUNT_KEY, as the collector
    stations = stations or load_stations()
    col = ee.ImageCollection(T_COLLECTION)
    proj = ee.Image(col.first()).projection()
    gm = ee.Image("USGS/GMTED2010_FULL").select("mea")
    cell = gm.reduceResolution(ee.Reducer.mean(), maxPixels=4096).reproject(proj).rename("cell")
    pts = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([s["longitude"], s["latitude"]]),
                                           {"station": s["station_id"]}) for s in stations])

    def read(image, **kw):
        fc = image.addBands(ee.Image.constant(0).rename("pad")).reduceRegions(
            collection=pts, reducer=ee.Reducer.first(), tileScale=4, **kw).getInfo()
        return {f["properties"]["station"]: f["properties"] for f in fc["features"]}

    old = read(cell, scale=5000)                          # the old collector's reading
    bil = read(cell.resample("bilinear"), scale=100)      # the new collector's reading
    point = read(gm.rename("point"), scale=250)           # terrain at the station itself
    out = {}
    for s in stations:
        sid = s["station_id"]
        c_old, c_bil, p = old[sid].get("cell"), bil[sid].get("cell"), point[sid].get("point")
        offshore = (p == 0 and c_old == 0) or s.get("elevation_m") is None
        row = {"name": s.get("name") or s.get("station_name"), "elev": s.get("elevation_m"),
               "cell_nn5km": _r(c_old), "cell_bilinear": _r(c_bil), "terrain_at_point": _r(p),
               "offshore": bool(offshore)}
        if sid in NOTES:
            row["note"] = NOTES[sid]
        out[sid] = row
    return {
        "description": "WeatherNext model-cell height (GMTED2010 mean over the 0.05 degree cell) per "
                       "station and sampling method. See cloud/heights.py and DECISIONS.md.",
        "lapse_c_per_km": LAPSE_C_PER_KM,
        "stations": out,
    }


def _r(x):
    return None if x is None else round(float(x), 1)


def main():
    data = compute()
    HEIGHTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {HEIGHTS_FILE} ({len(data['stations'])} stations)")
    for sid, f in flags(data).items():
        print(sid, data["stations"][sid]["name"], f)


if __name__ == "__main__":
    main()
