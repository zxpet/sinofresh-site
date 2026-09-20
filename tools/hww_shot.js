const { chromium } = require('playwright-core');
const path = require('path');
const OUT = path.resolve(__dirname, '..', 'screenshots', 'batch2');
require('fs').mkdirSync(OUT, { recursive: true });
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const [name, u] of [['soft-chews-hww','/products/soft-chews/'],['drops-hww','/products/drops/']]) {
    const ctx = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    const p = await ctx.newPage();
    await p.goto('http://sinofresh.local' + u, { waitUntil: 'networkidle' });
    await p.evaluate(() => document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; }));
    await p.evaluate(async () => { await document.fonts.ready; });
    await p.evaluate(() => {
      const sec = [...document.querySelectorAll('section')].find((s) => s.querySelector(':scope > .wp-block-columns > .wp-block-column > .wp-block-group.has-top-border-color'));
      if (sec) sec.scrollIntoView({ block: 'start' });
    });
    await p.waitForTimeout(300);
    await p.screenshot({ path: path.join(OUT, name + '-375.png'), fullPage: false });
    const docH = await p.evaluate(() => document.documentElement.scrollHeight);
    console.log(name, 'docH@375 =', docH);
    await ctx.close();
  }
  await b.close();
})();
