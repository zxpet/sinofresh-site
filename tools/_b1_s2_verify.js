/* Batch 1 / Stage 2.1+2.2+2.6 — visibility + interaction probe.
   getBoundingClientRect() lies about a closed <details>: Chromium keeps the
   descendants' layout available, so a rect measure reports the full height of
   content that is not painted. checkVisibility({contentVisibilityAuto:true})
   is the honest test, and the section's own height is the second opinion.
   Usage: node tools/_b1_s2_verify.js  -> /tmp/b1/s2/verify.json */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const PAGES = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
const URL = (s) => `http://sinofresh.local/products/${s}/`;

const PROBE = () => {
  const q = (s) => document.querySelector(s);
  const vis = (el) => (el ? el.checkVisibility({ contentVisibilityAuto: true, opacityProperty: true, visibilityProperty: true }) : null);
  const H = (el) => (el ? Math.round(el.getBoundingClientRect().height) : null);
  const T = (el) => (el ? Math.round(el.getBoundingClientRect().top + scrollY) : null);
  const W = (el) => (el ? Math.round(el.getBoundingClientRect().width) : null);
  const fold = q('.configurator__fold');
  return {
    docH: document.body.scrollHeight,
    sectionH: H(q('#configurator')),
    foldOpen: fold ? fold.open : null,
    foldH: H(fold),
    summaryH: H(q('.configurator__fold-head')),
    cfgVisible: vis(q('.configurator')),
    foldBodyVisible: vis(q('.configurator__fold-body')),
    cfgH: H(q('.configurator')), cfgTop: T(q('.configurator')), cfgW: W(q('.configurator')),
    optionsH: H(q('.configurator__options')), optionsW: W(q('.configurator__options')),
    summaryColH: H(q('.configurator__summary-col')), summaryColW: W(q('.configurator__summary-col')),
    exploreVisible: vis(q('.sf-explore')), exploreH: H(q('.sf-explore')), exploreW: W(q('.sf-explore')), exploreTop: T(q('.sf-explore')),
    exploreLinks: document.querySelectorAll('.sf-explore a').length,
    groups: document.querySelectorAll('.configurator__group').length,
    items: document.querySelectorAll('.configurator__item').length,
    submits: document.querySelectorAll('.configurator__submit').length,
    summaryPointerEvents: fold ? getComputedStyle(q('.configurator__fold-head')).pointerEvents : null,
    iconDisplay: q('.configurator__fold-icon') ? getComputedStyle(q('.configurator__fold-icon')).display : null,
    barDisplay: q('.configurator__bar') ? getComputedStyle(q('.configurator__bar')).display : null,
    barPosition: q('.configurator__bar') ? getComputedStyle(q('.configurator__bar')).position : null,
    mobilebarDisplay: q('.configurator__mobilebar') ? getComputedStyle(q('.configurator__mobilebar')).display : null,
    summaryCardDisplay: q('.configurator__summary') ? getComputedStyle(q('.configurator__summary')).display : null,
    drawerHidden: q('#configurator-drawer') ? q('#configurator-drawer').hidden : null,
    icon: q('.configurator__fold-icon') ? { display: getComputedStyle(q('.configurator__fold-icon')).display } : null,
    tocIds: Array.from(document.querySelectorAll('h2')).map((h) => h.id || '(none)'),
    leadTime: (() => {
      const td = Array.from(document.querySelectorAll('.sf-spectable td')).find((x) => /working days/.test(x.textContent));
      return td ? td.textContent.trim() : null;
    })(),
    // is the first option button a real hit target, or is something over it?
    itemHit: (() => {
      const b = q('.configurator__item');
      if (!b) return null;
      const r = b.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return 'zero-size';
      if (r.top < 0 || r.bottom > innerHeight) return 'offscreen';
      const el = document.elementFromPoint(Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2));
      return el === b || (el && b.contains(el)) ? 'hit' : 'covered-by:' + (el ? el.className : 'null');
    })(),
    summaryCardH: H(q('.configurator__summary')),
    summaryCardPosition: q('.configurator__summary') ? getComputedStyle(q('.configurator__summary')).position : null,
    summaryCardTop: q('.configurator__summary') ? getComputedStyle(q('.configurator__summary')).top : null,
    chipsPerRow: (() => {
      const chips = Array.from(document.querySelectorAll('.sf-explore__chip'));
      if (!chips.length) return null;
      const tops = {};
      chips.forEach((c) => { const t = Math.round(c.getBoundingClientRect().top); tops[t] = (tops[t] || 0) + 1; });
      return Object.values(tops);
    })(),
  };
};

/* Hit-test real tap targets: scroll each one into view first, then ask the
   viewport what is actually on top of its centre. */
const TAP = () => {
  const test = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return { sel, missing: true };
    el.scrollIntoView({ block: 'center' });
    const r = el.getBoundingClientRect();
    const x = Math.round(r.left + r.width / 2);
    const y = Math.round(r.top + r.height / 2);
    const hit = document.elementFromPoint(x, y);
    return {
      sel,
      box: Math.round(r.width) + 'x' + Math.round(r.height),
      inViewport: r.top >= 0 && r.bottom <= innerHeight,
      hit: hit === el || (hit && el.contains(hit)) ? 'self' : (hit ? hit.tagName.toLowerCase() + '.' + String(hit.getAttribute('class') || '').slice(0, 34) : 'null'),
    };
  };
  return [test('.configurator__item'), test('.configurator__submit'), test('.sf-explore__chip'), test('.sf-explore__btn')];
};

