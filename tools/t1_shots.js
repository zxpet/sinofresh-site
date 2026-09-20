/* 任务1 底部区域截图：mode=before|after, outDir */
const fs = require('fs');
const path = require('path');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const NODE = '/Users/meng/.workbuddy/binaries/node/versions/22.22.2-3/bin/node';

const mode = process.argv[2] || 'after';
const outDir = process.argv[3];

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const br = await pw.chromium.launch({ executablePath: CHROME, headless: true });

  for (const vw of [375, 1440]) {
    const ctx = await br.newContext({ viewport: { width: vw, height: 812 } });
    const p = await ctx.newPage();
    await p.addInitScript(() => { try { localStorage.setItem('sf_cookie_consent', JSON.stringify({ necessary: true, analytics: false, marketing: false })); } catch (e) {} });
    await p.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'networkidle' });
    await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { scrollTo(0, y); await new Promise(r => setTimeout(r, 70)); } scrollTo(0, document.body.scrollHeight); });
    await p.waitForTimeout(1200);
    await p.evaluate(() => document.fonts.ready);
    // 底部 200px 放大：语言切换器 + 吸底条
    await p.screenshot({ path: path.join(outDir, mode + '-bottom-' + vw + '.png'), clip: { x: 0, y: 612, width: vw, height: 200 } });
    console.log('shot: bottom-' + vw);

    if (vw === 375) {
      await p.evaluate(() => { const t = document.querySelector('.configurator__bar-trigger'); if (t) t.click(); });
      await p.waitForTimeout(700);
      await p.screenshot({ path: path.join(outDir, mode + '-drawer-open-375.png') });
      console.log('shot: drawer-open-375');
    }
    await ctx.close();
  }
  await br.close();
  console.log('DONE');
})();
