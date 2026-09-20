/**
 * m5_shots.js — 对齐核验 + 1440/1024/375 Quality 全页截图
 */
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/';

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  for (const [w, h, tag] of [[1440, 900, '1440'], [1024, 800, '1024'], [375, 812, '375']]) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    const p = await ctx.newPage();
    await p.goto('http://sinofresh.local/quality/', { waitUntil: 'networkidle', timeout: 60000 });
    await p.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
    await p.evaluate(async () => {
      const H = document.documentElement.scrollHeight;
      for (let y = 0; y < H; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 25)); }
      window.scrollTo(0, 0); await new Promise(r => setTimeout(r, 300));
    });
    // 左缘对齐核验：所有顶层区块内第一个 h1/h2 的 left
    const align = await p.evaluate(() => {
      const rows = [];
      document.querySelectorAll('.wp-site-blocks > .wp-block-group').forEach((el) => {
        if (el.classList.contains('sf-hero-inner')) return;
        const head = el.querySelector('h2, h3');
        if (!head) return;
        const r = head.getBoundingClientRect();
        const c = getComputedStyle(el);
        rows.push({
          padL: Math.round(parseFloat(c.paddingLeft)),
          bg: c.backgroundColor === 'rgba(0, 0, 0, 0)' ? 'bare' : 'bg',
          headLeft: Math.round(r.left),
          title: head.textContent.trim().slice(0, 30),
        });
      });
      return rows;
    });
    console.log(`\n### Quality @${w} 左缘对齐`);
    align.forEach((x) => console.log(`   padL=${String(x.padL).padStart(2)} [${x.bg}] headLeft=${String(x.headLeft).padStart(3)}  ${x.title}`));
    const ls = [...new Set(align.map((x) => x.headLeft))];
    const pads = [...new Set(align.map((x) => x.padL))];
    console.log(`   → headLeft 唯一值: [${ls.join(',')}]   padL 唯一值: [${pads.join(',')}]`);

    // 隐藏粘性元素后截全页图
    await p.addStyleTag({ content: '.sf-header,.sf-topbar,.sf-cookie,.sf-fab,.sf-contact-stack,#wpadminbar{display:none!important}' });
    await p.waitForTimeout(250);
    await p.screenshot({ path: OUT + `mb_${tag}_quality_fullpage.png`, fullPage: true });
    // 三个重点区块特写（375/1024）
    if (w !== 1440) {
      for (const [lb, fn] of [['In-House QC Laboratory', 'inhouse'], ['Certificate of Analysis', 'coa'], ['Full Traceability', 'trace']]) {
        const el = p.locator(`section:has(h2:has-text("${lb}"))`).first();
        if (await el.count()) { await el.scrollIntoViewIfNeeded(); await p.waitForTimeout(200); await el.screenshot({ path: `${OUT}mb_${tag}_q_${fn}.png` }); }
      }
    }
    await ctx.close();
  }
  await b.close();
})().catch((e) => { console.error(e); process.exit(1); });
