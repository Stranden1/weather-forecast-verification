/* Optional private viewer check: node tests/private_forecast_ui_test.cjs URL [SCREENSHOT_DIR].
   Run the loopback viewer first. Screenshots contain private future forecasts:
   keep them in ignored work/, never site/ or Git. No external browser requests. */
const fs = require('node:fs/promises');
const { existsSync } = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

async function main() {
  const url = process.argv[2];
  assert(/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(url || ''), 'Provide the private loopback URL.');
  const shots = process.argv[3] && path.resolve(process.argv[3]);
  if (shots) await fs.mkdir(shots, { recursive: true });
  const executablePath = process.env.WX_BROWSER_EXECUTABLE ||
    ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(existsSync);
  const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  const errors = [], layouts = [];
  try {
    for (const [name, width, height] of [['desktop',1280,900],['mobile',375,812],['narrow',320,812]]) {
      for (const colorScheme of ['light','dark']) {
        const context = await browser.newContext({ viewport:{width,height}, colorScheme });
        const page = await context.newPage();
        page.on('pageerror', e => errors.push(e.message));
        await page.route('**/*', route => route.request().url().startsWith(url + '/') ? route.continue() : route.abort());
        await page.goto(url, {waitUntil:'networkidle'});
        await page.waitForFunction(() => document.querySelector('#station option'));
        assert.equal(await page.locator('#station').inputValue(), 'SN68860');
        assert.equal(await page.locator('#station option').count(),49);
        assert.equal(await page.evaluate(() => document.documentElement.dataset.theme),colorScheme);
        const layout = await page.evaluate(() => ({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,
          height:document.documentElement.scrollHeight,storyY:document.getElementById('story').getBoundingClientRect().top}));
        assert(layout.scrollWidth<=width+1,`${name} overflows horizontally`);
        assert(layout.storyY<height,`${name} comparison is below the first screen`);
        assert(await page.locator('#hours button').count()>0);
        assert.match(await page.locator('#wn-issued').textContent(),/Issued/);
        assert(await page.locator('#wn-value').evaluate(el=>parseFloat(getComputedStyle(el).fontSize))>=28,'Forecast values should be prominent');
        if(shots) await page.screenshot({path:path.join(shots,`${name}-${colorScheme}.png`),fullPage:true});
        for (const v of ['w','p','t']) {
          await page.locator(`[data-variable="${v}"]`).click();
          assert.equal(await page.locator(`[data-variable="${v}"]`).getAttribute('aria-pressed'),'true');
          assert((await page.locator('#table-body tr').count())>0);
          if(v==='p') {
            assert.match(await page.locator('#coverage').textContent(),/hour ending/);
            assert.match(await page.locator('#wn-range').textContent(),/median/);
          }
        }
        await page.locator('#hours button').last().focus();
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('#hours button').last().getAttribute('aria-pressed'),'true');
        await page.locator('[data-hours="24"]').click();
        assert.match(await page.locator('#coverage').textContent(),/24-hour/);
        await page.locator('#theme').click();
        assert.equal(await page.evaluate(() => document.documentElement.dataset.theme),colorScheme==='dark'?'light':'dark');
        layouts.push({name,colorScheme,...layout});
        await context.close();
      }
    }
    // Deterministic missing-hour and rain-median checks, without altering saved state.
    const context = await browser.newContext({viewport:{width:375,height:812}});
    const page = await context.newPage();
    page.on('pageerror',e=>errors.push(e.message));
    const row = {issued:'2026-10-12T12:00:00Z',t:3,t_p10:1,t_p90:5,w:7,w_p10:4,w_p90:10,p:.4,p_p50:.1,p_p90:.8,p_prob:30};
    const fixture = {loaded:'2026-10-12T14:00:00Z',collected:'2026-10-12T13:00:00Z',notices:[],stations:[
      {id:'SN68860',name:'Test station',points:[
        {time:'2026-10-12T17:00:00Z',yr:{...row},wn:{...row}},
        {time:'2026-10-12T18:00:00Z',yr:{...row},wn:{...row,t:5}},
        {time:'2026-10-12T23:00:00Z',wn:{...row}}]},
      {id:'EMPTY',name:'No saved hours',points:[]}]};
    await page.route('**/*',route=>{
      if(route.request().url()===url+'/api/forecasts')return route.fulfill({json:fixture});
      return route.request().url().startsWith(url+'/')?route.continue():route.abort();
    });
    await page.goto(url,{waitUntil:'networkidle'});
    assert.equal(await page.locator('#chart polyline').count(),3,'Missing hours must split the lines');
    assert.equal(await page.locator('#chart polygon').count(),2,'Ranges must also stop at gaps');
    await page.locator('#largest-gap').click();
    assert.equal(await page.locator('#hours button').nth(1).getAttribute('aria-pressed'),'true','Largest gap must choose the largest shared-hour difference');
    await page.locator('[data-variable="p"]').click();
    assert.equal(await page.locator('#wn-value').textContent(),'0.10 mm','Precipitation must show median, not mean');
    await page.locator('#hours button').last().click();
    assert.equal(await page.locator('#yr-value').textContent(),'—');
    assert.match(await page.locator('#difference').textContent(),/needs both/);
    await page.locator('#station').selectOption('EMPTY');
    assert.match(await page.locator('#story').textContent(),/No shared/);
    assert.equal(await page.locator('#hours button').count(),0);
    assert.equal(await page.locator('#wn-value').textContent(),'—');
    assert(await page.locator('#largest-gap').isDisabled());
    await context.close();
    assert.deepEqual(errors,[]);
    const result={checked:new Date().toISOString(),layouts,pageErrors:errors,fixtureChecks:'gaps, missing provider, precipitation median, empty station'};
    if(shots)await fs.writeFile(path.join(shots,'validation.json'),JSON.stringify(result,null,2));
    console.log(JSON.stringify(result,null,2));
  } finally {await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
