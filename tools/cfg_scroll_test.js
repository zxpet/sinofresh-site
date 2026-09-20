const { chromium } = require('playwright-core');
const path = require('path');
const OUT = path.resolve(__dirname, '..', 'screenshots', 'batch1');
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const ctx = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  await p.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'networkidle' });
  await p.evaluate(() => document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; }));
  await p.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.querySelectorAll('img')].map((i) => (i.complete && i.naturalWidth) ? 0 : new Promise((r) => { i.addEventListener('load', r, { once: true }); setTimeout(r, 4000); }))); });
  const cfgTop = await p.evaluate(() => Math.round(document.querySelector('.configurator').getBoundingClientRect().top + window.scrollY));
  console.log('configurator top =', cfgTop);
  for (const off of [cfgTop - 700, cfgTop - 500, cfgTop - 300, cfgTop - 150, cfgTop, cfgTop + 300, cfgTop + 900, cfgTop + 1500]) {
    await p.evaluate((y) => window.scrollTo(0, y), off);
    await p.waitForTimeout(260);
    const m = await p.evaluate(() => {
      const px = (v) => Math.round(parseFloat(v) || 0);
      const col = document.querySelector('.configurator__summary-col');
      const card = document.querySelector('.configurator__summary');
      const b = col.getBoundingClientRect();
      return { scrollY: Math.round(window.scrollY), colTop: px(b.top), colBottom: px(b.bottom), cardH: px(card.getBoundingClientRect().height), cardTop: px(card.getBoundingClientRect().top), vpH: innerHeight };
    });
    const name = 'cfg-scroll-' + String(off).replace(/[^0-9-]/g, '') + '.png';
    await p.screenshot({ path: path.join(OUT, name) });
    console.log(name, JSON.stringify(m), m.colTop >= 0 && m.colTop < 400 ? '<-- CARD IN FLOW TOP' : (m.colBottom >= m.vpH ? 'pinned-bottom' : 'natural'));
  }
  await ctx.close();
  await b.close();
})();
