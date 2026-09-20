const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const GAL = () => {
  const g = document.querySelector('.sf-fac');
  if (!g) return { err: 'no gallery' };
  const cs = getComputedStyle(g);
  const items = [...g.querySelectorAll(':scope > figure')];
  const R = e => { const b = e.getBoundingClientRect(); return { x: +b.x.toFixed(1), y: +b.y.toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1), r: +(b.width / b.height).toFixed(3) }; };
  return {
    tag: g.tagName, cls: g.className,
    display: cs.display, tracks: cs.gridTemplateColumns.split(' ').length, gap: cs.rowGap,
    gW: +g.getBoundingClientRect().width.toFixed(1),
    itemCount: items.length,
    items: items.map(it => {
      const ics = getComputedStyle(it), im = it.querySelector('img'), imcs = getComputedStyle(im);
      return {
        box: R(it), display: ics.display, margin: ics.margin, radius: ics.borderRadius,
        border: ics.borderTopWidth + ' ' + ics.borderTopStyle, bg: ics.backgroundColor,
        overflow: ics.overflow, role: it.getAttribute('role'), tab: it.getAttribute('tabindex'),
        img: R(im), fit: imcs.objectFit, pos: imcs.objectPosition, transform: imcs.transform, t: imcs.transitionProperty + ' ' + imcs.transitionDuration,
        src: im.getAttribute('src').split('/').pop(), loading: im.getAttribute('loading')
      };
    }),
    docH: document.documentElement.scrollHeight, scrollW: document.documentElement.scrollWidth, innerW: innerWidth
  };
};

async function hoverShot(page, sel) {
  const el = await page.$(sel);
  await el.scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  const box = await el.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await el.scrollIntoViewIfNeeded();
  await page.waitForTimeout(420);
  return box;
}

