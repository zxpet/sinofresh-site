const { chromium } = require('playwright-core');
const EXEC = process.env.HOME + '/Library/Caches/ms-playwright/chromium-1244/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const OUT = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/';

const SECTIONS = [
  ['cert', '.sf-certdetail'],
  ['lab', '.sf-eq'],
  ['steps', '.sf-qs'],
  ['pal', '.sf-pal'],
  ['faq', '.sf-faq'],
];

(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });

  for (const [tag, vp] of [['1440', { width: 1440, height: 900 }], ['375', { width: 375, height: 812 }]]) {
    const c = await b.newContext({ viewport: vp, deviceScaleFactor: 2 });
    const p = await c.newPage();
    await p.goto('http://sinofresh.local/quality/', { waitUntil: 'networkidle', timeout: 45000 });
    await p.evaluate(async () => { if (document.fonts) await document.fonts.ready; });
    // force all lazy images for element shots
    await p.evaluate(async () => {
      window.scrollTo(0, document.body.scrollHeight);
      await new Promise(r => setTimeout(r, 1200));
      window.scrollTo(0, 0);
      await new Promise(r => setTimeout(r, 400));
    });
    for (const [name, sel] of SECTIONS) {
      const el = await p.$(sel);
      if (!el) { console.log('MISS', tag, name); continue; }
      await el.scrollIntoViewIfNeeded();
      await p.waitForTimeout(300);
      await el.screenshot({ path: OUT + `q_${tag}_${name}.png` });
      const box = await el.boundingBox();
      console.log(`q_${tag}_${name}.png  ${Math.round(box.width)}x${Math.round(box.height)}`);
    }
    await p.screenshot({ path: OUT + `q_${tag}_fullpage.png`, fullPage: true });
    console.log(`q_${tag}_fullpage.png written`);
    await c.close();
  }
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
