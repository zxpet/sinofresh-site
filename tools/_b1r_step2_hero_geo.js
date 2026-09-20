/* Batch 1 (rev2) / Step 2 — Hero BEFORE geometry.
   Measures every box inside .sf-hero-inner at desktop 1440 / tablet 900 /
   mobile 375 so the single-column rebuild can be proven to land <=350px and to
   leave everything below the hero untouched.
   Pre-scrolls the whole page first so lazy images resolve (honest read).
   Usage: node tools/_b1r_step2_hero_geo.js  -> /tmp/b1/step2/hero_geo.json */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const PAGES = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
const BASE = 'http://sinofresh.local/products/';
const VIEWS = {
  desktop: { width: 1440, height: 900 },
  tablet: { width: 900, height: 900 },
  mobile: { width: 375, height: 812 },
};

function probe() {
  const R = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return {
      top: Math.round(r.top + scrollY), h: Math.round(r.height), w: Math.round(r.width),
      left: Math.round(r.left), display: cs.display, position: cs.position,
      mt: cs.marginTop, mb: cs.marginBottom, pt: cs.paddingTop, pb: cs.paddingBottom,
      fs: cs.fontSize, lh: cs.lineHeight, fw: cs.fontWeight, ls: cs.letterSpacing,
      bg: cs.backgroundColor, ta: cs.textAlign,
    };
  };
  const q = (s) => document.querySelector(s);
  const sec = q('section.sf-hero-inner');
  const cols = q('section.sf-hero-inner .wp-block-columns');
  const colEls = cols ? Array.from(cols.children).filter((c) => c.classList.contains('wp-block-column')) : [];
  const h1 = q('section.sf-hero-inner h1');
  const ps = sec ? Array.from(sec.querySelectorAll('p')) : [];
  const btnWrap = q('section.sf-hero-inner .wp-block-buttons');
  const btns = btnWrap ? Array.from(btnWrap.querySelectorAll('a.wp-block-button__link')) : [];
  const frame = q('section.sf-hero-inner .sf-product-hero-image');
  const pslider = q('section.sf-hero-inner .sf-pslider');
  const crumb = q('section.sf-hero-inner .sf-breadcrumb');

  // viewport width available to the constrained inner box
  const innerW = sec ? Math.round(sec.getBoundingClientRect().width) : null;
  const colBoxW = cols ? Math.round(cols.getBoundingClientRect().width) : null;

  return {
    docH: document.body.scrollHeight,
    viewport: { w: innerWidth, h: innerHeight },
    overflowX: document.documentElement.scrollWidth - innerWidth,
    spacing80: getComputedStyle(document.documentElement).getPropertyValue('--wp--preset--spacing--80').trim(),
    blockGap: getComputedStyle(document.documentElement).getPropertyValue('--wp--style--block-gap').trim(),
    contentSize: getComputedStyle(document.documentElement).getPropertyValue('--wp--style--global--content-size').trim(),
    hero: R(sec),
    heroInnerW: innerW,
    crumb: R(crumb),
    cols: cols ? Object.assign(R(cols), {
      gap: getComputedStyle(cols).columnGap,
      display: getComputedStyle(cols).display,
      nColumns: colEls.length,
    }) : null,
    colBoxW: colBoxW,
    columns: colEls.map((c) => R(c)),
    h1: Object.assign(R(h1), { text: h1 ? h1.textContent.trim() : null }),
    paras: ps.map((p) => Object.assign(R(p), { text: p.textContent.trim().slice(0, 120) })),
    btnWrap: btnWrap ? Object.assign(R(btnWrap), { gap: getComputedStyle(btnWrap).gap, justify: getComputedStyle(btnWrap).justifyContent }) : null,
    buttons: btns.map((a) => Object.assign(R(a), {
      text: a.textContent.trim(), href: a.getAttribute('href'),
      cls: String(a.getAttribute('class') || ''), minH: getComputedStyle(a).minHeight,
      hasBg: getComputedStyle(a).backgroundColor,
    })),
    frame: R(frame),
    pslider: pslider ? R(pslider) : null,
    sliderCount: sec ? sec.querySelectorAll('.sf-pslider').length : 0,
    slideCount: sec ? sec.querySelectorAll('.sf-pslider__slide').length : 0,
    slideImgs: sec ? Array.from(sec.querySelectorAll('.sf-pslider img')).map((im) => ({
      src: im.getAttribute('src'), w: im.naturalWidth, h: im.naturalHeight,
      loading: im.getAttribute('loading'), complete: im.complete,
      box: { w: Math.round(im.getBoundingClientRect().width), h: Math.round(im.getBoundingClientRect().height) },
    })) : [],
    // the sections right after the hero: prove they do not move (relative)
    afterHero: (function () {
      const kids = sec ? Array.from(sec.parentElement.children) : [];
      const idx = kids.indexOf(sec);
      return kids.slice(idx + 1, idx + 3).map((k) => ({ tag: k.tagName, cls: String(k.className).slice(0, 60), id: k.id, h: Math.round(k.getBoundingClientRect().height) }));
    })(),
    // sticky header height, for the scroll-margin discussion
    headerH: (function () { const h = q('header, .sf-header'); return h ? Math.round(h.getBoundingClientRect().height) : null; })(),
    anchors: ['#formulas', '#configurator', '#inquiry-form'].map((s) => {
      const el = q(s);
      if (!el) return { sel: s, exists: false };
      const cs = getComputedStyle(el);
      return { sel: s, exists: true, top: Math.round(el.getBoundingClientRect().top + scrollY), h: Math.round(el.getBoundingClientRect().height), smt: cs.scrollMarginTop, smb: 'scroll-margin-bottom' in cs ? cs.scrollMarginBottom : null };
    }),
    tocItems: document.querySelectorAll('[id^="sf-sec-"]').length,
    h2s: Array.from(document.querySelectorAll('h2')).map((h) => h.textContent.trim().slice(0, 60)),
  };
}

async function accept(p) {
  const r = p.locator('button:has-text("Reject Non-Essential")');
  if (await r.count()) await r.first().click({ force: true }).catch(() => {});
}

(async () => {
  const out = {};
  const browser = await pw.chromium.launch({ executablePath: CHROME, args: ['--no-sandbox'] });
  for (const [view, vp] of Object.entries(VIEWS)) {
    out[view] = {};
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    for (const s of PAGES) {
      await page.goto(BASE + s + '/', { waitUntil: 'load' });
      await accept(page);
      // honest read: pre-scroll the whole page to force lazy images in
      await page.evaluate(async () => {
        const H = document.body.scrollHeight;
        for (let y = 0; y < H; y += 400) { scrollTo(0, y); await new Promise((r) => setTimeout(r, 40)); }
        scrollTo(0, 0);
        await Promise.all(Array.from(document.images).map((im) => im.complete || new Promise((r) => { im.onload = im.onerror = r; })));
      });
      await page.waitForTimeout(260);
      await page.evaluate(() => scrollTo(0, 0));
      await page.waitForTimeout(120);
      out[view][s] = await page.evaluate(probe);
    }
    await ctx.close();
  }
  await browser.close();
  const OUT = process.env.GEO_OUT || '/tmp/b1/step2/hero_geo.json';
  fs.mkdirSync(OUT.replace(/\/[^/]+$/, ''), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
  console.log('wrote', OUT);
})();
