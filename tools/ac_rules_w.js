// 375px 下溯源 .sf-slot--cover 的 padding / 图片宽高来自哪条规则
const { chromium } = require('playwright-core');
const EXEC = '/Users/meng/.agent-browser/browsers/chrome-153.0.8010.36/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing';
const W = +(process.argv[2] || 375);
(async () => {
  const b = await chromium.launch({ executablePath: EXEC, headless: true });
  const ctx = await b.newContext({ viewport: { width: W, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('http://sinofresh.local/', { waitUntil: 'load', timeout: 30000 });
  await page.waitForSelector('.sf-slot--cover');
  await page.evaluate(() => document.querySelector('.sf-slot--cover').closest('section').scrollIntoView({ block: 'center' }));
  await page.waitForFunction(() => [...document.querySelectorAll('.sf-slot--cover img')].every(i => i.complete && i.naturalWidth > 0), { timeout: 15000 });
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('DOM.enable'); await cdp.send('CSS.enable');
  const { root } = await cdp.send('DOM.getDocument');
  const sel = '.sf-slot--cover, .sf-slot--cover .wp-block-image, .sf-slot--cover img';
  const { nodeIds } = await cdp.send('DOM.querySelectorAll', { nodeId: root.nodeId, selector: sel });
  console.log('viewport ' + W + ' 命中节点 ' + nodeIds.length);
  for (const nodeId of nodeIds) {
    const { node } = await cdp.send('DOM.describeNode', { nodeId });
    const attrs = node.attributes || [];
    let cls = '';
    for (let i = 0; i < attrs.length; i += 2) if (attrs[i] === 'class') cls = attrs[i + 1];
    console.log('\n#### ' + node.nodeName + ' .' + cls.split(' ').slice(0, 5).join('.'));
    const ms = await cdp.send('CSS.getMatchedStylesForNode', { nodeId });
    const src = async (m) => {
      try {
        const st = await cdp.send('CSS.getStyleSheetText', { styleSheetId: m.rule.styleSheetId });
        const r = m.rule.style.range;
        if (!r) return '';
        const line = st.text.slice(0, r.start).split('\n').length;
        return '  L' + line;
      } catch (e) { return ''; }
    };
    for (const m of ms.matchedCSSRules || []) {
      const t = (m.rule.style && m.rule.style.cssText) || '';
      if (!/padding|width|height|gap|overflow|border-radius|aspect-ratio|place|display|max-width/i.test(t)) continue;
      const loc = await src(m);
      console.log('  [' + m.rule.origin + '] ' + m.rule.selectorList.text.slice(0, 100) + loc);
      console.log('      ' + t.replace(/\s+/g, ' ').slice(0, 220));
    }
  }
  await b.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
