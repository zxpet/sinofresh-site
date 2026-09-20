// Post-change verification: geometry + screenshots for both batches.
const { chromium } = require('playwright-core');
const fs = require('fs');

const EXEC = '/Users/meng/.agent-browser/browsers/chrome-153.0.8010.36/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/combined-verify';
const URL = 'http://sinofresh.local/';

const FIND = {
  mapSub: `[...document.querySelectorAll('section p')].find(x => x.textContent.trim().startsWith('Exporting to 4 Continents'))`,
  heroSub: `[...document.querySelectorAll('p.sf-slide__subtitle')].find(x => x.textContent.includes('OEM/ODM manufacturer'))`,
  aboutChk: `[...document.querySelectorAll('p')].find(x => x.innerHTML.includes('✓') && x.textContent.includes('FDA registered, cGMP'))`,
  faqAns: `[...document.querySelectorAll('p')].find(x => x.textContent.trim().startsWith('FDA registration, cGMP, ISO 9001'))`,
  footBlurb: `[...document.querySelectorAll('p')].find(x => x.textContent.includes('Private label pet supplement manufacturer'))`,
  mapSection: `[...document.querySelectorAll('section')].find(x => x.querySelector(':scope > p.sf-eyebrow') && x.querySelector(':scope > p.sf-eyebrow').textContent.trim() === 'Export footprint')`,
  aboutSection: `[...document.querySelectorAll('section')].find(x => x.querySelector('h2') && x.querySelector('h2').textContent.trim() === 'About SINO FRESH')`,
};

const lineInfo = (expr) => `(() => {
  const el = ${expr};
  if (!el) return null;
  const cs = getComputedStyle(el);
  const range = document.createRange(); range.selectNodeContents(el);
  const tops = new Set([...range.getClientRects()].map(x => Math.round(x.top)));
  const r = el.getBoundingClientRect();
  return { text: el.textContent.replace(/\\s+/g,' ').trim(), lines: tops.size, h: +r.height.toFixed(1), w: +r.width.toFixed(1), lh: +(parseFloat(cs.lineHeight)||0).toFixed(1), fs: cs.fontSize };
})()`;

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ executablePath: EXEC, headless: true });
  const report = {};

  for (const vp of [{ name: 'desktop', width: 1440, height: 900 }, { name: 'mobile', width: 375, height: 812 }]) {
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    await page.goto(URL, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(async () => {
      const h = document.body.scrollHeight;
      for (let y = 0; y < h; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 25)); }
      window.scrollTo(0, 0); await new Promise(r => setTimeout(r, 300));
    });

    const geo = await page.evaluate((F) => {
      const bad = [];
      const cw = document.documentElement.clientWidth;
      document.querySelectorAll('body *').forEach(el => {
        if (el.closest('.sf-marquee__track, .sf-stories__group, .sf-hero-track, .wp-block-cover.sf-slide, .sf-hero-slider')) return;
        const b = el.getBoundingClientRect();
        if (b.width > 0 && (b.right > cw + 1 || b.left < -1)) bad.push({ tag: el.tagName, cls: (el.className||'').toString().slice(0,60), l:+b.left.toFixed(1), r:+b.right.toFixed(1) });
      });
      const sec = eval(F.mapSection);
      const slot = sec && sec.querySelector('.sf-slot--map');
      const svg = sec && sec.querySelector('svg.sf-map');
      const regions = sec && sec.querySelector('.sf-map__regions');
      const h2 = sec && sec.querySelector('h2');
      const sub = sec && h2 && h2.nextElementSibling;
      const r = el => { if (!el) return null; const b = el.getBoundingClientRect(); return { top: +(b.top+scrollY).toFixed(1), h: +b.height.toFixed(1), w: +b.width.toFixed(1) }; };
      return {
        docH: document.documentElement.scrollHeight,
        overflowX: document.documentElement.scrollWidth - cw,
        offenders: bad.slice(0, 8),
        mapSection: r(sec), mapSlot: r(slot), svg: r(svg), regions: r(regions),
        statsRow: !!(sec && sec.querySelector('.sf-map-stats')),
        statCards: sec ? sec.querySelectorAll('.wp-block-columns.sf-panel--4').length : -1,
        gap_svg_to_regions: (svg && regions) ? +(regions.getBoundingClientRect().top - svg.getBoundingClientRect().bottom).toFixed(1) : null,
      };
    }, FIND);

    const lines = {};
    for (const [k, expr] of Object.entries(FIND)) {
      if (!['mapSub','heroSub','aboutChk','faqAns','footBlurb'].includes(k)) continue;
      lines[k] = await page.evaluate(lineInfo(expr));
    }

    // FAQ needs <details> open to render & to screenshot meaningfully
    await page.evaluate(() => document.querySelectorAll('details').forEach(d => d.open = true));
    await page.waitForTimeout(200);

    const shots = [
      ['mapSection', 'map-section'],
      ['aboutSection', 'about-section'],
      ['faqAns', 'faq-answer'],
      ['footBlurb', 'footer-blurb'],
    ];
    for (const [k, name] of shots) {
      try {
        const h = await page.evaluateHandle(FIND[k]);
        const el = h.asElement();
        if (el) await el.screenshot({ path: `${OUT}/${vp.name}-${name}.png`, animations: 'disabled', timeout: 8000 });
      } catch (e) { console.error(`shot fail ${k}: ${e.message.split('\n')[0]}`); }
    }
    // hero needs the viewport at top
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(250);
    await page.screenshot({ path: `${OUT}/${vp.name}-hero.png`, animations: 'disabled' });
    try {
      const hh = await page.evaluateHandle(FIND.heroSub);
      const el = hh.asElement();
      if (el) await el.screenshot({ path: `${OUT}/${vp.name}-hero-subtitle.png`, animations: 'disabled', timeout: 8000 });
    } catch (e) { console.error(`hero crop fail: ${e.message.split('\n')[0]}`); }

    report[vp.name] = { geo, lines };
    await ctx.close();
  }

  await browser.close();
  fs.writeFileSync(`${OUT}/verify-report.json`, JSON.stringify(report, null, 2));
  for (const k of Object.keys(report)) {
    const { geo, lines } = report[k];
    console.log(`\n========== ${k} ==========`);
    console.log(`docH=${geo.docH} overflowX=${geo.overflowX} 地图section高=${geo.mapSection && geo.mapSection.h} 数字卡行存在=${geo.statsRow} 残留sf-panel--4=${geo.statCards}`);
    console.log(`svg=${JSON.stringify(geo.svg)} regions=${JSON.stringify(geo.regions)} 地图→大洲间距=${geo.gap_svg_to_regions}px`);
    for (const key of Object.keys(lines)) {
      const v = lines[key];
      console.log(`${key.padEnd(10)} lines=${v ? v.lines : '?'} h=${v ? v.h : '?'} w=${v ? v.w : '?'} fs=${v ? v.fs : '?'} | ${v ? v.text.slice(0, 95) : 'NOT FOUND'}`);
    }
    console.log('出屏元素:', geo.offenders.length ? JSON.stringify(geo.offenders) : '无 ✅');
  }
})();
