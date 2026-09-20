// q1: 全站 FAQ 区块宽度扫描 + 版心对比
const { chromium } = require('playwright-core');

const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const BASE = 'http://sinofresh.local';

const PAGES = [
  '/', '/quality/', '/faq/', '/services/', '/cooperation/',
  '/factory-tour/', '/contact/', '/soft-chews/', '/drops/', '/powders/',
  '/pastes/', '/tablets/', '/liquids/', '/fish-oil/', '/dental-chews/'
];

(async () => {
  const browser = await chromium.launch({ executablePath: EXEC, headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  const rows = [];
  for (const p of PAGES) {
    await page.goto(BASE + p, { waitUntil: 'networkidle', timeout: 45000 });
    await page.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
    const r = await page.evaluate(() => {
      const out = { url: location.pathname, faqCount: 0, faq: null, refs: [] };
      const faqs = Array.from(document.querySelectorAll('.sf-faq'));
      out.faqCount = faqs.length;
      if (!faqs.length) return out;
      const f = faqs[0];
      const fr = f.getBoundingClientRect();
      const cs = getComputedStyle(f);
      // 找最近的 section 祖先
      let sec = f.closest('section') || f.parentElement;
      const sr = sec.getBoundingClientRect();
      const scs = getComputedStyle(sec);
      // section 内容盒宽
      const secInner = sr.width - parseFloat(scs.paddingLeft) - parseFloat(scs.paddingRight);
      // 参考：section 内的 h2（居中标题）
      const h2 = sec.querySelector(':scope > h2');
      const refs = [];
      if (h2) {
        const hr = h2.getBoundingClientRect();
        refs.push({ what: 'h2 (section direct)', w: +hr.width.toFixed(1), left: +hr.left.toFixed(1), right: +hr.right.toFixed(1) });
      }
      const p1 = sec.querySelector(':scope > p');
      if (p1) {
        const pr = p1.getBoundingClientRect();
        refs.push({ what: 'p (section direct)', w: +pr.width.toFixed(1), left: +pr.left.toFixed(1), right: +pr.right.toFixed(1) });
      }
      // 另一参考：全站正文块（wide 或 constrained 的 group 内容）
      const hero = document.querySelector('.sf-hero-inner');
      if (hero) {
        const hr2 = hero.getBoundingClientRect();
        refs.push({ what: 'hero section', w: +hr2.width.toFixed(1) });
      }
      out.faq = {
        cls: f.className,
        contentSizeVar: getComputedStyle(f).getPropertyValue('--wp--style--global--content-size').trim(),
        w: +fr.width.toFixed(1),
        left: +fr.left.toFixed(1),
        right: +fr.right.toFixed(1),
        maxWidth: cs.maxWidth,
        marginLeft: cs.marginLeft,
        marginRight: cs.marginRight,
        secInner: +secInner.toFixed(1),
        secLeft: +sr.left.toFixed(1),
        details: f.querySelectorAll('details').length,
        firstDetailW: f.querySelector('details') ? +f.querySelector('details').getBoundingClientRect().width.toFixed(1) : null
      };
      out.refs = refs;
      // 全页最长正文段落宽度（代表正文版心）
      let maxP = 0;
      document.querySelectorAll('main p, section p').forEach(el => {
        const w = el.getBoundingClientRect().width;
        if (w > maxP && el.textContent.trim().length > 40) maxP = w;
      });
      out.maxTextW = +maxP.toFixed(1);
      return out;
    });
    rows.push(r);
  }

  console.log(JSON.stringify(rows, null, 1));
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
