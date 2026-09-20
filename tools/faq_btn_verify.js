/**
 * 首页 FAQ 按钮 vs View All Articles 按钮一致性扫描 + 截图
 * 用法：node tools/faq_btn_verify.js <tag>
 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/faq-btn';
fs.mkdirSync(OUT, { recursive: true });
const tag = process.argv[2] || 'after';

(async () => {
  const b = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox', '--disable-dev-shm-usage'] });

  const measure = async (vw) => {
    const ctx = await b.newContext({ viewport: { width: vw, height: vw < 500 ? 812 : 900 }, isMobile: vw < 500, hasTouch: vw < 500 });
    const page = await ctx.newPage();
    page.setDefaultTimeout(30000);
    await page.goto('http://sinofresh.local/', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);

    const data = await page.evaluate(() => {
      const pick = el => {
        if (!el) return null;
        const c = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        return {
          cls: el.className,
          rect: { x: Math.round(r.x), w: Math.round(r.width), h: Math.round(r.height) },
          radius: c.borderRadius, border: `${c.borderTopWidth} ${c.borderTopStyle} ${c.borderTopColor}`,
          bg: c.backgroundColor, color: c.color, fontWeight: c.fontWeight,
          fontSize: c.fontSize, fontFamily: c.fontFamily.slice(0, 30),
          padding: `${c.paddingTop} ${c.paddingRight} ${c.paddingBottom} ${c.paddingLeft}`,
          display: c.display, transition: c.transitionDuration,
        };
      };
      const links = [...document.querySelectorAll('a.wp-block-button__link')];
      const faq = links.find(a => /View All FAQs/.test(a.textContent));
      const art = links.find(a => /View All Articles/.test(a.textContent));
      const coop = links.find(a => /Cooperation Models/.test(a.textContent));
      return {
        articles: pick(art), faq: pick(faq), coop: pick(coop),
        faqHref: faq ? faq.getAttribute('href') : null,
        overflow: document.documentElement.scrollWidth - window.innerWidth,
      };
    });

    // hover check on FAQ button
    if (vw >= 1000) {
      const faq = await page.$('a:has-text("View All FAQs")');
      if (faq) {
        await faq.scrollIntoViewIfNeeded().catch(() => { });
        await page.waitForTimeout(500);
        const before = await faq.evaluate(el => { const c = getComputedStyle(el); return { bg: c.backgroundColor, tf: c.transform }; });
        await faq.hover();
        await page.waitForTimeout(400);
        const after = await faq.evaluate(el => { const c = getComputedStyle(el); return { bg: c.backgroundColor, tf: c.transform }; });
        data.faqHover = { before, after, changed: before.bg !== after.bg || before.tf !== after.tf };
        // same for articles
        const art = await page.$('a:has-text("View All Articles")');
        await art.scrollIntoViewIfNeeded().catch(() => { });
        await page.waitForTimeout(400);
        await art.hover();
        await page.waitForTimeout(400);
        const aAfter = await art.evaluate(el => { const c = getComputedStyle(el); return { bg: c.backgroundColor, tf: c.transform }; });
        data.articlesHoverAfter = aAfter;
      }
    }

    // shots: FAQ button area + Articles button
    for (const [sel, name] of [['a:has-text("View All FAQs")', 'faq'], ['a:has-text("View All Articles")', 'articles']]) {
      const el = await page.$(sel);
      if (!el) { console.log('no el', name); continue; }
      await el.scrollIntoViewIfNeeded().catch(() => { });
      await page.waitForTimeout(600);
      // shoot the wrapping section chunk: button + some context
      const holder = await el.evaluateHandle(e => e.closest('.wp-block-buttons') || e.closest('p'));
      await holder.asElement().screenshot({ path: `${OUT}/${tag}-${name}-${vw}.png`, animations: 'disabled', timeout: 15000 }).catch(e => console.log('shot fail', name, e.message.split('\n')[0]));
      console.log('shot', name, vw);
    }
    await ctx.close();
    return data;
  };

  const d1440 = await measure(1440);
  const d375 = await measure(375);
  await b.close();
  fs.writeFileSync(`${OUT}/verify-${tag}.json`, JSON.stringify({ d1440, d375 }, null, 2));
  console.log('\n=== 1440 ===');
  console.log('FAQ  ', JSON.stringify(d1440.faq, null, 1));
  console.log('ART  ', JSON.stringify(d1440.articles, null, 1));
  console.log('COOP ', JSON.stringify(d1440.coop, null, 1));
  console.log('faqHref', d1440.faqHref, '| overflow', d1440.overflow);
  console.log('hover faq:', JSON.stringify(d1440.faqHover));
  console.log('hover articles after:', JSON.stringify(d1440.articlesHoverAfter));
  console.log('\n=== 375 ===  overflow:', d375.overflow, '| faq', JSON.stringify(d375.faq && d375.faq.rect));
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
