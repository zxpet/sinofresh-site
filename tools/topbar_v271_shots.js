// Topbar rework v2.7.1: geometry + screenshots (desktop 1440 / mobile 375)
const { chromium } = require('playwright-core');
const OUT = 'screenshots/social-2700';

(async () => {
  const b = await chromium.launch({ channel: 'chrome' });

  // --- desktop 1440 ---
  const dctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const dp = await dctx.newPage();
  await dp.goto('http://sinofresh.local/', { waitUntil: 'networkidle' });
  const d = await dp.evaluate(() => {
    const top = document.querySelector('.sf-topbar');
    const tb = top.getBoundingClientRect();
    const badges = top.querySelector('.sf-topbar-badges').getBoundingClientRect();
    const meta = top.querySelector('.sf-topbar__meta').getBoundingClientRect();
    const email = top.querySelector('.sf-topbar__email').getBoundingClientRect();
    const emailSvg = top.querySelector('.sf-topbar__email svg').getBoundingClientRect();
    const anchors = [...top.querySelectorAll('a')];
    return {
      topbarH: Math.round(tb.height),
      badgesBeforeMeta: badges.left < meta.left,
      order: badges.left < meta.left && meta.left < email.left ? 'badges>hours>email' : 'check',
      anchors: anchors.map(a => a.href),
      emailCenterOffset: +( (emailSvg.top + emailSvg.height / 2) - (email.top + email.height / 2) ).toFixed(1),
      socialInTopbar: top.querySelectorAll('.sf-topbar-social').length,
    };
  });
  console.log('DESKTOP:', JSON.stringify(d));
  await dp.screenshot({ path: `${OUT}/v271-desktop-topbar.png`, clip: { x: 0, y: 0, width: 1440, height: 90 } });
  await dctx.close();

  // --- mobile 375 ---
  const mctx = await b.newContext({ viewport: { width: 375, height: 720 }, isMobile: true });
  const mp = await mctx.newPage();
  await mp.goto('http://sinofresh.local/', { waitUntil: 'networkidle' });
  const m = await mp.evaluate(() => {
    const top = document.querySelector('.sf-topbar');
    const cs = getComputedStyle(top);
    const email = top.querySelector('.sf-topbar__email');
    const er = email.getBoundingClientRect();
    return {
      topbarH: Math.round(top.getBoundingClientRect().height),
      padding: cs.paddingTop + ' / ' + cs.paddingLeft,
      leftGroupHidden: getComputedStyle(top.querySelector('.sf-topbar-left')).display === 'none',
      emailCentered: Math.abs(er.left + er.width / 2 - 187.5) < 8,
      overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    };
  });
  console.log('MOBILE:', JSON.stringify(m));
  await mp.screenshot({ path: `${OUT}/v271-mobile-topbar-375.png`, clip: { x: 0, y: 0, width: 375, height: 130 } });

  // --- footer icons sanity (both widths) ---
  const foot = await mp.evaluate(() => {
    const s = document.querySelector('.sf-social');
    const a = [...s.querySelectorAll('a')];
    return { n: a.length, svgW: a[0].querySelector('svg').getBoundingClientRect().width };
  });
  console.log('MOBILE FOOTER:', JSON.stringify(foot));

  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
