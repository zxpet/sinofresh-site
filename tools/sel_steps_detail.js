const { chromium } = require('playwright-core');
const PAGES = [
  ['home', '/'], ['soft-chews', '/products/soft-chews/'], ['drops', '/products/drops/'],
  ['services', '/services/'], ['products', '/products/'], ['about', '/about/'],
];
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  for (const [n, u] of PAGES) {
    const c = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    const p = await c.newPage();
    await p.goto('http://sinofresh.local' + u, { waitUntil: 'networkidle' });
    const r = await p.evaluate(() => {
      const px = (v) => Math.round(parseFloat(v) || 0);
      const sections = [...document.querySelectorAll('section')].filter((s) =>
        s.querySelector(':scope > .wp-block-columns > .wp-block-column > .wp-block-group.has-top-border-color')
      );
      return {
        body: [...document.body.classList].filter((x) => /page|template|postid|single/.test(x)).join(' '),
        docH: document.documentElement.scrollHeight,
        sections: sections.map((s) => {
          const groups = [...s.querySelectorAll(':scope > .wp-block-columns')];
          return {
            head: s.querySelector('h2') ? s.querySelector('h2').textContent.trim() : null,
            secCls: s.className.replace(/wp-container-core-group[\w-]*/g, '').replace(/\s+/g, ' ').trim().slice(0, 70),
            groups: groups.map((g) => ({
              cls: g.className.replace(/wp-container-core-columns[\w-]*/g, '').replace(/\s+/g, ' ').trim(),
              n: g.querySelectorAll(':scope > .wp-block-column').length,
              disp: getComputedStyle(g).display,
              tracks: getComputedStyle(g).gridTemplateColumns,
              colW: [...g.children].map((k) => px(k.getBoundingClientRect().width)),
              colT: [...g.children].map((k) => px(k.getBoundingClientRect().top)),
            })),
          };
        }),
      };
    });
    console.log('===== ' + n + '  body="' + r.body + '" docH=' + r.docH);
    r.sections.forEach((s) => {
      console.log('  SEC ' + s.head + ' | ' + s.secCls);
      s.groups.forEach((g, i) =>
        console.log('    g' + i + ' n=' + g.n + ' disp=' + g.disp + ' tracks=' + g.tracks + ' w=' + g.colW + ' t=' + g.colT + ' | "' + g.cls + '"')
      );
    });
    await c.close();
  }
  await b.close();
})();
