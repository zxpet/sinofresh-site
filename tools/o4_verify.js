/**
 * o4_verify.js — OEM/ODM 四卡版核验（1440 / 1024 / 375）
 * 度量：板块高度、卡宽、卡等高、h3 行数、描述行数、明细条数、横向溢出
 */
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const TARGETS = [
  { slug: 'home', url: '/', h2: 'OEM & ODM Services' },
  { slug: 'services', url: '/services/', h2: 'OEM or ODM \u2014 Choose Your Path' },
];

function probe(h2text) {
  const px = (v) => Math.round(parseFloat(v) || 0);
  const sec = [...document.querySelectorAll('.wp-site-blocks > .wp-block-group')]
    .find((s) => s.querySelector('h2') && s.querySelector('h2').textContent.trim() === h2text);
  if (!sec) return { error: 'section not found' };
  const sr = sec.getBoundingClientRect();
  const cols = [...sec.querySelectorAll('.wp-block-columns')][0];
  const colEls = [...cols.querySelectorAll(':scope > .wp-block-column')];
  const lines = (el) => {
    if (!el) return null;
    const r = document.createRange();
    r.selectNodeContents(el);
    const tops = new Set([...r.getClientRects()].filter((x) => x.width > 0).map((x) => Math.round(x.top)));
    return tops.size;
  };
  const cards = colEls.map((c) => {
    const g = c.querySelector(':scope > .wp-block-group');
    const gr = g.getBoundingClientRect();
    const cr = c.getBoundingClientRect();
    const h3 = g.querySelector('h3'), p = g.querySelector('p:not([style*="14px"])') || g.querySelector('p');
    const bullets = [...g.querySelectorAll('p')].filter((x) => x.textContent.trim().startsWith('\u2713'));
    return {
      title: h3 ? h3.textContent.trim() : null,
      colW: Math.round(cr.width), colH: Math.round(cr.height),
      cardW: Math.round(gr.width), cardH: Math.round(gr.height),
      innerW: Math.round(gr.width) - px(getComputedStyle(g).paddingLeft) - px(getComputedStyle(g).paddingRight),
      h3Lines: lines(h3), descLines: lines(p), bullets: bullets.length,
      pad: px(getComputedStyle(g).paddingLeft),
      bottom: Math.round(gr.bottom), top: Math.round(gr.top),
      scrollOverflow: g.scrollWidth > Math.ceil(gr.width) + 1,
    };
  });
  const rowH = cards.length ? Math.max(...cards.map((c) => c.cardH)) - Math.min(...cards.map((c) => c.cardH)) : 0;
  const doc = document.documentElement;
  return {
    url: location.pathname, vw: window.innerWidth,
    secTop: Math.round(sr.top + window.scrollY), secH: Math.round(sr.height),
    colsPerRow: colEls.length,
    sameRowTops: [...new Set(colEls.map((c) => Math.round(c.getBoundingClientRect().top)))].length,
    rowDelta: rowH, cards,
    docW: doc.scrollWidth, docH: doc.scrollHeight,
    hOverflow: doc.scrollWidth > window.innerWidth,
  };
}

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  for (const w of [1440, 1024, 375]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 1 });
    const p = await ctx.newPage();
    for (const t of TARGETS) {
      await p.goto('http://sinofresh.local' + t.url, { waitUntil: 'networkidle', timeout: 45000 });
      await p.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
      const r = await p.evaluate(probe, t.h2);
      console.log('===== ' + w + ' ' + t.slug + ' =====');
      if (r.error) { console.log('  ' + r.error); continue; }
      console.log(`  板块 top=${r.secTop} h=${r.secH} | 列数=${r.colsPerRow} 不同行数=${r.sameRowTops} | docH=${r.docH} docW=${r.docW} vw=${r.vw} 横向溢出=${r.hOverflow}`);
      r.cards.forEach((c) => {
        console.log(`   - 「${c.title}」 列${c.colW}x${c.colH} 卡${c.cardW}x${c.cardH} 内宽${c.innerW} pad${c.pad} H3行=${c.h3Lines} 描述行=${c.descLines} 明细=${c.bullets} 底=${c.bottom}${c.scrollOverflow ? '  <<内容溢出>>' : ''}`);
      });
      console.log(`  卡高差=${r.rowDelta}`);
    }
    await ctx.close();
  }
  await b.close();
})().catch((e) => { console.error(e); process.exit(1); });
