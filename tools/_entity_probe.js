/* Definitive entity check: capture the exact PDF text produced by a real
   browser flow, for both the single-dosage and the basket endpoints. */
const { chromium } = require('playwright-core');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const posted = [];
  page.on('request', (r) => {
    if (r.url().includes('config-pdf') && r.postData()) {
      try { posted.push(JSON.parse(r.postData())); } catch (e) { posted.push(r.postData().slice(0, 200)); }
    }
  });

  const RAW = 'Hip & joint';
  await page.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'load' });
  await page.waitForTimeout(700);

  const g = page.locator('.configurator__group[data-group="functions"]');
  await g.locator('.configurator__item[data-value="Custom"]').click();
  await page.waitForTimeout(350);
  await g.locator('textarea.configurator__custom-input').fill(RAW);
  await g.locator('textarea.configurator__custom-input').blur();
  await page.waitForTimeout(250);

  // fill remaining groups with their first chip so PDF is allowed
  const groups = page.locator('.configurator__options .configurator__group');
  const n = await groups.count();
  for (let i = 0; i < n; i++) {
    const grp = groups.nth(i);
    const name = await grp.getAttribute('data-group');
    if (name === 'functions') continue;
    if (!(await grp.locator('.configurator__item.is-selected').count())) {
      await grp.locator('.configurator__item').first().click();
    }
  }
  await page.waitForTimeout(300);

  console.log('--- basket summary stored');
  await page.locator('.configurator__summary .configurator__basket').click();
  await page.waitForTimeout(800);
  console.log(await page.evaluate(() => sessionStorage.getItem('sinofresh_basket')));

  // single PDF via in-page fetch (playwright response buffering is unreliable)
  const b64single = await page.evaluate(async () => {
    const root = document.querySelector('.configurator');
    const groupsEls = [...document.querySelectorAll('.configurator__group')];
    const store = JSON.parse(sessionStorage.getItem('sinofresh_config_soft-chews') || '{}');
    function dv(name, v) {
      if (v !== 'Custom') return v;
      const t = store[name + '_custom'] || '';
      return t ? 'Custom: ' + t : 'Custom (specify in notes)';
    }
    const config = groupsEls.map((gr) => {
      const nm = gr.getAttribute('data-group');
      const h4 = gr.querySelector('h4');
      const label = h4 ? h4.textContent.replace(/\s+/g, ' ').trim() : nm;
      const val = store[nm];
      return { label, value: Array.isArray(val) ? val.map((x) => dv(nm, x)).join(', ') : (dv(nm, val) || '—') };
    });
    const res = await fetch('/wp-json/sinofresh/v1/config-pdf', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slug: root.getAttribute('data-slug') || 'soft-chews', config })
    });
    const buf = await res.arrayBuffer();
    let bin = ''; const bytes = new Uint8Array(buf);
    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin);
  });
  fs.writeFileSync('screenshots/entity-single.pdf', Buffer.from(b64single, 'base64'));

  // basket PDF via in-page fetch
  const b64basket = await page.evaluate(async () => {
    const items = JSON.parse(sessionStorage.getItem('sinofresh_basket') || '[]');
    const res = await fetch('/wp-json/sinofresh/v1/config-pdf', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ basket: items.map((i) => ({ slug: i.slug, summary: i.summary, formula: i.formula || '' })) })
    });
    const buf = await res.arrayBuffer();
    let bin = ''; const bytes = new Uint8Array(buf);
    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin);
  });
  fs.writeFileSync('screenshots/entity-basket.pdf', Buffer.from(b64basket, 'base64'));

  console.log('--- POST payloads (first two)');
  console.log(JSON.stringify(posted.slice(0, 2), null, 1).slice(0, 700));
  console.log('--- drawer text');
  await page.locator('.sf-basket-btn').click();
  await page.waitForTimeout(600);
  console.log(await page.evaluate(() => {
    const d = document.querySelector('.sf-basket-drawer');
    return d ? JSON.stringify({ text: d.innerText.slice(0, 200), html: d.innerHTML.slice(0, 300) }) : 'no drawer';
  }));
  await browser.close();
})();
