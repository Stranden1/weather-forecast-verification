/* Optional browser regression check: node tests/scorecard_ui_test.cjs DATA_DIR [SCREENSHOT_DIR].
   Requires Playwright on NODE_PATH (or installed locally); uses existing Chrome on Windows.
   Only reads the site/data fixtures and writes optional screenshots. No collection or deployment.
   WX_TEST_MAP_TILES=1 permits map tiles; otherwise all external browser requests are blocked. */
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
  const views = JSON.parse(await fs.readFile(path.join(data, 'views.json'), 'utf8'));
  const events = JSON.parse(await fs.readFile(path.join(data, 'events.json'), 'utf8'));
  const errors = [];
  const server = http.createServer(async (req, res) => {
    try {
      const relative = decodeURIComponent(req.url.split('?')[0]);
      const root = relative.startsWith('/data/') ? data : site;
      const file = path.resolve(root, relative.startsWith('/data/') ? relative.slice(6) : relative.slice(1) || 'index.html');
      if (!file.startsWith(root + path.sep)) { res.writeHead(403); return res.end(); }
      const buffer = await fs.readFile(file);
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
          return route.abort();
        });
        page.on('pageerror', error => errors.push(error.message));
        await page.goto(url, { waitUntil: 'networkidle' });
        await page.waitForFunction(() => document.querySelector('#tiles .tile'));
        const layout = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
          height: document.documentElement.scrollHeight, answerY: document.getElementById('answer').getBoundingClientRect().top,
          tilesY: document.getElementById('tiles').getBoundingClientRect().top }));
        assert(layout.scrollWidth <= width + 1, `${name}: page overflows horizontally`);
        assert(layout.answerY < height, `${name}: answer is below the first screen`);
        assert(layout.tilesY < height, `${name}: comparison is below the first screen`);
        assert.equal(await page.locator('#monthly').evaluate(el => el.open), false);
        if (shots) {
          await page.screenshot({ path: path.join(shots, `${name}-${colorScheme}-top.png`) });
          await page.locator('#map').scrollIntoViewIfNeeded();
          if (process.env.WX_TEST_MAP_TILES === '1') await page.waitForFunction(() => [...document.querySelectorAll('#map img.leaflet-tile')].every(i => i.complete && i.naturalWidth > 0));
          await page.evaluate(() => scrollTo(0, 0));
          await page.screenshot({ path: path.join(shots, `${name}-${colorScheme}.png`), fullPage: true });
        }
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
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ layouts, errors, screenshots: shots || null }));
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error.stack); process.exitCode = 1; });
