/* Optional browser regression check: node tests/scorecard_ui_test.cjs DATA_DIR [SCREENSHOT_DIR].
   Requires Playwright on NODE_PATH (or installed locally); uses existing Chrome on Windows.
   Only reads the site/data fixtures and writes optional screenshots. No collection or deployment.
   WX_TEST_MAP_TILES=1 permits map tiles; WX_TEST_FONTS=1 permits Google Fonts. */
const fs = require('node:fs/promises');
const { existsSync } = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

async function main() {
  assert(process.argv[2], 'Provide a disposable exported data directory.');
  const data = path.resolve(process.argv[2]);
  const site = path.resolve(__dirname, '../site');
  const shots = process.argv[3] && path.resolve(process.argv[3]);
  if (shots) await fs.mkdir(shots, { recursive: true });
  const meta = JSON.parse(await fs.readFile(path.join(data, 'meta.json'), 'utf8'));
  // Old read-only fixtures predate the additive offshore export field.
  const heights = JSON.parse(await fs.readFile(path.resolve(__dirname, '../config/wn_heights.json'), 'utf8'));
  for (const station of meta.stations) station.offshore = heights.stations[station.id]?.offshore ?? null;
  const leaderboardFixture = JSON.parse(await fs.readFile(path.join(data, 'leaderboard.json'), 'utf8'));
  const views = JSON.parse(await fs.readFile(path.join(data, 'views.json'), 'utf8'));
  const events = JSON.parse(await fs.readFile(path.join(data, 'events.json'), 'utf8'));
  const errors = [];
  const server = http.createServer(async (req, res) => {
    try {
      const relative = decodeURIComponent(req.url.split('?')[0]);
      const root = relative.startsWith('/data/') ? data : site;
      const file = path.resolve(root, relative.startsWith('/data/') ? relative.slice(6) : relative.slice(1) || 'index.html');
      if (!file.startsWith(root + path.sep)) { res.writeHead(403); return res.end(); }
      const buffer = file === path.join(data, 'meta.json') ? JSON.stringify(meta) : await fs.readFile(file);
      res.setHeader('Content-Type', { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css',
        '.json': 'application/json', '.png': 'image/png' }[path.extname(file)] || 'application/octet-stream');
      res.end(buffer);
    } catch { res.writeHead(404); res.end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const url = `http://127.0.0.1:${server.address().port}`;
  const executablePath = process.env.WX_BROWSER_EXECUTABLE ||
    ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(existsSync);
  let browser;
  try {
    browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
    const layouts = [];
    for (const [name, width, height] of [['desktop', 1280, 900], ['mobile', 375, 812], ['narrow', 320, 812]]) {
      for (const colorScheme of ['light', 'dark']) {
        const context = await browser.newContext({ viewport: { width, height }, colorScheme });
        const page = await context.newPage();
        await page.route('**/*', route => {
          const request = route.request().url();
          if (request.startsWith(url) || (process.env.WX_TEST_MAP_TILES === '1' && request.startsWith('https://tile.openstreetmap.org/'))) return route.continue();
          if (process.env.WX_TEST_FONTS === '1' && /^https:\/\/fonts\.(googleapis|gstatic)\.com\//.test(request)) return route.continue();
          return route.abort();
        });
        page.on('pageerror', error => errors.push(error.message));
        await page.goto(url, { waitUntil: 'networkidle' });
        await page.waitForFunction(() => document.querySelector('#tiles .tile'));
        await page.evaluate(() => document.fonts.ready);
        assert.equal(await page.locator('html').getAttribute('data-theme'), colorScheme, 'First visit follows system theme');
        const nextTheme = colorScheme === 'light' ? 'dark' : 'light';
        assert.equal(await page.locator('#theme-toggle').textContent(), nextTheme === 'dark' ? 'Dark mode' : 'Light mode');
        await page.emulateMedia({ colorScheme: nextTheme });
        await page.waitForFunction(theme => document.documentElement.dataset.theme === theme, nextTheme);
        await page.locator('#theme-toggle').click();
        assert.equal(await page.locator('html').getAttribute('data-theme'), colorScheme);
        await page.reload({ waitUntil: 'networkidle' });
        await page.waitForFunction(() => document.querySelector('#tiles .tile'));
        assert.equal(await page.locator('html').getAttribute('data-theme'), colorScheme, 'Explicit choice survives reload and overrides system');
        await page.evaluate(() => document.fonts.ready);
        const layout = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
          height: document.documentElement.scrollHeight, answerY: document.getElementById('answer').getBoundingClientRect().top,
          tilesY: document.getElementById('tiles').getBoundingClientRect().top }));
        assert(layout.scrollWidth <= width + 1, `${name}: page overflows horizontally`);
        assert(layout.answerY < height, `${name}: answer is below the first screen`);
        assert(layout.tilesY < height, `${name}: comparison is below the first screen`);
        assert.equal(await page.locator('#monthly').evaluate(el => el.open), false);
        // Scrolling the map into view must leave its controls unobstructed on phones.
        await page.locator('#map').scrollIntoViewIfNeeded();
        const zoom = page.locator('.leaflet-control-zoom-in');
        const target = await zoom.boundingBox();
        assert(target.width >= 44 && target.height >= 44, 'Map zoom has a 44 px touch target');
        assert(await zoom.evaluate(el => {
          const r = el.getBoundingClientRect();
          return el.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2));
        }), 'Map zoom is not covered by filters');
        assert(await page.locator('.seg button').evaluateAll(buttons => buttons.every(b => b.getBoundingClientRect().height >= 44)), 'Filters have 44 px touch targets');
        assert(await page.locator('#scope').evaluate(el => el.getBoundingClientRect().top < document.getElementById('answer').getBoundingClientRect().top), 'Dates appear with the verdict context');
        assert((await page.locator('#map-key').textContent()).includes('No paired data'));
        assert((await page.locator('#map-note').textContent()).includes('not statistical winner verdicts'));
        assert(await page.locator('.diff-gap small').evaluateAll(labels => labels.length > 0 && labels.every(el => el.getBoundingClientRect().height >= 12)), 'Percentage meaning is visually readable');
        const score = leaderboardFixture.t['24'].all;
        assert.equal(await page.locator('#blend-finding').isVisible(), score.verdict_avg === 'better');
        const eligible = meta.stations.filter(s => typeof s.offshore === 'boolean' && views.all.stations.t['24'][s.id]?.days >= meta.min_days_for_verdict);
        const offshore = eligible.filter(s => s.offshore).map(s => views.all.stations.t['24'][s.id]);
        assert((await page.locator('#map-pattern').textContent()).includes(`WeatherNext lower at ${offshore.filter(r => r.wn < r.yr).length} of ${offshore.length} offshore stations`));
        assert(await page.locator('.station-caveat').count() > 0);
        assert.equal(await page.locator('.foot a').getAttribute('href'), 'https://github.com/Stranden1/weather-forecast-verification');
        assert(await page.evaluate(() => {
          const [published, adjusted] = Chart.getChart('horizon-chart').data.datasets;
          return published.pointRadius > adjusted.pointRadius && adjusted.secondary && adjusted.pointBackgroundColor !== adjusted.pointBorderColor;
        }));
        for (const section of ['practical', 'horizons', 'monthly', 'about']) {
          assert.equal(await page.locator('#' + section).evaluate(el => getComputedStyle(el).backgroundColor), 'rgba(0, 0, 0, 0)');
        }
        if (events.length) {
          await page.waitForSelector('#replay-chart');
          assert.deepEqual(await page.locator('#replay-body .wn-notice').evaluate(el => el.textContent), meta.wn_value_attribution.join(''));
        }
        await page.evaluate(() => scrollTo(0, 0));
        if (shots) {
          await page.screenshot({ path: path.join(shots, `${name}-${colorScheme}-top.png`) });
          await page.locator('#map').scrollIntoViewIfNeeded();
          if (process.env.WX_TEST_MAP_TILES === '1') await page.waitForFunction(() => [...document.querySelectorAll('#map img.leaflet-tile')].every(i => i.complete && i.naturalWidth > 0));
          await page.evaluate(() => scrollTo(0, 0));
          await page.screenshot({ path: path.join(shots, `${name}-${colorScheme}.png`), fullPage: true });
          await page.locator('#station-section').screenshot({ path: path.join(shots, `${name}-${colorScheme}-stations.png`) });
        }
        const dot = page.locator('#map .map-marker').first();
        const overviewSize = await dot.evaluate(el => el.getBoundingClientRect().width);
        assert(overviewSize <= 8.1, 'Overview markers stay small');
        const markerPosition = () => page.locator('#map .leaflet-marker-icon').evaluateAll(icons => icons.map(el => el.style.transform).join('|'));
        // Pan a real station toward the centre before capturing a regional zoom.
        const stationBox = await page.locator('#map .leaflet-marker-icon').first().boundingBox();
        const bounds = await page.locator('#map').boundingBox();
        const panBefore = await page.locator('#map .leaflet-map-pane').evaluate(el => el.style.transform);
        await page.mouse.move(stationBox.x + stationBox.width / 2 + 26, stationBox.y + stationBox.height / 2 + 26);
        await page.mouse.down();
        await page.mouse.move(bounds.x + bounds.width / 2 + 26, bounds.y + bounds.height / 2 + 26, { steps: 10 });
        await page.waitForTimeout(100); // release after the drag settles, without fling inertia
        await page.mouse.up();
        await page.waitForFunction(before => document.querySelector('#map .leaflet-map-pane').style.transform !== before,
          panBefore);
        const waitForZoom = before => page.waitForFunction(before =>
          [...document.querySelectorAll('#map .leaflet-marker-icon')].map(el => el.style.transform).join('|') !== before &&
          !document.querySelector('#map .leaflet-map-pane').classList.contains('leaflet-zoom-anim'), before);
        const clickZoom = async button => {
          const before = await markerPosition();
          await button.click();
          await waitForZoom(before);
        };
        for (let i = 0; i < 4; i++) await clickZoom(zoom);
        await page.waitForFunction(size => document.querySelector('#map .map-marker').getBoundingClientRect().width > size, overviewSize);
        if (shots) {
          if (process.env.WX_TEST_MAP_TILES === '1') await page.waitForFunction(() => [...document.querySelectorAll('#map img.leaflet-tile')].every(i => i.complete && i.naturalWidth > 0));
          await page.locator('#map').screenshot({ path: path.join(shots, `${name}-${colorScheme}-map-zoomed.png`) });
        }
        for (let i = 0; i < 4; i++) await clickZoom(page.locator('.leaflet-control-zoom-out'));
        await page.waitForFunction(() => document.querySelector('#map .map-marker').getBoundingClientRect().width <= 8.1);
        if (name === 'desktop') {
          const mapBox = await page.locator('#map').boundingBox();
          const before = await markerPosition();
          await page.mouse.move(mapBox.x + mapBox.width / 2, mapBox.y + mapBox.height / 2);
          await page.mouse.wheel(0, -300);
          await waitForZoom(before);
          const zoomed = await markerPosition();
          await page.mouse.wheel(0, 300);
          await waitForZoom(zoomed);
        }
        // Inspect the redesigned lower sections expanded at every size and theme.
        for (const id of ['more-analysis', 'monthly', 'about']) await page.locator('#' + id + ' > summary').click();
        assert((await page.evaluate(() => document.documentElement.scrollWidth)) <= width + 1);
        if (shots) {
          await page.locator('#more-analysis').screenshot({ path: path.join(shots, `${name}-${colorScheme}-analysis.png`) });
          await page.locator('#monthly').screenshot({ path: path.join(shots, `${name}-${colorScheme}-monthly.png`) });
          await page.locator('#about').screenshot({ path: path.join(shots, `${name}-${colorScheme}-methodology.png`) });
        }
        for (const id of ['more-analysis', 'monthly', 'about']) await page.locator('#' + id + ' > summary').click();
        layouts.push({ name, colorScheme, ...layout });
        if (name === 'mobile' && colorScheme === 'light') {
          await page.locator('#var-seg button[data-v="w"]').click();
          await page.locator('#event-region').selectOption('land');
          const expected = views.all.practical.w['24'].land;
          assert((await page.locator('#practical-body').textContent()).includes(expected.events.toLocaleString() + ' observed event hours'));
          if (shots) {
            await page.setViewportSize({ width, height: 1200 });
            await page.locator('#practical').screenshot({ path: path.join(shots, 'strong-wind-land.png') });
            await page.setViewportSize({ width, height });
          }
          await page.locator('#var-seg button[data-v="p"]').click();
          await page.locator('#more-analysis > summary').click();
          assert((await page.locator('#patterns').textContent()).includes('WeatherNext (median)'));
          assert((await page.locator('#station-panel').textContent()).includes('WeatherNext (median)'));
          assert((await page.evaluate(() => Chart.getChart('trend-chart').data.datasets.map(d => d.label))).includes('WeatherNext (median), 7-day'));
          await page.locator('#period-seg button[data-v="last30"]').click();
          assert((await page.locator('#trend-table tr').nth(1).textContent()).includes(meta.periods.last30.start));
          await page.locator('#var-seg button[data-v="t"]').click();
          const adjusted = meta.stations.find(s => {
            const r = views.last30.stations.t['24']?.[s.id];
            return r?.wnh != null && r.wnh !== r.wn;
          });
          if (adjusted) {
            await page.locator('#station-pick').selectOption(adjusted.id);
            await page.waitForFunction(() => document.getElementById('station-panel').textContent.includes('Height-adjusted means'));
            await page.locator('#station-pick').selectOption('');
          }
          await page.locator('#trend-h').selectOption('120');
          const trend = await page.evaluate(() => Chart.getChart('trend-chart').data.datasets.map(d => ({ data: d.data, spanGaps: d.spanGaps })));
          assert.equal(trend[0].spanGaps, false);
          // A keyboard-accessible selector covers every active station, including ones outside the top differences.
          assert.equal(await page.locator('#station-pick option').count(), meta.stations.length + 1);
          const sid = meta.stations.find(s => views.all.stations.p['24']?.[s.id])?.id;
          assert(sid, 'Fixture needs a station with paired rain data.');
          await page.locator('#station-pick').selectOption(sid);
          await page.waitForSelector('#station-chart');
          await page.locator('#var-seg button[data-v="p"]').click();
          await page.waitForFunction(() => Chart.getChart('station-chart')?.data.datasets.some(d => d.label === 'WeatherNext (median)'));
          assert((await page.locator('#station-table').textContent()).includes('WeatherNext (median)'));
          await page.locator('#station-pick').selectOption('');
          assert((await page.locator('#station-panel').textContent()).includes('Biggest differences'));
          // Exercise a one-point replay without changing the exported fixture.
          if (events.length) {
            await page.locator('#period-seg button[data-v="all"]').click();
            await page.route('**/data/events/*.json', async route => {
              const id = path.basename(new URL(route.request().url()).pathname);
              const event = JSON.parse(await fs.readFile(path.join(data, 'events', id), 'utf8'));
              event.points = event.points.slice(0, 1);
              await route.fulfill({ contentType: 'application/json', body: JSON.stringify(event) });
            });
            await page.locator('#replay-pick').selectOption(events[0].id);
            await page.waitForFunction(() => Chart.getChart('replay-chart')?.data.datasets.find(d => d.label === 'Measured')?.pointRadius > 0);
            assert((await page.locator('#replay-table').textContent()).includes('Measured'));
          }
          assert((await page.evaluate(() => document.documentElement.scrollWidth)) <= width + 1);
        }
        await context.close();
      }
    }
    // Synthetic display cases stay in intercepted responses; fixture files remain read-only.
    const context = await browser.newContext({ viewport: { width: 320, height: 812 }, colorScheme: 'light' });
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', route => route.request().url().startsWith(url) ? route.continue() : route.abort());
    const sample = structuredClone(views);
    const ids = meta.stations.slice(0, 4).map(s => s.id);
    assert.equal(ids.length, 4);
    sample.all.stations.t['24'][ids[0]] = { yr: 1, wn: 2, n: 168, days: 7 };
    sample.all.stations.t['24'][ids[1]] = { yr: 2, wn: 1, n: 168, days: 7 };
    sample.all.stations.t['24'][ids[2]] = { yr: 1, wn: 1, n: 168, days: 7 };
    delete sample.all.stations.t['24'][ids[3]];
    await page.route('**/data/views.json', route => route.fulfill({ contentType: 'application/json', body: JSON.stringify(sample) }));
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.waitForSelector('#map .leaflet-marker-icon');
    for (const [i, kind] of ['yr', 'wn', 'equal', 'missing'].entries()) {
      const marker = page.locator('#map .leaflet-marker-icon').nth(i);
      assert(await marker.evaluate((el, kind) => !!el.querySelector(`.map-marker-${kind}`), kind));
    }
    await page.locator('#map .leaflet-marker-icon').nth(3).focus();
    await page.keyboard.press('Enter');
    await page.waitForFunction(id => document.getElementById('station-pick').value === id, ids[3]);
    const leaderboard = JSON.parse(await fs.readFile(path.join(data, 'leaderboard.json'), 'utf8'));
    for (const verdict of ['yr', 'weathernext', 'too_close', 'not_enough_data']) {
      const scores = structuredClone(leaderboard);
      scores.t['24'].all.verdict = verdict;
      scores.t['24'].all.verdict_avg = verdict === 'yr' ? 'better' : verdict === 'weathernext' ? 'worse' : verdict;
      await page.route('**/data/leaderboard.json', route => route.fulfill({ contentType: 'application/json', body: JSON.stringify(scores) }));
      await page.reload({ waitUntil: 'networkidle' });
      await page.waitForSelector('#tiles .tile');
      assert.equal(await page.locator('#blend-finding').isVisible(), verdict === 'yr');
      assert.equal(await page.locator('#tiles .winner-label').count(), ['yr', 'weathernext'].includes(verdict) ? 1 : 0);
      assert.equal(await page.locator('#tiles .v').nth(0).evaluate(el => el.getBoundingClientRect().top),
        await page.locator('#tiles .v').nth(1).evaluate(el => el.getBoundingClientRect().top), 'Score values align when a provider has a verdict');
      assert((await page.evaluate(() => document.documentElement.scrollWidth)) <= 320);
      await page.unroute('**/data/leaderboard.json');
    }
    await page.route('**/data/leaderboard.json', route => route.fulfill({ contentType: 'application/json', body: '{}' }));
    await page.route('**/data/views.json', route => route.fulfill({ contentType: 'application/json', body: '{}' }));
    await page.route('**/data/summary.json', route => route.fulfill({ contentType: 'application/json', body: '{}' }));
    await page.route('**/data/events.json', route => route.fulfill({ contentType: 'application/json', body: '[]' }));
    await page.reload({ waitUntil: 'networkidle' });
    for (const id of ['blend-finding', 'map-pattern', 'practical', 'horizons', 'more-analysis', 'monthly', 'replays']) {
      assert.equal(await page.locator('#' + id).isVisible(), false, `${id} hidden with empty data`);
    }
    await context.close();
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ layouts, errors, screenshots: shots || null }));
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error.stack); process.exitCode = 1; });
