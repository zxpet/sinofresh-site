// q5: 灯箱交互测试（桌面）
const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/';

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  const c = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await c.newPage();
  await p.goto('http://sinofresh.local/quality/', { waitUntil: 'networkidle' });
  await p.evaluate(async () => { if (document.fonts) await document.fonts.ready; });

  const link = p.locator('.sf-certrow__media a').first();
  await link.scrollIntoViewIfNeeded();
  await p.waitForTimeout(400);

  // hit-test then real click
  const box = await link.boundingBox();
  const hit = await p.evaluate(([x, y]) => document.elementFromPoint(x, y)?.closest('.sf-certrow__media a') !== null, [box.x + box.width / 2, box.y + box.height / 2]);
  console.log('hit-test:', hit);

  await p.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await p.waitForTimeout(600);

  let st = await p.evaluate(() => {
    const lb = document.querySelector('.sf-lb');
    return {
      lbExists: !!lb, lbOpen: lb ? !lb.hidden : false, isOpenClass: lb ? lb.classList.contains('is-open') : false,
      src: lb ? (lb.querySelector('img').src || '').split('/').pop() : null,
      count: lb ? lb.querySelector('.sf-lb__count').textContent : null,
      scrollLocked: document.documentElement.classList.contains('sf-lb-open'),
      focusedIsClose: document.activeElement === (lb && lb.querySelector('.sf-lb__btn--close')),
      itemCount: document.querySelectorAll('.sf-certrow__media a').length
    };
  });
  console.log('after click:', JSON.stringify(st));
  await p.screenshot({ path: OUT + 'q_1440_lightbox.png' });

  // next → 2/4
  await p.keyboard.press('ArrowRight');
  await p.waitForTimeout(400);
  st = await p.evaluate(() => document.querySelector('.sf-lb__count').textContent + ' ' + document.querySelector('.sf-lb__img').src.split('/').pop());
  console.log('after ArrowRight:', st);

  // prev twice → wraps to 4/4
  await p.keyboard.press('ArrowLeft');
  await p.keyboard.press('ArrowLeft');
  await p.waitForTimeout(400);
  console.log('after 2x ArrowLeft:', await p.evaluate(() => document.querySelector('.sf-lb__count').textContent));

  // Esc closes
  await p.keyboard.press('Escape');
  await p.waitForTimeout(500);
  st = await p.evaluate(() => ({
    hidden: document.querySelector('.sf-lb').hidden,
    unlocked: !document.documentElement.classList.contains('sf-lb-open'),
    focusBack: document.activeElement.classList.contains('sf-certrow__media') || !!document.activeElement.closest('.sf-certrow__media')
  }));
  console.log('after Esc:', JSON.stringify(st));

  // backdrop click opens + closes
  await p.locator('.sf-certrow__media a').nth(1).click();
  await p.waitForTimeout(500);
  await p.mouse.click(60, 450); // far left = backdrop
  await p.waitForTimeout(500);
  console.log('after backdrop click:', await p.evaluate(() => document.querySelector('.sf-lb').hidden));

  // modifier-click must NOT open the lightbox (native new tab)
  const [nav] = await Promise.all([
    p.waitForEvent('popup', { timeout: 4000 }).catch(() => null),
    p.evaluate(() => {
      const a = document.querySelectorAll('.sf-certrow__media a')[0];
      const ev = new MouseEvent('click', { bubbles: true, cancelable: true, metaKey: true, button: 0 });
      a.dispatchEvent(ev);
    })
  ]);
  console.log('meta-click opened popup (native):', !!nav);
  console.log('lightbox stayed closed:', await p.evaluate(() => document.querySelector('.sf-lb').hidden));

  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
