/* Related 区块：滚动到位 + 等图后测量，区分结构差异与懒加载假象 */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const SLUGS = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
fs.mkdirSync('/tmp/b1s', { recursive: true });

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const out = {};
  for (const s of SLUGS) {
    await page.goto(`http://sinofresh.local/products/${s}/`, { waitUntil: 'load', timeout: 45000 });
    await page.waitForTimeout(300);
    /* 1) 未滚动（懒加载未触发）先量一次 */
    const before = await page.evaluate(() => {
      const grids = Array.from(document.querySelectorAll('.sf-related-grid'));
      return {
        gridCount: grids.length,
        perGrid: grids.map((g) => ({ n: g.querySelectorAll(':scope > .wp-block-column').length, tiles: g.querySelectorAll('.sf-tile').length, h: Math.round(g.getBoundingClientRect().height) })),
        totalTiles: document.querySelectorAll('.sf-related-grid .sf-tile').length,
        tileH: Array.from(document.querySelectorAll('.sf-related-grid .sf-tile')).map((t) => Math.round(t.getBoundingClientRect().height)),
        imgState: Array.from(document.querySelectorAll('.sf-related-grid .sf-tile__media img')).map((i) => ({ src: i.getAttribute('src'), loading: i.getAttribute('loading'), complete: i.complete, nw: i.naturalWidth, w: Math.round(i.getBoundingClientRect().width), h: Math.round(i.getBoundingClientRect().height) })),
      };
    });
    /* 2) 滚动到位并等待懒加载完成 */
    await page.evaluate(() => {
      const g = document.querySelector('.sf-related-grid');
      if (g) g.closest('section').scrollIntoView({ block: 'center', behavior: 'instant' });
    });
    await page.waitForTimeout(700);
    await page.evaluate(() => Promise.all(Array.from(document.images).map((i) => (i.complete ? 0 : new Promise((r) => { i.onload = i.onerror = r; setTimeout(r, 1500); })))));
    const after = await page.evaluate(() => {
      const grids = Array.from(document.querySelectorAll('.sf-related-grid'));
      return {
        gridCount: grids.length,
        perGrid: grids.map((g) => ({ n: g.querySelectorAll(':scope > .wp-block-column').length, tiles: g.querySelectorAll('.sf-tile').length, h: Math.round(g.getBoundingClientRect().height), cols: getComputedStyle(g).gridTemplateColumns })),
        totalTiles: document.querySelectorAll('.sf-related-grid .sf-tile').length,
        tileH: Array.from(document.querySelectorAll('.sf-related-grid .sf-tile')).map((t) => Math.round(t.getBoundingClientRect().height)),
        imgState: Array.from(document.querySelectorAll('.sf-related-grid .sf-tile__media img')).map((i) => ({ src: i.getAttribute('src'), loading: i.getAttribute('loading'), complete: i.complete, nw: i.naturalWidth, w: Math.round(i.getBoundingClientRect().width), h: Math.round(i.getBoundingClientRect().height) })),
      };
    });
    out[s] = { before, after };
    console.log(`--- ${s}: 未滚动 grid=${before.gridCount} perGrid=${JSON.stringify(before.perGrid.map((x) => x.n))} tiles=${before.totalTiles} tileH=[${before.tileH.join(',')}]`);
    console.log(`      等图后 grid=${after.gridCount} perGrid=${JSON.stringify(after.perGrid.map((x) => x.n))} tiles=${after.totalTiles} tileH=[${after.tileH.join(',')}]`);
    console.log(`      img: ` + after.imgState.map((i) => `${(i.src || '').split('/').pop()}:nw=${i.nw},${i.w}x${i.h},lazy=${i.loading}`).join(' | '));
  }
  await browser.close();
  fs.writeFileSync('/tmp/b1s/related2.json', JSON.stringify(out, null, 2));
})();
