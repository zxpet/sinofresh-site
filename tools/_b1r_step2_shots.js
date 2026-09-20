/* Batch 1 / 步骤 2 截图交付 —— Hero 极简（8 页剂型页）
   代表页 liquids + soft-chews 两页 × 桌面 1440 / 移动 375
   每档输出两张：干净首屏 + 测量标注首屏（Hero 高度 / 无轮播 / 2 按钮）
   Usage: node tools/_b1r_step2_shots.js [outdir]   -> 默认 /tmp/b1/step2/shots */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const PAGES = ['liquids', 'soft-chews'];
const OUT = process.argv[2] || '/tmp/b1/step2/shots';
fs.mkdirSync(OUT, { recursive: true });

async function accept(p) {
  const r = p.locator('button:has-text("Reject Non-Essential")');
  if (await r.count()) await r.first().click({ force: true }).catch(() => {});
}

/* 预滚动逼出懒加载——不这么做，首屏以下的图层会塌陷，测量失真 */
async function settle(page) {
  await page.evaluate(async () => {
    const s = Math.round(innerHeight * 0.8);
    for (let y = 0; y < document.body.scrollHeight; y += s) {
      scrollTo(0, y); await new Promise((r) => setTimeout(r, 60));
    }
    scrollTo(0, 0); await new Promise((r) => setTimeout(r, 300));
  });
  await page.evaluate(() => Promise.all(Array.from(document.images)
    .filter((i) => !i.complete)
    .map((i) => new Promise((r) => { i.onload = i.onerror = r; }))));
}

const probe = () => {
  const hero = document.querySelector('section.sf-hero-inner');
  const h1 = hero && hero.querySelector('h1');
  const sub = hero && hero.querySelector('p');
  const btns = hero ? Array.from(hero.querySelectorAll('.wp-block-button__link')) : [];
  const r = hero ? hero.getBoundingClientRect() : null;
  return {
    heroH: r ? Math.round(r.height) : null,
    heroW: r ? Math.round(r.width) : null,
    pt: hero ? getComputedStyle(hero).paddingTop : null,
    pb: hero ? getComputedStyle(hero).paddingBottom : null,
    h1: h1 ? h1.textContent.trim() : null,
    h1H: h1 ? Math.round(h1.getBoundingClientRect().height) : null,
    h1Align: h1 ? getComputedStyle(h1).textAlign : null,
    sub: sub ? sub.textContent.trim() : null,
    subH: sub ? Math.round(sub.getBoundingClientRect().height) : null,
    buttons: btns.map((b) => ({
      text: b.textContent.trim(), href: b.getAttribute('href'),
      bg: getComputedStyle(b).backgroundColor, style: b.className,
    })),
    sliderNodes: document.querySelectorAll('.sf-pslider, .sf-product-hero-image, .sf-slider-progress').length,
    heroCols: document.querySelectorAll('section.sf-hero-inner .wp-block-columns').length,
    sliderScript: document.querySelectorAll('script[id*="product-slider"]').length,
    reqQuote: document.body.innerHTML.includes('Request a Quote') &&
              !!document.querySelector('section.sf-hero-inner')
      ? document.querySelector('section.sf-hero-inner').innerHTML.includes('Request a Quote') : null,
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    schema: (document.querySelector('script[type="application/ld+json"]') || {}).textContent || '',
  };
};

