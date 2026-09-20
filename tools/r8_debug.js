const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const c = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const p = await c.newPage();
  await p.goto('http://sinofresh.local/products/drops/', { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready);
  const r = await p.evaluate(() => {
    const px = (v) => Math.round(parseFloat(v) || 0);
    const out = {};
    const sels = {
      'three+adjacent': 'body.page-child.parent-pageid-19 section:has(> .wp-block-columns + .wp-block-columns + .wp-block-columns)',
      'two+adjacent': 'body.page-child.parent-pageid-19 section:has(> .wp-block-columns + .wp-block-columns)',
      'anyColumnsChild': 'body.page-child.parent-pageid-19 section:has(> .wp-block-columns)',
      'global_three': 'section:has(> .wp-block-columns + .wp-block-columns + .wp-block-columns)',
    };
    for (const k of Object.keys(sels)) out[k] = document.querySelectorAll(sels[k]).length;
    const f = document.querySelector('.configurator') ? document.querySelector('.configurator').previousElementSibling : null;
    // describe every direct child group-count of each section
    out.sections = [...document.querySelectorAll('section')].map((s, i) => {
      const kids = [...s.children];
      let runs = 0, best = 0;
      for (const k of kids) { if (k.classList.contains('wp-block-columns')) { runs++; best = Math.max(best, runs); } else runs = 0; }
      return {
        i,
        tag: s.tagName,
        maxAdjacentGroups: best,
        totalGroups: s.querySelectorAll(':scope > .wp-block-columns').length,
        pt: px(getComputedStyle(s).paddingTop), pb: px(getComputedStyle(s).paddingBottom),
        h: px(s.getBoundingClientRect().height),
        cls: s.className.replace(/wp-container-core-[\w-]*/g, '').replace(/is-layout-[\w-]*/g, '').replace(/\s+/g, ' ').trim().slice(0, 46),
      };
    });
    return out;
  });
  console.log(JSON.stringify(r, null, 1));
  await c.close();
  await b.close();
})();
