// Client Stories 手势滑动核验：几何 + 真实触摸滑动 + 吸附 + 复制组 + 截图
const { chromium } = require('playwright-core');
const EXEC = '/Users/meng/.agent-browser/browsers/chrome-153.0.8010.36/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/stories-swipe';
const tag = process.argv[2] || 'after';
const fs = require('fs');
const INIT_CSS = `document.addEventListener('DOMContentLoaded',function(){var s=document.createElement('style');s.textContent='.sf-header{position:static!important}';document.head.appendChild(s);});`;

const GEOM = () => {
  const mq = document.querySelector('.sf-marquee');
  const track = document.querySelector('.sf-marquee__track');
  const groups = [...document.querySelectorAll('.sf-stories__group')];
  const cs = getComputedStyle(mq), tcs = getComputedStyle(track);
  const cards = [...document.querySelectorAll('.sf-story')];
  const r = el => { const b = el.getBoundingClientRect(); return { left: +b.left.toFixed(1), right: +b.right.toFixed(1), top: +(b.top + scrollY).toFixed(1), w: +b.width.toFixed(2), h: +b.height.toFixed(2) }; };
  const fb = document.querySelector('.sf-float-btn');
  const cb = document.querySelector('.sf-cookie-banner');
  const mqr = r(mq);
  const vis = cards.filter(c => c.offsetParent !== null);
  return {
    marquee: { overflowX: cs.overflowX, overflowY: cs.overflowY, marginTop: cs.marginTop, overscrollBehaviorX: cs.overscrollBehaviorX, ...mqr },
    track: { display: tcs.display, width: tcs.width, animationName: tcs.animationName, animationDuration: tcs.animationDuration, animationPlayState: tcs.animationPlayState, transform: tcs.transform },
    groups: groups.map(g => ({ count: g.children.length, ariaHidden: g.getAttribute('aria-hidden'), w: +g.getBoundingClientRect().width.toFixed(1), gap: getComputedStyle(g).gap, padRight: getComputedStyle(g).paddingRight, display: getComputedStyle(g).display })),
    cardCount: cards.length,
    visibleCardCount: vis.length,
    card: cards.length ? { w: cards[0].getBoundingClientRect().width, boxSizing: getComputedStyle(cards[0]).boxSizing, snapAlign: getComputedStyle(cards[0]).scrollSnapAlign, ...r(cards[0]) } : null,
    cardWidths: [...new Set(cards.map(c => +c.getBoundingClientRect().width.toFixed(2)))],
    scrollability: { mqScrollW: mq.scrollWidth, mqClientW: mq.clientWidth, canScroll: mq.scrollWidth > mq.clientWidth + 1, mqScrollLeft: mq.scrollLeft, maxScroll: mq.scrollWidth - mq.clientWidth },
    snapType: cs.scrollSnapType,
    webkitOverflowScrolling: cs.webkitOverflowScrolling || '(unset)',
    scrollbarWidth: cs.scrollbarWidth,
    reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
    visibleNames: vis.map(c => (c.querySelector('h3') || {}).textContent),
    allNames: cards.map(c => (c.querySelector('h3') || {}).textContent),
    floatBtn: fb ? { visible: getComputedStyle(fb).display !== 'none', ...r(fb) } : null,
    cookieBanner: cb ? { display: getComputedStyle(cb).display, ...r(cb) } : null,
    overflow: { docW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth, px: document.documentElement.scrollWidth - document.documentElement.clientWidth },
  };
};

