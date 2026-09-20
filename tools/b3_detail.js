/* b3 detail: blog post-template grid, search list, category chip geometry */
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local';
const PAGES = [
  ['blog', '/blog/'],
  ['search', '/?s=pet'],
  ['cooperation', '/cooperation/'],
];

async function settle(page) {
  await page.evaluate(() => {
    document.querySelectorAll('img').forEach((i) => { i.loading = 'eager'; i.decoding = 'sync'; });
  });
  await page.evaluate(async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; });
  await page.waitForTimeout(300);
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  for (const [w, h] of [[375, 812], [768, 1024]]) {
    for (const [name, url] of PAGES) {
      const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
      const page = await ctx.newPage();
      await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 60000 });
      await settle(page);
      const info = await page.evaluate(() => {
        const px = (v) => Math.round(parseFloat(v) || 0);
        const out = {};
        const tpl = document.querySelector('.wp-block-post-template');
        if (tpl) {
          const cs = getComputedStyle(tpl);
          out.tpl = {
            cls: tpl.className.slice(0, 80),
            display: cs.display,
            tracks: cs.gridTemplateColumns,
            dir: cs.flexDirection,
            lis: [...tpl.children].map((li) => {
              const b = li.getBoundingClientRect();
              const chip = li.querySelector('.taxonomy-category');
              const fig = li.querySelector('figure');
              return {
                w: px(b.width), h: px(b.height),
                chip: chip ? { t: px(chip.getBoundingClientRect().top + window.scrollY), h: px(chip.getBoundingClientRect().height), fs: getComputedStyle(chip).fontSize } : null,
                fig: fig ? { h: px(fig.getBoundingClientRect().height), imgH: fig.querySelector('img') ? px(fig.querySelector('img').getBoundingClientRect().height) : 0 } : null,
              };
            }),
          };
        }
        const tbl = document.querySelector('.wp-block-table');
        if (tbl) {
          const t = tbl.querySelector('table');
          out.tbl = {
            figW: px(tbl.getBoundingClientRect().width),
            figScrollable: getComputedStyle(tbl).overflowX,
            tblW: px(t.getBoundingClientRect().width),
            tblScrollW: t.scrollWidth,
            snap: getComputedStyle(tbl).scrollSnapType,
          };
        }
        return out;
      });
      console.log(`--- ${name} @${w}: ${JSON.stringify(info)}`);
      if (w === 375) {
        await page.screenshot({ path: `/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/batch3/before-${name}-375.png`, fullPage: true });
      }
      await ctx.close();
    }
  }
  await browser.close();
})();
