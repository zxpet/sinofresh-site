/* 阶段 1 截图交付：8 剂型页桌面 1440（Hero 视口 + 速览表元素）+ 移动 375 */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const SLUGS = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
const OUT = process.argv[2] || '/tmp/b1/shots_s1';
fs.mkdirSync(OUT, { recursive: true });

async function accept(p) {
  const r = p.locator('button:has-text("Reject Non-Essential")');
  if (await r.count()) await r.first().click({ force: true }).catch(() => {});
}

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });

  const cD = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pd = await cD.newPage();
  for (const s of SLUGS) {
    await pd.goto(`http://sinofresh.local/products/${s}/`, { waitUntil: 'load', timeout: 45000 });
    await accept(pd);
    await pd.waitForTimeout(500);
    await pd.screenshot({ path: `${OUT}/d-${s}-hero.png` });
    const el = pd.locator('.sf-spectable');
    await el.screenshot({ path: `${OUT}/d-${s}-table.png` });
    console.log('  desktop', s);
  }
  await cD.close();

  const cM = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const pm = await cM.newPage();
  for (const s of ['liquids', 'dental-chews', 'soft-chews']) {
    await pm.goto(`http://sinofresh.local/products/${s}/`, { waitUntil: 'load', timeout: 45000 });
    await accept(pm);
    await pm.waitForTimeout(500);
    await pm.screenshot({ path: `${OUT}/m-${s}-hero.png` });
    await pm.locator('.sf-spectable').screenshot({ path: `${OUT}/m-${s}-table.png` });
    console.log('  mobile ', s);
  }
  await cM.close();

  await browser.close();
  console.log('OK -> ' + OUT);
})();
