/* Yr vs WeatherNext scorecard. Reads the small JSON files in data/. */
(() => {
  // ?demo previews the made-up data from `python -m cloud.demo` (never deployed).
  const DATA = window.WX_DATA_BASE || (new URLSearchParams(location.search).has("demo") ? "data_demo/" : "data/");
  const SOURCE_NAME = { yr: "Yr", frost: "Frost", wn: "WeatherNext" };
  const SOURCE_STATUS = {
    ok: "✓", partial: "partly working", error: "failed", no_data: "no new data",
    no_access: "waiting for access", paused: "paused",
  };
  const STALE_H = 9; // runs are every 6 h; allow for GitHub's schedule delays
  const H_LABEL = { 6: "6 h", 12: "12 h", 24: "1 day", 48: "2 days", 72: "3 days", 120: "5 days", 168: "7 days", 240: "10 days" };
  const VERDICT = {
    yr: ["Yr is ahead", "yr"], weathernext: ["WeatherNext is ahead", "wn"],
    too_close: ["Too close to call", ""], not_enough_data: ["Not enough days yet", ""],
  };
  const S = { v: "t", period: "all", trendH: 24, mapH: 24, patH: 24, station: null };
  let D = {}, charts = {}, map, markers = [];

  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const fmt = (x, d = 2) => x == null ? "–" : Number(x).toFixed(d);
  // Skill 0.36 -> "36% better", -0.12 -> "12% worse" (than the naive guess).
  const skillPct = x => { if (x == null) return "–"; const p = Math.round(Math.abs(x) * 100);
    return p === 0 ? "same" : `${p}% ${x > 0 ? "better" : "worse"}`; };
  const skillSentence = x => skillPct(x) === "same" ? "About the same as a naive guess" : `${skillPct(x)} than a naive guess`;
  const unit = () => D.meta.variables[S.v].unit;
  const hs = () => (S.v === "p" ? D.meta.precip_horizons : D.meta.horizons);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  async function load() {
    const names = ["meta", "leaderboard", "trend", "stations", "calibration", "patterns", "rain", "health"];
    const got = await Promise.all(names.map(n => fetch(DATA + n + ".json").then(r => r.ok ? r.json() : {}).catch(() => ({}))));
    names.forEach((n, i) => (D[n] = got[i]));
  }

  function seg(el, items, get, set) {
    el.innerHTML = items.map(([v, l]) => `<button data-v="${v}" aria-pressed="${v === get()}">${l}</button>`).join("");
    el.onclick = e => {
      const b = e.target.closest("button"); if (!b) return;
      set(b.dataset.v);
      [...el.children].forEach(c => c.setAttribute("aria-pressed", c === b));
      render();
    };
  }
  function hSelect(id, key) {
    const el = document.getElementById(id);
    const opts = hs();
    if (!opts.includes(S[key])) S[key] = opts.includes(24) ? 24 : opts[0];
    el.innerHTML = opts.map(h => `<option value="${h}" ${h === S[key] ? "selected" : ""}>${H_LABEL[h]}</option>`).join("");
    el.onchange = () => { S[key] = +el.value; render(); };
  }

  function baseOptions(yTitle) {
    const ink2 = css("--ink-2"), grid = css("--grid");
    return {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "top", align: "start", labels: { color: ink2, boxWidth: 14, boxHeight: 3, usePointStyle: false } },
        tooltip: { callbacks: { label: c => ` ${c.dataset.label}: ${fmt(c.parsed.y)} ${unit()}` } },
      },
      scales: {
        x: { ticks: { color: ink2 }, grid: { display: false }, border: { color: css("--line") } },
        y: { beginAtZero: true, ticks: { color: ink2 }, grid: { color: grid }, border: { display: false },
             title: { display: true, text: yTitle, color: ink2 } },
      },
    };
  }
  function line(label, data, color, extra = {}) {
    return { label, data, borderColor: color, backgroundColor: color, borderWidth: 2, pointRadius: 4,
             pointHoverRadius: 6, spanGaps: true, tension: 0.2, ...extra };
  }
  function chart(id, config) {
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(document.getElementById(id), config);
  }

  function renderTiles() {
    const h = hs().includes(24) ? 24 : hs()[0];
    const s = D.leaderboard?.[S.v]?.[h]?.[S.period];
    const el = document.getElementById("tiles");
    if (!s || !s.n) { el.innerHTML = `<div class="tile empty" style="grid-column:1/-1">No scored forecasts yet for this selection.</div>`; return; }
    const [vt, cls] = VERDICT[s.verdict] || VERDICT.not_enough_data;
    const ci = s.ci_lo != null ? `95% range of the difference: ${fmt(s.ci_lo)} to ${fmt(s.ci_hi)} ${unit()}` :
      `A verdict needs at least ${D.meta.min_days_for_verdict} days of data`;
    const skill = p => s.base?.[`skill_${p}`] == null ? "" :
      `<div class="d">${skillSentence(s.base[`skill_${p}`])} (naive error ${fmt(s.base.mae)} ${unit()})</div>`;
    el.innerHTML = `
      <div class="tile"><p class="k"><span class="dot yr"></span>Yr · 1 day ahead</p>
        <div class="v">${fmt(s.mae_yr)} <small>${unit()} avg. error</small></div>
        <div class="d">Bias ${fmt(s.bias_yr)} ${unit()} (positive = forecast too high)</div>${skill("yr")}</div>
      <div class="tile"><p class="k"><span class="dot wn"></span>WeatherNext · 1 day ahead</p>
        <div class="v">${fmt(s.mae_wn)} <small>${unit()} avg. error</small></div>
        <div class="d">Bias ${fmt(s.bias_wn)} ${unit()} · median version ${fmt(s.mae_wn50)}</div>${skill("wn")}</div>
      <div class="tile"><p class="k">Verdict · ${s.days} days, ${s.n.toLocaleString()} forecasts</p>
        <div class="v" style="font-size:24px"><span class="badge ${cls}" style="font-size:15px">${vt}</span></div>
        <div class="d">${ci}</div></div>`;
  }

  function renderHorizon() {
    const b = D.leaderboard?.[S.v] || {};
    const H = hs().filter(h => b[h]?.[S.period]?.n);
    const g = k => H.map(h => b[h][S.period][k]);
    const base = H.map(h => b[h][S.period].base?.mae ?? null);
    const o = baseOptions(`Average error (${unit()})`);
    const ds = [
      line("Yr", g("mae_yr"), css("--yr")),
      line("WeatherNext (average)", g("mae_wn"), css("--wn")),
      line("WeatherNext (median)", g("mae_wn50"), css("--wn"), { borderDash: [5, 4], pointStyle: "rectRot", pointRadius: 4, backgroundColor: css("--surface") }),
    ];
    if (base.some(x => x != null))
      ds.push(line("Naive guess (same as before)", base, css("--ink-3"), { borderDash: [2, 3], pointStyle: "rect", pointRadius: 3 }));
    chart("horizon-chart", { type: "line", options: o, data: { labels: H.map(h => H_LABEL[h]), datasets: ds } });
    document.getElementById("horizon-table").innerHTML = `<div class="table-scroll"><table>
      <tr><th>Ahead</th><th>Yr</th><th>WeatherNext</th><th>Median</th><th>Difference</th><th>95% range</th><th>Verdict</th>
        <th>Naive guess</th><th>Yr vs naive</th><th>WeatherNext vs naive</th></tr>
      ${H.map(h => { const s = b[h][S.period]; const [vt, cls] = VERDICT[s.verdict] || VERDICT.not_enough_data;
        return `<tr><td>${H_LABEL[h]}</td><td>${fmt(s.mae_yr)}</td><td>${fmt(s.mae_wn)}</td><td>${fmt(s.mae_wn50)}</td>
        <td>${fmt(s.diff)}</td><td>${s.ci_lo == null ? "–" : fmt(s.ci_lo) + " to " + fmt(s.ci_hi)}</td>
        <td><span class="badge ${cls}">${vt}</span></td>
        <td>${fmt(s.base?.mae)}</td><td>${skillPct(s.base?.skill_yr)}</td><td>${skillPct(s.base?.skill_wn)}</td></tr>`; }).join("")}
      </table></div><p class="muted" style="font-size:13px">Difference = WeatherNext error − Yr error, in ${unit()}. Negative means WeatherNext was closer.
      Naive guess = the value measured at the same time of day on the latest day already known when the forecast was made.
      "36% better" means the forecast's average error was 36% smaller than the naive guess's, counting only forecasts that have a naive value.</p>`;
  }

  function rolling(arr, k = 7) {
    return arr.map((_, i) => { const w = arr.slice(Math.max(0, i - k + 1), i + 1).filter(x => x != null);
      return w.length >= Math.min(k, 3) ? w.reduce((a, b) => a + b, 0) / w.length : null; });
  }
  function renderTrend() {
    hSelect("trend-h", "trendH");
    let t = D.trend?.[S.v]?.[S.trendH] || [];
    if (S.period === "last30") t = t.slice(-30);
    const yr = t.map(r => r.yr), wn = t.map(r => r.wn);
    const faint = c => c + "55";
    chart("trend-chart", { type: "line", options: baseOptions(`Average error (${unit()})`), data: {
      labels: t.map(r => r.day.slice(5)), datasets: [
        line("Yr, 7-day", rolling(yr), css("--yr"), { pointRadius: 0 }),
        line("WeatherNext, 7-day", rolling(wn), css("--wn"), { pointRadius: 0 }),
        line("Yr, daily", yr, faint(css("--yr")), { borderWidth: 0, pointRadius: 3, showLine: false }),
        line("WeatherNext, daily", wn, faint(css("--wn")), { borderWidth: 0, pointRadius: 3, showLine: false }),
      ] } });
  }

  function mix(a, b, t) { // hex blend for the diverging scale
    const p = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
    const [x, y] = [p(a), p(b)];
    return "#" + x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, "0")).join("");
  }
  function renderMap() {
    hSelect("map-h", "mapH");
    const st = D.stations?.[S.v]?.[S.mapH] || {};
    if (!map) {
      map = L.map("map", { scrollWheelZoom: false }).setView([64.5, 13], 4);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        { maxZoom: 10, attribution: "© OpenStreetMap contributors" }).addTo(map);
    }
    markers.forEach(m => m.remove()); markers = [];
    const neutral = css("--neutral"), yr = css("--yr"), wn = css("--wn");
    // Colour strength relative to the largest station difference (min 0.1 unit).
    const scale = Math.max(0.1, ...Object.values(st).filter(r => r.yr != null && r.wn != null)
      .map(r => Math.abs(r.wn - r.yr)));
    for (const s of D.meta.stations) {
      const r = st[s.id];
      let color = neutral, tip = `${esc(s.name)}<br>No data yet`;
      if (r && r.yr != null && r.wn != null) {
        const d = r.wn - r.yr, t = Math.min(1, Math.abs(d) / scale);
        color = d > 0 ? mix(neutral, yr, t) : mix(neutral, wn, t);
        tip = `<b>${esc(s.name)}</b><br>Yr ${fmt(r.yr)} · WeatherNext ${fmt(r.wn)} ${unit()}<br>${r.n} forecasts`;
      }
      const m = L.circleMarker([s.lat, s.lon], { radius: 8, weight: 2, color: css("--surface"), fillColor: color, fillOpacity: 1 })
        .bindTooltip(tip).on("click", () => { S.station = s.id; renderStation(); }).addTo(map);
      markers.push(m);
    }
    renderStation();
  }

  async function renderStation() {
    const el = document.getElementById("station-panel");
    const s = D.meta.stations.find(x => x.id === S.station);
    if (!s) return;
    const st = D.stations?.[S.v]?.[S.mapH]?.[s.id];
    let rec = null;
    try { rec = await fetch(`${DATA}recent/${s.id}.json`).then(r => r.ok ? r.json() : null); } catch (e) {}
    el.innerHTML = `<h3>${esc(s.name)}</h3>
      <p class="muted" style="margin:0 0 8px;font-size:14px">${s.elev != null ? Math.round(s.elev) + " m above sea level · " : ""}${esc(s.county || "")}</p>
      <p style="margin:0 0 12px;font-size:14px">Average error ${H_LABEL[S.mapH]} ahead: <b>Yr ${fmt(st?.yr)}</b> · <b>WeatherNext ${fmt(st?.wn)}</b> ${unit()}</p>
      <p class="muted" style="margin:0 0 4px;font-size:13px">Last 7 days: forecast made 1 day ahead vs what happened</p>
      <div class="chart"><canvas id="station-chart"></canvas></div>
      ${D.meta.publish_forecast_values ? "" : `<p class="muted" style="font-size:12px">WeatherNext's raw values are hidden until its data terms are confirmed; its errors are included in every score.</p>`}`;
    if (!rec) { el.querySelector(".chart").innerHTML = `<p class="empty">No recent data.</p>`; return; }
    const ds = [line("Measured", rec[`obs_${S.v}`], css("--obs"), { pointRadius: 0, borderWidth: 2 }),
                line("Yr", rec[`yr_${S.v}`], css("--yr"), { pointRadius: 0 })];
    if (rec[`wn_${S.v}`]) ds.push(line("WeatherNext", rec[`wn_${S.v}`], css("--wn"), { pointRadius: 0 }));
    const o = baseOptions(unit()); o.scales.y.beginAtZero = S.v !== "t";
    o.scales.x.ticks.maxTicksLimit = 7;
    chart("station-chart", { type: "line", options: o, data: {
      labels: rec.time.map(t => t.slice(5, 10) + " " + t.slice(11, 13) + "h"), datasets: ds } });
  }

  function renderPatterns() {
    hSelect("pat-h", "patH");
    document.getElementById("pat-h-label").textContent = H_LABEL[S.patH];
    const rows = D.patterns?.[S.v]?.[S.patH] || [];
    const bar = (x, max, c) => x == null ? "" :
      `<span style="display:inline-block;height:8px;width:${Math.max(2, 80 * x / max)}px;background:var(${c});border-radius:0 4px 4px 0;vertical-align:middle;margin-left:6px"></span>`;
    const max = Math.max(...rows.flatMap(r => [r.mae_yr || 0, r.mae_wn || 0]), 0.01);
    document.getElementById("patterns").innerHTML = rows.length ? `<div class="table-scroll"><table>
      <tr><th>Situation</th><th>Forecasts</th><th>Yr error</th><th>WeatherNext error</th><th>Difference</th></tr>
      ${rows.map(r => `<tr><td>${esc(r.label)}</td><td>${r.n.toLocaleString()}</td>
        <td>${fmt(r.mae_yr)}${bar(r.mae_yr, max, "--yr")}</td><td>${fmt(r.mae_wn)}${bar(r.mae_wn, max, "--wn")}</td>
        <td>${fmt(r.diff)}</td></tr>`).join("")}</table></div>` : `<p class="empty">No data yet.</p>`;

    const cal = D.calibration?.[S.v]?.[S.patH];
    document.querySelector(".two").style.gridTemplateColumns = S.v === "p" ? "1fr" : "";
    document.getElementById("calibration").hidden = S.v === "p";
    document.getElementById("calibration").innerHTML = S.v === "p" ? "" : `<h3>Honest about uncertainty?</h3>
      <p class="sub" style="font-size:14px">Both services give a likely range (10th to 90th percentile).
      The measurement should land inside it about 80% of the time.</p>
      ${cal && (cal.yr || cal.wn) ? `<div class="table-scroll"><table><tr><th>Service</th><th>Inside range</th><th>Range score</th><th>Avg. width</th><th>Forecasts</th></tr>
        ${["yr", "wn"].filter(p => cal[p]).map(p => `<tr><td><span class="dot ${p}"></span> ${p === "yr" ? "Yr" : "WeatherNext"}</td>
        <td>${Math.round(cal[p].inside * 100)}%</td><td>${fmt(cal.q?.[p]?.pinball)}</td>
        <td>${cal.q?.[p]?.width == null ? "–" : fmt(cal.q[p].width, 1) + " " + unit()}</td>
        <td>${cal[p].n.toLocaleString()}</td></tr>`).join("")}</table></div>
        <p class="muted" style="font-size:13px">Range score and width: lower is better. The score rewards ranges that
        catch the measurement while staying narrow${cal.q ? `; both use the ${cal.q.n.toLocaleString()} forecasts where both services gave a range, and Yr's main value counts as its middle` : ""}.</p>`
        : `<p class="muted">No data yet.</p>`}`;

    const rain = S.v === "p" ? D.rain?.[S.patH] : null;
    document.getElementById("rain").innerHTML = !rain ? "" : `<h3>Catching rain</h3>
      <p class="sub" style="font-size:14px">A wet hour is more than 0.1 mm. ${rain.wet_hours.toLocaleString()} wet and
      ${rain.dry_hours.toLocaleString()} dry hours so far.</p>
      <div class="table-scroll"><table><tr><th>Service</th><th>Rain caught</th><th>False alarms</th><th>Overall skill</th><th>Error when wet</th></tr>
      ${["yr", "wn"].map(p => `<tr><td><span class="dot ${p}"></span> ${p === "yr" ? "Yr" : "WeatherNext"}</td>
        <td>${rain[p].pod == null ? "–" : Math.round(rain[p].pod * 100) + "%"}</td>
        <td>${rain[p].far == null ? "–" : Math.round(rain[p].far * 100) + "%"}</td>
        <td>${fmt(rain[p].csi)}</td><td>${fmt(rain[p].wet_mae)} mm</td></tr>`).join("")}</table></div>
      <p class="muted" style="font-size:12px">Overall skill (CSI) runs from 0 to 1; higher is better.</p>`;
  }

  function ago(iso) {
    const h = (Date.now() - Date.parse(iso)) / 36e5;
    if (h < 1) return `${Math.max(1, Math.round(h * 60))} min ago`;
    return h < 48 ? `${Math.round(h)} h ago` : `${Math.round(h / 24)} days ago`;
  }
  function renderHealth() {
    const el = document.getElementById("health"), h = D.health;
    if (!h || !h.generated_at) return;
    el.hidden = false;
    if (!h.last_run) { el.textContent = "No collection runs yet."; return; }
    const age = (Date.now() - Date.parse(h.last_run)) / 36e5;
    const parts = [];
    let warn = false;
    if (h.last_run_failed) {
      warn = true;
      parts.push(`Last run failed ${ago(h.last_run)}` + (h.last_success ? ` (last good run ${ago(h.last_success)})` : ""));
    } else if (age > STALE_H) {
      warn = true;
      parts.push(`No update for ${ago(h.last_run).replace(" ago", "")}: collection may have stopped`);
    } else {
      parts.push(`Updated ${ago(h.last_run)}`);
    }
    for (const k of ["yr", "frost", "wn"]) {
      const s = h.sources?.[k]; if (!s) continue;
      if (s.status === "error" || s.status === "partial") warn = true;
      parts.push(s.status === "ok" ? `${SOURCE_NAME[k]} ✓` : `${SOURCE_NAME[k]}: ${SOURCE_STATUS[s.status] || s.status}`);
    }
    if (h.expected_48h) {
      const n = Math.min(h.runs_48h, h.expected_48h);
      if (h.expected_48h - h.runs_48h > 2) warn = true;
      parts.push(`${n} of ${h.expected_48h} runs in 48 h`);
    }
    el.classList.toggle("warn", warn);
    el.innerHTML = (warn ? `<span class="warn-label">Check:</span> ` : "") + parts.map(esc).join(" · ");
  }

  function render() {
    renderTiles(); renderHorizon(); renderTrend(); renderMap(); renderPatterns();
  }

  load().then(() => {
    const m = D.meta || {};
    renderHealth();
    if (!m.variables) { document.getElementById("fresh").textContent = "No data published yet."; return; }
    const updated = D.health?.generated_at ? "" : ` · updated ${m.generated_at.replace("T", " ").slice(0, 16)} UTC`;
    document.getElementById("fresh").textContent = m.days
      ? `${m.days} days scored (${m.first_day} to ${m.last_day})${updated}`
      : "Collecting… the first scores appear about a day after collection starts.";
    if (m.demo) document.querySelector(".hero").insertAdjacentHTML("afterbegin",
      `<p class="badge" style="margin-bottom:8px">Demo data: made-up numbers for previewing the layout</p>`);
    document.getElementById("attrib").textContent = (m.attribution || []).join(" ");
    seg(document.getElementById("var-seg"), Object.entries(m.variables).map(([k, v]) => [k, v.name]),
        () => S.v, v => (S.v = v));
    seg(document.getElementById("period-seg"), [["all", "All time"], ["last30", "Last 30 days"]],
        () => S.period, v => (S.period = v));
    S.station = S.station || (m.stations.find(s => s.id === "SN18700") || m.stations[0])?.id;
    render();
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
  });
})();
