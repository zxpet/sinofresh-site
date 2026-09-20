/* Batch-1 verification: dosage pages + configurator + hero rhythm.
 * node batch1_check.js before|after
 * Writes screenshots/batch1-verify-<label>.json and prints a table.
 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const LABEL = process.argv[2] || 'after';
const BASE = 'http://sinofresh.local';
const PAGES = [
  ['soft-chews', '/products/soft-chews/'], ['tablets', '/products/tablets/'],
  ['powders', '/products/powders/'], ['pastes', '/products/pastes/'],
  ['drops', '/products/drops/'], ['liquids', '/products/liquids/'],
  ['fish-oil', '/products/fish-oil/'], ['dental-chews', '/products/dental-chews/'],
];
const A = 'section:has(> .wp-block-columns:not([class*="sf-"]) > .wp-block-column > .wp-block-group.has-top-border-color)';
const B = 'section:has(> .wp-block-columns:not([class*="sf-"]) + .wp-block-columns):has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-card-white-background-color)';
const R8 = 'section:has(> .wp-block-group > .wp-block-columns + .wp-block-separator)';
const SCOPE = 'body.page-child.parent-pageid-19';
const CFG = { A, B, R8, SCOPE };

async function settle(page) {
  await page.evaluate(() => document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; i.decoding = 'sync'; }));
  await page.evaluate(async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; });
  await page.evaluate(async () => {
    await Promise.all([...document.querySelectorAll('img')].map((i) => (i.complete && i.naturalWidth) ? 0 : new Promise((r) => { i.addEventListener('load', r, { once: true }); i.addEventListener('error', r, { once: true }); setTimeout(r, 4000); })));
    window.scrollTo(0, document.body.scrollHeight);
  });
  await page.waitForTimeout(300);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(200);
}

const collect = (CFG) => {
  const px = (v) => Math.round(parseFloat(v) || 0);
  const box = (el) => {
    if (!el) return null;
    const b = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return { w: px(b.width), h: px(b.height), top: px(b.top + window.scrollY), disp: cs.display, tracks: cs.gridTemplateColumns, pad: px(cs.paddingTop) + '/' + px(cs.paddingBottom) };
  };
  const out = { docH: document.documentElement.scrollHeight, ovf: document.documentElement.scrollWidth - document.documentElement.clientWidth, W: document.documentElement.clientWidth };

  const a = [...document.querySelectorAll(CFG.SCOPE + ' ' + CFG.A)];
  const b = [...document.querySelectorAll(CFG.SCOPE + ' ' + CFG.B)];
  const r8 = [...document.querySelectorAll(CFG.SCOPE + ' ' + CFG.R8)];
  out.A = a.map((el) => {
    const cols = [...el.querySelectorAll(':scope > .wp-block-columns > .wp-block-column')];
    const tops = [...new Set(cols.map((c) => px(c.getBoundingClientRect().top)))];
    return { head: (el.querySelector('h2') || {}).textContent, sec: box(el), nCols: cols.length, rows: tops.length, colW: cols.length ? px(cols[0].getBoundingClientRect().width) : 0, colH: cols.map((c) => px(c.getBoundingClientRect().height)), rowTops: tops, groupDisp: cols[0] ? getComputedStyle(cols[0].parentElement).display : null, lastSpan: cols.length ? getComputedStyle(cols[cols.length - 1]).gridColumnEnd : null };
  });
  out.B = b.map((el) => {
    const cols = [...el.querySelectorAll(':scope > .wp-block-columns > .wp-block-column')];
    const tops = [...new Set(cols.map((c) => px(c.getBoundingClientRect().top)))];
    const card = el.querySelector('.wp-block-column > .wp-block-group.has-card-white-background-color');
    const img = el.querySelector('img');
    return { head: (el.querySelector('h2') || {}).textContent, sec: box(el), nCols: cols.length, rows: tops.length, colW: cols.length ? px(cols[0].getBoundingClientRect().width) : 0, colH: cols.map((c) => px(c.getBoundingClientRect().height)), rowTops: tops, cardPad: card ? getComputedStyle(card).padding : null, img: img ? box(img) : null, lastSpan: cols.length ? getComputedStyle(cols[cols.length - 1]).gridColumnEnd : null };
  });
  out.R8 = r8.map((el) => ({ head: (el.querySelector('h2') || {}).textContent, pad: box(el).pad, h: box(el).h }));
  out.hero = box(document.querySelector('.sf-hero-inner'));
  const cfg = document.querySelector('.configurator');
  if (cfg) {
    const s = document.querySelector('.configurator__summary');
    const col = document.querySelector('.configurator__summary-col');
    const bar = document.querySelector('.configurator__mobilebar');
    const r = document.querySelector('.configurator__reset');
    const cp = document.querySelector('.configurator__copy');
    const sub = document.querySelector('.configurator__submit:not(.configurator__submit--bar)');
    out.cfg = {
      colPos: col ? getComputedStyle(col).position : null, colBottom: col ? getComputedStyle(col).bottom : null,
      sumH: s ? px(s.getBoundingClientRect().height) : null, sumPos: s ? getComputedStyle(s).position : null,
      sumMaxH: s ? getComputedStyle(s).maxHeight : null, sumOverflow: s ? getComputedStyle(s).overflowY : null,
      bar: bar ? getComputedStyle(bar).display + '/' + px(bar.getBoundingClientRect().height) : 'absent',
      resetH: r ? px(r.getBoundingClientRect().height) : null, copyH: cp ? px(cp.getBoundingClientRect().height) : null,
      submitH: sub ? px(sub.getBoundingClientRect().height) : null,
      optsH: px(document.querySelector('.configurator__options').getBoundingClientRect().height),
    };
  } else out.cfg = null;
  return out;
};

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  const out = { label: LABEL, pages: {} };
  const rows = [];
  for (const [name, url] of PAGES) {
    const rec = { url, viewports: {} };
    for (const [w, h, tag] of [[375, 812, '375'], [420, 900, '420'], [768, 1024, '768']]) {
      const ctx = await browser.newContext({ viewport: { width: w, height: h }, isMobile: true, hasTouch: true });
      const page = await ctx.newPage();
      await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 60000 });
      await settle(page);
      rec.viewports[tag] = await page.evaluate(collect, CFG);
      await ctx.close();
    }
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 60000 });
    await settle(page);
    rec.viewports['1440'] = await page.evaluate(() => ({
      docH: document.documentElement.scrollHeight,
      sections: [...document.querySelectorAll('section')].map((el, i) => ({ i, cls: el.className.replace(/\s+/g, ' ').trim().slice(0, 50), h: Math.round(el.getBoundingClientRect().height), w: Math.round(el.getBoundingClientRect().width), top: Math.round(el.getBoundingClientRect().top + window.scrollY) })),
      cols: [...document.querySelectorAll('.wp-block-columns')].map((el, i) => ({ i, h: Math.round(el.getBoundingClientRect().height), w: Math.round(el.getBoundingClientRect().width), tracks: getComputedStyle(el).gridTemplateColumns })),
    }));
    await ctx.close();
    out.pages[name] = rec;
    const v = rec.viewports['375'];
    rows.push([name, v.docH, v.ovf,
      v.A.length ? v.A[0].cols + 'x' + v.A[0].rows + ' w=' + v.A[0].colW + ' sec=' + v.A[0].sec.h : '-',
      v.B.length ? v.B[0].cols + 'x' + v.B[0].rows + ' w=' + v.B[0].colW + ' sec=' + v.B[0].sec.h : '-',
      v.hero ? v.hero.pad : '-',
      v.cfg ? ('sum ' + v.cfg.sumH + ' ' + v.cfg.sumPos + ' col ' + v.cfg.colPos + ' bar ' + v.cfg.bar + ' R/C ' + v.cfg.resetH + '/' + v.cfg.copyH) : '-']);
  }
  await browser.close();
  fs.writeFileSync(path.resolve(__dirname, '..', 'screenshots', 'batch1-verify-' + LABEL + '.json'), JSON.stringify(out, null, 1));
  console.log('page         docH375 ovf | HowWeWork(7)              | Related(7)                 | hero    | configurator');
  for (const r of rows) console.log(String(r[0]).padEnd(13) + String(r[1]).padEnd(8) + String(r[2]).padEnd(4) + '| ' + String(r[3]).padEnd(26) + '| ' + String(r[4]).padEnd(27) + '| ' + String(r[5]).padEnd(8) + '| ' + r[6]);
})();
