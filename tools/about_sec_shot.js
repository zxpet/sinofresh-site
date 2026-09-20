/* Section screenshots for the About tasks: pass out-dir + slug list.
   usage: node about_sec_shot.js <outDir> <slug[,slug...]> */
const fs = require('fs');
const path = require('path');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const outDir = process.argv[2] || '/tmp/about-sec';
const slugs = (process.argv[3] || 'Our Core Values').split(',');
const SELECTOR = {
  'Our Core Values': 'section.wp-block-group:has(h2:text-is("Our Core Values"))',
  'Our Team': 'section.wp-block-group:has(h2:text-is("Our Team"))',
  'Inside Our Factory': 'section.wp-block-group:has(h2:text-is("Inside Our Factory"))',
  'Our Journey': 'section.wp-block-group:has(h2:text-is("Our Journey"))'
};

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  for (const w of [1440, 375]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    await page.goto('http://sinofresh.local/about/', { waitUntil: 'networkidle' });
    const reject = page.locator('button:has-text("Reject Non-Essential")');
    if (await reject.count()) await reject.first().click({ force: true }).catch(() => { });
    // screenshot session only: keep the sticky header from covering the section top
    await page.addStyleTag({ content: 'header{position:static!important;visibility:hidden!important}' });
    await page.evaluate(async () => { const s = Math.round(innerHeight * 0.8); for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 80)); } });
    await page.waitForTimeout(1400);
    for (const slug of slugs) {
      const sel = SELECTOR[slug] || 'section.wp-block-group:has(h2:text-is("' + slug + '"))';
      const sec = page.locator(sel).first();
      if (!(await sec.count())) { console.log('MISS ' + slug); continue; }
      await sec.scrollIntoViewIfNeeded();
      await page.waitForTimeout(400);
      const name = slug.toLowerCase().replace(/[^a-z]+/g, '-').replace(/-+$/, '');
      await sec.screenshot({ path: path.join(outDir, name + '_' + w + '.png'), animations: 'disabled' });
    }
    await ctx.close();
    console.log(w + ' ok');
  }
  await b.close();
})();
