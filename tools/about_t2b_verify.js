/* Task 2 (rebuild): 8-milestone journey + hover effects.
   Checks geometry (all years inline), the real .sf-journey__dot node, the rail
   segments, hover scale on the group + node, horizontal overflow, the cleared
   stagger delay, and the reduced-motion escape hatch. Writes tools/_about_t2b.json
   and screenshots to screenshots/about-t2b/. */
const fs = require('fs');
const path = require('path');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const URL = 'http://sinofresh.local/about/';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/about-t2b';
const out = {};

const GEOM = () => {
  const wrap = document.querySelector('.sf-journey');
  const sec = (() => { let s = wrap; while (s && !s.matches('.wp-site-blocks > *')) s = s.parentElement; return s; })();
  const items = [...wrap.querySelectorAll('.sf-journey__item')];
  const rows = items.map((it, i) => {
    const yr = it.querySelector('.sf-journey__year');
    const h3 = it.querySelector('h3');
    const dot = it.querySelector('.sf-journey__dot');
    const ir = it.getBoundingClientRect(), pr = yr.getBoundingClientRect(), hr = h3.getBoundingClientRect();
    const dr = dot ? dot.getBoundingClientRect() : null;
    const dc = dot ? getComputedStyle(dot) : null;
    const after = getComputedStyle(it, '::after');
    return {
      i, year: yr.textContent.trim(), title: h3.textContent.trim(),
      gapTop: +(pr.top - hr.top).toFixed(1),
      sameLine: Math.abs(pr.top - hr.top) < 6,
      itemLeft: +ir.left.toFixed(1), itemW: +ir.width.toFixed(1), itemRight: +ir.right.toFixed(1), rowH: +ir.height.toFixed(1),
      yearLeft: +pr.left.toFixed(1), yearRel: +(pr.left - ir.left).toFixed(1), yearW: +pr.width.toFixed(1),
      dotLeft: dr ? +dr.left.toFixed(1) : null, dotRel: dr ? +(dr.left - ir.left).toFixed(1) : null,
      dotTop: dr ? +(dr.top - ir.top).toFixed(1) : null, dotW: dr ? +dr.width.toFixed(1) : null,
      dotH: dr ? +dr.height.toFixed(1) : null,
      dotPos: dc ? dc.position : null, dotBg: dc ? dc.backgroundColor : null, dotBorder: dc ? dc.borderTopWidth + ' ' + dc.borderTopColor : null,
      dotTransition: dc ? dc.transitionDuration : null,
      rail: { display: after.display, left: after.left, width: after.width, top: after.top, bottom: after.bottom, bg: after.backgroundColor },
      delayInline: it.style.transitionDelay || ''
    };
  });
  const h = document.documentElement;
  return {
    rows,
    wrapCls: wrap.className,
    dotCount: wrap.querySelectorAll('.sf-journey__dot').length,
    itemCount: items.length,
    itemTransition: getComputedStyle(items[0]).transitionDuration + ' / ' + getComputedStyle(items[0]).transition,
    transformOrigin: getComputedStyle(items[0]).transformOrigin,
    journeySectionH: +sec.getBoundingClientRect().height.toFixed(1),
    sections: [...document.querySelectorAll('.wp-site-blocks > *')].map(s => ({ cls: (s.className || '').slice(0, 38), h: +s.getBoundingClientRect().height.toFixed(1) })),
    docH: h.scrollHeight, hScroll: h.scrollWidth - h.clientWidth
  };
};

const HOVER = (idx) => {
  const items = [...document.querySelectorAll('.sf-journey__item')];
  const it = items[idx];
  const dot = it.querySelector('.sf-journey__dot');
  const ir = it.getBoundingClientRect();
  const h = document.documentElement;
  return {
    idx,
    itemTransform: getComputedStyle(it).transform,
    dotTransform: getComputedStyle(dot).transform,
    itemW: +ir.width.toFixed(1), itemRight: +ir.right.toFixed(1),
    viewport: innerWidth, hScroll: h.scrollWidth - h.clientWidth,
    dotW: +dot.getBoundingClientRect().width.toFixed(1)
  };
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });

  for (const w of [1440, 375]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    await page.goto(URL, { waitUntil: 'networkidle' });
    const reject = page.locator('button:has-text("Reject Non-Essential")');
    if (await reject.count()) await reject.first().click({ force: true }).catch(() => {});
    // pre-scroll to force every lazy image and to trip the reveal observers
    await page.evaluate(async () => {
      const s = Math.round(innerHeight * 0.8);
      for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 80)); }
      scrollTo(0, 0);
    });
    await page.waitForTimeout(1800);
    const rec = { geom: await page.evaluate(GEOM) };

    // hover the middle row, then the last one (right-edge / overflow check)
    for (const idx of [3, 7]) {
      await page.locator('.sf-journey > .sf-journey__item').nth(idx).scrollIntoViewIfNeeded();
      await page.locator('.sf-journey > .sf-journey__item').nth(idx).hover({ force: true });
      await page.waitForTimeout(420);
      rec['hover' + idx] = await page.evaluate(HOVER, idx);
      await page.screenshot({ path: path.join(OUT, `hover_${idx}_${w}.png`) });
      await page.mouse.move(2, 2);
      await page.waitForTimeout(300);
    }

    // section screenshot
    await page.locator('.sf-journey').first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    const sec = page.locator('section.wp-block-group:has(h2:text-is("Our Journey"))').first();
    await sec.screenshot({ path: path.join(OUT, `journey_${w}.png`), animations: 'disabled' });
    out[w] = rec;
    await ctx.close();
  }

  // reduced motion
  {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
    const page = await ctx.newPage();
    await page.goto(URL, { waitUntil: 'networkidle' });
    await page.locator('.sf-journey').first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(800);
    await page.locator('.sf-journey > .sf-journey__item').nth(2).hover({ force: true });
    await page.waitForTimeout(420);
    out.reducedMotion = await page.evaluate(() => {
      const wrap = document.querySelector('.sf-journey');
      const items = [...wrap.querySelectorAll('.sf-journey__item')];
      const it = items[2], dot = it.querySelector('.sf-journey__dot');
      return {
        live: wrap.classList.contains('sf-journey--live'),
        opacities: items.map(e => getComputedStyle(e).opacity),
        hoverItemTransform: getComputedStyle(it).transform,
        hoverDotTransform: getComputedStyle(dot).transform,
        itemTransition: getComputedStyle(it).transitionDuration,
        dotTransition: getComputedStyle(dot).transitionDuration
      };
    });
    await ctx.close();
  }

  // script scope + assets
  {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    const scripts = [];
    for (const p of ['/about/', '/', '/products/', '/quality/']) {
      await page.goto('http://sinofresh.local' + p, { waitUntil: 'domcontentloaded' });
      scripts.push({ p, about: await page.evaluate(() => [...document.scripts].filter(s => /about\.js/.test(s.src)).length) });
    }
    out.scripts = scripts;
    await ctx.close();
  }

  await b.close();
  fs.writeFileSync('/Users/meng/WorkBuddy/sinofresh外贸网站建设/tools/_about_t2b.json', JSON.stringify(out, null, 1));
  console.log('done');
})();
