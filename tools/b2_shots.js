/* Batch-2 visual evidence: key sections at 375 + 768, plus form shots. */
const { chromium } = require('playwright-core');
const path = require('path');
const OUT = path.resolve(__dirname, '..', 'screenshots', 'batch2');
require('fs').mkdirSync(OUT, { recursive: true });

const JOBS = [
  // [file, url, width, anchorSelector]
  ['quality-certs-375.png', '/quality/', 375, 'h2'], // placeholder, real anchor below
];

const SHOTS = [
  ['about-values-375', '/about/', 375, '.wp-block-columns:has(> .wp-block-column > .wp-block-group.has-border-light-border-color):not(:has(figure))'],
  ['about-team-375', '/about/', 375, '.wp-block-columns:has(> .wp-block-column:nth-child(3) > .wp-block-group.has-bg-light-background-color.is-content-justification-center)'],
  ['about-factory-375', '/about/', 375, 'section:has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-border-light-border-color):has(figure)'],
  ['quality-certs-375', '/quality/', 375, 'section.has-bg-light-background-color:has(> .wp-block-columns > .wp-block-column:nth-child(4) > .wp-block-group.has-card-white-background-color)'],
  ['quality-lab-375', '/quality/', 375, '.wp-block-columns:has(> .wp-block-column:nth-child(3) > .wp-block-group.has-bg-light-background-color.is-content-justification-center)'],
  ['quality-qc-375', '/quality/', 375, 'section:has(> .wp-block-columns + .wp-block-columns):has(> .wp-block-columns > .wp-block-column > p.has-accent-color)'],
  ['quality-trace-375', '/quality/', 375, '.wp-block-columns:has(> .wp-block-column > .wp-block-group.has-bg-light-background-color.is-layout-constrained)'],
  ['services-hww-375', '/services/', 375, 'section:has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-top-border-color)'],
  ['factory-form-375', '/factory-tour/', 375, '.gform_wrapper'],
  ['contact-form-375', '/contact/', 375, '.gform_wrapper'],
  ['quality-hww-768', '/quality/', 768, 'section:has(> .wp-block-columns + .wp-block-columns):has(> .wp-block-columns > .wp-block-column > p.has-accent-color)'],
  ['about-team-768', '/about/', 768, '.wp-block-columns:has(> .wp-block-column:nth-child(3) > .wp-block-group.has-bg-light-background-color.is-content-justification-center)'],
];

(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const [name, url, w, sel] of SHOTS) {
    const ctx = await b.newContext({ viewport: { width: w, height: 812 }, isMobile: w <= 768, hasTouch: w <= 768 });
    const p = await ctx.newPage();
    await p.goto('http://sinofresh.local' + url, { waitUntil: 'networkidle', timeout: 60000 });
    await p.evaluate(() => document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; }));
    await p.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.querySelectorAll('img')].map((i) => (i.complete && i.naturalWidth) ? 0 : new Promise((r) => { i.addEventListener('load', r, { once: true }); setTimeout(r, 4000); }))); });
    const ok = await p.evaluate((s) => {
      const el = document.querySelector(s);
      if (!el) return false;
      el.scrollIntoView({ block: 'start' });
      return true;
    }, sel);
    await p.waitForTimeout(350);
    await p.screenshot({ path: path.join(OUT, name + '.png') });
    console.log((ok ? 'shot ' : 'MISS ') + name);
    await ctx.close();
  }
  await b.close();
})();
