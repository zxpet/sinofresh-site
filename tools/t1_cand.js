/* 任务1 候选修复方案实测（注入 CSS 量几何，不改文件） */
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const CANDS = {
  'C0 基线（不改）': '',
  'C1 bar 预留右空间': 'body:has(.configurator__bar) .configurator__bar{padding-right:calc(10vw + 136px)!important}',
  'C2 switcher 上移': 'body:has(.configurator__bar) .trp-language-switcher{--bottom:72px!important}',
  'C3 C2 + float 上移': 'body:has(.configurator__bar) .trp-language-switcher{--bottom:72px!important} body:has(.configurator__bar) .sf-float-stack{bottom:72px!important}',
  'C4 C1 + float 上移': 'body:has(.configurator__bar) .configurator__bar{padding-right:calc(10vw + 136px)!important} body:has(.configurator__bar) .sf-float-stack{bottom:72px!important}',
};

function ow(a, b) {
  if (!a || !b) return null;
  const x = Math.max(0, Math.min(a.r, b.r) - Math.max(a.x, b.x));
  const y = Math.max(0, Math.min(a.b, b.b) - Math.max(a.y, b.y));
  return x * y;
}
const pad = (v, n) => String(v).padStart(n);

(async () => {
  const br = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  for (const [name, css] of Object.entries(CANDS)) {
    console.log('\n########## ' + name + ' ##########');
    for (const vw of [320, 360, 375, 414, 767, 1440]) {
      const ctx = await br.newContext({ viewport: { width: vw, height: 812 } });
      const p = await ctx.newPage();
      await p.addInitScript(() => { try { localStorage.setItem('sf_cookie_consent', JSON.stringify({ necessary: true, analytics: false, marketing: false })); } catch (e) {} });
      await p.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'domcontentloaded' });
      await p.waitForTimeout(900);
      if (css) await p.addStyleTag({ content: '@media (max-width: 767px){' + css + '}' });
      await p.waitForTimeout(400);
      const r = await p.evaluate(() => {
        const Q = s => document.querySelector(s);
        const G = e => { if (!e) return null; const r = e.getBoundingClientRect(); const st = getComputedStyle(e); return { x: Math.round(r.x), y: Math.round(r.y), r: Math.round(r.right), b: Math.round(r.bottom), w: Math.round(r.width), h: Math.round(r.height), vis: st.display !== 'none' && st.visibility !== 'hidden' }; };
        const sw = Q('.trp-language-switcher');
        return {
          bar: G(Q('.configurator__bar')), trig: G(Q('.configurator__bar-trigger')),
          sub: G(Q('.configurator__bar-submit')), sw: G(sw), float: G(Q('.sf-float-stack')),
          swBottomVar: sw ? getComputedStyle(sw).getPropertyValue('--bottom').trim() : null,
        };
      });
      const { bar, trig, sub, sw, float } = r;
      if (!bar || !bar.vis) {
        console.log(' ' + pad(vw, 4) + ' | 无配置器条' + (sw ? ' | switcher y=' + sw.y + '..' + sw.b : ''));
      } else {
        const oSubSw = ow(sub, sw), oSwFl = ow(sw, float), oFlBar = ow(float, bar);
        console.log(' ' + pad(vw, 4) + ' | bar ' + bar.x + '..' + bar.r + ' y' + bar.y +
          ' | trig w=' + (trig ? trig.w : '-') +
          ' | submit ' + sub.x + '..' + sub.r + ' w=' + sub.w +
          ' | sw ' + sw.x + '..' + sw.r + ' y' + sw.y + '..' + sw.b + ' (--bottom=' + r.swBottomVar + ')' +
          ' | 重叠: sub∩sw=' + oSubSw + ' sw∩float=' + oSwFl + ' float∩bar=' + oFlBar);
      }
      await ctx.close();
    }
  }
  await br.close();
})();
