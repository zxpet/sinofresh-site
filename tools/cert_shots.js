const { chromium } = require('playwright-core');
const path = require('path');
const tag = process.argv[2];
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/cert-marquee';
require('fs').mkdirSync(OUT, { recursive: true });
async function preroll(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    const h = document.documentElement.scrollHeight;
    for (let y = 0; y < h; y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); }
    window.scrollTo(0, 0);
    await Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; })));
  });
  await page.waitForTimeout(400);
}
async function shotSection(page, url, file) {
  await page.goto(url, { waitUntil: 'networkidle' });
  await preroll(page);
  const r = await page.evaluate(() => {
    const el = document.querySelector('img[src*="cert-fda"]').closest('section');
    const rect = el.getBoundingClientRect();
    return { y: Math.round(rect.y + window.scrollY), h: Math.min(Math.round(rect.height) + 20, 1600) };
  });
  await page.screenshot({ path: path.join(OUT, file), clip: { x: 0, y: r.y, width: 1440, height: r.h }, fullPage: true });
  console.log(file, 'y=' + r.y, 'h=' + r.h);
}
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await shotSection(page, 'http://sinofresh.local/', tag + '-home-1440-certs.png');
  await shotSection(page, 'http://sinofresh.local/quality/', tag + '-quality-1440-certs.png');
  await ctx.close();
  const mctx = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const m = await mctx.newPage();
  for (const [slug, url] of [['home','http://sinofresh.local/'],['quality','http://sinofresh.local/quality/']]) {
    await m.goto(url, { waitUntil: 'networkidle' });
    await preroll(m);
    const r = await m.evaluate(() => {
      const el = document.querySelector('img[src*="cert-fda"]').closest('section');
      const rect = el.getBoundingClientRect();
      return { y: Math.round(rect.y + window.scrollY), h: Math.min(Math.round(rect.height) + 20, 1400) };
    });
    await m.screenshot({ path: path.join(OUT, tag + '-' + slug + '-375-certs.png'), clip: { x: 0, y: r.y, width: 375, height: r.h }, fullPage: true });
    console.log(slug, '375 y=' + r.y, 'h=' + r.h);
  }
  await mctx.close(); await b.close();
  console.log('done', tag);
})();
