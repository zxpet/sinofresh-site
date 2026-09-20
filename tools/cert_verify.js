const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  // ---- desktop 1440 ----
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  for (const [name, url] of [['home','http://sinofresh.local/'],['quality','http://sinofresh.local/quality/']]) {
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.evaluate(async () => { await document.fonts.ready; });
    const m1 = await page.evaluate(() => {
      const t = document.querySelector('.sf-cert-marquee__track');
      const card = document.querySelector('.sf-cert');
      const title = card.querySelector('.sf-cert__title');
      const sub = card.querySelector('.sf-cert__sub');
      return { x1: getComputedStyle(t).transform, anim: getComputedStyle(t).animationName,
               cardW: Math.round(card.getBoundingClientRect().width),
               gapTitleSub: Math.round(sub.getBoundingClientRect().top - title.getBoundingClientRect().bottom),
               cards: document.querySelectorAll('.sf-certs-group')[0].children.length,
               dupHidden: getComputedStyle(document.querySelector('.sf-certs-group[aria-hidden]')).display };
    });
    await page.waitForTimeout(1000);
    const m2 = await page.evaluate(() => getComputedStyle(document.querySelector('.sf-cert-marquee__track')).transform);
    await page.hover('.sf-cert-marquee');
    await page.waitForTimeout(300);
    const m3 = await page.evaluate(() => getComputedStyle(document.querySelector('.sf-cert-marquee__track')).animationPlayState);
    const ox = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    console.log(name + ' desktop: anim=' + m1.anim + ' moving=' + (m1.x1 !== m2) + ' cardW=' + m1.cardW + ' gapTitleSub=' + m1.gapTitleSub + 'px cards=' + m1.cards + ' dup=' + m1.dupHidden + ' hover=' + m3 + ' overflowX=' + ox);
  }
  await ctx.close();
  // ---- mobile 375 ----
  const mctx = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
  const m = await mctx.newPage();
  for (const [name, url] of [['home','http://sinofresh.local/'],['quality','http://sinofresh.local/quality/']]) {
    await m.goto(url, { waitUntil: 'networkidle' });
    const r = await m.evaluate(() => {
      const mq = document.querySelector('.sf-cert-marquee');
      const cs = getComputedStyle(document.querySelector('.sf-cert-marquee__track'));
      return { ov: document.documentElement.scrollWidth - document.documentElement.clientWidth,
               anim: cs.animationName,
               scrollable: mq.scrollWidth > mq.clientWidth,
               snap: getComputedStyle(mq).scrollSnapType,
               dup: getComputedStyle(document.querySelector('.sf-certs-group[aria-hidden]')).display,
               dots: getComputedStyle(document.querySelector('.sf-certs-dots')).display };
    });
    console.log(name + ' mobile: overflowX=' + r.ov + ' anim=' + r.anim + ' scrollable=' + r.scrollable + ' snap=' + r.snap + ' dup=' + r.dup + ' dots=' + r.dots);
  }
  await mctx.close();
  // ---- reduced motion ----
  const rctx = await b.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const rp = await rctx.newPage();
  await rp.goto('http://sinofresh.local/', { waitUntil: 'networkidle' });
  const rm = await rp.evaluate(() => {
    const t = document.querySelector('.sf-cert-marquee__track');
    return { anim: getComputedStyle(t).animationName, x1: getComputedStyle(t).transform,
             visible: [...document.querySelectorAll('.sf-certs-group')[0].children].every(c => c.getBoundingClientRect().width > 0) };
  });
  await rp.waitForTimeout(600);
  const rm2 = await rp.evaluate(() => getComputedStyle(document.querySelector('.sf-cert-marquee__track')).transform);
  console.log('reduced-motion: anim=' + rm.anim + ' static=' + (rm.x1 === rm2) + ' allCardsVisible=' + rm.visible);
  await rctx.close();
  await b.close();
})();
