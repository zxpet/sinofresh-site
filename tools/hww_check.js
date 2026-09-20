const { chromium } = require('playwright-core');
const PAGES = [['soft-chews','/products/soft-chews/'],['tablets','/products/tablets/'],['powders','/products/powders/'],['pastes','/products/pastes/']];
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const [n, u] of PAGES) {
    for (const vp of [375, 1440]) {
      const ctx = await b.newContext({ viewport: { width: vp, height: 900 }, isMobile: vp < 800, hasTouch: vp < 800 });
      const p = await ctx.newPage();
      await p.goto('http://sinofresh.local' + u, { waitUntil: 'networkidle' });
      await p.evaluate(() => document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; }));
      await p.evaluate(async () => { await document.fonts.ready; });
      const r = await p.evaluate(() => {
        const px = (v) => Math.round(parseFloat(v) || 0);
        const secs = [...document.querySelectorAll('section')].filter((s) => s.querySelector(':scope > .wp-block-columns > .wp-block-column > .wp-block-group.has-top-border-color'));
        return secs.map((sec) => {
          const disp = getComputedStyle(sec).display;
          const groups = [...sec.querySelectorAll(':scope > .wp-block-columns')];
          const cols = [...sec.querySelectorAll(':scope > .wp-block-columns > .wp-block-column')];
          const tops = [...new Set(cols.map((c) => Math.round(c.getBoundingClientRect().top + window.scrollY)))];
          const last = cols[cols.length - 1];
          const lastRect = last.getBoundingClientRect();
          const secRect = sec.getBoundingClientRect();
          return { disp, nGroups: groups.length, nCols: cols.length, rows: tops.length,
            colW: Math.round(cols[0].getBoundingClientRect().width),
            lastSpan: Math.round(lastRect.width), lastLeft: Math.round(lastRect.left - secRect.left),
            lastTop: Math.round(lastRect.top - secRect.top),
            secH: Math.round(secRect.height),
            gridDisp: getComputedStyle(last).display };
        });
      });
      console.log(`${n} @${vp}: ` + JSON.stringify(r));
      await ctx.close();
    }
  }
  await b.close();
})();
