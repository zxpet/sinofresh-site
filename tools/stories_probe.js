// Client Stories 区块现状探测：结构 / 动画 / 宽度 / 溢出 / 与浮层关系
const { chromium } = require('playwright-core');
const EXEC = '/Users/meng/.agent-browser/browsers/chrome-153.0.8010.36/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const tag = process.argv[2] || 'before';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/stories-swipe';
const fs = require('fs');
const INIT_CSS = `document.addEventListener('DOMContentLoaded',function(){var s=document.createElement('style');s.textContent='.sf-header{position:static!important}';document.head.appendChild(s);});`;

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  const out = {};

  for (const [label, vp, rm] of [['375', { width: 375, height: 812 }, false], ['768', { width: 768, height: 900 }, false], ['1440', { width: 1440, height: 900 }, false], ['375-rm', { width: 375, height: 812 }, true]]) {
    const ctx = await b.newContext({ viewport: vp, deviceScaleFactor: 2, reducedMotion: rm ? 'reduce' : 'no-preference' });
    await ctx.addInitScript(INIT_CSS);
    const page = await ctx.newPage();
    page.setDefaultTimeout(25000);
    await page.goto('http://sinofresh.local/', { waitUntil: 'load', timeout: 30000 });
    await page.waitForSelector('.sf-marquee__track', { timeout: 20000 });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(600);

    const info = await page.evaluate(() => {
      const mq = document.querySelector('.sf-marquee');
      const track = document.querySelector('.sf-marquee__track');
      const groups = [...document.querySelectorAll('.sf-stories__group')];
      const cs = getComputedStyle(mq);
      const tcs = getComputedStyle(track);
      const cards = [...document.querySelectorAll('.sf-story')];
      const r = el => { const b = el.getBoundingClientRect(); return { left: +b.left.toFixed(1), right: +b.right.toFixed(1), top: +(b.top + scrollY).toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1) }; };
      const fb = document.querySelector('.sf-float-btn');
      const cb = document.querySelector('.sf-cookie-banner');
      const mqr = r(mq);
      return {
        marquee: { overflowX: cs.overflowX, overflowY: cs.overflowY, marginTop: cs.marginTop, ...mqr },
        track: { display: tcs.display, width: tcs.width, animationName: tcs.animationName, animationDuration: tcs.animationDuration, animationPlayState: tcs.animationPlayState, transform: tcs.transform, scrollSnapType: tcs.scrollSnapType, overflowX: tcs.overflowX },
        groups: groups.map(g => ({ count: g.children.length, ariaHidden: g.getAttribute('aria-hidden'), w: +g.getBoundingClientRect().width.toFixed(1), gap: getComputedStyle(g).gap, padRight: getComputedStyle(g).paddingRight, display: getComputedStyle(g).display })),
        cardCount: cards.length,
        card: cards.length ? { w: cards[0].getBoundingClientRect().width, snapAlign: getComputedStyle(cards[0]).scrollSnapAlign, ...r(cards[0]) } : null,
        cardWidths: [...new Set(cards.map(c => Math.round(c.getBoundingClientRect().width)))],
        scrollability: { mqScrollW: mq.scrollWidth, mqClientW: mq.clientWidth, canScroll: mq.scrollWidth > mq.clientWidth + 1, mqScrollLeft: mq.scrollLeft, trackScrollW: track.scrollWidth, trackClientW: track.clientWidth },
        webkitOverflowScrolling: cs.webkitOverflowScrolling || '(unset)',
        reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
        // 可见卡片（在 marquee 视口内）
        visibleCards: cards.map((c, i) => { const b = c.getBoundingClientRect(); return { i, name: (c.querySelector('h3') || {}).textContent, left: +b.left.toFixed(0), right: +b.right.toFixed(0), inView: b.right > mqr.left && b.left < mqr.right }; }).filter(c => c.inView).map(c => c.i + ':' + c.name),
        floatBtn: fb ? { text: fb.textContent.replace(/\s+/g, ' ').trim().slice(0, 30), ...r(fb) } : null,
        cookieBanner: cb ? { display: getComputedStyle(cb).display, ...r(cb) } : null,
        overflow: { docW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth, px: document.documentElement.scrollWidth - document.documentElement.clientWidth },
      };
    });
    out[label] = info;
    console.log(`\n=== ${label} (reducedMotion=${info.reducedMotion}) ===`);
    console.log(`  track: animation=${info.track.animationName} ${info.track.animationDuration} ${info.track.animationPlayState}  transform=${info.track.transform.slice(0, 40)}  snap=${info.track.scrollSnapType}  overflowX=${info.track.overflowX}`);
    console.log(`  marquee: overflowX=${info.marquee.overflowX}  w=${info.marquee.w}  scrollW=${info.scrollability.mqScrollW} clientW=${info.scrollability.mqClientW} canScroll=${info.scrollability.canScroll}  -webkit-overflow-scrolling=${info.webkitOverflowScrolling}`);
    console.log(`  groups: ${JSON.stringify(info.groups)}`);
    console.log(`  卡片数=${info.cardCount}  宽度集合=${JSON.stringify(info.cardWidths)}  snapAlign=${info.card ? info.card.snapAlign : '-'}`);
    console.log(`  视口内可见卡片: ${info.visibleCards.join(' | ')}`);
    console.log(`  浮层: float=${info.floatBtn ? info.floatBtn.text + ' t=' + info.floatBtn.top + ' h=' + info.floatBtn.h : 'none'}  cookie=${info.cookieBanner ? info.cookieBanner.display + ' t=' + info.cookieBanner.top : 'none'}`);
    console.log(`  溢出: ${info.overflow.px}px`);

    const el = await page.$('.sf-marquee');
    await el.scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);
    await el.screenshot({ path: `${OUT}/${tag}-stories-${label}.png`, animations: 'disabled' });
    await ctx.close();
  }
  await b.close();
  fs.writeFileSync(`${OUT}/${tag}-report.json`, JSON.stringify(out, null, 2));
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
