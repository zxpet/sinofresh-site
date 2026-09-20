/* Natural heights of the merged triple band columns. */
const { chromium } = require('playwright-core');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  await page.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(500);
  const data = await page.evaluate(() => {
    const cols = [...document.querySelectorAll('.sf-triple > .wp-block-column')];
    return cols.map((c, i) => {
      const kids = [...c.children];
      const colTop = c.getBoundingClientRect().top;
      let bottom = 0;
      kids.forEach(k => { bottom = Math.max(bottom, k.getBoundingClientRect().bottom - colTop); });
      const list = c.querySelector('.sf-spec-list, ul');
      const items = [...c.querySelectorAll('.sf-spec-row, li')];
      return {
        i,
        naturalH: Math.round(bottom),
        listH: Math.round(list.getBoundingClientRect().height),
        listTop: Math.round(list.getBoundingClientRect().top - colTop),
        itemHs: items.map(it => Math.round(it.getBoundingClientRect().height)),
      };
    });
  });
  console.log(JSON.stringify(data, null, 2));
  await browser.close();
})();
