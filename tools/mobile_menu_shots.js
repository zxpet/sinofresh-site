/* Capture the overlay menu closed (submenu collapsed) and expanded. */
const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ headless: true, args: ['--disable-gpu','--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 375, height: 812 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  await p.goto('http://sinofresh.local/', { waitUntil: 'networkidle', timeout: 90000 });
  await p.waitForTimeout(600);
  await p.click('.wp-block-navigation__responsive-container-open');
  await p.waitForTimeout(600);
  const s1 = await p.evaluate(() => {
    const li = document.querySelector('.is-menu-open .has-child');
    const btn = li.querySelector(':scope > .wp-block-navigation__submenu-icon');
    const ul = li.querySelector(':scope > ul');
    const r = btn.getBoundingClientRect();
    return { aria: btn.getAttribute('aria-expanded'), btn: { w: +r.width.toFixed(0), h: +r.height.toFixed(0), x: +r.x.toFixed(0) },
             ulH: +ul.getBoundingClientRect().height.toFixed(0), ulVis: getComputedStyle(ul).visibility };
  });
  console.log('collapsed state', JSON.stringify(s1));
  await p.screenshot({ path: 'screenshots/mobile-after/375-09-menu-collapsed.png' });
  await p.click('.is-menu-open .has-child > .wp-block-navigation__submenu-icon');
  await p.waitForTimeout(500);
  const s2 = await p.evaluate(() => {
    const li = document.querySelector('.is-menu-open .has-child');
    const btn = li.querySelector(':scope > .wp-block-navigation__submenu-icon');
    const ul = li.querySelector(':scope > ul');
    const first = ul.querySelector('a');
    return { aria: btn.getAttribute('aria-expanded'), ulH: +ul.getBoundingClientRect().height.toFixed(0),
             firstLinkX: +first.getBoundingClientRect().x.toFixed(0) };
  });
  console.log('expanded state', JSON.stringify(s2));
  await p.screenshot({ path: 'screenshots/mobile-after/375-10-menu-expanded.png' });
  await b.close();
})();
