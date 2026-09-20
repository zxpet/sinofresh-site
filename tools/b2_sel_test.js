/* Batch-2 leak test: verify candidate :has() selectors only hit the
   intended sections on the intended pages. Run against every site page. */
const { chromium } = require('playwright-core');

const SEL = {
  S1_values: '.wp-block-columns:has(> .wp-block-column > .wp-block-group.has-border-light-border-color):not(:has(figure))',
  S2_team_lab: '.wp-block-columns:has(> .wp-block-column > .wp-block-group.has-bg-light-background-color.is-content-justification-center):not(:has(> .wp-block-column > figure))',
  S3_factory: 'section:has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-border-light-border-color):has(figure)',
  S4_certs: 'body.page-id-15 section.has-bg-light-background-color:has(> .wp-block-columns > .wp-block-column:nth-child(4) > .wp-block-group.has-card-white-background-color)',
  S5_qc: 'section:has(> .wp-block-columns + .wp-block-columns):has(> .wp-block-columns > .wp-block-column > p.has-accent-color)',
  S6_palat: '.wp-block-columns:has(> .wp-block-column:nth-child(4)):not(:has(> .wp-block-column:nth-child(5))):has(> .wp-block-column > p.has-accent-color)',
  S7_trace: '.wp-block-columns:has(> .wp-block-column > .wp-block-group.has-bg-light-background-color.is-layout-constrained)',
  S8_hww: 'section:has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-top-border-color)',
};

const PAGES = [
  ['home', '/'], ['products', '/products/'],
  ['soft-chews', '/products/soft-chews/'], ['tablets', '/products/tablets/'],
  ['powders', '/products/powders/'], ['pastes', '/products/pastes/'],
  ['drops', '/products/drops/'], ['liquids', '/products/liquids/'],
  ['fish-oil', '/products/fish-oil/'], ['dental-chews', '/products/dental-chews/'],
  ['about', '/about/'], ['quality', '/quality/'], ['factory-tour', '/factory-tour/'],
  ['services', '/services/'], ['cooperation', '/cooperation/'], ['contact', '/contact/'],
  ['blog', '/blog/'], ['privacy', '/privacy-policy/'], ['terms', '/terms/'],
  ['cookies', '/cookie-policy/'],
];

(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const [n, u] of PAGES) {
    const ctx = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    const p = await ctx.newPage();
    await p.goto('http://sinofresh.local' + u, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
    const r = await p.evaluate((SEL) => {
      const out = {};
      for (const [k, s] of Object.entries(SEL)) {
        const els = [...document.querySelectorAll(s)];
        if (els.length) {
          out[k] = els.map((e) => {
            const h = e.tagName === 'SECTION' ? e.querySelector('h1,h2') : e.closest('section') && e.closest('section').querySelector('h1,h2');
            const kids = e.tagName === 'SECTION' ? e.querySelectorAll(':scope > .wp-block-columns > .wp-block-column').length : e.children.length;
            return (h ? h.textContent.trim().slice(0, 24) : '?') + '/' + kids;
          });
        }
      }
      return out;
    }, SEL);
    console.log(n + ': ' + (Object.keys(r).length ? JSON.stringify(r) : 'no hits'));
    await ctx.close();
  }
  await b.close();
})();
