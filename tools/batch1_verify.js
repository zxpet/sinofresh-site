/* Batch-1 verification: page heights, configurator single-select, JS errors,
   three breakpoints, screenshots. */
const { chromium, webkit } = require('playwright-core');

const BASE = 'http://sinofresh.local/products/';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/round8/';
const PAGES = ['tablets', 'powders', 'pastes'];

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  const report = {};

  // JS errors on the three pages (desktop)
  for (const slug of PAGES) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message.split('\n')[0]));
    const resp = await page.goto(BASE + slug + '/?nocache=' + Date.now(), { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(600);
    const h = await page.evaluate(() => document.documentElement.scrollHeight);
    report[slug] = { status: resp.status(), jsErrors: errors, desktopHeight: h };
    await ctx.close();
  }

  // configurator single-select + progress + reset on tablets
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    await page.goto(BASE + 'tablets/?nocache=' + Date.now(), { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(400);
    const shapeButtons = page.locator('[data-group="shape"] .configurator__item');
    await shapeButtons.nth(0).click();
    await shapeButtons.nth(2).click(); // single-select: selection must move, not accumulate
    const state = await page.evaluate(() => ({
      selected: [...document.querySelectorAll('[data-group="shape"] .configurator__item.is-selected, [data-group="shape"] .configurator__item[aria-pressed="true"]')].map(b => b.dataset.value),
      progress: document.querySelector('.configurator__progress') ? document.querySelector('.configurator__progress').textContent.trim() : null,
      shapeSummary: (document.querySelector('.configurator__summary-row[data-group="shape"] .configurator__summary-value') || {}).textContent,
      copyBtn: !!document.querySelector('.configurator__copy'),
      resetBtn: !!document.querySelector('.configurator__reset'),
      mobilebar: !!document.querySelector('.configurator__mobilebar'),
    }));
    await page.click('.configurator__reset');
    await page.waitForTimeout(200);
    state.afterResetProgress = await page.evaluate(() => document.querySelector('.configurator__progress').textContent.trim());
    report.configuratorTablets = state;
    await ctx.close();
  }

  // desktop full-page screenshots x3
  for (const slug of PAGES) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 });
    const page = await ctx.newPage();
    await page.goto(BASE + slug + '/?nocache=' + Date.now(), { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(600);
    await page.screenshot({ path: OUT + `${slug}-desktop-full.png`, fullPage: true });
    await ctx.close();
  }

  // iPad 768 (tablets page): triple must be 2 columns + 3rd spans
  {
    const ctx = await browser.newContext({ viewport: { width: 768, height: 1024 }, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    await page.goto(BASE + 'tablets/?nocache=' + Date.now(), { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(500);
    const d = await page.evaluate(() => {
      const cols = [...document.querySelectorAll('.sf-triple > .wp-block-column')];
      const r = cols.map(c => ({ w: Math.round(c.getBoundingClientRect().width), x: Math.round(c.getBoundingClientRect().x) }));
      return { cols: r, overflow: document.documentElement.scrollWidth > innerWidth ? 'OVERFLOW' : 'none' };
    });
    report.ipad768 = d;
    const grid = page.locator('.sf-triple');
    await grid.scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    const b = await grid.boundingBox();
    await page.screenshot({ path: OUT + 'tablets-ipad-triple.png', clip: { x: 0, y: b.y - 20, width: 768, height: Math.min(b.height + 40, 900) } });
    await page.screenshot({ path: OUT + 'tablets-ipad-full.png', fullPage: true });
    await ctx.close();
  }

  // mobile 420 (pastes page)
  {
    const ctx = await browser.newContext({ viewport: { width: 420, height: 900 }, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    await page.goto(BASE + 'pastes/?nocache=' + Date.now(), { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(500);
    const d = await page.evaluate(() => {
      const cols = [...document.querySelectorAll('.sf-triple > .wp-block-column')];
      return {
        colWidths: cols.map(c => Math.round(c.getBoundingClientRect().width)),
        overflow: document.documentElement.scrollWidth > innerWidth ? 'OVERFLOW ' + document.documentElement.scrollWidth : 'none',
        faqW: Math.round(document.querySelector('.sf-faq').getBoundingClientRect().width),
      };
    });
    report.mobile420 = d;
    await page.screenshot({ path: OUT + 'pastes-mobile-full.png', fullPage: true });
    await ctx.close();
  }

  await browser.close();

  // WebKit (Safari) check on tablets
  const wb = await webkit.launch({ headless: true });
  {
    const page = await wb.newPage({ viewport: { width: 1440, height: 900 } });
    await page.goto(BASE + 'tablets/?nocache=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(900);
    const d = await page.evaluate(() => {
      const hero = document.querySelector('.sf-product-hero-image img');
      const tile = document.querySelector('.sf-tile__media img');
      return {
        heroVisible: !!hero && hero.getBoundingClientRect().height > 0,
        tileRadiusClip: tile ? getComputedStyle(tile.parentElement).overflow || getComputedStyle(tile.closest('.sf-tile')).overflow : null,
        tripleCols: [...document.querySelectorAll('.sf-triple > .wp-block-column')].map(c => Math.round(c.getBoundingClientRect().height)),
        overflow: document.documentElement.scrollWidth > innerWidth ? 'OVERFLOW' : 'none',
      };
    });
    report.webkit = d;
    await page.locator('.sf-triple').scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    const b = await page.locator('.sf-triple').boundingBox();
    await page.screenshot({ path: OUT + 'tablets-webkit-triple.png', clip: { x: b.x, y: b.y, width: b.width, height: b.height } });
    await page.close();
  }
  await wb.close();

  console.log(JSON.stringify(report, null, 1));
})().catch(e => { console.error('FAIL:', e.message.split('\n')[0]); process.exit(1); });
