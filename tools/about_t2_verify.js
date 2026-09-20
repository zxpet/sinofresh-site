const path = require('path');
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/Workbuddy/sinofresh外贸网站建设/screenshots/about-t2';

const measure = () => {
  const secs = [...document.querySelectorAll('.wp-site-blocks > *')];
  const findSec = (kw) => secs.find((s) => { const h = s.querySelector('h2'); return h && h.textContent.trim().toLowerCase().includes(kw); });
  const j = findSec('journey');
  const rows = [...document.querySelectorAll('.sf-journey__item')].map((el, i) => {
    const p = el.querySelector('.sf-journey__year');
    const h3 = el.querySelector('h3');
    const body = el.querySelector('.sf-journey__body');
    const dot = getComputedStyle(el, '::before');
    const r = el.getBoundingClientRect();
    return {
      i, year: p.textContent.trim(), title: h3.textContent.trim(),
      sameLine: Math.abs(p.getBoundingClientRect().top - h3.getBoundingClientRect().top) < 3,
      yearLeft: +p.getBoundingClientRect().left.toFixed(1),
      bodyLeft: +h3.getBoundingClientRect().left.toFixed(1),
      bodyW: +body.getBoundingClientRect().width.toFixed(1),
      rowH: +r.height.toFixed(1),
      dot: { w: dot.width, h: dot.height, border: dot.borderTopWidth + ' ' + dot.borderTopColor, bg: dot.backgroundColor, top: dot.top, left: dot.left },
      opacity: getComputedStyle(el).opacity
    };
  });
  const jr = j ? j.getBoundingClientRect() : null;
  const rail = j ? getComputedStyle(j, '::before') : null;
  const hs = {};
  secs.forEach((s) => { const h = s.querySelector('h2'); const k = h ? h.textContent.trim().slice(0, 24) : '(no h2)'; hs[k] = +s.getBoundingClientRect().height.toFixed(1); });
  return {
    journeySectionH: jr ? +jr.height.toFixed(1) : null,
    rail: rail ? { content: rail.content, left: rail.left, width: rail.width, top: rail.top, bottom: rail.bottom } : null,
    rows,
    hScroll: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    docH: document.documentElement.scrollHeight,
    sections: hs
  };
};

(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  fs.mkdirSync(OUT, { recursive: true });
  const report = {};

  for (const w of [1440, 375]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    await page.goto('http://sinofresh.local/about/', { waitUntil: 'networkidle' });
    await page.evaluate(async () => { const s = Math.round(innerHeight * 0.8); for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise((r) => setTimeout(r, 70)); } scrollTo(0, 0); });
    await page.waitForTimeout(700);
    report[w] = await page.evaluate(measure);
    const sec = page.locator('.wp-site-blocks > *').filter({ has: page.locator('h2:text-matches("Our Journey", "i")') }).first();
    await sec.screenshot({ path: path.join(OUT, `journey_${w}.png`), animations: 'disabled' });
    await ctx.close();
  }

  // reduced-motion branch
  const ctxR = await b.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const pr = await ctxR.newPage();
  await pr.goto('http://sinofresh.local/about/', { waitUntil: 'networkidle' });
  await pr.waitForTimeout(500);
  report.reducedMotion = await pr.evaluate(() => ({
    live: !!document.querySelector('.sf-journey--live'),
    opacities: [...document.querySelectorAll('.sf-journey__item')].map((e) => getComputedStyle(e).opacity),
    transforms: [...document.querySelectorAll('.sf-journey__item')].map((e) => getComputedStyle(e).transform)
  }));
  await ctxR.close();

  // about.js must not load anywhere else
  const ctxO = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const po = await ctxO.newPage();
  report.scripts = {};
  for (const p of ['/about/', '/', '/products/', '/quality/', '/faq/', '/contact/']) {
    await po.goto('http://sinofresh.local' + p, { waitUntil: 'networkidle' });
    report.scripts[p] = await po.evaluate(() => [...document.querySelectorAll('script[src*="about.js"]')].length);
  }
  await ctxO.close();

  await b.close();
  fs.writeFileSync('/Users/meng/Workbuddy/sinofresh外贸网站建设/tools/_about_t2.json', JSON.stringify(report, null, 1));
  console.log(JSON.stringify(report, null, 1));
})();
