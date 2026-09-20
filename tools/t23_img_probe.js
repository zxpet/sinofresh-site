/* 任务 2.3 burst 残留清理 —— 运行时请求采集探针
 * mode=net  : 加载 19 页，采集全部请求 URL + 状态码 → /tmp/t23/runtime_urls.txt
 * mode=shots: 首页 + 剂型页 + quality 页截图（桌面 1440 / 移动 375）
 */
const fs = require('fs');
const path = require('path');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

// 任务 2.3 待清：uploads/burst/ 整目录（8 文件）+ uploads/js/ 空壳
const TARGETS = [
  '/wp-content/uploads/burst/',
  '/wp-content/uploads/burst/js/burst.min.js',
  '/wp-content/uploads/burst/maxmind/GeoLite2-Country.mmdb',
  '/wp-content/uploads/burst/exports/',
  '/wp-content/uploads/js/',
];
// 对照组：确认在用资源（必须被请求，证明探针有效）
const CONTROL = ['/wp-content/uploads/2026/09/soft-chews.webp', '/wp-content/uploads/2026/09/hero1-exterior.webp', 'favicon'];
// 信息组：burst 相关但不在文件清理范围的 DB 残留（仅观测）
const INFO = ['burst', 'GeoLite2', 'maxmind'];

const URLS = ['/', '/about/', '/products/', '/products/soft-chews/', '/products/tablets/',
  '/products/powders/', '/products/pastes/', '/products/drops/', '/products/liquids/',
  '/products/fish-oil/', '/products/dental-chews/', '/quality/', '/faq/', '/services/',
  '/cooperation/', '/contact/', '/blog/', '/factory-tour/', '/feedback/'];

const mode = process.argv[2];
const outDir = process.argv[3];

async function acceptCookies(page) {
  const reject = page.locator('button:has-text("Reject Non-Essential")');
  if (await reject.count()) await reject.first().click({ force: true }).catch(() => {});
}
async function scrollAll(page) {
  await page.evaluate(async () => {
    const s = Math.round(innerHeight * 0.8);
    for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise(r => setTimeout(r, 80)); }
    scrollTo(0, 0);
  });
  await page.waitForTimeout(1000);
  await page.evaluate(() => document.fonts.ready);
}

(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });

  if (mode === 'net') {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    const all = new Map();
    const bad = [];
    page.on('request', r => { if (!all.has(r.url())) all.set(r.url(), { status: '?', type: r.resourceType() }); });
    page.on('response', r => { const e = all.get(r.url()); if (e) e.status = r.status(); if (r.status() >= 400) bad.push(r.status() + ' ' + r.url()); });
    page.on('requestfailed', r => { bad.push('FAILED ' + (r.failure() && r.failure().errorText) + ' ' + r.url()); });

    for (const u of URLS) {
      await page.goto('http://sinofresh.local' + u, { waitUntil: 'networkidle' });
      await acceptCookies(page);
      await scrollAll(page);
      await page.waitForTimeout(400);
    }

    const urls = [...all.keys()];
    fs.mkdirSync('/tmp/t23', { recursive: true });
    fs.writeFileSync('/tmp/t23/runtime_urls.txt', urls.join('\n'));
    console.log('=== 采集 ' + URLS.length + ' 页，共 ' + urls.length + ' 个唯一请求 URL ===');

    const rel = urls.filter(u => u.includes('/wp-content/uploads/')).map(u => decodeURIComponent(u.split('/wp-content/uploads/')[1].split('?')[0]));
    fs.writeFileSync('/tmp/t23/runtime_upload_paths.txt', rel.join('\n'));
    console.log('=== 其中 uploads/ 下被请求的路径：' + new Set(rel).size + ' 个 ===');
    [...new Set(rel)].sort().forEach(p => console.log('   ' + p));

    const hit = TARGETS.filter(n => urls.some(u => decodeURIComponent(u).includes(n)));
    console.log('\n=== 待清 burst/ + js/ 的请求命中（应为 0） ===');
    console.log(hit.length ? hit.map(h => '  HIT ' + h).join('\n') : '  命中 0 ✅');

    const ct = CONTROL.filter(n => urls.some(u => u.includes(n)));
    console.log('\n=== 对照组（应为 ' + CONTROL.length + '） ===');
    console.log(ct.length ? ct.map(c => '  OK  ' + c + ' ×' + urls.filter(u => u.includes(c)).length).join('\n') : '  ⚠ 对照组零命中，探针可能失效');

    const inf = INFO.filter(n => urls.some(u => u.includes(n)));
    console.log('\n=== 信息组（burst 关键词，仅观测） ===');
    console.log(inf.length ? inf.map(h => '  HIT ' + h + ' ×' + urls.filter(u => u.includes(h)).length).join('\n') : '  命中 0');

    console.log('\n=== 非 2xx / failed 请求（应为 0） ===');
    console.log(bad.length ? [...new Set(bad)].map(x => '  ' + x).join('\n') : '  0 ✅');
    fs.writeFileSync('/tmp/t23/runtime_bad.txt', [...new Set(bad)].join('\n'));
    console.log('\nDONE');
  }

  if (mode === 'shots') {
    fs.mkdirSync(outDir, { recursive: true });
    const targets = [
      { url: '/', tag: 'home', w: 1440, h: 900 },
      { url: '/products/soft-chews/', tag: 'soft-chews', w: 1440, h: 900 },
      { url: '/quality/', tag: 'quality', w: 1440, h: 900 },
    ];
    for (const t of targets) {
      const ctx = await b.newContext({ viewport: { width: t.w, height: t.h } });
      const page = await ctx.newPage();
      await page.addInitScript(() => { try { localStorage.setItem('sf_cookie_consent', JSON.stringify({ necessary: true, analytics: false, marketing: false })); } catch (e) {} });
      await page.goto('http://sinofresh.local' + t.url, { waitUntil: 'networkidle' });
      await acceptCookies(page);
      await scrollAll(page);
      await page.addStyleTag({ content: 'header{position:static!important}' });
      await page.evaluate(() => scrollTo(0, 0));
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(outDir, t.tag + '-top.png') });
      await page.screenshot({ path: path.join(outDir, t.tag + '-full.png'), fullPage: true });
      console.log('shot:', t.tag);
      await ctx.close();
    }
    for (const t of [{ url: '/products/soft-chews/', tag: 'soft-chews' }, { url: '/', tag: 'home' }]) {
      const ctx = await b.newContext({ viewport: { width: 375, height: 812 } });
      const page = await ctx.newPage();
      await page.addInitScript(() => { try { localStorage.setItem('sf_cookie_consent', JSON.stringify({ necessary: true, analytics: false, marketing: false })); } catch (e) {} });
      await page.goto('http://sinofresh.local' + t.url, { waitUntil: 'networkidle' });
      await scrollAll(page);
      await page.screenshot({ path: path.join(outDir, t.tag + '-top-375.png') });
      console.log('shot:', t.tag, '375');
      await ctx.close();
    }
    console.log('DONE');
  }

  await b.close();
})();
