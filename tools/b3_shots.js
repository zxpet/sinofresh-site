/* b3 shots: after screenshots for the 4 visually-changed pages */
const { chromium } = require('playwright-core');
const BASE = 'http://sinofresh.local';
const SHOTS = [
  ['cooperation', '/cooperation/', 375],
  ['cooperation-768', '/cooperation/', 768],
  ['blog-768', '/blog/', 768],
  ['404', '/no-such-page-b3/', 375],
  ['cookie', '/cookie-policy/', 375],
];
(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  for (const [name, url, w] of SHOTS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 1, isMobile: w <= 768, hasTouch: w <= 768 });
    const page = await ctx.newPage();
    await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 60000 });
    await page.evaluate(() => { document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; i.decoding = 'sync'; }); });
    await page.evaluate(async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; });
    await page.waitForTimeout(300);
    await page.evaluate(async () => {
      await Promise.all([...document.querySelectorAll('img')].map((i) => i.complete && i.naturalWidth ? 0 : new Promise((r) => { i.addEventListener('load', r, { once: true }); i.addEventListener('error', r, { once: true }); setTimeout(r, 4000); })));
    });
    await page.screenshot({ path: `/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/batch3/after-${name}.png`, fullPage: true });
    console.log('shot', name);
    await ctx.close();
  }
  await browser.close();
})();
