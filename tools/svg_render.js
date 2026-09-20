/* Render the nav SVG large for visual comparison. */
const { chromium } = require('playwright-core');
(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--disable-gpu', '--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1240, height: 320 }, deviceScaleFactor: 1 });
  const svgPath = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme/assets/images/sinofresh-logo-nav.svg';
  const fs = require('fs');
  const svg = fs.readFileSync(svgPath, 'utf8');
  await page.setContent(`<body style="margin:0;background:#1B4D3E;display:flex;align-items:center;justify-content:center;height:320px">${svg.replace('<svg ', '<svg width="1200" ')}</body>`);
  await page.waitForTimeout(300);
  await page.screenshot({ path: '/Users/meng/WorkBuddy/sinofresh外贸网站建设/screenshots/round6/svg-nav-render-1200.png' });
  await browser.close();
  console.log('ok');
})();
