const { chromium } = require('playwright-core');
const PAGES = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
const CAND = {
  sep3: 'section:has(> .wp-block-group > .wp-block-columns + .wp-block-separator + .wp-block-columns)',
  sepAny: 'section:has(.wp-block-columns + .wp-block-separator + .wp-block-columns)',
  sepDirect: 'section:has(> .wp-block-group > .wp-block-columns + .wp-block-separator)',
};
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const n of PAGES) {
    const c = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    const p = await c.newPage();
    await p.goto('http://sinofresh.local/products/' + n + '/', { waitUntil: 'networkidle' });
    const r = await p.evaluate((C) => {
      const px = (v) => Math.round(parseFloat(v) || 0);
      const out = {};
      for (const k of Object.keys(C)) {
        out[k] = [...document.querySelectorAll('body.page-child.parent-pageid-19 ' + C[k])].map((e) =>
          px(getComputedStyle(e).paddingTop) + '/' + px(getComputedStyle(e).paddingBottom) + ' h=' + px(e.getBoundingClientRect().height) + ' sep=' + e.querySelectorAll('.wp-block-separator').length + ' "' + (e.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 28) + '"');
      }
      return out;
    }, CAND);
    console.log(n.padEnd(14) + Object.keys(CAND).map((k) => k + '=' + JSON.stringify(r[k])).join('  '));
    await c.close();
  }
  await b.close();
})();
