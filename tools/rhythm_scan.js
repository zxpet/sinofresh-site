const { chromium } = require('playwright-core');
const PAGES = [
  ['home', '/'], ['products', '/products/'], ['soft-chews', '/products/soft-chews/'], ['tablets', '/products/tablets/'],
  ['powders', '/products/powders/'], ['pastes', '/products/pastes/'], ['drops', '/products/drops/'], ['liquids', '/products/liquids/'],
  ['fish-oil', '/products/fish-oil/'], ['dental-chews', '/products/dental-chews/'], ['about', '/about/'], ['quality', '/quality/'],
  ['factory-tour', '/factory-tour/'], ['services', '/services/'], ['cooperation', '/cooperation/'], ['contact', '/contact/'],
  ['blog', '/blog/'], ['test-article', '/test-article/'], ['privacy-policy', '/privacy-policy/'], ['cookie-policy', '/cookie-policy/'],
  ['terms', '/terms/'], ['404', '/404-probe/'],
];
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  console.log('page            | heroInner(pt/pb) | sections with padding >= 56 (cls:pt/pb)');
  for (const [n, u] of PAGES) {
    const c = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    const p = await c.newPage();
    await p.goto('http://sinofresh.local' + u, { waitUntil: 'networkidle' });
    const r = await p.evaluate(() => {
      const px = (v) => Math.round(parseFloat(v) || 0);
      const hi = document.querySelector('.sf-hero-inner');
      const hiCs = hi ? getComputedStyle(hi) : null;
      const bad = [...document.querySelectorAll('section')]
        .map((s) => {
          const cs = getComputedStyle(s);
          return { cls: s.className.replace(/wp-container-core-[\w-]*/g, '').replace(/is-layout-[\w-]*/g, '').replace(/\s+/g, ' ').trim().slice(0, 52), pt: px(cs.paddingTop), pb: px(cs.paddingBottom), h: px(s.getBoundingClientRect().height) };
        })
        .filter((s) => s.pt >= 56 || s.pb >= 56);
      return { hi: hiCs ? px(hiCs.paddingTop) + '/' + px(hiCs.paddingBottom) : 'none', bad, docH: document.documentElement.scrollHeight };
    });
    console.log(n.padEnd(15) + ' | ' + String(r.hi).padEnd(16) + ' | ' + (r.bad.length ? r.bad.map((x) => x.pt + '/' + x.pb + ' h=' + x.h + ' "' + x.cls + '"').join(' ; ') : '-'));
    await c.close();
  }
  await b.close();
})();
