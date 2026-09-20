/* Desktop geometry fingerprint (1440px) — the before/after baseline for the
 * rollout. Media-query-only changes must leave every number here identical.
 *   node site_fingerprint.js before|after
 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const BASE = 'http://sinofresh.local';
const PAGES = [
  ['home', '/'], ['products', '/products/'], ['soft-chews', '/products/soft-chews/'],
  ['tablets', '/products/tablets/'], ['powders', '/products/powders/'], ['pastes', '/products/pastes/'],
  ['drops', '/products/drops/'], ['liquids', '/products/liquids/'], ['fish-oil', '/products/fish-oil/'],
  ['dental-chews', '/products/dental-chews/'], ['about', '/about/'], ['quality', '/quality/'],
  ['factory-tour', '/factory-tour/'], ['services', '/services/'], ['cooperation', '/cooperation/'],
  ['contact', '/contact/'], ['blog', '/blog/'], ['test-article', '/test-article/'],
  ['privacy-policy', '/privacy-policy/'], ['cookie-policy', '/cookie-policy/'], ['terms', '/terms/'],
  ['404', '/404-probe/'], ['search', '/?s=soft'],
];

function fingerprint() {
  const r = (el) => { const b = el.getBoundingClientRect(); return { y: Math.round(b.y + scrollY), w: Math.round(b.width), h: Math.round(b.height) }; };
  const main = document.querySelector('main') || document.body;
  return {
    docH: document.documentElement.scrollHeight,
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    sections: [...main.querySelectorAll('section, footer, header')].map(s => r(s)).filter(x => x.h > 0),
    cols: [...document.querySelectorAll('.wp-block-columns')].map(c => ({
      n: c.children.length,
      kids: [...c.children].map(k => r(k)).map(k => `${k.w}x${k.h}@${k.w && k.y}`),
    })),
    grids: [...document.querySelectorAll('.sf-dosage-grid, .sf-certs, .sf-panel--3, .sf-panel--bare, .sf-strip, .sf-triple')].map(g => ({
      cls: g.className.toString().split(' ').filter(x => /^sf-/.test(x)).join('.'),
      style: getComputedStyle(g).gridTemplateColumns + '|' + getComputedStyle(g).display,
      ...r(g),
    })),
  };
}

(async () => {
  const label = process.argv[2] || 'before';
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  const out = {};
  for (const [slug, url] of PAGES) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    try { await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 90000 }); }
    catch (e) { out[slug] = { error: String(e).slice(0, 80) }; await ctx.close(); continue; }
    await page.waitForTimeout(400);
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(async () => { const s = innerHeight; for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 50)); } scrollTo(0, 0); });
    await page.waitForTimeout(400);
    out[slug] = await page.evaluate(fingerprint);
    await ctx.close();
    console.error('fp', slug, out[slug].docH);
  }
  await browser.close();
  const f = path.resolve(__dirname, '..', 'screenshots', `site-fingerprint-1440-${label}.json`);
  fs.mkdirSync(path.dirname(f), { recursive: true });
  fs.writeFileSync(f, JSON.stringify(out, null, 1));
  console.log('written', f);
})();
