// Predict re-wrap for the 5 cert-list locations after adding ", HACCP, BRC".
// Non-destructive: mutates only the in-memory DOM copy.
const { chromium } = require('playwright-core');
const fs = require('fs');

const EXEC = '/Users/meng/.agent-browser/browsers/chrome-153.0.8010.36/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/cert-subtitle';
const URL = 'http://sinofresh.local/';

// selector = JS expression returning the element; mutate = JS on element to apply new text
const TARGETS = [
  { key: '1-map-subtitle', label: '地图副标题',
    find: `[...document.querySelectorAll('section p')].find(x => x.textContent.trim().startsWith('Exporting to 4 Continents'))`,
    before: 'Exporting to 4 Continents · 30+ Countries · FDA, cGMP, ISO 9001, FSSC 22000',
    after: 'Exporting to 4 Continents · 30+ Countries · FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC',
    mode: 'text' },
  { key: '2-footer-blurb', label: '页脚简介',
    find: `[...document.querySelectorAll('footer p, .wp-block-template-part p')].find(x => x.textContent.includes('Private label pet supplement manufacturer'))`,
    before: 'Shandong SINO FRESH Pet Food Co., Ltd. — Private label pet supplement manufacturer with 8 dosage forms, FDA, cGMP, ISO 9001, FSSC 22000.',
    after: 'Shandong SINO FRESH Pet Food Co., Ltd. — Private label pet supplement manufacturer with 8 dosage forms, FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC.',
    mode: 'text' },
  { key: '3-hero-subtitle', label: 'Hero 副标题',
    find: `[...document.querySelectorAll('p.sf-slide__subtitle')].find(x => x.textContent.includes('OEM/ODM manufacturer'))`,
    before: 'OEM/ODM manufacturer for 8 dosage forms. FDA registered, cGMP, ISO 9001, FSSC 22000. Exporting to 30+ countries.',
    after: 'OEM/ODM manufacturer for 8 dosage forms. FDA registered, cGMP, ISO 9001, FSSC 22000, HACCP, BRC. Exporting to 30+ countries.',
    mode: 'text' },
  { key: '4-about-check', label: 'About 对勾',
    find: `[...document.querySelectorAll('p')].find(x => x.innerHTML.includes('✓') && x.textContent.includes('FDA registered, cGMP'))`,
    before: 'FDA registered, cGMP, ISO 9001, FSSC 22000',
    after: 'FDA registered, cGMP, ISO 9001, FSSC 22000, HACCP, BRC',
    mode: 'innerhtml' },
  { key: '5-faq-answer', label: 'FAQ 回答',
    find: `[...document.querySelectorAll('p')].find(x => x.textContent.trim().startsWith('FDA registration, cGMP, ISO 9001'))`,
    before: 'FDA registration, cGMP, ISO 9001, FSSC 22000.',
    after: 'FDA registration, cGMP, ISO 9001, FSSC 22000, HACCP, BRC.',
    mode: 'text' },
];

const measureFn = (findExpr) => `
  (() => {
    const el = ${findExpr};
    if (!el) return null;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const range = document.createRange(); range.selectNodeContents(el);
    const tops = new Set([...range.getClientRects()].map(x => Math.round(x.top)));
    const cw = document.documentElement.clientWidth;
    return {
      text: el.textContent.trim(),
      w: +r.width.toFixed(1), h: +r.height.toFixed(1),
      lineHeight: +(parseFloat(cs.lineHeight) || 0).toFixed(1),
      fontSize: cs.fontSize,
      lines: tops.size,
      parentW: +(el.parentElement.getBoundingClientRect().width).toFixed(1),
      overflowX: document.documentElement.scrollWidth - cw,
      docH: document.documentElement.scrollHeight,
      outside: r.left < -1 || r.right > cw + 1,
    };
  })()`;

const mutFn = (findExpr, mode, before, after) => `
  (() => {
    const el = ${findExpr};
    if (!el) return 'NOT_FOUND';
    if ('${mode}' === 'innerhtml') {
      if (!el.innerHTML.includes(${JSON.stringify(before)})) return 'TEXT_MISMATCH';
      el.innerHTML = el.innerHTML.replace(${JSON.stringify(before)}, ${JSON.stringify(after)});
    } else {
      if (!el.textContent.includes(${JSON.stringify(before)})) return 'TEXT_MISMATCH';
      el.textContent = ${JSON.stringify(after)};
    }
    return 'OK';
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
      window.scrollTo(0, 0); await new Promise(r => setTimeout(r, 250));
      document.querySelectorAll('details').forEach(d => d.open = true); // FAQ answers must be renderable
    });
    await page.waitForTimeout(200);

    report[vp.name] = {};
    const shotTargets = [];

    for (const t of TARGETS) {
      const before = await page.evaluate(measureFn(t.find));
      if (!before) { report[vp.name][t.key] = { error: 'element not found' }; continue; }
      const mutate = await page.evaluate(mutFn(t.find, t.mode, t.before, t.after));
      await page.waitForTimeout(120);
      const after = await page.evaluate(measureFn(t.find));
      report[vp.name][t.key] = { label: t.label, mutate, before, after };
      shotTargets.push({ ...t, afterMeasured: after });
    }

    // screenshots: hero + footer + section crops of before/after for the 4 visual spots
    for (const t of shotTargets) {
      try {
        const loc = await page.evaluateHandle(t.find);
        const el = loc.asElement();
        if (el) await el.screenshot({ path: `${OUT}/${vp.name}-${t.key}-after.png`, animations: 'disabled', timeout: 8000 });
      } catch (e) { console.error(`shot fail ${vp.name}/${t.key}: ${e.message.split('\n')[0]}`); }
    }
    // viewport shot of hero (top) and full page height
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(150);
    await page.screenshot({ path: `${OUT}/${vp.name}-hero-viewport-after.png`, animations: 'disabled' });
    await ctx.close();
  }

  await browser.close();
  fs.writeFileSync(`${OUT}/predict5-report.json`, JSON.stringify(report, null, 2));
  for (const k of Object.keys(report)) {
    console.log(`\n===== ${k} =====`);
    for (const key of Object.keys(report[k])) {
      const v = report[k][key];
      if (v.error) { console.log(`${key}: ERROR ${v.error}`); continue; }
      const b = v.before, a = v.after;
      console.log(`${key} [${v.mutate}] lines ${b.lines}→${a.lines} | boxH ${b.h}→${a.h} | lh ${a.lineHeight} | fs ${a.fontSize} | w ${b.w}→${a.w} | overflowX ${a.overflowX} | docH ${b.docH}→${a.docH} | outside=${a.outside}`);
    }
  }
})();
