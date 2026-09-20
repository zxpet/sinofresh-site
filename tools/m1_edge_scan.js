/**
 * m1_edge_scan.js — 全站移动端/桌面端「贴边」扫描
 * 输出 JSON 到 stdout。
 * 判定：内容叶子元素（文字/图片）的 left < 16 或 right > vw-16 → 贴边
 */
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const PAGES = [
  ['home', '/'], ['products', '/products/'], ['soft-chews', '/products/soft-chews/'],
  ['tablets', '/products/tablets/'], ['powders', '/products/powders/'], ['pastes', '/products/pastes/'],
  ['drops', '/products/drops/'], ['liquids', '/products/liquids/'], ['fish-oil', '/products/fish-oil/'],
  ['dental-chews', '/products/dental-chews/'], ['about', '/about/'], ['quality', '/quality/'],
  ['factory-tour', '/factory-tour/'], ['services', '/services/'], ['cooperation', '/cooperation/'],
  ['contact', '/contact/'], ['faq', '/faq/'], ['blog', '/blog/'],
  ['privacy-policy', '/privacy-policy/'], ['cookie-policy', '/cookie-policy/'], ['terms', '/terms/'],
  ['404', '/404-probe/'],
];

const PROBE = () => {
  const vw = window.innerWidth;
  const EDGE = 16;

  const sig = (el) => {
    if (!el) return '';
    const c = (el.getAttribute && el.getAttribute('class')) || '';
    return el.tagName.toLowerCase() + (c ? '.' + c.trim().split(/\s+/).join('.') : '');
  };
  const cs = (el) => getComputedStyle(el);
  const px = (v) => { const n = parseFloat(v); return isNaN(n) ? 0 : Math.round(n); };

  // 找最近的「背景容器」（有非透明背景色的祖先，含自身）
  const findBgAncestor = (el) => {
    let cur = el;
    while (cur && cur !== document.body) {
      const b = cs(cur).backgroundColor;
      if (b && b !== 'rgba(0, 0, 0, 0)' && b !== 'transparent') return cur;
      cur = cur.parentElement;
    }
    return null;
  };
  const findSection = (el) => {
    let cur = el;
    while (cur && cur !== document.body) {
      if (cur.tagName === 'SECTION' || /wp-block-group|wp-block-columns|wp-block-cover/.test(cur.className || '')) return cur;
      cur = cur.parentElement;
    }
    return null;
  };
  const findConstrained = (el) => {
    let cur = el;
    while (cur && cur !== document.body) {
      if ((cur.className || '').toString().includes('is-layout-constrained')) return cur;
      cur = cur.parentElement;
    }
    return null;
  };

  const isLeafContent = (el) => {
    const tag = el.tagName;
    if (tag === 'IMG' || tag === 'PICTURE' || tag === 'SVG' || tag === 'VIDEO' || tag === 'IFRAME') return true;
    // 有直接文本子节点的元素
    for (const n of el.childNodes) {
      if (n.nodeType === 3 && n.textContent.trim().length > 0) return true;
    }
    return false;
  };

  const tagCount = {};
  const offenders = [];
  const seenKey = new Set();

  document.querySelectorAll('body *').forEach((el) => {
    if (el.tagName === 'SCRIPT' || el.tagName === 'STYLE' || el.tagName === 'NOSCRIPT') return;
    if (!isLeafContent(el)) return;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return;
    // 视口外（未滚动到）也判定，用文档坐标更稳：改用 offsetLeft 链
    const left = r.left;
    const right = r.right;
    if (left >= EDGE && right <= vw - EDGE) return;

    const sec = findSection(el);
    const bg = findBgAncestor(el);
    const con = findConstrained(el);
    const key = `${sig(sec)}||${sig(el)}||${Math.round(left)}`;
    if (seenKey.has(key)) return;
    seenKey.add(key);

    const inBgOnly = bg && sec && bg === sec;
    offenders.push({
      tag: el.tagName.toLowerCase(),
      cls: ((el.getAttribute('class') || '')).slice(0, 70),
      text: (el.textContent || '').trim().slice(0, 42),
      left: Math.round(left),
      right: Math.round(right),
      w: Math.round(r.width),
      pageTop: Math.round(r.top + window.scrollY),
      section: sig(sec).slice(0, 110),
      sectionPadL: sec ? px(cs(sec).paddingLeft) : null,
      sectionPadR: sec ? px(cs(sec).paddingRight) : null,
      sectionMaxW: sec ? cs(sec).maxWidth : null,
      bg: sig(bg).slice(0, 110),
      bgPadL: bg ? px(cs(bg).paddingLeft) : null,
      bgPadR: bg ? px(cs(bg).paddingRight) : null,
      bgColor: bg ? cs(bg).backgroundColor : null,
      hasBgClass: bg ? /has-background/.test(bg.className || '') : null,
      constrained: con ? sig(con).slice(0, 90) : null,
      constrainedMaxW: con ? cs(con).maxWidth : null,
      isHeader: !!el.closest('header'),
      inMain: !!el.closest('main'),
    });
    const k = tagCount[sec ? sig(sec) : '?'] || 0;
    tagCount[sec ? sig(sec) : '?'] = k + 1;
  });

  // 顶层区块清单（含 padding 读数）
  const sections = [];
  const root = document.querySelector('main') || document.querySelector('.wp-site-blocks') || document.body;
  const walk = (parent, depth) => {
    Array.from(parent.children).forEach((el) => {
      const cls = (el.getAttribute('class') || '');
      if (el.tagName === 'SECTION' || /wp-block-group|wp-block-columns|wp-block-cover|wp-block-gallery/.test(cls)) {
        const c = cs(el);
        const r = el.getBoundingClientRect();
        sections.push({
          depth,
          tag: el.tagName.toLowerCase(),
          cls: cls.slice(0, 130),
          top: Math.round(r.top + window.scrollY),
          h: Math.round(r.height),
          w: Math.round(r.width),
          left: Math.round(r.left),
          padL: px(c.paddingLeft), padR: px(c.paddingRight),
          maxW: c.maxWidth,
          bg: c.backgroundColor,
          hasBg: el.classList.contains('has-background') || null,
          constrained: el.classList.contains('is-layout-constrained') || false,
        });
        if (depth < 2) walk(el, depth + 1);
      }
    });
  };
  walk(root, 0);

  return {
    url: location.pathname,
    vw,
    docW: document.documentElement.scrollWidth,
    docH: document.documentElement.scrollHeight,
    hOverflow: document.documentElement.scrollWidth > window.innerWidth,
    sections,
    offenders,
  };
};

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  const out = { '375': {}, '1440': {} };
  for (const [vp, w] of [[375, 375], [1440, 1440]]) {
    const ctx = await b.newContext({ viewport: { width: w, height: w === 375 ? 812 : 900 }, deviceScaleFactor: 1 });
    const p = await ctx.newPage();
    for (const [slug, url] of PAGES) {
      try {
        await p.goto('http://sinofresh.local' + url, { waitUntil: 'networkidle', timeout: 45000 });
        await p.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
        // 预滚动逼出懒加载与动画落地
        await p.evaluate(async () => {
          const H = document.documentElement.scrollHeight;
          for (let y = 0; y < H; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 30)); }
          window.scrollTo(0, 0);
          await new Promise(r => setTimeout(r, 250));
        });
        await p.waitForTimeout(300);
        const r = await p.evaluate(PROBE);
        out[String(vp)][slug] = r;
      } catch (e) {
        out[String(vp)][slug] = { url, error: String(e).slice(0, 160) };
      }
    }
    await ctx.close();
  }
  await b.close();
  console.log(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
