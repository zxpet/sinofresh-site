/* Usage: node align_dosage_shots.js <tag> <slug> <Label> */
const { chromium } = require('playwright-core');
const path = require('path');
const tag = process.argv[2], slug = process.argv[3], label = process.argv[4];
const OUT = '/Users/meng/Workbuddy/sinofresh外贸网站建设/screenshots/align-' + slug;
require('fs').mkdirSync(OUT, { recursive: true });
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  await page.goto('http://sinofresh.local/products/' + slug + '/', { waitUntil: 'networkidle' });
  await page.evaluate(async () => { await document.fonts.ready; });
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(OUT, `${tag}-1440-full.png`), fullPage: true });
  const cta = await page.evaluate(() => {
    const el = document.querySelector('#inquiry-form') || [...document.querySelectorAll('section')].at(-1);
    const r = el.getBoundingClientRect();
    return { y: Math.round(r.y + window.scrollY) - 10, height: Math.min(Math.round(r.height) + 20, 1400) };
  });
  await page.screenshot({ path: path.join(OUT, `${tag}-1440-cta.png`), clip: { x: 0, y: cta.y, width: 1440, height: cta.height }, fullPage: true });
  await page.screenshot({ path: path.join(OUT, `${tag}-1440-hero.png`), clip: { x: 0, y: 0, width: 1440, height: 900 } });
  await ctx.close();
  const mctx = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true, deviceScaleFactor: 1 });
  const m = await mctx.newPage();
  await m.goto('http://sinofresh.local/products/' + slug + '/', { waitUntil: 'networkidle' });
  await m.evaluate(async () => { await document.fonts.ready; });
  const overflow = await m.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  const gform = await m.evaluate(() => !!document.querySelector('.gform_wrapper'));
  const raw = await m.evaluate(() => document.documentElement.innerHTML.includes('<!-- wp:columns'));
  console.log('375 overflowX:', overflow, '| gform:', gform, '| rawComments:', raw);
  await m.screenshot({ path: path.join(OUT, `${tag}-375-hero.png`) });
  await mctx.close();
  await b.close();
  console.log('done', tag, slug);
})();
