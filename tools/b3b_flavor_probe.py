#!/usr/bin/env python3
"""Probe the duplicated "Custom" chip in the Flavor group of a formula page.

Read-only. It never writes to the site: it opens the page, reads the chips off
the live DOM, and clicks two of them with a real mouse to see what each one is
actually wired to.

The point of the tool is to separate three claims that read the same in a
screenshot:

  * the page renders the word Custom TWICE (a markup fact),
  * neither of them is pre-checked (so a "ticked" one in a screenshot is a
    post-interaction state, not how the page arrives), and
  * only one of them opens H8a's text box -- the other is a dead chip that can
    be picked but leads nowhere.

Usage:
  python3 tools/b3b_flavor_probe.py                     # dev, post 158
  python3 tools/b3b_flavor_probe.py --path /formulas/probiotic-powder/
  python3 tools/b3b_flavor_probe.py --json out.json

Auth: dev.zxpet.com sits behind Basic Auth, and `close --all` throws the
credentials away with the context -- they are set BEFORE every open, or the
site answers 401 and every selector reads 0 while looking exactly like a
wrong-selector bug.
"""
import argparse
import json
import subprocess
import sys
import time

AB = '/Users/meng/.workbuddy/binaries/node/versions/22.22.2-3/bin/agent-browser'
USER = 'sfdev'
PASS = 'VkEws18Kl5V1qp3TpZ6s'

# Reads the Flavor group and every Custom chip on the page. Fields answer the
# four questions the tick asks: what is rendered (labels), what is wired
# (customAttr / boxFor), what arrives checked (checkedCount), and whether the
# extra chip pushed the rail into horizontal scrolling (railScrolls).
PROBE = r"""
(() => {
  const group = document.querySelector('[data-sf-config-group="flavor"]');
  const chips = group ? [...group.querySelectorAll('.sf-fdetail-config__opt')] : [];
  const box   = group ? group.querySelector('.sf-fdetail-config__custom') : null;
  const rail  = group ? group.querySelector('.sf-fdetail-config__options') : null;
  const summ  = document.querySelector('[data-sf-config-summary]');
  const read = c => {
    const inp = c.querySelector('input');
    const t   = c.querySelector('.sf-fdetail-config__text');
    const e   = c.querySelector('.sf-fdetail-config__empty-label');
    return {
      label: (t ? t.textContent : (e ? e.textContent : '')).trim(),
      value: inp ? inp.value : null,
      checked: !!(inp && inp.checked),
      customAttr: c.hasAttribute('data-sf-config-custom'),
      on: c.classList.contains('is-on'),
    };
  };
  return {
    path: location.pathname,
    title: document.title,
    theme: [...document.querySelectorAll('link[rel=stylesheet]')]
             .map(l => l.href).filter(h => h.includes('sinofresh-theme')),
    groupFound: !!group,
    chipCount: chips.length,
    chips: chips.map(read),
    namedCustom: chips.filter(c => read(c).label === 'Custom').length,
    customChipIndexes: chips.map((c, i) => read(c).label === 'Custom' ? i + 1 : 0)
                            .filter(Boolean),
    checkedCount: chips.filter(c => read(c).checked).length,
    onCount: chips.filter(c => read(c).on).length,
    boxExists: !!box,
    boxHidden: box ? box.hasAttribute('hidden') : null,
    boxFor: box ? box.getAttribute('data-sf-config-custom-for') : null,
    boxInputCount: box ? box.querySelectorAll('[data-sf-config-custom-input]').length : 0,
    railScrolls: rail ? rail.scrollWidth > rail.clientWidth + 1 : null,
    railScrollW: rail ? rail.scrollWidth : null,
    railClientW: rail ? rail.clientWidth : null,
    railClass: rail ? rail.className : null,
    summary: summ ? summ.textContent.trim() : null,
    jsOn: !!document.querySelector('.sf-fdetail-config--js'),
  };
})()
"""

