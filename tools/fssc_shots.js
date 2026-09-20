console.log('launching...');
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');
const tag = process.argv[2];
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/cert-grid';
fs.mkdirSync(OUT, { recursive: true });
async function preroll(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    const h = document.documentElement.scrollHeight;
    for (let y = 0; y < h; y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 50)); }
    window.scrollTo(0, 0);
    await Promise.race([
      Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; }))),
      new Promise(r => setTimeout(r, 4000))
    ]);
  });
  await page.waitForTimeout(400);
}
async function shot(page, url, sel, file, vw) {
  console.log('shot:', file);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.evaluate(() => localStorage.setItem('sf_cookie_consent', JSON.stringify({necessary:true,marketing:false})));
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 30000 });
  await preroll(page);
  const r = await page.evaluate((sel) => {
    const el = document.querySelector(sel).closest('section');
    const rect = el.getBoundingClientRect();
    return { y: Math.round(rect.y + window.scrollY), h: Math.min(Math.round(rect.height) + 20, 2800),
             ov: document.documentElement.scrollWidth - document.documentElement.clientWidth };
  }, sel);
  await page.screenshot({ path: path.join(OUT, file), clip: { x: 0, y: r.y, width: vw, height: r.h }, fullPage: true });
  console.log(file, 'y=' + r.y, 'h=' + r.h, 'overflowX=' + r.ov);
}
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const d = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const dp = await d.newPage();
  await shot(dp, 'http://sinofresh.local/', '.sf-certgrid, .sf-cert-marquee', tag + '-home-1440-certgrid.png', 1440);
  await shot(dp, 'http://sinofresh.local/quality/', '.sf-certdetail, .sf-cert-marquee', tag + '-quality-1440-certrows.png', 1440);
  await shot(dp, 'http://sinofresh.local/products/drops/', '.sf-hero-inner', tag + '-drops-1440-hero.png', 1440);
  await d.close();
  const m = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const mp = await m.newPage();
  await shot(mp, 'http://sinofresh.local/', '.sf-certgrid, .sf-cert-marquee', tag + '-home-375-certgrid.png', 375);
  await shot(mp, 'http://sinofresh.local/quality/', '.sf-certdetail, .sf-cert-marquee', tag + '-quality-375-certrows.png', 375);
  await m.close();
  await b.close();
  console.log('done', tag);
})();
