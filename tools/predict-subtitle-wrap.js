// Predict how the map subtitle re-wraps after adding HACCP + BRC.
// Non-destructive: only mutates the in-memory DOM copy.
const { chromium } = require('playwright-core');
const fs = require('fs');

const EXEC = '/Users/meng/.agent-browser/browsers/chrome-153.0.8010.36/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/cert-subtitle';
const URL = 'http://sinofresh.local/';
const NEW = 'Exporting to 4 Continents · 30+ Countries · FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC';

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ executablePath: EXEC, headless: true });
  const out = {};

  for (const vp of [{ name: 'desktop', width: 1440, height: 900 }, { name: 'mobile', width: 375, height: 812 }]) {
    const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    await page.goto(URL, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(async () => {
      const h = document.body.scrollHeight;
      for (let y = 0; y < h; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 30)); }
      window.scrollTo(0, 0); await new Promise(r => setTimeout(r, 250));
    });

    const measure = () => page.evaluate(() => {
      const subs = [...document.querySelectorAll('section p')].filter(p => (p.textContent || '').startsWith('Exporting to 4 Continents'));
      const p = subs[0];
      if (!p) return null;
      const cs = getComputedStyle(p);
      const lh = parseFloat(cs.lineHeight) || 0;
      const r = p.getBoundingClientRect();
      // count visual lines via Range client rects (dedupe by top)
      const range = document.createRange(); range.selectNodeContents(p);
      const tops = new Set([...range.getClientRects()].map(x => Math.round(x.top)));
      return {
        text: p.textContent.trim(),
        renderedWidthPx: +r.width.toFixed(1),
        boxHeight: +r.height.toFixed(1),
        lineHeight: +lh.toFixed(1),
        fontSize: cs.fontSize,
        lines: tops.size,
        scrollW: document.documentElement.scrollWidth,
        clientW: document.documentElement.clientWidth,
        docH: document.documentElement.scrollHeight,
      };
    });

    const before = await measure();

    // crop shot of the subtitle strip (before)
    const sub = page.locator('section p', { hasText: 'Exporting to 4 Continents' }).first();
    await sub.scrollIntoViewIfNeeded();
    await page.waitForTimeout(200);
    await sub.screenshot({ path: `${OUT}/${vp.name}-subtitle-before.png` });

    // mutate in memory → after
    await page.evaluate((newText) => {
      const p = [...document.querySelectorAll('section p')].find(x => (x.textContent || '').startsWith('Exporting to 4 Continents'));
      p.textContent = newText;
    }, NEW);
    await page.waitForTimeout(150);
    const after = await measure();
    await sub.screenshot({ path: `${OUT}/${vp.name}-subtitle-after.png` });

    // full section for context
    const sec = page.locator('section:has(> p.sf-eyebrow:text-is("Export footprint"))').first();
    await sec.screenshot({ path: `${OUT}/${vp.name}-section-after.png` });

    out[vp.name] = { before, after };
    await ctx.close();
  }

  await browser.close();
  fs.writeFileSync(`${OUT}/predict-report.json`, JSON.stringify(out, null, 2));
  for (const k of Object.keys(out)) {
    const b = out[k].before, a = out[k].after;
    console.log(`\n== ${k} ==`);
    console.log(` before: lines=${b.lines} boxH=${b.boxHeight} lineH=${b.lineHeight} fs=${b.fontSize} textW=${b.renderedWidthPx} docH=${b.docH} overflow=${b.scrollW - b.clientW}`);
    console.log(` after : lines=${a.lines} boxH=${a.boxHeight} lineH=${a.lineHeight} fs=${a.fontSize} textW=${a.renderedWidthPx} docH=${a.docH} overflow=${a.scrollW - a.clientW}`);
    console.log(` after text: ${a.text}`);
  }
})();
