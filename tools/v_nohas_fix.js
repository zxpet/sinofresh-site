// 验证 no-has 降级修复：
//   模式 legacy：剥除 CSS 中 :has 规则 + 强制 html.no-has（= 真实老内核 + 降级块）
//   模式 modern：页面原样（新内核，探测不加 class，降级块不生效）
// 用法: node v_nohas_fix.js <urls逗号分隔> <width> <shotDir可选>
const fs = require('fs');
const path = require('path');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME +
  '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const CSS_FILE = process.env.HOME + '/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme/style.css';

function stripHas(css) {
  let out = '', i = 0, n = css.length;
  while (i < n) {
    const b = css.indexOf('{', i);
    if (b === -1) { out += css.slice(i); break; }
    const prelude = css.slice(i, b);
    let d = 1, j = b + 1;
    while (j < n && d > 0) { if (css[j] === '{') d++; else if (css[j] === '}') d--; j++; }
    const body = css.slice(b + 1, j - 1);
    const bare = prelude.replace(/\/\*[\s\S]*?\*\//g, '');
    const clean = bare.trim();
    if (clean.startsWith('@media') || clean.startsWith('@supports')) out += prelude + '{' + stripHas(body) + '}';
    else if (clean.startsWith('@')) out += prelude + '{' + body + '}';
    else if (!bare.includes(':has(')) out += prelude + '{' + body + '}';
    i = j;
  }
  return out;
}

const METRIC = () => ({
  docH: document.body.scrollHeight,
  hScroll: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  sections: [...document.querySelectorAll('section, .sf-panel, .sf-certrow')].map(el => {
    const r = el.getBoundingClientRect();
    return { c: (el.className || '').toString().trim().split(/\s+/).slice(0, 3).join('.'), top: Math.round(r.top + scrollY), h: Math.round(r.height) };
  })
});

(async () => {
  const urls = process.argv[2].split(',');
  const width = Number(process.argv[3] || 440);
  const shotDir = process.argv[4] || null;
  const stripped = stripHas(fs.readFileSync(CSS_FILE, 'utf8'));
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });

  for (const url of urls) {
    const out = {};
    for (const mode of ['legacy', 'modern']) {
      const ctx = await b.newContext({ viewport: { width, height: 900 } });
      if (mode === 'legacy') {
        await ctx.route(/\/style\.css/, r => r.fulfill({ contentType: 'text/css', body: stripped }));
        await ctx.addInitScript(() => {
          const add = () => { document.documentElement.className += ' no-has'; };
          if (document.documentElement) add();
          else window.addEventListener('DOMContentLoaded', add);
        });
      }
      const p = await ctx.newPage();
      await p.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
      await p.evaluate(() => document.fonts.ready);
      await p.evaluate(async () => {
        const step = Math.round(window.innerHeight * 0.8);
        for (let y = 0; y < document.body.scrollHeight; y += step) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 40)); }
        window.scrollTo(0, 0);
      });
      await p.waitForTimeout(700);
      out[mode] = await p.evaluate(METRIC);
      if (shotDir && mode === 'legacy') {
        fs.mkdirSync(shotDir, { recursive: true });
        const name = (url.replace(/^https?:\/\//, '').replace(/[^a-z0-9]+/gi, '_') || 'home') + '_' + width + '_legacy.png';
        await p.screenshot({ path: path.join(shotDir, name), fullPage: true });
      }
      await ctx.close();
    }
    const L = out.legacy, M = out.modern;
    // legacy vs modern 的 section 指纹差异（忽略整体平移：top 差为常数视为连锁）
    let topShifts = [], hDiffs = [];
    const mmap = new Map(M.sections.map(s => [s.c + s.h, s]));
    for (const s of L.sections) {
      const g = mmap.get(s.c + s.h);
      if (g) topShifts.push(s.top - g.top);
    }
    const shiftConsistent = topShifts.length > 0 ? (Math.max(...topShifts) - Math.min(...topShifts)) : 0;
    console.log(`${url}`);
    console.log(`  legacy(docH=${L.docH}, hScroll=${L.hScroll})  modern(docH=${M.docH}, hScroll=${M.hScroll})  docH差=${L.docH - M.docH}`);
    console.log(`  section top 偏移范围: ${topShifts.length ? Math.min(...topShifts) + '~' + Math.max(...topShifts) : 'n/a'} ${shiftConsistent <= 4 ? '（整体平移=布局结构一致 ✓）' : '（散乱=结构仍有差异 ✕）'}`);
  }
  await b.close();
})();
