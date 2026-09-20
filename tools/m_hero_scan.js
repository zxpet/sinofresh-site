// 全站 Hero 区移动端裁切扫描：测面包屑/H1/副标题左边缘、容器 padding、视口溢出
// 用法: node m_hero_scan.js <widths,逗号分隔> [shotDir]
const path = require('path');
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');

const CHROME = process.env.HOME +
  '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const BASE = 'http://sinofresh.local';
const PAGES = [
  ['/', 'home'],
  ['/products/', 'products'],
  ['/about/', 'about'],
  ['/quality/', 'quality'],
  ['/factory-tour/', 'factory-tour'],
  ['/services/', 'services'],
  ['/cooperation/', 'cooperation'],
  ['/contact/', 'contact'],
  ['/blog/', 'blog'],
  ['/faq/', 'faq'],
  ['/products/soft-chews/', 'soft-chews'],
  ['/products/tablets/', 'tablets'],
  ['/products/powders/', 'powders'],
  ['/products/pastes/', 'pastes'],
  ['/products/liquids/', 'liquids'],
  ['/products/drops/', 'drops'],
  ['/products/dental-chews/', 'dental-chews'],
  ['/products/fish-oil/', 'fish-oil'],
];

const widths = process.argv[2].split(',').map(Number);
const shotDir = process.argv[3] || null;

const PROBE = () => {
  const vw = window.innerWidth;
  // 找 hero：内页 .sf-hero-inner，或首页 .sf-hero-slider 外层 section
  const hero = document.querySelector('.sf-hero-inner') ||
    document.querySelector('.wp-site-blocks > .wp-block-group.sf-hero-slider') ||
    document.querySelector('.sf-hero-slider');
  if (!hero) return { heroFound: false };
  const hcs = getComputedStyle(hero);
  const hr = hero.getBoundingClientRect();

  const pick = (sel) => {
    const el = hero.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return { sel, left: +r.left.toFixed(1), right: +r.right.toFixed(1), width: +r.width.toFixed(1), marginLeft: cs.marginLeft, pl: cs.paddingLeft };
  };
  const breadcrumb = pick('.sf-breadcrumb');
  const h1 = pick('h1');
  const sub = pick('.sf-hero-inner p, .sf-hero-slider p');

  // hero 内所有直接子孙文本元素中最靠左的
  let minLeft = Infinity, minEl = null;
  hero.querySelectorAll('*').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    const hasText = el.childNodes.length && [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!hasText) return;
    if (r.left < minLeft) { minLeft = r.left; minEl = el; }
  });

  // hero 自身是否溢出视口
  const heroOver = hr.left < -1 || hr.right > vw + 1;

  // 文档级横滚
  const de = document.documentElement;

  return {
    heroFound: true,
    heroClass: hero.className.replace(/\s+/g, ' ').slice(0, 80),
    heroRect: { left: +hr.left.toFixed(1), right: +hr.right.toFixed(1), width: +hr.width.toFixed(1) },
    heroPadding: { left: hcs.paddingLeft, right: hcs.paddingRight },
    heroOverflow: heroOver,
    breadcrumb, h1, sub,
    leftmostText: minEl ? { tag: minEl.tagName, cls: (typeof minEl.className === 'string' ? minEl.className : '').slice(0, 60), left: +minLeft.toFixed(1) } : null,
    docHScroll: de.scrollWidth - de.clientWidth,
  };
};

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const report = [];
  for (const w of widths) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    for (const [p, name] of PAGES) {
      const url = BASE + p;
      const entry = { width: w, page: name, url };
      try {
        await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
        await page.evaluate(() => document.fonts.ready);
        await page.waitForTimeout(300);
        const res = await page.evaluate(PROBE);
        Object.assign(entry, res);
        if (shotDir) {
          fs.mkdirSync(shotDir, { recursive: true });
          const f = path.join(shotDir, `${name}_${w}_hero.png`);
          const hero = await page.$('.sf-hero-inner, .sf-hero-slider');
          if (hero) await hero.screenshot({ path: f });
          entry.shot = f;
        }
      } catch (e) {
        entry.err = String(e).slice(0, 200);
      }
      report.push(entry);
      if (entry.err) console.log(`[${w}] ${name}  ERROR ${entry.err}`);
      else if (!entry.heroFound) console.log(`[${w}] ${name}  未找到 hero`);
      else {
        const bl = entry.breadcrumb ? entry.breadcrumb.left : '-';
        const hl = entry.h1 ? entry.h1.left : '-';
        const sl = entry.sub ? entry.sub.left : '-';
        console.log(`[${w}] ${name.padEnd(14)} 面包屑=${bl}  H1=${hl}  副标题=${sl}  heroL=${entry.heroRect.left} pl=${entry.heroPadding.left} pr=${entry.heroPadding.right} 横滚=${entry.docHScroll}px`);
      }
    }
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync('/Users/meng/WorkBuddy/sinofresh外贸网站建设/tools/_m_hero_scan.json', JSON.stringify(report, null, 1));
  console.log('\n报告已写入 tools/_m_hero_scan.json');
})();
