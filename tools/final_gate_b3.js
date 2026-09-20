/* Full-site final gate: all 23 pages.
 * Checks per page: HTTP status, JS errors, h1 count, img alt coverage,
 * Schema JSON-LD presence, / --> residue, docH + overflowX at 375, href="#" count.
 */
const { chromium } = require('playwright-core');
const fs = require('fs');

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

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  const out = {};
  for (const [name, url] of PAGES) {
    const ctx = await browser.newContext({ viewport: { width: 375, height: 812 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
    const page = await ctx.newPage();
    const jsErrors = [];
    page.on('pageerror', (e) => jsErrors.push(String(e).slice(0, 120)));
    const resp = await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 60000 });
    await page.evaluate(() => { document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; }); });
    await page.evaluate(async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; });
    await page.waitForTimeout(250);
    const m = await page.evaluate(() => {
      const doc = document.documentElement;
      const imgs = [...document.querySelectorAll('img')];
      return {
        docH: doc.scrollHeight,
        ovx: doc.scrollWidth - doc.clientWidth,
        h1: document.querySelectorAll('h1').length,
        imgs: imgs.length,
        imgsNoAlt: imgs.filter((i) => !i.getAttribute('alt')).length,
        schema: document.querySelectorAll('script[type="application/ld+json"]').length,
        residue: document.body.innerHTML.includes('/ -->'),
        hashLinks: [...document.querySelectorAll('a[href="#"]')].length,
      };
    });
    m.status = resp ? resp.status() : null;
    m.jsErrors = jsErrors.length;
    out[name] = m;
    const flag = (m.status !== 200 || m.jsErrors || m.ovx || m.h1 !== 1 || m.imgsNoAlt || m.residue) ? '  <-- CHECK' : '';
    console.log(`${name}: ${m.status} docH=${m.docH} ovx=${m.ovx} h1=${m.h1} img=${m.imgs}/${m.imgsNoAlt}alt schema=${m.schema} residue=${m.residue} jsErr=${m.jsErrors} hash=${m.hashLinks}${flag}`);
    await ctx.close();
  }
  fs.writeFileSync('/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/final-gate-b3.json', JSON.stringify(out, null, 1));
  await browser.close();
})();
