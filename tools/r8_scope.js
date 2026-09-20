const { chromium } = require('playwright-core');
const PAGES = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const n of PAGES) {
    const c = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    const p = await c.newPage();
    await p.goto('http://sinofresh.local/products/' + n + '/', { waitUntil: 'networkidle' });
    const r = await p.evaluate(() => {
      const px = (v) => Math.round(parseFloat(v) || 0);
      const info = (e) => px(getComputedStyle(e).paddingTop) + '/' + px(getComputedStyle(e).paddingBottom) + ' h=' + px(e.getBoundingClientRect().height) + ' "' + (e.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 30) + '"';
      const q = (s) => [...document.querySelectorAll(s)].map(info);
      return {
        descendant: q('body.page-child.parent-pageid-19 section:has(.wp-block-columns + .wp-block-columns + .wp-block-columns)'),
        direct: q('body.page-child.parent-pageid-19 section:has(> .wp-block-columns + .wp-block-columns + .wp-block-columns)'),
      };
    });
    console.log(n.padEnd(14) + ' descendant=' + JSON.stringify(r.descendant) + '\n' + ' '.repeat(15) + 'direct=' + JSON.stringify(r.direct));
    await c.close();
  }
  await b.close();
})();
