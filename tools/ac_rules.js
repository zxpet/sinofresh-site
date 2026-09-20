// 用 CDP 找出 slot 的 padding / 图片宽高 是谁设的
const { chromium } = require('playwright-core');
const EXEC = '/Users/meng/.agent-browser/browsers/chrome-153.0.8010.36/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('http://sinofresh.local/', { waitUntil: 'load', timeout: 30000 });
  await page.waitForSelector('.sf-slot--cover');
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('DOM.enable'); await cdp.send('CSS.enable');
  const { root } = await cdp.send('DOM.getDocument');
  const sel = '.sf-slot--cover, .sf-slot--cover .wp-block-image, .sf-slot--cover img';
  const { nodeIds } = await cdp.send('DOM.querySelectorAll', { nodeId: root.nodeId, selector: sel });
  for (const nodeId of nodeIds) {
    const { node } = await cdp.send('DOM.describeNode', { nodeId });
    const attrs = node.attributes || [];
    let cls = '';
    for (let i = 0; i < attrs.length; i += 2) if (attrs[i] === 'class') cls = attrs[i + 1];
    console.log('\n#### ' + node.nodeName + ' .' + cls.split(' ').slice(0, 4).join('.'));
    const ms = await cdp.send('CSS.getMatchedStylesForNode', { nodeId });
    for (const m of ms.matchedCSSRules || []) {
      const t = (m.rule.style && m.rule.style.cssText) || '';
      if (!/padding|width|height|gap|overflow|border-radius|aspect-ratio|place-items|display/i.test(t)) continue;
      console.log('  [' + m.rule.origin + '] ' + m.rule.selectorList.text.slice(0, 110));
      console.log('      ' + t.slice(0, 220));
    }
  }
  await b.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
