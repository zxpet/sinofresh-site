// 模拟不支持 :has() 的老内核渲染：拦截 style.css，剥除所有含 :has( 的规则再返回
// 用法: node m_nohas_sim.js <url> <width> <shotPrefix>
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME +
  '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const CSS_FILE = process.env.HOME + '/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme/style.css';
const CSS_URL = /\/style\.css[^?]*(\?.*)?$/;
const url = process.argv[2], width = Number(process.argv[3]), prefix = process.argv[4] || 'nohas';

// —— 简易 CSS 规则分割器：剥除 selector 含 :has( 的规则（@media 递归）——
function stripHas(css) {
  let out = '', i = 0, n = css.length;
  while (i < n) {
    // 找下一个 '{'
    const b = css.indexOf('{', i);
    if (b === -1) { out += css.slice(i); break; }
    let prelude = css.slice(i, b);
    // 跳过注释和字符串里的 { —— 简化处理：本文件无此场景
    // 配对取 body
    let depth = 1, j = b + 1;
    while (j < n && depth > 0) {
      if (css[j] === '{') depth++;
      else if (css[j] === '}') depth--;
      j++;
    }
    const body = css.slice(b + 1, j - 1);
    const bare = prelude.trim().replace(/\/\*[\s\S]*?\*\//g, '');
    const clean = bare.trim();
    if (clean.startsWith('@media') || clean.startsWith('@supports')) {
      out += prelude + '{' + stripHas(body) + '}';
    } else if (clean.startsWith('@')) {
      out += prelude + '{' + body + '}'; // @font-face/@keyframes 等原样
    } else {
      if (!bare.includes(':has(')) out += prelude + '{' + body + '}';
    }
    i = j;
  }
  return out;
}

(async () => {
  const orig = fs.readFileSync(CSS_FILE, 'utf8');
  const stripped = stripHas(orig);
  const stat = { origRules: (orig.match(/:has\(/g) || []).length, removedHas: (orig.match(/:has\(/g) || []).length - (stripped.match(/:has\(/g) || []).length };
  console.log(`剥除 :has 规则后剩余 :has 出现次数 = ${(stripped.match(/:has\(/g) || []).length}（原 ${stat.origRules}）`);

  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const ctx = await b.newContext({ viewport: { width, height: 900 } });
  await ctx.route(CSS_URL, route => {
    const req = route.request();
    route.fulfill({ contentType: 'text/css', body: stripped });
  });
  const p = await ctx.newPage();
  await p.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  await p.evaluate(() => document.fonts.ready.then(() => true));
  await p.evaluate(async () => {
    const step = Math.round(window.innerHeight * 0.8);
    for (let y = 0; y < document.body.scrollHeight; y += step) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 50)); }
    window.scrollTo(0, 0);
  });
  await p.waitForTimeout(600);
  // 溢出检测
  const probe = await p.evaluate(() => {
    const vw = window.innerWidth, de = document.documentElement, roots = [];
    for (const el of document.querySelectorAll('*')) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;
      if (!(r.right > vw + 1 || r.left < -1)) continue;
      let parentOver = el.parentElement ? (() => { const pr = el.parentElement.getBoundingClientRect(); return pr.right > vw + 1 || pr.left < -1; })() : false;
      let clipped = false, q = el.parentElement;
      while (q && q !== document.documentElement) {
        const cs = getComputedStyle(q);
        if (/(hidden|auto|scroll|clip)/.test(cs.overflowX)) { clipped = true; break; }
        q = q.parentElement;
      }
      if (!parentOver && !clipped) roots.push(`${el.tagName}.${(el.className||'').toString().trim().split(/\s+/).slice(0,3).join('.')} w=${Math.round(r.width)} right=${Math.round(r.right)} :: ${(el.innerText||'').replace(/\s+/g,' ').slice(0,40)}`);
    }
    return { hScroll: de.scrollWidth - de.clientWidth, docScrollW: de.scrollWidth, roots: roots.slice(0, 20) };
  });
  console.log(`[${width}px no-has] 横滚=${probe.hScroll}px 根因溢出=${probe.roots.length}`);
  probe.roots.forEach(r => console.log('  ! ' + r));
  await p.screenshot({ path: `/Users/meng/WorkBuddy/sinofresh外贸网站建设/tools/_m_shots/${prefix}_${width}_top.png` });
  await p.screenshot({ path: `/Users/meng/WorkBuddy/sinofresh外贸网站建设/tools/_m_shots/${prefix}_${width}_full.png`, fullPage: true });
  console.log('截图已保存 ' + prefix);
  await b.close();
})();
