const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  for (const w of [1440, 375]) {
    const ctx = await b.newContext({ viewport: { width: w, height: w === 375 ? 760 : 900 }, deviceScaleFactor: w === 375 ? 2 : 1 });
    const page = await ctx.newPage();
    await page.goto('http://sinofresh.local/about/', { waitUntil: 'networkidle' });
    await page.evaluate(async () => { await document.fonts.ready; const s = Math.round(innerHeight * 0.8); for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } scrollTo(0, 0); });
    await page.waitForTimeout(800);
    // sticky header would cover the section top in an element shot — neutralize for this session only
    await page.addStyleTag({ content: 'header, .sf-header, [class*="header"]{position:static!important;visibility:hidden!important}' });
    const el = await page.evaluateHandle(() => {
      const secs = [...document.querySelectorAll('.wp-site-blocks > *')];
      return secs.find(s => { const h = s.querySelector('h2'); return h && /^our team$/i.test(h.textContent.trim()); });
    });
    await el.asElement().scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    await el.asElement().screenshot({ path: `screenshots/t5_${w}_after_sec.png` });
    await ctx.close();
    console.log('shot', w);
  }
  await b.close();
})();
