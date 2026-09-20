/* Trace every hidden/class mutation on the flavor Custom wrap, with stacks. */
const { chromium } = require('playwright-core');

(async () => {
  const b = await chromium.launch();
  const p = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  await p.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'load' });
  await p.waitForTimeout(900);
  await p.evaluate(() => {
    window.__log = [];
    const g = document.querySelector('.configurator__group[data-group="flavor"]');
    const w = g.querySelector('.configurator__custom');
    const t0 = performance.now();
    new MutationObserver((muts) => {
      muts.forEach((m) => {
        if (m.attributeName === 'hidden' || m.attributeName === 'class') {
          window.__log.push({
            t: Math.round(performance.now() - t0),
            attr: m.attributeName,
            hidden: w.hidden,
            cls: w.className,
            stack: (new Error().stack || '').split('\n').slice(1, 4).join(' <- ').slice(0, 200)
          });
        }
      });
    }).observe(w, { attributes: true, attributeFilter: ['hidden', 'class'] });
  });

  const gFn = p.locator('.configurator__group[data-group="functions"]');
  await gFn.locator('.configurator__item[data-value="Custom"]').click();
  await p.waitForTimeout(300);
  const ta = gFn.locator('textarea.configurator__custom-input');
  await ta.click();
  await ta.type('Hip & joint');
  await ta.blur();
  await p.waitForTimeout(250);
  await p.evaluate(() => window.__log.push({ t: 'MARK', attr: 'flavor-click', hidden: null, cls: '' }));
  await p.locator('.configurator__group[data-group="flavor"] .configurator__item[data-value="Custom"]').click();
  await p.waitForTimeout(800);

  const log = await p.evaluate(() => window.__log);
  log.forEach((e) => {
    console.log(String(e.t).padStart(6) + ' ' + String(e.attr).padEnd(12) + ' hidden=' + e.hidden + ' cls=' + e.cls + (e.stack ? '  | ' + e.stack : ''));
  });
  await b.close();
})();
