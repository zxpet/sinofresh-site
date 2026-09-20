const { chromium } = require('playwright-core');

const TARGETS = [
  { url: '/',          label: 'home',        slider: '.sf-hero-slider',  dots: '.sf-hero-dots a, .sf-hero-dots button', expect: 1 },
  { url: '/soft-chews/', label: 'soft-chews', slider: '.sf-pslider',      dots: '.sf-pslider__dots a, .sf-pslider__dots button', expect: 1 },
];

(async () => {
  const browser = await chromium.launch();
  const out = {};
  for (const t of TARGETS) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    const errors = [], failed = [];
    page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text().slice(0, 160)); });
    page.on('pageerror', (e) => errors.push('pageerror: ' + String(e).slice(0, 160)));
    page.on('response', (r) => { if (r.status() >= 400) failed.push(r.status() + ' ' + r.url().slice(-70)); });

    await page.goto('http://sinofresh.local' + t.url, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(400);

    const probe = await page.evaluate((sel) => {
      // 1) stylesheet actually parsed, and which ver
      const sheets = [...document.styleSheets].map((s) => {
        let rules = 0; try { rules = s.cssRules.length; } catch (e) { rules = -1; }
        return { href: s.href || '(inline)', rules };
      });
      const styleSheet = sheets.find((s) => /style\.css/.test(s.href));
      // 2) runtime slider init evidence (aria-label is injected by JS only)
      const root = document.querySelector(sel);
      const dots = root ? [...root.querySelectorAll('[aria-label^="Go to"]')].map((d) => d.getAttribute('aria-label')) : [];
      const bar = root ? root.querySelector('.sf-slider-progress__bar') : null;
      // 3) computed style proves our sheet governs the page
      const hdr = document.querySelector('.sf-header');
      const cs = hdr ? getComputedStyle(hdr) : null;
      const body = getComputedStyle(document.body);
      const hero = document.querySelector('.sf-hero-slider .sf-slide');
      const heroBox = hero ? hero.getBoundingClientRect() : null;
      return {
        styleSheetVersion: styleSheet ? (styleSheet.href.match(/ver=([\d.]+)/) || [])[1] : null,
        styleSheetRules: styleSheet ? styleSheet.rules : null,
        totalSheets: sheets.length,
        bodyFont: body.fontFamily.split(',')[0],
        headerBg: cs ? cs.backgroundColor : null,
        headerHeight: hdr ? Math.round(hdr.getBoundingClientRect().height) : null,
        sliderFound: !!root,
        sliderDots: dots,
        progressBarWidth: bar ? Math.round(bar.getBoundingClientRect().width) : null,
        heroSlideW: heroBox ? Math.round(heroBox.width) : null,
        heroSlideH: heroBox ? Math.round(heroBox.height) : null,
      };
    }, t.slider);

    out[t.label] = { probe, errors, failed };
    await ctx.close();
  }
  await browser.close();
  console.log(JSON.stringify(out, null, 1));
})();