/* 标注层：Hero 量高条 + 按钮编号 + 左上信息卡 */
const annotate = (m) => {
  const hero = document.querySelector('section.sf-hero-inner');
  const r = hero.getBoundingClientRect();
  const top = r.top + scrollY, left = r.left + scrollX;
  // 350px 是**桌面**预算（单栏一屏内）；移动端堆叠后必然更高，无此判据
  const desk = innerWidth >= 1000;
  const budget = desk ? `（预算 ≤350px ${m.heroH <= 350 ? '✓' : '✗'}）` : '（移动端堆叠，无 350px 判据）';
  const mk = (tag, css, txt) => {
    const e = document.createElement(tag);
    e.className = 's2anno';                    // 统一标记，便于整体清除
    if (css) e.setAttribute('style', css);
    if (txt != null) e.textContent = txt;
    return e;
  };
  const box = mk('div', `position:absolute;left:${left}px;top:${top}px;width:${r.width}px;` +
    `height:${r.height}px;border:2px dashed #E11D48;box-sizing:border-box;pointer-events:none;z-index:99998`);
  document.body.appendChild(box);

  const tag = mk('div', `position:absolute;left:${left + 8}px;top:${top + 8}px;background:#E11D48;color:#fff;` +
    `font:700 13px/1.5 -apple-system,system-ui,sans-serif;padding:3px 9px;border-radius:3px;` +
    `pointer-events:none;z-index:99999`, `Hero 高度 ${m.heroH}px ${budget}`);
  document.body.appendChild(tag);

  // 右侧垂直量高条
  const bar = mk('div', `position:absolute;left:${left + r.width + 10}px;top:${top}px;width:2px;` +
    `height:${r.height}px;background:#E11D48;pointer-events:none;z-index:99999`);
  document.body.appendChild(bar);
  const barT = mk('div', `position:absolute;left:${left + r.width + 16}px;top:${top + r.height / 2 - 10}px;` +
    `color:#E11D48;font:700 12px/1.4 -apple-system,system-ui,sans-serif;` +
    `pointer-events:none;z-index:99999;white-space:nowrap`, `${m.heroH}px`);
  document.body.appendChild(barT);

  // 按钮编号
  const btns = hero.querySelectorAll('.wp-block-button__link');
  btns.forEach((b, i) => {
    const br = b.getBoundingClientRect();
    const bd = mk('div', `position:absolute;left:${br.left + scrollX - 2}px;top:${br.top + scrollY - 2}px;` +
      `width:${br.width + 4}px;height:${br.height + 4}px;border:2px solid #2563EB;box-sizing:border-box;` +
      `pointer-events:none;z-index:99999`);
    document.body.appendChild(bd);
    const badge = mk('div', `position:absolute;left:${br.left + scrollX - 10}px;top:${br.top + scrollY - 10}px;` +
      `width:20px;height:20px;border-radius:50%;background:#2563EB;color:#fff;text-align:center;` +
      `font:700 12px/20px -apple-system,system-ui,sans-serif;pointer-events:none;z-index:100000`,
      String(i + 1));
    document.body.appendChild(badge);
  });

  // 左上信息卡
  const rows = [
    `Hero 高度：${m.heroH}px ${budget}`,
    `轮播节点：${m.sliderNodes} 个（.sf-pslider / .sf-product-hero-image / .sf-slider-progress）`,
    `轮播脚本：${m.sliderScript} 个（已删 product-slider.js）`,
    `Hero 内两栏：${m.heroCols}（应为 0，已改单栏居中）`,
    `按钮：${m.buttons.length} 个`,
    ...m.buttons.map((b, i) => `　${i + 1}. ${b.text} → ${b.href}`),
    `H1 对齐：${m.h1Align}，高 ${m.h1H}px`,
    `横向溢出：${m.overflowX}px`,
  ];
  const card = mk('div', `position:fixed;left:12px;bottom:12px;max-width:min(640px,calc(100vw - 24px));` +
    `box-sizing:border-box;background:rgba(17,24,39,.94);` +
    `color:#fff;font:500 12.5px/1.7 -apple-system,system-ui,sans-serif;padding:11px 14px;border-radius:6px;` +
    `pointer-events:none;z-index:100001;white-space:pre-wrap;word-break:break-word`);
  card.textContent = rows.join('\n');
  document.body.appendChild(card);

  // 顶部徽标
  const badge = mk('div', `position:fixed;right:16px;top:16px;background:${m.sliderNodes === 0 ? '#059669' : '#DC2626'};` +
    `color:#fff;font:700 13px/1.5 -apple-system,system-ui,sans-serif;padding:5px 12px;border-radius:4px;` +
    `pointer-events:none;z-index:100001`,
    m.sliderNodes === 0 ? '✓ 无轮播' : '✗ 仍有轮播');
  document.body.appendChild(badge);
};

const clear = () => document.querySelectorAll('.s2anno').forEach((e) => e.remove());

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const report = {};
  for (const [label, w, h] of [['1440', 1440, 900], ['375', 375, 812]]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    for (const slug of PAGES) {
      await page.goto(`http://sinofresh.local/products/${slug}/`, { waitUntil: 'load' });
      await accept(page);
      await settle(page);
      await page.evaluate(() => scrollTo(0, 0));
      await page.waitForTimeout(250);
      const m = await page.evaluate(probe);
      report[`${slug}-${label}`] = m;

      await page.screenshot({ path: `${OUT}/s2-${slug}-${label}-首屏.png` });

      await page.evaluate(annotate, m);
      await page.waitForTimeout(200);
      await page.screenshot({ path: `${OUT}/s2-${slug}-${label}-首屏-标注.png` });
      await page.evaluate(clear);

      console.log(`${slug} @${label}  Hero=${m.heroH}px 轮播=${m.sliderNodes} 按钮=${m.buttons.length} `
        + `两栏=${m.heroCols} 脚本=${m.sliderScript} 溢出=${m.overflowX}`);
    }
    await ctx.close();
  }
  // 附加：Hero 元素特写（桌面）
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  for (const slug of PAGES) {
    await page.goto(`http://sinofresh.local/products/${slug}/`, { waitUntil: 'load' });
    await accept(page);
    await settle(page);
    const el = page.locator('section.sf-hero-inner');
    if (await el.count()) {
      await el.screenshot({ path: `${OUT}/s2-${slug}-1440-Hero特写.png` }).catch(() => {});
    }
  }
  await ctx.close();
  await browser.close();
  fs.writeFileSync(`${OUT}/measure.json`, JSON.stringify(report, null, 1));
  console.log('\n→ ' + OUT + '/measure.json');
})();
