// Probe the homepage "Export footprint" map section geometry + screenshots.
// Usage: node probe-mapstats.js <label>   e.g. before | after
const { chromium } = require('playwright-core');
const fs = require('fs');

const EXEC = '/Users/meng/.agent-browser/browsers/chrome-153.0.8010.36/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/mapstats-removal';
const URL = 'http://sinofresh.local/';

(async () => {
  const label = process.argv[2] || 'probe';
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ executablePath: EXEC, headless: true });
  const report = {};

  for (const vp of [{ name: 'desktop', width: 1440, height: 900 }, { name: 'mobile', width: 375, height: 812 }]) {
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    await page.goto(URL, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    // scroll through the page once to force lazy loading + entrance animations
    await page.evaluate(async () => {
      const h = document.body.scrollHeight;
      for (let y = 0; y < h; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 40)); }
      window.scrollTo(0, 0);
      await new Promise(r => setTimeout(r, 300));
    });

    const sec = page.locator('section:has(> p.sf-eyebrow:text-is("Export footprint"))').first();
    const n = await sec.count();
    report[vp.name] = { sectionFound: n };
    if (n === 0) { await ctx.close(); continue; }
    await sec.scrollIntoViewIfNeeded();
    // wait for entrance animation to settle (opacity == 1)
    await page.waitForFunction(() => {
      const s = [...document.querySelectorAll('section')].find(x => x.querySelector(':scope > p.sf-eyebrow') && x.querySelector(':scope > p.sf-eyebrow').textContent.trim() === 'Export footprint');
      if (!s) return false;
      return getComputedStyle(s).opacity === '1';
    }, { timeout: 5000 }).catch(() => {});

    const geo = await page.evaluate(() => {
      const s = [...document.querySelectorAll('section')].find(x => x.querySelector(':scope > p.sf-eyebrow') && x.querySelector(':scope > p.sf-eyebrow').textContent.trim() === 'Export footprint');
      const r = el => { if (!el) return null; const b = el.getBoundingClientRect(); return { top: +(b.top + scrollY).toFixed(1), h: +b.height.toFixed(1), w: +b.width.toFixed(1) }; };
      const h2 = s.querySelector('h2');
      const sub = h2.nextElementSibling;
      const slot = s.querySelector('.sf-slot--map');
      const stats = s.querySelector('.sf-map-stats');
      const regions = s.querySelector('.sf-map__regions');
      const svg = s.querySelector('svg.sf-map');
      const cards = stats ? [...stats.querySelectorAll('.sf-cell')].map(c => (c.textContent || '').replace(/\s+/g, ' ').trim()) : [];
      const gap = (a, b) => (a && b) ? +(b.getBoundingClientRect().top - a.getBoundingClientRect().bottom).toFixed(1) : null;
      return {
        section: r(s),
        h2: r(h2), sub: r(sub),
        slot: r(slot), svg: r(svg),
        stats: r(stats), regions: r(regions),
        statsCount: stats ? stats.querySelectorAll(':scope > .wp-block-column').length : 0,
        cardTexts: cards,
        statsCols: stats ? getComputedStyle(stats).gridTemplateColumns : null,
        regionsCols: regions ? getComputedStyle(regions).gridTemplateColumns : null,
        regionsMarginTop: regions ? getComputedStyle(regions).marginTop : null,
        gap_svg_to_next: gap(svg, stats || regions),
        gap_stats_to_regions: gap(stats, regions),
        gap_sub_to_slot: gap(sub, slot),
        docH: document.documentElement.scrollHeight,
        docW: document.documentElement.scrollWidth,
        clientW: document.documentElement.clientWidth,
        overflowPx: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        offenders: (() => {
          const cw = document.documentElement.clientWidth;
          const bad = [];
          document.querySelectorAll('body *').forEach(el => {
            const b = el.getBoundingClientRect();
            if (b.width > 0 && (b.right > cw + 1 || b.left < -1)) {
              bad.push({ tag: el.tagName, cls: (el.className || '').toString().slice(0, 70), l: +b.left.toFixed(1), r: +b.right.toFixed(1) });
            }
          });
          return bad.slice(0, 12);
        })(),
      };
    });
    report[vp.name].geo = geo;

    await sec.screenshot({ path: `${OUT}/${label}-${vp.name}-section.png` });
    await page.screenshot({ path: `${OUT}/${label}-${vp.name}-viewport.png` });
    await ctx.close();
  }

  await browser.close();
  fs.writeFileSync(`${OUT}/${label}-report.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
})();
