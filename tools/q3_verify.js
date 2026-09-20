// q3: 改动后 1440 + 375 实测验证
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const BASE = 'http://sinofresh.local';

const FAQ_PAGES = ['/', '/quality/', '/faq/', '/services/', '/cooperation/', '/factory-tour/', '/contact/',
  '/products/soft-chews/', '/products/drops/', '/products/powders/', '/products/pastes/',
  '/products/tablets/', '/products/liquids/', '/products/fish-oil/', '/products/dental-chews/'];

const measure = async (page) => page.evaluate(() => {
  const rect = (el) => el ? el.getBoundingClientRect() : null;
  const n = (v) => v === null ? null : Math.round(v);
  const out = { path: location.pathname, docH: document.documentElement.scrollHeight, docW: document.documentElement.scrollWidth, winW: window.innerWidth };

  // ---- FAQ ----
  const faq = document.querySelector('.sf-faq');
  if (faq) {
    const r = rect(faq);
    const sec = faq.closest('section');
    const h2 = sec ? Array.from(sec.children).find(c => c.tagName === 'H2') : null;
    out.faq = {
      w: n(r.width), left: n(r.left), right: n(r.right),
      maxW: getComputedStyle(faq).maxWidth,
      firstDetailW: n(rect(faq.querySelector('details')).width),
      secH2: h2 ? { w: n(rect(h2).width), left: n(rect(h2).left) } : null,
      pW: n(rect(faq.querySelector('details p')).width)
    };
  }

  // ---- certificates ----
  const rows = Array.from(document.querySelectorAll('.sf-certrow'));
  if (rows.length) {
    const detail = document.querySelector('.sf-certdetail');
    out.cert = {
      wrapH: n(rect(detail).height),
      wrapW: n(rect(detail).width),
      count: rows.length,
      rows: rows.map(tr => {
        const m = tr.querySelector('.sf-certrow__media');
        const img = tr.querySelector('img');
        return {
          name: tr.querySelector('.sf-certrow__name').textContent.trim(),
          h: n(rect(tr).height),
          mediaW: n(rect(m).width), mediaH: n(rect(m).height),
          img: img ? n(rect(img).width) + 'x' + n(rect(img).height) : 'placeholder',
          aHref: (() => { const a = m.querySelector('a'); return a ? a.getAttribute('href').split('/').pop() : null; })(),
          aTarget: (() => { const a = m.querySelector('a'); return a ? a.getAttribute('target') : null; })(),
          radius: getComputedStyle(img || m).borderRadius,
          shadow: getComputedStyle(img || m).boxShadow !== 'none'
        };
      })
    };
  }

  // ---- QC lab ----
  const lab = document.querySelector('.sf-eq');
  if (lab) {
    const tiles = Array.from(lab.querySelectorAll(':scope > .wp-block-image'));
    const first = tiles[0];
    out.lab = {
      display: getComputedStyle(lab).display,
      cols: getComputedStyle(lab).gridTemplateColumns,
      count: tiles.length,
      tileW: n(rect(first).width),
      imgH: n(rect(first.querySelector('img')).height),
      capCount: lab.querySelectorAll('figcaption').length,
      capPos: first.querySelector('figcaption') ? getComputedStyle(first.querySelector('figcaption')).position : null,
      capText: first.querySelector('figcaption') ? first.querySelector('figcaption').textContent.slice(0, 42) : null,
      capStrongDisplay: first.querySelector('figcaption strong') ? getComputedStyle(first.querySelector('figcaption strong')).display : null,
      radius: getComputedStyle(first.querySelector('img')).borderRadius,
      gridRows: getComputedStyle(lab).gridTemplateRows.split(' ').length
    };
  }

  // ---- QC steps ----
  const qs = document.querySelector('.sf-qs');
  if (qs) {
    const steps = Array.from(qs.querySelectorAll('.sf-qs__step'));
    const first = steps[0];
    const num = first.querySelector('.sf-qs__num');
    const img = first.querySelector('img');
    out.steps = {
      count: steps.length,
      stepH: steps.map(s => n(rect(s).height)),
      railW: n(rect(num.parentElement).width),
      numH: n(rect(num).height),
      numColor: getComputedStyle(num).color,
      numFont: getComputedStyle(num).fontSize,
      contentCols: getComputedStyle(first.querySelector('.sf-qs__content')).gridTemplateColumns,
      imgW: n(rect(img).width), imgH: n(rect(img).height),
      imgRadius: getComputedStyle(img).borderRadius,
      sepBorders: steps.slice(1).map(s => getComputedStyle(s).borderTopWidth).join(',')
    };
  }

  // ---- palatability ----
  const pal = document.querySelector('.sf-pal');
  if (pal) {
    const steps = Array.from(pal.querySelectorAll('.sf-pal__step'));
    const dot = steps[0].querySelector('.sf-pal__dot');
    out.pal = {
      display: getComputedStyle(pal).display,
      cols: getComputedStyle(pal).gridTemplateColumns,
      gap: getComputedStyle(pal).columnGap,
      count: steps.length,
      stepW: n(rect(steps[0]).width),
      stepH: steps.map(s => n(rect(s).height)),
      dotW: n(rect(dot).width), dotH: n(rect(dot).height),
      dotRadius: getComputedStyle(dot).borderRadius,
      dotColor: getComputedStyle(dot).color,
      dotBg: getComputedStyle(dot).backgroundColor,
      connectorCount: steps.slice(1).filter(s => getComputedStyle(s, '::before').content !== 'none').length
    };
  }

  // ---- overflow ----
  const over = [];
  document.querySelectorAll('body *').forEach(el => {
    const rc = el.getBoundingClientRect();
    if (rc.width > 0 && (rc.right > window.innerWidth + 1 || rc.left < -1)) {
      const cls = (el.className || '').toString().slice(0, 44);
      over.push((el.tagName || '').toLowerCase() + '.' + cls + ' L' + Math.round(rc.left) + ' R' + Math.round(rc.right));
    }
  });
  out.overCount = over.length;
  out.over = over.slice(0, 5);
  return out;
});

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });

  // ---------- desktop 1440 ----------
  const c1 = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p1 = await c1.newPage();
  console.log('===== 1440 FAQ =====');
  const faqRows = [];
  for (const u of FAQ_PAGES) {
    await p1.goto(BASE + u, { waitUntil: 'networkidle', timeout: 45000 });
    await p1.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
    const m = await measure(p1);
    faqRows.push({ path: m.path, faqW: m.faq ? m.faq.w : null, faqLeft: m.faq ? m.faq.left : null, faqMaxW: m.faq ? m.faq.maxW : null, detailW: m.faq ? m.faq.firstDetailW : null, secH2W: m.faq && m.faq.secH2 ? m.faq.secH2.w : null, secH2Left: m.faq && m.faq.secH2 ? m.faq.secH2.left : null, pW: m.faq ? m.faq.pW : null, over: m.overCount });
  }
  faqRows.forEach(r => console.log(JSON.stringify(r)));

  console.log('\n===== 1440 Quality =====');
  await p1.goto(BASE + '/quality/', { waitUntil: 'networkidle', timeout: 45000 });
  await p1.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
  const q = await measure(p1);
  console.log('docH', q.docH, 'overCount', q.overCount, q.over);
  console.log('CERT', JSON.stringify(q.cert, null, 1));
  console.log('LAB', JSON.stringify(q.lab, null, 1));
  console.log('STEPS', JSON.stringify(q.steps, null, 1));
  console.log('PAL', JSON.stringify(q.pal, null, 1));

  // ---------- mobile 375 ----------
  console.log('\n===== 375 =====');
  const c2 = await b.newContext({ viewport: { width: 375, height: 812 }, deviceScaleFactor: 2 });
  const p2 = await c2.newPage();
  for (const u of ['/quality/', '/', '/faq/', '/services/', '/products/soft-chews/']) {
    await p2.goto(BASE + u, { waitUntil: 'networkidle', timeout: 45000 });
    await p2.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
    const m = await measure(p2);
    console.log(JSON.stringify({
      path: m.path, docH: m.docH, docW: m.docW, winW: m.winW, overflow: m.docW > m.winW,
      faqW: m.faq ? m.faq.w : null, overCount: m.overCount, over: m.over,
      certRowH: m.cert ? m.cert.rows[0].h : null, certImg: m.cert ? m.cert.rows[0].img : null,
      labCols: m.lab ? m.lab.cols : null, labTileW: m.lab ? m.lab.tileW : null,
      stepsCount: m.steps ? m.steps.count : null, stepRail: m.steps ? m.steps.railW : null,
      palCols: m.pal ? m.pal.cols : null
    }));
  }

  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
