const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  // 1) Homepage: scroll to stories, hover a card, click through
  await page.goto('http://sinofresh.local/', { waitUntil: 'load', timeout: 30000 });
  await page.evaluate(() => { const b = document.querySelector('.sf-cookie-banner'); if (b) b.style.display = 'none'; });
  await page.evaluate(() => document.fonts.ready);
  const stories = page.locator('.sf-stories');
  await stories.scrollIntoViewIfNeeded();
  await page.waitForTimeout(600);
  // pause marquee via hover on region, then hover card
  const box0 = await stories.boundingBox();
  await page.mouse.move(box0.x + box0.width / 2, box0.y + box0.height / 2);
  await page.waitForTimeout(800);
  const card = page.locator('a.sf-story--link').nth(1);
  await card.hover();
  await page.waitForTimeout(400);
  const region = page.locator('.sf-stories').first();
  const ok = await page.evaluate(() => {
    const a = document.querySelector('a.sf-story--link');
    const r = a.getBoundingClientRect();
    return { tag: a.tagName, href: a.getAttribute('href'), more: a.querySelector('.sf-story__more')?.textContent.trim() };
  });
  console.log('card check:', JSON.stringify(ok));
  await page.screenshot({ path: '/tmp/navscan/cs-home-hover-1440.png', clip: { x: 0, y: 0, width: 1440, height: 900 } });
  // hover label region shot: crop around stories
  const box = await stories.boundingBox();
  await page.screenshot({ path: '/tmp/navscan/cs-home-stories-1440.png', clip: { x: 0, y: Math.max(0, box.y - 120), width: 1440, height: 620 } });
  // click card 1 -> case article
  await page.locator('a.sf-story--link').nth(0).click();
  await page.waitForLoadState('load');
  console.log('clicked through to:', page.url());
  const h1 = await page.evaluate(() => document.querySelector('h1')?.textContent.trim());
  console.log('article h1:', h1);

  // 2) Case article screenshot
  await page.evaluate(() => { const b = document.querySelector('.sf-cookie-banner'); if (b) b.style.display = 'none'; });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
  await page.screenshot({ path: '/tmp/navscan/cs-article-top-1440.png' });
  await page.screenshot({ path: '/tmp/navscan/cs-article-full-1440.png', fullPage: true });

  // 3) Category page
  await page.goto('http://sinofresh.local/category/case-studies/', { waitUntil: 'load' });
  await page.evaluate(() => { const b = document.querySelector('.sf-cookie-banner'); if (b) b.style.display = 'none'; });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
  await page.screenshot({ path: '/tmp/navscan/cs-category-1440.png', fullPage: true });
  const cat = await page.evaluate(() => ({
    h1: document.querySelector('h1')?.textContent.trim(),
    count: document.querySelector('.sf-archive-count')?.textContent.trim(),
    cards: document.querySelectorAll('.wp-block-post-template h3').length,
  }));
  console.log('category:', JSON.stringify(cat));

  // 4) Related-articles query on case page (should show Test Article only, no 404s)
  await browser.close();
  console.log('DONE');
})();
