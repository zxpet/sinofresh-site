// About 页 7 处问题扫描：视频区 / 发展史 / Core Values / Team / Factory / 分页
// 用法: node about_scan.js [widths] [shotDir]
const path = require('path');
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const CHROME = process.env.HOME +
  '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const URL = 'http://sinofresh.local/about/';
const widths = (process.argv[2] || '1440,375').split(',').map(Number);
const shotDir = process.argv[3] || null;

const PROBE = () => {
  const r = (el) => { const b = el.getBoundingClientRect(); return { l: +b.left.toFixed(1), t: +b.top.toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1) }; };
  const sect = [...document.querySelectorAll('.wp-site-blocks > section')];
  const find = (txt) => sect.find(s => (s.querySelector('h2') || {}).textContent && s.querySelector('h2').textContent.trim().toLowerCase().includes(txt));
  const out = {};

  // ---- 1. 视频区 ----
  const vc = document.querySelector('.sf-video-cover');
  if (vc) {
    const img = vc.querySelector('img');
    const csBefore = getComputedStyle(vc, '::before');
    const csAfter = getComputedStyle(vc, '::after');
    out.video = {
      box: r(vc),
      img: img ? r(img) : null,
      imgNatural: img ? { w: img.naturalWidth, h: img.naturalHeight } : null,
      imgObjectFit: img ? getComputedStyle(img).objectFit : null,
      playBtn: { w: csBefore.width, h: csBefore.height, bg: csBefore.backgroundColor, triBorder: csAfter.borderLeftWidth },
      hasAnchor: !!vc.querySelector('a'),
      hasIframe: !!vc.querySelector('iframe'),
      clickable: vc.getAttribute('onclick') || null,
      section: vc.closest('section') ? r(vc.closest('section')) : null
    };
  }

  // ---- 2. 发展史 ----
  const j = find('journey');
  if (j) {
    const items = [...j.querySelectorAll(':scope > div > div')].filter(d => d.querySelector('p, h3'));
    const rows = items.filter(d => d.querySelector('h3'));
    out.journey = {
      section: r(j),
      h2: r(j.querySelector('h2')),
      rowCount: rows.length,
      rows: rows.map(row => {
        const p = row.querySelector('p');
        const h3 = row.querySelector('h3');
        const cs = getComputedStyle(row);
        return {
          year: (p ? p.textContent : '').trim(),
          title: (h3 ? h3.textContent : '').trim(),
          years: [...row.querySelectorAll('p')].map(x => x.textContent.trim()).filter(Boolean),
          box: r(row),
          h3Top: h3 ? +h3.getBoundingClientRect().top.toFixed(1) : null,
          borderLeft: cs.borderLeftWidth + ' ' + cs.borderLeftStyle + ' ' + cs.borderLeftColor,
          flexDir: cs.flexDirection,
          gap: cs.gap
        };
      }),
      markers: j.querySelectorAll('.sf-journey__dot, [class*=dot], [class*=marker], [class*=line]').length,
      anyTransition: [...j.querySelectorAll('*')].filter(e => { const c = getComputedStyle(e); return c.transitionDuration !== '0s' || c.animationName !== 'none'; }).length,
      countUp: j.querySelectorAll('.sf-num').length
    };
  }

  // ---- 3. Core Values ----
  const cv = find('core values');
  if (cv) {
    const cols = [...cv.querySelectorAll('.wp-block-column')];
    out.coreValues = {
      section: r(cv),
      colCount: cols.length,
      colsPerRow: null,
      cards: cols.map(c => {
        const card = c.querySelector('.wp-block-group');
        const h3 = card.querySelector('h3');
        const p = card.querySelector('p');
        return {
          colBox: r(c), cardBox: card ? r(card) : null,
          h3Top: h3 ? +h3.getBoundingClientRect().top.toFixed(1) : null,
          h3Lines: h3 ? h3.getClientRects().length : null,
          pTop: p ? +p.getBoundingClientRect().top.toFixed(1) : null,
          pl: card ? getComputedStyle(card).paddingLeft : null,
          align: card ? getComputedStyle(card).alignItems + '/' + getComputedStyle(card).justifyContent : null
        };
      }),
      columnsWrapFlexWrap: getComputedStyle(cv.querySelector('.wp-block-columns')).flexWrap
    };
    // 同一行的列（按 top 分组）
    const byTop = {};
    cols.forEach((c, i) => { const t = Math.round(c.getBoundingClientRect().top); (byTop[t] = byTop[t] || []).push(i); });
    out.coreValues.rowsByTop = byTop;
  }

  // ---- 4. Team ----
  const tm = find('our team');
  if (tm) {
    const circles = [...tm.querySelectorAll('.wp-block-column > .wp-block-group')];
    out.team = {
      circleCount: circles.length,
      memberCount: tm.querySelectorAll('h3').length,
      circles: circles.map(c => {
        const img = c.querySelector('img');
        const cs = getComputedStyle(c);
        const fig = c.querySelector('figure');
        const fcs = fig ? getComputedStyle(fig) : null;
        const ics = img ? getComputedStyle(img) : null;
        return {
          box: r(c), styleWH: cs.width + 'x' + cs.height, radius: cs.borderRadius,
          overflow: cs.overflow, display: cs.display, alignItems: cs.alignItems, justifyContent: cs.justifyContent,
          img: img ? r(img) : null,
          figBox: fig ? r(fig) : null,
          figDisplay: fcs ? fcs.display : null,
          imgObjectFit: ics ? ics.objectFit : null,
          imgW: ics ? ics.width : null
        };
      })
    };
  }

  // ---- 5. Factory ----
  const fc = find('factory');
  if (fc) {
    const cards = [...fc.querySelectorAll('.wp-block-column > .wp-block-group')];
    out.factory = {
      section: r(fc),
      cardCount: cards.length,
      rows: [...fc.querySelectorAll('.wp-block-columns')].map(c => r(c)),
      cards: cards.map(c => {
        const img = c.querySelector('img');
        const fig = c.querySelector('figure');
        return {
          box: r(c), minH: getComputedStyle(c).minHeight, padding: getComputedStyle(c).padding,
          figBox: fig ? r(fig) : null, figDisplay: fig ? getComputedStyle(fig).display : null, figMargin: fig ? getComputedStyle(fig).margin : null,
          img: img ? r(img) : null, objectFit: img ? getComputedStyle(img).objectFit : null,
          natural: img ? img.naturalWidth + 'x' + img.naturalHeight : null,
          hasAnchor: !!c.querySelector('a'), hasIframe: !!c.querySelector('iframe')
        };
      })
    };
  }

  // ---- 6. 分页 ----
  out.pagination = {
    anyNav: document.querySelectorAll('nav.wp-block-query-pagination, .wp-block-query-pagination, .page-numbers, nav[class*=pagination]').length,
    anyQuery: document.querySelectorAll('.wp-block-query').length,
    buttonsOnPage: document.querySelectorAll('a.wp-block-button__link, button').length
  };

  // ---- 7. Hero ----
  const hero = document.querySelector('.sf-hero-inner');
  if (hero) out.hero = { box: r(hero), h1: r(hero.querySelector('h1')), pt: getComputedStyle(hero).paddingTop };

  // 段落文字抽查（15年 口误等）
  const txt = document.body.innerText;
  out.textHits = {
    has15years: /15\s*(\+)?\s*years|15年/i.test(txt),
    m2Count: (txt.match(/m²/g) || []).length,
    fourContinents: /four continents/i.test(txt),
    yearTokens: [...new Set((txt.match(/\b(19|20)\d{2}\b/g) || []))]
  };
  out.docH = document.documentElement.scrollHeight;
  out.hScroll = document.documentElement.scrollWidth - document.documentElement.clientWidth;
  return out;
};

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const report = {};
  for (const w of widths) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 });
    await page.evaluate(() => document.fonts.ready);
    // 预滚动逼懒加载
    await page.evaluate(async () => {
      const step = Math.round(window.innerHeight * 0.8);
      for (let y = 0; y < document.body.scrollHeight; y += step) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); }
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(500);
    report[w] = await page.evaluate(PROBE);
    if (shotDir) {
      fs.mkdirSync(shotDir, { recursive: true });
      for (const [name, sel] of [['video', '.sf-video-cover'], ['journey', ''], ['core', ''], ['team', ''], ['factory', '']]) {
        let el = null;
        if (sel) el = await page.$(sel);
        else {
          const h2txt = { journey: 'journey', core: 'core values', team: 'our team', factory: 'factory' }[name];
          el = await page.evaluateHandle((t) => [...document.querySelectorAll('.wp-site-blocks > section')].find(s => { const h = s.querySelector('h2'); return h && h.textContent.trim().toLowerCase().includes(t); }), h2txt);
          el = el.asElement();
        }
        if (el) { try { await el.screenshot({ path: path.join(shotDir, `about_${name}_${w}.png`), animations: 'disabled' }); } catch (e) { console.log('shot fail', name, String(e).slice(0, 120)); } }
      }
      await page.screenshot({ path: path.join(shotDir, `about_full_${w}.png`), fullPage: false });
    }
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync('/Users/meng/Workbuddy/sinofresh外贸网站建设/tools/_about_scan.json', JSON.stringify(report, null, 1));
  // 摘要打印
  for (const w of widths) {
    const d = report[w];
    console.log(`\n=========== ${w}px ===========`);
    if (d.video) console.log(`[1 视频区] 容器 ${JSON.stringify(d.video.box)} img=${d.video.img ? JSON.stringify(d.video.img) : 'none'} natural=${JSON.stringify(d.video.imgNatural)} fit=${d.video.imgObjectFit} play=${d.video.playBtn.w}x${d.video.playBtn.h} 锚点=${d.video.hasAnchor} iframe=${d.video.hasIframe}`);
    if (d.journey) { console.log(`[2 发展史] 区块高=${d.journey.section.h} 行数=${d.journey.rowCount} 竖线元素=${d.journey.markers} 有过渡元素=${d.journey.anyTransition} countUp=${d.journey.countUp}`); d.journey.rows.forEach((r, i) => console.log(`   行${i + 1}: 年份=[${r.years.join(',')}] 标题="${r.title}" box=${JSON.stringify(r.box)} h3Top=${r.h3Top} border=${r.borderLeft}`)); }
    if (d.coreValues) { console.log(`[3 CoreValues] 列数=${d.coreValues.colCount} 行分组=${JSON.stringify(d.coreValues.rowsByTop)} wrap=${d.coreValues.columnsWrapFlexWrap}`); d.coreValues.cards.forEach((c, i) => console.log(`   卡${i + 1} card=${JSON.stringify(c.cardBox)} h3Top=${c.h3Top} h3行数=${c.h3Lines} pTop=${c.pTop} pad=${c.pl} align=${c.align}`)); }
    if (d.team) { console.log(`[4 Team] 圆=${d.team.circleCount} 成员=${d.team.memberCount}`); d.team.circles.forEach((c, i) => console.log(`   圆${i + 1} box=${JSON.stringify(c.box)} wh=${c.styleWH} radius=${c.radius} ovf=${c.overflow} display=${c.display} alignItems=${c.alignItems} fig=${JSON.stringify(c.figBox)} figDisplay=${c.figDisplay} img=${JSON.stringify(c.img)} fit=${c.imgObjectFit} imgW=${c.imgW}`)); }
    if (d.factory) { console.log(`[5 Factory] 卡=${d.factory.cardCount}`); d.factory.cards.forEach((c, i) => console.log(`   卡${i + 1} box=${JSON.stringify(c.box)} minH=${c.minH} pad=${c.padding} fig=${JSON.stringify(c.figBox)} figDisplay=${c.figDisplay} img=${JSON.stringify(c.img)} fit=${c.objectFit} natural=${c.natural} 锚点=${c.hasAnchor}`)); }
    console.log(`[6 分页] query-pagination=${d.pagination.anyNav} wp:query=${d.pagination.anyQuery}`);
    console.log(`[7 Hero] pt=${d.hero.pt} h1=${JSON.stringify(d.hero.h1)}`);
    console.log(`[文案] 15years=${d.textHits.has15years} m²次数=${d.textHits.m2Count} fourContinents=${d.textHits.fourContinents} 年份=[${d.textHits.yearTokens.join(',')}] docH=${d.docH} 横滚=${d.hScroll}`);
  }
  console.log('\n报告已写入 tools/_about_scan.json');
})();
