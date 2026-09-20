/* Mobile optimisation probe — captures per-breakpoint screenshots + metrics.
   Usage: node mobile_probe.js <label>            (label = before | after)
   Output: screenshots/mobile-<label>/*.png + /tmp/mobile-<label>.json */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const LABEL = process.argv[2] || 'before';
const OUT = path.join(__dirname, '..', 'screenshots', `mobile-${LABEL}`);
fs.mkdirSync(OUT, { recursive: true });

const URL = 'http://sinofresh.local/';

// width, height, tag
const VIEWPORTS = [
  [375, 812, '375'],
  [420, 900, '420'],
  [768, 1024, '768'],
  [1280, 900, '1280'],
];

/* named probes → css selector (first match) */
const PROBES = {
  topbar: '.sf-topbar',
  header: '.sf-header',
  hero: '.sf-hero-slider',
  heroCta: '.sf-hero__cta',
  dosageGrid: '.wp-block-columns.sf-dosage-grid',
  tile1: '.sf-dosage-grid .sf-tile',
  tile1media: '.sf-dosage-grid .sf-tile__media',
  strip: '.wp-block-columns.sf-strip',
  claim1: '.sf-strip .sf-claim',
  certsCols: '.sf-certs-target',
  certCard1: '.sf-certs-target .sf-card',
  panel4: '.wp-block-columns.sf-panel--4',
  stats: '.wp-block-columns.sf-stats',
  aboutBtn: '.wp-block-columns.are-vertically-aligned-stretch .wp-block-button__link',
  footer: '.sf-footer',
  footcol: '.sf-footcol',
  legal: '.sf-footer-legal',
  faq: '.sf-faq',
};

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  const report = {};

  for (const [w, h, tag] of VIEWPORTS) {
    const ctx = await browser.newContext({
      viewport: { width: w, height: h },
      deviceScaleFactor: 2,
      isMobile: w < 769,
      hasTouch: w < 769,
    });
    const page = await ctx.newPage();
    const resp = await page.goto(URL, { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForTimeout(700);

    // freeze the marquee so screenshots are deterministic
    await page.addStyleTag({ content: '.sf-marquee__track{animation-play-state:paused !important}' });
    // wait for webfonts so glyph metrics are stable across runs
    await page.evaluate(() => document.fonts.ready);

    const metrics = await page.evaluate((probes) => {
      const rect = (el) => {
        if (!el) return null;
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        return {
          x: Math.round(r.x), y: Math.round(r.y + scrollY),
          w: Math.round(r.width), h: Math.round(r.height),
          display: cs.display,
          padTop: cs.paddingTop, padBottom: cs.paddingBottom,
          padLeft: cs.paddingLeft, padRight: cs.paddingRight,
          font: cs.fontSize, lh: cs.lineHeight,
          columns: cs.gridTemplateColumns,
          aspect: cs.aspectRatio,
        };
      };
      const out = {};
      for (const [k, sel] of Object.entries(probes)) out[k] = rect(document.querySelector(sel));

      // tile count + first tile copy font sizes
      out._tileCount = document.querySelectorAll('.sf-dosage-grid .sf-tile').length;
      const t = document.querySelector('.sf-dosage-grid .sf-tile h3');
      if (t) out._tileH3 = getComputedStyle(t).fontSize;
      const tp = document.querySelector('.sf-dosage-grid .sf-tile p');
      if (tp) out._tileP = getComputedStyle(tp).fontSize;

      // claim icon rendered size
      const ci = document.querySelector('.sf-strip .sf-claim svg');
      if (ci) {
        const r = ci.getBoundingClientRect();
        out._claimIcon = { w: +r.width.toFixed(1), h: +r.height.toFixed(1) };
      }

      out._docHeight = Math.round(document.documentElement.scrollHeight);
      out._bodyHeight = Math.round(document.body.scrollHeight);
      out._scrollW = document.documentElement.scrollWidth;
      out._clientW = document.documentElement.clientWidth;
      out._overflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;

      // offenders wider than the viewport
      const off = [];
      document.querySelectorAll('body *').forEach((el) => {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.right > document.documentElement.clientWidth + 1.5) {
          if (off.length < 12) off.push({
            sel: el.tagName.toLowerCase() + '.' + (el.className || '').toString().split(' ').slice(0, 2).join('.'),
            right: Math.round(r.right), w: Math.round(r.width),
          });
        }
      });
      out._offenders = off;

      // hero cta buttons visible?
      const hc = document.querySelector('.sf-hero__cta');
      out._heroCtaVisible = hc ? getComputedStyle(hc).display !== 'none' : false;
      // header cta
      const hcta = document.querySelector('.sf-header .wp-block-buttons');
      out._headerCtaDisplay = hcta ? getComputedStyle(hcta).display : 'none-el';
      // nav hamburger
      const burger = document.querySelector('.wp-block-navigation__responsive-container-open');
      out._burger = rect(burger);
      // desktop nav inline
      const navInline = document.querySelector('.wp-block-navigation__container');
      out._navInlineDisplay = navInline ? getComputedStyle(navInline).display : null;
      return out;
    }, PROBES);

    report[tag] = { status: resp ? resp.status() : null, ...metrics };

    // ---- screenshots ----
    if (tag !== '1280') {
      // top of page: topbar + header + hero
      await page.screenshot({ path: path.join(OUT, `${tag}-01-top.png`) });
    }

    // section-by-section, scrolled to each anchor
    const SHOTS = [
      ['02-dosage', 'Our 8 Dosage Forms'],
      ['03-clean', 'Formulated Clean'],
      ['04-certs', 'Certifications'],
      ['05-export', 'Exporting to 4 Continents'],
      ['06-about', 'About SINO FRESH'],
      ['07-faq', 'Frequently Asked Questions'],
    ];
    for (const [name, text] of SHOTS) {
      const el = await page.evaluateHandle((t) => {
        const hs = [...document.querySelectorAll('h2')];
        const h = hs.find((x) => x.textContent.trim().startsWith(t));
        return h ? h.closest('section') || h : null;
      }, text);
      const node = el.asElement();
      if (node) {
        try {
          await node.scrollIntoViewIfNeeded();
          await page.waitForTimeout(350);
          const box = await node.boundingBox();
          if (box) {
            await page.screenshot({
              path: path.join(OUT, `${tag}-${name}.png`),
              clip: { x: 0, y: Math.max(0, box.y), width: w, height: Math.min(box.height, 2400) },
            });
          }
        } catch (e) { /* clip outside viewport after scroll — ignore */ }
      }
    }

    // footer
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(OUT, `${tag}-08-footer.png`) });

    const ctx2 = report[tag];
    ctx2._captured = fs.readdirSync(OUT).filter((f) => f.startsWith(tag + '-')).length;
    await ctx.close();
    console.error('captured', tag, 'docHeight', metrics._docHeight, 'overflow', metrics._overflow);
  }

  fs.writeFileSync(`/tmp/mobile-${LABEL}.json`, JSON.stringify(report, null, 1));
  await browser.close();
})();
