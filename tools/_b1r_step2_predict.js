/* Batch 1 (rev2) / Step 2 scan — pre-flight predictions.
   (a) Would each page's H1 fit on ONE line inside the 1200px constrained box
       at the current 52px?  (b) the same for the proposed spec subtitle.
   (c) the real sticky header height once scrolled (for the scroll-margin work).
   Usage: node tools/_b1r_step2_predict.js  -> /tmp/b1/step2/predict.json */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const PAGES = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
const BASE = 'http://sinofresh.local/products/';

const SUB = '8 dosage forms \u00b7 FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC \u00b7 MOQ 500 units \u00b7 Export to 30+ countries';

function measure(SUB) {
  const h1 = document.querySelector('section.sf-hero-inner h1');
  const spec = document.querySelector('section.sf-hero-inner p:nth-of-type(2)');
  const font = h1 ? getComputedStyle(h1) : null;
  const specFont = spec ? getComputedStyle(spec) : getComputedStyle(document.body);

  // offscreen ruler: clone the H1's own typography, lay it out at a given width
  function ruler(text, f, width, extra) {
    const host = document.createElement('div');
    host.style.cssText = 'position:absolute;left:-99999px;top:0;visibility:hidden;width:' + width + 'px;';
    const d = document.createElement('div');
    d.style.cssText = 'margin:0;padding:0;';
    d.style.font = f.font || '';
    d.style.fontFamily = f.fontFamily;
    d.style.fontSize = f.fontSize;
    d.style.fontWeight = f.fontWeight;
    d.style.lineHeight = f.lineHeight;
    d.style.letterSpacing = f.letterSpacing;
    d.style.textTransform = f.textTransform;
    if (extra) for (const k in extra) d.style[k] = extra[k];
    d.textContent = text;
    host.appendChild(d);
    document.body.appendChild(host);
    const rects = d.getClientRects().length;
    const w = Math.ceil(d.getBoundingClientRect().width);
    const h = Math.ceil(d.getBoundingClientRect().height);
    const lh = parseFloat(getComputedStyle(d).lineHeight);
    document.body.removeChild(host);
    return { lines: rects || Math.round(h / lh), textW: w, boxH: h, lineH: lh };
  }

  const h1Text = h1 ? h1.textContent.trim() : '';
  const out = {
    h1Text,
    h1Style: font ? { fontSize: font.fontSize, fontWeight: font.fontWeight, lineHeight: font.lineHeight, letterSpacing: font.letterSpacing, fontFamily: font.fontFamily.slice(0, 40) } : null,
    // H1 at the current size inside the constrained content box
    h1_at_1200_current: h1 ? ruler(h1Text, font, 1200) : null,
    h1_at_1200_44: h1 ? ruler(h1Text, font, 1200, { fontSize: '44px', lineHeight: '48px' }) : null,
    h1_at_1200_40: h1 ? ruler(h1Text, font, 1200, { fontSize: '40px', lineHeight: '44px' }) : null,
    h1_at_1440_current: h1 ? ruler(h1Text, font, 1440) : null,
    h1_at_781_current: h1 ? ruler(h1Text, font, 781) : null,
    h1_at_375_current: h1 ? ruler(h1Text, font, 375) : null,
    // proposed spec subtitle, 18px and 15px, at 1200
    sub_18_at_1200: ruler(SUB, { fontFamily: specFont.fontFamily, fontSize: '18px', fontWeight: '400', lineHeight: '28.8px', letterSpacing: 'normal' }, 1200),
    sub_15_at_1200: ruler(SUB, { fontFamily: specFont.fontFamily, fontSize: '15px', fontWeight: '400', lineHeight: '26.4px', letterSpacing: 'normal' }, 1200),
    sub_14_at_375: ruler(SUB, { fontFamily: specFont.fontFamily, fontSize: '14px', fontWeight: '400', lineHeight: '24px', letterSpacing: 'normal' }, 375),
    sub_13_at_375: ruler(SUB, { fontFamily: specFont.fontFamily, fontSize: '13px', fontWeight: '400', lineHeight: '22px', letterSpacing: 'normal' }, 375),
    contentBox: (function () {
      const g = document.querySelector('section.sf-hero-inner .wp-block-group');
      return g ? Math.round(g.getBoundingClientRect().width) : null;
    })(),
  };
  return out;
}

async function sticky() {
  // measure the header when it is actually stuck
  const h = document.querySelector('header, .sf-header');
  if (!h) return null;
  const cs = getComputedStyle(h);
  return { h: Math.round(h.getBoundingClientRect().height), position: cs.position, top: cs.top, cls: String(h.className).slice(0, 80) };
}

(async () => {
  const out = {};
  const browser = await pw.chromium.launch({ executablePath: CHROME, args: ['--no-sandbox'] });
  for (const vp of [{ name: 'desktop', width: 1440 }, { name: 'mobile', width: 375 }]) {
    out[vp.name] = {};
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: 900 } });
    const page = await ctx.newPage();
    for (const s of PAGES) {
      await page.goto(BASE + s + '/', { waitUntil: 'load' });
      const rj = page.locator('button:has-text("Reject Non-Essential")');
      if (await rj.count()) await rj.first().click({ force: true }).catch(() => {});
      await page.waitForTimeout(200);
      const pred = await page.evaluate(measure, SUB);
      // sticky: scroll past the header, then measure
      await page.evaluate(() => scrollTo(0, 1500));
      await page.waitForTimeout(420);
      pred.stickyHeader = await page.evaluate(sticky);
      pred.pinnedAt = await page.evaluate(() => Math.round(document.querySelector('header, .sf-header').getBoundingClientRect().bottom));
      out[vp.name][s] = pred;
    }
    await ctx.close();
  }
  await browser.close();
  const OUT = '/tmp/b1/step2/predict.json';
  fs.mkdirSync(OUT.replace(/\/[^/]+$/, ''), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
  console.log('wrote', OUT);
})();
