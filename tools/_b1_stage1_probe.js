/* 阶段 1 细节探针：Hero 按钮换行 / 死链归属 / 表格视觉属性 */
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  for (const vp of [{ w: 1440, h: 900, tag: 'desktop1440' }, { w: 1024, h: 800, tag: 'desktop1024' }, { w: 768, h: 900, tag: 'tablet768' }, { w: 375, h: 812, tag: 'mobile375' }]) {
    const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, isMobile: vp.w < 769, hasTouch: vp.w < 769 });
    const p = await ctx.newPage();
    await p.goto('http://sinofresh.local/products/liquids/', { waitUntil: 'load', timeout: 45000 });
    const r = await p.locator('button:has-text("Reject Non-Essential")');
    if (await r.count()) await r.first().click({ force: true }).catch(() => {});
    await p.waitForTimeout(400);
    const out = await p.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('.sf-hero-inner a.wp-block-button__link')).map(a => {
        const q = a.getBoundingClientRect();
        const cs = getComputedStyle(a);
        return { t: a.textContent.trim(), href: a.getAttribute('href'), x: Math.round(q.left), y: Math.round(q.top + scrollY), w: Math.round(q.width), h: Math.round(q.height), deco: cs.textDecorationLine, decor: cs.textDecorationThickness };
      });
      const rows = {};
      btn.forEach(b => { (rows[b.y] = rows[b.y] || []).push(b.t); });
      const dead = Array.from(document.querySelectorAll('a[href="#"]')).map(a => {
        const p = [];
        let el = a, n = 0;
        while (el && n < 6) { p.unshift(el.tagName + (el.className ? '.' + String(el.className).split(' ').slice(0, 2).join('.') : '')); el = el.parentElement; n++; }
        return { text: a.textContent.trim().slice(0, 40), path: p.join(' > '), cls: a.className, aria: a.getAttribute('aria-label') || '' };
      });
      const wrap = document.querySelector('.sf-hero-inner .wp-block-buttons');
      return { btn, rows, dead, wrapBox: wrap ? { w: Math.round(wrap.getBoundingClientRect().width), h: Math.round(wrap.getBoundingClientRect().height), gap: getComputedStyle(wrap).gap, wrap: getComputedStyle(wrap).flexWrap, jc: getComputedStyle(wrap).justifyContent } : null };
    });
    console.log('================ ' + vp.tag + ' ================');
    console.log('buttons wrapper:', JSON.stringify(out.wrapBox));
    out.btn.forEach(b => console.log(`  · ${b.t.padEnd(26)} ${b.w}x${b.h} @x=${b.x} y=${b.y}  deco=${b.deco}/${b.decor}`));
    console.log('  行分组:', JSON.stringify(out.rows));
    if (vp.tag === 'desktop1440') { console.log('  死链 ' + out.dead.length + ' 个:'); out.dead.forEach(d => console.log(`    - "${d.text}" aria="${d.aria}" | ${d.path} | cls=${d.cls}`)); }
    await ctx.close();
  }
  await browser.close();
})();
