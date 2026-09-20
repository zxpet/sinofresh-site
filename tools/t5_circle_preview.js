const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const U = 'http://sinofresh.local/wp-content/uploads/2026/09/';
const N = ['sam', 'kevin', 'linda', 'echo', 'amy'];

(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const ctx = await b.newContext({ viewport: { width: 780, height: 260 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  const html = `<body style="margin:0;background:#fff;font-family:-apple-system,sans-serif;padding:20px">
  <p style="font:600 12px/1.4 sans-serif;color:#666;margin:0 0 10px">object-fit:cover · object-position:center · 120px circle (2x)</p>
  <div style="display:flex;gap:16px">${N.map(n => `<figure style="margin:0;text-align:center">
    <div style="width:120px;height:120px;border-radius:999px;overflow:hidden;background:#f3f6f4">
      <img src="${U}team-${n}.webp" style="display:block;width:100%;height:100%;object-fit:cover;object-position:center;border-radius:999px">
    </div>
    <figcaption style="font:600 12px/1.6 sans-serif;color:#333">${n}</figcaption></figure>`).join('')}</div></body>`;
  await page.setContent(html, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'screenshots/t5_circle_preview.png' });
  await b.close();
  console.log('ok');
})();