# Where is chip N on screen, and what element does the browser say is on top of
# that point? A lazy-loaded image that settles after the scroll is the classic
# way a computed coordinate lands on a different element than the one intended.
AT = r"""
(() => {
  const group = document.querySelector('[data-sf-config-group="flavor"]');
  const chips = group ? [...group.querySelectorAll('.sf-fdetail-config__opt')] : [];
  const c = chips[%d];
  if (!c) return { missing: true };
  // 'instant' on purpose: the site's own scroll-behavior may be smooth, and a
  // coordinate read mid-animation describes a position the chip has left by
  // the time the mouse arrives.
  c.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
  const b = c.getBoundingClientRect();
  const y = Math.round(b.top + b.height / 2);
  // Scan across the chip instead of trusting the centre point. The centre is
  // the right target, but a fixed-position layer (the float stack) can sit over
  // it for part of a scroll animation, and then a click that "missed" says
  // nothing about the chip. The first point that hit-checks to the chip is the
  // point the click uses, and it is still a real click on the chip.
  const probes = [];
  for (let fx = 0.5; fx <= 0.9; fx += 0.2) {
    probes.push(fx);
  }
  for (let fx = 0.3; fx >= 0.1; fx -= 0.2) {
    probes.push(fx);
  }
  let picked = null;
  for (const fx of probes) {
    const px = Math.round(b.left + b.width * fx);
    const hit = document.elementFromPoint(px, y);
    const ok = !!(hit && c.contains(hit));
    if (ok) { picked = { x: px, y: y, fx: fx, hitTag: hit.tagName + '.' + (hit.className || '') }; break; }
  }
  const centre = document.elementFromPoint(Math.round(b.left + b.width / 2), y);
  return { x: picked ? picked.x : null, y: y,
           w: Math.round(b.width), h: Math.round(b.height),
           fx: picked ? picked.fx : null,
           label: (c.querySelector('.sf-fdetail-config__text') || {}).textContent,
           customAttr: c.hasAttribute('data-sf-config-custom'),
           centreHit: centre ? centre.tagName + '.' + (centre.className || '') : null,
           centreIsChip: !!(centre && c.contains(centre)),
           hitTag: picked ? picked.hitTag : (centre ? 'MISSED -> ' + centre.tagName + '.' + centre.className : null),
           hitInChip: !!picked,
           scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior };
})()
"""

# The ticked state, read straight after a click. Separate from PROBE so a
# "nothing changed" result cannot be blamed on the bigger selector set.
CHECKED = r"""
(() => {
  const group = document.querySelector('[data-sf-config-group="flavor"]');
  const chips = group ? [...group.querySelectorAll('.sf-fdetail-config__opt')] : [];
  return {
    checked: chips.map((c, i) => c.querySelector('input').checked ? i + 1 : 0)
                   .filter(Boolean),
    checkedValues: chips.filter(c => c.querySelector('input').checked)
                        .map(c => c.querySelector('input').value),
    active: document.activeElement ? document.activeElement.tagName : null,
    boxHidden: group ? group.querySelector('.sf-fdetail-config__custom').hasAttribute('hidden') : null,
    summary: (document.querySelector('[data-sf-config-summary]') || {}).textContent,
  };
})()
"""

SETTLE = 0.35  # seconds: let any scroll animation finish before aiming


def ab(*args, stdin=None):
    p = subprocess.run([AB] + list(args), input=stdin, capture_output=True,
                       text=True)
    if p.returncode != 0:
        raise SystemExit('agent-browser %s failed: %s' % (' '.join(args),
                                                          p.stderr.strip()))
    return p.stdout


def evaljs(script):
    """Two wrappers come off: the transport envelope, then a JSON string
    literal. Stopping at the first decode is how a caller ends up calling
    .get() on a str, far from the real cause."""
    out = ab('eval', '--json', '--stdin', stdin=script)
    outer = json.loads(out)
    if isinstance(outer, str):
        outer = json.loads(outer)
    if isinstance(outer, dict):
        if outer.get('success') is False:
            raise SystemExit('eval failed: %s' % outer.get('error'))
        data = outer.get('data')
        if isinstance(data, dict) and 'result' in data:
            outer = data['result']
    if isinstance(outer, str):
        try:
            outer = json.loads(outer)
        except ValueError:
            pass
    return outer


