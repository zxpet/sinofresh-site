/* Standard Formulas 卡片化 + CPT —— 运行时几何探针（只读，不改源码）
   回答四件事：
     1. TOC 契约：dosage 页 H2 顺序 / 注入的 #sf-sec-N / rail label（H2 文本依赖）
     2. sf-formulas 当前占用高度（折叠态 vs 逐个展开），以及它在页内的 top
     3. Related 区块 .sf-tile 的真实卡片高度（卡片化后的高度基准）
     4. 配方条目数 / label→value 兄弟结构（configurator.js readFormula 的契约）
   Usage: node tools/_sf_formula_probe.js [out.json]  -> 默认 /tmp/b1/cpt_scan/probe.json */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const OUT = process.argv[2] || '/tmp/b1/cpt_scan/probe.json';
const PAGES = ['soft-chews', 'tablets', 'liquids', 'fish-oil'];

async function accept(p) {
  const r = p.locator('button:has-text("Reject Non-Essential")');
  if (await r.count()) await r.first().click({ force: true }).catch(() => {});
}
async function settle(page) {
  await page.evaluate(async () => {
    const s = Math.round(innerHeight * 0.8);
    for (let y = 0; y < document.body.scrollHeight; y += s) {
      scrollTo(0, y); await new Promise((r) => setTimeout(r, 50));
    }
    scrollTo(0, 0); await new Promise((r) => setTimeout(r, 250));
  });
  await page.evaluate(() => Promise.all(Array.from(document.images)
    .filter((i) => !i.complete)
    .map((i) => new Promise((r) => { i.onload = i.onerror = r; }))));
}

const probe = () => {
  const R = (el) => { const r = el.getBoundingClientRect(); return { top: Math.round(r.top + scrollY), h: Math.round(r.height), w: Math.round(r.width) }; };
  const sec = document.querySelector('section.sf-formulas');
  const items = sec ? Array.from(sec.querySelectorAll('.sf-formula__item')) : [];

  /* 1. TOC 契约 */
  const toc = Array.from(document.querySelectorAll('.sf-toc a')).map((a) => ({
    href: a.getAttribute('href'),
    label: (a.textContent || '').replace(/\s+/g, ' ').trim(),
  }));
  const h2s = Array.from(document.querySelectorAll('h2')).map((h) => ({
    id: h.id || null, text: (h.textContent || '').replace(/\s+/g, ' ').trim(),
    cls: h.className,
  }));

  /* 2. formulas 区几何 + 逐条折叠态高度 */
  const itemInfo = items.map((d) => {
    const name = d.querySelector('.sf-formula__name');
    const use = d.querySelector('.sf-formula__use');
    const labels = Array.from(d.querySelectorAll('.sf-formula__label'));
    /* configurator.js readFormula 的契约：label 的 nextElementSibling 必须是值节点 */
    const sibOk = labels.every((l) => l.nextElementSibling && l.nextElementSibling.textContent.trim() !== '');
    return {
      name: name ? name.textContent.trim() : null,
      use: use ? use.textContent.trim() : null,
      open: d.hasAttribute('open'),
      h: Math.round(d.getBoundingClientRect().height),
      labels: labels.length,
      labelSiblingOk: sibOk,
      imgCount: d.querySelectorAll('img').length,
      cta: !!d.querySelector('.sf-formula__cta'),
      ctaData: d.querySelector('.sf-formula__cta') ? d.querySelector('.sf-formula__cta').getAttribute('data-formula') : null,
    };
  });

  /* 3. Related 卡片高度基准 */
  const tiles = Array.from(document.querySelectorAll('.sf-dosage-grid .sf-tile')).slice(0, 3)
    .map((t) => ({ h: Math.round(t.getBoundingClientRect().height), w: Math.round(t.getBoundingClientRect().width) }));
  const grid = document.querySelector('.sf-dosage-grid');
  const gridH = grid ? Math.round(grid.getBoundingClientRect().height) : null;
  const gridCols = grid ? getComputedStyle(grid).gridTemplateColumns : null;

  /* 4. 内容宽度与 ItemList */
  const ld = Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
    .map((s) => { try { return JSON.parse(s.textContent); } catch (e) { return null; } })
    .filter(Boolean).map((o) => o['@type']);
  const inner = document.querySelector('.wp-site-blocks > * .wp-block-group');

  return {
    secTop: sec ? R(sec).top : null,
    secH: sec ? R(sec).h : null,
    secW: sec ? R(sec).w : null,
    itemCount: itemInfo.length,
    items: itemInfo,
    collapsedSum: itemInfo.reduce((a, b) => a + b.h, 0),
    toc, h2s,
    relatedTiles: tiles, relatedGridH: gridH, relatedCols: gridCols,
    ldTypes: ld,
    contentW: inner ? Math.round(inner.getBoundingClientRect().width) : null,
    docH: Math.round(document.documentElement.scrollHeight),
  };
};

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const out = {};
  for (const [label, w, h] of [['1440', 1440, 1000], ['375', 375, 812]]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    for (const slug of PAGES) {
      await page.goto(`http://sinofresh.local/products/${slug}/`, { waitUntil: 'load' });
      await accept(page); await settle(page);
      const m = await page.evaluate(probe);
      out[`${slug}@${label}`] = m;
      console.log(`${slug}@${label}  ｜配方 ${m.itemCount} 条 / 折叠合计 ${m.collapsedSum}px ｜`
        + `区块 top=${m.secTop} h=${m.secH} w=${m.secW} ｜Related 卡片 h=${m.relatedTiles[0] ? m.relatedTiles[0].h : '—'} `
        + `(${m.relatedCols}) ｜TOC ${m.toc.length} 项 ｜ld=${m.ldTypes.join(',')} ｜docH=${m.docH}`);
    }
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
  console.log('\n→ ' + OUT);
})();
