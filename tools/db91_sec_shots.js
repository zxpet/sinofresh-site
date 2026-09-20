/* 首页 09-19 新增区块截图（sf-card__title-link / See Our Quality Control 所在区块） */
const fs = require('fs');
const path = require('path');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const outDir = process.argv[2];

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('http://sinofresh.local/', { waitUntil: 'networkidle' });
  const reject = page.locator('button:has-text("Reject Non-Essential")');
  if (await reject.count()) await reject.first().click({ force: true }).catch(() => {});
  await page.evaluate(async () => {
    const s = Math.round(innerHeight * 0.8);
    for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 90)); }
  });
  await page.waitForTimeout(1400);
  await page.evaluate(() => document.fonts.ready);
  await page.addStyleTag({ content: 'header{position:static!important}' });

  // 09-19 新增标记：含 "See Our Quality Control" 的区块
  const sec = page.locator('section:has-text("See Our Quality Control")').last();
  if (await sec.count()) {
    await sec.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    await sec.screenshot({ path: path.join(outDir, 'home-sec-quality-1440.png'), animations: 'disabled' });
    console.log('shot: See Our Quality Control section');
  } else {
    console.log('MISS section');
  }

  // 卡片区（sf-card__title-link 出现处）
  const cards = page.locator('.sf-card__title-link').first();
  if (await cards.count()) {
    const box = await cards.boundingBox();
    console.log('sf-card__title-link first box y=' + Math.round(box.y));
    await page.evaluate(() => scrollTo(0, 0));
    const cardSec = page.locator('section:has(.sf-card__title-link)').first();
    await cardSec.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    await cardSec.screenshot({ path: path.join(outDir, 'home-sec-cards-1440.png'), animations: 'disabled' });
    console.log('shot: sf-card section');
  }
  await ctx.close();
  await b.close();
  console.log('DONE');
})();
