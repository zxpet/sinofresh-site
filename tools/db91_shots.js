/* DB91 回收站处理后的首页确认截图
   usage: node db91_shots.js <outDir> */
const fs = require('fs');
const path = require('path');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const outDir = process.argv[2] || '/tmp/db91-shots';

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });

  // ---- 桌面：首屏 + 整页 ----
  for (const w of [1440, 375]) {
    const h = w === 1440 ? 900 : 812;
    const ctx = await b.newContext({ viewport: { width: w, height: h } });
    const page = await ctx.newPage();
    const errs = [];
    page.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 120)); });
    page.on('requestfailed', r => errs.push('REQFAIL ' + r.url().slice(0, 100)));

    await page.goto('http://sinofresh.local/', { waitUntil: 'networkidle' });
    // 关掉 cookie banner（若有）
    const reject = page.locator('button:has-text("Reject Non-Essential")');
    if (await reject.count()) await reject.first().click({ force: true }).catch(() => {});
    await page.waitForTimeout(300);

    // 预滚动逼出懒加载
    await page.evaluate(async () => {
      const s = Math.round(innerHeight * 0.8);
      for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 90)); }
      scrollTo(0, 0);
    });
    await page.waitForTimeout(1200);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(300);

    const bodyH = await page.evaluate(() => document.body.scrollHeight);
    console.log(`${w}: bodyScrollHeight=${bodyH}  consoleErrors=${errs.length}`);
    if (errs.length) console.log('   ' + errs.slice(0, 6).join('\n   '));

    // 首屏（仅压平 sticky header，不隐藏，保留可见性证明）
    await page.addStyleTag({ content: 'header{position:static!important}' });
    await page.screenshot({ path: path.join(outDir, `home-top-${w}.png`), animations: 'disabled' });

    // 整页
    await page.screenshot({ path: path.join(outDir, `home-full-${w}.png`), fullPage: true, animations: 'disabled' });

    await ctx.close();
  }
  await b.close();
  console.log('DONE -> ' + outDir);
})();
