/* Generic page probe + screenshots.
   Usage: node probe.js <mode>
   modes: baseline | triple | social
*/
const { chromium } = require('playwright-core');
const path = require('path');

const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/round6';
const BASE = 'http://sinofresh.local';

async function newPage(browser, w = 1440, h = 900) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
  return await ctx.newPage();
}

(async () => {
  const mode = process.argv[2] || 'baseline';
  const browser = await chromium.launch({
    headless: true,
    args: ['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage'],
  });
  const fs = require('fs');
  fs.mkdirSync(OUT, { recursive: true });

  if (mode === 'baseline' || mode === 'logo') {
    const page = await newPage(browser);
    await page.goto(BASE + '/', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(600);
    const info = await page.evaluate(() => {
      const nav = document.querySelector('.sf-header .sf-logo');
      const navImg = nav && nav.querySelector('img');
      const ftr = document.querySelector('.sf-footer-logo');
      const ftrImg = ftr && ftr.querySelector('img');
      const r = (el) => { if (!el) return null; const b = el.getBoundingClientRect(); return { w: Math.round(b.width), h: Math.round(b.height), x: Math.round(b.left), y: Math.round(b.top) }; };
      let svgBBox = null, gBBox = null, vb = null;
      try {
        const img = navImg;
        // re-fetch the svg as an inline document to measure bbox
        return {
          navHref: nav && nav.querySelector('a') ? nav.querySelector('a').getAttribute('href') : null,
          navImg: navImg ? { src: navImg.getAttribute('src'), nw: navImg.naturalWidth, nh: navImg.naturalHeight, attrW: navImg.getAttribute('width'), attrH: navImg.getAttribute('height'), rect: r(navImg) } : null,
          navFig: r(nav),
          ftrImg: ftrImg ? { src: ftrImg.getAttribute('src'), nw: ftrImg.naturalWidth, nh: ftrImg.naturalHeight, rect: r(ftrImg) } : null,
          ftrFig: r(ftr),
          headerRect: r(document.querySelector('.sf-header')),
          topbarRect: r(document.querySelector('.sf-topbar')),
        };
      } catch (e) { return { err: String(e) }; }
    });
    console.log(JSON.stringify(info, null, 2));
    const navBox = await page.locator('.sf-header .sf-logo').first().boundingBox();
    if (navBox) {
      await page.screenshot({ path: path.join(OUT, 'logo-nav.png'), clip: { x: Math.max(0, navBox.x - 16), y: Math.max(0, navBox.y - 12), width: navBox.width + 32, height: navBox.height + 24 } });
    }
    await page.locator('.sf-footer').first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    const ftrBox = await page.locator('.sf-footer-logo').first().boundingBox();
    if (ftrBox) {
      await page.screenshot({ path: path.join(OUT, 'logo-footer.png'), clip: { x: Math.max(0, ftrBox.x - 20), y: Math.max(0, ftrBox.y - 14), width: Math.max(320, ftrBox.width + 40), height: ftrBox.height + 28 } });
    }
    // topbar social hrefs
    const socials = await page.evaluate(() => {
      const out = { topbar: [], footer: [] };
      document.querySelectorAll('.sf-topbar-social a').forEach(a => out.topbar.push({ label: a.getAttribute('aria-label'), href: a.getAttribute('href') }));
      document.querySelectorAll('.sf-footer .sf-social a').forEach(a => out.footer.push({ label: a.getAttribute('aria-label'), href: a.getAttribute('href'), target: a.getAttribute('target'), rel: a.getAttribute('rel') }));
      return out;
    });
    console.log('TOP SOCIAL', JSON.stringify(socials.topbar));
    console.log('FOOT SOCIAL', JSON.stringify(socials.footer));
  }

  if (mode === 'triple') {
    const page = await newPage(browser);
    await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(600);
    const data = await page.evaluate(() => {
      const cols = [...document.querySelectorAll('.sf-triple > .wp-block-column')];
      const r = (el) => { const b = el.getBoundingClientRect(); return { w: Math.round(b.width), h: Math.round(b.height), top: Math.round(b.top + window.scrollY) }; };
      return {
        pageH: document.documentElement.scrollHeight,
        cols: cols.map((c, i) => {
          const list = c.querySelector('.sf-spec-list, ul');
          const items = c.querySelectorAll('.sf-spec-row, li');
          let itemH = 0, gap = null;
          if (items.length > 1) {
            const a = items[0].getBoundingClientRect(), b = items[1].getBoundingClientRect();
            itemH = Math.round(a.height);
            gap = Math.round(b.top - (a.top + a.height));
          }
          const cs = list ? getComputedStyle(list) : null;
          const liCs = items.length ? getComputedStyle(items[1] || items[0]) : null;
          return {
            i, ...r(c),
            listTag: list ? list.tagName + '.' + list.className : null,
            items: items.length,
            itemH, gap,
            liLineHeight: liCs ? liCs.lineHeight : null,
            liFontSize: liCs ? liCs.fontSize : null,
            liPadding: liCs ? liCs.padding : null,
            liMarginTop: liCs ? liCs.marginTop : null,
          };
        }),
      };
    });
    console.log(JSON.stringify(data, null, 2));
    const box = await page.locator('.sf-triple').first().boundingBox();
    await page.locator('.sf-triple').first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    const b2 = await page.locator('.sf-triple').first().boundingBox();
    await page.screenshot({ path: path.join(OUT, 'triple-' + (process.argv[3] || 'before') + '.png'), clip: { x: b2.x, y: Math.max(0, b2.y), width: b2.width, height: Math.min(b2.height, 900) } });
  }

  await browser.close();
})();
