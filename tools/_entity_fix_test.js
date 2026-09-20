/* Entity fix verification: no "&amp;" may reach a PDF, in any encoding state.
   Phase 1 (node): drive a real browser, save both PDFs.
   Phase 2 (python): extract the PDF text and assert the decoded characters. */
const { chromium } = require('playwright-core');
const fs = require('fs');

const BASE = 'http://sinofresh.local';
let pass = 0, fail = 0;
function ok(label, cond) {
  if (cond) { pass++; console.log('PASS ' + label); }
  else { fail++; console.log('FAIL ' + label); }
}

/* Real-button PDF capture.
   The payload MUST travel through the page's own code path
   (buildConfigPairs -> requestPdf -> blob download). Driving the endpoint
   from a synthetic page-side fetch skips exactly the layer under test, so
   the earlier version of this file could not catch an escaping bug in the
   page code even if one existed. Byte capture happens in the route handler
   on Playwright's side, which is byte-exact — page-side res.body() proved
   unreliable for streamed PDF responses. */
let capture = { body: null, bytes: null };

async function clickAndCapture(page, button, file) {
  capture = { body: null, bytes: null };
  await button.click();
  for (let i = 0; i < 75 && !capture.bytes; i++) await page.waitForTimeout(200);
  if (!capture.bytes) return { ok: false, body: null, bytes: null };
  fs.writeFileSync(file, capture.bytes);
  return { ok: true, body: capture.body, bytes: capture.bytes };
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  /* Intercept the real request so the bytes the browser actually received
     are what gets written to disk and asserted on. */
  await ctx.route('**/wp-json/sinofresh/v1/config-pdf', async (route) => {
    capture.body = route.request().postDataJSON();
    const resp = await route.fetch();
    capture.bytes = Buffer.from(await resp.body());
    await route.fulfill({ response: resp });
  });

  await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
  await page.waitForTimeout(700);

  const gFn = page.locator('.configurator__group[data-group="functions"]');
  const ta = gFn.locator('textarea.configurator__custom-input');
  await gFn.locator('.configurator__item[data-value="Custom"]').click();
  await page.waitForTimeout(350);
  await ta.click();
  await ta.type('Hip & joint');           // keyboard, raw ampersand
  await ta.blur();
  await page.waitForTimeout(250);

  ok('raw input kept in the field', (await ta.inputValue()) === 'Hip & joint');

  let st = await page.evaluate(() => sessionStorage.getItem('sinofresh_config_soft-chews'));
  const cfg = JSON.parse(st);
  ok('stored custom value is raw', cfg.functions_custom === 'Hip & joint');
  ok('storage carries no entity', !/&(?:amp|lt|gt|quot|#0?39);/.test(st));

  let sum = await page.evaluate(() => document.querySelector('.configurator__summary-row[data-group="functions"] .configurator__summary-value').textContent);
  ok('summary shows "Custom: Hip & joint"', sum === 'Custom: Hip & joint');

  /* A value that arrives already entity-encoded (legacy state, serialized
     markup, pasted HTML) must be decoded at the storage boundary. */
  const gFl = page.locator('.configurator__group[data-group="flavor"]');
  const fi = gFl.locator('input.configurator__custom-input');
  await gFl.locator('.configurator__item[data-value="Custom"]').click();
  await page.waitForTimeout(350);
  await fi.click();
  await fi.type('Fish &amp; Chips');
  await fi.blur();
  await page.waitForTimeout(250);
  ok('pre-escaped input decoded in the field', (await fi.inputValue()) === 'Fish & Chips');
  const cfg2 = JSON.parse(await page.evaluate(() => sessionStorage.getItem('sinofresh_config_soft-chews')));
  ok('pre-escaped input stored decoded', cfg2.flavor_custom === 'Fish & Chips');
  sum = await page.evaluate(() => document.querySelector('.configurator__summary-row[data-group="flavor"] .configurator__summary-value').textContent);
  ok('summary shows "Custom: Fish & Chips"', sum === 'Custom: Fish & Chips');

  /* Fill the remaining groups so both PDFs are allowed. */
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

  await page.locator('.configurator__summary .configurator__basket').click();
  await page.waitForTimeout(800);
  const basketRaw = await page.evaluate(() => sessionStorage.getItem('sinofresh_basket'));
  ok('basket summary carries no entity', !/&(?:amp|lt|gt|quot|#0?39);/.test(basketRaw));
  ok('basket summary keeps raw "&"', /Hip & joint/.test(basketRaw));
  ok('basket summary keeps raw flavor', /Fish & Chips/.test(basketRaw));

  /* Drawer text (visible to the buyer). */
  await page.locator('.sf-basket-btn').click();
  await page.waitForTimeout(500);
  const drawerText = await page.evaluate(() => {
    const d = document.querySelector('.sf-basket-drawer');
    return d ? d.innerText : '';
  });
  ok('drawer shows raw "&"', /Hip & joint/.test(drawerText) && /Fish & Chips/.test(drawerText));
  ok('drawer shows no entity', !/&amp;/.test(drawerText));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  /* Both PDFs — clicked through the REAL buttons. */
  const single = await clickAndCapture(
    page,
    page.locator('.configurator__summary .configurator__pdf'),
    'screenshots/entity-fix-single.pdf'
  );
  ok('single PDF captured via real button', single.ok);
  ok('single payload carries no entity', !/amp;/.test(JSON.stringify(single.body)));

  await page.locator('.sf-basket-btn').click();
  await page.waitForTimeout(500);
  const basketPdfBtn = page.locator('.sf-basket-drawer button').filter({ hasText: /PDF/i }).first();
  const bk = await clickAndCapture(page, basketPdfBtn, 'screenshots/entity-fix-basket.pdf');
  ok('basket PDF captured via real button', bk.ok);
  ok('basket payload carries no entity', !/amp;/.test(JSON.stringify(bk.body)));

  /* Reload: restore must not resurrect an entity. */
  await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
  await page.waitForTimeout(800);
  ok('restored field is raw', (await page.locator('.configurator__group[data-group="functions"] textarea.configurator__custom-input').inputValue()) === 'Hip & joint');

  console.log(`\n[BROWSER] ${pass} PASS / ${fail} FAIL`);
  await browser.close();
  process.exit(fail ? 1 : 0);
})();
