/* Task 7 — About page final acceptance: desktop 1440 + mobile 375 + schema.
 *   node tools/about_t7_verify.js
 * Prints one PASS/FAIL line per requirement, then a JSON blob of raw numbers.
 */
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const fs = require('fs');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const URL = 'http://sinofresh.local/about/';
let pass = 0, fail = 0;
const row = (ok, name, detail) => {
  (ok ? pass++ : fail++);
  console.log((ok ? 'PASS  ' : 'FAIL  ') + name.padEnd(46) + (detail === undefined ? '' : detail));
};

const warm = async (page) => {
  await page.goto(URL, { waitUntil: 'networkidle' });
  await page.evaluate(async () => { await document.fonts.ready; });
  await page.evaluate(async () => { const s = Math.round(innerHeight * 0.8); for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 55)); } scrollTo(0, 0); });
  await page.waitForTimeout(600);
};

/* the journey entrance is staggered (up to 630ms delay + 550ms fade) and the
   inline stagger delay is only cleared once the row has landed, so a snapshot
   taken too early reads opacity 0 on the last node. Poll until settled. */
const settleJourney = async (page, budget = 6000) => {
  const t0 = Date.now();
  while (Date.now() - t0 < budget) {
    const ok = await page.evaluate(() => [...document.querySelectorAll('.sf-journey__item')].every(i => getComputedStyle(i).opacity === '1' && !i.style.transitionDelay));
    if (ok) return Date.now() - t0;
    await page.waitForTimeout(200);
  }
  return -1;
};

