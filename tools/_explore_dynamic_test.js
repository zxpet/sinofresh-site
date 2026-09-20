/*
 * Stage C — [sf_explore_chips] cross-sell chips.
 *
 * Covers: 8 dynamic links in menu_order, current-page highlight, one-row
 * layout at 1440, horizontal scroll at 375 with no page overflow, and real
 * click-through navigation (soft-chews chip -> tablets page, whose own chip
 * is then highlighted).
 *
 * Run: NODE_PATH=/Users/meng/.workbuddy/binaries/node/workspace/node_modules \
 *      node tools/_explore_dynamic_test.js
 */
const { chromium } = require('playwright-core');
const fs = require('fs');

const BASE = 'http://sinofresh.local';
const SHOTS = 'screenshots';
const EXPECT = [
  ['Soft Chews', '/products/soft-chews/'],
  ['Tablets', '/products/tablets/'],
  ['Powders', '/products/powders/'],
  ['Pastes', '/products/pastes/'],
  ['Drops', '/products/drops/'],
  ['Liquids', '/products/liquids/'],
  ['Fish Oil', '/products/fish-oil/'],
  ['Dental Chews', '/products/dental-chews/'],
];

let pass = 0, fail = 0;
const ok = (label, cond) => {
  if (cond) { pass++; console.log('PASS ' + label); }
  else { fail++; console.log('FAIL ' + label); }
};

async function dismissCookie(page) {
  const btn = page.locator('#cookie-accept, .sf-cookie__accept, [data-cookie-accept]').first();
  if (await btn.count() && await btn.isVisible().catch(() => false)) {
    await btn.click().catch(() => {});
    await page.waitForTimeout(200);
  }
}

async function chipFacts(page) {
  return page.evaluate(() => {
    const nav = document.querySelector('.sf-explore__chips');
    if (!nav) return null;
    const chips = [...nav.querySelectorAll('.sf-explore__chip')];
    const navR = nav.getBoundingClientRect();
    return {
      count: chips.length,
      texts: chips.map((c) => c.textContent.trim()),
      hrefs: chips.map((c) => c.getAttribute('href')),
      current: chips.filter((c) => c.classList.contains('is-current')).map((c) => c.textContent.trim()),
      ariaCurrent: chips.filter((c) => c.getAttribute('aria-current') === 'page').map((c) => c.textContent.trim()),
      // one row == every chip shares the same top offset
      tops: chips.map((c) => Math.round(c.getBoundingClientRect().top)),
      navScrollW: nav.scrollWidth,
      navClientW: nav.clientWidth,
      navOverflowX: getComputedStyle(nav).overflowX,
      navFlexWrap: getComputedStyle(nav).flexWrap,
      navTop: Math.round(navR.top),
      inOptionsColumn: !!nav.closest('.configurator__options'),
      chipRadius: getComputedStyle(chips[0]).borderRadius,
      chipBorder: getComputedStyle(chips[0]).borderTopWidth,
      currentBg: (() => {
        const c = chips.find((x) => x.classList.contains('is-current'));
        return c ? getComputedStyle(c).backgroundColor : null;
      })(),
      plainBg: (() => {
        const c = chips.find((x) => !x.classList.contains('is-current'));
        return c ? getComputedStyle(c).backgroundColor : null;
      })(),
      docScrollW: document.documentElement.scrollWidth,
      winW: window.innerWidth,
    };
  });
}

