/* b3 leak: 375 docH spot-check on non-batch-3 pages vs batch2-final2 baseline */
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local';
const PAGES = [
  ['home', '/'],
  ['products', '/products/'],
  ['soft-chews', '/products/soft-chews/'],
  ['about', '/about/'],
  ['quality', '/quality/'],
  ['services', '/services/'],
  ['contact', '/contact/'],
  ['factory-tour', '/factory-tour/'],
];

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  const out = {};
  for (const [name, url] of PAGES) {
    const ctx = await browser.newContext({ viewport: { width: 375, height: 812 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
    const page = await ctx.newPage();
    await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 60000 });
    await page.evaluate(() => {
      document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; });
    });
    await page.evaluate(async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; });
    await page.waitForTimeout(300);
    const m = await page.evaluate(() => ({
      docH: document.documentElement.scrollHeight,
      ovx: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    }));
    out[name] = m;
    console.log(`${name}: docH=${m.docH} ovx=${m.ovx}`);
    await ctx.close();
  }
  require('fs').writeFileSync('/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/batch3-leak.json', JSON.stringify(out, null, 1));
  await browser.close();
})();
