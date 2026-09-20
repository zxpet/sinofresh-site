/**
 * m3_verify.js — ≤1240px 裸区块 inset 修复验证
 * 逐页检查：29 个裸块 padding=38、内容左缘=38、无双缩进、无横向溢出、hero 不贴边
 */
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const PAGES = [
  ['home', '/'], ['products', '/products/'], ['soft-chews', '/products/soft-chews/'],
  ['tablets', '/products/tablets/'], ['powders', '/products/powders/'], ['pastes', '/products/pastes/'],
  ['drops', '/products/drops/'], ['liquids', '/products/liquids/'], ['fish-oil', '/products/fish-oil/'],
  ['dental-chews', '/products/dental-chews/'], ['about', '/about/'], ['quality', '/quality/'],
  ['factory-tour', '/factory-tour/'], ['services', '/services/'], ['cooperation', '/cooperation/'],
  ['contact', '/contact/'], ['faq', '/faq/'], ['blog', '/blog/'], ['test-article', '/test-article/'],
  ['privacy-policy', '/privacy-policy/'], ['cookie-policy', '/cookie-policy/'], ['terms', '/terms/'],
  ['404', '/404-probe/'],
];

const NAKED = '.wp-site-blocks > .wp-block-group.is-layout-constrained:not(.has-background):not(.sf-hero-inner)';

const PROBE = (NAKED) => {
  const vw = window.innerWidth;
  const px = (v) => Math.round(parseFloat(v) || 0);
  const naked = [...document.querySelectorAll(NAKED)];
  const bad = [];
  const rows = [];
  naked.forEach((el) => {
    const c = getComputedStyle(el);
    let minL = Infinity, maxR = -Infinity;
    el.querySelectorAll('h1,h2,h3,h4,p,li,img,figcaption,a').forEach((k) => {
      if (k.closest('.sf-lb')) return;
      const r = k.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0) return;
      minL = Math.min(minL, r.left);
      maxR = Math.max(maxR, r.right);
    });
    const rec = {
      h2: (el.querySelector('h2') || {}).textContent ? el.querySelector('h2').textContent.slice(0, 30) : '(no h2)',
      padL: px(c.paddingLeft), padR: px(c.paddingRight),
      minL: minL === Infinity ? null : Math.round(minL),
      maxR: maxR === -Infinity ? null : Math.round(maxR),
    };
    rows.push(rec);
    if (rec.padL !== 38 || rec.padR !== 38) bad.push('padding!=38 :: ' + JSON.stringify(rec));
    if (rec.minL !== null && rec.minL !== 38) bad.push('content flush :: ' + JSON.stringify(rec));
    if (rec.minL !== null && rec.maxR > vw - 38 + 1) bad.push('right flush :: ' + JSON.stringify(rec));
  });

  // 双缩进探测：父链上存在「被本次修复加了 38px 的裸区块」时，子元素是否又叠了一层水平 padding
  const doubleIndent = [];
  const nearestNaked = (el) => {
    let cur = el.parentElement;
    while (cur && cur !== document.body) {
      if (naked.includes(cur)) return cur;
      cur = cur.parentElement;
    }
    return null;
  };
  document.querySelectorAll('.wp-site-blocks *').forEach((el) => {
    if (naked.includes(el)) return;
    const owner = nearestNaked(el);
    if (!owner) return;
    const pl = px(getComputedStyle(el).paddingLeft);
    if (pl > 0) {
      doubleIndent.push({ pl, tag: el.tagName.toLowerCase(), cls: (el.getAttribute('class') || '').slice(0, 60) });
    }
  });

  // hero
  const hero = document.querySelector('.sf-hero-inner');
  let heroL = null, heroPadL = null;
  if (hero) {
    heroPadL = px(getComputedStyle(hero).paddingLeft);
    let m = Infinity;
    hero.querySelectorAll('h1,p,a,span').forEach((k) => { const r = k.getBoundingClientRect(); if (r.width > 0 && r.height > 0) m = Math.min(m, r.left); });
    heroL = m === Infinity ? null : Math.round(m);
  }

  // Quality 页列宽（检查 38+16=54）
  const colPads = [...document.querySelectorAll('.wp-block-columns')].map((c) => px(getComputedStyle(c).paddingLeft)).filter((v) => v > 0);

  return {
    vw, docW: document.documentElement.scrollWidth,
    overflow: document.documentElement.scrollWidth - window.innerWidth,
    nakedCount: naked.length, rows, bad,
    doubleIndent, heroPadL, heroL, colPads,
  };
};

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  for (const [w, h] of [[1024, 800], [768, 1024], [375, 812]]) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    const p = await ctx.newPage();
    let totNaked = 0, totBad = [], ovf = [];
    console.log(`\n########## ${w}px ##########`);
    for (const [slug, url] of PAGES) {
      await p.goto('http://sinofresh.local' + url, { waitUntil: 'networkidle', timeout: 45000 });
      await p.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
      await p.evaluate(async () => {
        const H = document.documentElement.scrollHeight;
        for (let y = 0; y < H; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 20)); }
        window.scrollTo(0, 0); await new Promise(r => setTimeout(r, 180));
      });
      const r = await p.evaluate(PROBE, NAKED);
      totNaked += r.nakedCount;
      if (r.overflow > 0) ovf.push(`${slug}:${r.overflow}`);
      r.bad.forEach((x) => totBad.push(`${slug} :: ${x}`));
      const di = r.doubleIndent.filter((x) => x.pl >= 38);
      const line = `${slug.padEnd(15)} naked=${r.nakedCount} heroPadL=${r.heroPadL} heroL=${r.heroL} colPads=[${r.colPads.join(',')}] ovf=${r.overflow}${r.bad.length ? '  <BAD:' + r.bad.length + '>' : ''}${di.length ? '  <DOUBLE:' + JSON.stringify(di) + '>' : ''}`;
      console.log('  ' + line);
      if (r.bad.length) console.log('     ' + r.rows.map((x) => `${x.padL}|L${x.minL}|R${x.maxR} ${x.h2}`).join(' || '));
    }
    console.log(`  ---- ${w}px 小计: 裸块 ${totNaked} 个, 异常 ${totBad.length} 条, 溢出页 ${ovf.length ? ovf.join(',') : '无'}`);
    totBad.slice(0, 12).forEach((x) => console.log('     BAD ' + x));
    await ctx.close();
  }
  await b.close();
})().catch((e) => { console.error(e); process.exit(1); });
