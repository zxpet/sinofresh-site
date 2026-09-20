/* 任务 2.1 主题零引用图清理 —— 删除前取证探针
 * mode=net  : 加载 19 页，采集全部请求 URL 与状态码，交叉比对主题 assets/images 零引用清单
 * mode=shots: 首页 + 剂型页截图（桌面 1440 / 移动 375）
 */
const fs = require('fs');
const path = require('path');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

// 待清 11 张（主题 assets/images/）
const TARGETS = [
  'Macro_product_photography_of_d_2026-09-14T23-38-58.png',
  'Macro_product_photography_of_e_2026-09-14T23-39-46.png',
  'Macro_product_photography_of_f_2026-09-14T23-39-21.png',
  'Macro_product_photography_of_g_2026-09-14T23-39-45.png',
  'Macro_product_photography_of_r_2026-09-14T23-38-55.png',
  'Product_photography_of_a_matte_2026-09-14T23-39-23.png',
  'Product_photography_of_a_small_2026-09-14T23-39-23.png',
  'Product_photography_of_a_white_2026-09-14T23-39-47.png',
  'Wide_angle_interior_view_of_a__2026-09-14T23-39-03.png',
  'configurator-preview.png',
  'sinofresh-logo-nav.png'
];
// 对照组：必须被请求（证明探针有效）
const CONTROL = ['favicon.png', 'favicon-32.png'];

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
    const all = new Map();   // url -> {status, type}
    const bad = [];
    page.on('request', r => { if (!all.has(r.url())) all.set(r.url(), { status: '?', type: r.resourceType() }); });
    page.on('response', r => { const e = all.get(r.url()); if (e) e.status = r.status(); if (r.status() >= 400) bad.push(r.status() + ' ' + r.url()); });
    page.on('requestfailed', r => { bad.push('FAILED ' + (r.failure() && r.failure().errorText) + ' ' + r.url()); });

    for (const u of URLS) {
      await page.goto('http://sinofresh.local' + u, { waitUntil: 'networkidle' });
      await acceptCookies(page);
      await scrollAll(page);
      await page.waitForTimeout(500);
    }

    const urls = [...all.keys()];
    console.log('=== 采集 ' + URLS.length + ' 页，共 ' + urls.length + ' 个唯一请求 URL ===');

    const hit = TARGETS.filter(n => urls.some(u => u.includes(n)));
    console.log('\n=== 待清 11 张主题图 的请求命中（应为 0） ===');
    console.log(hit.length ? hit.map(h => '  HIT ' + h).join('\n') : '  命中 0 ✅（浏览器从未请求过这 11 个文件）');

    const ctl = CONTROL.filter(n => urls.some(u => u.includes(n)));
    console.log('\n=== 对照组 favicon（应为 2） ===');
    console.log(ctl.length ? ctl.map(c => '  OK  ' + c + '  请求 ' + urls.filter(u => u.includes(c)).length + ' 条 URL').join('\n') : '  ⚠ 对照组零命中，探针可能失效');

    console.log('\n=== 非 2xx / failed 请求（应为 0） ===');
    console.log(bad.length ? [...new Set(bad)].map(x => '  ' + x).join('\n') : '  0 ✅');

    console.log('\n=== 全部 assets/images 请求（应只有 favicon） ===');
    const imgs = urls.filter(u => u.includes('/assets/images/'));
    console.log(imgs.length ? imgs.map(x => '  ' + x).join('\n') : '  （无）');

    fs.writeFileSync('/tmp/t21_req_urls.txt', urls.join('\n'));
    fs.writeFileSync('/tmp/t21_req_images.txt', urls.filter(u => /\.(png|jpe?g|webp|svg|gif|avif)(\?|$)/i.test(u)).join('\n'));
    console.log('\nDONE');
  }

  if (mode === 'shots') {
    fs.mkdirSync(outDir, { recursive: true });
    const targets = [
      { url: '/', tag: 'home', w: 1440, h: 900 },
      { url: '/products/soft-chews/', tag: 'soft-chews', w: 1440, h: 900 },
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
    for (const t of [{ url: '/products/soft-chews/', tag: 'soft-chews' }]) {
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
