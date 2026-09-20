const path = require('path');
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const out = '/Users/meng/Workbuddy/sinofresh外贸网站建设/screenshots/about-t1';
(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  fs.mkdirSync(out, { recursive: true });
  for (const w of [1440, 375]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    await page.goto('http://sinofresh.local/about/', { waitUntil: 'networkidle' });
    await page.evaluate(async () => { const s = Math.round(innerHeight*0.8); for (let y=0;y<document.body.scrollHeight;y+=s){scrollTo(0,y);await new Promise(r=>setTimeout(r,60));} scrollTo(0,0); });
    await page.waitForTimeout(400);
    for (const [name, kw] of [['who', 'who we are'], ['journey', 'journey']]) {
      const h = await page.evaluateHandle((k) => [...document.querySelectorAll('.wp-site-blocks > section')].find(s => { const h2=s.querySelector('h2'); return h2 && h2.textContent.trim().toLowerCase().includes(k); }), kw);
      const el = h.asElement();
      if (el) await el.screenshot({ path: path.join(out, `t1_${name}_${w}.png`), animations: 'disabled' });
    }
    await ctx.close();
  }
  await b.close(); console.log('shots done');
})();
