// Latest Articles 区块：图片填充 bug + 高度构成 探测
const { chromium } = require('playwright-core');
const EXEC = '/Users/meng/.agent-browser/browsers/chrome-153.0.8010.36/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/article-cover';
const fs = require('fs');
const tag = process.argv[2] || 'before';
const INIT_CSS = `document.addEventListener('DOMContentLoaded',function(){var s=document.createElement('style');s.textContent='.sf-header{position:static!important}';document.head.appendChild(s);});`;

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  const out = {};
  for (const [label, w] of [['1440', 1440], ['1280', 1280], ['1024', 1024], ['375', 375]]) {
    const ctx = await b.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 2 });
    await ctx.addInitScript(INIT_CSS);
    const page = await ctx.newPage();
    page.setDefaultTimeout(25000);
    await page.goto('http://sinofresh.local/', { waitUntil: 'load', timeout: 30000 });
    await page.waitForSelector('.sf-slot--cover', { timeout: 20000 });
    await page.evaluate(() => document.fonts.ready);
    // 先滚到区块并等三张封面真正解码（懒加载 + 首图未进视口时 naturalWidth=0）
    await page.evaluate(() => document.querySelector('.sf-slot--cover').closest('section').scrollIntoView({ block: 'center' }));
    await page.waitForFunction(() => [...document.querySelectorAll('.sf-slot--cover img')].every(i => i.complete && i.naturalWidth > 0), { timeout: 15000 });
    await page.waitForTimeout(400);

    const info = await page.evaluate(() => {
      const slot0 = document.querySelector('.sf-slot--cover');
      const sec = slot0.closest('section');
      const R = el => { const b = el.getBoundingClientRect(); return { w: +b.width.toFixed(2), h: +b.height.toFixed(2), top: +(b.top + scrollY).toFixed(1), left: +b.left.toFixed(1) }; };
      const cs = getComputedStyle(slot0);
      const img0 = slot0.querySelector('img');
      const fig0 = slot0.querySelector('.wp-block-image');
      const ics = getComputedStyle(img0);
      // 各 slot 明细
      const slots = [...document.querySelectorAll('.sf-slot--cover')].map(s => {
        const im = s.querySelector('img'), fg = s.querySelector('.wp-block-image');
        const sb = s.getBoundingClientRect(), ib = im.getBoundingClientRect(), fb = fg.getBoundingClientRect();
        return {
          slot: { w: +sb.width.toFixed(2), h: +sb.height.toFixed(2) },
          figure: { w: +fb.width.toFixed(2), h: +fb.height.toFixed(2), left: +fb.left.toFixed(2), display: getComputedStyle(fg).display },
          img: { w: +ib.width.toFixed(2), h: +ib.height.toFixed(2), left: +ib.left.toFixed(2), top: +ib.top.toFixed(2), natW: im.naturalWidth, natH: im.naturalHeight, ratio: +(im.naturalWidth / im.naturalHeight).toFixed(3), src: im.currentSrc.split('/').pop() },
          gapLeft: +(ib.left - sb.left).toFixed(2),
          gapRight: +(sb.right - ib.right).toFixed(2),
          gapBottom: +(ib.bottom - sb.bottom).toFixed(2),
          gapTop: +(ib.top - sb.top).toFixed(2),
          slotOverflow: getComputedStyle(s).overflow,
          slotRadius: [cs2 => 0, 'borderTopLeftRadius', 'borderTopRightRadius', 'borderBottomRightRadius', 'borderBottomLeftRadius'].slice(1).map(k => getComputedStyle(s)[k]).join(' '),
          imgRadius: getComputedStyle(im).borderRadius,
          imgObjectFit: getComputedStyle(im).objectFit,
          imgAspect: getComputedStyle(im).aspectRatio,
          imgHeightCss: getComputedStyle(im).height,
        };
      });
      // 区块内部高度构成
      const kids = [...sec.children].map(k => ({ tag: k.tagName, cls: k.className.split(' ').slice(0, 3).join('.'), ...R(k) })).filter(k => !k.cls.includes('sf-'));
      const kids2 = [...sec.children].map(k => { const ks = getComputedStyle(k); return { tag: k.tagName, cls: k.className.split(' ').filter(c => c.startsWith('sf-') || c.startsWith('has-')).slice(0, 3).join('.'), ...R(k), mt: ks.marginTop, mb: ks.marginBottom }; });
      return {
        section: { ...R(sec), pad: getComputedStyle(sec).paddingTop + ' / ' + getComputedStyle(sec).paddingBottom, bg: getComputedStyle(sec).backgroundColor },
        sectionKids: kids2,
        slot0: { ...R(slot0), radius: cs.borderTopLeftRadius + ' ' + cs.borderTopRightRadius + ' ' + cs.borderBottomRightRadius + ' ' + cs.borderBottomLeftRadius, overflow: cs.overflow, aspect: cs.aspectRatio, display: cs.display, alignItems: cs.alignItems, justifyItems: cs.justifyItems },
        img0: { ...R(img0), radius: ics.borderRadius, objectFit: ics.objectFit, aspect: ics.aspectRatio, heightCss: ics.height, natW: img0.naturalWidth, natH: img0.naturalHeight, src: img0.currentSrc.split('/').pop() },
        figure0: { ...R(fig0), display: getComputedStyle(fig0).display },
        slots,
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      };
    });
    out[label] = info;
    console.log(`\n=== ${label} ===`);
    console.log(`  区块高=${info.section.h}px (pad ${info.section.pad})`);
    console.log(`  内部构成: ${info.sectionKids.map(k => `${k.cls || k.tag}=${k.h}(mt${k.mt}/mb${k.mb})`).join('  ')}`);
    console.log(`  slot: ${info.slot0.w}×${info.slot0.h} aspect=${info.slot0.aspect} radius="${info.slot0.radius}" overflow=${info.slot0.overflow} grid=${info.slot0.display}/${info.slot0.alignItems}/${info.slot0.justifyItems}`);
    console.log(`  figure: ${info.figure0.w}×${info.figure0.h} display=${info.figure0.display}`);
    console.log(`  img: ${info.img0.w}×${info.img0.h} 自然=${info.img0.natW}×${info.img0.natH} objectFit=${info.img0.objectFit} aspect=${info.img0.aspect} height=${info.img0.heightCss} radius=${info.img0.radius} src=${info.img0.src}`);
    info.slots.forEach((s, i) => console.log(`  卡${i + 1}: slot ${s.slot.w}×${s.slot.h} | fig ${s.figure.w}×${s.figure.h} | img ${s.img.w}×${s.img.h} 自然比=${s.img.ratio} | 内边距 L${s.gapLeft} R${s.gapRight} T${s.gapTop} B${s.gapBottom} | slotRadius=${s.slotRadius} imgRadius=${s.imgRadius} overflow=${s.slotOverflow}`));
    console.log(`  页面横向溢出: ${info.overflow}px`);

    const el = await page.$('.sf-slot--cover');
    const secEl = await page.evaluateHandle(() => document.querySelector('.sf-slot--cover').closest('section'));
    await secEl.asElement().scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    await secEl.asElement().screenshot({ path: `${OUT}/${tag}-section-${label}.png`, animations: 'disabled' });
    await el.screenshot({ path: `${OUT}/${tag}-slot-${label}.png`, animations: 'disabled' });
    await ctx.close();
  }
  await b.close();
  fs.writeFileSync(`${OUT}/${tag}-report.json`, JSON.stringify(out, null, 2));
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
