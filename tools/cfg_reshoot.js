const { chromium } = require('playwright-core');
const path = require('path');
const OUT = path.resolve(__dirname, '..', 'screenshots', 'batch1');
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const [name, w, h, scrollTo] of [
    ['cfg-mid-375.png', 375, 812, '.configurator__group:nth-child(4)'],
    ['cfg-start-375.png', 375, 812, '.configurator'],
    ['cfg-end-375.png', 375, 812, '.configurator__group:nth-last-child(2)'],
  ]) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: true, hasTouch: true });
    const p = await ctx.newPage();
    await p.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'networkidle' });
    await p.evaluate(() => document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; }));
    await p.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.querySelectorAll('img')].map((i) => (i.complete && i.naturalWidth) ? 0 : new Promise((r) => { i.addEventListener('load', r, { once: true }); setTimeout(r, 4000); }))); });
    await p.evaluate(async (s) => { const el = document.querySelector(s); if (el) el.scrollIntoView({ block: 'start' }); await new Promise((r) => setTimeout(r, 300)); }, scrollTo);
    await p.screenshot({ path: path.join(OUT, name) });
    await ctx.close();
    console.log('shot', name);
  }
  await b.close();
})();
