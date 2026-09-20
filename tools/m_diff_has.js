// 对比 normal 与 no-has 渲染下每个 section 的布局指纹，定位 :has() 失效造成的可见错乱
// 用法: node m_diff_has.js <urls逗号分隔> <width>
const fs = require('fs');
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
    const clean = prelude.trim().replace(/\/\*[\s\S]*?\*\//g, '').trim();
    if (clean.startsWith('@media') || clean.startsWith('@supports')) out += prelude + '{' + stripHas(body) + '}';
    else if (clean.startsWith('@')) out += prelude + '{' + body + '}';
    else if (!prelude.includes(':has(')) out += prelude + '{' + body + '}';
    i = j;
  }
  return out;
}

const FINGERPRINT = () => {
  const fps = [];
  document.querySelectorAll('section, .sf-section, [class*="sf-"]').forEach(el => {
    if (el.closest('svg')) return;
    const r = el.getBoundingClientRect();
    if (r.height < 8) return;
    fps.push({
      key: el.tagName + '|' + (el.className || '').toString().trim().split(/\s+/).slice(0, 3).join('.'),
      top: Math.round(r.top + scrollY), h: Math.round(r.height),
      txt: (el.innerText || '').replace(/\s+/g, ' ').slice(0, 40)
    });
  });
  return { docH: document.body.scrollHeight, fps };
};

(async () => {
  const urls = process.argv[2].split(',');
  const width = Number(process.argv[3] || 440);
  const stripped = stripHas(fs.readFileSync(CSS_FILE, 'utf8'));
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const ctx0 = await b.newContext({ viewport: { width, height: 900 } });
  const ctx1 = await b.newContext({ viewport: { width, height: 900 } });
  await ctx1.route(/\/style\.css/, r => r.fulfill({ contentType: 'text/css', body: stripped }));

  for (const url of urls) {
    const p0 = await ctx0.newPage(), p1 = await ctx1.newPage();
    await p0.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    await p1.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    for (const p of [p0, p1]) {
      await p.evaluate(() => document.fonts.ready);
      await p.evaluate(async () => {
        const step = Math.round(window.innerHeight * 0.8);
        for (let y = 0; y < document.body.scrollHeight; y += step) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 40)); }
        window.scrollTo(0, 0);
      });
      await p.waitForTimeout(800);
    }
    const f0 = await p0.evaluate(FINGERPRINT);
    const f1 = await p1.evaluate(FINGERPRINT);
    console.log(`\n===== ${url}  docH: normal=${f0.docH} nohas=${f1.docH} (${f1.docH - f0.docH >= 0 ? '+' : ''}${f1.docH - f0.docH}) =====`);
    // 匹配指纹：按 key+txt 找对应，比对 top/h
    const map1 = new Map(f1.fps.map(f => [f.key + '|' + f.txt, f]));
    let diffs = 0;
    for (const f of f0.fps) {
      const g = map1.get(f.key + '|' + f.txt);
      if (!g) continue;
      if (Math.abs(g.top - f.top) > 24 || Math.abs(g.h - f.h) > 24) {
        diffs++;
        console.log(`  Δ ${f.key}  top ${f.top}->${g.top} (${g.top - f.top >= 0 ? '+' : ''}${g.top - f.top})  h ${f.h}->${g.h} (${g.h - f.h >= 0 ? '+' : ''}${g.h - f.h})  :: ${f.txt}`);
      }
      map1.delete(f.key + '|' + f.txt);
    }
    // nohas 多出来的（新出现/文本匹配不上的大块）
    for (const g of map1.values()) {
      if (g.h > 100) console.log(`  + [nohas 新增块] ${g.key} h=${g.h} top=${g.top} :: ${g.txt}`);
    }
    if (!diffs) console.log('  （无显著布局差异）');
    await p0.close(); await p1.close();
  }
  await b.close();
})();
