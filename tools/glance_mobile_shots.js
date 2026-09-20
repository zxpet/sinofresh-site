/* Glance mobile-list verification: metrics + cropped screenshots.
   Usage: node glance_mobile_shots.js <before|after>                       */
const { chromium } = require('playwright-core');
const path = require('path');

const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/glance-mobile';
const tag = process.argv[2] || 'after';
const URL = 'http://sinofresh.local/';

async function ready(page) {
  await page.goto(URL, { waitUntil: 'domcontentloaded' });
  await page.evaluate(() =>
    localStorage.setItem('sf_cookie_consent', JSON.stringify({ necessary: true, marketing: false })));
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(500);
  // .sf-num carries a count-up animation that parks at "0" until the row is
  // 40% in view — scroll there and let the 1.5s tween finish before measuring.
  await page.evaluate(() => {
    const s = document.querySelector('.sf-stats');
    if (s) (s.closest('section') || s).scrollIntoView({ block: 'center' });
  });
  await page.waitForTimeout(2400);
  // belt and braces: if the observer has not fired yet, write the final figure
  // back from the count-up's own bookkeeping so shots are comparable.
  await page.evaluate(() => {
    document.querySelectorAll('.sf-num').forEach((el) => {
      if (el.field) el.textContent = el.field.head + el.field.to.toLocaleString('en-US') + el.field.tail;
    });
  });
}

const PROBE = () => {
  const sec = document.querySelector('.sf-stats');
  const section = sec ? sec.closest('section') : null;
  const cols = [...document.querySelectorAll('.wp-block-columns.sf-stats')];
  const cells = [...document.querySelectorAll('.wp-block-columns.sf-stats > .wp-block-column')];
  const first = cells[0];
  const num = first.querySelector('.sf-num');
  const ps = first.querySelectorAll('.wp-block-group > p');
  const label = ps[1];
  const sub = ps[2];
  const be = getComputedStyle(first, '::before');
  // combined height of all stats rows (row1 top -> row2 bottom)
  let top = null, bottom = null;
  cols.forEach((c) => {
    const r = c.getBoundingClientRect();
    if (top === null) top = r.top + window.scrollY;
    bottom = r.bottom + window.scrollY;
  });
  return {
    statsGrids: cols.map((c) => getComputedStyle(c).gridTemplateColumns.split(' ').length),
    cellCount: cells.length,
    cellDisplay: getComputedStyle(first).display,
    dot: be.content !== 'none'
      ? { w: be.width, h: be.height, bg: be.backgroundColor, radius: be.borderRadius, mt: be.marginTop }
      : null,
    numFS: getComputedStyle(num).fontSize,
    labelFS: label ? getComputedStyle(label).fontSize : null,
    labelText: label ? label.textContent.trim() : null,
    subFS: sub ? getComputedStyle(sub).fontSize : null,
    subDisplay: sub ? getComputedStyle(sub).display : null,
    cellH: Math.round(cells[0].getBoundingClientRect().height),
    statsBlockH: top !== null ? Math.round(bottom - top) : null,
    nums: cells.map((c) => c.querySelector('.sf-num').textContent.trim()),
    labels: cells.map((c) => c.querySelectorAll('.wp-block-group > p')[1].textContent.trim()),
    snapNums: [...document.querySelectorAll('.sf-snapshot__num')].map((n) => n.textContent.trim()),
    snapNumFS: document.querySelector('.sf-snapshot__num') ? getComputedStyle(document.querySelector('.sf-snapshot__num')).fontSize : null,
    snapRowW: document.querySelector('.sf-snapshot__row') ? Math.round(document.querySelector('.sf-snapshot__row').getBoundingClientRect().width) : null,
    cellOverflow: cells.some((c) => c.scrollWidth > c.clientWidth + 1),
    ov: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    y: section ? Math.round(section.getBoundingClientRect().top + window.scrollY) : 0,
    h: section ? Math.round(section.getBoundingClientRect().height) : 0,
  };
};

(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const [w, h, name] of [[1440, 900, '1440'], [768, 900, '768'], [420, 900, '420'], [375, 812, '375']]) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: w < 500, hasTouch: w < 500 });
    const p = await ctx.newPage();
    await ready(p);
    const m = await p.evaluate(PROBE);
    console.log(name, JSON.stringify(m));
    await p.screenshot({
      path: path.join(OUT, `${tag}-home-${name}-glance.png`),
      clip: { x: 0, y: m.y, width: w, height: Math.min(m.h + 20, 2800) },
      fullPage: true,
    });
    await ctx.close();
  }
  await b.close();
})();
