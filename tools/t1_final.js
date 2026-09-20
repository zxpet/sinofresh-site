/* 任务1 第四轮：最终片段验证（不带 !important，靠特异性）+ 抽屉按钮逐项重叠 */
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

const FINAL = [
  'body:has(.configurator__bar) .trp-language-switcher{bottom:68px}',
  'body:has(.configurator__bar) .sf-float-stack{bottom:132px}',
  'body:has(.configurator__drawer.is-open) .trp-language-switcher{display:none}',
  'body:has(.configurator__drawer.is-open) .sf-float-stack{display:none}',
].join(' ');

const CANDS = { 'BASE 基线': '', 'FINAL 最终片段（无 !important）': FINAL };
function ow(a, b) { if (!a || !b) return null; const x = Math.max(0, Math.min(a.r, b.r) - Math.max(a.x, b.x)); const y = Math.max(0, Math.min(a.b, b.b) - Math.max(a.y, b.y)); return x * y; }
const G_JS = `const G = e => { if(!e) return null; const r=e.getBoundingClientRect(); const st=getComputedStyle(e); return {x:Math.round(r.x),y:Math.round(r.y),r:Math.round(r.right),b:Math.round(r.bottom),w:Math.round(r.width),h:Math.round(r.height),d:st.display}; };`;

(async () => {
  const br = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  for (const [name, css] of Object.entries(CANDS)) {
    console.log('\n########## ' + name + ' ##########');
    for (const vw of [320, 375, 414, 767, 1440]) {
      const ctx = await br.newContext({ viewport: { width: vw, height: 812 } });
      const p = await ctx.newPage();
      await p.addInitScript(() => { try { localStorage.setItem('sf_cookie_consent', JSON.stringify({ necessary: true, analytics: false, marketing: false })); } catch (e) {} });
      await p.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'domcontentloaded' });
      await p.waitForTimeout(900);
      if (css) await p.addStyleTag({ content: '@media (max-width: 767px){' + css + '}' });
      await p.waitForTimeout(400);

      const closed = await p.evaluate(`(() => {${G_JS}
        return { bar:G(document.querySelector('.configurator__bar')), sub:G(document.querySelector('.configurator__bar-submit')),
                 sw:G(document.querySelector('.trp-language-switcher')), float:G(document.querySelector('.sf-float-stack')) };})()`);

      await p.evaluate(() => { const t = document.querySelector('.configurator__bar-trigger'); if (t) t.click(); });
      await p.waitForTimeout(700);
      const open = await p.evaluate(`(() => {${G_JS}
        const btns=[...document.querySelectorAll('.configurator__drawer-actions button, .configurator__drawer-actions a')].map(e=>({t:e.textContent.trim().slice(0,16),...G(e)}));
        return { sw:G(document.querySelector('.trp-language-switcher')), float:G(document.querySelector('.sf-float-stack')), acts:[...document.querySelectorAll('.configurator__drawer-actions')].map(G), btns };})()`);

      const barOn = closed.bar && closed.bar.d !== 'none';
      const line = [];
      if (barOn) {
        line.push('未展开 submit ' + closed.sub.x + '..' + closed.sub.r + ' (w' + closed.sub.w + ')');
        line.push('sw y' + closed.sw.y + '..' + closed.sw.b + ' x' + closed.sw.x + '..' + closed.sw.r);
        line.push('重叠 sub∩sw=' + ow(closed.sub, closed.sw) + ' sw∩float=' + ow(closed.sw, closed.float) + ' float∩bar=' + ow(closed.float, closed.bar));
      } else {
        line.push('无 bar | sw y' + (closed.sw ? closed.sw.y + '..' + closed.sw.b : '-') + ' | float y' + (closed.float ? closed.float.y + '..' + closed.float.b : '-'));
      }
      const swOpen = open.sw && open.sw.d !== 'none' ? open.sw : null;
      line.push('|| 抽屉展开 sw ' + (open.sw ? (open.sw.d === 'none' ? 'display:none' : 'y' + open.sw.y + '..' + open.sw.b) : '-'));
      line.push('按钮重叠[' + open.btns.map(b => b.t + '=' + ow(swOpen, b)).join(' ') + ']');
      console.log(' ' + String(vw).padStart(4) + ' | ' + line.join(' | '));
      await ctx.close();
    }
  }
  await br.close();
})();
