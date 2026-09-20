const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  const shots = [
    ['http://sinofresh.local/category/case-studies/', '/tmp/navscan/archive-case-empty-1440.png'],
    ['http://sinofresh.local/category/manufacturing/', '/tmp/navscan/archive-manufacturing-1440.png'],
  ];
  for (const [url, file] of shots) {
    await page.goto(url, { waitUntil: 'load', timeout: 30000 });
    await page.evaluate(() => { const b = document.querySelector('.sf-cookie-banner'); if (b) b.style.display = 'none'; });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(400);
    await page.screenshot({ path: file, fullPage: true });
    console.log('saved', file);
  }
  // assertions
  await page.goto('http://sinofresh.local/category/case-studies/', { waitUntil: 'load' });
  const checks = await page.evaluate(() => {
    const h1 = document.querySelector('h1');
    const count = document.querySelector('.sf-archive-count');
    const hero = document.querySelector('.sf-hero-inner');
    const heroBg = hero ? getComputedStyle(hero).backgroundColor : '';
    const noRes = !!document.querySelector('.wp-block-query-no-results');
    const btn = document.querySelector('.wp-block-query-no-results a');
    const footer = !!document.querySelector('.sf-footer, footer');
    return {
      h1: h1 ? h1.textContent.trim() : null,
      count: count ? count.textContent.trim() : null,
      heroBg,
      noRes,
      btnHref: btn ? btn.getAttribute('href') : null,
      footer,
    };
  });
  console.log('case-studies page:', JSON.stringify(checks, null, 1));
  await page.goto('http://sinofresh.local/category/manufacturing/', { waitUntil: 'load' });
  const checks2 = await page.evaluate(() => {
    const cards = document.querySelectorAll('.wp-block-post-template > .wp-block-group');
    const titles = [...document.querySelectorAll('.wp-block-post-template h3 a')].map(a => a.textContent.trim()).slice(0, 3);
    return { cardCount: cards.length, sampleTitles: titles };
  });
  console.log('manufacturing page:', JSON.stringify(checks2, null, 1));
  await browser.close();
})();
