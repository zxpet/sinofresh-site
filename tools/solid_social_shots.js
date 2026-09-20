// Solid social icons v2.7.1: geometry + footer screenshots (desktop 1440 / mobile 375)
const { chromium } = require('playwright-core');
const OUT = 'screenshots/social-2700';

(async () => {
  const b = await chromium.launch({ channel: 'chrome' });

  const dctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const dp = await dctx.newPage();
  await dp.goto('http://sinofresh.local/', { waitUntil: 'networkidle' });
  const d = await dp.evaluate(() => {
    const s = document.querySelector('.sf-social');
    const a = [...s.querySelectorAll('a')];
    const gaps = a.slice(1).map((x, i) => +(x.getBoundingClientRect().left - a[i].getBoundingClientRect().right).toFixed(1));
    const fills = a.map(x => getComputedStyle(x.querySelector('svg')).fill);
    return {
      n: a.length,
      svgW: a.map(x => Math.round(x.querySelector('svg').getBoundingClientRect().width)),
      gaps: [...new Set(gaps)],
      solid: fills.every(f => f !== 'none'),
      rowW: Math.round(s.getBoundingClientRect().width),
    };
  });
  console.log('DESKTOP FOOTER:', JSON.stringify(d));
  const dfoot = await dp.evaluate(() => {
    const r = document.querySelector('.sf-social').getBoundingClientRect();
    return { y: Math.round(r.top + scrollY), h: Math.round(r.height) };
  });
  await dp.screenshot({ path: `${OUT}/solid-desktop-footer.png`, fullPage: true, clip: { x: 0, y: Math.max(0, dfoot.y - 80), width: 1440, height: dfoot.h + 360 } });
  await dctx.close();

  const mctx = await b.newContext({ viewport: { width: 375, height: 720 }, isMobile: true });
  const mp = await mctx.newPage();
  await mp.goto('http://sinofresh.local/', { waitUntil: 'networkidle' });
  const m = await mp.evaluate(() => {
    const s = document.querySelector('.sf-social');
    const a = [...s.querySelectorAll('a')];
    const r = s.getBoundingClientRect();
    const gaps = a.slice(1).map((x, i) => +(x.getBoundingClientRect().left - a[i].getBoundingClientRect().right).toFixed(1));
    return {
      n: a.length,
      svgW: a.map(x => Math.round(x.querySelector('svg').getBoundingClientRect().width)),
      gaps: [...new Set(gaps)],
      oneRow: new Set(a.map(x => Math.round(x.getBoundingClientRect().top))).size === 1,
      overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      rowW: Math.round(r.width),
    };
  });
  console.log('MOBILE FOOTER:', JSON.stringify(m));
  const mfoot = await mp.evaluate(() => {
    const r = document.querySelector('.sf-social').getBoundingClientRect();
    return { y: Math.round(r.top + scrollY) };
  });
  await mp.screenshot({ path: `${OUT}/solid-mobile-footer-375.png`, fullPage: true, clip: { x: 0, y: Math.max(0, mfoot.y - 200), width: 375, height: 420 } });
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
