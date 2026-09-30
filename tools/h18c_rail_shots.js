/*
 * H18c — visual evidence for the rail-capacity scan. READ ONLY.
 *
 * Crops the gallery (rail + main photo + switch) at 1440 / 1240 / 1200 / 375,
 * with the rail's tile count pushed to 7 by cloning nodes in the browser's own
 * DOM. The clones are labelled SIMULATED in the filename and in the report:
 * the site itself shows four tiles today, and nothing here touches the DB.
 *
 * Run:
 *   NODE_PATH=/Users/meng/.workbuddy/binaries/node/workspace/node_modules \
 *   /Users/meng/.workbuddy/binaries/node/versions/22.22.2-3/bin/node \
 *     tools/h18c_rail_shots.js
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const DEV = 'https://dev.zxpet.com';
const SLUG = 'joint-support-soft-chews';
const OUT = path.join(__dirname, '..', 'docs', 'h18c-shots');
const SEL = '.sf-fdetail2__media .sf-gallery__inner';

/* push the rail to n tiles by cloning the ones already there */
const growTo = (n) => {
  const rail = document.querySelector('.sf-fdetail2__media .sf-gallery__thumbs');
  if (!rail) { return null; }
  const base = Array.from(rail.querySelectorAll('.sf-gallery__thumb'));
  if (!base.length) { return null; }
  let i = 0;
  while (rail.querySelectorAll('.sf-gallery__thumb').length < n) {
    const c = base[i % base.length].cloneNode(true);
    c.id = c.id + '-sim' + i;
    c.setAttribute('aria-selected', 'false');
    c.setAttribute('tabindex', '-1');
    rail.appendChild(c);
    i++;
  }
  return rail.querySelectorAll('.sf-gallery__thumb').length;
};

const plan = [
  { w: 1440, n: null, file: 'a-1440-rail-as-shipped-4-tiles.png' },
  { w: 1440, n: 6, file: 'b-1440-rail-SIMULATED-6-tiles.png' },
  { w: 1440, n: 7, file: 'c-1440-rail-SIMULATED-7-tiles.png' },
  { w: 1440, n: 8, file: 'd-1440-rail-SIMULATED-8-tiles-pushes-down.png' },
  { w: 1240, n: 7, file: 'e-1240-rail-SIMULATED-7-tiles-just-fits.png' },
  { w: 1200, n: 7, file: 'f-1200-rail-SIMULATED-7-tiles-overflows.png' },
  { w: 1024, n: 7, file: 'g-1024-row-SIMULATED-7-tiles-scrolls.png' },
  { w: 768, n: 7, file: 'h-768-row-SIMULATED-7-tiles-fits.png' },
  { w: 375, n: null, file: 'i-375-no-rail-dots.png' },
];

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  for (const p of plan) {
    const ctx = await browser.newContext({
      viewport: { width: p.w, height: 1000 },
      deviceScaleFactor: 1,
      httpCredentials: { username: 'sfdev', password: 'VkEws18Kl5V1qp3TpZ6s' },
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    });
    const page = await ctx.newPage();
    await page.goto(`${DEV}/formulas/${SLUG}/`, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(1000);
    /* guard: prove we are on the served page, not a 401 shell */
    const guard = await page.evaluate(() => ({
      host: location.hostname, title: document.title,
      rail: !!document.querySelector('.sf-fdetail2__media .sf-gallery__thumbs'),
      stage: !!document.querySelector('.sf-fdetail2__media .sf-gallery__stage'),
      tiles: document.querySelectorAll('.sf-gallery__thumb').length,
    }));
    if (!guard.stage || guard.host !== 'dev.zxpet.com') {
      console.log(`GUARD FAILED at ${p.w}: ${JSON.stringify(guard)}`);
      await ctx.close();
      process.exitCode = 1;
      continue;
    }
    if (p.n) { await page.evaluate(growTo, p.n); await page.waitForTimeout(300); }
    await page.locator(SEL).scrollIntoViewIfNeeded();
    await page.waitForTimeout(250);
    await page.locator(SEL).screenshot({ path: path.join(OUT, p.file) });
    const bytes = fs.statSync(path.join(OUT, p.file)).size;
    console.log(`${p.file}  vp=${p.w}  requested=${p.n || guard.tiles}  real tiles=${guard.tiles}  ${bytes}B`);
    await ctx.close();
  }
  await browser.close();
})();
