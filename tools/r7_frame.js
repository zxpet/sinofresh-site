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
    const chain = [];
    const walk = (el, depth) => {
      if (!el || depth > 5) return;
      const cs = getComputedStyle(el);
      chain.push({ d: depth, tag: el.tagName, inline: (el.getAttribute('style') || '').slice(0, 70),
        w: px(el.getBoundingClientRect().width), h: px(el.getBoundingClientRect().height),
        pad: cs.padding, mar: cs.margin, disp: cs.display, lh: cs.lineHeight, fs: cs.fontSize, va: cs.verticalAlign });
      [...el.children].forEach((k) => walk(k, depth + 1));
    };
    walk(frame, 0);
    return chain;
  });
  r.forEach((x) => console.log('  '.repeat(x.d) + `<${x.tag}> ${x.w}x${x.h} disp=${x.disp} pad=${x.pad} mar=${x.mar} lh=${x.lh} fs=${x.fs} va=${x.va} inline="${x.inline}"`));
  await c.close();
  await b.close();
})();
