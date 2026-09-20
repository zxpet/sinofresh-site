/**
 * o8_overflow.js — 卡片内部横向溢出真伪校验
 * card scrollWidth > clientWidth 若仅等于 4px，即 .sf-card::after 的 hover 命中区外扩，
 * 不是真实内容溢出；同时逐个后代元素与内容盒右边界比对。
 */
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const T = [
  ['home', '/', 'OEM & ODM Services'],
  ['services', '/services/', 'OEM or ODM \u2014 Choose Your Path'],
];

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  for (const w of [1440, 375]) {
    const p = await (await b.newContext({ viewport: { width: w, height: 900 } })).newPage();
    for (const t of T) {
      await p.goto('http://sinofresh.local' + t[1], { waitUntil: 'networkidle' });
      const rows = await p.evaluate((h2t) => {
        const sec = [...document.querySelectorAll('.wp-site-blocks > .wp-block-group')]
          .find((s) => s.querySelector('h2') && s.querySelector('h2').textContent.trim() === h2t);
        const res = [];
        sec.querySelectorAll('.wp-block-column > .wp-block-group').forEach((g) => {
          const gr = g.getBoundingClientRect();
          const cs = getComputedStyle(g);
          const contentRight = gr.right - parseFloat(cs.paddingRight) - parseFloat(cs.borderRightWidth);
          const bad = [];
          g.querySelectorAll('*').forEach((el) => {
            const r2 = el.getBoundingClientRect();
            if (r2.width > 0 && r2.right > contentRight + 0.5) bad.push(el.tagName.toLowerCase() + '.' + String(el.className || '').slice(0, 24) + ' R' + Math.round(r2.right));
          });
          res.push({
            title: (g.querySelector('h3') || {}).textContent,
            contentRight: Math.round(contentRight),
            delta: g.scrollWidth - g.clientWidth,
            bad: bad.slice(0, 3),
          });
        });
        return res;
      }, t[2]);
      console.log('--- ' + w + ' ' + t[0] + ' ---');
      rows.forEach((x) => console.log('  [' + x.title + '] 内容右=' + x.contentRight + ' scrollDelta=' + x.delta + ' 越界子元素=' + (x.bad.length ? JSON.stringify(x.bad) : '无')));
    }
    await p.close();
  }
  await b.close();
})().catch((e) => { console.error(e); process.exit(1); });
