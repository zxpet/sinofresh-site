const { chromium } = require('playwright-core');
const path = require('path');
const tag = process.argv[2] || 'before';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/gf-form2';
const PAGES = [
  ['home', 'http://sinofresh.local/'],
  ['contact', 'http://sinofresh.local/contact/'],
  ['soft-chews', 'http://sinofresh.local/products/soft-chews/'],
];
// addStyleTag on this site breaks Playwright's screenshot stability detection
// (root cause unproven) -> inject via addInitScript instead, with exact
// selectors (.sf-header sticky bar + .sf-cookie-banner overlay)
const INIT_CSS = `
  document.addEventListener('DOMContentLoaded', function () {
    var s = document.createElement('style');
    s.id = 'sf-shot-css';
    s.textContent = '.sf-header{position:static!important}.sf-cookie-banner{display:none!important}';
    document.head.appendChild(s);
  });
`;
(async () => {
  const b = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  for (const vp of [{ width: 1440, height: 900 }, { width: 375, height: 812 }]) {
    const ctx = await b.newContext({ viewport: vp, isMobile: vp.width < 500, hasTouch: vp.width < 500 });
    await ctx.addInitScript(INIT_CSS);
    const page = await ctx.newPage();
    page.setDefaultTimeout(25000);
    for (const [name, url] of PAGES) {
      try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForSelector('.gform_wrapper .gform_fields', { timeout: 20000 });
        await page.waitForTimeout(600);
        await page.evaluate(() => {
          const w = document.querySelector('.gform_wrapper');
          return { h: w ? w.getBoundingClientRect().height : 0 };
        });
        await page.waitForTimeout(400);
        const el = await page.$('.gform_wrapper');
        await el.screenshot({ path: path.join(OUT, tag + '-' + name + '-' + vp.width + '.png'), animations: 'disabled', timeout: 20000 });
        console.log('OK', name, vp.width);
      } catch (e) { console.log('FAIL', name, vp.width, e.message.split('\n')[0]); }
    }
    await ctx.close();
  }
  await b.close();
  console.log('done', tag);
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
