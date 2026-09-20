/* 移动 375 实测：配置器移动端处理 + 逐区块高度 */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const SLUGS = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
fs.mkdirSync('/tmp/b1s', { recursive: true });

async function warmImages(page) {
  await page.evaluate(async () => {
    const H = document.documentElement.scrollHeight;
    for (let y = 0; y < H + 900; y += 500) { scrollTo(0, y); await new Promise((r) => setTimeout(r, 60)); }
    scrollTo(0, 0);
  });
  await page.waitForTimeout(250);
  await page.evaluate(() => Promise.all(Array.from(document.images).map((i) => (i.complete ? 0 : new Promise((r) => { i.onload = i.onerror = r; setTimeout(r, 1500); })))));
  await page.evaluate(() => scrollTo(0, 0));
  await page.waitForTimeout(220);
}

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const ctx = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  const out = {};
  for (const s of SLUGS) {
    await page.goto(`http://sinofresh.local/products/${s}/`, { waitUntil: 'load', timeout: 45000 });
    await page.waitForTimeout(300);
    await warmImages(page);
    out[s] = await page.evaluate(() => {
      const q = (x) => document.querySelector(x);
      const R = (el) => (el ? { h: Math.round(el.getBoundingClientRect().height), w: Math.round(el.getBoundingClientRect().width) } : null);
      const vis = (el) => (el ? el.checkVisibility({ contentVisibilityAuto: true, opacityProperty: true, visibilityProperty: true }) : null);
      const secs = Array.from(document.querySelectorAll('.wp-site-blocks > .wp-block-group')).map((x) => ({
        id: x.id || null,
        cls: String(x.getAttribute('class') || '').replace('wp-block-group', '').trim().slice(0, 40),
        h: Math.round(x.getBoundingClientRect().height),
      }));
      const fold = q('.configurator__fold');
      const body = q('.configurator__fold-body');
      return {
        docH: document.documentElement.scrollHeight,
        heroH: q('.sf-hero-inner') ? Math.round(q('.sf-hero-inner').getBoundingClientRect().height) : null,
        sections: secs,
        cfg: {
          secH: q('#configurator') ? Math.round(q('#configurator').getBoundingClientRect().height) : null,
          foldOpen: fold ? fold.open : null,
          foldBodyVisible: vis(body),
          foldBodyH: R(body) && R(body).h,
          summaryPointer: fold && fold.querySelector('summary') ? getComputedStyle(fold.querySelector('summary')).pointerEvents : null,
          iconDisplay: q('.configurator__fold-icon') ? getComputedStyle(q('.configurator__fold-icon')).display : null,
          barDisplay: q('.configurator__bar') ? getComputedStyle(q('.configurator__bar')).display : null,
          mobilebarDisplay: q('.configurator__mobilebar') ? getComputedStyle(q('.configurator__mobilebar')).display : null,
          summaryColPos: q('.configurator__summary-col') ? getComputedStyle(q('.configurator__summary-col')).position : null,
          drawerHidden: q('#configurator-drawer') ? q('#configurator-drawer').hidden : null,
          groups: document.querySelectorAll('.configurator__group').length,
        },
        gridCols: (() => { const g = q('.sf-related-grid'); return g ? getComputedStyle(g).gridTemplateColumns : null; })(),
      };
    });
    console.log(`  ${s}: doc=${out[s].docH} hero=${out[s].heroH} cfg=${out[s].cfg.secH} bar=${out[s].cfg.barDisplay} drawerHidden=${out[s].cfg.drawerHidden} foldOpen=${out[s].cfg.foldOpen} bodyVis=${out[s].cfg.foldBodyVisible}`);
  }
  await browser.close();
  fs.writeFileSync('/tmp/b1s/mobile.json', JSON.stringify(out, null, 2));
  console.log('OK -> /tmp/b1s/mobile.json');
})();
