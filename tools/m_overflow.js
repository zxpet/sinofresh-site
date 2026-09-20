// 移动端横向溢出诊断：找导致 viewport 溢出的"根因元素"
// 用法: node m_overflow.js <urls,逗号分隔> <widths,逗号分隔> [shotDir]
const path = require('path');
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const CHROME = process.env.HOME +
  '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const urls = process.argv[2].split(',');
const widths = process.argv[3].split(',').map(Number);
const shotDir = process.argv[4] || null;

const PROBE = () => {
  const vw = window.innerWidth;
  const de = document.documentElement;
  const items = [];
  const all = document.querySelectorAll('*');
  for (const el of all) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    if (!(r.right > vw + 1 || r.left < -1)) continue;
    // 祖先是否有裁剪容器
    let clippedBy = null;
    let p = el.parentElement;
    while (p && p !== document.documentElement) {
      const cs = getComputedStyle(p);
      if (/(hidden|auto|scroll|clip)/.test(cs.overflowX) || /(hidden|auto|scroll|clip)/.test(cs.overflow)) {
        clippedBy = p.tagName + '.' + (typeof p.className === 'string' ? p.className.trim().split(/\s+/).slice(0, 3).join('.') : '(svg)');
        break;
      }
      p = p.parentElement;
    }
    // 父元素是否也溢出
    const pr = el.parentElement ? el.parentElement.getBoundingClientRect() : null;
    const parentOver = pr ? (pr.right > vw + 1 || pr.left < -1) : false;
    items.push({
      tag: el.tagName,
      cls: typeof el.className === 'string' ? el.className.trim() : '(svg)',
      id: el.id || '',
      w: Math.round(r.width),
      l: Math.round(r.left),
      r: Math.round(r.right),
      over: Math.round(r.right - vw),
      clippedBy,
      parentOver,
      root: !parentOver && !clippedBy,
      text: (el.innerText || '').replace(/\s+/g, ' ').slice(0, 60),
      rects: el.getClientRects().length
    });
  }
  return {
    vw,
    docScrollW: de.scrollWidth,
    docClientW: de.clientWidth,
    bodyScrollW: document.body.scrollWidth,
    hScroll: de.scrollWidth - de.clientWidth,
    items
  };
};

const autoScroll = async (page) => {
  await page.evaluate(async () => {
    const step = Math.round(window.innerHeight * 0.8);
    const max = document.body.scrollHeight;
    for (let y = 0; y < max; y += step) {
      window.scrollTo(0, y);
      await new Promise(r => setTimeout(r, 60));
    }
    window.scrollTo(0, 0);
  });
};

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const report = [];
  for (const w of widths) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    for (const url of urls) {
      let entry = { width: w, url, ok: false };
      try {
        await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
        await page.evaluate(() => document.fonts.ready.then(() => true));
        await autoScroll(page);
        await page.waitForTimeout(400);
        const res = await page.evaluate(PROBE);
        entry = Object.assign(entry, res, { ok: true });
        if (shotDir) {
          fs.mkdirSync(shotDir, { recursive: true });
          const name = (url.replace(/^https?:\/\//, '').replace(/[^a-z0-9]+/gi, '_') || 'home') + '_' + w + '.png';
          await page.screenshot({ path: path.join(shotDir, name) });
          entry.shot = name;
        }
      } catch (e) {
        entry.err = String(e).slice(0, 200);
      }
      report.push(entry);
      const roots = (entry.items || []).filter(i => i.root);
      const clipped = (entry.items || []).filter(i => i.clippedBy);
      console.log(`[${w}px] ${url}  docScrollW=${entry.docScrollW} clientW=${entry.docClientW} 横滚=${entry.hScroll}px`);
      console.log(`  溢出元素 ${(entry.items || []).length} 个 (根因 ${roots.length} / 被裁剪 ${clipped.length})`);
      roots.slice(0, 12).forEach(i => {
        console.log(`   ! <${i.tag} class="${i.cls}"> w=${i.w} left=${i.l} right=${i.r} over=${i.over} rects=${i.rects} :: ${i.text}`);
      });
      console.log('');
    }
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync('/Users/meng/WorkBuddy/sinofresh外贸网站建设/tools/_m_overflow_report.json', JSON.stringify(report, null, 1));
  console.log('报告已写入 tools/_m_overflow_report.json');
})();
