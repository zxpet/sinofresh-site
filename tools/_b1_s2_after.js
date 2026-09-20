/* Batch 1 / Stage 2.1+2.2 — geometry AFTER the configurator fold.
   Mirrors tools/_b1_s2_before.js so the two JSON files line up key by key.
   Usage: node tools/_b1_s2_after.js  -> /tmp/b1/s2/after.json */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const PAGES = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
const VIEWS = {
  desktop: { width: 1440, height: 900 },
  tablet:  { width: 900,  height: 900 },
  mobile:  { width: 375,  height: 812 },
};

function snap(page) {
  return page.evaluate(() => {
    const R = (el) => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      return {
        top: Math.round(r.top + scrollY), h: Math.round(r.height), w: Math.round(r.width),
        left: Math.round(r.left), display: cs.display, position: cs.position,
        mt: cs.marginTop, mb: cs.marginBottom, pt: cs.paddingTop, pb: cs.paddingBottom,
      };
    };
    const q = (s) => document.querySelector(s);
    const sec = q('#configurator');
    const fold = q('.configurator__fold');
    const desc = q('.configurator__fold-desc');
    const icon = q('.configurator__fold-icon');
    const h2 = q('#configurator h2');
    return {
      docH: document.body.scrollHeight,
      blockGap: getComputedStyle(document.documentElement).getPropertyValue('--wp--style--block-gap').trim(),
      section: R(sec),
      h2: R(h2),
      desc: R(desc),
      icon: icon ? Object.assign(R(icon), { pointerEvents: getComputedStyle(icon).pointerEvents }) : null,
      cfg: R(q('.configurator')),
      options: R(q('.configurator__options')),
      summaryCol: R(q('.configurator__summary-col')),
      explore: R(q('.sf-explore')),
      exploreRow: R(q('.configurator__explore-row')),
      exploreCol: R(q('.configurator__explore-col')),
      bar: R(q('.configurator__bar')),
      mobilebar: R(q('.configurator__mobilebar')),
      drawerHidden: q('#configurator-drawer') ? q('#configurator-drawer').hidden : null,
      groups: (q('.configurator') || document).querySelectorAll('.configurator__group').length,
      items: (q('.configurator') || document).querySelectorAll('.configurator__item').length,
      summarySticky: q('.configurator__summary') ? getComputedStyle(q('.configurator__summary')).position : null,
      allH2: Array.from(document.querySelectorAll('h2')).map((h) => h.id || '(none)'),
      sectionChildren: sec ? Array.from(sec.children).map((c) => c.tagName.toLowerCase() + '.' + String(c.getAttribute('class') || '').split(' ').slice(0, 2).join('.')) : [],
      // --- fold-specific ---
      fold: fold ? Object.assign(R(fold), {
        open: fold.open,
        summaryH: Math.round(q('.configurator__fold-head').getBoundingClientRect().height),
        summaryPointerEvents: getComputedStyle(q('.configurator__fold-head')).pointerEvents,
        bodyDisplay: getComputedStyle(q('.configurator__fold-body')).display,
        bodyH: Math.round(q('.configurator__fold-body').getBoundingClientRect().height),
      }) : null,
      cfgVisible: (() => { const c = q('.configurator'); if (!c) return null; const r = c.getBoundingClientRect(); return r.height > 0; })(),
      exploreLinks: Array.from(document.querySelectorAll('.sf-explore a')).map((a) => ({ t: (a.textContent || '').trim().slice(0, 18), href: a.getAttribute('href') })),
      exploreVisible: (() => { const e = q('.sf-explore'); if (!e) return null; return e.getBoundingClientRect().height > 0; })(),
      leadTime: (() => { const td = Array.from(document.querySelectorAll('.sf-spectable td')).find((x) => /working days/.test(x.textContent)); return td ? td.textContent.trim() : null; })(),
      cfgTabFocusable: (() => { const b = q('.configurator__item'); if (!b) return null; const r = b.getBoundingClientRect(); return r.width > 0 && r.height > 0; })(),
    };
  });
}

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const out = {};
  for (const [view, vp] of Object.entries(VIEWS)) {
    out[view] = {};
    const ctx = await browser.newContext({ viewport: vp });
    for (const slug of PAGES) {
      const page = await ctx.newPage();
      let r;
      try {
        const resp = await page.goto(`http://sinofresh.local/products/${slug}/`, { waitUntil: 'load', timeout: 45000 });
        const status = resp ? resp.status() : 0;
        const rej = page.locator('button:has-text("Reject Non-Essential")');
        if (await rej.count()) await rej.first().click({ force: true }).catch(() => {});
        await page.evaluate(async () => {
          const s = Math.round(innerHeight * 0.8);
          for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise((r) => setTimeout(r, 50)); }
          scrollTo(0, 0);
          await new Promise((r) => setTimeout(r, 250));
        });
        r = await snap(page);
        r.http = status;
        r.phpErr = (await page.content()).match(/Fatal error|Parse error|Warning:|Notice:|Deprecated:|critical error/g);
        r.phpErr = r.phpErr ? r.phpErr.length : 0;
      } catch (e) {
        r = { error: String(e).slice(0, 200) };
      }
      out[view][slug] = r;
      await page.close();
    }
    await ctx.close();
  }
  fs.writeFileSync('/tmp/b1/s2/after.json', JSON.stringify(out, null, 1));
  console.log('after.json written');
  await browser.close();
})();
