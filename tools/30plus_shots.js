console.log('launching...');
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');
const tag = process.argv[2]; // e.g. before / after
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/30plus';
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
async function shot(page, url, sel, file, vw, extra) {
  console.log('shot:', file);
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.evaluate(() => localStorage.setItem('sf_cookie_consent', JSON.stringify({necessary:true,marketing:false})));
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 30000 });
  await preroll(page);
  const found = await page.evaluate(({ sel, extra }) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const sec = el.closest('section') || el;
    const rect = sec.getBoundingClientRect();
    return { y: Math.round(rect.y + window.scrollY), h: Math.min(Math.round(rect.height) + (extra || 20), 2800),
             ov: document.documentElement.scrollWidth - document.documentElement.clientWidth };
  }, { sel, extra });
  if (!found) { console.log(file, 'SELECTOR NOT FOUND'); return; }
  await page.screenshot({ path: path.join(OUT, file), clip: { x: 0, y: found.y, width: vw, height: found.h }, fullPage: true });
  console.log(file, 'y=' + found.y, 'h=' + found.h, 'overflowX=' + found.ov);
}
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const d = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const dp = await d.newPage();
  // 改后：hero + 快照条一起截（含轮播底部）；改前：同一区域（无快照条）
  await shot(dp, 'http://sinofresh.local/', '.sf-hero-slider', tag + '-home-1440-hero-zone.png', 1440, 620);
  await shot(dp, 'http://sinofresh.local/', '.sf-stats', tag + '-home-1440-glance.png', 1440, 40);
  await d.close();
  const m = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const mp = await m.newPage();
  await shot(mp, 'http://sinofresh.local/', '.sf-hero-slider', tag + '-home-375-hero-zone.png', 375, 700);
  await m.close();
  await b.close();
  console.log('done', tag);
})();
