/* Final verification pass: pages 200, no JS errors, logo geometry,
   social hrefs, triple band, mobile 420px, sticky header. */
const { chromium } = require('playwright-core');
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/round6';

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });

  const pages = ['/', '/products/soft-chews/', '/products/', '/about/', '/quality/', '/contact/', '/blog/'];
  for (const p of pages) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push('pageerror: ' + e.message));
    page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
    const resp = await page.goto('http://sinofresh.local' + p, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(700);
    const tokens = await page.evaluate(() => document.documentElement.innerHTML.includes('{{sf-social:'));
    console.log(p, resp.status(), 'tokens-left:', tokens, 'js-errors:', errors.length ? errors : 'none');
    await ctx.close();
  }

  // desktop visuals
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  await page.goto('http://sinofresh.local/', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(800);
  const geo = await page.evaluate(() => {
    const r = (el) => { if (!el) return null; const b = el.getBoundingClientRect(); return { w: Math.round(b.width), h: Math.round(b.height), x: Math.round(b.left) }; };
    const nav = document.querySelector('.sf-logo img');
    const hrefs = [...document.querySelectorAll('.sf-topbar-social a, .sf-footer .sf-social a, .sf-footer .sf-footcontact a')]
      .map(a => (a.getAttribute('aria-label') || a.textContent.trim().slice(0, 8)) + '=' + a.getAttribute('href') + ' rel=' + a.getAttribute('rel'));
    return { nav: r(nav), navNatural: nav ? nav.naturalWidth + 'x' + nav.naturalHeight : null, hrefs };
  });
  console.log(JSON.stringify(geo, null, 1));
  await page.screenshot({ path: OUT + '/final-header-desktop.png', clip: { x: 0, y: 0, width: 1440, height: 130 } });
  await page.locator('.sf-footer').scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);
  const fb = await page.locator('.sf-footer-grid').boundingBox();
  await page.screenshot({ path: OUT + '/final-footer-desktop.png', clip: { x: 0, y: fb.y, width: 1440, height: Math.min(fb.height, 600) } });
  // sticky state
  await page.evaluate(() => window.scrollTo(0, 900));
  await page.waitForTimeout(900);
  await page.screenshot({ path: OUT + '/final-header-sticky.png', clip: { x: 0, y: 0, width: 1440, height: 140 } });
  await ctx.close();

  // triple band desktop
  const ctx2 = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  const p2 = await ctx2.newPage();
  await p2.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'domcontentloaded' });
  await p2.waitForTimeout(700);
  await p2.locator('.sf-triple').scrollIntoViewIfNeeded();
  await p2.waitForTimeout(300);
  const tb = await p2.locator('.sf-triple').boundingBox();
  await p2.screenshot({ path: OUT + '/final-triple-desktop.png', clip: { x: tb.x, y: tb.y, width: tb.width, height: tb.height } });
  const colH = await p2.evaluate(() => [...document.querySelectorAll('.sf-triple > .wp-block-column')].map(c => Math.round(c.getBoundingClientRect().height)));
  console.log('triple col heights:', colH);
  await ctx2.close();

  // mobile 420
  const ctx3 = await browser.newContext({ viewport: { width: 420, height: 900 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const p3 = await ctx3.newPage();
  await p3.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'domcontentloaded' });
  await p3.waitForTimeout(700);
  const m = await p3.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    navLogo: (() => { const i = document.querySelector('.sf-logo img'); const b = i.getBoundingClientRect(); return Math.round(b.width) + 'x' + Math.round(b.height); })(),
    tripleCols: [...document.querySelectorAll('.sf-triple > .wp-block-column')].map(c => Math.round(c.getBoundingClientRect().height)),
  }));
  console.log('mobile 420:', JSON.stringify(m));
  await p3.screenshot({ path: OUT + '/final-mobile-420-header.png', clip: { x: 0, y: 0, width: 420, height: 120 } });
  await p3.locator('.sf-triple').scrollIntoViewIfNeeded();
  await p3.waitForTimeout(300);
  const mtb = await p3.locator('.sf-triple').boundingBox();
  await p3.screenshot({ path: OUT + '/final-mobile-420-triple.png', clip: { x: 0, y: mtb.y, width: 420, height: Math.min(mtb.height, 850) } });
  await p3.locator('.sf-footer').scrollIntoViewIfNeeded();
  await p3.waitForTimeout(300);
  const mfb = await p3.locator('.sf-footer-grid').boundingBox();
  await p3.screenshot({ path: OUT + '/final-mobile-420-footer.png', clip: { x: 0, y: mfb.y, width: 420, height: Math.min(mfb.height, 800) } });
  await ctx3.close();

  await browser.close();
  console.log('done');
})();
