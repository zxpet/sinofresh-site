/* Deep structural digest: padding offenders, grid inventory, key blocks. */
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local';
const PAGES = [
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

function probe() {
  const out = { padding: [], grids: [], blocks: {}, texts: {} };

  // 1. generous vertical padding that survived the mobile pass
  [...document.querySelectorAll('.wp-block-group, .wp-block-column, section, .wp-block-columns')].forEach(el => {
    const cs = getComputedStyle(el);
    const pt = parseFloat(cs.paddingTop), pb = parseFloat(cs.paddingBottom);
    if (Math.max(pt, pb) >= 56) {
      out.padding.push({
        tag: el.tagName.toLowerCase() + '.' + el.className.toString().split(' ').filter(c => /^sf-|^wp-block-group$|^wp-block-columns$/.test(c)).join('.'),
        pt: Math.round(pt), pb: Math.round(pb), w: Math.round(el.getBoundingClientRect().width),
        txt: (el.textContent || '').trim().slice(0, 34),
      });
    }
  });

  // 2. every columns block: display + tracks + inline widths of kids
  [...document.querySelectorAll('.wp-block-columns')].forEach((c, i) => {
    const cs = getComputedStyle(c);
    const tracks = cs.gridTemplateColumns === 'none' ? null : cs.gridTemplateColumns.split(' ').filter(Boolean);
    const kids = [...c.children];
    const firstRowW = kids.map(k => Math.round(k.getBoundingClientRect().width));
    const xs = kids.map(k => Math.round(k.getBoundingClientRect().x));
    out.grids.push({
      i, sf: c.className.toString().split(' ').filter(x => /^sf-/.test(x)).join('.') || '-',
      display: cs.display, flexWrap: cs.flexWrap, n: kids.length,
      tracks: tracks ? tracks.length : 0, trackStr: (tracks || []).slice(0, 4).join(' '),
      kidW: firstRowW.slice(0, 5), kidX: xs.slice(0, 5),
      heading: (() => { let p = c.previousElementSibling; while (p && !/^H[1-4]$/.test(p.tagName)) p = p.previousElementSibling; return p ? p.textContent.trim().slice(0, 40) : null; })(),
      txt: (c.textContent || '').trim().slice(0, 40),
    });
  });

  // 3. key block inventory
  const q = (s) => document.querySelectorAll(s).length;
  out.blocks = {
    tiles: q('.sf-tile'), dosageGrid: q('.sf-dosage-grid'), certs: q('.sf-certs'), certsDots: q('.sf-certs-dots'),
    strip: q('.sf-strip'), claim: q('.sf-claim'), panel3: q('.sf-panel--3'), panel4: q('.sf-panel--4'),
    panelBare: q('.sf-panel--bare'), panel: q('.sf-panel'), stats: q('.sf-stats'), panels: q('.sf-panel--2, .sf-panel--3, .sf-panel--4'),
    cardFlush: q('.sf-card--flush'), slotCover: q('.sf-slot--cover'), slotPhoto: q('.sf-slot--photo'),
    faq: q('.sf-faq'), footcol: q('.sf-footcol'), aboutCta: q('.sf-about__cta'),
    gform: q('.gform_wrapper'), gformInput: q('.gform_wrapper input, .gform_wrapper select, .gform_wrapper textarea'),
    configurator: q('[class*="sf-configu"], .sf-quote, .sf-options, .sf-opt'),
    tables: q('table'), iframe: q('iframe'), forms: q('form'),
    marquee: q('.sf-marquee'), hero: q('.sf-hero'), heroSlider: q('.sf-hero-slider'), story: q('.sf-story'),
    section: q('.sf-section'),
  };

  // 4. headings outline for hierarchy review
  out.headings = [...document.querySelectorAll('h1,h2,h3')].slice(0, 40).map(h => h.tagName + ' ' + h.textContent.trim().slice(0, 44));
  return out;
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  const all = {};
  for (const [slug, url] of PAGES) {
    const ctx = await browser.newContext({ viewport: { width: 375, height: 900 }, deviceScaleFactor: 1, isMobile: true });
    const page = await ctx.newPage();
    try { await page.goto(BASE + url, { waitUntil: 'networkidle', timeout: 90000 }); }
    catch (e) { all[slug] = { error: String(e).slice(0, 100) }; await ctx.close(); continue; }
    await page.waitForTimeout(400);
    await page.evaluate(() => document.fonts.ready);
    all[slug] = await page.evaluate(probe);
    await ctx.close();
    console.error('probed', slug);
  }
  await browser.close();
  console.log(JSON.stringify(all, null, 1));
})();
