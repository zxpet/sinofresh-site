/**
 * m1b_probe.js — 多档视口探测「裸区块」贴边 + 截图取证
 */
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/';

const TARGETS = [
  ['quality', '/quality/', ['In-House QC Laboratory', 'Certificate of Analysis', 'Full Traceability']],
  ['soft-chews', '/products/soft-chews/', null],
  ['factory-tour', '/factory-tour/', null],
];

const PROBE = () => {
  const vw = window.innerWidth;
  const px = (v) => Math.round(parseFloat(v) || 0);
  // 找出所有顶层 section + 其左右内边距
  const rows = [];
  document.querySelectorAll('main > *, main section, .wp-site-blocks > .wp-block-group').forEach((el) => {
    if (!/wp-block-group|wp-block-columns/.test(el.className || '')) return;
    if (el.closest('header') || el.closest('footer')) return;
    const c = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (r.height < 40) return;
    const bg = c.backgroundColor;
    const hasBgAttr = el.classList.contains('has-background');
    // 该区块内最靠左/最靠右的「文本或图片叶子」
    let minL = Infinity, maxR = -Infinity, sampleL = '', sampleR = '';
    el.querySelectorAll('h1,h2,h3,h4,p,li,img,figcaption,a.wp-block-button__link').forEach((k) => {
      const kr = k.getBoundingClientRect();
      if (kr.width <= 0 || kr.height <= 0) return;
      const inMarquee = k.closest('.sf-stories, .sf-hero-slider, [class*="marquee"], .wp-block-cover');
      if (inMarquee) return;
      if (kr.left < minL) { minL = kr.left; sampleL = k.tagName.toLowerCase() + ':' + (k.textContent || '').trim().slice(0, 26); }
      if (kr.right > maxR) { maxR = kr.right; sampleR = k.tagName.toLowerCase() + ':' + (k.textContent || '').trim().slice(0, 26); }
    });
    rows.push({
      tag: el.tagName.toLowerCase(),
      cls: (el.getAttribute('class') || '').slice(0, 78),
      top: Math.round(r.top + window.scrollY),
      h: Math.round(r.height),
      padL: px(c.paddingLeft), padR: px(c.paddingRight),
      bg: bg === 'rgba(0, 0, 0, 0)' ? 'none' : bg,
      hasBgAttr,
      minL: minL === Infinity ? null : Math.round(minL),
      maxR: maxR === -Infinity ? null : Math.round(maxR),
      sampleL, sampleR,
    });
  });
  return { vw, docW: document.documentElement.scrollWidth, rows };
};

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  for (const [w, h] of [[375, 812], [768, 1024], [1024, 800], [1440, 900]]) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    const p = await ctx.newPage();
    for (const [slug, url, labels] of TARGETS) {
      await p.goto('http://sinofresh.local' + url, { waitUntil: 'networkidle', timeout: 45000 });
      await p.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
      await p.evaluate(async () => {
        const H = document.documentElement.scrollHeight;
        for (let y = 0; y < H; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 25)); }
        window.scrollTo(0, 0); await new Promise(r => setTimeout(r, 200));
      });
      const r = await p.evaluate(PROBE);
      console.log(`\n##### ${slug} @${w}  docW=${r.docW} vw=${r.vw} overflow=${r.docW > r.vw}`);
      for (const row of r.rows) {
        const flag = row.minL !== null && row.minL < 16 ? ' <<< 贴边' : (row.minL !== null && row.minL < 24 ? ' <紧' : '');
        console.log(`  pad${row.padL}/${row.padR} top${String(row.top).padStart(5)} h${String(row.h).padStart(5)} bg=${row.bg.padEnd(18)} hasBgAttr=${String(row.hasBgAttr).padEnd(5)} 内容L=${row.minL} R=${row.maxR}${flag}`);
        console.log(`      ${row.cls}`);
        if (flag && row.sampleL) console.log(`      ← 最左: ${row.sampleL} | 最右: ${row.sampleR}`);
      }
      if (w === 375 && labels) {
        for (const lb of labels) {
          const el = p.locator(`section:has(h2:text-is("${lb}"))`).first();
          if (await el.count()) {
            await el.scrollIntoViewIfNeeded();
            await p.waitForTimeout(150);
            await el.screenshot({ path: OUT + `m1_375_${slug}_${lb.split(' ')[0].toLowerCase()}.png` });
          }
        }
      }
    }
    await ctx.close();
  }
  await b.close();
})().catch((e) => { console.error(e); process.exit(1); });
