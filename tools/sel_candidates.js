const { chromium } = require('playwright-core');
const PAGES = [
  ['home', '/'], ['products', '/products/'], ['soft-chews', '/products/soft-chews/'], ['drops', '/products/drops/'],
  ['fish-oil', '/products/fish-oil/'], ['about', '/about/'], ['quality', '/quality/'], ['cooperation', '/cooperation/'],
  ['services', '/services/'], ['contact', '/contact/'], ['blog', '/blog/'], ['test-article', '/test-article/'],
  ['privacy-policy', '/privacy-policy/'], ['404', '/404-probe/'],
];
const BODY = 'body';
const CAND = {
  R_prodLink: BODY + ' section:has(> .wp-block-columns > .wp-block-column a[href^="/products/"])',
  R_prodLinkFig: BODY + ' section:has(> .wp-block-columns > .wp-block-column figure.wp-block-image):has(> .wp-block-columns > .wp-block-column a[href^="/products/"])',
  R_twoGroupsProdLink: BODY + ' section:has(> .wp-block-columns + .wp-block-columns):has(> .wp-block-columns > .wp-block-column a[href^="/products/"])',
  S_topBorder: BODY + ' section:has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-top-border-color)',
  S_topBorderBare: BODY + ' section:has(> .wp-block-columns:not([class*="sf-"]) > .wp-block-column > .wp-block-group.has-top-border-color)',
};
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const [n, u] of PAGES) {
    const c = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    const p = await c.newPage();
    await p.goto('http://sinofresh.local' + u, { waitUntil: 'networkidle' });
    const r = await p.evaluate((C) => {
      const out = { body: [...document.body.classList].filter((x) => /page-child|page-id|parent-page/.test(x)).join(' ') };
      for (const k of Object.keys(C)) {
        out[k] = [...document.querySelectorAll(C[k])].map((e) => {
          const h = e.querySelector('h1,h2');
          return (h ? h.textContent.trim().slice(0, 22) : '?') + '(' + e.querySelectorAll(':scope > .wp-block-columns > .wp-block-column').length + ')';
        });
      }
      return out;
    }, CAND);
    const parts = Object.keys(CAND).map((k) => k.replace(/^[RS]_/, '') + '=' + (r[k].length ? r[k].join(',') : '-'));
    console.log(n.padEnd(15) + '[' + r.body + ']  ' + parts.join('  '));
    await c.close();
  }
  await b.close();
})();