def click_chip(n):
    """Real mouse click on chip N (1-based).

    Three steps, because one is not enough: scroll to the chip, WAIT for the
    scroll to settle, then re-read the coordinates and hit-check them, and only
    then move/down/up. A coordinate computed in the same tick as the scroll is
    a guess at where the chip is; on a page whose scroll-behavior is smooth the
    guess is wrong by exactly the distance still to travel, and the click lands
    on whatever is there instead -- with no error to show for it.

    Integer coordinates only: a float silently leaves the pointer where it was
    and the down/up land at (0,0), which is the header.
    """
    first = evaljs(AT % (n - 1))
    if first.get('missing'):
        return None, None
    time.sleep(SETTLE)
    where = evaljs(AT % (n - 1))          # re-read after the scroll settled
    if not where.get('hitInChip'):
        return where, False
    ab('mouse', 'move', str(int(where['x'])), str(int(where['y'])))
    ab('mouse', 'down', 'left')
    ab('mouse', 'up', 'left')
    return where, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='https://dev.zxpet.com')
    ap.add_argument('--path', default='/formulas/joint-support-soft-chews/')
    ap.add_argument('--viewport', default='1440x900',
                    help='WxH; a short viewport parks the fixed float stack '
                         'over the chip row, which is a test artefact rather '
                         'than a property of the page')
    ap.add_argument('--json', default=None)
    args = ap.parse_args()

    url = args.base.rstrip('/') + args.path
    report = {'url': url, 'viewport': args.viewport}

    ab('close', '--all')
    ab('set', 'credentials', USER, PASS)
    ab('open', url)
    # After open, not before: open resets the viewport to its own default.
    vw, vh = args.viewport.lower().split('x')
    ab('set', 'viewport', vw, vh)
    got = evaljs("(() => ({ w: innerWidth, h: innerHeight,"
                 " rs: document.readyState, path: location.pathname }))()")
    report['viewportActual'] = got

    base = evaljs(PROBE)
    report['onload'] = base

    if not base.get('groupFound'):
        print('flavor group not found -- served page guard: %s / %s'
              % (base.get('path'), base.get('title')))
        print(json.dumps(base, ensure_ascii=False, indent=2))
        return 1

    print('== Flavor group on %s ==' % url)
    print('   served page   : %s   ("%s")' % (base['path'], base['title']))
    print('   viewport      : %sx%s   readyState %s'
          % (got['w'], got['h'], got['rs']))
    print('   theme sheet   : %s' % (base['theme'][0].split('/')[-1]
                                     if base['theme'] else '(none)'))
    print()
    print('   chips         : %d   (named Custom: %d, at positions %s)'
          % (base['chipCount'], base['namedCustom'], base['customChipIndexes']))
    print('   checked now   : %d      is-on now: %d'
          % (base['checkedCount'], base['onCount']))
    print('   custom box    : exists=%s hidden=%s for=%s inputs=%d'
          % (base['boxExists'], base['boxHidden'], base['boxFor'],
             base['boxInputCount']))
    print('   options rail  : %s   %sx%s  class=%s'
          % ('SCROLLS' if base['railScrolls'] else 'fits',
             base['railScrollW'], base['railClientW'], base['railClass']))
    print('   js upgraded   : %s' % base['jsOn'])
    print()
    print('   %-4s %-16s %-8s %-8s %s' % ('#', 'label', 'value',
                                           'custom?', 'state'))
    for i, c in enumerate(base['chips'], 1):
        mark = []
        if c['checked']:
            mark.append('CHECKED')
        if c['on']:
            mark.append('is-on')
        print('   %-4d %-16s %-8s %-8s %s'
              % (i, c['label'], c['value'], 'yes' if c['customAttr'] else '-',
                 ' '.join(mark) or '-'))

    # --- the two Custom chips, clicked in turn -----------------------------
    for n in base['customChipIndexes']:
        where, hit = click_chip(n)
        if where is None:
            print('\n   chip %d: gone after open' % n)
            continue
        state = evaljs(CHECKED)
        after = evaljs(PROBE)
        print()
        print('   clicked chip %d  (custom attr: %s; hit %s at %s,%s; scroll-behavior %s)'
              % (n, where['customAttr'], 'on chip' if hit else
                 'MISSED -> %s' % where['hitTag'], where['x'], where['y'],
                 where.get('scrollBehavior')))
        print('     checked now : %s  (values %s)'
              % (state['checked'] or 'none', state['checkedValues'] or '-'))
        print('     text box    : %s' % ('revealed' if state['boxHidden'] is False
                                         else 'still hidden'))
        print('     summary line: %r' % (state['summary'] or ''))
        report['click_%d' % n] = {'where': where, 'state': state, 'after': after}

    if args.json:
        with open(args.json, 'w') as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        print('\n   wrote %s' % args.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