async function dismiss(page) {
  const rej = page.locator('button:has-text("Reject Non-Essential")');
  if (await rej.count()) await rej.first().click({ force: true }).catch(() => {});
}

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const out = { desktop: {}, tablet: {}, mobile: {}, interactions: {} };

  // ---------- desktop: folded state + open/close interaction ----------
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    for (const s of PAGES) {
      const page = await ctx.newPage();
      const resp = await page.goto(URL(s), { waitUntil: 'load', timeout: 45000 });
      await dismiss(page);
      await page.waitForTimeout(300);
      const rec = { http: resp ? resp.status() : 0 };
      rec.folded = await page.evaluate(PROBE);

      // expand by clicking the summary (native details toggle, no JS needed)
      await page.locator('.configurator__fold > summary').click({ position: { x: 600, y: 20 } });
      await page.waitForTimeout(400);
      rec.expanded = await page.evaluate(PROBE);
      rec.taps = await page.evaluate(TAP);

      // collapse again
      await page.locator('.configurator__fold > summary').click({ position: { x: 600, y: 20 } });
      await page.waitForTimeout(400);
      rec.refolded = await page.evaluate(PROBE);

      out.desktop[s] = rec;
      await page.close();
    }
    await ctx.close();
  }

  // ---------- tablet + mobile ----------
  for (const [view, vp] of Object.entries({ tablet: { width: 900, height: 900 }, mobile: { width: 375, height: 812 } })) {
    const ctx = await browser.newContext({ viewport: vp });
    for (const s of PAGES) {
      const page = await ctx.newPage();
      const resp = await page.goto(URL(s), { waitUntil: 'load', timeout: 45000 });
      await dismiss(page);
      await page.evaluate(async () => {
        const st = Math.round(innerHeight * 0.8);
        for (let y = 0; y < document.body.scrollHeight; y += st) { scrollTo(0, y); await new Promise((r) => setTimeout(r, 50)); }
        scrollTo(0, 0);
        await new Promise((r) => setTimeout(r, 250));
      });
      const rec = { http: resp ? resp.status() : 0 };
      rec.state = await page.evaluate(PROBE);
      rec.taps = await page.evaluate(TAP);
      await page.evaluate(() => scrollTo(0, 0));
      // tapping the summary must do nothing on a phone/tablet
      await page.locator('.configurator__fold > summary').click({ force: true, position: { x: 120, y: 20 } }).catch(() => {});
      await page.waitForTimeout(350);
      rec.afterTap = await page.evaluate(PROBE);
      out[view][s] = rec;
      await page.close();
    }
    await ctx.close();
  }

  // ---------- deep-link / hashchange / formula jump (JS still to come) ----------
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    await page.goto(URL('liquids') + '#configurator', { waitUntil: 'load', timeout: 45000 });
    await dismiss(page);
    await page.waitForTimeout(600);
    out.interactions.deepLinkLoad = await page.evaluate(PROBE);
    await page.evaluate(() => { history.pushState(null, '', location.pathname); location.hash = ''; });
    await page.waitForTimeout(200);
    await page.evaluate(() => { location.hash = '#configurator'; });
    await page.waitForTimeout(600);
    out.interactions.hashchange = await page.evaluate(PROBE);
    // TOC link
    await page.evaluate(() => { location.hash = 'sf-sec-0'; });
    await page.waitForTimeout(500);
    out.interactions.tocJump = await page.evaluate(() => ({ hash: location.hash, scrollY: Math.round(scrollY), cfgVisible: document.querySelector('.configurator').checkVisibility({ contentVisibilityAuto: true }) }));
    // "Reference this formula ->" with the fold CLOSED.
    // The CTA lives inside a collapsed .sf-formula__item, so open that first —
    // that is the real path a visitor takes.
    await page.evaluate(() => {
      location.hash = '';
      document.querySelector('.configurator__fold').open = false;
      const item = document.querySelector('.sf-formula__item');
      if (item) item.open = true;
    });
    await page.waitForTimeout(400);
    await page.locator('.sf-formula__cta').first().click();
    await page.waitForTimeout(900);
    out.interactions.formulaJump = await page.evaluate(PROBE);
    // explore chip click -> navigates
    await page.evaluate(() => { document.querySelector('.configurator__fold').open = false; });
    try {
      await page.locator('.sf-explore__chip').nth(1).click({ timeout: 10000 });
      await page.waitForTimeout(1200);
      out.interactions.exploreChip = { url: page.url() };
    } catch (e) {
      out.interactions.exploreChip = { error: String(e).slice(0, 160) };
    }
    await ctx.close();
  }

  fs.writeFileSync('/tmp/b1/s2/verify.json', JSON.stringify(out, null, 1));
  console.log('verify.json written');
  await browser.close();
})();
