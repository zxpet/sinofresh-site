/* Batch 1 / Stage 2 — geometry BEFORE the configurator fold.
   Captures the exact vertical rhythm (block gap above .configurator, the
   explore band's box, the two configurator columns) so the folded build can be
   proven identical where it must be, and changed only where it must change.
   Usage: node tools/_b1_s2_before.js  -> /tmp/b1/s2/before.json */
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
    const out = {
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
      exploreParent: q('.sf-explore') ? '.' + q('.sf-explore').parentElement.className : null,
      exploreRowW: R(q('.configurator__explore-row')),
      bar: R(q('.configurator__bar')),
      mobilebar: R(q('.configurator__mobilebar')),
      drawerHidden: q('#configurator-drawer') ? q('#configurator-drawer').hidden : null,
      groups: (q('.configurator') || document).querySelectorAll('.configurator__group').length,
      items: (q('.configurator') || document).querySelectorAll('.configurator__item').length,
      summarySticky: q('.configurator__summary') ? getComputedStyle(q('.configurator__summary')).position : null,
      toc: Array.from(document.querySelectorAll('#configurator h2')).map((h) => ({ id: h.id, text: h.textContent.trim().slice(0, 40) })),
      // every h2 on the page with its injected TOC id (order matters)
      allH2: Array.from(document.querySelectorAll('h2')).map((h) => h.id || '(none)'),
      // the section's own children, to see what the constrained layout wraps
      sectionChildren: sec ? Array.from(sec.children).map((c) => c.tagName.toLowerCase() + '.' + String(c.getAttribute('class') || '').split(' ').slice(0, 2).join('.')) : [],
      foldExists: !!q('.configurator__fold'),
    };
    return out;
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
  fs.mkdirSync('/tmp/b1/s2', { recursive: true });
  fs.writeFileSync('/tmp/b1/s2/before.json', JSON.stringify(out, null, 1));
  const pick = out.desktop.liquids;
  console.log(JSON.stringify({
    blockGap: pick.blockGap,
    sectionChildren: pick.sectionChildren,
    section: pick.section, h2: pick.h2, p: pick.p, sprite: pick.sprite, cfg: pick.cfg,
    options: pick.options, summaryCol: pick.summaryCol, explore: pick.explore,
    exploreParent: pick.exploreParent, bar: pick.bar, mobilebar: pick.mobilebar,
    docH: pick.docH, groups: pick.groups, items: pick.items, allH2: pick.allH2,
  }, null, 1));
  console.log('--- heights (section#configurator) ---');
  for (const s of PAGES) {
    const d = out.desktop[s], t = out.tablet[s], m = out.mobile[s];
    console.log(`${s.padEnd(14)} http=${d.http} desktop=${d.section.h} tablet=${t.section.h} mobile=${m.section.h} | docH d=${d.docH} t=${t.docH} m=${m.docH} | explore=${d.explore.h}x${d.explore.w}`);
  }
  await browser.close();
})();
