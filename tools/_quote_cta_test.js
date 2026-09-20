/*
 * Quote CTA smart scroll — E2E.
 *   NODE_PATH=... node tools/_quote_cta_test.js
 *
 * Covers: in-page smooth scroll on form pages (home / dosage / contact /
 * factory-tour), native navigation on formless pages (about / quality),
 * footer CTA parity, sticky-header clearance, reduced-motion instant jump,
 * the about dead-link fix, and Download Catalog untouched.
 */
const { chromium } = require('playwright-core');

const BASE = 'http://sinofresh.local';
let pass = 0, fail = 0;
const ok = (l, c) => { if (c) { pass++; console.log('PASS ' + l); } else { fail++; console.log('FAIL ' + l); } };

async function dismissCookie(page) {
  const btn = page.locator('#cookie-accept, .sf-cookie__accept, [data-cookie-accept]').first();
  if (await btn.count() && await btn.isVisible().catch(() => false)) {
    await btn.click().catch(() => {});
    await page.waitForTimeout(200);
  }
}

async function scrollToTop(page) { await page.evaluate(() => window.scrollTo(0, 0)); await page.waitForTimeout(150); }

// click a CTA and report geometry after the scroll settles (poll until the
// scroll position stops moving — smooth scrolls on 10k px pages are slow)
async function clickAndMeasure(page, sel) {
  await scrollToTop(page);
  const before = await page.evaluate(() => ({ y: Math.round(scrollY), path: location.pathname }));
  await page.click(sel);
  let prev = -1, still = 0;
  for (let i = 0; i < 60; i++) {
    await page.waitForTimeout(150);
    const y = await page.evaluate(() => Math.round(scrollY));
    if (y === prev) still++; else still = 0; // correction passes pause ~0.5s
    prev = y;
    if (still >= 14) break;                  // motionless for ~2s => settled
  }
  return {
    before,
    after: await page.evaluate(() => {
      const t = document.querySelector('#inquiry-form, #quote, #booking-form');
      const hdr = document.querySelector('.sf-header');
      const r = t ? t.getBoundingClientRect() : null;
      const h = hdr ? hdr.getBoundingClientRect() : null;
      return {
        y: Math.round(scrollY), path: location.pathname, hash: location.hash,
        targetTop: r ? Math.round(r.top) : null,
        headerBottom: h ? Math.round(h.bottom) : null,
        docH: document.documentElement.scrollHeight,
      };
    }),
  };
}

