/* Blog list mobile (375px) scan: chips + cards + rule-effectiveness */
const path = require('path');
const { chromium } = require('playwright-core');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
  await page.goto('http://sinofresh.local/blog/', { waitUntil: 'networkidle' });
  // header static + hide cookie banner (convention)
  await page.addStyleTag({ content: 'header{position:static !important}.sf-cookie-banner,.sf-cookie-consent{display:none !important}' });
  await page.evaluate(() => document.fonts.ready);

  const report = await page.evaluate(() => {
    const out = {};
    const cs = (el, props) => { const s = getComputedStyle(el); const o = {}; props.forEach(p => o[p] = s.getPropertyValue(p)); return o; };
    const rect = el => { const r = el.getBoundingClientRect(); return { x: +r.x.toFixed(1), y: +r.y.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1) }; };

    out.body = { className: document.body.className, scrollW: document.documentElement.scrollWidth, innerW: window.innerWidth, docH: document.documentElement.scrollHeight };
    out.ovf = document.documentElement.scrollWidth > window.innerWidth;

    // 1. chips
    const chipsWrap = document.querySelector('.wp-block-buttons');
    if (chipsWrap) {
      out.chips = { wrapClass: chipsWrap.className, wrapRect: rect(chipsWrap), wrapStyle: cs(chipsWrap, ['display', 'flex-wrap', 'overflow-x', 'gap', 'justify-content']) };
      const links = [...chipsWrap.querySelectorAll('a')];
      out.chips.count = links.length;
      const tops = new Set(links.map(a => Math.round(a.getBoundingClientRect().top)));
      out.chips.rows = tops.size;
      out.chips.firstRect = rect(links[0]);
      out.chips.firstStyle = cs(links[0], ['padding', 'border-radius', 'font-size', 'white-space']);
      out.chips.linkList = links.map(a => ({ t: a.textContent.trim(), top: Math.round(a.getBoundingClientRect().top), w: +a.getBoundingClientRect().width.toFixed(0) }));
    } else out.chips = 'NO .wp-block-buttons';

    // 2. cards
    const posts = [...document.querySelectorAll('.wp-block-post')];
    out.cardCount = posts.length;
    if (posts.length) {
      const c0 = posts[0];
      const group = c0.querySelector('.wp-block-group');
      out.card0 = { postRect: rect(c0), groupClass: group ? group.className : null };
      if (group) out.card0.groupStyle = cs(group, ['padding', 'border-radius', 'background-color', 'display', 'flex-direction']);
      const img = c0.querySelector('img');
      out.card0.img = img ? { rect: rect(img), natural: img.naturalWidth + 'x' + img.naturalHeight, src: (img.currentSrc || img.src).split('/').pop() } : (c0.querySelector('figure') ? { figureRect: rect(c0.querySelector('figure')), noImg: true } : 'none');
      const cat = c0.querySelector('.taxonomy-category');
      out.card0.category = cat ? { rect: rect(cat), style: cs(cat, ['font-size', 'color']) } : null;
      const title = c0.querySelector('.wp-block-post-title');
      out.card0.title = title ? { rect: rect(title), style: cs(title, ['font-size', 'line-height', 'margin']) } : null;
      const ex = c0.querySelector('.wp-block-post-excerpt');
      out.card0.excerpt = ex ? { rect: rect(ex), style: cs(ex, ['display', 'font-size']) } : null;
      const rm = [...c0.querySelectorAll('a')].map(a => a.textContent.trim());
      out.card0.links = rm;
      // per-card heights
      out.cardHeights = posts.map((p, i) => ({ i, h: +p.getBoundingClientRect().height.toFixed(0), top: Math.round(p.getBoundingClientRect().top) }));
      out.distinctCardTops = new Set(posts.map(p => Math.round(p.getBoundingClientRect().top))).size;
    }

    // template-level: post-template class
    const pt = document.querySelector('.wp-block-post-template');
    out.postTemplate = pt ? { className: pt.className, style: cs(pt, ['display', 'grid-template-columns', 'gap']) } : null;
    return out;
  });

  console.log(JSON.stringify(report, null, 2));

  // screenshots
  const dir = path.join(__dirname, '..', 'screenshots', 'bloglist-scan');
  require('fs').mkdirSync(dir, { recursive: true });
  await page.screenshot({ path: path.join(dir, 'mob-375-firstscreen.png') });
  // scroll to cards, shot card detail
  await page.evaluate(() => { const c = document.querySelector('.wp-block-post'); if (c) c.scrollIntoView(); window.scrollBy(0, -80); });
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(dir, 'mob-375-cards.png') });

  // matched-rules probe for chip wrap + card padding via CDP
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('DOM.enable'); await cdp.send('CSS.enable');
  const { root } = await cdp.send('DOM.getDocument', { depth: -1 });
  const probe = async (sel, prop) => {
    const { nodeId } = await cdp.send('DOM.querySelector', { nodeId: root.nodeId, selector: sel });
    if (!nodeId) return sel + ' -> not found';
    const { matchedCSSRules } = await cdp.send('CSS.getMatchedStylesForNode', { nodeId });
    const hits = [];
    const walk = rules => rules.forEach(r => {
      if (r.rule.origin === 'regular' && r.rule.style.cssText.includes(prop)) {
        const sels = r.rule.selectorList.text.replace(/\s+/g, ' ');
        if ((sels.includes('blog') || sels.includes('buttons') || sels.includes('post')) && !sels.includes('sf-hero')) hits.push(sels.slice(0, 140) + ' { ' + r.rule.style.cssText.replace(/\s+/g, ' ').slice(0, 160) + ' }');
      }
      if (r.matchedCSSRules) walk(r.matchedCSSRules);
    });
    walk(matchedCSSRules || []);
    return hits.join('\n') || '(no user rule for ' + prop + ')';
  };
  console.log('\n=== matched rules: chips wrap ===\n' + await probe('.wp-block-buttons', 'flex-wrap'));
  console.log('\n=== matched rules: card group padding ===\n' + await probe('.wp-block-post .wp-block-group.has-card-white-background-color', 'padding-top'));
  console.log('\n=== matched rules: excerpt display ===\n' + await probe('.wp-block-post .wp-block-post-excerpt', 'display'));

  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
