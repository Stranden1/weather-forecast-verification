"""Generate clearly-labelled DEMO site data to preview the webpage layout.

    python -m cloud.demo site/data_demo
Never mix this with real data: the page shows a 'Demo data' banner.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .config import HORIZONS, load_stations
from .summarize import build


def fake_scored(days=45, seed=3):
    rng = np.random.default_rng(seed)
    stations = load_stations()
    rows = []
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    for d in range(days):
        shift = rng.normal(0, 0.4)
        for hr in range(24):
            t = start + timedelta(days=d, hours=hr)
            for s in stations:
                elev = s.get("elevation_m") or 100
                for h in HORIZONS:
                    if h > 48 and hr % 6:
                        continue
                    obs = 12 - d * 0.2 - elev / 150 + 4 * np.sin((hr - 9) / 24 * 6.283) + rng.normal()
                    e_yr = 0.8 + h / 90 + elev / 2000
                    e_wn = 1.0 + h / 110 + elev / 1500
                    y, w = obs + rng.normal(shift, e_yr), obs + rng.normal(shift * 0.8, e_wn)
                    ow = max(0, rng.gamma(2, 1.8))
                    rain = rng.random() < 0.15
                    op = rng.gamma(1.2, 1.0) if rain else 0.0
                    row = dict(target=t.strftime("%Y-%m-%dT%H:%M:%SZ"), station=s["station_id"], h=h, lead_h=h,
                               obs_t=obs, yr_t=y, yr_t_p10=y - 1.3 * e_yr, yr_t_p90=y + 1.3 * e_yr,
                               wn_t=w, wn_t_p50=w + rng.normal(0, .2), wn_t_p10=w - 1.1 * e_wn, wn_t_p90=w + 1.1 * e_wn,
                               obs_w=ow, yr_w=max(0, ow + rng.normal(0.3, 1 + h / 150)),
                               wn_w=max(0, ow + rng.normal(-0.2, 0.9 + h / 120)), wn_w_p50=max(0, ow + rng.normal(-0.3, 1)),
                               yr_w_p10=max(0, ow - 2), yr_w_p90=ow + 2, wn_w_p10=max(0, ow - 1.5), wn_w_p90=ow + 1.5)
                    if h <= 48:
                        row.update(obs_p=op, yr_p=max(0, op * rng.uniform(.3, 1.3) + (rng.random() < .1) * rng.gamma(1, .5)),
                                   wn_p=max(0, op * rng.uniform(.5, 1.1) + rng.gamma(1, .15)),
                                   wn_p_p50=max(0, op * rng.uniform(.3, 1)))
                    rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "site/data_demo")
    build(fake_scored(), out, publish_values=True)
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    meta["demo"] = True
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print("demo data written to", out)
