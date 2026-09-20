/**
 * Latest Articles 截图：section 特写 或 viewport 一屏视图
 * 用法：node tools/blog_cards_shot2.js <tag> <vw> <section|screen>
 */
const { chromium } = require('playwright-core');
const path = require('path');
const tag = process.argv[2] || 'after';
const vw = parseInt(process.argv[3] || '1440', 10);
const mode = process.argv[4] || 'section';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/blog-cards';
(async () => {
  const b = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const ctx = await b.newContext({ viewport: { width: vw, height: vw < 500 ? 812 : 900 }, isMobile: vw < 500, hasTouch: vw < 500 });
  const page = await ctx.newPage();
  page.setDefaultTimeout(30000);
  await page.goto('http://sinofresh.local/', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.sf-card--flush', { timeout: 20000 });
  await page.waitForTimeout(500);
  // bring the section into view so lazy covers load
  await page.evaluate(() => {
    const s = document.querySelector('.sf-card--flush').closest('section');
    window.scrollTo(0, s.getBoundingClientRect().top + window.scrollY - 30);
  });
  await page.evaluate(async () => {
    const wait = [...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; }));
    await Promise.race([Promise.all(wait), new Promise(r => setTimeout(r, 4000))]);
  });
  await page.evaluate(async () => { await document.fonts.ready; });
  await page.waitForTimeout(500);
  // unobstructed shots: unpin the sticky header, drop the cookie bar
  await page.evaluate(() => {
    const s = document.createElement('style');
    s.textContent = '.sf-header{position:static!important}.sf-cookie-banner{display:none!important}';
    document.head.appendChild(s);
  });
  await page.waitForTimeout(300);

  if (mode === 'screen') {
    await page.evaluate(() => {
      const s = document.querySelector('.sf-card--flush').closest('section');
      window.scrollTo(0, s.getBoundingClientRect().top + window.scrollY);
    });
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(OUT, tag + '-screen-' + vw + '.png'), animations: 'disabled', timeout: 20000 });
    const info = await page.evaluate(() => {
      const s = document.querySelector('.sf-card--flush').closest('section');
      const btn = s.querySelector('.wp-block-buttons');
      const r = s.getBoundingClientRect();
      const br = btn.getBoundingClientRect();
      return {
        sectionTopInViewport: Math.round(r.top),
        sectionHeight: Math.round(r.height),
        buttonBottomInViewport: Math.round(br.bottom),
        fitsInViewport: br.bottom <= window.innerHeight,
        viewportH: window.innerHeight,
      };
    });
    console.log('screen', vw, JSON.stringify(info));
  } else {
    const handle = await page.$('.sf-card--flush');
    const el = await handle.evaluateHandle(e => e.closest('section'));
    await el.asElement().screenshot({ path: path.join(OUT, tag + '-section-' + vw + '.png'), animations: 'disabled', timeout: 20000 });
    console.log('section', vw, 'ok');
  }
  await b.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
