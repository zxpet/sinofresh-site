// 各宽度下 Client Stories 卡片实测盒模型（改前）
const { chromium } = require('playwright-core');
const EXEC = '/Users/meng/.agent-browser/browsers/chrome-153.0.8010.36/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  for (const w of [375, 480, 640, 768, 769, 900, 1440]) {
    const page = await (await b.newContext({ viewport: { width: w, height: 900 } })).newPage();
    await page.goto('http://sinofresh.local/', { waitUntil: 'load', timeout: 30000 });
    await page.waitForSelector('.sf-story', { timeout: 20000 });
    const r = await page.evaluate(() => {
      const el = document.querySelector('.sf-story');
      const cs = getComputedStyle(el);
      const mq = document.querySelector('.sf-marquee');
      return { w: cs.width, pad: cs.padding, bw: cs.borderWidth, rect: +el.getBoundingClientRect().width.toFixed(1), mqW: +mq.getBoundingClientRect().width.toFixed(1), gap: getComputedStyle(document.querySelector('.sf-stories__group')).gap };
    });
    const pct = (r.rect / w * 100).toFixed(0);
    console.log(String(w).padStart(5) + '  card w=' + r.w + ' pad=' + r.pad + ' border=' + r.bw + ' -> rect=' + r.rect + ' (' + pct + 'vw)  marqueeW=' + r.mqW + '  gap=' + r.gap);
    await page.context().close();
  }
  await b.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
