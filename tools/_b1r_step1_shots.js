/* Batch 1 / 步骤 1 截图交付 —— 回滚后（配置器默认展开）
   桌面 1440：8 页 section#configurator（展开态）+ liquids/soft-chews 全页 + Hero
   移动 375 ：8 页 section#configurator + liquids/soft-chews 全页
   Usage: node tools/_b1r_step1_shots.js [outdir]  -> 默认 /tmp/b1/step1/shots */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const SLUGS = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
const FULL = ['liquids', 'soft-chews'];
const OUT = process.argv[2] || '/tmp/b1/step1/shots';
fs.mkdirSync(OUT, { recursive: true });

async function accept(p) {
  const r = p.locator('button:has-text("Reject Non-Essential")');
  if (await r.count()) await r.first().click({ force: true }).catch(() => {});
}

async function settle(page) {
  await page.evaluate(async () => {
    const s = Math.round(innerHeight * 0.8);
    for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise((r) => setTimeout(r, 60)); }
    scrollTo(0, 0);
    await new Promise((r) => setTimeout(r, 300));
  });
  await page.evaluate(() => Promise.all(
    Array.from(document.images).filter((i) => !i.complete).map((i) => new Promise((r) => { i.onload = i.onerror = r; }))
  ));
}

async function shot(page, sel, file) {
  const el = page.locator(sel);
  if (!(await el.count())) { console.log('  MISS ' + sel); return false; }
  await el.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(280);
  await el.screenshot({ path: file }).catch((e) => console.log('  ERR ' + file + ' ' + e.message));
  return true;
}

const probe = () => {
  const f = document.querySelector('.configurator__fold');
  const cfg = document.querySelector('.configurator');
  const exp = document.querySelector('.sf-explore');
  const q = (s) => document.querySelector(s);
  const smt = (s) => { const e = q(s); return e ? getComputedStyle(e).scrollMarginTop : null; };
  const r = cfg ? cfg.getBoundingClientRect() : null;
  return {
    foldExists: !!f,
    exploreParent: exp ? '.' + String(exp.parentElement.getAttribute('class')) : null,
    cfgVisible: cfg ? cfg.checkVisibility({ contentVisibilityAuto: true, opacityProperty: true, visibilityProperty: true }) : null,
    cfgRect: r ? { top: Math.round(r.top + scrollY), h: Math.round(r.height), w: Math.round(r.width) } : null,
    sectionChildren: Array.from(q('#configurator').children).map((c) => c.tagName.toLowerCase()),
    scrollMargins: { formulas: smt('#formulas'), configurator: smt('#configurator') },
    docH: document.body.scrollHeight,
  };
};

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const state = { desktop: {}, mobile: {} };

  /* ---------- desktop 1440 ---------- */
  const cD = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const pd = await cD.newPage();
  for (const s of SLUGS) {
    await pd.goto(`http://sinofresh.local/products/${s}/`, { waitUntil: 'load', timeout: 45000 });
    await accept(pd);
    await settle(pd);
    state.desktop[s] = await pd.evaluate(probe);
    await shot(pd, 'section#configurator', `${OUT}/d-${s}-configurator.png`);
    if (FULL.includes(s)) {
      await shot(pd, '#hero, .sf-hero, section:first-of-type', `${OUT}/d-${s}-hero.png`);
      await pd.screenshot({ path: `${OUT}/d-${s}-full.png`, fullPage: true }).catch((e) => console.log('  ERR full ' + e.message));
    }
    console.log('  desktop', s, JSON.stringify(state.desktop[s].cfgRect));
  }
  await cD.close();

  /* ---------- mobile 375 ---------- */
  const cM = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const pm = await cM.newPage();
  for (const s of SLUGS) {
    await pm.goto(`http://sinofresh.local/products/${s}/`, { waitUntil: 'load', timeout: 45000 });
    await accept(pm);
    await settle(pm);
    state.mobile[s] = await pm.evaluate(probe);
    state.mobile[s].overflowX = await pm.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    await shot(pm, 'section#configurator', `${OUT}/m-${s}-configurator.png`);
    if (FULL.includes(s)) {
      await pm.screenshot({ path: `${OUT}/m-${s}-full.png`, fullPage: true }).catch((e) => console.log('  ERR full ' + e.message));
    }
    console.log('  mobile ', s, 'overflowX=' + state.mobile[s].overflowX, JSON.stringify(state.mobile[s].cfgRect));
  }
  await cM.close();

  await browser.close();
  fs.writeFileSync(`${OUT}/state.json`, JSON.stringify(state, null, 2));
  console.log('OK -> ' + OUT);
  console.log('files: ' + fs.readdirSync(OUT).length);
})();
