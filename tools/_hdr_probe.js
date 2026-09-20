/*
 * Header hamburger position probe — 375px vs 1440px.
 * Measures the flex children of .sf-header and the gap between the
 * hamburger (nav open button) and the inquiry-basket button.
 *
 * Run: NODE_PATH=/Users/meng/.workbuddy/binaries/node/workspace/node_modules \
 *      node tools/_hdr_probe.js [url]
 */
const { chromium } = require('playwright-core');

const BASE = process.argv[2] || 'http://sinofresh.local/';

(async () => {
  const browser = await chromium.launch();
  for (const vw of [375, 1440]) {
    const ctx = await browser.newContext({ viewport: { width: vw, height: 812 } });
    await ctx.addInitScript(() => {
      try { localStorage.setItem('sinofresh_cookie_consent', '1'); } catch (e) {}
    });
    const page = await ctx.newPage();
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(400);

    const data = await page.evaluate(() => {
      const hdr = document.querySelector('.sf-header');
      const cs = getComputedStyle(hdr);
      const kids = Array.from(hdr.children).map((el) => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return {
          cls: el.className.toString().slice(0, 60),
          x: Math.round(r.x), w: Math.round(r.width), h: Math.round(r.height),
          right: Math.round(r.right),
          ml: s.marginLeft, mr: s.marginRight,
          display: s.display, position: s.position,
        };
      });
      const nav = document.querySelector('.sf-header .wp-block-navigation');
      const navR = nav ? nav.getBoundingClientRect() : null;
      const open = document.querySelector('.sf-header .wp-block-navigation__responsive-container-open');
      const openR = open ? open.getBoundingClientRect() : null;
      const openS = open ? getComputedStyle(open) : null;
      const bag = document.querySelector('.sf-header .sf-basket-btn');
      const bagR = bag ? bag.getBoundingClientRect() : null;
      const logo = document.querySelector('.sf-header .sf-logo');
      const logoR = logo ? logo.getBoundingClientRect() : null;
      const cta = document.querySelector('.sf-header .sf-header__cta');
      const ctaR = cta ? cta.getBoundingClientRect() : null;
      return {
        header: {
          x: Math.round(hdr.getBoundingClientRect().x),
          w: Math.round(hdr.getBoundingClientRect().width),
          display: cs.display, justify: cs.justifyContent, align: cs.alignItems,
          wrap: cs.flexWrap, gap: cs.gap, columnGap: cs.columnGap, rowGap: cs.rowGap,
          padL: cs.paddingLeft, padR: cs.paddingRight,
        },
        kids,
        nav: navR ? { x: Math.round(navR.x), w: Math.round(navR.width), right: Math.round(navR.right), flex: getComputedStyle(nav).flex } : null,
        open: openR ? { x: Math.round(openR.x), w: Math.round(openR.width), right: Math.round(openR.right), display: openS.display, ml: openS.marginLeft, mr: openS.marginRight } : null,
        bag: bagR ? { x: Math.round(bagR.x), w: Math.round(bagR.width), right: Math.round(bagR.right) } : null,
        logo: logoR ? { x: Math.round(logoR.x), w: Math.round(logoR.width), right: Math.round(logoR.right) } : null,
        cta: ctaR ? { x: Math.round(ctaR.x), w: Math.round(ctaR.width), right: Math.round(ctaR.right), justify: getComputedStyle(cta).justifyContent, gap: getComputedStyle(cta).gap } : null,
      };
    });

    console.log('\n=== viewport ' + vw + ' ===');
    console.log(JSON.stringify(data, null, 2));
    if (data.open && data.bag) {
      console.log('gap(hamburger right -> bag left) = ' + (data.bag.x - data.open.right));
      console.log('gap(hamburger center -> bag center) = ' +
        Math.round(((data.open.x + data.open.w / 2) - (data.bag.x + data.bag.w / 2)) * -1));
    }
    if (data.logo && data.open) console.log('gap(logo right -> hamburger left) = ' + (data.open.x - data.logo.right));
    await ctx.close();
  }
  await browser.close();
})();
