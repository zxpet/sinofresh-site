// q5b: 灯箱交互测试修正版
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  const c = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await c.newPage();
  await p.goto('http://sinofresh.local/quality/', { waitUntil: 'networkidle' });

  const openLb = async (nth) => {
    const link = p.locator('.sf-certrow__media a').nth(nth);
    await link.scrollIntoViewIfNeeded();
    await p.waitForTimeout(300);
    const box = await link.boundingBox();
    await p.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
    await p.waitForTimeout(500);
  };
  const lbHidden = () => p.evaluate(() => document.querySelector('.sf-lb')?.hidden);

  // 1. open #2
  await openLb(1);
  console.log('open #2:', await p.evaluate(() => [document.querySelector('.sf-lb__count').textContent, !document.querySelector('.sf-lb').hidden]));

  // 2. backdrop click at bottom-right (clear of all buttons)
  await p.mouse.click(1380, 860);
  await p.waitForTimeout(500);
  console.log('backdrop click closes:', await lbHidden());

  // 3. prev button click (element click, not coordinates)
  await openLb(0);
  await p.click('.sf-lb__btn--prev');
  await p.waitForTimeout(400);
  console.log('prev btn wraps to 4/4:', await p.evaluate(() => document.querySelector('.sf-lb__count').textContent));

  // 4. backdrop close via Escape for cleanliness
  await p.keyboard.press('Escape');
  await p.waitForTimeout(400);

  // 5. meta-click must leave default nav alone (synthetic events cannot
  //    navigate, so assert defaultPrevented instead of a popup)
  console.log('meta-click defaultPrevented:', await p.evaluate(() => {
    const a = document.querySelectorAll('.sf-certrow__media a')[0];
    const ev = new MouseEvent('click', { bubbles: true, cancelable: true, metaKey: true, button: 0 });
    a.dispatchEvent(ev);
    return ev.defaultPrevented;
  }), '(expect false = native new tab preserved)');
  console.log('meta-click did not open lightbox:', await lbHidden());

  console.log('plain-click defaultPrevented:', await p.evaluate(() => {
    const a = document.querySelectorAll('.sf-certrow__media a')[0];
    const ev = new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 });
    a.dispatchEvent(ev);
    return ev.defaultPrevented;
  }), '(expect true = lightbox takes over)');
  await p.keyboard.press('Escape');

  // 6. keyboard: Tab stays inside the dialog
  await openLb(0);
  const tabWalk = [];
  for (let i = 0; i < 6; i++) {
    await p.keyboard.press('Tab');
    tabWalk.push(await p.evaluate(() => document.activeElement.className.replace('sf-lb__btn ', '')));
  }
  console.log('tab cycle:', JSON.stringify(tabWalk));
  await p.keyboard.press('Escape');

  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
