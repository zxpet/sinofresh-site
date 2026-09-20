const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const vp of [375, 768]) {
    const ctx = await b.newContext({ viewport: { width: vp, height: 900 }, isMobile: vp <= 768, hasTouch: vp <= 768 });
    const p = await ctx.newPage();
    await p.goto('http://sinofresh.local/factory-tour/', { waitUntil: 'networkidle' });
    await p.evaluate(async () => { await document.fonts.ready; });
    const r = await p.evaluate(() => {
      const px = (v) => Math.round(parseFloat(v) || 0);
      const wrap = document.querySelector('.gform_wrapper');
      const fields = document.querySelector('.gform_fields');
      const inputs = [...document.querySelectorAll('.gform_fields input:not([type=hidden]):not([type=submit]), .gform_fields select, .gform_fields textarea')];
      return {
        wrapFound: !!wrap, wrapClass: wrap ? wrap.className.slice(0, 60) : null,
        fieldsDisplay: fields ? getComputedStyle(fields).display : null,
        fieldsCols: fields ? getComputedStyle(fields).gridTemplateColumns.slice(0, 40) : null,
        tops: [...new Set(inputs.map((i) => px(i.getBoundingClientRect().top)))].length,
        n: inputs.length,
        fs: [...new Set(inputs.map((i) => getComputedStyle(i).fontSize))],
        h: inputs.map((i) => px(i.getBoundingClientRect().height)),
      };
    });
    console.log(vp + ': ' + JSON.stringify(r));
    await ctx.close();
  }
  await b.close();
})();