(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });

  /* ---------------- desktop 1440 ---------------- */
  let ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  let page = await ctx.newPage();
  const errs = []; page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE ' + m.text()); });
  await page.goto('http://sinofresh.local/about/', { waitUntil: 'networkidle' });
  await page.evaluate(async () => { await document.fonts.ready; const s = Math.round(innerHeight * 0.8); for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } scrollTo(0, 0); });
  await page.waitForTimeout(900);
  const d = await page.evaluate(GAL);
  console.log('== 1440 gallery ==');
  console.log(JSON.stringify({ tag: d.tag, cls: d.cls, display: d.display, tracks: d.tracks, gap: d.gap, gW: d.gW, itemCount: d.itemCount, docH: d.docH, scrollW: d.scrollW }, null, 0));
  d.items.forEach(i => console.log(`  #${i.src} box=${JSON.stringify(i.box)} img=${JSON.stringify(i.img)} fit=${i.fit} radius=${i.radius} border=${i.border} bg=${i.bg} margin=${i.margin} ovf=${i.overflow} role=${i.role}/${i.tab} tr=${i.t}`));

  // hover state: item 0 must scale to 1.05
  const gsel = '.sf-fac > figure:nth-child(1)';
  await hoverShot(page, gsel);
  const hov = await page.evaluate((sel) => {
    const im = document.querySelector(sel + ' img');
    return { transform: getComputedStyle(im).transform, trans: getComputedStyle(im).transition, matches: im.matches(':hover') || im.closest('figure').matches(':hover') };
  }, gsel);
  console.log('hover state:', JSON.stringify(hov));
  await page.addStyleTag({ content: 'header,[class*="header"]{position:static!important;visibility:hidden!important}' });
  await page.evaluate(() => { document.querySelectorAll('body *').forEach(el => { if (getComputedStyle(el).position === 'fixed') el.style.display = 'none'; }); });
  const gel = await page.$('.sf-fac');
  await gel.scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);
  await gel.screenshot({ path: 'screenshots/t6_1440_grid_hover.png' });

  // lightbox flow
  await page.mouse.move(0, 0);
  await page.waitForTimeout(300);
  await page.click('.sf-fac > figure:nth-child(1)');
  await page.waitForTimeout(500);
  let lb = await page.evaluate(() => {
    const b = document.querySelector('.sf-lb');
    if (!b) return { err: 'no .sf-lb' };
    const img = b.querySelector('.sf-lb__img');
    const btn = b.querySelector('.sf-lb__btn--close');
    const cs = getComputedStyle(img);
    return { hidden: b.hidden, open: b.classList.contains('is-open'), src: img.getAttribute('src').split('/').pop(), alt: img.alt, count: b.querySelector('.sf-lb__count').textContent, focused: document.activeElement.className, imgBox: (r => ({ w: +r.width.toFixed(0), h: +r.height.toFixed(0) }))(img.getBoundingClientRect()), imgCss: { w: cs.width, h: cs.height, maxW: cs.maxWidth, maxH: cs.maxHeight }, nat: img.naturalWidth + 'x' + img.naturalHeight, attrs: img.getAttribute('width') + 'x' + img.getAttribute('height'), complete: img.complete, scrollLocked: getComputedStyle(document.documentElement).overflow, thumbsCurrent: document.querySelectorAll('.sf-fac .is-current').length };
  });
  console.log('== lightbox open ==', JSON.stringify(lb));
  await page.screenshot({ path: 'screenshots/t6_1440_lightbox.png' });

  await page.click('.sf-lb__btn--next'); await page.waitForTimeout(420);
  const lb2 = await page.evaluate(() => ({ src: document.querySelector('.sf-lb__img').getAttribute('src').split('/').pop(), count: document.querySelector('.sf-lb__count').textContent }));
  console.log('after next:', JSON.stringify(lb2));
  await page.click('.sf-lb__btn--prev'); await page.waitForTimeout(420);
  await page.click('.sf-lb__btn--prev'); await page.waitForTimeout(420);
  const lb3 = await page.evaluate(() => ({ src: document.querySelector('.sf-lb__img').getAttribute('src').split('/').pop(), count: document.querySelector('.sf-lb__count').textContent }));
  console.log('after prev x2 (wrap to 6/6):', JSON.stringify(lb3));

  await page.keyboard.press('Escape'); await page.waitForTimeout(500);
  const lb4 = await page.evaluate(() => ({ hidden: document.querySelector('.sf-lb').hidden, lock: document.documentElement.classList.contains('sf-lb-open'), focusBack: document.activeElement.getAttribute('aria-label') }));
  console.log('after Escape:', JSON.stringify(lb4));

  // backdrop click closes
  await page.click('.sf-fac > figure:nth-child(3)'); await page.waitForTimeout(450);
  await page.mouse.click(20, 20); await page.waitForTimeout(500);
  const lb5 = await page.evaluate(() => ({ hidden: document.querySelector('.sf-lb').hidden, lock: document.documentElement.classList.contains('sf-lb-open') }));
  console.log('after backdrop click:', JSON.stringify(lb5));

  // arrow keys + inert-selector check
  await page.click('.sf-fac > figure:nth-child(1)'); await page.waitForTimeout(400);
  await page.keyboard.press('ArrowRight'); await page.waitForTimeout(400);
  const lb6 = await page.evaluate(() => document.querySelector('.sf-lb__count').textContent);
  await page.keyboard.press('Escape'); await page.waitForTimeout(400);
  console.log('after ArrowRight:', lb6);

  const inert = await page.evaluate(() => {
    const sel = 'body.page-id-14 section:has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-border-light-border-color):has(figure)';
    const sel2 = 'body.page-id-14 section:has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-border-light-border-color):has(figure) > .wp-block-columns > .wp-block-column > .wp-block-group';
    return { section: document.querySelectorAll(sel).length, group: document.querySelectorAll(sel2).length, coreValues: document.querySelectorAll('body.page-id-14 .wp-block-columns:has(> .wp-block-column > .wp-block-group.has-border-light-border-color):not(:has(figure))').length };
  });
  console.log('inert-selector probe (1440):', JSON.stringify(inert));
  console.log('page errors:', JSON.stringify(errs));
  await ctx.close();

  /* ---------------- mobile 375 ---------------- */
  ctx = await b.newContext({ viewport: { width: 375, height: 760 }, deviceScaleFactor: 2 });
  page = await ctx.newPage();
  const errs2 = []; page.on('pageerror', e => errs2.push('PAGEERROR ' + e.message));
  await page.goto('http://sinofresh.local/about/', { waitUntil: 'networkidle' });
  await page.evaluate(async () => { await document.fonts.ready; const s = Math.round(innerHeight * 0.8); for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } scrollTo(0, 0); });
  await page.waitForTimeout(900);
  const m = await page.evaluate(GAL);
  console.log('== 375 gallery ==');
  console.log(JSON.stringify({ display: m.display, tracks: m.tracks, gap: m.gap, gW: m.gW, itemCount: m.itemCount, docH: m.docH, scrollW: m.scrollW, innerW: m.innerW }, null, 0));
  console.log('  item boxes:', JSON.stringify(m.items.map(i => i.box)));
  console.log('  img boxes :', JSON.stringify(m.items.map(i => i.img)));
  const inertM = await page.evaluate(() => ({ section: document.querySelectorAll('body.page-id-14 section:has(> .wp-block-columns > .wp-block-column > .wp-block-group.has-border-light-border-color):has(figure)').length }));
  console.log('inert-selector probe (375):', JSON.stringify(inertM));
  await page.addStyleTag({ content: 'header,[class*="header"]{position:static!important;visibility:hidden!important}' });
  await page.evaluate(() => { document.querySelectorAll('body *').forEach(el => { if (getComputedStyle(el).position === 'fixed') el.style.display = 'none'; }); });
  await (await page.$('.sf-fac')).screenshot({ path: 'screenshots/t6_375_grid.png' });
  await page.click('.sf-fac > figure:nth-child(1)');
  await page.waitForTimeout(600);
  const mlb = await page.evaluate(() => {
    const bb = document.querySelector('.sf-lb');
    const img = bb.querySelector('.sf-lb__img');
    const r = img.getBoundingClientRect();
    const btns = [...bb.querySelectorAll('.sf-lb__btn')].map(x => { const q = x.getBoundingClientRect(); return x.className.replace('sf-lb__btn ', '') + ':' + Math.round(q.x) + ',' + Math.round(q.y) + ' ' + Math.round(q.width) + 'x' + Math.round(q.height); });
    return { hidden: bb.hidden, src: img.getAttribute('src').split('/').pop(), count: bb.querySelector('.sf-lb__count').textContent, imgBox: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }, btns, overflowX: document.documentElement.scrollWidth > innerWidth };
  });
  console.log('== 375 lightbox ==', JSON.stringify(mlb));
  await page.screenshot({ path: 'screenshots/t6_375_lightbox.png' });
  await page.keyboard.press('Escape'); await page.waitForTimeout(450);
  console.log('375 after Escape hidden =', await page.evaluate(() => document.querySelector('.sf-lb').hidden));
  console.log('mobile page errors:', JSON.stringify(errs2));
  await ctx.close();
  await b.close();
})();
