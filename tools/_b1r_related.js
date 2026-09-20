/* Related 区块高度差异定位 + 网格几何 */
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
    await page.waitForTimeout(400);
    out[s] = await page.evaluate(() => {
      const g = document.querySelector('.sf-related-grid');
      const sec = g ? g.closest('section') : null;
      const cs = g ? getComputedStyle(g) : null;
      const tiles = g ? Array.from(g.querySelectorAll('.sf-tile')) : [];
      /* group tiles by rounded top to derive rows */
      const rows = {};
      tiles.forEach((t) => {
        const r = t.getBoundingClientRect();
        const k = Math.round(r.top);
        (rows[k] = rows[k] || []).push({ h: Math.round(r.height), w: Math.round(r.width), h3: (t.querySelector('h3') || {}).textContent, np: t.querySelectorAll('p').length });
      });
      return {
        gridDisplay: cs ? cs.display : null,
        gridCols: cs ? cs.gridTemplateColumns : null,
        gap: cs ? cs.gap : null,
        secH: sec ? Math.round(sec.getBoundingClientRect().height) : null,
        tileCount: tiles.length,
        rows: Object.keys(rows).sort((a, b) => a - b).map((k) => ({ top: k, n: rows[k].length, tiles: rows[k] })),
      };
    });
    const r = out[s];
    console.log(`--- ${s} secH=${r.secH} cols=${r.gridCols} gap=${r.gap} tiles=${r.tileCount} rows=${r.rows.length}`);
    r.rows.forEach((row) => console.log(`    row@${row.top} n=${row.n} h=[${row.tiles.map((t) => t.h).join(',')}] p=[${row.tiles.map((t) => t.np).join(',')}] ${row.tiles.map((t) => t.h3).join(' / ')}`));
  }
  await browser.close();
  fs.writeFileSync('/tmp/b1s/related.json', JSON.stringify(out, null, 2));
})();
