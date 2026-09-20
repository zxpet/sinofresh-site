/* Batch evidence: node icons_batch_shots.js <batch-tag> page1,page2,...
   Group clips per page + 375 wrap check + one mobile viewport shot. */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const tag = process.argv[2];
const pages = process.argv[3].split(',');
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

(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const p of pages) {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    await page.goto('http://sinofresh.local/products/' + p + '/', { waitUntil: 'networkidle' });
    await settle(page);
    const groups = await page.evaluate(() => [...document.querySelectorAll('.configurator__group')].map(g => g.getAttribute('data-group')));
    for (const g of groups) {
      const box = await page.evaluate((sel) => { const el = document.querySelector(sel); const r = el.getBoundingClientRect(); return { x: Math.round(r.x) - 8, y: Math.round(r.y + window.scrollY) - 8, width: Math.round(r.width) + 16, height: Math.round(r.height) + 16 }; }, `.configurator__group[data-group="${g}"]`);
      await page.screenshot({ path: path.join(OUT, `${tag}-${p}-1440-${g}.png`), clip: box, fullPage: true });
    }
    // selected state check on first icon button of first icon group
    const sel = await page.evaluate(() => {
      const btn = document.querySelector('.configurator__group[data-group="shape"] .configurator__item, .configurator__group[data-group="appearance"] .configurator__item, .configurator__group[data-group="texture"] .configurator__item, .configurator__group[data-group="form"] .configurator__item');
      return btn ? btn.getAttribute('data-value') : null;
    });
    if (sel) {
      await page.click(`.configurator__item[data-value="${sel}"]`);
      await page.waitForTimeout(250);
      const st = await page.evaluate(() => {
        const btn = document.querySelector('.configurator__item.is-selected');
        const svg = btn.querySelector('.configurator__icon, .configurator__dot');
        return { color: getComputedStyle(btn).color, child: svg ? getComputedStyle(svg).stroke || getComputedStyle(svg).backgroundColor : null };
      });
      console.log(p, 'selected', sel, JSON.stringify(st));
    }
    await ctx.close();

    // 375 wrap check
    const ctx2 = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true, deviceScaleFactor: 1 });
    const m = await ctx2.newPage();
    await m.goto('http://sinofresh.local/products/' + p + '/', { waitUntil: 'networkidle' });
    await settle(m);
    const overflow = await m.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    const wraps = await m.evaluate(() => {
      const bad = [];
      document.querySelectorAll('.configurator__item').forEach((btn) => {
        const svg = btn.querySelector('.configurator__icon, .configurator__dot');
        if (!svg) return;
        const br = btn.getBoundingClientRect(), sr = svg.getBoundingClientRect();
        const padTop = parseFloat(getComputedStyle(btn).paddingTop);
        if (Math.abs(sr.top - br.top - padTop) > 8) bad.push(btn.getAttribute('data-value'));
      });
      return bad;
    });
    console.log(p, '375 overflowX:', overflow, 'misaligned:', JSON.stringify(wraps));
    await m.evaluate(() => { const g = document.querySelector('.configurator__group[data-group="flavor"], .configurator__group'); g.scrollIntoView({ block: 'start' }); });
    await m.waitForTimeout(300);
    await m.screenshot({ path: path.join(OUT, `${tag}-${p}-375.png`) });
    await ctx2.close();
  }
  await b.close();
  console.log('done', tag);
})();
