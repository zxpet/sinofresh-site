/*
 * Header screenshots for the hamburger-position task.
 *   NODE_PATH=... node tools/_hdr_shots.js <label>
 * Writes screenshots/hdr-<label>-375.png (top 140px) and -1440.png (top 180px),
 * plus a full-viewport phone shot.
 */
const { chromium } = require('playwright-core');

const label = process.argv[2] || 'before';
const BASE = 'http://sinofresh.local/';

async function dismissCookie(page) {
  const btn = page.locator('#cookie-accept, .sf-cookie__accept, [data-cookie-accept]').first();
  if (await btn.count() && await btn.isVisible().catch(() => false)) {
    await btn.click().catch(() => {});
    await page.waitForTimeout(200);
  }
}

(async () => {
  const browser = await chromium.launch();
  for (const [vw, vh, clipH, tag] of [[375, 812, 150, '375'], [1440, 900, 180, '1440']]) {
    const ctx = await browser.newContext({ viewport: { width: vw, height: vh }, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await dismissCookie(page);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(400);
    // neutralise sticky so we always capture the un-scrolled header
    await page.evaluate(() => {
      const h = document.querySelector('.sf-header');
      if (h) { h.style.position = 'static'; h.style.top = 'auto'; }
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(200);
    await page.screenshot({ path: `screenshots/hdr-${label}-${tag}.png`, clip: { x: 0, y: 0, width: vw, height: clipH } });
    if (tag === '375') {
      await page.screenshot({ path: `screenshots/hdr-${label}-375-full.png` });
    }
    console.log('wrote screenshots/hdr-' + label + '-' + tag + '.png');
    await ctx.close();
  }
  await browser.close();
})();
