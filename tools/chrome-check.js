/* Chrome(Chromium) regression check for Safari card fixes.
   Usage: node chrome-check.js <url> <outPng> */
const { chromium } = require('playwright-core');

(async () => {
  const [url, outPng] = process.argv.slice(2);
  const browser = await chromium.launch({
    headless: true,
    args: ['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  const data = await page.evaluate(() => {
    const t = document.querySelector('.sf-tile');
    if (!t) return { tiles: 0 };
    const m = t.querySelector('.sf-tile__media');
    const img = m.querySelector('img');
    const col = document.querySelector('.sf-dosage-grid > .wp-block-column');
    return {
      tiles: document.querySelectorAll('.sf-tile').length,
      colW: Math.round(col.getBoundingClientRect().width),
      mediaH: Math.round(m.getBoundingClientRect().height),
      imgH: Math.round(img.getBoundingClientRect().height),
      tileH: Math.round(t.getBoundingClientRect().height),
      hoverOK: (() => {
        const a = t.querySelector('a');
        const r = a.getBoundingClientRect();
        const el = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        return a === el || a.contains(el);
      })(),
    };
  });
  console.log(JSON.stringify(data));
  await page.locator('.sf-dosage-grid').scrollIntoViewIfNeeded();
  await page.evaluate(() => window.scrollBy(0, -120));
  await page.waitForTimeout(400);
  await page.screenshot({ path: outPng });
  await browser.close();
})().catch((e) => { console.error('FAIL: ' + e.message); process.exit(1); });
