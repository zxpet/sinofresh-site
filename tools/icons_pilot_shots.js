/* Icons pilot evidence: node icons_pilot_shots.js before|after
   Writes screenshots/icons-pilot/ */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const tag = process.argv[2] || 'after';
const OUT = path.resolve(__dirname, '..', 'screenshots', 'icons-pilot');
fs.mkdirSync(OUT, { recursive: true });

async function settle(page) {
  await page.evaluate(() => document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; i.decoding = 'sync'; }));
  await page.evaluate(async () => { await document.fonts.ready; });
  await page.evaluate(async () => {
    await Promise.all([...document.querySelectorAll('img')].map((i) => (i.complete && i.naturalWidth) ? 0 : new Promise((r) => { i.addEventListener('load', r, { once: true }); i.addEventListener('error', r, { once: true }); setTimeout(r, 4000); })));
    await new Promise((r) => setTimeout(r, 200));
  });
}

async function clipSel(page, sel) {
  const box = await page.evaluate((s) => { const el = document.querySelector(s); if (!el) return null; const b = el.getBoundingClientRect(); return { x: Math.round(b.x) - 8, y: Math.round(b.y + window.scrollY) - 8, width: Math.round(b.width) + 16, height: Math.round(b.height) + 16 }; }, sel);
  return box;
}

(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  await page.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'networkidle' });
  await settle(page);

  // 1) five groups, desktop, clipped per group
  for (const g of ['shape', 'color', 'flavor', 'packaging', 'functions']) {
    const box = await clipSel(page, `.configurator__group[data-group="${g}"]`);
    if (box) await page.screenshot({ path: path.join(OUT, `${tag}-1440-${g}.png`), clip: box, fullPage: true });
    else console.log('missing group', g);
  }

  // 2) selected state: click Bone, verify icon stroke follows currentColor
  await page.click('.configurator__item[data-value="Bone"]');
  await page.waitForTimeout(300);
  const state = await page.evaluate(() => {
    const btn = document.querySelector('.configurator__item.is-selected');
    if (!btn) return { selected: false };
    const cs = getComputedStyle(btn);
    const svg = btn.querySelector('.configurator__icon');
    return { selected: true, btnColor: cs.color, fontWeight: cs.fontWeight, iconStroke: svg ? getComputedStyle(svg).stroke : null, text: btn.textContent.trim() };
  });
  console.log('selected-state:', JSON.stringify(state));
  const box = await clipSel(page, '.configurator__group[data-group="shape"]');
  await page.screenshot({ path: path.join(OUT, `${tag}-1440-selected-bone.png`), clip: box, fullPage: true });

  // 3) multi-select group? functions is multi? click Joint Support + Immune if allowed
  await page.click('.configurator__group[data-group="functions"] .configurator__item[data-value="Immune Support"]');
  await page.waitForTimeout(200);

  await ctx.close();

  // mobile 375: two viewport shots + clip of flavor group
  const ctx2 = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true, deviceScaleFactor: 1 });
  const m = await ctx2.newPage();
  await m.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'networkidle' });
  await settle(m);
  const mBox = await clipSel(m, '.configurator__group[data-group="flavor"]');
  await m.screenshot({ path: path.join(OUT, `${tag}-375-flavor.png`), clip: mBox, fullPage: true });
  await m.evaluate(() => { document.querySelector('.configurator__group[data-group="packaging"]').scrollIntoView({ block: 'start' }); });
  await m.waitForTimeout(300);
  await m.screenshot({ path: path.join(OUT, `${tag}-375-viewport-packaging.png`) });

  // wrap check: any button whose content wraps (icon line + text line)?
  const wraps = await m.evaluate(() => {
    const bad = [];
    document.querySelectorAll('.configurator__item').forEach((btn) => {
      const r = btn.getBoundingClientRect();
      const svg = btn.querySelector('.configurator__icon, .configurator__dot');
      if (svg) {
        const s = svg.getBoundingClientRect();
        if (Math.abs(s.top - btn.getBoundingClientRect().top - parseFloat(getComputedStyle(btn).paddingTop)) > 8) bad.push(btn.getAttribute('data-value'));
      }
    });
    return bad;
  });
  console.log('375 wrap/misalign buttons:', JSON.stringify(wraps));
  await ctx2.close();
  await b.close();
  console.log('done', tag);
})();
