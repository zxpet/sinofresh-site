/* Batch-3 probe for cooperation / blog / 404 / search / privacy / cookie / terms.
 *
 *   node batch3_probe.js before  -> screenshots/batch3-before.json
 *   node batch3_probe.js after   -> screenshots/batch3-after.json
 *
 * Mobile (375/420/768): docH, overflowX, tables (width, scrollable ancestor,
 * per-cell min width), columns, hero padding, sections (classes + padding).
 * Desktop (1440): docH + per-section fingerprint for regression diff.
 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const LABEL = process.argv[2] || 'before';
const BASE = 'http://sinofresh.local';

const PAGES = [
  ['cooperation', '/cooperation/'],
  ['blog', '/blog/'],
  ['404', '/no-such-page-b3/'],
  ['search', '/?s=pet'],
  ['privacy', '/privacy-policy/'],
  ['cookie', '/cookie-policy/'],
  ['terms', '/terms/'],
];

const MOBILE = [
  [375, 812, '375'],
  [420, 900, '420'],
  [768, 1024, '768'],
];

async function settle(page) {
  await page.evaluate(() => {
    document.querySelectorAll('img').forEach((i) => {
      i.loading = 'eager';
      i.decoding = 'sync';
    });
  });
  await page.evaluate(async () => {
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
  });
  await page.evaluate(async () => {
    const imgs = [...document.querySelectorAll('img')];
    await Promise.all(
      imgs.map((i) =>
        i.complete && i.naturalWidth
          ? Promise.resolve()
          : new Promise((r) => {
              i.addEventListener('load', r, { once: true });
              i.addEventListener('error', r, { once: true });
              setTimeout(r, 4000);
            })
      )
    );
    window.scrollTo(0, document.body.scrollHeight);
  });
  await page.waitForTimeout(350);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(250);
}

function collect() {
  const px = (v) => Math.round(parseFloat(v) || 0);
  const doc = document.documentElement;
  const cls = (el) => (el ? el.className.replace(/\s+/g, ' ').trim().slice(0, 80) : null);

  const isScrollableX = (el) => {
    const cs = getComputedStyle(el);
    return /(auto|scroll)/.test(cs.overflowX) && el.scrollWidth > el.clientWidth + 1;
  };
  const scrollAncestor = (el) => {
    let n = el.parentElement;
    while (n && n !== document.body) {
      if (isScrollableX(n)) return n;
      n = n.parentElement;
    }
    return null;
  };

  const tables = [...document.querySelectorAll('table')].map((t, i) => {
    const b = t.getBoundingClientRect();
    const cells = [...t.querySelectorAll('th,td')];
    const sc = scrollAncestor(t);
    return {
      i,
      cls: cls(t).slice(0, 60),
      w: px(b.width),
      docOverflow: b.right > doc.clientWidth + 1 || b.left < -1,
      scrollW: t.scrollWidth,
      cellMinW: cells.length ? Math.min(...cells.map((c) => px(c.getBoundingClientRect().width))) : null,
      nCells: cells.length,
      inScrollable: !!sc,
      scrollCls: sc ? cls(sc) : null,
    };
  });

  const cols = [...document.querySelectorAll('.wp-block-columns')].map((el, i) => {
    const cs = getComputedStyle(el);
    const kids = [...el.children].filter((c) => getComputedStyle(c).display !== 'none');
    const sec = el.closest('section');
    return {
      i,
      cls: cls(el),
      section: sec ? cls(sec).slice(0, 60) : null,
      display: cs.display,
      tracks: cs.gridTemplateColumns,
      n: kids.length,
      widths: kids.map((k) => px(k.getBoundingClientRect().width)),
      h: px(el.getBoundingClientRect().height),
    };
  });

  const cards = [...document.querySelectorAll('.sf-tile, article, .sf-post-card, .post-card')].map((el, i) => {
    const b = el.getBoundingClientRect();
    if (!b.width && !b.height) return null;
    return {
      i,
      cls: cls(el),
      w: px(b.width),
      h: px(b.height),
      top: px(b.top + window.scrollY),
    };
  }).filter(Boolean).slice(0, 40);

  const heroInner = (() => {
    const h = document.querySelector('.sf-hero-inner');
    if (!h) return null;
    const cs = getComputedStyle(h);
    return { pt: px(cs.paddingTop), pb: px(cs.paddingBottom) };
  })();

  const sections = [...document.querySelectorAll('section')].map((el, i) => {
    const cs = getComputedStyle(el);
    return {
      i,
      cls: cls(el),
      pt: px(cs.paddingTop),
      pb: px(cs.paddingBottom),
      h: px(el.getBoundingClientRect().height),
    };
  });

  return {
    docH: doc.scrollHeight,
    docW: doc.clientWidth,
    scrollW: doc.scrollWidth,
    overflowX: doc.scrollWidth - doc.clientWidth,
    heroInner,
    tables,
    cols,
    cards,
    sections,
  };
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome' });
  const out = { label: LABEL, pages: {} };

  for (const [name, url] of PAGES) {
    const rec = { url, viewports: {}, jsErrors: [] };
    for (const [w, h, tag] of MOBILE) {
      const ctx = await browser.newContext({
        viewport: { width: w, height: h },
        deviceScaleFactor: 1,
        isMobile: w <= 768,
        hasTouch: w <= 768,
      });
      const page = await ctx.newPage();
      page.on('pageerror', (e) => rec.jsErrors.push(String(e).slice(0, 160)));
      await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 60000 });
      await settle(page);
      rec.viewports[tag] = await page.evaluate(collect);
      await ctx.close();
    }
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 60000 });
    await settle(page);
    const d = await page.evaluate(collect);
    rec.viewports['1440'] = {
      docH: d.docH,
      sections: d.sections.map((s) => ({ i: s.i, cls: s.cls, h: s.h, w: d.docW })),
      cols: d.cols.map((c) => ({ i: c.i, cls: c.cls, h: c.h, w: 0, tracks: c.tracks })),
    };
    await ctx.close();
    out.pages[name] = rec;
    console.error(`  ${name}: 375=${rec.viewports['375'].docH}/ovx${rec.viewports['375'].overflowX} 768=${rec.viewports['768'].docH}/ovx${rec.viewports['768'].overflowX} 1440=${rec.viewports['1440'].docH}`);
  }

  await browser.close();
  const dest = path.resolve(__dirname, '..', 'screenshots', `batch3-${LABEL}.json`);
  fs.writeFileSync(dest, JSON.stringify(out, null, 1));
  console.error(`written ${dest}`);
})();
