/**
 * Quality 页扫描：QC Lab caption 样式 + QC Steps 布局实测
 * 用法：node tools/quality_scan.js <vw>
 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/quality-qc';
fs.mkdirSync(OUT, { recursive: true });
const vw = parseInt(process.argv[2] || '1440', 10);

(async () => {
  const b = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const ctx = await b.newContext({
    viewport: { width: vw, height: vw < 500 ? 812 : 900 },
    isMobile: vw < 500, hasTouch: vw < 500,
  });
  const page = await ctx.newPage();
  page.setDefaultTimeout(30000);
  await page.goto('http://sinofresh.local/quality/', { waitUntil: 'domcontentloaded' });

  // 1) preroll: force lazy images to load
  await page.evaluate(async () => {
    const h = document.body.scrollHeight;
    for (let y = 0; y < h; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(400);
  await page.evaluate(async () => {
    const wait = [...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; }));
    await Promise.race([Promise.all(wait), new Promise(r => setTimeout(r, 5000))]);
  });
  await page.evaluate(async () => { await document.fonts.ready; });
  await page.waitForTimeout(400);

  const data = await page.evaluate(() => {
    const cs = el => el ? getComputedStyle(el) : null;
    const pick = (el, keys) => { if (!el) return null; const c = getComputedStyle(el); const o = {}; keys.forEach(k => o[k] = c[k]); return o; };
    const box = el => { if (!el) return null; const r = el.getBoundingClientRect(); return { x: Math.round(r.x), y: Math.round(r.y + window.scrollY), w: Math.round(r.width), h: Math.round(r.height), bottom: Math.round(r.bottom + window.scrollY) }; };

    const res = {};

    // ---- QC Lab captions ----
    const capFig = document.querySelector('.sf-eq figcaption, .sf-eq .wp-element-caption');
    const capStrong = capFig ? capFig.querySelector('strong') : null;
    res.caption = {
      rect: box(capFig),
      fig: pick(capFig, ['color', 'textShadow', 'fontSize', 'fontWeight', 'lineHeight', 'filter', 'textAlign', 'background', 'textRendering']),
      strong: pick(capStrong, ['color', 'textShadow', 'fontSize', 'fontWeight', 'display', 'marginBottom', 'filter']),
      // who sets textShadow? walk ancestors
      ancestorShadow: (() => {
        const out = [];
        let el = capFig;
        while (el && el !== document.documentElement) {
          const c = getComputedStyle(el);
          if (c.textShadow && c.textShadow !== 'none') out.push({ sel: el.tagName + '.' + (el.className || '').toString().slice(0, 60), textShadow: c.textShadow });
          el = el.parentElement;
        }
        return out;
      })(),
      // rules that declare text-shadow (CSSOM probe)
      shadowRules: (() => {
        const out = [];
        const walk = (rules, media) => {
          for (const r of rules) {
            if (r.selectorText !== undefined && r.style && r.style.textShadow) out.push({ sel: r.selectorText, val: r.style.textShadow, media: media || '' });
            if (r.cssRules) walk(r.cssRules, media || (r.conditionText || ''));
          }
        };
        for (const sh of document.styleSheets) { try { walk(sh.cssRules); } catch (e) { } }
        return out;
      })(),
    };

    // ---- QC Steps ----
    const wrap = document.querySelector('.sf-qs');
    const sec = wrap ? wrap.closest('section') : null;
    res.section = box(sec);
    res.sectionCS = pick(sec, ['paddingTop', 'paddingBottom']);
    // H2 of that section
    const h2 = sec ? sec.querySelector('h2') : null;
    res.h2 = { rect: box(h2), cs: pick(h2, ['fontSize', 'marginTop', 'marginBottom']) };

    const steps = [...document.querySelectorAll('.sf-qs__step')];
    res.steps = steps.map((st, i) => {
      const num = st.querySelector('.sf-qs__num');
      const content = st.querySelector('.sf-qs__content');
      const text = st.querySelector('.sf-qs__text');
      const h3 = st.querySelector('h3');
      const p = st.querySelector('p');
      const fig = st.querySelector('.sf-qs__media');
      const img = fig ? fig.querySelector('img') : null;
      const nb = box(num), h3b = box(h3), pb = box(p), fb = box(fig), stb = box(st), tb = box(text);
      return {
        i: i + 1,
        step: stb,
        stepCS: pick(st, ['display', 'gridTemplateColumns', 'gap', 'alignItems', 'marginTop', 'paddingTop', 'borderTopWidth', 'borderTopColor']),
        num: nb, numCS: pick(num, ['fontSize', 'fontWeight', 'color', 'lineHeight', 'letterSpacing']),
        content: box(content), contentCS: pick(content, ['display', 'gridTemplateColumns', 'gap', 'alignItems']),
        text: tb,
        h3: h3b, h3CS: pick(h3, ['fontSize', 'fontWeight', 'color', 'marginTop', 'marginBottom', 'lineHeight']),
        p: pb, pCS: pick(p, ['fontSize', 'color', 'marginTop', 'lineHeight']),
        fig: fb, img: box(img), imgCS: pick(img, ['objectFit', 'borderRadius', 'aspectRatio', 'width', 'height']),
        gaps: {
          numRight_to_h3Left: Math.round(h3b.x - (nb.x + nb.w)),
          numBottom_to_h3Top: Math.round(h3b.y - nb.bottom),
          numRight_to_textLeft: Math.round(tb.x - (nb.x + nb.w)),
          h3Bottom_to_pTop: Math.round(pb.y - h3b.bottom),
          textRight_to_figLeft: Math.round(fb.x - (tb.x + tb.w)),
        },
        numVsTitleSameRow: Math.abs(nb.y - h3b.y) < 20,
        imgW: box(img) ? box(img).w : 0,
      };
    });
    res.totalH = res.section ? res.section.h : null;
    res.stepsSumH = res.steps.reduce((a, s) => a + (s.step ? s.step.h : 0), 0);
    return res;
  });

  fs.writeFileSync(`${OUT}/scan-${vw}.json`, JSON.stringify(data, null, 2));

  // ---- shots ----
  await page.evaluate(() => {
    const s = document.createElement('style');
    s.textContent = '.sf-header{position:static!important}.sf-cookie-banner{display:none!important}';
    document.head.appendChild(s);
  });
  await page.waitForTimeout(300);
  const shoot = async (sel, name) => {
    const h = await page.$(sel);
    if (!h) { console.log('no el', sel); return; }
    await h.scrollIntoViewIfNeeded().catch(() => { });
    await page.waitForTimeout(600);
    await h.screenshot({ path: `${OUT}/${name}-${vw}.png`, animations: 'disabled', timeout: 20000 }).catch(e => console.log('shot fail', name, e.message.split('\n')[0]));
    console.log('shot', name, vw);
  };
  await shoot('.sf-eq', 'lab');
  await shoot('.sf-qs', 'steps');
  if (vw > 1000) {
    const h = await page.$('.sf-qs__step');
    if (h) { await h.scrollIntoViewIfNeeded().catch(() => { }); await page.waitForTimeout(400); await h.screenshot({ path: `${OUT}/step1-${vw}.png`, animations: 'disabled', timeout: 20000 }).catch(() => { }); }
  }

  await b.close();
  console.log('done', vw);
  console.log('--- caption ---');
  console.log(JSON.stringify(data.caption, null, 2));
  console.log('--- section ---', JSON.stringify(data.section), 'h2', JSON.stringify(data.h2));
  console.log('totalH', data.totalH, 'stepsSumH', data.stepsSumH);
  data.steps.forEach(s => console.log(`\n#${s.i} step=${s.step.h}px num[${s.numCS.fontSize}/${s.numCS.color}] numR->h3L=${s.gaps.numRight_to_h3Left} numB->h3T=${s.gaps.numBottom_to_h3Top} numR->txtL=${s.gaps.numRight_to_textLeft} h3B->pT=${s.gaps.h3Bottom_to_pTop} txtR->figL=${s.gaps.textRight_to_figLeft} imgW=${s.imgW} sameRow=${s.numVsTitleSameRow}`));
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
