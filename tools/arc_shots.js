/* Arc screenshots: desktop map block, mobile 375, reduced-motion static check */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const OUT = path.resolve(__dirname, '..', 'screenshots', 'map-arcs');
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });

  async function shot(name, viewport, opts = {}) {
    const ctx = await browser.newContext({
      viewport,
      deviceScaleFactor: 2,
      ...(opts.reduced ? { reducedMotion: 'reduce' } : {}),
    });
    const page = await ctx.newPage();
    await page.goto('http://sinofresh.local/', { waitUntil: 'networkidle', timeout: 90000 });
    await page.evaluate(() => document.fonts.ready);
    const map = page.locator('section:has(.sf-slot--map)').first();
    await map.scrollIntoViewIfNeeded();
    await page.waitForTimeout(opts.reduced ? 300 : 1200);
    await map.screenshot({ path: path.join(OUT, `${name}.png`) });
    // overflow check
    const ov = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    console.log(name, 'overflow-x:', ov);
    await ctx.close();
  }

  await shot('desktop-1440', { width: 1440, height: 900 });
  await shot('desktop-1440-t2', { width: 1440, height: 900 });
  await shot('mobile-375', { width: 375, height: 812 });
  await shot('reduced-motion-1440', { width: 1440, height: 900 }, { reduced: true });
  await browser.close();
  console.log('done');
})();
