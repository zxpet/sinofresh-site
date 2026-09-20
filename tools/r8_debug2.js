const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const c = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const p = await c.newPage();
  await p.goto('http://sinofresh.local/products/drops/', { waitUntil: 'networkidle' });
  const r = await p.evaluate(() => {
    const q = (s) => { try { return document.querySelectorAll(s).length; } catch (e) { return 'ERR ' + e.message; } };
    const out = {};
    const tests = [
      'section:has(> .wp-block-columns)',
      'section:has(.wp-block-columns)',
      'section:has(.wp-block-columns + .wp-block-columns)',
      'section:has(.wp-block-columns + .wp-block-columns + .wp-block-columns)',
      'section:has(> .wp-block-group > .wp-block-columns)',
      'section:has(> .wp-block-group > .wp-block-columns + .wp-block-columns)',
      'section:has(> .wp-block-group > .wp-block-columns + .wp-block-columns + .wp-block-columns)',
      'div.wp-block-group:has(> .wp-block-columns + .wp-block-columns + .wp-block-columns)',
      '.wp-block-columns + .wp-block-columns + .wp-block-columns',
      'body.page-child section:has(> .wp-block-group > .wp-block-columns + .wp-block-columns + .wp-block-columns)',
    ];
    for (const t of tests) out[t] = q(t);
    // who is the parent chain of the 3rd spec group?
    const gs = [...document.querySelectorAll('.wp-block-columns')];
    const spec = gs.find((g) => (g.textContent || '').includes('MOQ') && g.querySelectorAll(':scope > .wp-block-column > p').length === 2);
    out.specChain = [];
    let el = spec;
    for (let i = 0; i < 5 && el; i++) { out.specChain.push(el.tagName + '.' + el.className.replace(/wp-container-core-[\w-]*/g, 'wc').replace(/\s+/g, '.').slice(0, 70)); el = el.parentElement; }
    return out;
  });
  console.log(JSON.stringify(r, null, 1));
  await c.close();
  await b.close();
})();
