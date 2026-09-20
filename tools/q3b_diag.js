const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  const c = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await c.newPage();

  // ---- /faq/ : why is the section h2 still 800 ----
  await p.goto('http://sinofresh.local/faq/', { waitUntil: 'networkidle' });
  const faq = await p.evaluate(() => {
    const f = document.querySelector('.sf-faq');
    const sec = f.closest('section');
    const h2 = Array.from(sec.children).find(x => x.tagName === 'H2');
    const cs = getComputedStyle(sec);
    const h2cs = getComputedStyle(h2);
    // which rules set h2 max-width?
    const rules = [];
    for (const sheet of document.styleSheets) {
      let list; try { list = sheet.cssRules; } catch (e) { continue; }
      const walk = (rs) => {
        for (const r of rs) {
          if (r.cssRules && r.cssRules.length && !r.selectorText) { walk(r.cssRules); continue; }
          if (!r.selectorText) continue;
          try { if (h2.matches(r.selectorText) && /max-width|content-size/.test(r.style.cssText)) rules.push({ sel: r.selectorText.slice(0, 90), css: r.style.cssText.slice(0, 120), href: (sheet.href || 'inline').split('/').pop() }); } catch (e) { }
        }
      };
      walk(list);
    }
    return {
      secClass: sec.className,
      secStyleAttr: sec.getAttribute('style'),
      secVarContent: cs.getPropertyValue('--wp--style--global--content-size').trim(),
      secVarWide: cs.getPropertyValue('--wp--style--global--wide-size').trim(),
      h2Class: h2.className,
      h2W: Math.round(h2.getBoundingClientRect().width),
      h2MaxW: h2cs.maxWidth,
      h2Margin: h2cs.marginLeft + ' / ' + h2cs.marginRight,
      faqW: Math.round(f.getBoundingClientRect().width),
      faqVarContent: getComputedStyle(f).getPropertyValue('--wp--style--global--content-size').trim(),
      rules: rules
    };
  });
  console.log('/faq/ DIAGNOSIS');
  console.log(JSON.stringify(faq, null, 1));

  // ---- quality: measure the real rails ----
  await p.goto('http://sinofresh.local/quality/', { waitUntil: 'networkidle' });
  await p.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
  const q = await p.evaluate(() => {
    const step = document.querySelector('.sf-qs__step');
    const r = step.getBoundingClientRect();
    return {
      stepCols: getComputedStyle(step).gridTemplateColumns,
      stepW: Math.round(r.width),
      numBox: (() => { const n = step.querySelector('.sf-qs__num'); const b = n.getBoundingClientRect(); return { w: Math.round(b.width), h: Math.round(b.height), left: Math.round(b.left - r.left), top: Math.round(b.top - r.top) }; })(),
      contentLeft: Math.round(step.querySelector('.sf-qs__content').getBoundingClientRect().left - r.left),
      contentW: Math.round(step.querySelector('.sf-qs__content').getBoundingClientRect().width),
      textW: Math.round(step.querySelector('.sf-qs__text').getBoundingClientRect().width),
      imgW: Math.round(step.querySelector('img').getBoundingClientRect().width),
      palStep: (() => { const s = document.querySelector('.sf-pal__step'); const b = s.getBoundingClientRect(); return { w: Math.round(b.width), h: Math.round(b.height) }; })(),
      palBefore: (() => { const s = document.querySelectorAll('.sf-pal__step')[1]; const cs = getComputedStyle(s, '::before'); return { content: cs.content, left: cs.left, top: cs.top, w: cs.width, h: cs.height, bg: cs.backgroundColor }; })(),
      palAfter: (() => { const s = document.querySelectorAll('.sf-pal__step')[1]; const cs = getComputedStyle(s, '::after'); return { content: cs.content, left: cs.left, top: cs.top, transform: cs.transform, borderTop: cs.borderTopColor }; })(),
      certPlaceholder: (() => { const ph = document.querySelector('.sf-certrow__media--placeholder'); const b = ph.getBoundingClientRect(); return { w: Math.round(b.width), h: Math.round(b.height), boxSizing: getComputedStyle(ph).boxSizing }; })()
    };
  });
  console.log('\n/quality/ RE-MEASURE');
  console.log(JSON.stringify(q, null, 1));
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
