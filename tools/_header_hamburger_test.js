/*
 * Header hamburger position — measurement + assertions.
 *
 *   record:  NODE_PATH=... node tools/_header_hamburger_test.js record before
 *   verify:  NODE_PATH=... node tools/_header_hamburger_test.js verify after
 *
 * `record` writes screenshots/hdr-hamburger-<label>.json (pages x {375,1440}).
 * `verify` asserts the mobile hamburger now hugs the basket, that the desktop
 * geometry is byte-identical to the last recorded baseline, and that every
 * page in the set measures the same at 375.
 */
const { chromium } = require('playwright-core');
const fs = require('fs');

const BASE = 'http://sinofresh.local';
const PAGES = [
  ['home', '/'],
  ['products', '/products/'],
  ['soft-chews', '/products/soft-chews/'],
  ['tablets', '/products/tablets/'],
  ['about', '/about/'],
  ['quality', '/quality/'],
  ['contact', '/contact/'],
  ['blog', '/blog/'],
];

const mode = process.argv[2] || 'record';
const label = process.argv[3] || (mode === 'record' ? 'before' : 'after');

let pass = 0, fail = 0;
const ok = (l, c) => { if (c) { pass++; console.log('PASS ' + l); } else { fail++; console.log('FAIL ' + l); } };

async function dismissCookie(page) {
  const btn = page.locator('#cookie-accept, .sf-cookie__accept, [data-cookie-accept]').first();
  if (await btn.count() && await btn.isVisible().catch(() => false)) {
    await btn.click().catch(() => {});
    await page.waitForTimeout(200);
  }
}

async function measure(page) {
  return page.evaluate(() => {
    const R = (el) => { const b = el.getBoundingClientRect(); return { x: Math.round(b.x), w: Math.round(b.width), right: Math.round(b.right), y: Math.round(b.y), h: Math.round(b.height) }; };
    const hdr = document.querySelector('.sf-header');
    const hs = getComputedStyle(hdr);
    const logo = document.querySelector('.sf-header .sf-logo');
    const nav = document.querySelector('.sf-header .wp-block-navigation');
    const open = document.querySelector('.sf-header .wp-block-navigation__responsive-container-open');
    const bag = document.querySelector('.sf-header .sf-basket-btn');
    const cta = document.querySelector('.sf-header .sf-header__cta');
    const q = document.querySelector('.sf-header .sf-header__cta .wp-block-button');
    const openVis = open && getComputedStyle(open).display !== 'none';
    const out = {
      header: { ...R(hdr), justify: hs.justifyContent, align: hs.alignItems, wrap: hs.flexWrap, gap: hs.columnGap, padL: hs.paddingLeft, padR: hs.paddingRight },
      docOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      logo: R(logo),
      cta: R(cta),
      bag: R(bag),
      quote: q ? { display: getComputedStyle(q).display, ...R(q) } : null,
      nav: R(nav),
      hamburgerVisible: !!openVis,
      hamburger: openVis ? R(open) : null,
    };
    if (openVis) {
      out.gapBagToHamburgerBox = out.bag.x - out.hamburger.right;            // box edge -> box edge
      const glyphR = out.hamburger.x + Math.round((out.hamburger.w + 24) / 2); // 24px WP glyph, centred
      out.gapGlyph = out.bag.x + 10 - glyphR;                                 // glyph right -> 20px icon left
      out.gapLogoToHamburger = out.hamburger.x - out.logo.right;
    }
    return out;
  });
}

(async () => {
  const browser = await chromium.launch();
  const out = {};
  for (const [name, path] of PAGES) {
    out[name] = {};
    for (const vw of [375, 1440]) {
      const ctx = await browser.newContext({ viewport: { width: vw, height: 812 } });
      const page = await ctx.newPage();
      await page.goto(BASE + path, { waitUntil: 'networkidle' });
      await dismissCookie(page);
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(350);
      out[name][vw] = await measure(page);
      if (name === 'home') {
        console.log(`[${name} @${vw}] ` + JSON.stringify(out[name][vw]));
      }
      await ctx.close();
    }
  }
  await browser.close();

  const file = `screenshots/hdr-hamburger-${label}.json`;
  fs.writeFileSync(file, JSON.stringify(out, null, 1));
  console.log('\nwrote ' + file);

  if (mode === 'record') { console.log('recording only — no assertions'); return; }

  // ---- assertions --------------------------------------------------------
  const prevFile = `screenshots/hdr-hamburger-${process.argv[4] || 'before'}.json`;
  const prev = fs.existsSync(prevFile) ? JSON.parse(fs.readFileSync(prevFile, 'utf8')) : null;

  console.log('\n--- 1. mobile 375: hamburger hugs the basket ---');
  for (const [name] of PAGES) {
    const m = out[name][375];
    ok(`${name} @375 hamburger visible`, m.hamburgerVisible === true);
    if (m.hamburgerVisible) {
      ok(`${name} @375 gap bag<-hamburger box = ${m.gapBagToHamburgerBox}px (10-18)`,
        m.gapBagToHamburgerBox >= 10 && m.gapBagToHamburgerBox <= 18);
      ok(`${name} @375 hamburger sits right of logo (gap ${m.gapLogoToHamburger}px)`,
        m.gapLogoToHamburger > 20);
      ok(`${name} @375 hamburger right of header centre`, m.hamburger.x > 375 / 2);
      ok(`${name} @375 no horizontal overflow`, m.docOverflow <= 0);
      ok(`${name} @375 basket still at right edge (${m.bag.right} of 359)`,
        Math.abs(m.bag.right - 359) <= 1);
    }
  }

  console.log('\n--- 2. desktop 1440 unchanged ---');
  if (!prev) {
    console.log('no baseline ' + prevFile + ' — skipping desktop comparison');
  } else {
    for (const [name] of PAGES) {
      const a = prev[name][1440], b = out[name][1440];
      ok(`${name} @1440 header box identical`, JSON.stringify(a.header) === JSON.stringify(b.header));
      ok(`${name} @1440 logo/nav/cta/bag/quote identical`,
        JSON.stringify([a.logo, a.nav, a.cta, a.bag, a.quote]) === JSON.stringify([b.logo, b.nav, b.cta, b.bag, b.quote]));
      ok(`${name} @1440 hamburger still hidden (nav is inline)`, b.hamburgerVisible === false);
    }
  }

  console.log('\n--- 3. cross-site consistency @375 ---');
  const sig = (m) => JSON.stringify({ gap: m.gapBagToHamburgerBox, navW: m.nav.w, ctaX: m.cta.x, bagX: m.bag.x });
  const first = sig(out[PAGES[0][0]][375]);
  for (const [name] of PAGES) ok(`${name} @375 matches home signature`, sig(out[name][375]) === first);

  console.log('\n--- 4. page-level: logo + header box untouched @375 ---');
  if (prev) {
    for (const [name] of PAGES) {
      const a = prev[name][375], b = out[name][375];
      ok(`${name} @375 header box identical`, JSON.stringify(a.header) === JSON.stringify(b.header));
      ok(`${name} @375 logo + cta + bag identical`, JSON.stringify([a.logo, a.cta, a.bag]) === JSON.stringify([b.logo, b.cta, b.bag]));
      ok(`${name} @375 quote button still hidden`, b.quote && b.quote.display === 'none');
    }
  }

  console.log(`\nRESULT ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
