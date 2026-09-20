const { chromium } = require('playwright-core');
const PAGES = [
  ['soft-chews', '/products/soft-chews/'], ['tablets', '/products/tablets/'], ['powders', '/products/powders/'],
  ['pastes', '/products/pastes/'], ['drops', '/products/drops/'], ['liquids', '/products/liquids/'],
  ['fish-oil', '/products/fish-oil/'], ['dental-chews', '/products/dental-chews/'],
];
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const [n, u] of PAGES) {
    const c = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    const p = await c.newPage();
    await p.goto('http://sinofresh.local' + u, { waitUntil: 'networkidle' });
    await p.evaluate(() => document.fonts.ready);
    const r = await p.evaluate(() => {
      const px = (v) => Math.round(parseFloat(v) || 0);
      const box = (el) => {
        if (!el) return null;
        const cs = getComputedStyle(el);
        const b = el.getBoundingClientRect();
        return {
          tag: el.tagName.toLowerCase(),
          cls: el.className.toString().replace(/wp-container-core-[\w-]*/g, '').replace(/\s+/g, ' ').trim().slice(0, 46),
          w: px(b.width), h: px(b.height),
          pad: px(cs.paddingTop) + '/' + px(cs.paddingRight) + '/' + px(cs.paddingBottom) + '/' + px(cs.paddingLeft),
          mar: px(cs.marginTop) + '/' + px(cs.marginBottom),
          disp: cs.display, gap: cs.gap, fs: cs.fontSize, lh: cs.lineHeight,
          rad: cs.borderRadius, bg: cs.backgroundColor,
        };
      };
      // first related card on a variant page
      const rel = [...document.querySelectorAll('section')].find((s) =>
        /Related Dosage Forms/.test(s.textContent) && s.querySelectorAll(':scope > .wp-block-columns').length === 2);
      const out = { body: [...document.body.classList].join(' ') };
      if (rel) {
        const col = rel.querySelector(':scope > .wp-block-columns > .wp-block-column');
        out.relSection = box(rel);
        out.relGroup = box(rel.querySelector(':scope > .wp-block-columns'));
        out.relCol = box(col);
        out.relCard = box(col.firstElementChild);
        out.cardKids = [...col.firstElementChild.children].map(box);
        const imgWrap = col.querySelector('.wp-block-group');
        out.imgWrap = box(imgWrap);
        out.imgWrapKids = [...imgWrap.children].map(box);
        out.figure = box(col.querySelector('figure'));
        out.img = box(col.querySelector('img'));
        out.h3 = box(col.querySelector('h3'));
        out.ps = [...col.querySelectorAll('p')].map(box);
      }
      const st = [...document.querySelectorAll('section')].find((s) =>
        /How We Work/.test(s.textContent) && s.querySelectorAll(':scope > .wp-block-columns').length === 2);
      if (st) {
        const col = st.querySelector(':scope > .wp-block-columns > .wp-block-column');
        out.stepSection = box(st);
        out.stepCol = box(col);
        out.stepInner = box(col.firstElementChild);
        out.stepKids = [...col.firstElementChild.children].map(box);
      }
      return out;
    });
    if (n === 'drops') console.log(JSON.stringify(r, null, 1));
    else console.log(n + ' body="' + r.body + '" relCard=' + (r.relCard ? r.relCard.h : '-') + ' stepCol=' + (r.stepCol ? r.stepCol.h : '-'));
    await c.close();
  }
  await b.close();
})();
