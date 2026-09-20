// contact page full screenshots (desktop + mobile)
const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch();
  for (const [vw, vh, tag] of [[1440, 900, '1440'], [375, 812, '375']]) {
    const ctx = await b.newContext({ viewport: { width: vw, height: vh }, deviceScaleFactor: 2 });
    const p = await ctx.newPage();
    await p.goto('http://sinofresh.local/contact/', { waitUntil: 'networkidle' });
    const btn = p.locator('#cookie-accept, .sf-cookie__accept, [data-cookie-accept]').first();
    if (await btn.count() && await btn.isVisible().catch(() => false)) await btn.click().catch(() => {});
    await p.evaluate(() => document.fonts.ready);
    await p.waitForTimeout(500);
    await p.screenshot({ path: 'screenshots/contact-current-' + tag + '.png', fullPage: true });
    console.log(tag, 'fullPage height:', await p.evaluate(() => document.documentElement.scrollHeight));
    await ctx.close();
  }
  await b.close();
})();
