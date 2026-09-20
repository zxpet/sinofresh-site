/* Batch-1 visual evidence. node batch1_shots.js
   Writes screenshots/batch1/ */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const OUT = path.resolve(__dirname, '..', 'screenshots', 'batch1');
fs.mkdirSync(OUT, { recursive: true });

async function settle(page) {
  await page.evaluate(() => document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; i.decoding = 'sync'; }));
  await page.evaluate(async () => { await document.fonts.ready; });
  await page.evaluate(async () => {
    await Promise.all([...document.querySelectorAll('img')].map((i) => (i.complete && i.naturalWidth) ? 0 : new Promise((r) => { i.addEventListener('load', r, { once: true }); i.addEventListener('error', r, { once: true }); setTimeout(r, 4000); })));
    await new Promise((r) => setTimeout(r, 200));
  });
}

async function shot(browser, url, w, h, file, opts = {}) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, isMobile: w <= 768, hasTouch: w <= 768, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  await page.goto('http://sinofresh.local' + url, { waitUntil: 'networkidle' });
  await settle(page);
  if (opts.scrollTo) {
    await page.evaluate(async (sel) => { const el = document.querySelector(sel); if (el) el.scrollIntoView({ block: 'start' }); await new Promise((r) => setTimeout(r, 250)); }, opts.scrollTo);
  }
  if (opts.scrollBy) {
    await page.evaluate(async (n) => { window.scrollBy(0, n); await new Promise((r) => setTimeout(r, 250)); }, opts.scrollBy);
  }
  if (opts.clipSel) {
    const box = await page.evaluate((sel) => { const el = document.querySelector(sel); if (!el) return null; const b = el.getBoundingClientRect(); return { x: Math.round(b.x), y: Math.round(b.y + window.scrollY), width: Math.round(b.width), height: Math.round(b.height) }; }, opts.clipSel);
    if (box) await page.screenshot({ path: path.join(OUT, file), clip: box, fullPage: true });
    else console.log('missing', opts.clipSel);
  } else {
    await page.screenshot({ path: path.join(OUT, file), fullPage: !!opts.full });
  }
  await ctx.close();
}

const A = 'section:has(> .wp-block-columns:not([class*="sf-"]) > .wp-block-column > .wp-block-group.has-top-border-color)';
const B = 'section:has(> .wp-block-columns:not([class*="sf-"]) + .wp-block-columns):has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-card-white-background-color)';
const R8 = 'section:has(> .wp-block-group > .wp-block-columns + .wp-block-separator)';

(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  // variant page: how-we-work + related + specs band, at three widths
  for (const [w, h, tag] of [[375, 812, '375'], [768, 1024, '768']]) {
    await shot(b, '/products/drops/', w, h, `drops-hww-${tag}.png`, { clipSel: A });
    await shot(b, '/products/drops/', w, h, `drops-related-${tag}.png`, { clipSel: B });
    await shot(b, '/products/drops/', w, h, `drops-specs-${tag}.png`, { clipSel: R8 });
  }
  await shot(b, '/products/drops/', 375, 812, 'drops-hero-375.png', { clipSel: '.sf-hero-inner' });
  await shot(b, '/products/drops/', 1440, 900, 'drops-1440.png', { full: true });
  // configurator: viewport shot mid-options so the pinned summary is visible
  await shot(b, '/products/soft-chews/', 375, 812, 'cfg-mid-375.png', { scrollTo: '.configurator__group:nth-child(4)' });
  await shot(b, '/products/soft-chews/', 375, 812, 'cfg-start-375.png', { scrollTo: '.configurator' });
  await shot(b, '/products/soft-chews/', 375, 812, 'cfg-end-375.png', { clipSel: '.configurator' });
  await shot(b, '/products/soft-chews/', 768, 1024, 'cfg-768.png', { scrollTo: '.configurator__group:nth-child(4)' });
  await shot(b, '/products/soft-chews/', 1440, 900, 'cfg-1440.png', { clipSel: '.configurator' });
  // control pages that must not change
  await shot(b, '/', 375, 812, 'home-375.png', { full: true });
  await shot(b, '/quality/', 375, 812, 'quality-hero-375.png', { clipSel: '.sf-hero-inner' });
  await shot(b, '/quality/', 1440, 900, 'quality-1440.png', { full: true });
  await b.close();
  console.log(fs.readdirSync(OUT).sort().join('\n'));
})();
