/* Related section shots: drops page desktop + mobile */
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');
const OUT = path.resolve(__dirname, '..', 'screenshots', 'related-fix');
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  async function shot(name, viewport) {
    const ctx = await browser.newContext({ viewport, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    await page.goto('http://sinofresh.local/products/drops/', { waitUntil: 'networkidle', timeout: 90000 });
    await page.evaluate(() => document.fonts.ready);
    const sec = page.locator('section:has(h2:text("Related Dosage Forms"))').last();
    await sec.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    await sec.screenshot({ path: path.join(OUT, `${name}.png`) });
    const ov = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    console.log(name, 'overflow-x:', ov);
    await ctx.close();
  }
  await shot('drops-related-desktop-1440', { width: 1440, height: 900 });
  await shot('drops-related-mobile-375', { width: 375, height: 812 });
  await browser.close();
  console.log('done');
})();