(async () => {
  const browser = await chromium.launch();

  console.log('--- 1. form pages: header CTA scrolls in place ---');
  for (const [name, path, wantHash] of [
    ['home', '/', '#inquiry-form'],
    ['soft-chews', '/products/soft-chews/', '#inquiry-form'],
    ['contact', '/contact/', '#inquiry-form'], // contact hosts BOTH ids; document order picks the form section
    ['factory-tour', '/factory-tour/', '#booking-form'],
  ]) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    await page.goto(BASE + path, { waitUntil: 'networkidle' });
    await dismissCookie(page);
    await page.evaluate(() => document.fonts.ready);
    const m = await clickAndMeasure(page, '.sf-header .sf-quote-cta');
    ok(`${name} no navigation (stayed ${m.after.path})`, m.after.path === path);
    ok(`${name} scrolled down (${m.before.y} -> ${m.after.y})`, m.after.y > m.before.y + 100);
    ok(`${name} url hash = ${m.after.hash}`, m.after.hash === wantHash);
    ok(`${name} target below sticky header (top ${m.after.targetTop} >= bar ${m.after.headerBottom} - 2)`,
      m.after.targetTop !== null && m.after.targetTop >= m.after.headerBottom - 2 && m.after.targetTop < 200);
    await ctx.close();
  }

  console.log('--- 2. formless pages: header CTA navigates to /contact/#quote ---');
  for (const name of ['about', 'quality']) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    await page.goto(`${BASE}/${name}/`, { waitUntil: 'networkidle' });
    await dismissCookie(page);
    await page.click('.sf-header .sf-quote-cta');
    await page.waitForURL('**/contact/#quote', { timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(700);
    const st = await page.evaluate(() => {
      const t = document.querySelector('#quote');
      const h = document.querySelector('.sf-header');
      return { path: location.pathname, hash: location.hash, top: Math.round(t.getBoundingClientRect().top), hb: Math.round(h.getBoundingClientRect().bottom) };
    });
    ok(`${name} -> ${st.path}${st.hash}`, st.path === '/contact/' && st.hash === '#quote');
    ok(`${name} #quote below sticky bar (top ${st.top} >= ${st.hb} - 2)`, st.top >= st.hb - 2 && st.top < 200);
    await ctx.close();
  }

  console.log('--- 3. footer CTA parity ---');
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    await page.goto(BASE + '/about/', { waitUntil: 'networkidle' });
    await dismissCookie(page);
    const vis = await page.locator('footer .sf-quote-cta, .wp-block-template-part .sf-quote-cta').last().isVisible().catch(() => false);
    ok('footer CTA visible on desktop about', vis);
    if (vis) {
      await page.locator('a.sf-quote-cta').last().click();
      await page.waitForURL('**/contact/#quote', { timeout: 8000 }).catch(() => {});
      ok('footer CTA navigates to /contact/#quote', page.url().includes('/contact/#quote'));
    }
    // home: footer CTA scrolls to the form instead
    await page.goto(BASE + '/', { waitUntil: 'networkidle' });
    await dismissCookie(page);
    const m = await clickAndMeasure(page, 'a.sf-quote-cta'); // last = footer
    ok('home footer CTA scrolls to form (y ' + m.before.y + ' -> ' + m.after.y + ', hash ' + m.after.hash + ')',
      m.after.path === '/' && m.after.y > m.before.y + 100 && m.after.hash === '#inquiry-form');
    await ctx.close();
  }

  console.log('--- 4. mobile 375: anchor landing below the phone bar ---');
  {
    const ctx = await browser.newContext({ viewport: { width: 375, height: 812 } });
    const page = await ctx.newPage();
    await page.goto(BASE + '/products/soft-chews/#inquiry-form', { waitUntil: 'networkidle' });
    await dismissCookie(page);
    await page.waitForTimeout(500);
    const st = await page.evaluate(() => {
      const t = document.querySelector('#inquiry-form').getBoundingClientRect();
      const h = document.querySelector('.sf-header').getBoundingClientRect();
      return { top: Math.round(t.top), hb: Math.round(h.bottom), overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth };
    });
    ok(`mobile #inquiry-form top ${st.top} >= bar bottom ${st.hb} - 2`, st.top >= st.hb - 2 && st.top < 200);
    ok('mobile no horizontal overflow', st.overflow <= 0);
    await ctx.close();
  }

  console.log('--- 5. prefers-reduced-motion: instant jump ---');
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const page = await ctx.newPage();
    await page.goto(BASE + '/', { waitUntil: 'networkidle' });
    await dismissCookie(page);
    await scrollToTop(page);
    await page.click('.sf-header .sf-quote-cta');
    await page.waitForTimeout(60);
    const y1 = await page.evaluate(() => Math.round(scrollY));
    await page.waitForTimeout(400);
    const y2 = await page.evaluate(() => Math.round(scrollY));
    ok(`reduced-motion lands immediately (${y1} ~ ${y2})`, y1 > 100 && Math.abs(y1 - y2) <= 2);
    await ctx.close();
  }

  console.log('--- 6. about "Book a Factory Tour" fixed ---');
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    await page.goto(BASE + '/about/', { waitUntil: 'networkidle' });
    await dismissCookie(page);
    const link = page.locator('a:has-text("Book a Factory Tour")').first();
    ok('about factory-tour button has href', await link.count() && (await link.getAttribute('href')) === '/factory-tour/');
    await link.click();
    await page.waitForURL('**/factory-tour/', { timeout: 8000 }).catch(() => {});
    ok('click navigates to /factory-tour/', page.url().includes('/factory-tour/'));
    await ctx.close();
  }

  console.log('--- 7. Download Catalog untouched ---');
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'networkidle' });
    await dismissCookie(page);
    const href = await page.locator('a:has-text("Download Catalog")').first().getAttribute('href');
    ok('Download Catalog still href="#" (untouched)', href === '#');
    await ctx.close();
  }

  await browser.close();
  console.log(`\nRESULT ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
