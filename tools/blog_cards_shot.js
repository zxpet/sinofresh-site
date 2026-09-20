/** Latest Articles 区块元素截图（已验证可行的元素截图模式） */
const { chromium } = require('playwright-core');
const path = require('path');
const tag = process.argv[2] || 'before';
const vw = parseInt(process.argv[3] || '1440', 10);
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/blog-cards';
const url = 'http://sinofresh.local/';
(async () => {
  const b = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const ctx = await b.newContext({ viewport: { width: vw, height: vw < 500 ? 812 : 900 }, isMobile: vw < 500, hasTouch: vw < 500 });
  const page = await ctx.newPage();
  page.setDefaultTimeout(30000);
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.sf-card--flush', { timeout: 20000 });
  await page.waitForTimeout(600);
  await page.evaluate(() => {
    const w = document.querySelector('.sf-card--flush');
    return { h: w ? w.getBoundingClientRect().height : 0 };
  });
  await page.waitForTimeout(300);
  // hide cookie banner via addInitScript-style approach: plain DOM style before shot
  await page.evaluate(() => {
    const s = document.createElement('style');
    s.textContent = '.sf-cookie-banner{display:none!important}';
    document.head.appendChild(s);
  });
  const sec = await page.$('.sf-card--flush');
  const el = await sec.evaluateHandle(e => e.closest('section'));
  await el.asElement().screenshot({ path: path.join(OUT, tag + '-section-' + vw + '.png'), animations: 'disabled', timeout: 20000 });
  console.log('OK ->', OUT + '/' + tag + '-section-' + vw + '.png');
  await b.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
