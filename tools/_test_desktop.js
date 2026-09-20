const pw = require('/Users/meng/.workbuddy/binaries/node/workspace/node_modules/playwright-core');
const CHROME = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
(async () => {
  const b = await pw.chromium.launch({ executablePath: CHROME, headless: true });
  const p = await (await b.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
  await p.goto('http://sinofresh.local/', { waitUntil: 'networkidle' });
  const el = await p.$('.sf-stories');
  await el.scrollIntoViewIfNeeded();
  await p.waitForTimeout(500);
  const d = await p.evaluate(() => {
    const m = document.querySelector('.sf-marquee.sf-stories');
    const cs = getComputedStyle(m);
    const t = getComputedStyle(m.querySelector('.sf-marquee__track'));
    const g = getComputedStyle(m.querySelector('.sf-stories__group'));
    const cards = [...m.querySelectorAll('.sf-story')];
    return { overflowX: cs.overflowX, scrollPad: cs.scrollPaddingLeft, anim: t.animationName, groupPadL: g.paddingLeft, groupPadR: g.paddingRight,
      cardW: getComputedStyle(cards[0]).width, snapAlign: getComputedStyle(cards[0]).scrollSnapAlign, visibleCards: cards.filter(c => c.getBoundingClientRect().width > 0).length };
  });
  console.log('=== 1440px 桌面 ===');
  console.log(JSON.stringify(d, null, 1));
  await p.screenshot({ path: 'tools/_m_shots/stories_1440_desktop.png' });
  await b.close();
})();
