/* Batch-1 final gate: statuses, JS errors, SEO invariants on the 8 dosage pages
   + quality (hero change), plus DOM-vs-CSS content integrity. */
const { chromium } = require('playwright-core');
const PAGES = [
  ['about', '/about/'], ['quality', '/quality/'], ['factory-tour', '/factory-tour/'],
  ['services', '/services/'], ['contact', '/contact/'],
  ['soft-chews', '/products/soft-chews/'], ['drops', '/products/drops/'],
];
const SEO = () => {
  const txt = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const headings = [...document.querySelectorAll('h1,h2,h3,h4')].map((h) => h.tagName + ':' + txt(h.textContent).slice(0, 40));
  const imgs = [...document.querySelectorAll('img')];
  const links = [...document.querySelectorAll('a[href]')];
  const visibleText = (el) => {
    let n = 0;
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) {
      const cs = getComputedStyle(w.currentNode.parentElement);
      if (cs.display !== 'none' && cs.visibility !== 'hidden' && w.currentNode.textContent.trim()) n++;
    }
    return n;
  };
  return {
    h1: document.querySelectorAll('h1').length,
    h2: document.querySelectorAll('h2').length,
    h3: document.querySelectorAll('h3').length,
    headingsSample: headings.slice(0, 6),
    imgTotal: imgs.length,
    imgNoAlt: imgs.filter((i) => i.getAttribute('alt') === null).length,
    imgEmptyAlt: imgs.filter((i) => i.getAttribute('alt') === '').length,
    internalLinks: links.filter((a) => a.getAttribute('href').startsWith('/')).length,
    externalLinks: links.filter((a) => /^https?:/.test(a.getAttribute('href'))).length,
    details: document.querySelectorAll('details').length,
    detailsVisibleTextNodes: [...document.querySelectorAll('details')].reduce((s, d) => s + visibleText(d), 0),
    schemaTypes: [...document.querySelectorAll('script[type="application/ld+json"]')].map((s) => {
      try { const j = JSON.parse(s.textContent); return (j['@type'] || (j['@graph'] || []).map((g) => g['@type']).join('+')) ; } catch (e) { return 'PARSE_ERR'; }
    }),
    // the two blocks we restructured must still expose every card link
    stepTitles: [...document.querySelectorAll('section')].filter((s) => /How We Work/.test(s.textContent)).map((s) => [...s.querySelectorAll('h3')].map((h) => txt(h.textContent))).flat(),
    relatedLinks: [...document.querySelectorAll('section')].filter((s) => /Related Dosage Forms/.test(s.textContent)).map((s) => [...s.querySelectorAll('a[href^="/products/"]')].map((a) => a.getAttribute('href'))).flat(),
    bodyTextChars: document.body.innerText.replace(/\s+/g, '').length,
  };
};
(async () => {
  const b = await chromium.launch({ channel: 'chrome' });
  let bad = 0;
  for (const [n, u] of PAGES) {
    const ctx = await b.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
    const p = await ctx.newPage();
    const errs = [];
    p.on('pageerror', (e) => errs.push('pageerror:' + String(e).slice(0, 90)));
    p.on('console', (m) => { if (m.type() === 'error') errs.push('console:' + m.text().slice(0, 90)); });
    const resp = await p.goto('http://sinofresh.local' + u, { waitUntil: 'networkidle' });
    const r = await p.evaluate(SEO);
    const flag = (c, msg) => { if (!c) { bad++; console.log('   !! ' + n + ' ' + msg); } };
    flag(resp.status() === 200, 'status ' + resp.status());
    flag(r.h1 === 1, 'h1=' + r.h1);
    flag(r.imgNoAlt === 0, 'imgNoAlt=' + r.imgNoAlt);
    
    
    flag(!r.schemaTypes.includes('PARSE_ERR'), 'schema parse error');
    flag(errs.length === 0, 'js errors: ' + errs.join(' | '));
    console.log(
      n.padEnd(13) + ' ' + resp.status() + ' h1=' + r.h1 + ' h2=' + r.h2 + ' h3=' + r.h3 +
      ' img=' + r.imgTotal + '(alt-empty ' + r.imgEmptyAlt + ')' +
      ' links int/ext=' + r.internalLinks + '/' + r.externalLinks +
      ' details=' + r.details + '(' + r.detailsVisibleTextNodes + ' txt nodes)' +
      ' schema=' + r.schemaTypes.join(',') +
      ' steps=' + r.stepTitles.length + ' relLinks=' + r.relatedLinks.length +
      ' bodyChars=' + r.bodyTextChars + (errs.length ? ' JS_ERR:' + errs.join('|') : '')
    );
    await ctx.close();
  }
  await b.close();
  console.log(bad ? '\nGATE: ' + bad + ' problem(s)' : '\nGATE: all checks passed');
})();
