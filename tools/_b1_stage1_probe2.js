/* 阶段 1 补充探针：速览表几何/对齐 + 锚点跳转落点（阶段 3 的 before 基线） */
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage();
  await p.goto('http://sinofresh.local/products/liquids/', { waitUntil: 'load', timeout: 45000 });
  const r = p.locator('button:has-text("Reject Non-Essential")');
  if (await r.count()) await r.first().click({ force: true }).catch(() => {});
  await p.waitForTimeout(600);

  const geo = await p.evaluate(() => {
    const band = document.querySelector('.sf-spectable');
    const t = document.querySelector('.sf-spectable__table');
    const cap = document.querySelector('.sf-spectable__caption');
    const box = e => { const q = e.getBoundingClientRect(); return { x: Math.round(q.left), w: Math.round(q.width), h: Math.round(q.height) }; };
    return {
      band: box(band), bandPad: getComputedStyle(band).paddingLeft + '/' + getComputedStyle(band).paddingTop,
      table: box(t), cap: box(cap),
      th: Array.from(t.querySelectorAll('thead th')).map(x => { const q = x.getBoundingClientRect(); return { txt: x.textContent, x: Math.round(q.left), w: Math.round(q.width), ta: getComputedStyle(x).textAlign, bg: getComputedStyle(x).backgroundColor, c: getComputedStyle(x).color }; }),
      td: Array.from(t.querySelectorAll('tbody td')).map(x => { const q = x.getBoundingClientRect(); return { txt: x.textContent.trim().slice(0, 22), x: Math.round(q.left), w: Math.round(q.width), ta: getComputedStyle(x).textAlign }; }),
      headerH: document.querySelector('.sf-header').getBoundingClientRect().height | 0,
      headerPos: getComputedStyle(document.querySelector('.sf-header')).position,
    };
  });
  console.log('=== 速览表几何（桌面 1440）===');
  console.log('band', JSON.stringify(geo.band), 'padding', geo.bandPad);
  console.log('table', JSON.stringify(geo.table), 'caption', JSON.stringify(geo.cap));
  console.log('thead th:');
  geo.th.forEach(x => console.log(`   ${x.txt.padEnd(14)} x=${x.x} w=${x.w} text-align=${x.ta} bg=${x.bg} color=${x.c}`));
  console.log('tbody td:');
  geo.td.forEach(x => console.log(`   ${x.txt.padEnd(24)} x=${x.x} w=${x.w} text-align=${x.ta}`));

  console.log();
  console.log('=== 锚点跳转落点（阶段 3 before 基线）header高=' + geo.headerH + ' position=' + geo.headerPos + ' ===');
  for (const [label, sel] of [['Browse Standard Formulas', '.sf-hero-inner a[href="#formulas"]'], ['Build Custom Formula', '.sf-hero-inner a[href="#configurator"]'], ['Request a Quote', '.sf-hero-inner a[href="#inquiry-form"]']]) {
    await p.evaluate(() => scrollTo(0, 0));
    await p.waitForTimeout(300);
    await p.click(sel, { force: true });
    await p.waitForTimeout(2200);
    const res = await p.evaluate(() => {
      const tgt = location.hash ? document.querySelector(location.hash) : null;
      return { hash: location.hash, top: tgt ? Math.round(tgt.getBoundingClientRect().top) : null, scrollY: Math.round(scrollY) };
    });
    const overlap = res.top === null ? 'n/a' : (res.top < geo.headerH ? `⛔ 被 header 遮 ${geo.headerH - res.top}px` : `✅ 露出 ${res.top - geo.headerH}px`);
    console.log(`   ${label.padEnd(26)} hash=${res.hash.padEnd(16)} 目标视口 top=${res.top}  scrollY=${res.scrollY}  ${overlap}`);
  }
  await b.close();
})();
