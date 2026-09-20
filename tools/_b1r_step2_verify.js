/* Batch 1 / 步骤 2 — Hero 极简化后核验探针。
   区块抽取逻辑与 tools/_b1r_scan.js 完全相同（.wp-site-blocks > .wp-block-group|section，
   键 {id, cls, top, h, bg, firstHeading}），因此可与步骤 2 前置扫描的 /tmp/b1s/scan.json
   做逐区块对比，判定「除 Hero 外零回归」。

   输出：/tmp/b1/step2/verify2.json
   用法：node tools/_b1r_step2_verify.js */
const fs = require('fs');
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const PAGES = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids', 'fish-oil', 'dental-chews'];
const VIEWS = {
  desktop: { width: 1440, height: 900 },
  tablet: { width: 900, height: 900 },
  mobile: { width: 375, height: 812 },
};

function probe() {
  const q = (s) => document.querySelector(s);
  const hero = q('section.sf-hero-inner');
  const h1 = q('section.sf-hero-inner h1');
  const para = q('section.sf-hero-inner p');
  const crumb = q('section.sf-hero-inner .sf-breadcrumb');
  const btnsWrap = q('section.sf-hero-inner .wp-block-buttons');
  const btns = Array.from(document.querySelectorAll('section.sf-hero-inner .wp-block-button > a')).map((a) => ({
    text: a.textContent.trim(),
    href: a.getAttribute('href'),
    h: Math.round(a.getBoundingClientRect().height),
    w: Math.round(a.getBoundingClientRect().width),
    filled: /has-cta-background-color/.test(a.className),
    outline: /is-style-outline/.test(a.closest('.wp-block-button').className),
  }));
  const slides = document.querySelectorAll('section.sf-hero-inner .sf-pslider, section.sf-hero-inner .sf-pslider__slide');
  const secs = Array.from(document.querySelectorAll('.wp-site-blocks > .wp-block-group, .wp-site-blocks > section')).map((s) => {
    const inner = s.querySelector('h2, h3');
    return {
      id: s.id || null,
      cls: String(s.getAttribute('class') || '').replace('wp-block-group', '').trim().slice(0, 60),
      top: Math.round(s.getBoundingClientRect().top + scrollY),
      h: Math.round(s.getBoundingClientRect().height),
      bg: getComputedStyle(s).backgroundColor,
      firstHeading: inner ? inner.textContent.trim().slice(0, 48) : null,
    };
  });
  const btnDiv = q('section.sf-hero-inner .wp-block-buttons');
  return {
    url: location.pathname,
    docHeight: document.documentElement.scrollHeight,
    overflowX: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
    hero: {
      h: hero ? Math.round(hero.getBoundingClientRect().height) : null,
      top: hero ? Math.round(hero.getBoundingClientRect().top + scrollY) : null,
      pt: hero ? getComputedStyle(hero).paddingTop : null,
      pb: hero ? getComputedStyle(hero).paddingBottom : null,
      bg: hero ? getComputedStyle(hero).backgroundColor : null,
      childTags: hero ? Array.from(hero.children).map((c) => c.tagName.toLowerCase() + '.' + String(c.getAttribute('class') || '').split(' ').slice(0, 2).join('.')) : [],
    },
    h1: h1 ? {
      text: h1.textContent.trim(),
      h: Math.round(h1.getBoundingClientRect().height),
      w: Math.round(h1.getBoundingClientRect().width),
      fs: getComputedStyle(h1).fontSize,
      ta: getComputedStyle(h1).textAlign,
      cls: String(h1.getAttribute('class')),
    } : null,
    p: para ? {
      text: para.textContent.trim(),
      h: Math.round(para.getBoundingClientRect().height),
      w: Math.round(para.getBoundingClientRect().width),
      fs: getComputedStyle(para).fontSize,
      ta: getComputedStyle(para).textAlign,
      cls: String(para.getAttribute('class')),
    } : null,
    paraCount: document.querySelectorAll('section.sf-hero-inner p').length,
    crumb: crumb ? { h: Math.round(crumb.getBoundingClientRect().height), text: crumb.textContent.trim() } : null,
    btnWrap: btnsWrap ? {
      h: Math.round(btnsWrap.getBoundingClientRect().height),
      w: Math.round(btnsWrap.getBoundingClientRect().width),
      justifyContent: getComputedStyle(btnDiv).justifyContent,
      mt: getComputedStyle(btnDiv).marginTop,
      cls: String(btnDiv.getAttribute('class')),
      nBtn: btnsWrap.querySelectorAll('.wp-block-button').length,
    } : null,
    buttons: btns,
    sliderNodes: slides.length,
    heroCols: hero ? hero.querySelectorAll('.wp-block-columns').length : null,
    cols: hero ? Array.from(hero.querySelectorAll(':scope > .wp-block-columns > .wp-block-column')).map((c) => Math.round(c.getBoundingClientRect().height)) : [],
    sections: secs,
  };
}

(async () => {
  const browser = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const out = {};
  for (const [view, vp] of Object.entries(VIEWS)) {
    out[view] = {};
    const ctx = await browser.newContext({ viewport: vp });
    for (const slug of PAGES) {
      const page = await ctx.newPage();
      let r;
      try {
        const resp = await page.goto(`http://sinofresh.local/products/${slug}/`, { waitUntil: 'load', timeout: 45000 });
        const rej = page.locator('button:has-text("Reject Non-Essential")');
        if (await rej.count()) await rej.first().click({ force: true }).catch(() => {});
        await page.evaluate(async () => {
          const s = Math.round(innerHeight * 0.8);
          for (let y = 0; y < document.body.scrollHeight; y += s) { scrollTo(0, y); await new Promise((r) => setTimeout(r, 50)); }
          scrollTo(0, 0);
          await new Promise((r) => setTimeout(r, 250));
        });
        r = await page.evaluate(probe);
        r.http = resp ? resp.status() : 0;
      } catch (e) {
        r = { error: String(e).slice(0, 200) };
      }
      out[view][slug] = r;
      await page.close();
    }
    await ctx.close();
  }
  fs.mkdirSync('/tmp/b1/step2', { recursive: true });
  const OUT = process.env.V_OUT || '/tmp/b1/step2/verify2.json';
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
  console.log('wrote ' + OUT);

  const d = out.desktop;
  console.log('\n=== 桌面 1440：Hero ===');
  for (const s of PAGES) {
    const x = d[s];
    console.log(`  ${s.padEnd(13)} http=${x.http} heroH=${String(x.hero.h).padStart(4)} pt/pb=${x.hero.pt}/${x.hero.pb}`
      + ` h1=${x.h1.h}(${x.h1.ta}) p=${x.p.h}(${x.p.fs}) crumb=${x.crumb.h}`
      + ` btnWrap=${x.btnWrap.h} nBtn=${x.btnWrap.nBtn} jc=${x.btnWrap.justifyContent}`
      + ` slider=${x.sliderNodes} cols=${x.heroCols} ovfX=${x.overflowX}`);
  }
  console.log('\n=== 移动 375 ===');
  const m = out.mobile;
  for (const s of PAGES) {
    const x = m[s];
    console.log(`  ${s.padEnd(13)} heroH=${String(x.hero.h).padStart(4)} h1=${String(x.h1.h).padStart(3)} p=${String(x.p.h).padStart(3)}`
      + ` btnWrap=${String(x.btnWrap.h).padStart(3)} nBtn=${x.btnWrap.nBtn} slider=${x.sliderNodes} ovfX=${x.overflowX}`);
  }
  await browser.close();
})();
