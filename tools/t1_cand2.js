/* 任务1 第二轮：垂直堆叠方案实测（bar → switcher → float stack） */
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const CANDS = {
  'C5a 覆盖 bottom 属性': 'body:has(.configurator__bar) .trp-language-switcher{bottom:68px!important} body:has(.configurator__bar) .sf-float-stack{bottom:132px!important}',
  'C5b 覆盖 --bottom 变量': 'body:has(.configurator__bar) .trp-language-switcher{--bottom:68px!important} body:has(.configurator__bar) .sf-float-stack{bottom:132px!important}',
};

function ow(a, b) { if (!a || !b) return null; const x = Math.max(0, Math.min(a.r, b.r) - Math.max(a.x, b.x)); const y = Math.max(0, Math.min(a.b, b.b) - Math.max(a.y, b.y)); return x * y; }
const pad = (v, n) => String(v).padStart(n);

(async () => {
  const br = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  for (const [name, css] of Object.entries(CANDS)) {
    console.log('\n########## ' + name + ' ##########');
    for (const vw of [320, 360, 375, 414, 767, 768, 1440]) {
      const ctx = await br.newContext({ viewport: { width: vw, height: 812 } });
      const p = await ctx.newPage();
      await p.addInitScript(() => { try { localStorage.setItem('sf_cookie_consent', JSON.stringify({ necessary: true, analytics: false, marketing: false })); } catch (e) {} });
      await p.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'domcontentloaded' });
      await p.waitForTimeout(800);
      await p.addStyleTag({ content: '@media (max-width: 767px){' + css + '}' });
      await p.waitForTimeout(400);
      const r = await p.evaluate(() => {
        const Q = s => document.querySelector(s);
        const G = e => { if (!e) return null; const r = e.getBoundingClientRect(); const st = getComputedStyle(e); return { x: Math.round(r.x), y: Math.round(r.y), r: Math.round(r.right), b: Math.round(r.bottom), w: Math.round(r.width), h: Math.round(r.height), vis: st.display !== 'none' }; };
        return {
          bar: G(Q('.configurator__bar')), sub: G(Q('.configurator__bar-submit')),
          sw: G(Q('.trp-language-switcher')), float: G(Q('.sf-float-stack')),
        };
      });
      const { bar, sub, sw, float } = r;
      const vis = bar && bar.vis;
      const tag = ' ' + pad(vw, 4) + ' | ';
      if (!vis) {
        console.log(tag + '无配置器条 | sw y' + (sw ? sw.y + '..' + sw.b : '-') + ' | float y' + (float ? float.y + '..' + float.b : '-') + (vw >= 768 ? '  ← 桌面/平板须与基线一致' : ''));
      } else {
        console.log(tag + 'bar y' + bar.y + '..' + bar.b + ' | submit ' + sub.x + '..' + sub.r + ' w' + sub.w +
          ' | sw y' + sw.y + '..' + sw.b + ' x' + sw.x + '..' + sw.r +
          ' | float y' + float.y + '..' + float.b +
          ' || 重叠 sub∩sw=' + ow(sub, sw) + ' sw∩float=' + ow(sw, float) + ' float∩bar=' + ow(float, bar) + ' float∩sw=' + ow(float, sw));
      }
      await ctx.close();
    }
  }
  await br.close();
})();
