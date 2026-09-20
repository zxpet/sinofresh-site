/* toc-nav E2E — covers the 14 acceptance items */
const { chromium } = require('playwright-core');
const BASE = 'http://sinofresh.local';
let pass = 0, fail = 0;
function ok(cond, name) {
  if (cond) { pass++; console.log('  PASS ' + name); }
  else { fail++; console.log('  FAIL ' + name); }
}

(async () => {
  const browser = await chromium.launch();

  /* ---------- desktop 1440: home ---------- */
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    await page.goto(BASE + '/', { waitUntil: 'load' });
    await page.evaluate(() => { const b = document.querySelector('.sf-cookie-banner'); if (b) b.style.display = 'none'; });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForSelector('.sf-toc', { timeout: 5000 });

    console.log('[1] home: rail present + geometry');
    ok(await page.locator('.sf-toc').count() === 1, 'home has .sf-toc');
    const geo = await page.evaluate(() => {
      const r = document.querySelector('.sf-toc').getBoundingClientRect();
      const cs = getComputedStyle(document.querySelector('.sf-toc'));
      const dots = document.querySelectorAll('.sf-toc li').length;
      return { right: Math.round(1440 - r.right), top: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height), pos: cs.position, z: cs.zIndex, dots };
    });
    ok(geo.pos === 'fixed', 'rail is position:fixed');
    ok(geo.right === 20, 'rail right offset = 20px (got ' + geo.right + ')');
    ok(Math.abs(geo.top + geo.h / 2 - 450) <= 2, 'rail vertically centered');
    ok(parseInt(geo.z) < 9998, 'rail z-index below float stack 9998');

    console.log('[6] home: 9 dots, skip list honoured');
    ok(geo.dots === 9, 'home dot count = 9 (got ' + geo.dots + ')');
    const labels = await page.evaluate(() => [...document.querySelectorAll('.sf-toc__label')].map(e => e.textContent.trim()));
    const expected = ['Our 8 Dosage Forms', 'Certifications & Registrations', 'Quality Control at Every Step', 'OEM & ODM Services', 'Cooperation Models', 'Client Stories', 'About SINO FRESH', 'Latest Articles', 'Frequently Asked Questions'];
    ok(JSON.stringify(labels) === JSON.stringify(expected), 'labels match expected 9');
    const skipped = labels.some(t => /^(Formulated Clean|From Inquiry to After-Sales|Trusted by 30\+|Ready to Launch)/i.test(t));
    ok(!skipped, 'no skipped H2 in rail');
    ok(await page.evaluate(() => document.querySelectorAll('.sf-toc-target').length === 9), '9 sf-toc-target ids injected');

    console.log('[5] fade at top');
    ok(await page.evaluate(() => document.querySelector('.sf-toc').classList.contains('sf-toc--hidden')), 'hidden class at scrollY=0');
    await page.evaluate(() => window.scrollTo(0, 1500));
    await page.waitForTimeout(400);
    ok(await page.evaluate(() => !document.querySelector('.sf-toc').classList.contains('sf-toc--hidden')), 'visible after scroll 1500');

    console.log('[2] highlight follows scroll');
    const curAt1500 = await page.evaluate(() => [...document.querySelectorAll('.sf-toc li')].findIndex(li => li.classList.contains('is-current')));
    ok(curAt1500 >= 0, 'one dot highlighted at 1500 (idx ' + curAt1500 + ')');
    await page.evaluate(() => window.scrollTo(0, 6000));
    await page.waitForTimeout(400);
    const curAt6000 = await page.evaluate(() => [...document.querySelectorAll('.sf-toc li')].findIndex(li => li.classList.contains('is-current')));
    ok(curAt6000 > curAt1500, 'highlight advances deeper (1500->6000: ' + curAt1500 + '->' + curAt6000 + ')');
    await page.evaluate(() => window.scrollTo(0, 1500));
    await page.waitForTimeout(400);
    const curBack = await page.evaluate(() => [...document.querySelectorAll('.sf-toc li')].findIndex(li => li.classList.contains('is-current')));
    ok(curBack === curAt1500, 'highlight returns on scroll-up');

    console.log('[3] click dot -> smooth scroll + hash');
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(300);
    await page.evaluate(() => document.querySelectorAll('.sf-toc li')[3].querySelector('a').click());
    await page.waitForTimeout(1800);
    const clickRes = await page.evaluate(() => {
      const target = document.querySelectorAll('.sf-toc-target')[3];
      return { top: Math.round(target.getBoundingClientRect().top), hash: location.hash, margin: getComputedStyle(target).scrollMarginTop };
    });
    ok(Math.abs(clickRes.top - 96) <= 8, 'target lands at 96px below header (got ' + clickRes.top + ')');
    ok(clickRes.hash === '#' + (await page.evaluate(() => document.querySelectorAll('.sf-toc-target')[3].id)), 'URL hash updated');
    ok(clickRes.margin === '96px', 'scroll-margin-top = 96px');
    const curAfterClick = await page.evaluate(() => [...document.querySelectorAll('.sf-toc li')].findIndex(li => li.classList.contains('is-current')));
    ok(curAfterClick === 3, 'clicked dot becomes current');

    console.log('[4] hover expands label');
    const dot3 = page.locator('.sf-toc li').nth(2).locator('a');
    await dot3.hover();
    await page.waitForTimeout(350);
    const hoverRes = await page.evaluate(() => {
      const a = document.querySelectorAll('.sf-toc li')[2].querySelector('a');
      const label = a.querySelector('.sf-toc__label');
      const dot = a.querySelector('.sf-toc__dot');
      const lr = label.getBoundingClientRect();
      const dr = dot.getBoundingClientRect();
      return { labelOp: getComputedStyle(label).opacity, dotTransform: getComputedStyle(dot).transform, labelRightOfDot: lr.right <= dr.left + 1, lr: Math.round(lr.width), visible: lr.width > 0 && lr.height > 0 };
    });
    ok(hoverRes.labelOp === '1', 'label opacity 1 on hover');
    ok(hoverRes.dotTransform !== 'none', 'dot scaled on hover');
    ok(hoverRes.visible && hoverRes.labelRightOfDot, 'label card left of dot, rendered');

    console.log('[11] no overlap with float stack');
    const overlap = await page.evaluate(() => {
      const t = document.querySelector('.sf-toc').getBoundingClientRect();
      const s = document.querySelector('.sf-float-stack').getBoundingClientRect();
      return !(t.bottom < s.top || s.bottom < t.top);
    });
    ok(!overlap, 'rail and float stack vertically disjoint');

    console.log('[14] screenshots (desktop)');
    await page.evaluate(() => window.scrollTo(0, 1500));
    await page.waitForTimeout(500);
    await page.screenshot({ path: '/tmp/navscan/toc-home-1440.png' });
    await dot3.hover();
    await page.waitForTimeout(350);
    await page.screenshot({ path: '/tmp/navscan/toc-home-hover-1440.png' });
    await ctx.close();
  }

  /* ---------- [7] other whitelisted pages ---------- */
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    const cases = [
      ['/quality/', 8], ['/about/', 6], ['/services/', 6], ['/factory-tour/', 6],
      ['/products/soft-chews/', 6], ['/products/tablets/', 6], ['/products/powders/', 6],
      ['/products/pastes/', 6], ['/products/drops/', 6], ['/products/liquids/', 6],
      ['/products/fish-oil/', 6], ['/products/dental-chews/', 6]
    ];
    for (const [path, n] of cases) {
      await page.goto(BASE + path, { waitUntil: 'load' });
      await page.waitForSelector('.sf-toc', { timeout: 5000 });
      const dots = await page.evaluate(() => document.querySelectorAll('.sf-toc li').length);
      ok(dots === n, path + ' -> ' + n + ' dots (got ' + dots + ')');
    }
    await ctx.close();
  }

  /* ---------- [8] non-whitelisted pages ---------- */
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    for (const path of ['/contact/', '/products/', '/blog/', '/faq/', '/feedback/', '/cooperation/']) {
      await page.goto(BASE + path, { waitUntil: 'load' });
      const res = await page.evaluate(() => ({ toc: !!document.querySelector('.sf-toc'), script: !!document.querySelector('script[src*="toc-nav"]') }));
      ok(!res.toc && !res.script, path + ' -> no TOC, script not enqueued');
    }
    await ctx.close();
  }

  /* ---------- [9] mobile 375 ---------- */
  {
    const ctx = await browser.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    const page = await ctx.newPage();
    await page.goto(BASE + '/', { waitUntil: 'load' });
    const res = await page.evaluate(() => {
      const t = document.querySelector('.sf-toc');
      return t ? { display: getComputedStyle(t).display } : { display: 'absent' };
    });
    ok(res.display === 'none' || res.display === 'absent', 'mobile 375: rail hidden (' + res.display + ')');
    await page.screenshot({ path: '/tmp/navscan/toc-mobile-375.png' });
    await ctx.close();
  }

  /* ---------- [10] prefers-reduced-motion ---------- */
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const page = await ctx.newPage();
    await page.goto(BASE + '/', { waitUntil: 'load' });
    await page.waitForSelector('.sf-toc');
    await page.evaluate(async () => {
      for (let y = 0; y <= document.body.scrollHeight; y += 800) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); }
      window.scrollTo(0, 0);
      await new Promise(r => setTimeout(r, 400));
    });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.evaluate(() => document.querySelectorAll('.sf-toc li')[4].querySelector('a').click());
    await page.waitForTimeout(250);
    const top = await page.evaluate(() => Math.round(document.querySelectorAll('.sf-toc-target')[4].getBoundingClientRect().top));
    ok(Math.abs(top - 96) <= 8, 'reduced-motion: instant jump to target (top ' + top + ')');
    await ctx.close();
  }

  console.log('\n=== RESULT: ' + pass + ' pass / ' + fail + ' fail ===');
  await browser.close();
  process.exit(fail ? 1 : 0);
})();
