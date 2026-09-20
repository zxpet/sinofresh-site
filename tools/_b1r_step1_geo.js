/* Batch 1 / 步骤 1 — geometry probe AFTER the configurator-fold rollback.
   Same payload keys as tools/_b1_s2_before.js (the unfolded Stage-1 baseline)
   so the two JSONs diff key-by-key, plus two extras:
     scrollMargins   — #formulas / #configurator scroll-margin-top (step 5 target)
     foldExists      — must be false again
   Usage: node tools/_b1r_step1_geo.js  -> /tmp/b1/step1/geo.json
   Reads:  /tmp/b1/s2/before.json (baseline, never written) */
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
    const smt = (s) => {
      const el = q(s);
      return el ? getComputedStyle(el).scrollMarginTop : null;
    };
    return {
      docH: document.body.scrollHeight,
      status: document.title ? 1 : 1,
      blockGap: getComputedStyle(document.documentElement).getPropertyValue('--wp--style--block-gap').trim(),
      section: R(sec),
      h2: R(q('#configurator h2')),
      p: R(q('#configurator > p')),
      sprite: q('#configurator > svg.configurator__sprite') ? { display: getComputedStyle(q('#configurator > svg.configurator__sprite')).display } : null,
      cfg: R(q('.configurator')),
      options: R(q('.configurator__options')),
      summaryCol: R(q('.configurator__summary-col')),
      explore: R(q('.sf-explore')),
      exploreParent: q('.sf-explore') ? '.' + String(q('.sf-explore').parentElement.getAttribute('class')) : null,
      exploreRowW: R(q('.configurator__explore-row')),
      bar: R(q('.configurator__bar')),
      mobilebar: R(q('.configurator__mobilebar')),
      drawerHidden: q('#configurator-drawer') ? q('#configurator-drawer').hidden : null,
      groups: (q('.configurator') || document).querySelectorAll('.configurator__group').length,
      items: (q('.configurator') || document).querySelectorAll('.configurator__item').length,
      summarySticky: q('.configurator__summary') ? getComputedStyle(q('.configurator__summary')).position : null,
      toc: Array.from(document.querySelectorAll('#configurator h2')).map((h) => ({ id: h.id, text: h.textContent.trim().slice(0, 40) })),
      allH2: Array.from(document.querySelectorAll('h2')).map((h) => h.id || '(none)'),
      sectionChildren: sec ? Array.from(sec.children).map((c) => c.tagName.toLowerCase() + '.' + String(c.getAttribute('class') || '').split(' ').slice(0, 2).join('.')) : [],
      foldExists: !!q('.configurator__fold'),
      scrollMargins: { formulas: smt('#formulas'), configurator: smt('#configurator'), inquiry: smt('#inquiry-form') },
      foldDescExists: !!q('.configurator__fold-desc'),
      splitSectionH: null,
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
      } catch (e) {
        r = { error: String(e).slice(0, 200) };
      }
      out[view][slug] = r;
      await page.close();
    }
    await ctx.close();
  }
  fs.mkdirSync('/tmp/b1/step1', { recursive: true });
  const OUT = process.env.GEO_OUT || '/tmp/b1/step1/geo.json';
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
  console.log('wrote ' + OUT);
  console.log('--- section#configurator heights (rollback) vs baseline ---');
  let base = null;
  try { base = JSON.parse(fs.readFileSync('/tmp/b1/s2/before.json', 'utf8')); } catch (e) {}
  for (const s of PAGES) {
    const d = out.desktop[s], t = out.tablet[s], m = out.mobile[s];
    const b = base ? base.desktop[s] : null;
    const bt = base ? base.tablet[s] : null;
    const bm = base ? base.mobile[s] : null;
    const f = (x, y) => (x == null || y == null ? '?' : (x - y === 0 ? '0' : `${x - y > 0 ? '+' : ''}${x - y}`));
    console.log(`${s.padEnd(14)} http=${d.http} fold=${d.foldExists} | D ${d.section.h} (Δ${f(d.section.h, b && b.section.h)}) T ${t.section.h} (Δ${f(t.section.h, bt && bt.section.h)}) M ${m.section.h} (Δ${f(m.section.h, bm && bm.section.h)}) | exploreParent=${d.exploreParent}`);
  }
  const p = out.desktop.liquids;
  console.log('--- liquids desktop ---');
  console.log(`  sectionChildren=${JSON.stringify(p.sectionChildren)}`);
  console.log(`  h2=${JSON.stringify(p.h2)}`);
  console.log(`  p=${JSON.stringify(p.p)}`);
  console.log(`  cfg=${JSON.stringify(p.cfg)}`);
  console.log(`  explore=${JSON.stringify(p.explore)}  exploreRowW=${JSON.stringify(p.exploreRowW)}`);
  console.log(`  scrollMargins=${JSON.stringify(p.scrollMargins)}`);
  console.log(`  docH=${p.docH}`);
  await browser.close();
})();
