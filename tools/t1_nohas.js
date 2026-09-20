/* 任务1 收尾验证：① 现代引擎（无 no-has）几何；② 模拟 html.no-has 降级后几何 */
const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
function ow(a, b) { if (!a || !b) return null; const x = Math.max(0, Math.min(a.r, b.r) - Math.max(a.x, b.x)); const y = Math.max(0, Math.min(a.b, b.b) - Math.max(a.y, b.y)); return x * y; }
const G = `const G=e=>{if(!e)return null;const r=e.getBoundingClientRect();const s=getComputedStyle(e);return{x:Math.round(r.x),y:Math.round(r.y),r:Math.round(r.right),b:Math.round(r.bottom),w:Math.round(r.width),radius:s.borderRadius,d:s.display};};`;

(async () => {
  const br = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  for (const mode of ['现代引擎（html 无 no-has）', '模拟 html.no-has 降级']) {
    console.log('\n########## ' + mode + ' ##########');
    for (const vw of [320, 375, 414, 767, 1440]) {
      const ctx = await br.newContext({ viewport: { width: vw, height: 812 } });
      const p = await ctx.newPage();
      await p.addInitScript(`(() => { try { localStorage.setItem('sf_cookie_consent', JSON.stringify({necessary:true,analytics:false,marketing:false})); } catch(e){}
        ${mode.includes('no-has') ? "document.addEventListener('DOMContentLoaded',()=>{document.documentElement.className+=' no-has';});" : ''} })()`);
      await p.goto('http://sinofresh.local/products/soft-chews/', { waitUntil: 'networkidle' });
      await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } });
      await p.waitForTimeout(900);
      const r = await p.evaluate(`(() => {${G}
        return { htmlCls: document.documentElement.className, bar:G(document.querySelector('.configurator__bar')),
                 sub:G(document.querySelector('.configurator__bar-submit')), sw:G(document.querySelector('.trp-language-switcher')), float:G(document.querySelector('.sf-float-stack')) };})()`);
      const hasNoHas = r.htmlCls.includes('no-has');
      console.log(' ' + String(vw).padStart(4) + ' | html.no-has=' + (hasNoHas ? 'Y' : 'n') +
        ' | sw radius=' + (r.sw ? r.sw.radius : '-') + ' y' + (r.sw ? r.sw.y + '..' + r.sw.b : '-') +
        ' | submit ' + (r.sub ? r.sub.x + '..' + r.sub.r + ' w' + r.sub.w : '-') +
        ' | 重叠 sub∩sw=' + ow(r.sub, r.sw) + ' sw∩float=' + ow(r.sw, r.float) + ' float∩bar=' + ow(r.float, r.bar));
      await ctx.close();
    }
  }
  await br.close();
})();
