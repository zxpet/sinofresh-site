const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const PROBE = () => {
  const secs = [...document.querySelectorAll('.wp-site-blocks > *')];
  const sec = secs.find(s => { const h = s.querySelector('h2'); return h && /^our team$/i.test(h.textContent.trim()); });
  if (!sec) return { err: 'team section not found' };
  const cols = sec.querySelector('.wp-block-columns');
  const csCols = getComputedStyle(cols);
  const colEls = [...cols.children];
  const R = e => { const b = e.getBoundingClientRect(); return { x: +b.x.toFixed(1), y: +b.y.toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1), cx: +(b.x + b.width / 2).toFixed(1) }; };
  const team = colEls.map((col, i) => {
    const csCol = getComputedStyle(col);
    const av = col.querySelector(':scope > .wp-block-group');
    const fig = av && av.querySelector('figure');
    const img = av && av.querySelector('img');
    const h3 = col.querySelector('h3');
    const ps = [...col.querySelectorAll(':scope > p')];
    const A = R(av), F = R(fig), I = R(img), H = R(h3), P0 = R(ps[0]), P1 = R(ps[1]);
    const csAv = getComputedStyle(av), csFig = getComputedStyle(fig), csImg = getComputedStyle(img);
    return {
      i, name: h3.textContent.trim(),
      col: R(col), colDisplay: csCol.display, colAlignItems: csCol.alignItems, colGap: csCol.rowGap,
      av: A, avPad: csAv.padding, avBg: csAv.backgroundColor, avRadius: csAv.borderRadius, avDisplay: csAv.display,
      avJustify: csAv.justifyContent, avAlignItems: csAv.alignItems, avClass: (av.className || '').slice(0, 80),
      fig: F, figDisplay: csFig.display, figMargin: csFig.margin, figMaxW: csFig.maxWidth, figOverflow: csFig.overflow,
      img: I, imgFit: csImg.objectFit, imgPos: csImg.objectPosition, imgRadius: csImg.borderRadius,
      imgMaxW: csImg.maxWidth, imgH: csImg.height, imgDisplay: csImg.display,
      h3: H, h3Fs: getComputedStyle(h3).fontSize, h3Margin: getComputedStyle(h3).margin,
      p0: P0, p0Fs: ps[0] ? getComputedStyle(ps[0]).fontSize : null, p0Color: ps[0] ? getComputedStyle(ps[0]).color : null, p0Margin: ps[0] ? getComputedStyle(ps[0]).margin : null,
      p1: P1, p1Fs: ps[1] ? getComputedStyle(ps[1]).fontSize : null, p1Margin: ps[1] ? getComputedStyle(ps[1]).margin : null,
      gaps: {
        avToH3: +(H.y - (A.y + A.h)).toFixed(1),
        h3ToP0: +(P0.y - (H.y + H.h)).toFixed(1),
        p0ToP1: +(P1.y - (P0.y + P0.h)).toFixed(1)
      },
      centers: { av: A.cx, h3: H.cx, p0: P0.cx, p1: P1.cx }
    };
  });
  const out = {
    sectionH: +sec.getBoundingClientRect().height.toFixed(1),
    colsDisplay: csCols.display, colsGrid: csCols.gridTemplateColumns, colsGap: csCols.gap,
    colsWidth: +cols.getBoundingClientRect().width.toFixed(1),
    docH: document.documentElement.scrollHeight,
    scrollW: document.documentElement.scrollWidth, innerW: window.innerWidth,
    team
  };
  const tgt = { av: colEls[0].querySelector(':scope > .wp-block-group'), fig: colEls[0].querySelector('figure'), img: colEls[0].querySelector('img'), col: colEls[0] };
  const hits = [];
  for (const sheet of document.styleSheets) {
    const src = (sheet.href || 'inline').split('/').pop();
    const walk = (rules, media) => {
      for (const r of rules) {
        if (r.conditionText !== undefined) { walk(r.cssRules, r.conditionText); continue; }
        if (!r.selectorText) continue;
        for (const k of Object.keys(tgt)) {
          if (!tgt[k]) continue;
          let m = false; try { m = tgt[k].matches(r.selectorText); } catch (e) { continue; }
          if (!m) continue;
          const t = r.cssText || '';
          if (!/flex|display|height|width|align|grid|padding|object-fit|border-radius|background|font-size|margin|gap/i.test(t)) continue;
          hits.push(k + ' | [' + (media || 'all') + '] ' + r.selectorText.slice(0, 150) + ' :: ' + t.slice(t.indexOf('{') + 1, 170).replace(/\s+/g, ' ') + '  <' + src);
        }
      }
    };
    try { walk(sheet.cssRules, null); } catch (e) { }
  }
  out.rules = hits;
  return out;
};

(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  for (const w of [1440, 375]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
    const page = await ctx.newPage();
    await page.goto('http://sinofresh.local/about/', { waitUntil: 'networkidle' });
    await page.evaluate(async () => { await document.fonts.ready; const s = Math.round(innerHeight * 0.8); for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } scrollTo(0, 0); });
    await page.waitForTimeout(900);
    const r = await page.evaluate(PROBE);
    console.log('==================== ' + w + ' ====================');
    console.log(JSON.stringify({ sectionH: r.sectionH, colsDisplay: r.colsDisplay, colsGrid: r.colsGrid, colsGap: r.colsGap, colsWidth: r.colsWidth, docH: r.docH, scrollW: r.scrollW, innerW: r.innerW }, null, 0));
    (r.team || []).forEach(t => {
      console.log(`-- #${t.i} ${t.name}  colDisp=${t.colDisplay} align=${t.colAlignItems} colGap=${t.colGap}`);
      console.log(`   avatar  ${JSON.stringify(t.av)} pad=${t.avPad} bg=${t.avBg} radius=${t.avRadius} disp=${t.avDisplay} just=${t.avJustify} align=${t.avAlignItems}`);
      console.log(`   figure  ${JSON.stringify(t.fig)} disp=${t.figDisplay} margin=${t.figMargin} maxW=${t.figMaxW} overflow=${t.figOverflow}`);
      console.log(`   img     ${JSON.stringify(t.img)} fit=${t.imgFit} pos=${t.imgPos} radius=${t.imgRadius} maxW=${t.imgMaxW} h=${t.imgH} disp=${t.imgDisplay}`);
      console.log(`   h3      ${JSON.stringify(t.h3)} fs=${t.h3Fs} margin=${t.h3Margin}`);
      console.log(`   role    ${JSON.stringify(t.p0)} fs=${t.p0Fs} color=${t.p0Color} margin=${t.p0Margin}`);
      console.log(`   desc    ${JSON.stringify(t.p1)} fs=${t.p1Fs} margin=${t.p1Margin}`);
      console.log(`   gaps    ${JSON.stringify(t.gaps)}   centers ${JSON.stringify(t.centers)}`);
    });
    if (r.rules) { console.log('---- matching rules for #0 ----'); r.rules.forEach(x => console.log('   ' + x)); }
    await page.screenshot({ path: `screenshots/t5_${w}_before.png`, fullPage: false });
    const el = await page.evaluateHandle(() => {
      const secs = [...document.querySelectorAll('.wp-site-blocks > *')];
      return secs.find(s => { const h = s.querySelector('h2'); return h && /^our team$/i.test(h.textContent.trim()); });
    });
    try { await el.asElement().screenshot({ path: `screenshots/t5_${w}_before_sec.png` }); } catch (e) { console.log('sec shot fail ' + e.message); }
    await ctx.close();
  }
  await b.close();
})();
