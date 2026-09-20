const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const PROBE = () => {
  const secs = [...document.querySelectorAll('.wp-site-blocks > *')];
  const sec = secs.find(s => { const h = s.querySelector('h2'); return h && /core values/i.test(h.textContent); });
  if (!sec) return { err: 'section not found' };
  const cols = sec.querySelector('.wp-block-columns');
  const csCols = getComputedStyle(cols);
  const colEls = [...cols.children];
  const cards = colEls.map(c => c.querySelector(':scope > .wp-block-group'));
  const rows = new Map();
  colEls.forEach((c, i) => { const t = Math.round(c.getBoundingClientRect().top); rows.set(t, (rows.get(t) || []).concat(i)); });
  const info = {
    sectionH: +sec.getBoundingClientRect().height.toFixed(1),
    cols: { display: csCols.display, flexWrap: csCols.flexWrap, alignItems: csCols.alignItems, gap: csCols.gap, gridCols: csCols.gridTemplateColumns, maxW: csCols.maxWidth, width: +cols.getBoundingClientRect().width.toFixed(1) },
    colCount: colEls.length,
    rowsAtTop: [...rows.entries()].map(([t, idx]) => t + ':' + idx.join(',')),
    cards: cards.map((card, i) => {
      const col = colEls[i], cs = getComputedStyle(card), ccs = getComputedStyle(col);
      const h3 = card.querySelector('h3'), p = card.querySelector('p');
      return {
        i, title: h3.textContent.trim(),
        colH: +col.getBoundingClientRect().height.toFixed(1), colW: +col.getBoundingClientRect().width.toFixed(1),
        colAlign: ccs.alignSelf + '/' + ccs.display + '/' + ccs.flexBasis,
        cardH: +card.getBoundingClientRect().height.toFixed(1), cardW: +card.getBoundingClientRect().width.toFixed(1),
        cardTop: +card.getBoundingClientRect().top.toFixed(1), cardBottom: +card.getBoundingClientRect().bottom.toFixed(1),
        cardStyleHeight: cs.height, cardAlignSelf: cs.alignSelf, cardDisplay: cs.display,
        padding: cs.paddingTop + ' ' + cs.paddingRight + ' ' + cs.paddingBottom + ' ' + cs.paddingLeft,
        bg: cs.backgroundColor, border: cs.borderTopWidth + ' ' + cs.borderTopColor,
        h3H: +h3.getBoundingClientRect().height.toFixed(1), pH: +p.getBoundingClientRect().height.toFixed(1),
        cardClass: (card.className || '').slice(0, 90)
      };
    }),
    docH: document.documentElement.scrollHeight
  };
  // which theme rules match the column / card?
  const tgt = { cols, col: colEls[0], card: cards[0] };
  const hits = [];
  for (const sheet of document.styleSheets) {
    const src = (sheet.href || 'inline').split('/').pop();
    const walk = (rules, media) => {
      for (const r of rules) {
        if (r.conditionText !== undefined) { walk(r.cssRules, r.conditionText); continue; }
        if (!r.selectorText) continue;
        for (const k of Object.keys(tgt)) {
          let m = false; try { m = tgt[k].matches(r.selectorText); } catch (e) { continue; }
          if (!m) continue;
          const t = (r.cssText || '');
          if (!/flex|display|height|align|grid|padding|gap/i.test(t)) continue;
          hits.push(k + ' | [' + (media || 'all') + '] ' + r.selectorText + ' :: ' + t.slice(t.indexOf('{') + 1, 160).replace(/\s+/g, ' ') + '  <' + src);
        }
      }
    };
    try { walk(sheet.cssRules, null); } catch (e) { }
  }
  info.rules = hits;
  return info;
};

(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  for (const w of [1440, 375]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    await page.goto('http://sinofresh.local/about/', { waitUntil: 'networkidle' });
    await page.evaluate(async () => { const s = Math.round(innerHeight * 0.8); for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } scrollTo(0, 0); });
    await page.waitForTimeout(1000);
    const r = await page.evaluate(PROBE);
    console.log('==================== ' + w + ' ====================');
    console.log('sectionH=' + r.sectionH + ' docH=' + r.docH + ' colCount=' + r.colCount + ' rows=' + JSON.stringify(r.rowsAtTop));
    console.log('cols: ' + JSON.stringify(r.cols));
    r.cards.forEach(c => console.log('  #' + c.i + ' ' + c.title + ' | colH=' + c.colH + ' colW=' + c.colW + ' (' + c.colAlign + ') | cardH=' + c.cardH + ' top=' + c.cardTop + ' bottom=' + c.cardBottom + ' | styleH=' + c.cardStyleHeight + ' alignSelf=' + c.cardAlignSelf + ' display=' + c.cardDisplay + ' | pad=' + c.padding + ' | h3=' + c.h3H + ' p=' + c.pH));
    console.log('  card class: ' + r.cards[0].cardClass);
    console.log('  --- 命中规则 ---');
    r.rules.forEach(x => console.log('   ' + x));
    await ctx.close();
  }
  await b.close();
})();
