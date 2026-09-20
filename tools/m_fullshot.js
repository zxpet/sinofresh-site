// 整页截图：440px 视口，移除 cookie 弹窗等浮层后 fullPage
// 用法: node m_fullshot.js <url> <width> <outfile> [height]
const path = require('path');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME +
  '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const [url, w, out] = [process.argv[2], Number(process.argv[3]), process.argv[4]];

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  await page.evaluate(() => document.fonts.ready.then(() => true));
  await page.evaluate(async () => {
    const step = Math.round(window.innerHeight * 0.8);
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo(0, y);
      await new Promise(r => setTimeout(r, 50));
    }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(600);
  // 点击 cookie 横幅的拒绝/接受按钮（精准关闭，不做批量隐藏）
  await page.evaluate(() => {
    const btns = [...document.querySelectorAll('button, a, [role="button"]')];
    const hit = btns.find(b => /reject non-essential|accept all/i.test((b.innerText || '').trim()));
    if (hit) hit.click();
  });
  await page.waitForTimeout(500);
  await page.evaluate(() => {
    // 兜底：若弹窗仍在（display 未变），直接移除其最外层
    const overlay = [...document.querySelectorAll('body *')].find(el =>
      /We use cookies to improve your experience/i.test(el.innerText || '') &&
      el.children.length && !el.innerText.includes('Your Private Label'));
    if (overlay) {
      let top = overlay;
      while (top.parentElement && top.parentElement !== document.body && top.parentElement !== document.querySelector('.wp-site-blocks')) top = top.parentElement;
      top.remove();
    }
  });
  await page.waitForTimeout(200);
  await page.screenshot({ path: out, fullPage: true });
  console.log('saved:', out);
  await browser.close();
})();
