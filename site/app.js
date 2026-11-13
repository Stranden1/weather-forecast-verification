/* Yr vs WeatherNext scorecard. Reads the small JSON files in data/. */
(() => {
  // ?demo previews the made-up data from `python -m cloud.demo` (never deployed).
  const DATA = window.WX_DATA_BASE || (new URLSearchParams(location.search).has("demo") ? "data_demo/" : "data/");
  const SOURCE_NAME = { yr: "Yr", frost: "Frost", wn: "WeatherNext", ecmwf: "ECMWF" };
  const SOURCE_STATUS = {
    ok: "✓", partial: "partly working", error: "failed", no_data: "no new data",
    no_access: "waiting for access", paused: "paused",
  };
  const STALE_H = 8; // runs are every 3 h; allow 5 h for GitHub's schedule delays (seen 3-5 h)
  const NO_OBS_H = 48; // a station is "without measurements" after 2 days before the last scored day ends
  const H_LABEL = { 6: "6 h", 12: "12 h", 24: "1 day", 48: "2 days", 72: "3 days", 120: "5 days", 168: "7 days", 240: "10 days" };
  const VERDICT = {
    yr: ["Yr is ahead", "yr"], weathernext: ["WeatherNext is ahead", "wn"],
    too_close: ["Too close to call", ""], not_enough_data: ["Not enough days yet", ""],
  };
  const S = { v: "t", period: "all", hView: "diff", trendH: 24, mapH: 24, patH: 24, biasH: 24, eventH: 24, region: "all", station: null };
  let D = {}, charts = {}, map, markers = [], stationRequest = 0, replayRequest = 0;

  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const fmt = (x, d = 2) => x == null ? "–" : Number(x).toFixed(d);
  // Skill 0.36 -> "36% better", -0.12 -> "12% worse" (than the naive "same as yesterday" guess).
  const skillPct = x => { if (x == null) return "–"; const p = Math.round(Math.abs(x) * 100);
    return p === 0 ? "same" : `${p}% ${x > 0 ? "better" : "worse"}`; };
  const skillSentence = x => skillPct(x) === "same" ? "About as good as “same as yesterday”" : `${skillPct(x)} than “same as yesterday”`;
  const unit = () => D.meta.variables[S.v].unit;
  // "Both, averaged" against the better single service (gain = share of its error removed).
  const AVG_VERDICT = { better: "Clearly better", worse: "Clearly worse", too_close: "Too close to call", not_enough_data: "Not enough days yet" };
  const signedPct = x => { const p = Math.round(x * 100); return p === 0 ? "0%" : `${p > 0 ? "+" : "−"}${Math.abs(p)}%`; };
  // Rain leads with WeatherNext's median (its average spreads drizzle everywhere); the average is the dashed line.
  // Temperature and wind lead with the average. `wnPick` returns the headline and secondary numbers of a stats block.
  const isRain = () => S.v === "p";
  const rangeFmt = x => fmt(x, isRain() || (x != null && Math.abs(x) > 0 && Math.abs(x) < 0.01) ? 3 : 2);
  const wnName = () => isRain() ? "WeatherNext (median)" : "WeatherNext";
  const selected = name => D.views?.[S.period]?.[name] || {};
  const dates = () => D.meta.periods?.[S.period] || { start: D.meta.first_day, end: D.meta.last_day };
  const periodText = () => dates().start ? `${dates().start} to ${dates().end} (UTC target dates)` : "No dates yet";
  const wnPick = s => isRain()
    ? { main: s.mae_wn50, alt: s.mae_wn, bias: s.bias_wn50, diff: s.diff_50, lo: s.ci_50_lo, hi: s.ci_50_hi, verdict: s.verdict_50,
        skill: s.base?.skill_wn50, altVerdict: s.verdict, altWord: "average" }
    : { main: s.mae_wn, alt: s.mae_wn50, bias: s.bias_wn, diff: s.diff, lo: s.ci_lo, hi: s.ci_hi, verdict: s.verdict,
        skill: s.base?.skill_wn, altVerdict: null, altWord: "median" };
  const hs = () => (S.v === "p" ? D.meta.precip_horizons : D.meta.horizons);
  const dayMonth = iso => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "Europe/Oslo" });
  // Stations whose latest measurement is more than NO_OBS_H before the end of the last scored day.
  // Stations that never reported (last_obs null) are left out; missing pairs are marked separately on the map.
  function silentStations() {
    const m = D.meta; if (!m?.last_day) return new Map();
    const end = Date.parse(m.last_day + "T24:00:00Z");
    return new Map(m.stations.filter(s => s.last_obs && end - Date.parse(s.last_obs) > NO_OBS_H * 36e5)
      .map(s => [s.id, s.last_obs]));
  }
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // A file that is simply not there yet (404) is empty; a network, server or parse error is a
  // failed download, so the page can say "try again" instead of "no data published yet".
  const failed = new Set();
  async function load() {
    const names = ["meta", "leaderboard", "health", "summary", "events", "views"];
    const get = n => fetch(DATA + n + ".json")
      .then(r => r.ok ? r.json() : (r.status === 404 ? {} : Promise.reject(new Error(r.status))))
      .catch(() => { failed.add(n); return {}; });
    const got = await Promise.all(names.map(get));
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
             pointHoverRadius: 6, spanGaps: false, tension: 0.2, ...extra };
  }
  function chart(id, config) {
    if (charts[id]) charts[id].destroy();
    const canvas = document.getElementById(id);
    canvas.setAttribute("role", "img");
    charts[id] = new Chart(canvas, config);
  }

  function renderAnswer() {
    const s = D.leaderboard?.[S.v]?.[24]?.[S.period], el = document.getElementById("answer");
    if (!el) return;
    const w = s && wnPick(s);
    el.textContent = !s?.n || w.main == null ? "Waiting for paired forecasts" : (VERDICT[w.verdict] || VERDICT.not_enough_data)[0] + ".";
    document.getElementById("comparison-kicker").textContent = `${D.meta.variables[S.v].name} / 1 day ahead`;
    document.getElementById("comparison-context").textContent = s?.n && w.main != null
      ? `Checked against station measurements across Norway. Lower average error is better.` : "";
    document.getElementById("scope").textContent = `${periodText()}${isRain() ? " · WeatherNext's median throughout primary rain views" : ""}`;
  }

  const EVENT_DESCRIPTION = {
    t: ["Does it catch below-freezing hours?", "Air temperature below 0 °C at 2 m; this measures hours, not frost nights or road conditions."],
    w: ["Does it catch stronger wind?", "Mean wind of at least 10 m/s at 10 m, rather than gusts."],
    p: ["Does it catch wet hours?", "More than 0.1 mm of precipitation in an hour, including snow as water equivalent. In wind, gauges catch less snow than falls, so snow hours can make forecasts look too wet. WeatherNext's median is used for its yes/no prediction."],
  };
  function renderPractical() {
    const card = document.getElementById("practical"); if (!card) return;
    hSelect("event-h", "eventH");
    const region = document.getElementById("event-region"); region.value = S.region;
    region.onchange = () => { S.region = region.value; renderPractical(); };
    const [title, description] = EVENT_DESCRIPTION[S.v];
    document.getElementById("practical-heading").textContent = title;
    document.getElementById("practical-sub").textContent = description;
    const g = selected("practical")?.[S.v]?.[S.eventH]?.[S.region], el = document.getElementById("practical-body");
    if (!g?.n) { el.innerHTML = `<p class="empty">No paired hours in this group and period.</p>`; return; }
    const rate = x => x == null ? "–" : Math.round(x * 100) + "%";
    const bar = (x, provider) => x == null ? "" : `<span class="rate-bar" aria-hidden="true"><span style="width:${100 * x}%;background:var(--${provider})"></span></span>`;
    const count = x => x.toLocaleString();
    const rows = [
      ["Observed events caught", (p, provider) => `${rate(p.pod)} <span class="event-count">(${count(p.hits)} hours)</span>${bar(p.pod, provider)}`],
      ["Observed events missed", p => count(p.misses) + " hours"],
      ["False alarms", p => count(p.false_alarms) + " hours"],
      ["Forecast events that were false alarms", (p, provider) => rate(p.far) + bar(p.far, provider)],
      ["Average miss during observed events", p => `${fmt(p.event_mae)} ${unit()}`],
    ];
    // [data key, column title, colour token]; the height-adjusted column exists for temperature only.
    const cols = [["yr", "Yr", "yr"], ["wn", wnName(), "wn"]];
    if (g.wnh) cols.push(["wnh", "WeatherNext, height-adjusted (our estimate)", "ink-3"]);
    el.innerHTML = `<p class="event-count">${H_LABEL[S.eventH]} ahead · ${count(g.n)} paired hours over ${g.days} days at ${g.stations} stations.
      ${count(g.events)} observed event hours across ${g.event_days} days.</p>
      <div class="table-scroll"><table class="event-table"><tr><th>What happened</th>${cols.map(([, title]) => `<th>${title}</th>`).join("")}</tr>
      ${rows.map(([label, value]) => `<tr><td>${label}</td>${cols.map(([key, , tone]) => `<td>${value(g[key], tone)}</td>`).join("")}</tr>`).join("")}</table></div>
      <p class="muted" style="font-size:13px">A false alarm means the forecast crossed the threshold but the measurement did not.
      These are descriptive counts for shared hours, not a winner test or independent storms.${g.days < D.meta.min_days_for_verdict ? " Only a few days are available; read this with care." : ""}</p>`;
  }

  function renderTiles() {
    const h = hs().includes(24) ? 24 : hs()[0];
    const s = D.leaderboard?.[S.v]?.[h]?.[S.period];
    const el = document.getElementById("tiles");
    const detailBody = document.getElementById("score-detail-body");
    const blend = document.getElementById("blend-finding");
    blend.hidden = !(s?.n && s.verdict_avg === "better" && Number.isFinite(s.mae_avg) && Number.isFinite(s.avg_gain));
    blend.textContent = blend.hidden ? "" : `Average of both: ${fmt(s.mae_avg)} ${unit()} average error, about ${Math.round(s.avg_gain * 100)}% lower than the better single service. Our blend; an aggregate result.`;
    el.hidden = !s?.n;
    detailBody.parentElement.hidden = !s?.n;
    if (!s?.n) { el.innerHTML = ""; detailBody.innerHTML = ""; return; }
    const w = wnPick(s);
    const ci = w.lo != null ? `95% range of the difference: ${rangeFmt(w.lo)} to ${rangeFmt(w.hi)} ${unit()}` :
      `A verdict needs at least ${D.meta.min_days_for_verdict} days of data`;
    const skill = (p, x) => x == null ? "" :
      `<div class="d">${skillSentence(x)} (its error ${fmt(s.base.mae)} ${unit()})</div>`;
    // Temperature only: WeatherNext moved to each station's height (our adjustment, secondary).
    const adj = s.mae_wnh == null ? "" : `<div class="d">Height-adjusted (our estimate): ${fmt(s.mae_wnh)} ${unit()}</div>`;
    const [vh, clsh] = VERDICT[s.verdict_h] || VERDICT.not_enough_data;
    // A second verdict: the height-adjusted one for temperature, the average-based one for rain.
    const [va, clsa] = VERDICT[w.altVerdict] || VERDICT.not_enough_data;
    // Temperature and wind: the two forecasts averaged (our blend, cloud/summarize.py `e_avg`).
    const gain = s.avg_gain == null ? "" : `<div class="d">${s.avg_gain === 0 ? "Same as the better of the two"
      : `${Math.round(Math.abs(s.avg_gain) * 100)}% ${s.avg_gain > 0 ? "better" : "worse"} than the better of the two`}</div>` +
      (s.verdict_avg == null ? "" : `<div class="d">${s.avg_gain_lo == null ? `A verdict needs at least ${D.meta.min_days_for_verdict} days of data`
        : `95% range: ${signedPct(s.avg_gain_lo)} to ${signedPct(s.avg_gain_hi)}`}
        <span class="badge">${AVG_VERDICT[s.verdict_avg] || AVG_VERDICT.not_enough_data}</span></div>`);
    const avgTile = s.mae_avg == null ? "" : `
      <div class="detail-blend"><h3>Both, averaged</h3>
        <p><b>${fmt(s.mae_avg)} ${unit()}</b> average error · our blend of the two forecasts.</p>${gain}
        <p class="d">The midpoint of the two forecasts; improvement is an aggregate result, not a guarantee at each station. Bias ${fmt(s.bias_avg)} ${unit()}</p></div>`;
    const adjVerdict = isRain() ? `<div class="d">Using WeatherNext's average instead: <span class="badge ${clsa}">${va}</span></div>`
      : s.mae_wnh == null ? "" :
      `<div class="d">After a standard height adjustment: <span class="badge ${clsh}">${vh}</span></div>`;
    el.innerHTML = `
      <div class="tile competitor competitor-yr${w.verdict === "yr" ? " has-lower-error" : ""}"><p class="k">Yr</p>
        <div class="v">${fmt(s.mae_yr)} <small>${unit()} avg. error</small></div>
        <p class="competitor-source">MET Norway${w.verdict === "yr" ? ' <span class="winner-label">Lower error</span>' : ""}</p></div>
      <div class="tile competitor competitor-wn${w.verdict === "weathernext" ? " has-lower-error" : ""}"><p class="k">WeatherNext${isRain() ? " <small>median</small>" : ""}</p>
        <div class="v">${fmt(w.main)} <small>${unit()} avg. error</small></div>
        <p class="competitor-source">Google DeepMind${w.verdict === "weathernext" ? ' <span class="winner-label">Lower error</span>' : ""}</p></div>`;
    detailBody.innerHTML = `<p class="detail-evidence">${s.days} matched days · ${s.n.toLocaleString()} paired station-hours.<br>${ci}</p>
      <div class="score-detail-grid"><div><h3 class="yr">Yr</h3><p class="d">Bias ${fmt(s.bias_yr)} ${unit()} (positive = forecast too high)</p>${skill("yr", s.base?.skill_yr)}</div>
      <div><h3 class="wn">${wnName()}</h3><p class="d">Bias ${fmt(w.bias)} ${unit()} · ${w.altWord} version ${fmt(w.alt)} ${unit()}</p>${skill("wn", w.skill)}${adj}${adjVerdict}</div></div>${avgTile}`;
  }

  // Error by horizon. The default view plots WeatherNext's error minus Yr's with its 95% range,
  // because on the error-size scale the gap is a few hundredths of a unit and can't be seen.
  // Both charts leave out horizons with fewer than min_days_for_verdict days; the table keeps them.
  // Each series returns [difference, range low, range high, verdict] for one stats block.
  const horizonSeries = () => isRain()
    ? [{ label: "WeatherNext's median", get: s => [s.diff_50, s.ci_50_lo, s.ci_50_hi, s.verdict_50], shape: "circle" },
       { label: "WeatherNext's average", get: s => [s.diff, s.ci_lo, s.ci_hi, s.verdict], shape: "rect" }]
    : [{ label: "As published", get: s => [s.diff, s.ci_lo, s.ci_hi, s.verdict], shape: "circle" },
       ...(S.v === "t" ? [{ label: "Height-adjusted (our estimate)", get: s => [s.diff_h, s.ci_h_lo, s.ci_h_hi, s.verdict_h], shape: "triangle" }] : [])];
  const verdictColor = v => css(v === "yr" ? "--yr" : v === "weathernext" ? "--wn" : "--ink-3");
  // Legend marks for the series shapes; the second series is drawn hollow, as in the chart.
  const shapeMark = (shape, hollow) => shape === "triangle"
    ? `<span class="shape${hollow ? " hollow" : ""}">▲</span>`
    : `<span class="mark ${shape}${hollow ? " hollow" : ""}"></span>`;

  function renderHorizon() {
    const b = D.leaderboard?.[S.v] || {};
    const all = hs().filter(h => b[h]?.[S.period]?.n);
    const H = all.filter(h => b[h][S.period].days >= D.meta.min_days_for_verdict);
    const short = all.filter(h => !H.includes(h));
    const wnErr = isRain() ? "the average error of WeatherNext's median" : "WeatherNext's average error";
    document.getElementById("horizon-sub").textContent = S.hView === "diff"
      ? `How much larger ${wnErr} was than Yr's, for forecasts made this far ahead. ` +
        "Above the line Yr was closer; below it WeatherNext was. The bar is the 95% range: if it crosses the line, it's too close to call."
      : "Average error (MAE) for forecasts made this far before the weather happened. Lower is better.";
    const days = h => b[h][S.period].days;
    document.getElementById("horizon-note").textContent = (short.length
      ? `Not shown yet: ${short.map(h => `${H_LABEL[h]} (${days(h)} day${days(h) === 1 ? "" : "s"} of data)`).join(", ")}; ` +
        `a horizon appears once it has ${D.meta.min_days_for_verdict} days. `
      : "") + "Both forecasts come from the same moment, so each gets the same head start.";
    if (S.hView === "diff") renderHorizonDiff(b, H); else renderHorizonError(b, H);
    renderHorizonTable(b, all);
  }

  function renderHorizonDiff(b, H) {
    const series = horizonSeries().filter(x => H.some(h => x.get(b[h][S.period])[1] != null));
    const k = series.length, step = 0.24;
    const datasets = series.map((x, j) => {
      const data = H.map((h, i) => { const [y, lo, hi, v] = x.get(b[h][S.period]);
        return y == null ? null : { x: i + (j - (k - 1) / 2) * step, y, lo, hi, v, h }; }).filter(Boolean);
      const secondary = x.shape === "triangle";
      const colors = data.map(p => secondary ? css("--ink-3") : verdictColor(p.v));
      return { label: x.label, data, showLine: false, pointStyle: x.shape, pointRadius: secondary ? 4 : 7, pointHoverRadius: 8, secondary,
        borderWidth: secondary ? 1 : 2, pointBorderColor: colors, pointBackgroundColor: j === 0 ? colors : css("--surface") };
    });
    document.getElementById("horizon-legend").innerHTML =
      series.map((x, j) => `<span>${shapeMark(x.shape, j > 0)}${esc(x.label)}</span>`).join("") +
      `<span><span class="dot yr"></span>Yr clearly closer</span><span><span class="dot wn"></span>WeatherNext clearly closer</span>` +
      `<span><span class="dot neutral"></span>Too close to call</span>`;
    const vals = datasets.flatMap(d => d.data.flatMap(p => [p.y, p.lo, p.hi])).filter(x => x != null).map(Math.abs);
    // Symmetric around zero, on a round step, so the two halves read alike.
    const raw = Math.max(0.05, ...vals) * 1.1;
    const tick = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5].find(s => s >= raw / 3) || 10;
    const m = Math.ceil(raw / tick) * tick;
    const o = baseOptions(`WeatherNext error − Yr error (${unit()})`);
    o.plugins.legend.display = false;
    o.interaction = { mode: "nearest", axis: "x", intersect: false };
    o.plugins.tooltip.callbacks = {
      title: items => `${H_LABEL[items[0].raw.h]} ahead`,
      label: c => { const p = c.raw, who = p.y < 0 ? "WeatherNext" : "Yr";
        return [` ${c.dataset.label}: ${who} closer by ${fmt(Math.abs(p.y))} ${unit()}`,
                ` 95% range ${rangeFmt(p.lo)} to ${rangeFmt(p.hi)} · ${(VERDICT[p.v] || VERDICT.not_enough_data)[0]}`]; },
    };
    o.scales.x = { type: "linear", min: -0.5, max: H.length - 0.5, grid: { display: false }, border: { color: css("--line") },
      afterBuildTicks: sc => { sc.ticks = H.map((_, i) => ({ value: i })); },
      ticks: { color: css("--ink-2"), autoSkip: false, callback: v => H_LABEL[H[v]] ?? "" } };
    Object.assign(o.scales.y, { beginAtZero: false, min: -m, max: m });
    o.scales.y.ticks = { ...o.scales.y.ticks, stepSize: tick, callback: v => fmt(v, tick < 0.1 ? 2 : 1) };
    o.scales.y.grid = { color: c => c.tick.value === 0 ? css("--ink-3") : css("--grid"), lineWidth: c => c.tick.value === 0 ? 1.5 : 1 };
    chart("horizon-chart", { type: "scatter", options: o, data: { datasets }, plugins: [diffBackdrop, whiskers] });
  }

  // Faint tints and labels for the two halves of the difference chart, drawn under the data.
  const diffBackdrop = { id: "diffBackdrop", beforeDatasetsDraw(c) {
    const { ctx, chartArea: a, scales: { y } } = c, z = y.getPixelForValue(0);
    ctx.save();
    ctx.fillStyle = css("--yr") + "12"; ctx.fillRect(a.left, a.top, a.width, z - a.top);
    ctx.fillStyle = css("--wn") + "12"; ctx.fillRect(a.left, z, a.width, a.bottom - z);
    ctx.font = "13px system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
    const tag = (text, color, yy, base) => { ctx.textBaseline = base;
      ctx.fillStyle = color; ctx.fillText("●", a.left + 8, yy);
      ctx.fillStyle = css("--ink-2"); ctx.fillText(text, a.left + 24, yy); };
    tag("Yr closer", css("--yr"), a.top + 8, "top");
    tag("WeatherNext closer", css("--wn"), a.bottom - 8, "bottom");
    ctx.restore();
  } };
  // 95% range bars for points that carry lo/hi.
  const whiskers = { id: "whiskers", afterDatasetsDraw(c) {
    const { ctx, scales: { x, y } } = c;
    c.data.datasets.forEach((d, j) => { if (!c.isDatasetVisible(j)) return;
      d.data.forEach(p => { if (p.lo == null || p.hi == null) return;
        const px = x.getPixelForValue(p.x), lo = y.getPixelForValue(p.lo), hi = y.getPixelForValue(p.hi);
        ctx.save(); ctx.strokeStyle = d.secondary ? css("--ink-3") : verdictColor(p.v); ctx.lineWidth = d.secondary ? 1 : 2;
        if (d.secondary) ctx.setLineDash([3, 3]); ctx.beginPath();
        ctx.moveTo(px, lo); ctx.lineTo(px, hi);
        ctx.moveTo(px - 5, lo); ctx.lineTo(px + 5, lo); ctx.moveTo(px - 5, hi); ctx.lineTo(px + 5, hi);
        ctx.stroke(); ctx.restore(); }); });
  } };

  function renderHorizonError(b, H) {
    const rain = isRain();
    const g = k => H.map(h => b[h][S.period][k] ?? null);
    const ds = [
      line("Yr", g("mae_yr"), css("--yr")),
      line(rain ? "WeatherNext (median)" : "WeatherNext", g(rain ? "mae_wn50" : "mae_wn"), css("--wn")),
    ];
    if (rain) ds.push(line("WeatherNext (average)", g("mae_wn"), css("--wn"), { borderDash: [5, 4], pointStyle: "rectRot", backgroundColor: css("--surface") }));
    else if (g("mae_wnh").some(x => x != null))
      ds.push(line("WeatherNext, height-adjusted (our estimate)", g("mae_wnh"), css("--ink-3"), { borderWidth: 1, pointRadius: 3, borderDash: [2, 3], pointStyle: "triangle", backgroundColor: css("--surface") }));
    document.getElementById("horizon-legend").innerHTML = "";
    chart("horizon-chart", { type: "line", options: baseOptions(`Average error (${unit()})`), data: { labels: H.map(h => H_LABEL[h]), datasets: ds } });
  }

  function renderHorizonTable(b, H) {
    const rain = isRain(), hasAdj = H.some(h => b[h][S.period].mae_wnh != null), hasAvg = H.some(h => b[h][S.period].mae_avg != null);
    document.getElementById("horizon-table").innerHTML = `<div class="table-scroll"><table>
      <tr><th>Ahead</th><th>Yr</th><th>WeatherNext${rain ? " (median)" : ""}</th><th>${rain ? "Average" : "Median"}</th>${hasAdj ? "<th>Height-adj.</th>" : ""}${hasAvg ? "<th>Both, averaged</th>" : ""}<th>Difference</th><th>95% range</th><th>Verdict</th>
        <th>Same as yesterday</th><th>Yr vs it</th><th>WeatherNext vs it</th></tr>
      ${H.map(h => { const s = b[h][S.period]; const w = wnPick(s); const [vt, cls] = VERDICT[w.verdict] || VERDICT.not_enough_data;
        return `<tr><td>${H_LABEL[h]}</td><td>${fmt(s.mae_yr)}</td><td>${fmt(w.main)}</td><td>${fmt(w.alt)}</td>
        ${hasAdj ? `<td>${fmt(s.mae_wnh)}</td>` : ""}${hasAvg ? `<td>${fmt(s.mae_avg)}</td>` : ""}
        <td>${rangeFmt(w.diff)}</td><td>${w.lo == null ? "–" : rangeFmt(w.lo) + " to " + rangeFmt(w.hi)}</td>
        <td><span class="badge ${cls}">${vt}</span></td>
        <td>${fmt(s.base?.mae)}</td><td>${skillPct(s.base?.skill_yr)}</td><td>${skillPct(w.skill)}</td></tr>`; }).join("")}
      </table></div><p class="muted" style="font-size:13px">Average errors in ${unit()}. Difference = WeatherNext${rain ? " (median)" : ""} error − Yr error. Negative means WeatherNext was closer.
      ${hasAdj ? `Height-adj. = WeatherNext moved to each station's height at 6.5 °C per km (our adjustment, not Google's); the difference, range and verdict in this table use the published values.` : ""}
      ${hasAvg ? `Both, averaged = the midpoint of the Yr and WeatherNext forecasts (our blend, not a service).` : ""}
      "Same as yesterday" = the value measured at the same time of day on the latest day already known when the forecast was made
      (yesterday up to 1 day ahead, 2 days back for 2 days ahead, and so on).
      "60% better" means the forecast's average error was 60% smaller than that guess's, counting only forecasts that have one.</p>`;
  }

  // Steadiness: how much each service's forecast for the same station and hour changed from one
  // horizon to the next (cloud/replay.py), for the selected period (views.json).
  const STEADY = {
    yr: ["Yr steadier", "yr"], weathernext: ["WeatherNext steadier", "wn"],
    too_close: ["Too close to call", ""], not_enough_data: ["Not enough days yet", ""],
  };
  const H_SHORT = h => H_LABEL[h].replace(/ days?$/, " d");
  const stepLabel = s => `${H_SHORT(s.from)} → ${H_SHORT(s.to)}`;
  const stepText = s => `${H_LABEL[s.from]} → ${H_LABEL[s.to]}`;
  const pct = x => x == null ? "–" : Math.round(x * 100) + "%";
  const range = xs => { const v = xs.filter(x => x != null); if (!v.length) return "–";
    const [a, b] = [Math.min(...v), Math.max(...v)].map(pct); return a === b ? a : `${a.slice(0, -1)}–${b}`; };

  function renderSteadiness() {
    const card = document.getElementById("steady");
    const st = selected("steadiness")?.[S.v];
    const all = (st?.steps || []).filter(s => s.n);
    card.hidden = !all.length;
    if (!all.length) return;
    const minDays = D.meta.min_days_for_verdict;
    const steps = all.filter(s => s.days >= minDays);
    const short = all.filter(s => s.days < minDays);
    const wnName = isRain() ? "WeatherNext (median)" : "WeatherNext";
    const f = st.flip || {};
    document.getElementById("steady-flip").innerHTML = f.n ? `
      <span><b>Flip-flops per 100 forecasts:</b></span>
      <span><span class="dot yr"></span>Yr <b>${fmt(f.yr, 1)}</b></span>
      <span><span class="dot wn"></span>${wnName} <b>${fmt(f.wn, 1)}</b></span>
      <span class="muted">A flip-flop is a forecast that moved at least ${fmt(f.size, 1)} ${unit()} one way and then at least
        ${fmt(f.size, 1)} ${unit()} back over three horizons in a row (${f.n.toLocaleString()} forecasts checked).</span>` : "";

    const o = baseOptions(`Average change (${unit()})`);
    o.indexAxis = "y";
    o.interaction = { mode: "index", axis: "y", intersect: false };
    o.scales = { x: o.scales.y, y: { ...o.scales.x, ticks: { color: css("--ink-2"), autoSkip: false,
      callback: (_, i) => [stepLabel(steps[i]), (STEADY[steps[i].steadier] || STEADY.not_enough_data)[0]] } } };
    o.plugins.tooltip.callbacks = {
      title: items => `${stepText(steps[items[0].dataIndex])} ahead`,
      label: c => ` ${c.dataset.label}: changed ${fmt(c.parsed.x)} ${unit()} on average`,
      afterBody: items => { const s = steps[items[0].dataIndex];
        return s.ci_lo == null ? [] : [` Difference ${rangeFmt(s.diff)} ${unit()}, 95% range ${rangeFmt(s.ci_lo)} to ${rangeFmt(s.ci_hi)}`,
          ` ${(STEADY[s.steadier] || STEADY.not_enough_data)[0]}`]; },
    };
    const bar = (label, p, color) => ({ label, data: steps.map(s => s[p].rev), backgroundColor: color,
      borderRadius: 3, barPercentage: 0.8, categoryPercentage: 0.7 });
    chart("steady-chart", { type: "bar", options: o, data: { labels: steps.map(stepLabel),
      datasets: [bar("Yr", "yr", css("--yr")), bar(wnName, "wn", css("--wn"))] } });

    const minRev = { t: 0.2, w: 0.5, p: 0.1 }[S.v];
    document.getElementById("steady-note").textContent =
      (short.length ? `Not shown yet: ${short.map(s => `${stepText(s)} (${s.days} day${s.days === 1 ? "" : "s"} of data)`).join(", ")}; ` +
        `a step appears once it has ${minDays} days. ` : "") +
      `Changes of at least ${fmt(minRev, 1)} ${unit()} moved the forecast closer to what was measured ` +
      `${range(steps.map(s => s.yr.toward))} of the time for Yr and ${range(steps.map(s => s.wn.toward))} for WeatherNext ` +
      `(50% would be a coin toss). Steady is not the same as accurate: ` +
      `WeatherNext's forecast here is the ${isRain() ? "median" : "average"} of many possible outcomes, ` +
      `and Yr's first days are corrected with fresh station measurements, so it changes more close to the event. ` +
      `Only hours where both services issued a new forecast at both horizons count. ${periodText()}.`;

    document.getElementById("steady-table").innerHTML = `<div class="table-scroll"><table>
      <tr><th>Change from → to</th><th>Yr</th><th>${wnName}</th><th>Difference</th><th>95% range</th><th>Verdict</th>
        <th>Yr moved closer</th><th>WeatherNext moved closer</th><th>Forecasts</th><th>Days</th></tr>
      ${all.map(s => { const [vt, cls] = STEADY[s.steadier] || STEADY.not_enough_data;
        return `<tr><td>${stepText(s)}</td><td>${fmt(s.yr.rev)}</td><td>${fmt(s.wn.rev)}</td>
        <td>${rangeFmt(s.diff)}</td><td>${s.ci_lo == null ? "–" : rangeFmt(s.ci_lo) + " to " + rangeFmt(s.ci_hi)}</td>
        <td><span class="badge ${cls}">${vt}</span></td><td>${pct(s.yr.toward)}</td><td>${pct(s.wn.toward)}</td>
        <td>${s.n.toLocaleString()}</td><td>${s.days}</td></tr>`; }).join("")}
      </table></div><p class="muted" style="font-size:13px">Average size of the change in ${unit()}, in either direction.
      Difference = WeatherNext − Yr; negative means WeatherNext changed less. The 95% range and verdict use the same
      day-by-day test as the accuracy verdicts. "Moved closer" counts changes of at least ${fmt(minRev, 1)} ${unit()}.</p>`;
  }

  // Which way do they miss: signed error (bias) in 4 blocks of 6 h, Oslo time (cloud/summarize.py
  // bias_by_hour). Uses the selected period. Rain uses WeatherNext's median.
  const MISS = { t: ["too warm", "too cold"], w: ["too strong", "too weak"], p: ["too wet", "too dry"] };
  const missText = x => x == null ? "–" : Math.abs(x) < 0.005 ? "about right"
    : `${fmt(Math.abs(x))} ${unit()} ${MISS[S.v][x > 0 ? 0 : 1]}`;
  function renderBias() {
    const card = document.getElementById("bias");
    if (!card) return; // a cached index.html from before this card; the rest of the page must still render
    const byH = selected("bias")?.[S.v] || {};
    card.hidden = !Object.keys(byH).length;
    if (card.hidden) return;
    hSelect("bias-h", "biasH");
    const blocks = (byH[S.biasH] || []).filter(b => b.n);
    const wnKey = isRain() ? "bias_wn50" : "bias_wn", wnName = isRain() ? "WeatherNext (median)" : "WeatherNext";
    const adj = S.v === "t" && blocks.some(b => b.bias_wnh != null);
    document.getElementById("bias-sub").textContent = "Average error with its sign, by local time of day (Oslo). " +
      `Right of the line the forecast was ${MISS[S.v][0]}; left of it, ${MISS[S.v][1]}. A big error in either direction ` +
      "still counts here, so this shows a lean, not accuracy.";
    const s = D.leaderboard?.[S.v]?.[S.biasH]?.[S.period];
    document.getElementById("bias-lead").innerHTML = s?.n ? `${H_LABEL[S.biasH]} ahead, over all hours:
      <span class="dot yr"></span> Yr <b>${missText(s.bias_yr)}</b> ·
      <span class="dot wn"></span> ${wnName} <b>${missText(wnPick(s).bias)}</b>` +
      (adj && s.bias_wnh != null ? ` · height-adjusted <b>${missText(s.bias_wnh)}</b>` : "") : "";

    const o = baseOptions(`Average error with sign (${unit()})`);
    o.indexAxis = "y";
    o.interaction = { mode: "index", axis: "y", intersect: false };
    // Symmetric around zero on a round step, as in the horizon difference chart; rain biases are hundredths of a mm.
    const raw = Math.max(isRain() ? 0.01 : 0.05, ...blocks.flatMap(b => [b.bias_yr, b[wnKey], adj ? b.bias_wnh : 0].map(x => Math.abs(x || 0)))) * 1.1;
    const tick = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5].find(s => s >= raw / 2) || 10;
    const lim = Math.ceil(raw / tick) * tick;
    o.scales = { x: { ...o.scales.y, beginAtZero: false, min: -lim, max: lim,
        ticks: { ...o.scales.y.ticks, stepSize: tick, callback: v => fmt(v, tick < 0.01 ? 3 : tick < 0.1 ? 2 : 1) },
        grid: { color: c => c.tick.value === 0 ? css("--ink-3") : css("--grid") } },
      y: { ...o.scales.x, ticks: { color: css("--ink-2"), autoSkip: false } } };
    o.plugins.tooltip.callbacks = {
      title: items => `${blocks[items[0].dataIndex].label}, ${H_LABEL[S.biasH]} ahead`,
      label: c => ` ${c.dataset.label}: ${missText(c.parsed.x)}`,
      afterBody: items => { const b = blocks[items[0].dataIndex];
        return [` ${b.n.toLocaleString()} forecasts over ${b.days} day${b.days === 1 ? "" : "s"}`]; },
    };
    const bar = (label, key, color, extra = {}) => ({ label, data: blocks.map(b => b[key]), backgroundColor: color,
      borderColor: color, borderRadius: 3, barPercentage: 0.85, categoryPercentage: 0.75, ...extra });
    chart("bias-chart", { type: "bar", options: o, data: { labels: blocks.map(b => b.label), datasets: [
      bar("Yr", "bias_yr", css("--yr")), bar(wnName, wnKey, css("--wn")),
      ...(adj ? [bar("WeatherNext height-adjusted (our estimate)", "bias_wnh", "transparent",
        { borderColor: css("--wn"), borderWidth: 2 })] : [])] } });

    const few = blocks.filter(b => b.days < D.meta.min_days_for_verdict);
    document.getElementById("bias-note").textContent = (few.length
      ? `Fewer than ${D.meta.min_days_for_verdict} days so far for: ${few.map(b => b.label).join(", ")}; read these with care. ` : "") +
      (adj ? "WeatherNext's temperature is for the average height of its grid area, often higher than the station, " +
        "so part of its cold lean is height; the outlined bar shows it after our standard height adjustment. " : "") +
      (isRain() ? "Rain uses WeatherNext's median, as the tiles do. " : "") + periodText() + ".";

    document.getElementById("bias-table").innerHTML = `<div class="table-scroll"><table>
      <tr><th>Time of day</th><th>Yr</th><th>${wnName}</th>${adj ? "<th>Height-adj.</th>" : ""}<th>Forecasts</th><th>Days</th></tr>
      ${blocks.map(b => `<tr><td>${esc(b.label)}</td><td>${fmt(b.bias_yr)}</td><td>${fmt(b[wnKey])}</td>
        ${adj ? `<td>${fmt(b.bias_wnh)}</td>` : ""}<td>${b.n.toLocaleString()}</td><td>${b.days}</td></tr>`).join("")}
      </table></div><p class="muted" style="font-size:13px">Average of forecast − measurement in ${unit()}.
      Positive means the forecast was ${MISS[S.v][0]}, negative ${MISS[S.v][1]}.</p>`;
  }

  function rolling(arr, k = 7) {
    return arr.map((v, i) => { if (v == null) return null;
      const w = arr.slice(Math.max(0, i - k + 1), i + 1).filter(x => x != null);
      return w.length >= Math.min(k, 3) ? w.reduce((a, b) => a + b, 0) / w.length : null; });
  }
  function renderTrend() {
    hSelect("trend-h", "trendH");
    const rows = selected("trend")?.[S.v]?.[S.trendH] || [];
    const byDay = new Map(rows.map(r => [r.day, r])), t = [];
    if (dates().start && dates().end) for (let ts = Date.parse(dates().start); ts <= Date.parse(dates().end); ts += 864e5) {
      const day = new Date(ts).toISOString().slice(0, 10);
      t.push(byDay.get(day) || { day, n: 0, yr: null, wn: null });
    }
    const yr = t.map(r => r.yr), wn = t.map(r => r.wn);
    const faint = c => c + "55";
    chart("trend-chart", { type: "line", options: baseOptions(`Average error (${unit()})`), data: {
      labels: t.map(r => r.day.slice(5)), datasets: [
        line("Yr, 7-day", rolling(yr), css("--yr"), { pointRadius: 0 }),
        line(`${wnName()}, 7-day`, rolling(wn), css("--wn"), { pointRadius: 0 }),
        line("Yr, daily", yr, faint(css("--yr")), { borderWidth: 0, pointRadius: 3, showLine: false }),
        line(`${wnName()}, daily`, wn, faint(css("--wn")), { borderWidth: 0, pointRadius: 3, showLine: false }),
      ] } });
    const table = document.getElementById("trend-table");
    if (table) table.innerHTML = `<div class="table-scroll"><table>
      <tr><th>UTC date</th><th>Paired hours</th><th>Yr error</th><th>${wnName()} error</th></tr>
      ${t.map(r => `<tr><td>${r.day}</td><td>${r.n}</td><td>${fmt(r.yr)}</td><td>${fmt(r.wn)}</td></tr>`).join("")}
      </table></div>`;
  }

  function resizeMapMarkers() {
    const size = Math.max(8, Math.min(12, 8 + map.getZoom() - 5));
    map.getContainer().style.setProperty("--station-dot-size", `${size}px`);
    for (const marker of markers) {
      if (marker instanceof L.CircleMarker) marker.setRadius(size / 2 + 3);
    }
  }

  function renderMap() {
    hSelect("map-h", "mapH");
    const st = selected("stations")?.[S.v]?.[S.mapH] || {};
    const picker = document.getElementById("station-pick");
    if (picker) {
      picker.innerHTML = `<option value="">Biggest differences</option>` + [...D.meta.stations].sort((a, b) => a.name.localeCompare(b.name, "nb"))
        .map(s => `<option value="${esc(s.id)}">${esc(s.name)}</option>`).join("");
      picker.value = S.station || "";
      picker.onchange = () => { S.station = picker.value || null; renderStation(); };
    }
    if (!map) {
      // Leaflet only adds the tile layer (and its attribution text) once the map has a view, and a
      // fit made before that comes out a quarter step too tight, so start from a rough view.
      map = L.map("map", { scrollWheelZoom: true, touchZoom: true, zoomSnap: 0.25 }).setView([64.5, 13], 4);
      map.on("zoomend", resizeMapMarkers);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        { maxZoom: 10, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>' }).addTo(map);
      // Then fit every station (offshore Wisting at 73.5° N included), so a narrow window doesn't cut
      // off the far north. Quarter zoom steps fit tighter. The bottom padding is the attribution
      // bar's height (two lines on a phone), so no station sits under it.
      map.fitBounds(D.meta.stations.map(s => [s.lat, s.lon]), { paddingTopLeft: [16, 16],
        paddingBottomRight: [16, map.attributionControl.getContainer().offsetHeight + 12], animate: false });
    }
    markers.forEach(m => m.remove()); markers = [];
    const silent = silentStations();
    for (const s of D.meta.stations) {
      const r = st[s.id], quiet = silent.get(s.id);
      let kind = "missing", tip = `<b>${esc(s.name)}</b><br>No paired data for this variable, horizon and period`;
      if (r && r.yr != null && r.wn != null) {
        const d = r.wn - r.yr;
        kind = d > 0 ? "yr" : d < 0 ? "wn" : "equal";
        tip = `<b>${esc(s.name)}</b><br>Yr ${fmt(r.yr)} · ${wnName()} ${fmt(r.wn)} ${unit()}<br>${r.n} paired hours · ${r.days} days` +
          (s.flag && S.v === "t" ? "<br>Height note: see station details" : "");
      }
      if (quiet) tip += `<br>No measurements since ${dayMonth(quiet)}`;
      // A grey ring around stations without recent measurements, visible on either basemap.
      if (quiet) markers.push(L.circleMarker([s.lat, s.lon], { radius: 7, weight: 1, color: css("--ink-3"), fill: false,
        interactive: false }).addTo(map));
      const chooseStation = () => { S.station = s.id; renderStation(); };
      const m = L.marker([s.lat, s.lon], { title: s.name, alt: s.name,
        icon: L.divIcon({ className: "map-marker-target", iconSize: [24, 24], iconAnchor: [12, 12],
          html: `<span class="map-marker map-marker-${kind}" aria-hidden="true"></span>` }) })
        .bindTooltip(tip).on("click", chooseStation).addTo(map);
      const icon = m.getElement();
      const meaning = { yr: "lower Yr error", wn: "lower WeatherNext error", equal: "equal error", missing: "no paired data" }[kind];
      icon.setAttribute("aria-label", `Select ${s.name}: ${meaning}`);
      icon.addEventListener("keydown", e => {
        if (e.key !== "Enter" && e.key !== " ") return;
        e.preventDefault(); e.stopPropagation(); chooseStation();
      });
      markers.push(m);
    }
    renderMapPattern();
    resizeMapMarkers();
    renderStation();
  }

  function renderMapPattern() {
    const stats = selected("stations")?.[S.v]?.[S.mapH] || {};
    const eligible = D.meta.stations.filter(s => typeof s.offshore === "boolean" &&
      Number.isFinite(stats[s.id]?.yr) && Number.isFinite(stats[s.id]?.wn) &&
      stats[s.id].days >= D.meta.min_days_for_verdict);
    const parts = [[true, "Offshore"], [false, "On land"]].map(([offshore, label]) => {
      const rows = eligible.filter(s => s.offshore === offshore).map(s => stats[s.id]);
      if (!rows.length) return "";
      const yr = rows.filter(r => r.yr < r.wn).length;
      const wn = rows.filter(r => r.wn < r.yr).length;
      const equal = rows.length - yr - wn;
      if (offshore && (yr === rows.length || wn === rows.length)) {
        return `${label}: ${wn === rows.length ? "WeatherNext" : "Yr"} lower at all ${rows.length}.`;
      }
      return `${label}: Yr ${yr}, WeatherNext ${wn}${equal ? `, equal error ${equal}` : ""} of ${rows.length}.`;
    }).filter(Boolean);
    const el = document.getElementById("map-pattern");
    el.hidden = !parts.length;
    el.textContent = parts.length ? `${parts.join(" ")} ${H_LABEL[S.mapH]} ahead, ${periodText()}; stations with at least ${D.meta.min_days_for_verdict} paired days. Counts show lower average error, not winner tests.` : "";
  }

  // With no station selected the panel lists descriptive differences: stations with
  // enough days whose average error is at least DIFF_MIN smaller, the biggest gaps first.
  const DIFF_MIN = 0.10, DIFF_TOP = 3;
  function renderDiffs(el) {
    const st = selected("stations")?.[S.v]?.[S.mapH] || {}, minDays = D.meta.min_days_for_verdict || 7;
    const rows = D.meta.stations.map(s => ({ s, r: st[s.id] }))
      .filter(x => x.r && x.r.yr != null && x.r.wn != null && (x.r.days || 0) >= minDays)
      .map(x => ({ ...x, gap: (x.r.wn - x.r.yr) / Math.max(x.r.yr, x.r.wn) }));
    const pick = sign => rows.filter(x => sign * x.gap >= DIFF_MIN)
      .sort((a, b) => sign * (b.gap - a.gap)).slice(0, DIFF_TOP);
    const item = ({ s, r, gap }) => {
      const f = S.v === "t" ? s.flag : null;
      const note = f ? [f.dz != null ? `WeatherNext grid height ${Math.abs(f.dz)} m ${f.dz >= 0 ? "above" : "below"} station.` : "", f.note || ""].filter(Boolean).join(" ") : "";
      return `<li><div class="diff-row"><button class="diff-pick" data-id="${esc(s.id)}">${esc(s.name)}</button><strong class="diff-gap">${Math.round(Math.abs(gap) * 100)}%<small> lower error</small></strong></div>
        <span class="muted">Yr ${fmt(r.yr)} vs ${wnName()} ${fmt(r.wn)}&nbsp;${unit()}</span>${note ? `<span class="muted station-caveat">${esc(note)}</span>` : ""}</li>`;
    };
    const list = (sign, name, cls) => { const p = pick(sign);
      return p.length ? `<div class="diff-group diff-${cls}"><h4>${name} has lower error</h4><ol class="diff-list">${p.map(item).join("")}</ol></div>` : ""; };
    const lists = list(1, "Yr", "yr") + list(-1, wnName(), "wn");
    el.hidden = !lists;
    el.closest(".map-grid").classList.toggle("map-only", !lists);
    requestAnimationFrame(() => map.invalidateSize());
    el.innerHTML = lists ? `<p class="section-kicker">${H_LABEL[S.mapH]} ahead / Local comparison</p><h3>Biggest differences</h3><p class="chart-note muted">Percentages compare average error with the other service at the same station.</p>${lists}` : "";
    el.onclick = e => { const b = e.target.closest(".diff-pick"); if (b) { S.station = b.dataset.id; renderStation(); } };
  }

  async function renderStation() {
    const request = ++stationRequest;
    const el = document.getElementById("station-panel");
    const s = D.meta.stations.find(x => x.id === S.station);
    const picker = document.getElementById("station-pick"); if (picker) picker.value = s?.id || "";
    if (!s) { if (charts["station-chart"]) { charts["station-chart"].destroy(); delete charts["station-chart"]; } renderDiffs(el); return; }
    el.hidden = false;
    el.closest(".map-grid").classList.remove("map-only");
    requestAnimationFrame(() => map.invalidateSize());
    el.onclick = e => { if (e.target.closest(".diff-back")) { S.station = null; renderStation(); } };
    const st = selected("stations")?.[S.v]?.[S.mapH]?.[s.id];
    let rec = null;
    try { rec = await fetch(`${DATA}recent/${s.id}.json`).then(r => r.ok ? r.json() : null); } catch (e) {}
    if (request !== stationRequest) return;
    const f = S.v === "t" ? s.flag : null;
    const higher = dz => `${Math.abs(dz)} m ${dz > 0 ? "higher" : "lower"}`;
    const flagText = !f ? "" : `<p class="note" style="font-size:13px"><b>Height note.</b> ${f.dz != null
      ? `WeatherNext's temperature is for its grid area, which here is on average ${higher(f.dz)} than the station,
         so it should read about ${fmt(Math.abs(f.expected), 1)} °C ${f.expected < 0 ? "colder" : "warmer"} from height alone.
         ${f.dz_old != null && f.dz_old !== f.dz ? `Before 26 Sep we read a slightly different grid point, ${higher(f.dz_old)} than the station.` : ""}` : ""}
      ${f.note ? `${esc(f.note)} In the data up to 26 Sep, height explained only part of WeatherNext's error here.` : ""}</p>`;
    el.innerHTML = `<button class="diff-back">← Biggest differences</button>
      <h3>${esc(s.name)}</h3>
      <p class="muted" style="margin:0 0 8px;font-size:14px">${s.elev != null ? Math.round(s.elev) + " m above sea level · " : ""}${esc(s.county || "")}</p>
      <p style="margin:0 0 12px;font-size:14px">Average error ${H_LABEL[S.mapH]} ahead: <b>Yr ${fmt(st?.yr)}</b> · <b>${wnName()} ${fmt(st?.wn)}</b> ${unit()}${
        st?.wnh != null && st.wnh !== st.wn ? ` · WeatherNext height-adjusted ${fmt(st.wnh)} ${unit()} (our estimate)` : ""}</p>
      ${S.v === "t" && st?.wnh != null && st.wnh !== st.wn ? '<p class="chart-note muted">Height-adjusted means we estimate WeatherNext temperature at the station’s elevation using a standard temperature change with height. The main comparison uses the published forecast.</p>' : ""}
      ${flagText}${silentStations().has(s.id) ? `<p class="note" style="font-size:13px"><b>No measurements since ${dayMonth(s.last_obs)}.</b>
        No newer measurements occur in the finalized scored history through ${D.meta.last_day}; the live station may have recovered since.</p>` : ""}
      <p class="muted" style="margin:0 0 4px;font-size:13px">Last 7 days: forecast made 1 day ahead vs what happened</p>
      <div class="chart"><canvas id="station-chart" aria-label="Recent measured and forecast values at this station"></canvas></div>
      <details class="table-view"><summary>Show hourly values as a table</summary><div id="station-table"></div></details>
      ${D.meta.publish_forecast_values ? "" : `<p class="muted" style="font-size:12px">WeatherNext's forecast values are not shown, because its data terms don't clearly allow publishing them; its errors are included in every score.</p>`}`;
    if (!rec) {
      el.querySelector(".chart").hidden = true;
      el.querySelector(".table-view").hidden = true;
      return;
    }
    const ds = [line("Measured", rec[`obs_${S.v}`], css("--obs"), { pointRadius: 0, borderWidth: 2 }),
                line("Yr", rec[`yr_${S.v}`], css("--yr"), { pointRadius: 0 })];
    const wnValues = rec[isRain() ? "wn_p_p50" : `wn_${S.v}`];
    if (wnValues?.some(x => x != null)) {
      ds.push(line(wnName(), wnValues, css("--wn"), { pointRadius: 0 }));
      el.querySelector(".chart").insertAdjacentHTML("afterend", wnNotice());
    }
    const o = baseOptions(unit()); o.scales.y.beginAtZero = S.v !== "t";
    o.scales.x.ticks.maxTicksLimit = 7;
    chart("station-chart", { type: "line", options: o, data: {
      labels: rec.time.map(t => t.slice(5, 10) + " " + t.slice(11, 13) + "h"), datasets: ds } });
    document.getElementById("station-table").innerHTML = `<div class="table-scroll"><table>
      <tr><th>Time, UTC</th><th>Measured (${unit()})</th><th>Yr</th>${wnValues ? `<th>${wnName()}</th>` : ""}</tr>
      ${rec.time.map((t, i) => `<tr><td>${t.slice(0, 16).replace("T", " ")}</td><td>${fmt(rec[`obs_${S.v}`]?.[i])}</td>
        <td>${fmt(rec[`yr_${S.v}`]?.[i])}</td>${wnValues ? `<td>${fmt(wnValues[i])}</td>` : ""}</tr>`).join("")}</table></div>`;
  }

  // Required WeatherNext notices, shown next to every chart that draws WeatherNext values.
  function wnNotice() {
    const link = s => esc(s).replace(/https?:\/\/[^\s<]+[^\s<.,)]/g, u => `<a href="${u}" rel="noopener">${u}</a>`);
    return `<p class="attrib wn-notice">${(D.meta.wn_value_attribution || []).map(link).join("<br>")}</p>`;
  }

  // Storm replays: what each service said 7 days ... 6 hours before a notable event.
  const EV_ICON = { rain: "Rain", wind: "Wind", cold: "Cold" };
  async function renderReplays() {
    const request = ++replayRequest;
    const card = document.getElementById("replays");
    const list = (D.events || []).filter(e => e.day >= dates().start && e.day <= dates().end);
    card.hidden = !list.length;
    if (!list.length) return;
    const sel = document.getElementById("replay-pick");
    const name = id => (D.meta.stations.find(s => s.id === id) || {}).name || id;
    if (!S.replay || !list.some(e => e.id === S.replay)) S.replay = list[0].id;
    sel.innerHTML = list.map(e => `<option value="${e.id}" ${e.id === S.replay ? "selected" : ""}>${e.day} · ${EV_ICON[e.type]} · ${esc(name(e.station))} ${fmt(e.value, 1)} ${e.unit}${e.n_stations > 1 ? ` (+${e.n_stations - 1})` : ""}</option>`).join("");
    sel.onchange = () => { S.replay = sel.value; renderReplays(); };
    let r = null;
    try { r = await fetch(`${DATA}events/${S.replay}.json`).then(x => x.ok ? x.json() : null); } catch (e) {}
    if (request !== replayRequest) return;
    const body = document.getElementById("replay-body");
    if (!r) { body.innerHTML = `<p class="empty">This replay could not be loaded.</p>`; return; }
    const pts = r.points;  // farthest ahead first
    const others = r.stations.slice(1).map(s => `${esc(name(s.station))} ${fmt(s.value, 1)}`).join(", ");
    body.innerHTML = `<p style="margin:0 0 8px;font-size:15px"><b>${esc(r.label)} at ${esc(name(r.station))}, ${r.day}</b>:
        measured ${fmt(r.observed, 1)} ${r.unit} (${esc(r.what)}).${others ? ` <span class="muted">Also: ${others} ${r.unit}.</span>` : ""}</p>
      <div class="chart"><canvas id="replay-chart" aria-label="Forecasts before the event"></canvas></div>
      ${r.wn_shown ? wnNotice() : `<p class="muted" style="font-size:12px">WeatherNext's values are not shown for this event.</p>`}
      <details class="table-view"><summary>Show replay values as a table</summary><div id="replay-table"></div></details>
      <p class="muted" style="font-size:13px">${r.type === "rain"
        ? "Each point sums the 24 hourly forecasts for the UTC calendar day, each made that far before its hour. These can come from different forecast runs. The sum of hourly medians is not the median of the daily total. Rain is only scored up to 2 days ahead."
        : "Each point is the forecast for the same hour, made that far ahead. The hour is the most extreme measured hour that has forecasts at the most horizons."}
        Events are picked from the measurements only, never from who got it wrong.</p>`;
    const labels = pts.map(p => H_LABEL[p.h] + " before");
    const ds = [line("Yr", pts.map(p => p.yr), css("--yr")),
                line("Measured", pts.map(() => r.observed), css("--obs"), { borderDash: [6, 4], pointRadius: pts.length === 1 ? 5 : 0, pointStyle: "crossRot" })];
    if (r.wn_shown) {
      ds.splice(1, 0, line("WeatherNext (average)", pts.map(p => p.wn), css("--wn")));
      if (pts.some(p => p.wn50 != null))
        ds.splice(2, 0, line("Sum of WeatherNext hourly medians", pts.map(p => p.wn50), css("--wn"), { borderDash: [5, 4], pointStyle: "rectRot", backgroundColor: css("--surface") }));
    }
    const o = baseOptions(r.unit);
    o.scales.y.beginAtZero = r.type !== "cold";
    o.plugins.tooltip.callbacks.label = c => ` ${c.dataset.label}: ${fmt(c.parsed.y, 1)} ${r.unit}`;
    chart("replay-chart", { type: "line", options: o, data: { labels, datasets: ds } });
    document.getElementById("replay-table").innerHTML = `<div class="table-scroll"><table>
      <tr><th>Forecast made</th><th>Measured (${esc(r.unit)})</th><th>Yr</th>${r.wn_shown ? `<th>WeatherNext average</th>${r.type === "rain" ? "<th>Sum of hourly medians</th>" : ""}` : ""}</tr>
      ${pts.map(p => `<tr><td>${H_LABEL[p.h]} ahead</td><td>${fmt(r.observed, 1)}</td><td>${fmt(p.yr, 1)}</td>
        ${r.wn_shown ? `<td>${fmt(p.wn, 1)}</td>${r.type === "rain" ? `<td>${fmt(p.wn50, 1)}</td>` : ""}` : ""}</tr>`).join("")}</table></div>`;
  }

  function renderPatterns() {
    hSelect("pat-h", "patH");
    document.getElementById("pat-h-label").textContent = H_LABEL[S.patH];
    const rows = selected("patterns")?.[S.v]?.[S.patH] || [];
    const bar = (x, max, c) => x == null ? "" :
      `<span style="display:inline-block;height:8px;width:${Math.max(2, 80 * x / max)}px;background:var(${c});border-radius:0 4px 4px 0;vertical-align:middle;margin-left:6px"></span>`;
    const max = Math.max(...rows.flatMap(r => [r.mae_yr || 0, r.mae_wn || 0]), 0.01);
    document.getElementById("patterns").innerHTML = rows.length ? `<div class="table-scroll"><table>
      <tr><th>Situation</th><th>Paired hours</th><th>Yr error</th><th>${wnName()} error</th><th>Difference</th></tr>
      ${rows.map(r => `<tr><td>${esc(r.label)}</td><td>${r.n.toLocaleString()}</td>
        <td>${fmt(r.mae_yr)}${bar(r.mae_yr, max, "--yr")}</td><td>${fmt(r.mae_wn)}${bar(r.mae_wn, max, "--wn")}</td>
        <td>${fmt(r.diff)}</td></tr>`).join("")}</table></div>` : `<p class="empty">No data yet.</p>`;

    const cal = selected("calibration")?.[S.v]?.[S.patH];
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
        <p class="muted" style="font-size:13px">Lower range score is better; width must be judged with coverage. The score rewards ranges that
        catch the measurement while staying narrow${cal.q ? `; both use the ${cal.q.n.toLocaleString()} forecasts where both services gave a range, and Yr's main value counts as its middle` : ""}.</p>`
        : `<p class="muted">No data yet.</p>`}`;

    const rain = S.v === "p" ? selected("rain")?.[S.patH] : null;
    const RAIN_ROW = { yr: ["yr", "Yr"], wn50: ["wn", "WeatherNext (median)"], wn: ["wn", "WeatherNext (average)"] };
    document.getElementById("rain").innerHTML = !rain ? "" : `<h3>Catching rain</h3>
      <p class="sub" style="font-size:14px">A wet hour is more than 0.1 mm. ${rain.wet_hours.toLocaleString()} wet and
      ${rain.dry_hours.toLocaleString()} dry hours so far.</p>
      <div class="table-scroll"><table><tr><th>Service</th><th>Rain caught</th><th>False alarms</th><th>Overall skill</th><th>Error when wet</th></tr>
      ${["yr", "wn50", "wn"].filter(p => rain[p]).map(p => `<tr><td><span class="dot ${RAIN_ROW[p][0]}"></span> ${RAIN_ROW[p][1]}</td>
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
    for (const k of ["yr", "frost", "wn", "ecmwf"]) {
      const s = h.sources?.[k]; if (!s) continue;
      if (s.status === "error" || s.status === "partial") warn = true;
      parts.push(s.status === "ok" ? `${SOURCE_NAME[k]} ✓` : `${SOURCE_NAME[k]}: ${SOURCE_STATUS[s.status] || s.status}`);
    }
    if (h.expected_48h) {
      const n = Math.min(h.runs_48h, h.expected_48h);
      if (h.expected_48h - h.runs_48h > 2) warn = true;
      parts.push(`${n} of ${h.expected_48h} runs in 48 h`);
    }
    const silent = [...silentStations()].map(([id, t]) => [D.meta.stations.find(s => s.id === id).name, t]);
    if (silent.length) {
      if (silent.length / D.meta.stations.length > SILENT_WARN) warn = true;
      const names = silent.length <= 3 ? ` (${silent.map(([n]) => n).join(", ")})` : "";
      parts.push(silent.length === 1
        ? `Scored history: 1 station has no measurements since ${dayMonth(silent[0][1])}${names}`
        : `Scored history: ${silent.length} stations have no measurements for over 2 days${names}`);
    }
    el.classList.toggle("warn", warn);
    const detail = document.getElementById("health-detail");
    if (detail) {
      detail.textContent = parts.join(" · ") + (silent.length ? ` · Based on finalized scores through ${D.meta.last_day}; current station recovery can appear later.` : "");
      const issues = Object.values(h.sources || {}).some(s => s.status === "error" || s.status === "partial");
      const brief = [parts[0], ...(issues ? ["source issue"] : []), ...(silent.length ? ["station history warning"] : []),
        ...(h.expected_48h - h.runs_48h > 2 ? ["collection gap"] : [])];
      el.innerHTML = (warn ? `<span class="warn-label">Check:</span> ` : "") + brief.map(esc).join(" · ");
    } else el.innerHTML = (warn ? `<span class="warn-label">Check:</span> ` : "") + parts.map(esc).join(" · ");
  }

  // Month paragraphs are fixed-template text built at export (cloud/monthly.py); "September (5–27, 23 days): …"
  function renderSummary() {
    const months = D.summary?.months || [];
    const el = document.getElementById("summary");
    document.getElementById("monthly").hidden = !months.length;
    if (!months.length) return;
    // Header line in bold, then one line per variable with its label ("Temperature:") in bold.
    const line = s => { const i = s.indexOf(": ");
      return i < 0 ? esc(s) : `<b>${esc(s.slice(0, i))}</b>: ${esc(s.slice(i + 2))}`; };
    const para = m => { const [head, ...rest] = m.text.split("\n");
      return `<p><b>${esc(head)}</b>${rest.map(r => `<br>${line(r)}`).join("")}</p>`; };
    el.hidden = false;
    document.getElementById("summary-now").innerHTML = para(months[0]);
    const older = months.slice(1);
    document.getElementById("summary-earlier").hidden = !older.length;
    document.getElementById("summary-list").innerHTML = older.map(para).join("");
  }

  // ---------------------------------------------------------------------------------------------
  // Simple layer: the front page, Norwegian by default with an English toggle. Built only from data
  // that is already exported. Only the existing verdict (leaderboard.json) may name a winner; the
  // calendar, the frost icons and the station sentence describe and never get winner styling.
  // The expert cards below ("details") are unchanged and stay in English for now.
  // ---------------------------------------------------------------------------------------------
  const params = new URLSearchParams(location.search);
  const store = {
    get: k => { try { return localStorage.getItem(k); } catch { return null; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch {} },
  };
  let LANG = ["nb", "en"].includes(params.get("lang")) ? params.get("lang") : store.get("wx-lang") === "en" ? "en" : "nb";
  const SIMPLE_H = [6, 24, 48, 120, 240];
  const CITY_IDS = ["SN18700", "SN50540", "SN68860", "SN90450"]; // Oslo, Bergen, Trondheim, Tromsø first
  const EQUAL_GAP = 0.05;   // calendar: a day is "about equal" when the gap is under 5 % (display rule only)
  const SILENT_WARN = 0.2;  // the station line turns amber only when more than one in five are silent
  const UNIT = { t: "°C", w: "m/s", p: "mm" };
  const SS = { actualVar: "t", calVar: "t", station: store.get("wx-station") || CITY_IDS[0], cell: null };
  const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
  const locale = () => (LANG === "nb" ? "nb-NO" : "en-GB");
  const num = (x, d = 1) => x == null || !Number.isFinite(+x) ? "–"
    : new Intl.NumberFormat(locale(), { minimumFractionDigits: d, maximumFractionDigits: d }).format(x);
  const int = x => new Intl.NumberFormat(locale()).format(x);
  const pctOf = x => new Intl.NumberFormat(locale(), { style: "percent", maximumFractionDigits: 0 }).format(x);
  const fmtDate = (iso, opts = { day: "numeric", month: "short" }, tz = "Europe/Oslo") =>
    new Intl.DateTimeFormat(locale(), { timeZone: tz, ...opts }).format(new Date(iso));
  const utcDay = (d, opts) => fmtDate(d + "T12:00:00Z", opts, "UTC");
  function relTime(iso) {
    const min = (Date.now() - Date.parse(iso)) / 6e4;
    const rtf = new Intl.RelativeTimeFormat(LANG, { numeric: "auto" });
    if (min < 60) return rtf.format(-Math.max(1, Math.round(min)), "minute");
    if (min < 48 * 60) return rtf.format(-Math.round(min / 60), "hour");
    return rtf.format(-Math.round(min / 1440), "day");
  }
  const joinList = items => items.length < 2 ? items.join("")
    : items.slice(0, -1).join(", ") + ` ${t("and")} ` + items[items.length - 1];

  const TXT = {
    nb: {
      title: "Yr mot Google", tagline: "Hvem treffer best på været i Norge?", skip: "Hopp til sammenligningen",
      intro: n => `Hver dag sjekker vi varslene fra Yr og fra Google (WeatherNext), en KI-modell fra Google DeepMind, mot det ${n} målestasjoner faktisk målte.`,
      updated: (ago, days) => `Oppdatert ${ago} · ${days} dager sjekket`,
      lastFailed: (ago, good) => `Siste innsamling feilet ${ago}.` + (good ? ` Den siste vellykkede var ${good}.` : ""),
      stale: ago => `Siste oppdatering var ${ago}. Innsamlingen kan ha stoppet.`,
      failing: names => `${names}: feil to ganger på rad. De nyeste varslene kan mangle.`,
      noData: "Ingen data publisert ennå.", loadError: "Kunne ikke laste dataene. Prøv igjen om litt.",
      collecting: "Samler inn … de første tallene kommer omtrent en dag etter at innsamlingen startet.",
      stations: (ok, all) => `${ok} av ${all} stasjoner leverer målinger.`,
      silent: list => ` Ingen målinger fra ${list}; de timene er ikke med i sammenligningen.`,
      since: (name, d) => `${name} siden ${d}`, and: "og",
      verdictsKicker: "Kort fortalt", vars: { t: "Temperatur", w: "Vind", p: "Regn" },
      varsLower: { t: "temperatur", w: "vind", p: "regn" }, varsShort: { t: "Temp.", w: "Vind", p: "Regn" },
      hHead: { 6: "Om 6 t", 24: "I morgen", 48: "Om 2 d", 120: "Om 5 d", 240: "Om 10 d" },
      hPhrase: { 6: "6 timer fram", 24: "for i morgen", 48: "2 dager fram", 120: "5 dager fram", 240: "10 dager fram" },
      cell: { yr: "Yr", weathernext: "Google", too_close: "likt", not_enough_data: "–" },
      storyYr: l => `Yr treffer best ${l}.`, storyWn: l => `Google treffer best ${l}.`,
      storyEven: l => `${cap(l)} er det for jevnt til å kåre en vinner.`,
      storyMixed: l => `${cap(l)} er det ulikt for temperatur, vind og regn.`,
      keyYr: "Yr treffer best", keyWn: "Google treffer best", keyEven: "for jevnt til å kåre en vinner",
      keyTap: "Trykk på en rute for å se tallene.",
      verdictText: { yr: "Yr treffer best.", weathernext: "Google treffer best.", too_close: "For jevnt til å kåre en vinner.",
        not_enough_data: "For få dager til å kåre en vinner ennå." },
      cellDetail: (v, h, yr, wn, u, verdict, days) => `${v}, ${h}: Yr bommer i snitt med ${yr} ${u}, Google med ${wn} ${u}. ${verdict} Bygger på ${days} dager.`,
      cellRain: " For regn bruker vi det midterste av Googles mange utfall.",
      notScored: "ikke sjekket", tableCaption: "Hvem treffer best, etter hvor langt fram varselet gjelder",
      tableCorner: "Hvor langt fram",
      actualKicker: "Varsel mot virkelighet", place: "Sted",
      actualSub: "Siste 7 dager, varselet slik det så ut dagen før.",
      cities: "Byer", otherStations: "Andre stasjoner", measured: "Målt",
      actualText: (place, yr, wn, u) => `I ${place} bommet Yr i snitt med ${yr} ${u} de siste 7 dagene` + (wn == null ? "." : `, Google med ${wn} ${u}.`),
      actualNone: "Ingen ferske tall for denne stasjonen.",
      noticeLead: "Googles vilkår krever denne merknaden på engelsk under grafer med Googles varseltall:",
      wnHidden: "Googles varseltall vises ikke her; feilene deres er med i alle tallene.",
      calendarKicker: "Dag for dag",
      calendarSub: v => `${v} · varsel for i morgen. Hver rute er én dag.`,
      calYr: "Yr nærmest", calWn: "Google nærmest", calEq: "omtrent likt", calNone: "ingen tall",
      calCount: (y, g, e) => `Yr nærmest ${y} dager · Google nærmest ${g} dager · omtrent likt ${e} dager.`,
      calCloseCall: who => `${who} var nærmest flest dager, men samlet er forskjellen for liten til å kåre en vinner.`,
      calOther: (who, best) => `${who} var nærmest flest dager, men samlet bommer ${best} minst (se tabellen øverst).`,
      calNote: "En dag er «omtrent likt» når forskjellen i snittfeil er under 5 %. Kalenderen beskriver dag for dag; bare tabellen øverst kårer en vinner.",
      calDay: (d, yr, wn, u) => `${d}: Yr ${yr} ${u}, Google ${wn} ${u}`,
      blend: list => `<b>Tips:</b> Ser du på begge varslene for i morgen og tar midt imellom, bommer du omtrent ${list} enn med det beste av dem alene.`,
      blendPart: (p, v) => `${p} mindre på ${v}`,
      frostKicker: "Kuldegrader", frostQuestion: "Fanget varselet at det ble frost?",
      frostRow: (n, p) => `${n} av 10 frosttimer varslet (${p})`,
      frostFalse: (a, b) => `Varslet frost som ikke kom: Yr ${a}, Google ${b}.`,
      oneIn: n => `omtrent 1 av ${n} ganger`, never: "aldri", always: "nesten hver gang",
      frostNote: (n, days, st) => `Timer under 0 °C, varsel for i morgen: ${n} målte frosttimer over ${days} dager ved ${st} stasjoner. Beskrivende tall, ikke en vinnertest.`,
      fairKicker: "Er dette rettferdig?", readMore: "Les mer",
      fair: [
        ["Yr har hjemmebane.", "Yr justerer varslene sine med ferske målinger fra norske værstasjoner, også flere av dem vi sjekker mot."],
        ["Google-varselet er et gjennomsnitt av mange mulige utfall.", "Det gir litt mindre bom i snitt, men kan dempe ekstremvær. For regn bruker vi derfor det midterste utfallet."],
        ["Google regner for ruter på omtrent 5 km.", "I bratt terreng ligger ruta ofte høyere enn stasjonen, og da blir varselet for kaldt (omtrent 0,65 grader per 100 meter)."],
      ],
      showDetails: "Vis kart, alle stasjoner og detaljerte tall →", hideDetails: "Skjul detaljene ↑",
      themeDark: "Mørkt", themeLight: "Lyst", themeToDark: "Bytt til mørkt tema", themeToLight: "Bytt til lyst tema",
      sourcesTitle: "Kilder og vilkår",
      sourcesLead: "Tallene bygger på varsler og målinger fra MET Norway (Yr og Frost) og varsler fra Google (WeatherNext). Vilkårene krever at disse merknadene står ordrett på engelsk:",
      openSource: "Åpen kildekode", footerUpdated: "oppdateres automatisk omtrent hver 2,5 time",
      chartLabel: "Målt og varslet de siste 7 dagene", calendarLabel: m => `Dager i ${m}`, varGroup: "Værtype",
    },
    en: {
      title: "Yr vs Google", tagline: "Which forecast gets Norway's weather right?", skip: "Skip to the comparison",
      intro: n => `Every day we check the forecasts from Yr and from Google (WeatherNext), an AI model from Google DeepMind, against what ${n} weather stations actually measured.`,
      updated: (ago, days) => `Updated ${ago} · ${days} days checked`,
      lastFailed: (ago, good) => `The last collection failed ${ago}.` + (good ? ` The last successful one was ${good}.` : ""),
      stale: ago => `Last updated ${ago}. Collection may have stopped.`,
      failing: names => `${names}: errors twice in a row. The latest forecasts may be missing.`,
      noData: "No data published yet.", loadError: "Could not load the data. Please try again in a moment.",
      collecting: "Collecting… the first scores appear about a day after collection starts.",
      stations: (ok, all) => `${ok} of ${all} stations are reporting measurements.`,
      silent: list => ` No measurements from ${list}; those hours are not in the comparison.`,
      since: (name, d) => `${name} since ${d}`, and: "and",
      verdictsKicker: "In short", vars: { t: "Temperature", w: "Wind", p: "Rain" },
      varsLower: { t: "temperature", w: "wind", p: "rain" }, varsShort: { t: "Temp.", w: "Wind", p: "Rain" },
      hHead: { 6: "In 6 h", 24: "Tomorrow", 48: "In 2 d", 120: "In 5 d", 240: "In 10 d" },
      hPhrase: { 6: "6 hours ahead", 24: "for tomorrow", 48: "2 days ahead", 120: "5 days ahead", 240: "10 days ahead" },
      cell: { yr: "Yr", weathernext: "Google", too_close: "even", not_enough_data: "–" },
      storyYr: l => `Yr is closest ${l}.`, storyWn: l => `Google is closest ${l}.`,
      storyEven: l => `${cap(l)} it is too close to call.`,
      storyMixed: l => `${cap(l)} it differs between temperature, wind and rain.`,
      keyYr: "Yr is closest", keyWn: "Google is closest", keyEven: "too close to call",
      keyTap: "Tap a square to see the numbers.",
      verdictText: { yr: "Yr is closest.", weathernext: "Google is closest.", too_close: "Too close to call.",
        not_enough_data: "Not enough days for a verdict yet." },
      cellDetail: (v, h, yr, wn, u, verdict, days) => `${v}, ${h}: Yr misses by ${yr} ${u} on average, Google by ${wn} ${u}. ${verdict} Based on ${days} days.`,
      cellRain: " For rain we use the middle of Google's many outcomes.",
      notScored: "not checked", tableCaption: "Who is closest, by how far ahead the forecast is",
      tableCorner: "How far ahead",
      actualKicker: "Forecast vs what happened", place: "Place",
      actualSub: "Last 7 days, the forecast as it looked the day before.",
      cities: "Cities", otherStations: "Other stations", measured: "Measured",
      actualText: (place, yr, wn, u) => `In ${place} over the last 7 days, Yr missed by ${yr} ${u} on average` + (wn == null ? "." : `, Google by ${wn} ${u}.`),
      actualNone: "No recent numbers for this station.",
      noticeLead: "Google's terms require this notice under charts that show Google's forecast values:",
      wnHidden: "Google's forecast values are not shown here; their errors are in every score.",
      calendarKicker: "Day by day",
      calendarSub: v => `${v} · forecast for tomorrow. Each square is one day.`,
      calYr: "Yr closer", calWn: "Google closer", calEq: "about equal", calNone: "no data",
      calCount: (y, g, e) => `Yr closer on ${y} days · Google closer on ${g} days · about equal on ${e} days.`,
      calCloseCall: who => `${who} was closer on more days, but overall the difference is too small to call a winner.`,
      calOther: (who, best) => `${who} was closer on more days, but overall ${best} misses least (see the table at the top).`,
      calNote: "A day is \"about equal\" when the average errors differ by less than 5%. The calendar describes each day; only the table at the top names a winner.",
      calDay: (d, yr, wn, u) => `${d}: Yr ${yr} ${u}, Google ${wn} ${u}`,
      blend: list => `<b>Tip:</b> If you look at both forecasts for tomorrow and take the midpoint, you miss by about ${list} than with the better one alone.`,
      blendPart: (p, v) => `${p} less on ${v}`,
      frostKicker: "Below freezing", frostQuestion: "Did the forecast catch the frost?",
      frostRow: (n, p) => `${n} of 10 freezing hours forecast (${p})`,
      frostFalse: (a, b) => `Forecast frost that did not come: Yr ${a}, Google ${b}.`,
      oneIn: n => `about 1 in ${n} times`, never: "never", always: "almost every time",
      frostNote: (n, days, st) => `Hours below 0 °C, forecast for tomorrow: ${n} measured freezing hours over ${days} days at ${st} stations. Descriptive counts, not a winner test.`,
      fairKicker: "Is this fair?", readMore: "Read more",
      fair: [
        ["Yr plays at home.", "Yr adjusts its forecasts with fresh measurements from Norwegian weather stations, including several of the ones we check against."],
        ["Google's forecast is an average of many possible outcomes.", "That gives slightly smaller misses on average but can soften extreme weather. For rain we therefore use the middle outcome."],
        ["Google forecasts for squares of about 5 km.", "In steep terrain the square is often higher than the station, so the forecast comes out too cold (about 0.65 degrees per 100 metres)."],
      ],
      showDetails: "Show map, all stations and detailed numbers →", hideDetails: "Hide the details ↑",
      themeDark: "Dark", themeLight: "Light", themeToDark: "Switch to dark mode", themeToLight: "Switch to light mode",
      sourcesTitle: "Sources and terms",
      sourcesLead: "The numbers come from forecasts and measurements by MET Norway (Yr and Frost) and forecasts by Google (WeatherNext). The terms require these notices word for word:",
      openSource: "Open source", footerUpdated: "updated automatically about every 2.5 hours",
      chartLabel: "Measured and forecast over the last 7 days", calendarLabel: m => `Days in ${m}`, varGroup: "Weather type",
    },
  };
  const t = (key, ...args) => { const v = TXT[LANG][key]; return typeof v === "function" ? v(...args) : v; };

  // Headline numbers of one leaderboard block, the way the page scores them (rain: Google's median).
  const pick = (v, s) => v === "p"
    ? { yr: s.mae_yr, wn: s.mae_wn50, verdict: s.verdict_50 }
    : { yr: s.mae_yr, wn: s.mae_wn, verdict: s.verdict };
  const block = (v, h) => D.leaderboard?.[v]?.[h]?.all;

  function applyStatic() {
    document.documentElement.lang = LANG;
    document.title = t("title");
    document.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll("#lang-seg button").forEach(b => b.setAttribute("aria-pressed", b.dataset.v === LANG));
    document.getElementById("details-lang").hidden = LANG !== "nb";
    syncThemeControl();
  }

  function renderStatus() {
    const el = document.getElementById("status"), text = document.getElementById("status-text"), m = D.meta || {}, h = D.health || {};
    let warn = false, msg;
    if (!m.variables) { msg = failed.has("meta") ? t("loadError") : t("noData"); warn = failed.has("meta"); }
    else if (!m.days) msg = t("collecting");
    else if (h.last_run_failed) { warn = true; msg = t("lastFailed", relTime(h.last_run), h.last_success && relTime(h.last_success)); }
    else if (h.last_run && (Date.now() - Date.parse(h.last_run)) / 36e5 > STALE_H) { warn = true; msg = t("stale", relTime(h.last_run)); }
    else if (h.failing?.length) { warn = true; msg = t("failing", joinList(h.failing.map(k => k === "wn" ? "Google (WeatherNext)" : SOURCE_NAME[k]))); }
    else msg = t("updated", relTime(h.last_run || m.generated_at), int(m.days));
    text.textContent = msg;
    el.classList.toggle("warn", warn);

    const line = document.getElementById("stations-line");
    line.hidden = !m.stations?.length || !m.days;
    if (line.hidden) return;
    const silent = [...silentStations()];
    const all = m.stations.length, names = silent.map(([id, last]) =>
      t("since", m.stations.find(s => s.id === id).name, fmtDate(last)));
    line.textContent = t("stations", all - silent.length, all) + (silent.length ? t("silent", joinList(names)) : "");
    line.classList.toggle("warn", silent.length / all > SILENT_WARN);
  }

  // Verdict table: the existing 95 % verdicts, all days, for five horizons. The story sentences are
  // built from the same verdicts, grouped by horizon.
  function renderVerdicts() {
    const vars = ["t", "w", "p"], cols = SIMPLE_H.filter(h => vars.some(v => block(v, h)?.n));
    const verdictOf = (v, h) => { const s = block(v, h); return s?.n ? (pick(v, s).verdict || "not_enough_data") : null; };
    const groups = { yr: [], weathernext: [], too_close: [], mixed: [] };
    for (const h of cols) {
      const vs = vars.map(v => verdictOf(v, h)).filter(x => x && x !== "not_enough_data");
      if (!vs.length) continue;
      groups[vs.every(x => x === vs[0]) ? vs[0] : "mixed"].push(t("hPhrase")[h]);
    }
    // "2 dager fram og 5 dager fram" reads as "2 og 5 dager fram": shared endings are said once.
    const phrases = list => { const m = list.map(p => p.match(/^(\d+) (\S+) (fram|ahead)$/));
      if (list.length < 2 || !m.every(Boolean)) return joinList(list);
      const same = m.every(x => x[2] === m[0][2]);
      return joinList(m.map((x, i) => same && i < m.length - 1 ? x[1] : `${x[1]} ${x[2]}`)) + ` ${m[0][3]}`; };
    const story = [["yr", "storyYr"], ["weathernext", "storyWn"], ["too_close", "storyEven"], ["mixed", "storyMixed"]]
      .filter(([k]) => groups[k].length).map(([k, key]) => `<p>${esc(t(key, phrases(groups[k])))}</p>`);
    document.getElementById("s-story").innerHTML = story.join("");
    const cls = { yr: "v-yr", weathernext: "v-wn", too_close: "v-even" };
    const table = document.getElementById("verdict-table");
    table.innerHTML = `<caption class="sr-only">${esc(t("tableCaption"))}</caption>
      <tr><th scope="col"><span class="sr-only">${esc(t("tableCorner"))}</span></th>${cols.map(h => `<th scope="col">${esc(t("hHead")[h])}</th>`).join("")}</tr>
      ${vars.map(v => `<tr><th scope="row"><span class="long">${esc(t("vars")[v])}</span><span class="short" aria-hidden="true">${esc(t("varsShort")[v])}</span></th>${cols.map(h => {
        const vd = verdictOf(v, h);
        if (!vd) return `<td class="v-none"><span title="${esc(t("notScored"))}">–</span><span class="sr-only">${esc(t("notScored"))}</span></td>`;
        return `<td><button type="button" class="vcell ${cls[vd] || "v-none"}" data-cell="${v}:${h}" aria-pressed="${SS.cell === `${v}:${h}`}"
          aria-label="${esc(`${t("vars")[v]}, ${t("hPhrase")[h]}: ${t("verdictText")[vd]}`)}">${esc(t("cell")[vd])}</button></td>`;
      }).join("")}</tr>`).join("")}`;
    table.onclick = e => { const b = e.target.closest(".vcell"); if (!b) return;
      SS.cell = SS.cell === b.dataset.cell ? null : b.dataset.cell;
      table.querySelectorAll(".vcell").forEach(c => c.setAttribute("aria-pressed", c.dataset.cell === SS.cell));
      renderCellDetail(); };
    const sw = c => `<span class="swatch ${c}" aria-hidden="true"></span>`;
    document.getElementById("verdict-key").innerHTML =
      `<span>${sw("v-yr")}${esc(t("keyYr"))}</span><span>${sw("v-wn")}${esc(t("keyWn"))}</span><span>${sw("v-even")}${esc(t("keyEven"))}</span><span class="muted">${esc(t("keyTap"))}</span>`;
    renderCellDetail();
  }
  function renderCellDetail() {
    const el = document.getElementById("verdict-detail");
    const [v, h] = (SS.cell || ":").split(":"), s = SS.cell && block(v, h);
    el.hidden = !s?.n;
    if (el.hidden) { el.textContent = ""; return; }
    const p = pick(v, s), d = v === "p" ? 2 : 1;
    el.textContent = t("cellDetail", t("vars")[v], t("hPhrase")[h], num(p.yr, d), num(p.wn, d), UNIT[v],
      t("verdictText")[p.verdict || "not_enough_data"], int(s.days)) + (v === "p" ? t("cellRain") : "");
  }

  function varSeg(id, key, onChange) {
    const el = document.getElementById(id);
    el.setAttribute("aria-label", t("varGroup"));
    el.innerHTML = ["t", "w", "p"].map(v => `<button type="button" data-v="${v}" aria-pressed="${v === SS[key]}">${esc(t("vars")[v])}</button>`).join("");
    el.onclick = e => { const b = e.target.closest("button"); if (!b) return; SS[key] = b.dataset.v; onChange(); };
  }

  // Forecast vs what happened: recent/<station>.json (24 h ahead, last 7 days), Oslo by default.
  // The sentence describes; it never names a winner.
  let actualRequest = 0;
  async function renderActual() {
    const m = D.meta, v = SS.actualVar, request = ++actualRequest;
    document.getElementById("s-actual-sub").textContent = t("actualSub");
    varSeg("s-actual-var", "actualVar", renderActual);
    const sel = document.getElementById("s-station");
    if (!m.stations.some(s => s.id === SS.station)) SS.station = CITY_IDS.find(id => m.stations.some(s => s.id === id)) || m.stations[0]?.id;
    const cities = CITY_IDS.map(id => m.stations.find(s => s.id === id)).filter(Boolean);
    const others = m.stations.filter(s => !CITY_IDS.includes(s.id)).sort((a, b) => a.name.localeCompare(b.name, "nb"));
    const opt = s => `<option value="${esc(s.id)}" ${s.id === SS.station ? "selected" : ""}>${esc(s.name)}</option>`;
    sel.innerHTML = (cities.length ? `<optgroup label="${esc(t("cities"))}">${cities.map(opt).join("")}</optgroup>` : "") +
      `<optgroup label="${esc(t("otherStations"))}">${others.map(opt).join("")}</optgroup>`;
    sel.onchange = () => { SS.station = sel.value; store.set("wx-station", sel.value); renderActual(); };
    let rec = null;
    try { rec = await fetch(`${DATA}recent/${SS.station}.json`).then(r => r.ok ? r.json() : null); } catch (e) {}
    if (request !== actualRequest) return;
    const text = document.getElementById("s-actual-text"), notice = document.getElementById("s-actual-notice");
    const chartBox = document.querySelector("#s-actual .s-chart");
    const station = m.stations.find(s => s.id === SS.station);
    const obs = rec?.[`obs_${v}`], yr = rec?.[`yr_${v}`], wn = rec?.[v === "p" ? "wn_p_p50" : `wn_${v}`];
    if (!rec || !obs?.some(x => x != null)) {
      chartBox.hidden = true; notice.innerHTML = ""; text.textContent = t("actualNone");
      if (charts["s-actual-chart"]) { charts["s-actual-chart"].destroy(); delete charts["s-actual-chart"]; }
      return;
    }
    chartBox.hidden = false;
    const hasWn = !!wn?.some(x => x != null);
    // Both averages over the same hours (measured, Yr and, when shown, Google all present).
    const mae = f => { const e = obs.map((o, i) => o != null && yr?.[i] != null && (!hasWn || wn[i] != null) ? Math.abs(f[i] - o) : null)
      .filter(x => x != null); return e.length ? e.reduce((a, b) => a + b, 0) / e.length : null; };
    const d = v === "p" ? 2 : 1;
    text.textContent = t("actualText", station.name, num(mae(yr), d), hasWn ? num(mae(wn), d) : null, UNIT[v]);
    const ds = [line(t("measured"), obs, css("--obs"), { pointRadius: 0, borderWidth: 3 }),
                line("Yr", yr, css("--yr"), { pointRadius: 0 })];
    if (hasWn) ds.push(line("Google", wn, css("--wn"), { pointRadius: 0 }));
    notice.innerHTML = hasWn ? `<p class="muted s-note">${esc(t("noticeLead"))}</p><div lang="en">${wnNotice()}</div>`
      : `<p class="muted s-note">${esc(t("wnHidden"))}</p>`;
    const o = baseOptions(UNIT[v]);
    o.scales.y.beginAtZero = v !== "t";
    o.scales.y.title.display = true;
    o.scales.y.ticks.callback = x => num(x, v === "p" ? 1 : 0);
    // One tick per day, at local midnight, labelled with the weekday; the tooltip has the hour.
    const days = rec.time.map(x => fmtDate(x, { hour: "2-digit", hourCycle: "h23" }) === "00" ? fmtDate(x, { weekday: "short" }) : "");
    Object.assign(o.scales.x.ticks, { autoSkip: false, maxRotation: 0, callback: (_, i) => days[i] || null });
    o.scales.x.grid = { display: true, color: (c) => days[c.index] ? css("--grid") : "transparent" };
    o.plugins.tooltip.callbacks.label = c => ` ${c.dataset.label}: ${num(c.parsed.y, d)} ${UNIT[v]}`;
    document.getElementById("s-actual-chart").setAttribute("aria-label", `${t("chartLabel")}: ${station.name}`);
    chart("s-actual-chart", { type: "line", options: o, data: {
      labels: rec.time.map(x => fmtDate(x, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })), datasets: ds } });
  }

  // Calendar: one square per day from views.json → trend (24 h ahead, all days). Descriptive only.
  function renderCalendar() {
    const v = SS.calVar, m = D.meta, el = document.getElementById("calendar");
    varSeg("s-calendar-var", "calVar", renderCalendar);
    document.getElementById("s-calendar-sub").textContent = t("calendarSub", t("vars")[v]);
    const rows = D.views?.all?.trend?.[v]?.["24"] || [], byDay = new Map(rows.map(r => [r.day, r]));
    const { start, end } = m.periods?.all || { start: m.first_day, end: m.last_day };
    const kind = r => { if (!r || r.yr == null || r.wn == null) return "none";
      const gap = (r.wn - r.yr) / Math.max(r.yr, r.wn, 1e-9);
      return gap >= EQUAL_GAP ? "yr" : gap <= -EQUAL_GAP ? "wn" : "eq"; };
    const months = new Map(), count = { yr: 0, wn: 0, eq: 0 };
    if (start && end) for (let ts = Date.parse(start + "T00:00:00Z"); ts <= Date.parse(end + "T00:00:00Z"); ts += 864e5) {
      const day = new Date(ts).toISOString().slice(0, 10), r = byDay.get(day), k = kind(r);
      if (k !== "none") count[k]++;
      if (!months.has(day.slice(0, 7))) months.set(day.slice(0, 7), []);
      months.get(day.slice(0, 7)).push({ day, r, k });
    }
    const d = v === "p" ? 2 : 1;
    const label = { yr: t("calYr"), wn: t("calWn"), eq: t("calEq"), none: t("calNone") };
    el.innerHTML = [...months].map(([ym, days]) => {
      const name = utcDay(ym + "-15", { month: "short" });
      const full = utcDay(ym + "-15", { month: "long", year: "numeric" });
      const pad = +days[0].day.slice(8) - 1;  // so each column is the same day of the month
      return `<div class="cal-row"><span class="cal-month" aria-hidden="true">${esc(name)}</span><div class="cal-days" role="list" aria-label="${esc(t("calendarLabel", full))}">${
        '<span class="cal-pad"></span>'.repeat(pad)}${days.map(x => {
          const tip = x.k !== "none" ? t("calDay", utcDay(x.day), num(x.r.yr, d), num(x.r.wn, d), UNIT[v]) : `${utcDay(x.day)}: ${label.none}`;
          return `<span role="listitem" class="cal-day c-${x.k}" title="${esc(tip)}" aria-label="${esc(`${tip} (${label[x.k]})`)}"></span>`;
        }).join("")}</div></div>`;
    }).join("");
    const sw = c => `<span class="cal-day c-${c}" aria-hidden="true"></span>`;
    document.getElementById("calendar-key").innerHTML = ["yr", "wn", "eq", "none"].map(k => `<span>${sw(k)}${esc(label[k])}</span>`).join("");
    let sentence = t("calCount", count.yr, count.wn, count.eq);
    const s = block(v, 24), verdict = s?.n ? pick(v, s).verdict : null;
    const leader = count.yr > count.wn ? "yr" : count.wn > count.yr ? "weathernext" : null;
    const who = k => (k === "yr" ? "Yr" : "Google");
    if (leader && verdict === "too_close") sentence += " " + t("calCloseCall", who(leader));
    else if (leader && (verdict === "yr" || verdict === "weathernext") && verdict !== leader) sentence += " " + t("calOther", who(leader), who(verdict));
    document.getElementById("calendar-count").textContent = sentence;
    document.getElementById("calendar-note").textContent = t("calNote");
  }

  // Blend tip: only where the existing test says the midpoint is better (as in the details).
  function renderBlend() {
    const el = document.getElementById("s-blend");
    const parts = ["t", "w"].map(v => [v, block(v, 24)])
      .filter(([, s]) => s?.n && s.verdict_avg === "better" && Number.isFinite(s.avg_gain))
      .map(([v, s]) => t("blendPart", pctOf(s.avg_gain), t("varsLower")[v]));
    el.hidden = !parts.length;
    el.innerHTML = parts.length ? t("blend", esc(joinList(parts))) : "";
  }

  // Frost: views.json → practical (hours below 0 °C, 24 h ahead, all stations, all days).
  function renderFrost() {
    const g = D.views?.all?.practical?.t?.["24"]?.all, card = document.getElementById("s-frost");
    card.hidden = !(g?.events && g.yr?.pod != null && g.wn?.pod != null);
    if (card.hidden) return;
    const dots = (x, p) => { const n = Math.round(x * 10);
      return `<span class="dots" aria-hidden="true">${Array.from({ length: 10 }, (_, i) => `<span class="dot10 ${i < n ? p : "off"}"></span>`).join("")}</span>`; };
    document.getElementById("frost-rows").innerHTML = [["yr", "Yr"], ["wn", "Google"]].map(([p, name]) =>
      `<div class="icon-row"><span class="icon-name">${name}</span>${dots(g[p].pod, p)}<span class="icon-text">${esc(t("frostRow", Math.round(g[p].pod * 10), pctOf(g[p].pod)))}</span></div>`).join("");
    const oneIn = far => far == null ? "–" : far === 0 ? t("never") : Math.round(1 / far) <= 1 ? t("always") : t("oneIn", Math.round(1 / far));
    document.getElementById("frost-false").textContent = t("frostFalse", oneIn(g.yr.far), oneIn(g.wn.far));
    document.getElementById("frost-note").textContent = t("frostNote", int(g.events), int(g.days), int(g.stations));
  }

  function renderFair() {
    const list = document.getElementById("fair-list");
    list.innerHTML = t("fair").map(([lead, rest]) =>
      `<li><b>${esc(lead)}</b> ${esc(rest)} <a href="#about" class="read-more">${esc(t("readMore"))}</a></li>`).join("");
    list.onclick = e => {
      if (!e.target.closest(".read-more")) return;
      e.preventDefault();
      setDetails(true);
      const about = document.getElementById("about");
      about.open = true;
      about.scrollIntoView({ block: "start" });
    };
  }

  function renderSources() {
    const link = s => esc(s).replace(/https?:\/\/[^\s<]+[^\s<.,)]/g, u => `<a href="${u}" rel="noopener">${u}</a>`);
    document.getElementById("s-attrib").innerHTML = (D.meta?.attribution || []).map(a => `<span>${link(a)}</span>`).join("<br>");
  }

  function renderSimple() {
    applyStatic();
    document.getElementById("intro").textContent = t("intro", D.meta?.stations?.length || "");
    renderStatus();
    const ok = !!D.meta?.variables && !!D.meta?.days;
    document.querySelectorAll("#simple .s-card").forEach(el => { el.hidden = !ok; });
    document.getElementById("details-toggle").hidden = !D.meta?.variables;
    document.getElementById("s-sources").hidden = !D.meta?.variables;
    document.getElementById("details-toggle").textContent = t(document.getElementById("details").hidden ? "showDetails" : "hideDetails");
    if (!ok) return;
    renderVerdicts(); renderActual(); renderCalendar(); renderBlend(); renderFrost(); renderFair(); renderSources();
  }

  // The expert cards: shown on request, remembered, and opened by ?visning=detaljert (or ?view=detailed).
  let detailsReady = false;
  function setDetails(open, remember = true) {
    const el = document.getElementById("details"), btn = document.getElementById("details-toggle");
    el.hidden = !open;
    btn.setAttribute("aria-expanded", open);
    btn.textContent = t(open ? "hideDetails" : "showDetails");
    if (remember) store.set("wx-view", open ? "detailed" : "simple");
    if (!open || !D.meta?.variables) return;
    if (!detailsReady) { initDetails(); detailsReady = true; }
    render();
    if (map) map.invalidateSize();
  }

  function render() {
    renderAnswer(); renderTiles(); renderPractical(); renderHorizon(); renderSteadiness(); renderBias(); renderTrend(); renderMap(); renderReplays(); renderPatterns();
    // Hide wholly empty sections, keeping selectors available when another horizon has data.
    document.getElementById("practical").hidden = !Object.values(selected("practical")?.[S.v] || {}).some(groups => Object.values(groups).some(g => g.n));
    document.getElementById("horizons").hidden = !Object.values(D.leaderboard?.[S.v] || {}).some(h => h[S.period]?.n);
    document.getElementById("trend").hidden = !Object.values(selected("trend")?.[S.v] || {}).some(rows => rows.length);
    document.getElementById("patterns-section").hidden = !Object.values(selected("patterns")?.[S.v] || {}).some(rows => rows.length);
    document.getElementById("more-analysis").hidden = [...document.querySelectorAll("#more-analysis > section")].every(el => el.hidden);
    document.querySelectorAll(".section-nav a").forEach(a => { a.hidden = document.querySelector(a.getAttribute("href")).hidden; });
  }

  const themeToggle = document.getElementById("theme-toggle");
  const systemTheme = matchMedia("(prefers-color-scheme: dark)");
  let hasThemeChoice = false;
  try { hasThemeChoice = ["light", "dark"].includes(localStorage.getItem("wx-theme")); } catch {}
  const syncThemeControl = () => {
    const toLight = document.documentElement.dataset.theme === "dark";
    themeToggle.textContent = t(toLight ? "themeLight" : "themeDark");
    themeToggle.setAttribute("aria-label", t(toLight ? "themeToLight" : "themeToDark"));
  };
  // Charts read the theme colours when drawn, so a theme change redraws what is visible.
  const redraw = () => {
    if (!D.meta?.variables) return;
    renderSimple();
    if (!document.getElementById("details").hidden) render();
  };
  systemTheme.addEventListener("change", e => {
    if (hasThemeChoice) return;
    document.documentElement.dataset.theme = e.matches ? "dark" : "light";
    syncThemeControl();
    redraw();
  });
  syncThemeControl();
  themeToggle.onclick = () => {
    const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = theme;
    hasThemeChoice = true;
    try { localStorage.setItem("wx-theme", theme); } catch {}
    syncThemeControl();
    redraw();
  };
  document.getElementById("lang-seg").onclick = e => {
    const b = e.target.closest("button"); if (!b || b.dataset.v === LANG) return;
    LANG = b.dataset.v;
    store.set("wx-lang", LANG);
    renderSimple();
  };
  document.getElementById("details-toggle").onclick = () => setDetails(document.getElementById("details").hidden);

  // One-time setup of the expert cards (English), run when they are first shown.
  function initDetails() {
    const m = D.meta;
    const updated = D.health?.generated_at ? "" : ` · updated ${m.generated_at.replace("T", " ").slice(0, 16)} UTC`;
    document.getElementById("fresh").textContent = m.days
      ? `${m.days} scored days · ${m.stations.length} active collection stations${updated}`
      : "Collecting… the first scores appear about a day after collection starts.";
    // One line per notice; URLs become links (text is escaped first).
    const link = s => esc(s).replace(/https?:\/\/[^\s<]+[^\s<.,)]/g, u => `<a href="${u}" rel="noopener">${u}</a>`);
    document.getElementById("attrib").innerHTML = (m.attribution || []).map(a => `<span>${link(a)}</span>`).join("<br>");
    seg(document.getElementById("var-seg"), Object.entries(m.variables).map(([k, v]) => [k, k === "p" ? "Precipitation" : v.name]),
        () => S.v, v => (S.v = v));
    seg(document.getElementById("period-seg"), [["all", "All time"], ["last30", "Last 30 days"]],
        () => S.period, v => (S.period = v));
    seg(document.getElementById("horizon-view"), [["diff", "Difference"], ["mae", "Error size"]],
        () => S.hView, v => (S.hView = v));
  }

  load().then(() => {
    const m = D.meta || {};
    renderHealth();
    renderSummary();
    renderSimple();
    if (m.demo) document.querySelector(".hero").insertAdjacentHTML("afterbegin",
      `<p class="badge" style="margin-bottom:8px">Demo data: made-up numbers for previewing the layout</p>`);
    if (!m.variables) return;
    const asked = params.get("visning") === "detaljert" || params.get("view") === "detailed";
    if (asked || store.get("wx-view") === "detailed") setDetails(true, false);
  });
})();
