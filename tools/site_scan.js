/* Site-wide mobile audit for the SINO FRESH block theme.
 *
 *   node site_scan.js scan     -> per-page metrics at 375 and 1440 (JSON to stdout)
 *   node site_scan.js shots    -> 1440 full-page baseline PNGs into screenshots/site-before/
 *
 * For each page the 375 pass reports whether every rule of section 27 is
 * active (topbar slimming, nav CTA removal, section padding, two-up grids,
 * cert scroller, footer accordion) plus anything that still looks desktop:
 * 3+ track grids, sections over 48px, tables without a scroller, elements
 * wider than the viewport.
 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const BASE = 'http://sinofresh.local';
const PAGES = [
  ['home', '/'],
  ['products', '/products/'],
  ['soft-chews', '/products/soft-chews/'],
  ['tablets', '/products/tablets/'],
  ['powders', '/products/powders/'],
  ['pastes', '/products/pastes/'],
  ['drops', '/products/drops/'],
  ['liquids', '/products/liquids/'],
  ['fish-oil', '/products/fish-oil/'],
  ['dental-chews', '/products/dental-chews/'],
  ['about', '/about/'],
  ['quality', '/quality/'],
  ['factory-tour', '/factory-tour/'],
  ['services', '/services/'],
  ['cooperation', '/cooperation/'],
  ['contact', '/contact/'],
  ['blog', '/blog/'],
  ['test-article', '/test-article/'],
  ['privacy-policy', '/privacy-policy/'],
  ['cookie-policy', '/cookie-policy/'],
  ['terms', '/terms/'],
  ['404', '/404-probe/'],
  ['search', '/?s=soft'],
];

const OUTDIR = path.resolve(__dirname, '..', 'screenshots', 'site-before');

function collect() {
  const vis = (el) => {
    if (!el) return null;
    const cs = getComputedStyle(el);
    const b = el.getBoundingClientRect();
    return { display: cs.display, h: Math.round(b.height), w: Math.round(b.width), visible: cs.display !== 'none' && b.height > 0 };
  };

  const r = {
    topbar: vis(document.querySelector('.sf-topbar')),
    topbarMid: vis(document.querySelector('.sf-topbar-mid')),
    topbarRight: vis(document.querySelector('.sf-topbar-right')),
    topbarContact: vis(document.querySelector('.sf-topbar-contact')),
    headerH: Math.round((document.querySelector('.sf-header') || { getBoundingClientRect: () => ({ height: 0 }) }).getBoundingClientRect().height),
    navCta: vis(document.querySelector('.sf-header__cta')),
    burger: vis(document.querySelector('.wp-block-navigation__responsive-container-open')),
    logo: vis(document.querySelector('.sf-logo img')),
    docH: document.documentElement.scrollHeight,
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    h1: document.querySelectorAll('h1').length,
    h2: document.querySelectorAll('h2').length,
    h3: document.querySelectorAll('h3').length,
    img: document.querySelectorAll('img').length,
    imgNoAlt: [...document.querySelectorAll('img')].filter(i => !i.hasAttribute('alt')).length,
    details: document.querySelectorAll('details').length,
    detailsFooter: document.querySelectorAll('details.sf-footcol').length,
    detailsOpen: [...document.querySelectorAll('details')].filter(d => d.open).length,
    links: document.querySelectorAll('a[href]').length,
    jsonld: [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => {
      try { return JSON.parse(s.textContent)['@graph'] ? JSON.parse(s.textContent)['@graph'].map(g => g['@type']).flat().join(',') : (JSON.parse(s.textContent)['@type'] || '?'); }
      catch (e) { return 'parse-error'; }
    }),
    sections: [],
    grids: [],
    wide: [],
    tables: [],
    features: {},
  };

  // sections: padding + class rhythm
  const secClass = (el) => ['sf-section--xl', 'sf-section--large', 'sf-section--medium', 'sf-section--small'].find(c => el.classList.contains(c)) || '-';
  r.sections = [...document.querySelectorAll('.sf-section')].map((s, i) => {
    const cs = getComputedStyle(s);
    return { i, cls: secClass(s), pt: Math.round(parseFloat(cs.paddingTop)), pb: Math.round(parseFloat(cs.paddingBottom)), h: Math.round(s.getBoundingClientRect().height) };
  });

  // column blocks: tracks + child count
  r.grids = [...document.querySelectorAll('.wp-block-columns')].map((c, i) => {
    const cs = getComputedStyle(c);
    const tracks = cs.display === 'grid' ? cs.gridTemplateColumns.split(' ').filter(Boolean).length : 0;
    const tag = c.className.split(' ').filter(x => /^sf-/.test(x)).join('.') || '-';
    return { i, tag, display: cs.display, tracks, kids: c.children.length, gap: cs.columnGap || cs.gap, w: Math.round(c.getBoundingClientRect().width) };
  }).filter(g => g.tracks >= 3 || (g.display !== 'grid' && g.kids >= 3));

  // tables / anything that overflows its own box horizontally
  r.tables = [...document.querySelectorAll('table, .wp-block-table, .sf-table')].map(t => {
    const box = t.closest('.wp-block-table') || t;
    const par = box.parentElement;
    return { tag: t.className.toString().split(' ').slice(0, 2).join('.'), w: Math.round(box.getBoundingClientRect().width), parentW: Math.round(par.getBoundingClientRect().width), scrollable: getComputedStyle(par).overflowX };
  });

  // elements sticking out of the viewport
  const vw = document.documentElement.clientWidth;
  r.wide = [...document.querySelectorAll('body *')].filter(el => {
    const b = el.getBoundingClientRect();
    return b.width > vw + 2 && b.height > 24 && getComputedStyle(el).position !== 'fixed';
  }).slice(0, 12).map(el => ({ tag: el.tagName.toLowerCase() + '.' + el.className.toString().split(' ').slice(0, 2).join('.'), w: Math.round(el.getBoundingClientRect().width) }));

  // section-27 feature probes (mobile only)
  const cs1 = (sel, prop) => { const el = document.querySelector(sel); return el ? getComputedStyle(el)[prop] : null; };
  r.features = {
    sectionLargePT: (() => { const s = [...document.querySelectorAll('.sf-section--large')][0]; return s ? Math.round(parseFloat(getComputedStyle(s).paddingTop)) : null; })(),
    dosageGridCols: (() => { const g = document.querySelector('.sf-dosage-grid'); return g ? Math.round(g.getBoundingClientRect().width / (g.children[0] ? g.children[0].getBoundingClientRect().width : 1) * 10) / 10 : null; })(),
    certsSnap: cs1('.sf-certs', 'scrollSnapType'),
    certsOverflow: cs1('.sf-certs', 'overflowX'),
    certsDots: cs1('.sf-certs-dots', 'display'),
    stripCols: (() => { const g = document.querySelector('.sf-strip'); return g ? getComputedStyle(g).gridTemplateColumns : null; })(),
    panel3Merged: (() => { const g = document.querySelector('.sf-panel--3'); return g ? getComputedStyle(g).display : null; })(),
    footerGridGap: cs1('.sf-footer-grid', 'gap'),
    footcolSummaryH: (() => { const s = document.querySelector('.sf-footcol summary'); return s ? Math.round(s.getBoundingClientRect().height) : null; })(),
    aboutCtaBlock: cs1('.sf-about__cta .wp-block-button__link', 'display'),
    qcGridTracks: (() => { const s = [...document.querySelectorAll('section')].find(x => x.querySelector('.sf-panel--3')); return s ? getComputedStyle(s).display : null; })(),
    gravityForms: document.querySelectorAll('.gform_wrapper').length,
    configurator: document.querySelectorAll('[class*="sf-config"], .sf-quote-form, .sf-options').length,
    blogCards: document.querySelectorAll('.sf-card--flush').length,
    tiles: document.querySelectorAll('.sf-tile').length,
    faqDetails: document.querySelectorAll('.sf-faq details, details.sf-faq__item').length,
  };
  return r;
}

(async () => {
  const mode = process.argv[2] || 'scan';
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  if (mode === 'shots') fs.mkdirSync(OUTDIR, { recursive: true });
  const out = {};

  for (const [slug, url] of PAGES) {
    const rec = { url };
    for (const [w, tag, mobile] of [[375, 'm', true], [1440, 'd', false]]) {
      const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 1, isMobile: mobile });
      const page = await ctx.newPage();
      try {
        await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 90000 });
      } catch (e) {
        rec[tag] = { error: String(e).slice(0, 120) };
        await ctx.close();
        continue;
      }
      await page.waitForTimeout(400);
      await page.evaluate(() => document.fonts.ready);
      // settle lazy images by walking the page once
      await page.evaluate(async () => {
        const step = innerHeight;
        for (let y = 0; y < document.body.scrollHeight; y += step) { scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); }
        scrollTo(0, 0);
      });
      await page.waitForTimeout(500);
      if (tag === 'm' || mode === 'scan') rec[tag] = await page.evaluate(collect);
      if (mode === 'shots' && tag === 'd') {
        await page.screenshot({ path: path.join(OUTDIR, `${slug}-1440.png`), fullPage: true });
        rec[tag] = { docH: await page.evaluate(() => document.documentElement.scrollHeight) };
      }
      await ctx.close();
    }
    out[slug] = rec;
    console.error('scanned', slug);
  }
  await browser.close();
  console.log(JSON.stringify(out, null, 1));
})();
