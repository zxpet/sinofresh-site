const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const C = ['soft-chews', 'drops', 'dental-chews'];
  for (const n of C) {
    const c = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    const p = await c.newPage();
    await p.goto('http://sinofresh.local/products/' + n + '/', { waitUntil: 'networkidle' });
    await p.evaluate(() => document.fonts.ready);
    const r = await p.evaluate(() => {
      const px = (v) => Math.round(parseFloat(v) || 0);
      const A = 'section:has(> .wp-block-columns:not([class*="sf-"]) > .wp-block-column > .wp-block-group.has-top-border-color)';
      const B = 'section:has(> .wp-block-columns:not([class*="sf-"]) + .wp-block-columns):has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-card-white-background-color)';
      const box = (el) => { if (!el) return null; const cs = getComputedStyle(el); const b = el.getBoundingClientRect(); return { w: px(b.width), h: px(b.height), pad: cs.padding, mar: cs.margin, fs: cs.fontSize, minH: cs.minHeight, lh: cs.lineHeight, gc: cs.gridColumnEnd, disp: cs.display, tracks: cs.gridTemplateColumns }; };
      const out = {};
      const a = document.querySelector('body.page-child.parent-pageid-19 ' + A);
      if (a) {
        const col = a.querySelector(':scope > .wp-block-columns > .wp-block-column');
        const g = col.querySelector(':scope > .wp-block-group');
        out.A = { sec: box(a), col: box(col), group: box(g), kids: [...g.children].map(box), nCols: a.querySelectorAll(':scope > .wp-block-columns > .wp-block-column').length };
      }
      const bb = document.querySelector('body.page-child.parent-pageid-19 ' + B);
      if (bb) {
        const col = bb.querySelector(':scope > .wp-block-columns > .wp-block-column');
        const card = col.querySelector(':scope > .wp-block-group');
        const frame = card.querySelector(':scope > .wp-block-group');
        out.B = { sec: box(bb), col: box(col), card: box(card), frame: box(frame), img: box(card.querySelector('img')), h3: box(card.querySelector('h3')), ps: [...card.querySelectorAll(':scope > p')].map(box), nCols: bb.querySelectorAll(':scope > .wp-block-columns > .wp-block-column').length };
      }
      return out;
    });
    console.log('===== ' + n);
    if (r.A) {
      console.log(' A sec ' + r.A.sec.h + ' tracks=' + r.A.sec.tracks + ' n=' + r.A.nCols);
      console.log('   col ' + JSON.stringify(r.A.col) + '\n   grp ' + JSON.stringify(r.A.group));
      r.A.kids.forEach((k, i) => console.log('   kid' + i + ' ' + JSON.stringify(k)));
    }
    if (r.B) {
      console.log(' B sec ' + r.B.sec.h + ' n=' + r.B.nCols);
      console.log('   col ' + JSON.stringify(r.B.col));
      console.log('   card ' + JSON.stringify(r.B.card));
      console.log('   frame ' + JSON.stringify(r.B.frame) + ' img ' + JSON.stringify(r.B.img));
      console.log('   h3 ' + JSON.stringify(r.B.h3));
      r.B.ps.forEach((k, i) => console.log('   p' + i + ' ' + JSON.stringify(k)));
    }
    await c.close();
  }
  await b.close();
})();