(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch();

  /* ---------- desktop 1440 ---------- */
  const dctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await dctx.newPage();
  await page.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
  await page.waitForTimeout(700);
  await dismissCookie(page);
  await page.evaluate(() => document.fonts.ready);

  const d = await chipFacts(page);
  ok('desktop: chips nav present', !!d);
  ok('desktop: 8 chips', d.count === 8);
  ok('desktop: labels in menu_order', JSON.stringify(d.texts) === JSON.stringify(EXPECT.map((e) => e[0])));
  ok('desktop: hrefs point at each dosage page', JSON.stringify(d.hrefs.map((h) => new URL(h).pathname)) === JSON.stringify(EXPECT.map((e) => e[1])));
  ok('desktop: exactly one is-current', d.current.length === 1 && d.current[0] === 'Soft Chews');
  ok('desktop: is-current carries aria-current', d.ariaCurrent.length === 1 && d.ariaCurrent[0] === 'Soft Chews');
  ok('desktop: all 8 chips share one row (same top offset)', new Set(d.tops).size === 1);
  ok('desktop: nav does not overflow the band', d.navScrollW <= d.navClientW + 1);
  ok('desktop: no page-level horizontal overflow', d.docScrollW <= d.winW + 1);
  ok('desktop: chip is an outline pill (6px radius + 1px border)', d.chipRadius === '6px' && d.chipBorder === '1px');
  ok('desktop: current chip visually distinct from plain chips', d.currentBg !== d.plainBg);
  ok('desktop: band still lives in the options column', d.inOptionsColumn);
  console.log('     facts: currentBg=' + d.currentBg + ' plainBg=' + d.plainBg + ' navW=' + d.navClientW + ' scrollW=' + d.navScrollW);

  await page.locator('.sf-explore').scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);
  await page.locator('.sf-explore').screenshot({ path: `${SHOTS}/explore-stageC-desktop-band.png` });
  await page.screenshot({ path: `${SHOTS}/explore-stageC-desktop.png` });

  /* ---------- real click navigation ---------- */
  const before = page.url();
  await Promise.all([
    page.waitForURL('**/products/tablets/', { timeout: 15000 }),
    page.locator('.sf-explore__chip', { hasText: 'Tablets' }).click(),
  ]);
  await page.waitForTimeout(600);
  ok('click: navigated away from soft-chews', page.url() !== before);
  ok('click: landed on /products/tablets/', page.url().endsWith('/products/tablets/'));
  const after = await chipFacts(page);
  ok('click: tablets page shows itself as current', after.current.length === 1 && after.current[0] === 'Tablets');
  ok('click: soft-chews chip is no longer current', !after.current.includes('Soft Chews'));
  await page.locator('.sf-explore').scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${SHOTS}/explore-stageC-click-tablets.png` });

  /* ---------- edge: last chip ---------- */
  await page.goto(BASE + '/products/dental-chews/', { waitUntil: 'load' });
  await page.waitForTimeout(600);
  const last = await chipFacts(page);
  ok('edge: last page (dental-chews) highlights correctly', last.current.length === 1 && last.current[0] === 'Dental Chews');
  await dctx.close();

  /* ---------- mid width 1024: graceful degradation ---------- */
  const mctx1 = await browser.newContext({ viewport: { width: 1024, height: 800 } });
  const p1 = await mctx1.newPage();
  await p1.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
  await p1.waitForTimeout(600);
  const mid = await chipFacts(p1);
  ok('1024: no page-level horizontal overflow', mid.docScrollW <= mid.winW + 1);
  console.log('     1024px rows=' + new Set(mid.tops).size + ' (wraps gracefully, still all 8 visible)');
  await mctx1.close();

  /* ---------- mobile 375 ---------- */
  const mctx = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  const mpage = await mctx.newPage();
  await mpage.goto(BASE + '/products/soft-chews/', { waitUntil: 'load' });
  await mpage.waitForTimeout(700);
  await dismissCookie(mpage);
  await mpage.evaluate(() => document.fonts.ready);

  const m = await chipFacts(mpage);
  ok('mobile: 8 chips present', m.count === 8);
  ok('mobile: row does not wrap (nowrap)', m.navFlexWrap === 'nowrap');
  ok('mobile: row scrolls horizontally', m.navOverflowX === 'auto' && m.navScrollW > m.navClientW + 4);
  ok('mobile: no page-level horizontal overflow', m.docScrollW <= m.winW + 1);
  ok('mobile: current chip still marked', m.current.length === 1 && m.current[0] === 'Soft Chews');
  console.log('     facts: navClientW=' + m.navClientW + ' navScrollW=' + m.navScrollW + ' docScrollW=' + m.docScrollW + ' winW=' + m.winW);

  /* screenshots of the initial state first — the swipe below moves the row */
  await mpage.locator('.sf-explore').scrollIntoViewIfNeeded();
  await mpage.waitForTimeout(400);
  await mpage.locator('.sf-explore').screenshot({ path: `${SHOTS}/explore-stageC-mobile-band.png` });
  await mpage.screenshot({ path: `${SHOTS}/explore-stageC-mobile.png` });

  /* swipe the row and confirm it actually moves. Playwright's mouse does not
     drive native overflow scrolling, so dispatch real touch events over CDP
     — the same input path a finger takes. */
  await mpage.locator('.sf-explore').scrollIntoViewIfNeeded();
  await mpage.waitForTimeout(300);
  const navBox = await mpage.locator('.sf-explore__chips').boundingBox();
  const client = await mctx.newCDPSession(mpage);
  const y = Math.round(navBox.y + navBox.height / 2);
  const from = Math.round(navBox.x + navBox.width - 25);
  const to = Math.round(navBox.x + 25);
  await client.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: from, y }] });
  for (let i = 1; i <= 12; i++) {
    await client.send('Input.dispatchTouchEvent', {
      type: 'touchMove',
      touchPoints: [{ x: Math.round(from - (from - to) * (i / 12)), y }],
    });
    await mpage.waitForTimeout(16);
  }
  await client.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await mpage.waitForTimeout(500);
  const swipeScroll = await mpage.evaluate(() => document.querySelector('.sf-explore__chips').scrollLeft);
  ok('mobile: real touch swipe scrolls the row', swipeScroll > 10);

  /* the row is native overflow: programmatic scroll must work regardless of
     which input device is driving it (trackpad, keyboard, scrollbar) */
  const progScroll = await mpage.evaluate(() => {
    const nav = document.querySelector('.sf-explore__chips');
    nav.scrollLeft = 60;
    return nav.scrollLeft;
  });
  ok('mobile: row is natively scrollable (programmatic scroll sticks)', progScroll >= 55);
  console.log('     after touch swipe scrollLeft=' + swipeScroll + ', programmatic=' + progScroll);

  await mctx.close();

  await browser.close();
  console.log(`\n[stage C explore] ${pass} PASS / ${fail} FAIL`);
  process.exit(fail ? 1 : 0);
})();
