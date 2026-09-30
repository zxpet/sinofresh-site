/*
 * H18c — visual evidence for the rail on the tree AS DEPLOYED. READ ONLY.
 *
 * The scan-phase set (docs/h18c-shots/a..i) was taken BEFORE the change, at the
 * old 12px pitch; its 1200px shot is named "overflows", which is exactly what
 * the change was meant to stop being true. This script re-shoots the same
 * geometry against the shipped CSS so the visual record matches production.
 *
 * It also self-proves the rule it is documenting: each shot logs the rail's
 * computed `gap` and its pixel height, so "8px applied to >= 7 tiles, 12px
 * everywhere else" is read off the rendered page rather than asserted.
 *
 * Tiles beyond the record's own four are cloned in the browser's own DOM
 * (labelled SIMULATED in the filename); the DB is never touched.
 *
 * Run:
 *   NODE_PATH=/Users/meng/.workbuddy/binaries/node/workspace/node_modules \
 *   /Users/meng/.workbuddy/binaries/node/versions/22.22.2-3/bin/node \
 *     tools/h18c_rail_shots_post.js
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const DEV = 'https://dev.zxpet.com';
const SLUG = 'joint-support-soft-chews';
const OUT = path.join(__dirname, '..', 'docs', 'h18c-shots-post');
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

/* read the rail back off the rendered page: gap, height, overflow */
const readRail = () => {
  const rail = document.querySelector('.sf-fdetail2__media .sf-gallery__thumbs');
  const stage = document.querySelector('.sf-fdetail2__media .sf-gallery__stage');
  if (!rail) { return { rail: false }; }
  const cs = getComputedStyle(rail);
  return {
    rail: true,
    dir: cs.flexDirection,
    gap: cs.gap,
    overflowY: cs.overflowY,
    overflowX: cs.overflowX,
    h: Math.round(rail.getBoundingClientRect().height * 100) / 100,
    stageH: stage ? Math.round(stage.getBoundingClientRect().height * 100) / 100 : null,
    tiles: rail.querySelectorAll('.sf-gallery__thumb').length,
    scrolls: rail.scrollHeight > rail.clientHeight + 1 || rail.scrollWidth > rail.clientWidth + 1,
  };
};

const plan = [
  { w: 1440, n: null, file: 'post-1440-rail-as-shipped-4-tiles.png' },
  { w: 1440, n: 7, file: 'post-1440-rail-SIMULATED-7-tiles.png' },
  { w: 1440, n: 8, file: 'post-1440-rail-SIMULATED-8-tiles-pushed-down.png' },
  { w: 1240, n: 7, file: 'post-1240-rail-SIMULATED-7-tiles.png' },
  { w: 1200, n: 7, file: 'post-1200-rail-SIMULATED-7-tiles.png' },
  { w: 1101, n: 7, file: 'post-1101-rail-SIMULATED-7-tiles-dips.png' },
  { w: 1024, n: 7, file: 'post-1024-row-SIMULATED-7-tiles-scrolls.png' },
  { w: 768, n: 7, file: 'post-768-row-SIMULATED-7-tiles.png' },
  { w: 375, n: null, file: 'post-375-no-rail-dots.png' },
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
      sheet: (document.querySelector('link[href*="sinofresh-theme/style.css"]') || {}).href || null,
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
    const m = await page.evaluate(readRail);
    await page.locator(SEL).screenshot({ path: path.join(OUT, p.file) });
    const bytes = fs.statSync(path.join(OUT, p.file)).size;
    console.log(
      `${p.file}\n    vp=${p.w} requested=${p.n || guard.tiles} tiles=${m.tiles} ` +
      `dir=${m.dir} gap=${m.gap} railH=${m.h} stageH=${m.stageH} ` +
      `overflowY=${m.overflowY} scrolls=${m.scrolls} ${bytes}B`
    );
    await ctx.close();
  }
  await browser.close();
})();
