// Single post scan: featured image / meta / body typography measurements + screenshots
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const EXEC = '/Users/meng/.agent-browser/browsers/chrome-153.0.8010.36/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/single-scan';
const URL = 'http://sinofresh.local/how-to-choose-a-private-label-pet-supplement-manufacturer/';

const R = el => { if (!el) return null; const r = el.getBoundingClientRect(); return { w: +r.width.toFixed(1), h: +r.height.toFixed(1) }; };

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const tag = process.argv[2] || 'scan';
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  const report = {};

  for (const vp of [{ w: 1440, h: 900 }, { w: 375, h: 812 }]) {
    const ctx = await b.newContext({ viewport: { width: vp.w, height: vp.h } });
    const page = await ctx.newPage();
    await page.goto(URL, { waitUntil: 'load', timeout: 30000 });
    await page.evaluate(() => document.fonts.ready);
    // scroll through to force lazy-load
    await page.evaluate(async () => {
      for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); }
      window.scrollTo(0, 0);
    });
    await page.waitForFunction(() => { const i = document.querySelector('.wp-block-post-featured-image img'); return !i || (i.complete && i.naturalWidth > 0); }, { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(400);

    const d = await page.evaluate(() => {
      const R = el => { if (!el) return null; const r = el.getBoundingClientRect(); return { w: +r.width.toFixed(1), h: +r.height.toFixed(1) }; };
      const q = s => document.querySelector(s);
      const CS = el => el ? getComputedStyle(el) : null;
      const img = q('.wp-block-post-featured-image img');
      const fwrap = q('.wp-block-post-featured-image');
      const fig = q('.wp-block-post-featured-image figure');
      const h1 = q('h1');
      const heroSec = fwrap && fwrap.closest('section');
      const contentSec = q('.wp-block-post-content') && q('.wp-block-post-content').closest('section');
      const content = q('.wp-block-post-content');
      const bodyW = q('main') || document.body;
      const entry = content ? content.querySelector('.entry-content') : null;
      const paras = content ? [...content.querySelectorAll('p')].filter(p => p.textContent.trim().length > 40) : [];
      const p0 = paras[0];
      const h2 = content ? content.querySelector('h2') : null;
      const h3 = content ? content.querySelector('h3') : null;
      const metaRow = h1 && h1.parentElement.querySelector('.wp-block-group');
      const cat = document.querySelector('.wp-block-post-terms a, .wp-block-post-terms');
      const prev = q('.sf-prevnext');
      const rel = q('.sf-related');
      const cta = [...document.querySelectorAll('section')].find(s => s.textContent.includes('Ready to Launch'));
      const sfFp = getComputedStyle(fwrap || document.body);
      const imgRect = img ? img.getBoundingClientRect() : null;
      // measure first visible screen at scrollY=0: what occupies viewport
      const blocks = [];
      for (const el of [q('header'), heroSec && heroSec.parentElement, document.body]) break;
      return {
        docH: document.body.scrollHeight,
        viewport: { w: innerWidth, h: innerHeight },
        featured: {
          wrap: R(fwrap), fig: R(fig), img: imgRect ? { w: +imgRect.width.toFixed(1), h: +imgRect.height.toFixed(1), top: +imgRect.top.toFixed(1) } : null,
          natural: img ? { w: img.naturalWidth, h: img.naturalHeight, src: img.currentSrc.split('/').pop() } : null,
          objectFit: img ? CS(img).objectFit : null,
          wrapCSS: fwrap ? { aspectRatio: CS(fwrap).aspectRatio, maxHeight: CS(fwrap).maxHeight, width: CS(fwrap).width, maxWidth: CS(fwrap).maxWidth, marginInline: CS(fwrap).marginInline, radius: CS(fwrap).borderRadius, overflow: CS(fwrap).overflow } : null,
          imgCSS: img ? { width: CS(img).width, height: CS(img).height, aspectRatio: CS(img).aspectRatio, maxHeight: CS(img).maxHeight, radius: CS(img).borderRadius } : null,
          figCSS: fig ? { margin: CS(fig).margin, maxWidth: CS(fig).maxWidth, aspectRatio: CS(fig).aspectRatio } : null,
          vhPct: imgRect ? +(imgRect.height / innerHeight * 100).toFixed(1) : null,
          wideClass: fwrap ? fwrap.className : null,
          sectionPad: heroSec ? { t: CS(heroSec).paddingTop, b: CS(heroSec).paddingBottom, bg: CS(heroSec).backgroundColor } : null,
        },
        heroHead: {
          h1: { rect: R(h1), fontSize: h1 ? CS(h1).fontSize : null, lh: h1 ? CS(h1).lineHeight : null, color: h1 ? CS(h1).color : null, weight: h1 ? CS(h1).fontWeight : null, margin: h1 ? CS(h1).margin : null },
          cat: cat ? { text: cat.textContent.trim(), fs: CS(cat).fontSize, color: CS(cat).color, ls: CS(cat).letterSpacing, margin: CS(cat).margin } : null,
          meta: metaRow ? { text: metaRow.textContent.replace(/\s+/g, ' ').trim().slice(0, 80), fs: CS(metaRow).fontSize, color: CS(metaRow).color, gap: CS(metaRow).gap, marginTop: CS(metaRow).marginTop, children: [...metaRow.children].map(c => c.textContent.trim().slice(0, 24)) } : null,
          sectionPad: h1 && h1.closest('section') ? { t: CS(h1.closest('section')).paddingTop, b: CS(h1.closest('section')).paddingBottom } : null,
          heroSecH: h1 ? +h1.closest('section').getBoundingClientRect().height.toFixed(1) : null,
        },
        body: {
          contentBox: R(entry || content),
          constrained: content ? [...content.querySelectorAll(':scope > *')].slice(0, 3).map(c => ({ cls: (c.className || '').toString().slice(0, 60), w: +c.getBoundingClientRect().width.toFixed(1) })) : [],
          p: p0 ? { fs: CS(p0).fontSize, lh: CS(p0).lineHeight, color: CS(p0).color, mb: CS(p0).marginBottom, rect: R(p0) } : null,
          h2: h2 ? { fs: CS(h2).fontSize, lh: CS(h2).lineHeight, mt: CS(h2).marginTop, mb: CS(h2).marginBottom, color: CS(h2).color } : null,
          h3: h3 ? { fs: CS(h3).fontSize, lh: CS(h3).lineHeight, mt: CS(h3).marginTop, mb: CS(h3).marginBottom } : null,
          nParas: paras.length, nH2: content ? content.querySelectorAll('h2').length : 0,
        },
        prevnext: prev ? { rect: R(prev), display: CS(prev).display } : null,
        related: rel ? { h: +rel.getBoundingClientRect().height.toFixed(1), cols: rel.querySelectorAll('.wp-block-post-template > *').length } : null,
        cta: cta ? { h: +cta.getBoundingClientRect().height.toFixed(1) } : null,
      };
    });
    report[vp.w] = d;

    // screenshots: first screen (hero + featured), mid-body, plus section shots
    await page.screenshot({ path: path.join(OUT, `${tag}-${vp.w}-viewport0.png`) });   // 首屏
    const imgTop = await page.evaluate(() => { const i = document.querySelector('.wp-block-post-featured-image img'); return i ? i.getBoundingClientRect().top + scrollY : 0; });
    await page.evaluate(t => window.scrollTo(0, t + 80), imgTop);
    await page.waitForTimeout(250);
    await page.screenshot({ path: path.join(OUT, `${tag}-${vp.w}-featured.png`) });
    const bodyMid = await page.evaluate(() => { const ps = [...document.querySelectorAll('.wp-block-post-content p')]; const p = ps[Math.floor(ps.length / 2)]; return p ? p.getBoundingClientRect().top + scrollY - 200 : 0; });
    await page.evaluate(y => window.scrollTo(0, y), bodyMid);
    await page.waitForTimeout(250);
    await page.screenshot({ path: path.join(OUT, `${tag}-${vp.w}-bodymid.png`) });
    await ctx.close();
    console.log(`--- ${vp.w} ---`);
    console.log(JSON.stringify(d, null, 1).slice(0, 4200));
  }
  fs.writeFileSync(path.join(OUT, `${tag}-report.json`), JSON.stringify(report, null, 1));
  await b.close();
  console.log('\nDONE -> ' + OUT);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
