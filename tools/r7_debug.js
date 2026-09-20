const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const c = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const p = await c.newPage();
  await p.goto('http://sinofresh.local/products/drops/', { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready);
  const r = await p.evaluate(() => {
    const px = (v) => Math.round(parseFloat(v) || 0);
    const B = 'section:has(> .wp-block-columns:not([class*="sf-"]) + .wp-block-columns):has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-card-white-background-color)';
    const sec = document.querySelector('body.page-child.parent-pageid-19 ' + B);
    const col = sec.querySelector(':scope > .wp-block-columns > .wp-block-column');
    const card = col.querySelector(':scope > .wp-block-group');
    const frame = card.querySelector(':scope > .wp-block-group');
    const img = card.querySelector('img');
    const h3 = card.querySelector('h3');
    const ps = [...card.querySelectorAll(':scope > p')];
    const d = (el, name) => {
      const cs = getComputedStyle(el);
      return { name, tag: el.tagName, inline: el.getAttribute('style'), cls: el.className.replace(/wp-container-core-[\w-]*/g, '').replace(/\s+/g, ' ').trim().slice(0, 70),
        w: px(el.getBoundingClientRect().width), h: px(el.getBoundingClientRect().height),
        pad: cs.padding, mar: cs.margin, fs: cs.fontSize, minH: cs.minHeight, ar: cs.aspectRatio, of: cs.objectFit, gc: cs.gridColumnEnd, disp: cs.display };
    };
    return {
      card: d(card, 'card'), frame: d(frame, 'frame'), img: d(img, 'img'), h3: d(h3, 'h3'),
      p0: ps[0] ? d(ps[0], 'p0') : null, plast: ps[ps.length - 1] ? d(ps[ps.length - 1], 'plast') : null,
      noHits: document.querySelectorAll('body.page-child.parent-pageid-19 section:has(> .wp-block-columns:not([class*="sf-"]) + .wp-block-columns):has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-card-white-background-color) .wp-block-group.has-card-white-background-color').length,
    };
  });
  console.log(JSON.stringify(r, null, 1));
  await c.close();
  await b.close();
})();
