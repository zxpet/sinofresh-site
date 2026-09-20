/* Entity A/B/C end-to-end audit — REAL button path (no synthetic fetch).
 *
 * Scenario A: type "Hip & joint"        (single raw ampersand)
 * Scenario B: type "Hip &amp; joint"    (what a user may paste from markup)
 * Scenario C: type "Hip &amp;amp; joint" (already double-escaped)
 *
 * Every stage is printed with JSON.stringify so "&" vs "&amp;" is unambiguous:
 *   typed literal -> input.value -> sessionStorage -> summary card textContent
 *   -> summary card innerHTML (what devtools shows) -> POST body (real button)
 *   -> PDF bytes -> PDF extracted text.
 *
 * The PDF is captured with a route handler that reads the response body on the
 * server side of Playwright, which is byte-exact (page-side res.body() proved
 * unreliable for streamed PDF responses).
 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const BASE = 'http://sinofresh.local';
const OUT = 'screenshots';

const SCENARIOS = [
  { id: 'A', label: 'raw single &', fn: 'Hip & joint', fl: 'Fish & Chips' },
  { id: 'B', label: 'one level &amp;', fn: 'Hip &amp; joint', fl: 'Fish &amp; Chips' },
  { id: 'C', label: 'two levels &amp;amp;', fn: 'Hip &amp;amp; joint', fl: 'Fish &amp;amp; Chips' },
];

async function acceptCookies(page) {
  const btn = page.locator('button:has-text("Accept"), .sf-cookie__accept, [data-consent-accept]').first();
  if ((await btn.count()) && (await btn.isVisible().catch(() => false))) await btn.click();
  await page.waitForTimeout(200);
}

async function fillCustom(page, group, text, tag) {
  const g = page.locator(`.configurator__group[data-group="${group}"]`);
  await g.locator('.configurator__item[data-value="Custom"]').click();
  await page.waitForTimeout(420);
  const field = g.locator('.configurator__custom-input');
  await field.click();
  await field.type(text);
  await field.blur();
  await page.waitForTimeout(260);
  const after = await field.inputValue();
  console.log(`   [${tag}] ${group}: typed=${JSON.stringify(text)} -> field.value=${JSON.stringify(after)}`);
  return after;
}

async function fillRest(page) {
  const groups = page.locator('.configurator__options .configurator__group');
  const n = await groups.count();
  for (let i = 0; i < n; i++) {
    const grp = groups.nth(i);
    const name = await grp.getAttribute('data-group');
    if (name === 'functions' || name === 'flavor') continue;
    if (!(await grp.locator('.configurator__item.is-selected').count())) {
      await grp.locator('.configurator__item').first().click();
    }
  }
  await page.waitForTimeout(250);
}

(async () => {
  const browser = await chromium.launch();
  const report = [];

  for (const sc of SCENARIOS) {
    console.log('\n' + '='.repeat(74));
    console.log(`## Scenario ${sc.id} — ${sc.label}`);
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
    const page = await ctx.newPage();

    let captured = null;
    let capturedBody = null;
    await ctx.route('**/wp-json/sinofresh/v1/config-pdf', async (route) => {
      capturedBody = route.request().postDataJSON();
      const resp = await route.fetch();
      captured = Buffer.from(await resp.body());
      await route.fulfill({ response: resp });
    });

    await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
    await page.waitForTimeout(800);
    await acceptCookies(page);

    await fillCustom(page, 'functions', sc.fn, sc.id);
    await fillCustom(page, 'flavor', sc.fl, sc.id);
    await fillRest(page);

    // sessionStorage
    const cfg = JSON.parse(await page.evaluate(() => sessionStorage.getItem('sinofresh_config_soft-chews')));
    console.log(`   [${sc.id}] sessionStorage.functions_custom = ${JSON.stringify(cfg.functions_custom)}`);
    console.log(`   [${sc.id}] sessionStorage.flavor_custom    = ${JSON.stringify(cfg.flavor_custom)}`);
    console.log(`   [${sc.id}] storage JSON.stringify contains "amp;" ? ${/amp;/.test(JSON.stringify(cfg))}`);

    // summary card: rendered text AND serialized markup (devtools view)
    const card = await page.evaluate(() => {
      const rows = document.querySelectorAll('.configurator__summary-row');
      const out = [];
      rows.forEach((r) => {
        const label = r.querySelector('.configurator__summary-label');
        const val = r.querySelector('.configurator__summary-value');
        if (!val) return;
        out.push({ label: label ? label.textContent.trim() : '', text: val.textContent, html: val.innerHTML });
      });
      return out;
    });
    const fRow = card.find((r) => /Function/i.test(r.label));
    const vRow = card.find((r) => /Flavor/i.test(r.label));
    console.log(`   [${sc.id}] card Functions textContent = ${JSON.stringify(fRow.text)}`);
    console.log(`   [${sc.id}] card Functions innerHTML   = ${JSON.stringify(fRow.html)}   <-- devtools would show this`);
    console.log(`   [${sc.id}] card Flavor    textContent = ${JSON.stringify(vRow.text)}`);
    console.log(`   [${sc.id}] card Flavor    innerHTML   = ${JSON.stringify(vRow.html)}`);

    // REAL button -> real payload -> real bytes
    captured = null; capturedBody = null;
    await page.locator('.configurator__summary .configurator__pdf').click();
    await page.waitForTimeout(6000);

    console.log(`   [${sc.id}] POST body (real button) = ${JSON.stringify(capturedBody).slice(0, 420)}`);
    const pairsJson = JSON.stringify(capturedBody);
    console.log(`   [${sc.id}] POST body contains "amp;" ? ${/amp;/.test(pairsJson)}`);
    const file = path.join(OUT, `entity-abc-${sc.id}-single.pdf`);
    if (captured && captured.length) {
      fs.writeFileSync(file, captured);
      console.log(`   [${sc.id}] saved ${file} (${captured.length} bytes)  bytes contain "amp" ? ${captured.includes(Buffer.from('amp'))}`);
    } else {
      console.log(`   [${sc.id}] !! no PDF captured`);
    }

    // drawer text (buyer-visible surface)
    const basketRaw = await page.evaluate(() => sessionStorage.getItem('sinofresh_basket'));
    console.log(`   [${sc.id}] basket storage (${sc.id === 'A' ? 'before adding' : 'n/a'}) = ${basketRaw === null ? 'null' : basketRaw.slice(0, 160)}`);

    report.push({ sc: sc.id, fn: cfg.functions_custom, fl: cfg.flavor_custom, file, body: capturedBody });
    await ctx.close();
  }

  /* Scenario C also through the inquiry-basket PDF path (single summary string,
     parsed server-side by ' | ' + first ':'), which is a different code path. */
  console.log('\n' + '='.repeat(74));
  console.log('## Scenario C via inquiry basket (drawer button)');
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
  const page = await ctx.newPage();
  let bcap = null, bbody = null;
  await ctx.route('**/wp-json/sinofresh/v1/config-pdf', async (route) => {
    bbody = route.request().postDataJSON();
    const resp = await route.fetch();
    bcap = Buffer.from(await resp.body());
    await route.fulfill({ response: resp });
  });
  await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
  await page.waitForTimeout(800);
  await acceptCookies(page);
  await fillCustom(page, 'functions', 'Hip &amp;amp; joint', 'C');
  await fillCustom(page, 'flavor', 'Fish &amp;amp; Chips', 'C');
  await fillRest(page);
  await page.locator('.configurator__summary .configurator__basket').click();
  await page.waitForTimeout(900);
  const bst = await page.evaluate(() => sessionStorage.getItem('sinofresh_basket'));
  console.log(`   basket storage = ${JSON.stringify(bst)}`);
  console.log(`   basket storage contains "amp;" ? ${/amp;/.test(bst || '')}`);
  await page.locator('.sf-basket-btn').click();
  await page.waitForTimeout(600);
  const drawerInfo = await page.evaluate(() => {
    const d = document.querySelector('.sf-basket-drawer');
    const sum = d.querySelector('.sf-basket-drawer__item-summary');
    return { innerText: sum ? sum.innerText : '', innerHTML: sum ? sum.innerHTML : '' };
  });
  console.log(`   drawer item innerText = ${JSON.stringify(drawerInfo.innerText)}`);
  console.log(`   drawer item innerHTML = ${JSON.stringify(drawerInfo.innerHTML)}`);
  const dBtn = page.locator('.sf-basket-drawer button').filter({ hasText: /PDF/i }).first();
  await dBtn.click();
  await page.waitForTimeout(7000);
  console.log(`   basket POST body = ${JSON.stringify(bbody).slice(0, 420)}`);
  if (bcap && bcap.length) {
    fs.writeFileSync(path.join(OUT, 'entity-abc-C-basket.pdf'), bcap);
    console.log(`   saved screenshots/entity-abc-C-basket.pdf (${bcap.length} bytes)  bytes contain "amp" ? ${bcap.includes(Buffer.from('amp'))}`);
  } else {
    console.log('   !! no basket PDF captured');
  }
  await ctx.close();
  await browser.close();
})();
