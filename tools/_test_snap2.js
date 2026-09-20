const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const ctx = await b.newContext({ viewport: { width: 375, height: 812 } });
  const p = await ctx.newPage();
  await p.goto('http://sinofresh.local/', { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready);
  const el = await p.$('.sf-stories');
  await el.scrollIntoViewIfNeeded();
  await p.waitForTimeout(300);
  const results = {};
  for (const [label, i] of [['first(0)', 0], ['mid(3)', 3], ['last(5)', 5]]) {
    await p.evaluate(idx => {
      const cards = [...document.querySelectorAll('.sf-marquee.sf-stories .sf-story')].filter(c => c.getBoundingClientRect().width > 0);
      cards[idx].scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'center' });
    }, i);
    await p.waitForTimeout(700);
    results[label] = await p.evaluate(() => {
      const cards = [...document.querySelectorAll('.sf-marquee.sf-stories .sf-story')].filter(c => c.getBoundingClientRect().width > 0);
      return cards.map(c => { const r = c.getBoundingClientRect(); return { l: +r.left.toFixed(1), r: +r.right.toFixed(1) }; }).filter(x => x.r > 0 && x.l < 375);
    });
  }
  console.log('=== 375px 吸附实测（可见卡 left/right，预期被吸附卡 28.1/346.9） ===');
  console.log(JSON.stringify(results, null, 1));
  // 首卡居中状态截图（关掉 cookie 弹窗）
  await p.evaluate(() => document.querySelectorAll('.sf-marquee.sf-stories .sf-story')[0].scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'center' }));
  await p.waitForTimeout(700);
  try { await p.click('text=Reject Non-Essential', { timeout: 3000 }); } catch (e) {}
  await p.waitForTimeout(300);
  await p.screenshot({ path: 'tools/_m_shots/stories_375_after_center.png' });
  // 中间卡截图
  await p.evaluate(() => { const cs = [...document.querySelectorAll('.sf-marquee.sf-stories .sf-story')].filter(c => c.getBoundingClientRect().width > 0); cs[3].scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'center' }); });
  await p.waitForTimeout(700);
  await p.screenshot({ path: 'tools/_m_shots/stories_375_after_mid.png' });
  await b.close();
  console.log('screenshots saved');
})();
