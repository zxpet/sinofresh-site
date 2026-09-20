/* 任务1 第三轮：抽屉展开态的层叠核查（baseline vs C1 vs C5） */
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const CANDS = {
  'BASE 基线': '',
  'C1 bar 预留右空间': 'body:has(.configurator__bar) .configurator__bar{padding-right:calc(10vw + 136px)}',
  'C5 垂直堆叠': 'body:has(.configurator__bar) .trp-language-switcher{bottom:68px} body:has(.configurator__bar) .sf-float-stack{bottom:132px}',
};
function ow(a, b) { if (!a || !b) return null; const x = Math.max(0, Math.min(a.r, b.r) - Math.max(a.x, b.x)); const y = Math.max(0, Math.min(a.b, b.b) - Math.max(a.y, b.y)); return x * y; }

(async () => {
  const br = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  for (const [name, css] of Object.entries(CANDS)) {
    console.log('\n########## ' + name + ' ##########');
    for (const vw of [375, 320]) {
      const ctx = await br.newContext({ viewport: { width: vw, height: 812 } });
      const p = await ctx.newPage();
      await p.addInitScript(() => { try { localStorage.setItem('sf_cookie_consent', JSON.stringify({ necessary: true, analytics: false, marketing: false })); } catch (e) {} });
      await p.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'domcontentloaded' });
      await p.waitForTimeout(900);
      if (css) await p.addStyleTag({ content: '@media (max-width: 767px){' + css + '}' });
      await p.waitForTimeout(300);

      const closed = await p.evaluate(() => {
        const G = e => { if (!e) return null; const r = e.getBoundingClientRect(); return { x: Math.round(r.x), y: Math.round(r.y), r: Math.round(r.right), b: Math.round(r.bottom), w: Math.round(r.width), h: Math.round(r.height) }; };
        return { sub: G(document.querySelector('.configurator__bar-submit')), sw: G(document.querySelector('.trp-language-switcher')) };
      });

      // 点开抽屉
      await p.evaluate(() => { const t = document.querySelector('.configurator__bar-trigger'); if (t) t.click(); });
      await p.waitForTimeout(700);
      const open = await p.evaluate(() => {
        const G = e => { if (!e) return null; const r = e.getBoundingClientRect(); return { x: Math.round(r.x), y: Math.round(r.y), r: Math.round(r.right), b: Math.round(r.bottom), w: Math.round(r.width), h: Math.round(r.height) }; };
        const d = document.querySelector('.configurator__drawer');
        const acts = document.querySelector('.configurator__drawer-actions');
        const btns = [...document.querySelectorAll('.configurator__drawer-actions button, .configurator__drawer-actions a')].map(e => ({ t: e.textContent.trim().slice(0, 14), ...G(e) }));
        return { drawer: G(d), isOpen: d ? d.classList.contains('is-open') : null, actions: G(acts), btns };
      });
      const sw = closed.sw;
      const hits = open.btns.map(b => (b.t || '?') + '=' + ow(sw, b));
      console.log(' ' + vw + ' | 未展开: submit..' + closed.sub.r + ' sw.x' + sw.x +
        ' | 抽屉 isOpen=' + open.isOpen + ' 动作区 y' + (open.actions ? open.actions.y + '..' + open.actions.b : '-') +
        ' | sw y' + sw.y + '..' + sw.b + ' || sw∩动作区=' + ow(sw, open.actions) + ' | ' + hits.join(' '));
      await ctx.close();
    }
  }
  await br.close();
})();