// 当前吸附就位的卡片（左缘对齐滚动口左缘）+ 吸附偏差
const SNAP_STATE = () => {
  const mq = document.querySelector('.sf-marquee');
  const mL = mq.getBoundingClientRect().left;
  const vis = [...document.querySelectorAll('.sf-story')].filter(c => c.offsetParent !== null);
  const offs = vis.map((c, i) => ({ i, name: (c.querySelector('h3') || {}).textContent, off: +(c.getBoundingClientRect().left - mL).toFixed(2) }));
  const snapped = offs.filter(o => Math.abs(o.off) < 2);
  return { scrollLeft: +mq.scrollLeft.toFixed(2), maxScroll: mq.scrollWidth - mq.clientWidth, snapped, offs };
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  const out = {};
  const STATES = [['375', { width: 375, height: 812 }, false], ['768', { width: 768, height: 900 }, false], ['1440', { width: 1440, height: 900 }, false], ['375-rm', { width: 375, height: 812 }, true], ['1440-rm', { width: 1440, height: 900 }, true]];

  for (const [label, vp, rm] of STATES) {
    const ctx = await b.newContext({ viewport: vp, deviceScaleFactor: 2, hasTouch: true, reducedMotion: rm ? 'reduce' : 'no-preference' });
    await ctx.addInitScript(INIT_CSS);
    const page = await ctx.newPage();
    page.setDefaultTimeout(25000);
    await page.goto('http://sinofresh.local/', { waitUntil: 'load', timeout: 30000 });
    await page.waitForSelector('.sf-marquee__track', { timeout: 20000 });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(600);

    const info = await page.evaluate(GEOM);
    const el = await page.$('.sf-marquee');
    await el.scrollIntoViewIfNeeded();
    await page.waitForTimeout(300);

    // ---- 真实触摸滑动手势（CDP，touch 源）----
    const box = await el.boundingBox();
    const cdp = await ctx.newCDPSession(page);
    const y = Math.round(box.y + Math.min(box.height / 2, 120));
    const x = Math.round(vp.width / 2 - (vp.width > 500 ? 0 : 40)); // 避开右侧悬浮按钮
    const swipes = [];
    const snaps = { start: await page.evaluate(SNAP_STATE) };
    const frames = {};
    if (info.scrollability.canScroll) {
      await el.screenshot({ path: `${OUT}/${tag}-swipe-${label}-0.png`, animations: 'disabled' });
      for (let i = 1; i <= 7; i++) {
        await cdp.send('Input.synthesizeScrollGesture', { x, y, xDistance: -340, yDistance: 0, gestureSourceType: 'touch', speed: 800, preventFling: true });
        await page.waitForTimeout(650);
        const st = await page.evaluate(SNAP_STATE);
        swipes.push(st);
        if (i === 2) { frames['2'] = await el.screenshot({ path: `${OUT}/${tag}-swipe-${label}-2.png`, animations: 'disabled' }); }
        if (st.scrollLeft >= st.maxScroll - 1) break;
      }
      await el.screenshot({ path: `${OUT}/${tag}-swipe-${label}-end.png`, animations: 'disabled' });
    }
    info.swipe = { canScroll: info.scrollability.canScroll, steps: swipes.map(s => s.scrollLeft), snappedAfterEach: swipes.map(s => s.snapped.map(x => x.i + ':' + x.name)), finalSnap: swipes.length ? swipes[swipes.length - 1].snapped.map(x => x.i + ':' + x.name) : [], finalScrollLeft: swipes.length ? swipes[swipes.length - 1].scrollLeft : info.scrollability.mqScrollLeft, maxScroll: info.scrollability.maxScroll, finalOffs: swipes.length ? swipes[swipes.length - 1].offs : [] };

    out[label] = info;
    console.log(`\n=== ${label} (rm=${info.reducedMotion}) ===`);
    console.log(`  marquee: overflowX=${info.marquee.overflowX} overY=${info.marquee.overflowY} overscrollX=${info.marquee.overscrollBehaviorX} w=${info.marquee.w} scrollW=${info.scrollability.mqScrollW} clientW=${info.scrollability.mqClientW} snap=${info.snapType}`);
    console.log(`  track: animation=${info.track.animationName} ${info.track.animationDuration}  transform=${String(info.track.transform).slice(0, 34)}`);
    console.log(`  groups: ${JSON.stringify(info.groups)}`);
    console.log(`  DOM 卡=${info.cardCount} 可见卡=${info.visibleCardCount} 宽度集合=${JSON.stringify(info.cardWidths)} box=${info.card ? info.card.boxSizing : '-'} snapAlign=${info.card ? info.card.snapAlign : '-'}`);
    console.log(`  可见姓名: ${info.visibleNames.join(' | ')}`);
    console.log(`  scrollbar-width=${info.scrollbarWidth}  -webkit-overflow-scrolling=${info.webkitOverflowScrolling}`);
    console.log(`  手势滑动: canScroll=${info.swipe.canScroll} 步数=${info.swipe.steps.length} scrollLeft 轨迹=${JSON.stringify(info.swipe.steps)} max=${info.swipe.maxScroll.toFixed(1)}`);
    console.log(`  每次吸附: ${JSON.stringify(info.swipe.snappedAfterEach)}`);
    console.log(`  末次对齐偏差: ${JSON.stringify(info.swipe.finalOffs)}`);
    console.log(`  溢出: ${info.overflow.px}px`);
    await ctx.close();
  }
  await b.close();
  fs.writeFileSync(`${OUT}/${tag}-report.json`, JSON.stringify(out, null, 2));
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
