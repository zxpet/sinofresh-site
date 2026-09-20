const { chromium } = require('playwright-core');
const PAGES = [
  ['home', '/'], ['products', '/products/'], ['soft-chews', '/products/soft-chews/'],
  ['drops', '/products/drops/'], ['about', '/about/'], ['quality', '/quality/'],
  ['cooperation', '/cooperation/'], ['services', '/services/'], ['contact', '/contact/'],
  ['blog', '/blog/'], ['test-article', '/test-article/'], ['404', '/404-probe/'],
];
const SEL = {
  steps: 'section:has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-top-border-color)',
  related: 'section:has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-card-white-background-color)',
  tri: 'section:has(> .wp-block-columns.sf-triple)',
  p3: 'section:has(> .wp-block-columns.sf-panel--3)',
};
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const [n, u] of PAGES) {
    const c = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    const p = await c.newPage();
    await p.goto('http://sinofresh.local' + u, { waitUntil: 'networkidle' });
    const r = await p.evaluate((S) => {
      const out = {};
      for (const k of Object.keys(S)) {
        const els = [...document.querySelectorAll(S[k])];
        out[k] = els.map((e) => ({
          head: e.querySelector('h1,h2') ? e.querySelector('h1,h2').textContent.trim().slice(0, 26) : null,
          groups: e.querySelectorAll(':scope > .wp-block-columns').length,
          cols: e.querySelectorAll(':scope > .wp-block-columns > .wp-block-column').length,
        }));
      }
      return out;
    }, SEL);
    const parts = Object.keys(r).map((k) => k + '=' + (r[k].length ? JSON.stringify(r[k]) : '0'));
    console.log(n + ': ' + parts.join('  '));
    await c.close();
  }
  await b.close();
})();
