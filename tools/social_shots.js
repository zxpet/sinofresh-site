/* Social round shots: WP admin Social Links (8 fields), desktop topbar/footer, mobile 375 topbar. */
const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/social-2700';
  require('fs').mkdirSync(OUT, { recursive: true });

  // 1. admin
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await ctx.newPage();
  await page.goto('http://sinofresh.local/wp-login.php', { waitUntil: 'networkidle' });
  await page.fill('#user_login', 'qa_temp');
  await page.fill('#user_pass', 'QaTemp!2026');
  await page.click('#wp-submit');
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(800);
  await page.goto('http://sinofresh.local/wp-admin/admin.php?page=social-links', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('input[id^="sf_social_"]', { timeout: 20000 });
  await page.waitForTimeout(500);
  const fields = await page.evaluate(() => [...document.querySelectorAll('input[id^="sf_social_"]')].map((i) => i.id));
  console.log('admin fields:', JSON.stringify(fields));
  await page.screenshot({ path: `${OUT}/admin-social-links.png`, fullPage: true });
  await ctx.close();

  // 2. desktop topbar + footer (fresh context, no admin bar)
  const d = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const dp = await d.newPage();
  await dp.goto('http://sinofresh.local/', { waitUntil: 'networkidle' });
  await dp.evaluate(async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; });
  await dp.waitForTimeout(300);
  await dp.screenshot({ path: `${OUT}/desktop-topbar.png`, clip: { x: 0, y: 0, width: 1440, height: 120 } });
  const foot = await dp.evaluate(() => {
    const s = document.querySelector('.sf-social');
    const r = s.getBoundingClientRect();
    return { y: Math.round(r.top + window.scrollY), h: Math.round(r.height) };
  });
  await dp.screenshot({ path: `${OUT}/desktop-footer.png`, fullPage: true, clip: { x: 0, y: Math.max(0, foot.y - 60), width: 1440, height: foot.h + 420 } });
  // footer icon geometry (gap / size)
  const geom = await dp.evaluate(() => {
    const anchors = [...document.querySelectorAll('.sf-social a')];
    const gaps = anchors.slice(1).map((a, i) => Math.round(a.getBoundingClientRect().left - anchors[i].getBoundingClientRect().right));
    const sz = anchors.map((a) => Math.round(a.querySelector('svg').getBoundingClientRect().width));
    return { n: anchors.length, gaps, sizes: [...new Set(sz)], hrefs: anchors.map((a) => a.getAttribute('href')) };
  });
  console.log('footer geom:', JSON.stringify(geom));
  const tgeom = await dp.evaluate(() => {
    const anchors = [...document.querySelectorAll('.sf-topbar-social a')];
    const gaps = anchors.slice(1).map((a, i) => Math.round(a.getBoundingClientRect().left - anchors[i].getBoundingClientRect().right));
    const sz = anchors.map((a) => Math.round(a.querySelector('svg').getBoundingClientRect().width));
    const email = document.querySelector('.sf-topbar__email');
    const svg = email.querySelector('svg').getBoundingClientRect();
    const txt = email.querySelector('a').getBoundingClientRect();
    return { n: anchors.length, gaps, sizes: [...new Set(sz)], svgH: Math.round(svg.height), txtH: Math.round(txt.height), svgTop: Math.round(svg.top), txtTop: Math.round(txt.top) };
  });
  console.log('topbar geom:', JSON.stringify(tgeom));
  await d.close();

  // 3. mobile 375 topbar + footer
  const m = await browser.newContext({ viewport: { width: 375, height: 812 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
  const mp = await m.newPage();
  await mp.goto('http://sinofresh.local/', { waitUntil: 'networkidle' });
  await mp.evaluate(async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; });
  await mp.waitForTimeout(300);
  await mp.screenshot({ path: `${OUT}/mobile-topbar-375.png`, clip: { x: 0, y: 0, width: 375, height: 160 } });
  const mfoot = await mp.evaluate(() => {
    const s = document.querySelector('.sf-social');
    s.scrollIntoView();
    const r = s.getBoundingClientRect();
    return { y: Math.round(r.top + window.scrollY), h: Math.round(r.height), w: Math.round(r.width), rows: new Set(anchorsY()).size };
    function anchorsY() { return [...document.querySelectorAll('.sf-social a')].map((a) => Math.round(a.getBoundingClientRect().top)); }
  });
  await mp.evaluate((y) => window.scrollTo(0, y - 220), mfoot.y);
  await mp.waitForTimeout(200);
  await mp.screenshot({ path: `${OUT}/mobile-footer-375.png`, fullPage: true, clip: { x: 0, y: Math.max(0, mfoot.y - 220), width: 375, height: 460 } });
  const mgeom = await mp.evaluate(() => {
    const s = document.querySelector('.sf-social');
    const r = s.getBoundingClientRect();
    const anchors = [...s.querySelectorAll('a')];
    const tops = new Set(anchors.map((a) => Math.round(a.getBoundingClientRect().top)));
    const sz = anchors.map((a) => Math.round(a.querySelector('svg').getBoundingClientRect().width));
    return { n: anchors.length, rows: tops.size, rowW: Math.round(r.width), overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth, sizes: [...new Set(sz)] };
  });
  console.log('mobile footer geom:', JSON.stringify(mgeom));
  await m.close();
  await browser.close();
})();