(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const raw = {};

  /* ================= desktop 1440 ================= */
  let ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  let page = await ctx.newPage();
  const errs = []; page.on('pageerror', e => errs.push(e.message));
  await warm(page);
  const settleMs = await settleJourney(page);
  raw.journeySettleMs = settleMs;

  const d = await page.evaluate(() => {
    const out = {};
    const sec = (t) => [...document.querySelectorAll('.wp-site-blocks > .wp-block-group')].find(s => { const h = s.querySelector('h1,h2'); return h && h.textContent.trim().startsWith(t); });

    // hero
    const hero = document.querySelector('.sf-hero-inner');
    out.hero = hero ? { bg: getComputedStyle(hero).backgroundColor, h1: hero.querySelector('h1').textContent.trim(), left: Math.round(hero.querySelector('h1').getBoundingClientRect().left) } : null;

    // who we are
    const wwa = sec('Who We Are');
    const wwaText = wwa ? wwa.innerText : '';
    out.wwa = { iso8: /ISO 8 cleanrooms/.test(wwaText), legacy: /100,000-class|five dosage|four continents/.test(wwaText), dosages: ['soft chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish oil', 'dental chews'].filter(x => wwaText.toLowerCase().includes(x)).length };

    // journey
    const j = document.querySelector('.sf-journey');
    const items = [...j.querySelectorAll('.sf-journey__item')];
    out.journey = {
      n: items.length,
      dots: j.querySelectorAll('.sf-journey__dot').length,
      years: items.map(i => i.querySelector('.sf-journey__year').textContent.trim()),
      rail: items.slice(0, -1).every(i => getComputedStyle(i, '::after').display === 'block'),
      lastNoRail: getComputedStyle(items[items.length - 1], '::after').display === 'none',
      revealed: items.every(i => getComputedStyle(i).opacity === '1'),
      origin: getComputedStyle(items[0]).transformOrigin,
    };

    // core values
    const core = document.querySelector('.sf-core');
    out.core = {
      n: core.children.length,
      colH: [...core.children].map(c => +c.getBoundingClientRect().height.toFixed(1)),
      cardH: [...core.children].map(c => +c.querySelector('.wp-block-group').getBoundingClientRect().height.toFixed(1)),
    };

    // team
    const team = document.querySelector('.sf-team');
    const cols = [...team.children];
    out.team = {
      n: cols.length,
      avatar: cols.map(c => { const a = c.querySelector('.sf-team__avatar'); const r = a.getBoundingClientRect(); return Math.round(r.width) + 'x' + Math.round(r.height); }),
      figure: cols.map(c => { const f = c.querySelector('figure'); const r = f.getBoundingClientRect(); return Math.round(r.width) + 'x' + Math.round(r.height); }),
      bg: cols.map(c => getComputedStyle(c.querySelector('.sf-team__avatar')).backgroundColor),
      cx: cols.map(c => Math.round((r => (r.left + r.right) / 2)(c.querySelector('.sf-team__avatar').getBoundingClientRect()) * 10) / 10 + '/' + Math.round((r => (r.left + r.right) / 2)(c.querySelector('h3').getBoundingClientRect()) * 10) / 10),
      gaps: cols.map(c => { const h3 = c.querySelector('h3'), p1 = c.querySelectorAll('p')[0], p2 = c.querySelectorAll('p')[1]; return Math.round(p1.getBoundingClientRect().top - h3.getBoundingClientRect().bottom) + '/' + Math.round(p2.getBoundingClientRect().top - p1.getBoundingClientRect().bottom); }),
    };

    // factory
    const fac = sec('Inside Our Factory');
    const g = fac.querySelector('.sf-fac');
    const tiles = [...g.querySelectorAll('figure.sf-fac__item')];
    const t0 = tiles[0].getBoundingClientRect();
    out.fac = {
      bg: getComputedStyle(fac).backgroundColor,
      n: tiles.length,
      cols: getComputedStyle(g).gridTemplateColumns.split(' ').length,
      rows: new Set(tiles.map(t => Math.round(t.getBoundingClientRect().top))).size,
      tile: Math.round(t0.width) + 'x' + Math.round(t0.height),
      gridW: Math.round(g.getBoundingClientRect().width),
      shadow: getComputedStyle(tiles[0]).boxShadow.slice(0, 34),
      radius: getComputedStyle(tiles[0]).borderRadius,
      placeholders: tiles.filter(t => /fac-placeholder/.test(t.querySelector('img').getAttribute('src'))).length,
    };

    // video + cta
    const vid = document.querySelector('.sf-video, [class*="sf-video"]');
    out.video = vid ? { iframes: vid.querySelectorAll('iframe').length, poster: !!vid.querySelector('img'), posterSrc: (vid.querySelector('img') || {}).getAttribute ? vid.querySelector('img').getAttribute('src').split('/').pop() : null } : null;
    const cta = sec('Ready to Start?');
    out.cta = cta ? { bg: getComputedStyle(cta).backgroundColor, btn: cta.querySelector('.wp-block-button__link').textContent.trim() } : null;

    out.docH = document.documentElement.scrollHeight;
    out.overflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
    return out;
  });
  raw.d1440 = d;

  row(d.hero && d.hero.bg === 'rgb(46, 107, 84)' && d.hero.h1 === 'About SINO FRESH' && d.hero.left >= 20, '1440 · Hero 正常（底色/标题/未裁切）', JSON.stringify(d.hero));
  row(d.wwa.iso8 && d.wwa.dosages === 8 && !d.wwa.legacy, '1440 · Who We Are：8 剂型 + ISO 8', `dosages=${d.wwa.dosages} iso8=${d.wwa.iso8} legacy=${d.wwa.legacy}`);
  row(d.journey.n === 8 && d.journey.dots === 8 && d.journey.rail && d.journey.lastNoRail && d.journey.revealed, '1440 · Journey：8 条 + 圆点 + 竖线 + 已淡入', JSON.stringify({ n: d.journey.n, dots: d.journey.dots, rail: d.journey.rail, last: d.journey.lastNoRail, revealed: d.journey.revealed, settleMs }));
  row(new Set(d.core.colH).size === 1 && new Set(d.core.cardH).size === 1 && d.core.n === 5, '1440 · Core Values：5 卡等高', `cols=${JSON.stringify(d.core.colH)} cards=${JSON.stringify(d.core.cardH)}`);
  row(d.team.n === 5 && d.team.avatar.every(x => x === '120x120') && d.team.figure.every(x => x === '120x120') && d.team.bg.every(x => x === 'rgba(0, 0, 0, 0)') && d.team.cx.every(p => p.split('/')[0] === p.split('/')[1]) && d.team.gaps.every(x => x === '8/10'), '1440 · Team：5 头像铺满/无灰底/对齐/间距', `cx=${JSON.stringify(d.team.cx)} gaps=${JSON.stringify(d.team.gaps)}`);
  row(d.fac.n === 12 && d.fac.cols === 4 && d.fac.rows === 3 && d.fac.bg === 'rgb(243, 246, 244)' && d.fac.placeholders === 6, '1440 · Factory：12 图 4×3 + 浅灰底', JSON.stringify({ n: d.fac.n, cols: d.fac.cols, rows: d.fac.rows, bg: d.fac.bg, ph: d.fac.placeholders }));
  row(d.video && d.video.iframes === 0 && d.video.poster, '1440 · 视频区保持现状（0 iframe + 海报）', JSON.stringify(d.video));
  row(d.cta && d.cta.bg === 'rgb(27, 77, 62)' && /Book a Factory Tour/i.test(d.cta.btn), '1440 · 底部 CTA 正常', JSON.stringify(d.cta));
  row(d.overflow === 0, '1440 · 无横向溢出', 'overflow=' + d.overflow);

  /* hover states: journey item, journey dot, factory tile */
  await page.evaluate(() => document.querySelector('.sf-journey__item').scrollIntoView({ block: 'center' }));
  await page.waitForTimeout(300);
  let bb = await (await page.$('.sf-journey__item')).boundingBox();
  await page.mouse.move(bb.x + 40, bb.y + bb.height / 2);
  await page.waitForTimeout(420);
  const jh = await page.evaluate(() => {
    const it = document.querySelector('.sf-journey__item');
    return { item: getComputedStyle(it).transform, dot: getComputedStyle(it.querySelector('.sf-journey__dot')).transform };
  });
  row(jh.item.includes('1.04') && jh.dot.includes('1.5'), '1440 · Journey hover 放大（4% / 圆点 50%）', JSON.stringify(jh));

  await page.evaluate(() => document.querySelector('.sf-fac > figure:nth-child(1)').scrollIntoView({ block: 'center' }));
  await page.waitForTimeout(300);
  bb = await (await page.$('.sf-fac > figure:nth-child(1)')).boundingBox();
  await page.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2);
  await page.waitForTimeout(450);
  const fh = await page.evaluate(() => {
    const f = document.querySelector('.sf-fac > figure:nth-child(1)');
    return { tile: getComputedStyle(f).transform, shadow: getComputedStyle(f).boxShadow.slice(0, 34), img: getComputedStyle(f.querySelector('img')).transform };
  });
  row(fh.tile === 'none' && fh.shadow.includes('0px 8px 24px') && fh.img.includes('1.05'), '1440 · Factory hover：容器阴影加深+图片放大', JSON.stringify(fh));

  /* lightbox */
  await page.mouse.click(bb.x + bb.width / 2, bb.y + bb.height / 2);
  await page.waitForTimeout(520);
  const lb = await page.evaluate(() => {
    const bx = document.querySelector('.sf-lb');
    const img = bx.querySelector('.sf-lb__img');
    return { open: !bx.hidden && bx.classList.contains('is-open'), count: bx.querySelector('.sf-lb__count').textContent, img: (r => Math.round(r.width) + 'x' + Math.round(r.height))(img.getBoundingClientRect()), scroll: getComputedStyle(document.documentElement).overflow };
  });
  await page.keyboard.press('ArrowRight'); await page.waitForTimeout(280);
  const lb2 = await page.evaluate(() => document.querySelector('.sf-lb__count').textContent);
  await page.keyboard.press('Escape'); await page.waitForTimeout(320);
  const lb3 = await page.evaluate(() => ({ hidden: document.querySelector('.sf-lb').hidden, scroll: getComputedStyle(document.documentElement).overflow }));
  raw.lightbox = { ...lb, afterArrow: lb2, ...lb3 };
  row(lb.open && lb.count === '1 / 12' && lb.scroll === 'hidden' && lb2 === '2 / 12' && lb3.hidden && lb3.scroll !== 'hidden', '1440 · 灯箱：12 张/箭头/Esc/滚动锁', JSON.stringify(raw.lightbox));
  row(errs.length === 0, '1440 · 0 JS 错误', JSON.stringify(errs));
  await ctx.close();

  /* ================= mobile 375 ================= */
  ctx = await b.newContext({ viewport: { width: 375, height: 760 }, deviceScaleFactor: 2 });
  page = await ctx.newPage();
  const merrs = []; page.on('pageerror', e => merrs.push(e.message));
  await warm(page);
  const mSettle = await settleJourney(page);
  const m = await page.evaluate(() => {
    const sec = (t) => [...document.querySelectorAll('.wp-site-blocks > .wp-block-group')].find(s => { const h = s.querySelector('h1,h2'); return h && h.textContent.trim().startsWith(t); });
    const items = [...document.querySelectorAll('.sf-journey__item')];
    const team = document.querySelector('.sf-team');
    const tiles = [...document.querySelectorAll('.sf-fac > figure.sf-fac__item')];
    const t0 = tiles[0].getBoundingClientRect();
    return {
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      heroLeft: Math.round(document.querySelector('.sf-hero-inner h1').getBoundingClientRect().left),
      journeyN: items.length, journeyRevealed: items.every(i => getComputedStyle(i).opacity === '1'),
      journeyRowW: items.map(i => Math.round(i.getBoundingClientRect().width)).filter((v, i, a) => a.indexOf(v) === i),
      teamCols: getComputedStyle(team).gridTemplateColumns ? getComputedStyle(team).gridTemplateColumns.split(' ').length : team.children.length,
      teamAvatar: [...team.querySelectorAll('.sf-team__avatar')].map(a => (r => Math.round(r.width) + 'x' + Math.round(r.height))(a.getBoundingClientRect())),
      facCols: getComputedStyle(document.querySelector('.sf-fac')).gridTemplateColumns.split(' ').length,
      facTile: Math.round(t0.width) + 'x' + Math.round(t0.height),
      facSectionH: Math.round(sec('Inside Our Factory').getBoundingClientRect().height),
      secOrder: [...document.querySelectorAll('.wp-site-blocks > .wp-block-group')].map(s => { const h = s.querySelector('h1,h2'); return (h ? h.textContent.trim().slice(0, 18) : '?') + '=' + getComputedStyle(s).backgroundColor; }),
    };
  });
  raw.m375 = m;
  row(m.overflow === 0, '375 · 无横向溢出', 'overflow=' + m.overflow);
  row(m.heroLeft >= 20, '375 · Hero 内容未贴边', 'left=' + m.heroLeft);
  row(m.journeyN === 8 && m.journeyRevealed && m.journeyRowW.length === 1, '375 · Journey 8 条折行正常', JSON.stringify({ n: m.journeyN, w: m.journeyRowW, revealed: m.journeyRevealed, settleMs: mSettle }));
  row(m.teamAvatar.length === 5 && m.teamAvatar.every(x => x === '120x120'), '375 · Team 头像 5 个 120×120', JSON.stringify(m.teamAvatar));
  row(m.facCols === 3 && m.facTile.startsWith('94x'), '375 · Factory 3 列紧凑', `cols=${m.facCols} tile=${m.facTile} secH=${m.facSectionH}`);
  row(['Who We Are=rgb(243, 246, 244)', 'Our Core Values=rgb(243, 246, 244)', 'Our Team=rgb(255, 255, 255)', 'Inside Our Factory=rgb(243, 246, 244)'].every(x => m.secOrder.includes(x)), '375 · 灰/白节奏保持', m.secOrder.join(' | '));
  row(merrs.length === 0, '375 · 0 JS 错误', JSON.stringify(merrs));
  await ctx.close();
  await b.close();

  /* ================= schema ================= */
  const html = await (await fetch(URL)).text();
  fs.writeFileSync('screenshots/t7_about_rendered.html', html);
  const blocks = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map(x => x[1]);
  const org = blocks.map(x => JSON.parse(x)).find(o => o.hasCredential);
  const names = org ? org.hasCredential.map(c => c.name) : [];
  const want = ['FDA Registered', 'cGMP Compliant', 'ISO 9001 Certified', 'FSSC 22000 Certified', 'HACCP Certified', 'BRC Certified'];
  raw.schema = { blocks: blocks.length, names };
  row(!!org && names.length === 6, 'Schema · hasCredential = 6 条', JSON.stringify(names));
  row(want.every(w => names.includes(w)), 'Schema · 认证名称统一为目标 6 项', names.join(' / '));
  row(!/ISO 22000/.test(JSON.stringify(org)), 'Schema · 无 ISO 22000 残留', '');
  console.log('\n== RAW ==\n' + JSON.stringify(raw, null, 1));
  console.log('\nTOTAL: ' + pass + ' pass / ' + fail + ' fail');
  process.exit(fail ? 1 : 0);
})();
