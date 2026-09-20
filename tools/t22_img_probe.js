/* 任务 2.2 uploads 零引用图清理 —— 运行时请求采集探针
 * mode=net  : 加载 19 页，采集全部请求 URL + 状态码 → /tmp/t22/runtime_urls.txt
 * mode=shots: 首页 + 剂型页 + quality 页截图（桌面 1440 / 移动 375）
 */
const fs = require('fs');
const path = require('path');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

// 任务 2.2 待清 21 个（uploads/2026/09）—— 微信图片族 8 + 剂型 PNG 原图 9 + 被取代 webp 4
const TARGETS = [
  '微信图片_20260629142652_11_458.jpg',
  '微信图片_20260629142652_11_458-scaled.jpg',
  '微信图片_20260629142652_11_458-2048x1535.jpg',
  '微信图片_20260629142652_11_458-1536x1152.jpg',
  '微信图片_20260629142652_11_458-1024x768.jpg',
  '微信图片_20260629142652_11_458-768x576.jpg',
  '微信图片_20260629142652_11_458-300x225.jpg',
  '微信图片_20260629142652_11_458-150x150.jpg',
  'hero-facility.png', 'powders.png', 'soft-chews.png', 'dental-chews.png',
  'fish-oil.png', 'pastes.png', 'drops.png', 'liquids.png', 'tablets.png',
  'hero-line.webp', 'hero-facility.webp', 'hero-lab.webp', 'world-map.webp',
];
// 对照组：确认在用图（必须被请求，证明探针有效）
const CONTROL = ['hero1-exterior.webp', 'drops.webp', 'soft-chews.webp', 'favicon'];
// 信息组：报告 🟡 待确认项（不属于本次删除范围）
const INFO = ['sino-fresh-logo-1-150x150.png', 'blog-softchews-150x150.webp', 'sino-fresh-logo-1-scaled.png'];

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
    fs.writeFileSync('/tmp/t22/runtime_urls.txt', urls.join('\n'));
    console.log('=== 采集 ' + URLS.length + ' 页，共 ' + urls.length + ' 个唯一请求 URL ===');

    const rel = urls.filter(u => u.includes('/wp-content/uploads/')).map(u => decodeURIComponent(u.split('/wp-content/uploads/')[1].split('?')[0]));
    fs.writeFileSync('/tmp/t22/runtime_upload_paths.txt', rel.join('\n'));
    console.log('=== 其中 uploads/ 下被请求的路径：' + new Set(rel).size + ' 个 ===');
    [...new Set(rel)].sort().forEach(p => console.log('   ' + p));

    const hit = TARGETS.filter(n => urls.some(u => decodeURIComponent(u).includes(n)));
    console.log('\n=== 待清 21 个 的请求命中（应为 0） ===');
    console.log(hit.length ? hit.map(h => '  HIT ' + h).join('\n') : '  命中 0 ✅');

    const ct = CONTROL.filter(n => urls.some(u => u.includes(n)));
    console.log('\n=== 对照组（应为 ' + CONTROL.length + '） ===');
    console.log(ct.length ? ct.map(c => '  OK  ' + c + ' ×' + urls.filter(u => u.includes(c)).length).join('\n') : '  ⚠ 对照组零命中，探针可能失效');

    const inf = INFO.filter(n => urls.some(u => u.includes(n)));
    console.log('\n=== 信息组（🟡 待确认，不属于本次范围） ===');
    console.log(inf.length ? inf.map(h => '  HIT ' + h).join('\n') : '  命中 0');

    console.log('\n=== 非 2xx / failed 请求（应为 0） ===');
    console.log(bad.length ? [...new Set(bad)].map(x => '  ' + x).join('\n') : '  0 ✅');
    fs.writeFileSync('/tmp/t22/runtime_bad.txt', [...new Set(bad)].join('\n'));
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
