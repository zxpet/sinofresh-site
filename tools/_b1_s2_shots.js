/* Batch 1 / Stage 2.1+2.2 截图交付
   桌面 1440：section#configurator 折叠态（默认）+ 展开态（open=true）
   移动 375 ：section#configurator（应完全不变）
   Usage: node tools/_b1_s2_shots.js [outdir]  -> 默认 /tmp/b1/s2/shots */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const SLUGS = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
const OUT = process.argv[2] || '/tmp/b1/s2/shots';
fs.mkdirSync(OUT, { recursive: true });

async function accept(p) {
  const r = p.locator('button:has-text("Reject Non-Essential")');
  if (await r.count()) await r.first().click({ force: true }).catch(() => {});
}

async function shot(page, sel, file) {
  const el = page.locator(sel);
  if (!(await el.count())) { console.log('  MISS ' + sel); return false; }
  await el.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(260);
  await el.screenshot({ path: file }).catch((e) => { console.log('  ERR ' + file + ' ' + e.message); });
  return true;
}

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });

  /* ---------- desktop 1440 ---------- */
  const cD = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pd = await cD.newPage();
  const state = {};
  for (const s of SLUGS) {
    await pd.goto(`http://sinofresh.local/products/${s}/`, { waitUntil: 'load', timeout: 45000 });
    await accept(pd);
    await pd.waitForTimeout(420);
    // load-time state
    state[s] = await pd.evaluate(() => {
      const f = document.querySelector('.configurator__fold');
      const svg = document.querySelector('.configurator__sprite');
      const c = document.querySelector('.configurator');
      return {
        foldOpen: f ? f.open : null,
        svgInsideFold: !!(f && svg && f.contains(svg)),
        cfgInsideFoldBody: !!(f && c && f.querySelector('.configurator__fold-body') && f.querySelector('.configurator__fold-body').contains(c)),
        exploreOutsideFold: !!(f && document.querySelector('.configurator__explore-row') && !f.contains(document.querySelector('.configurator__explore-row'))),
      };
    });
    await shot(pd, 'section#configurator', `${OUT}/d-${s}-folded.png`);
    await pd.evaluate(() => { document.querySelector('.configurator__fold').open = true; });
    await pd.waitForTimeout(320);
    await shot(pd, 'section#configurator', `${OUT}/d-${s}-expanded.png`);
    console.log('  desktop', s);
  }
  await cD.close();

  /* ---------- mobile 375 ---------- */
  const cM = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const pm = await cM.newPage();
  const mstate = {};
  for (const s of SLUGS) {
    await pm.goto(`http://sinofresh.local/products/${s}/`, { waitUntil: 'load', timeout: 45000 });
    await accept(pm);
    await pm.waitForTimeout(420);
    mstate[s] = await pm.evaluate(() => {
      const f = document.querySelector('.configurator__fold');
      const sum = f && f.querySelector('summary');
      const body = f && f.querySelector('.configurator__fold-body');
      const icon = document.querySelector('.configurator__fold-icon');
      const bodyVis = body ? body.checkVisibility({ contentVisibilityAuto: true, opacityProperty: true, visibilityProperty: true }) : null;
      return {
        foldOpen: f ? f.open : null,
        bodyVisible: bodyVis,
        summaryPointerEvents: sum ? getComputedStyle(sum).pointerEvents : null,
        iconDisplay: icon ? getComputedStyle(icon).display : null,
        barDisplay: (() => { const b = document.querySelector('.configurator__bar'); return b ? getComputedStyle(b).display : null; })(),
      };
    });
    await shot(pm, 'section#configurator', `${OUT}/m-${s}.png`);
    console.log('  mobile ', s);
  }
  await cM.close();

  await browser.close();
  fs.writeFileSync(`${OUT}/state.json`, JSON.stringify({ desktop: state, mobile: mstate }, null, 2));
  console.log('OK -> ' + OUT);
})();
