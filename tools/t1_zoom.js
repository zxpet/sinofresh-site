/* 任务1：底部右下角 3 倍放大特写，用于判断语言切换器浮起后的圆角观感 */
const fs = require('fs');
const path = require('path');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const outDir = process.argv[2];
(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const br = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const ctx = await br.newContext({ viewport: { width: 375, height: 812 }, deviceScaleFactor: 3 });
  const p = await ctx.newPage();
  await p.addInitScript(() => { try { localStorage.setItem('sf_cookie_consent', JSON.stringify({ necessary: true, analytics: false, marketing: false })); } catch (e) {} });
  await p.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'networkidle' });
  await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { scrollTo(0, y); await new Promise(r => setTimeout(r, 70)); } scrollTo(0, document.body.scrollHeight); });
  await p.waitForTimeout(1200);
  await p.evaluate(() => document.fonts.ready);
  const geo = await p.evaluate(() => {
    const G = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return { x: Math.round(r.x), y: Math.round(r.y), r: Math.round(r.right), b: Math.round(r.bottom), radius: s.borderRadius, bg: s.backgroundColor }; };
    return { sw: G(document.querySelector('.trp-language-switcher')), bar: G(document.querySelector('.configurator__bar')) };
  });
  console.log(JSON.stringify(geo));
  await p.screenshot({ path: path.join(outDir, 'zoom-switcher-bar.png'), clip: { x: 180, y: 664, width: 195, height: 148 } });
  console.log('shot: zoom-switcher-bar');
  await ctx.close(); await br.close();
})();
