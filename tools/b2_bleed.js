const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const ctx = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  await p.goto('http://sinofresh.local/quality/', { waitUntil: 'networkidle' });
  await p.evaluate(() => document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; }));
  await p.evaluate(async () => { await document.fonts.ready; });
  const r = await p.evaluate(() => {
    const px = (v) => Math.round(parseFloat(v) || 0);
    const info = (el) => {
      const cs = getComputedStyle(el);
      const b = el.getBoundingClientRect();
      return { ml: cs.marginLeft, mr: cs.marginRight, pl: cs.paddingLeft, pr: cs.paddingRight, w: px(b.width) };
    };
    const out = [];
    for (const el of document.querySelectorAll('.wp-block-columns')) {
      const kids = [...el.children].filter((k) => getComputedStyle(k).display !== 'none');
      if (kids.length && px(kids[0].getBoundingClientRect().width) >= 370) {
        const sec = el.closest('section');
        out.push({ cols: info(el), sec: sec ? info(sec) : null, head: sec && sec.querySelector('h2') ? sec.querySelector('h2').textContent.trim().slice(0, 26) : null });
      }
    }
    return out;
  });
  console.log(JSON.stringify(r, null, 1));
  await b.close();
})();
