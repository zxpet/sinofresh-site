const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const ctx = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  await p.goto('http://sinofresh.local/about/', { waitUntil: 'networkidle' });
  await p.evaluate(() => document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; }));
  await p.evaluate(async () => { await document.fonts.ready; });
  const r = await p.evaluate(() => {
    const px = (v) => Math.round(parseFloat(v) || 0);
    const sec = document.querySelector('section:has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-border-light-border-color):has(figure)');
    if (!sec) return 'SECTION NOT MATCHED';
    const card = sec.querySelector('.wp-block-column > .wp-block-group');
    const img = sec.querySelector('img');
    const cs = getComputedStyle(card);
    const ci = getComputedStyle(img);
    return {
      secMatched: true,
      secDisplay: getComputedStyle(sec).display,
      cardRect: { w: px(card.getBoundingClientRect().width), h: px(card.getBoundingClientRect().height) },
      cardMinH: cs.minHeight, cardPad: cs.padding, cardDisp: cs.display,
      imgRect: { w: px(img.getBoundingClientRect().width), h: px(img.getBoundingClientRect().height) },
      imgCSS: { w: ci.width, h: ci.height, ar: ci.aspectRatio, fit: ci.objectFit },
      imgAttr: { w: img.getAttribute('width'), h: img.getAttribute('height'), style: img.getAttribute('style') },
      imgParentChain: (() => { let e = img, a = []; while (e && e !== card) { a.unshift(e.tagName + '.' + (e.className || '').split(' ')[0]); e = e.parentElement; } return a.join('>'); })(),
    };
  });
  console.log(JSON.stringify(r, null, 1));
  await b.close();
})();
