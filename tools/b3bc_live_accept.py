#!/usr/bin/env python3
"""Batch 3b — the live acceptance, run AFTER the pull.

tools/b3bc_preflight_check.py read the candidate copy while the pull was held
back. This one reads what dev serves with no header at all, and it exists
because the two are not the same question: the copy is proven against live, but
only the pull can put those bytes on the directory the site answers from.

Three things the tick asked for, each answered from the wire:

  1. the flavour group on post 158, in EN and in ZH: eight chips, one Custom,
     and clicking the Custom chip selects it and opens the text box;
  2. /quality/: 861px tall at 1440 with three steps to a row, and the numbers
     01..06 still on the six steps;
  3. live serves 2.10.81, and no page in the catalogue -- footer included --
     still carries an old theme token.

The no-header run is the point, so there is exactly one place where a request
header is set and it is the Authorization one. `close --all` throws the
credentials away with the browser context, which is how every selector on the
site comes back empty against a 401 page that looks like a broken selector;
each session therefore sets them before it opens anything, and every capture
asserts which stylesheet answered before it shoots.

Run with the interpreter that has PIL:
  /Users/meng/.workbuddy/binaries/python/envs/default/bin/python \
      tools/b3bc_live_accept.py
"""

import argparse
import base64
import html as htmllib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

from PIL import Image

USER, PASS = 'sfdev', 'VkEws18Kl5V1qp3TpZ6s'
BASE = 'https://dev.zxpet.com'
AUTH = 'Basic ' + base64.b64encode(('%s:%s' % (USER, PASS)).encode()).decode()
EXPECT_VER = '2.10.81'

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs', 'batch3b-live-accept-shots')
TMP = '/tmp/b3bc-live-accept'

# The catalogue sweep, so a page that disappears shows up as a 404 rather than
# as one fewer page in a count.
PATHS_FILE = os.path.join(ROOT, 'tools', 'b2d_s3_paths.txt')

CHEWS = '/formulas/joint-support-soft-chews/'
CHEWS_ZH = '/zh/formulas/joint-support-soft-chews/'
QUALITY = '/quality/'

FLAVOR = '[data-sf-config-group="flavor"]'
QS = '.sf-qs'
STEP = '.sf-qs__step'

FLAVOR_LABELS = ['Chicken', 'Beef', 'Lamb', 'Salmon', 'Peanut Butter',
                 'Cheese', 'Mint', 'Custom']

# A stylesheet token from this theme's own version line: 2.10.x. Anything older
# than the one being deployed is a page that cached a link to last week's CSS.
THEME_TOKEN = re.compile(r'^2\.10\.\d+$')

FAILED = []
COUNT = 0
RESULTS = []
FRAMES = []


def ck(label, cond, got=None):
    global COUNT
    COUNT += 1
    RESULTS.append({'label': label, 'ok': bool(cond)})
    if cond:
        print('  PASS  %s' % label)
    else:
        FAILED.append(label)
        print('  FAIL  %s' % label)
        if got is not None:
            print('        got: %r' % (got,))


def fetch(path):
    """No request header beyond the credential — this is the live layer."""
    req = urllib.request.Request(
        BASE + path,
        headers={'Authorization': AUTH,
                 'User-Agent': 'sf-b3bc-live-accept/1'})
    try:
        with urllib.request.urlopen(req, timeout=35) as rsp:
            return rsp.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as exc:
        return '__HTTP_%d__' % exc.code


def theme_and_version(page):
    """(theme directory, version) read out of the served stylesheet link.

    Matched without quote characters on purpose: core prints these links with
    single quotes, so a double-quoted pattern reports "no stylesheet at all",
    which is the same answer a failed fetch gives.
    """
    m = re.search(r'themes/(sinofresh-theme[a-z-]*)/style\.css\?ver=([0-9.]+)', page)
    return (m.group(1), m.group(2)) if m else ('(none)', '(none)')


def group_segment(page, key):
    """One configurator group's markup, up to the next group."""
    start = page.find('data-sf-config-group="%s"' % key)
    if start == -1:
        return ''
    nxt = re.search(r'data-sf-config-group="[a-z]+"', page[start + 10:])
    end = start + 10 + nxt.start() if nxt else len(page)
    return page[start:end]


def option_labels(segment):
    """Chip labels off the radio VALUE, not the visible span: a chip with no
    artwork renders its label in __empty-label and a check that only read
    __text would under-count exactly those."""
    out = []
    for m in re.finditer(r'<label[^>]*class="[^"]*sf-fdetail-config__opt[^"]*"([^>]*)>'
                         r'(.*?)</label>', segment, re.S):
        attrs, inner = m.group(1), m.group(2)
        v = re.search(r'value="([^"]*)"', inner)
        out.append({'label': htmllib.unescape(v.group(1)) if v else '',
                    'marked': 'data-sf-config-custom="1"' in attrs})
    return out


# ----------------------------------------------------------------- html layer

def check_flavor(path, tag):
    page = fetch(path)
    if page.startswith('__HTTP_'):
        ck('%s: %s answers 200' % (tag, path), False, page)
        return None
    ck('%s: %s answers 200' % (tag, path), True)
    d, v = theme_and_version(page)
    ck('%s: served from %s at %s' % (tag, d, EXPECT_VER),
       (d, v) == ('sinofresh-theme', EXPECT_VER), (d, v))
    seg = group_segment(page, 'flavor')
    opts = option_labels(seg)
    labels = [o['label'] for o in opts]
    ck('%s: the Flavor group draws eight chips' % tag, len(opts) == 8, len(opts))
    ck('%s: exactly one of them says Custom' % tag,
       sum(1 for x in labels if x == 'Custom') == 1, labels)
    ck('%s: exactly one of them owns the text box' % tag,
       sum(1 for o in opts if o['marked']) == 1, labels)
    ck('%s: and the one that owns it is the one that says Custom' % tag,
       [o['label'] for o in opts if o['marked']] == ['Custom'],
       [o['label'] for o in opts if o['marked']])
    ck('%s: the box is rendered once, and the group keeps its meta line' % tag,
       seg.count('data-sf-config-custom-input') == 1
       and 'sf-fdetail-config__meta' in seg,
       seg.count('data-sf-config-custom-input'))
    ck('%s: the record order survives' % tag, labels == FLAVOR_LABELS, labels)
    return seg


def check_quality_html():
    page = fetch(QUALITY)
    if page.startswith('__HTTP_'):
        ck('the quality page answers 200', False, page)
        return
    ck('the quality page answers 200', True)
    d, v = theme_and_version(page)
    ck('the quality page is served from the pulled theme at %s' % EXPECT_VER,
       (d, v) == ('sinofresh-theme', EXPECT_VER), (d, v))
    ck('six steps are served',
       len(re.findall(r'<article class="sf-qs__step">', page)) == 6,
       len(re.findall(r'<article class="sf-qs__step">', page)))
    nums = [re.sub(r'<[^>]+>', '', x).strip()
            for x in re.findall(r'<div class="sf-qs__num">(.*?)</div>', page, re.S)]
    ck('the numbers run 01..06', nums == ['01', '02', '03', '04', '05', '06'], nums)
    ck('every step still carries its photo and its number',
       len(re.findall(r'class="sf-qs__media"', page)) == 6
       and len(re.findall(r'class="sf-qs__num"', page)) == 6)


def check_sweep():
    paths = [l.strip() for l in open(PATHS_FILE, encoding='utf-8')
             if l.strip()]
    tokens = {}
    stale = []
    all_vers = {}
    dead = []
    for path in paths:
        page = fetch(path)
        if page.startswith('__HTTP_'):
            dead.append((path, page))
            continue
        d, v = theme_and_version(page)
        tokens.setdefault((d, v), []).append(path)
        for t in re.findall(r'\?ver=([0-9A-Za-z._-]+)', page):
            all_vers.setdefault(t, set()).add(path)
        if THEME_TOKEN.match(v or '') and v != EXPECT_VER:
            stale.append((path, v))
    ck('all %d catalogue pages serve' % len(paths), not dead, dead[:4])
    ck('every one of them links the theme at %s' % EXPECT_VER,
       list(tokens) == [('sinofresh-theme', EXPECT_VER)],
       {('%s@%s' % k): len(v) for k, v in tokens.items()})
    ck('no page still carries a stale theme token', not stale, stale[:6])
    print('        ?ver= values seen across the sweep: %s'
          % ', '.join('%s x%d' % (k, len(v)) for k, v in
                      sorted(all_vers.items(), key=lambda kv: -len(kv[1]))[:8]))
    return all_vers


def check_footer(home):
    """The footer is the other place a cached asset link would show up."""
    m = re.search(r'<footer.*?</footer>', home, re.S)
    if not m:
        ck('the homepage still has a footer to read', False)
        return
    seg = m.group(0)
    vers = sorted(set(re.findall(r'\?ver=([0-9A-Za-z._-]+)', seg)))
    bad = [v for v in vers if THEME_TOKEN.match(v) and v != EXPECT_VER]
    ck('the footer carries no stale theme token', not bad, bad)
    print('        footer asset tokens: %s' % (vers or 'none'))


# ------------------------------------------------------------- browser layer

def ab(*a, timeout=300):
    return subprocess.run(['agent-browser', *a], capture_output=True,
                          text=True, timeout=timeout).stdout.strip()


def ev(js):
    """agent-browser prints the result as a JSON string literal, so a dict
    arrives double-encoded: decode twice, or the first .get() raises on a str
    and the traceback points nowhere near the cause."""
    raw = ab('eval', js)
    if not raw:
        raise RuntimeError('eval returned nothing')
    try:
        once = json.loads(raw)
    except Exception:
        return raw
    if isinstance(once, str):
        try:
            return json.loads(once)
        except Exception:
            return once
    return once


def session():
    ab('close', '--all')
    time.sleep(1.0)
    ab('set', 'credentials', USER, PASS)
    time.sleep(0.4)
    ab('open', BASE + '/')
    time.sleep(2.2)


def wait_ready(tries=25):
    for _ in range(tries):
        st = ev("JSON.stringify({rs: document.readyState, t: document.title,"
                " n: document.querySelectorAll('link[rel=stylesheet]').length})")
        if (isinstance(st, dict) and st.get('rs') == 'complete'
                and st.get('n', 0) > 0 and st.get('t')):
            return True
        time.sleep(0.8)
    return False


def prescroll(step=700, pause=0.3, settle=1.2):
    info = ev('JSON.stringify({h: document.documentElement.scrollHeight})') or {}
    total = info.get('h') or 0
    y = 0
    while y < total:
        ab('eval', 'window.scrollTo(0, %d)' % y)
        time.sleep(pause)
        y += step
    ab('eval', 'window.scrollTo(0, 0)')
    time.sleep(settle)


def at(path, w, h=900):
    ab('open', BASE + path)
    time.sleep(2.2)
    wait_ready()
    for _ in range(4):
        ab('set', 'viewport', str(w), str(h))
        time.sleep(0.8)
        got = ev('JSON.stringify({w: innerWidth, p: location.pathname})')
        if isinstance(got, dict) and got.get('w') == w:
            prescroll()
            hid = ev("(() => { let n = 0;"
                     " document.querySelectorAll('.sf-cookie-banner')"
                     ".forEach(e => { e.style.display = 'none'; n++; }); return n; })()")
            if hid:
                print('        (hid %s cookie banner(s))' % hid)
            return got
        time.sleep(0.5)
    raise SystemExit('viewport %d did not take on %s' % (w, path))


def whose():
    """Which copy answered. A 401 page has no theme stylesheet at all, so this
    doubles as the guard against asserting on a page that is not the site."""
    return ev("""(() => {
      const l = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(x => x.href);
      const theme = l.find(h => h.includes('sinofresh-theme')) || '';
      return { theme: theme, path: location.pathname,
               v: (theme.match(/ver=([0-9.]+)/) || [])[1] || null,
               title: document.title }; })()""")


def served_guard(path):
    got = whose()
    if ((got or {}).get('v') != EXPECT_VER
            or (got or {}).get('path') != path):
        raise SystemExit('not on live %s: %r' % (path, got))
    return got


def rect(sel):
    return ev("""(() => {
      const e = document.querySelector(%s);
      if (!e) return null;
      const r = e.getBoundingClientRect();
      return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height,
               docW: document.documentElement.scrollWidth,
               docH: document.documentElement.scrollHeight }; })()""" % json.dumps(sel))


def qs_rows():
    """The steps grouped into rows by their own top edge.

    Read as rows rather than as a count of columns, because "three to a row" is
    a geometry the stylesheet can fail in ways a class name cannot describe:
    the grid could be three tracks with the steps stacked inside one of them.
    Rounded to the pixel on purpose -- sub-pixel tops differ by fractions and
    would split one row into three.
    """
    return ev("""(() => {
      const st = Array.from(document.querySelectorAll(%s));
      const rows = [];
      st.forEach(s => {
        const t = Math.round(s.getBoundingClientRect().top + scrollY);
        const row = rows.find(r => Math.abs(r.top - t) <= 4);
        if (row) { row.n++; } else { rows.push({ top: t, n: 1 }); }
      });
      const q = document.querySelector(%s);
      const img = document.querySelector('.sf-qs__media img, .sf-qs__media');
      const num = document.querySelector('.sf-qs__num');
      const ir = img ? img.getBoundingClientRect() : null;
      const cs = num ? getComputedStyle(num) : null;
      return { steps: st.length, rows: rows.map(r => r.n),
               gridHeight: q ? Math.round(q.getBoundingClientRect().height) : null,
               gridWidth: q ? Math.round(q.getBoundingClientRect().width) : null,
               colTemplate: q ? getComputedStyle(q).gridTemplateColumns : null,
               imgRatio: ir ? +(ir.width / ir.height).toFixed(3) : null,
               numSize: cs ? cs.fontSize : null,
               numColor: cs ? cs.color : null,
               docW: document.documentElement.scrollWidth }; })()"""
             % (json.dumps(STEP), json.dumps(QS)))


def click_marked_chip():
    """Click the flavour chip that owns the text box, with a real mouse.

    Integer coordinates on purpose: a float silently leaves the pointer where
    it was and the down/up land at (0,0), which reads as "the chip does not
    respond". `instant` scrolling on purpose too -- the site sets a smooth
    scroll-behavior, so a coordinate read mid-animation describes a position
    the chip has already left by the time the mouse arrives.
    """
    where = ev("""(() => {
      const g = document.querySelector('[data-sf-config-group="flavor"]');
      if (!g) return { missing: true };
      const c = g.querySelector('.sf-fdetail-config__opt[data-sf-config-custom="1"]');
      if (!c) return { no_marked_chip: true };
      c.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
      const b = c.getBoundingClientRect();
      const x = Math.round(b.left + b.width / 2), y = Math.round(b.top + b.height / 2);
      const hit = document.elementFromPoint(x, y);
      return { x: x, y: y, hitOnChip: !!(hit && c.contains(hit)),
               hitTag: hit ? hit.tagName + '.' + (hit.className || '') : null }; })()""")
    if not isinstance(where, dict) or not where.get('hitOnChip'):
        return where, None
    ab('mouse', 'move', str(int(where['x'])), str(int(where['y'])))
    ab('mouse', 'down', 'left')
    ab('mouse', 'up', 'left')
    time.sleep(0.7)
    after = ev("""(() => {
      const g = document.querySelector('[data-sf-config-group="flavor"]');
      const box = g.querySelector('.sf-fdetail-config__custom');
      const inp = g.querySelector('input[type=text]');
      const on = Array.from(g.querySelectorAll('.sf-fdetail-config__opt'))
        .map((c, i) => c.classList.contains('is-on') ? i + 1 : 0).filter(Boolean);
      const br = box ? box.getBoundingClientRect() : null;
      return { boxHidden: box ? box.hasAttribute('hidden') : null,
               boxVisible: !!(br && br.height > 0),
               boxDisplay: box ? getComputedStyle(box).display : null,
               focused: !!(inp && document.activeElement === inp),
               checkedRadio: (g.querySelector('input[type=radio]:checked') || {}).value || null,
               on: on }; })()""")
    return where, after


def _save(name, crop):
    cols = crop.getcolors(maxcolors=1 << 20) or []
    n = len(cols)
    ok = n >= 9
    crop.save(os.path.join(OUT, name + '.png'))
    FRAMES.append((name, crop.width, crop.height, n, ok))
    print('  %s %-36s %4dx%-5d colours=%-6d' % ('ok  ' if ok else 'FLAT',
                                                name, crop.width, crop.height, n))
    return ok


def fullshot(name):
    full = os.path.join(TMP, name + '-full.png')
    ab('screenshot', '--full', full)
    if not os.path.exists(full):
        print('  FAIL %-36s the capture wrote nothing' % name)
        FRAMES.append((name, 0, 0, 0, False))
        return None
    return Image.open(full)


def shoot_range(name, y0, y1):
    img = fullshot(name)
    if img is None:
        return False
    doc = ev('JSON.stringify({w: document.documentElement.scrollWidth,'
             ' h: document.documentElement.scrollHeight})') or {}
    sy = img.height / float(doc.get('h') or 1)
    top = max(0, min(img.height, int(y0 * sy)))
    bot = max(top, min(img.height, int(y1 * sy)))
    return _save(name, img.crop((0, top, img.width, bot)))


def shoot_sel(name, sel, pad=14, pad_top=14, extra=0):
    r = rect(sel)
    if not r:
        print('  FAIL %-36s no element %s' % (name, sel))
        FRAMES.append((name, 0, 0, 0, False))
        return False
    return shoot_range(name, r['y'] - pad_top, r['y'] + r['h'] + pad + extra)


def browser_pass():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    session()
    served_guard('/')

    print()
    print('== 4. /quality/ at 1440: one row of three, and 861px tall ==')
    at(QUALITY, 1440)
    served_guard(QUALITY)
    g = qs_rows() or {}
    print('        %s' % json.dumps(g, ensure_ascii=False))
    ck('the three-up grid measures 861px at 1440', g.get('gridHeight') == 861,
       g.get('gridHeight'))
    ck('the grid is three tracks wide', (g.get('colTemplate') or '').count('px') == 3
       or len(re.split(r'\s+', (g.get('colTemplate') or '').strip())) == 3,
       g.get('colTemplate'))
    ck('six steps come off the page', g.get('steps') == 6, g.get('steps'))
    ck('and they sit three to a row', g.get('rows') == [3, 3], g.get('rows'))
    ck('the photos are still 4:3', g.get('imgRatio') in (1.333, 1.334),
       g.get('imgRatio'))
    ck('the number is still 64px brand green',
       g.get('numSize') == '64px' and g.get('numColor') == 'rgb(90, 183, 53)',
       (g.get('numSize'), g.get('numColor')))
    shoot_sel('la-quality-3up-1440', QS, 18, 18)

    print()
    print('== 5. the same page has not pushed 1024 into a horizontal scroll ==')
    at(QUALITY, 1024)
    served_guard(QUALITY)
    g2 = qs_rows() or {}
    ck('no horizontal overflow at 1024',
       (g2.get('docW') or 0) <= 1024, g2.get('docW'))
    ck('still two rows at 1024', g2.get('rows') == [3, 3], g2.get('rows'))
    shoot_sel('la-quality-3up-1024', QS, 18, 18)

    print()
    print('== 6. post 158 EN: the Custom chip selects itself and opens the box ==')
    at(CHEWS, 1440)
    served_guard(CHEWS)
    shoot_sel('la-flavor-en-1440', FLAVOR, 14, 14)
    where, after = click_marked_chip()
    print('        clicked at %s,%s -> %s' % ((where or {}).get('x'),
                                              (where or {}).get('y'), after))
    ck('the mouse landed on the Custom chip', bool((where or {}).get('hitOnChip')),
       where)
    ck('clicking it checks its radio', (after or {}).get('checkedRadio') == 'Custom',
       (after or {}).get('checkedRadio'))
    ck('...and the chip reads as selected',
       (after or {}).get('on') == [8], (after or {}).get('on'))
    ck('...and the text box is open, not hidden',
       (after or {}).get('boxHidden') is False
       and (after or {}).get('boxVisible') is True, after)
    shoot_sel('la-flavor-en-custom-open-1440', FLAVOR, 14, 14, 90)

    print()
    print('== 7. post 158 ZH: the same eight chips behave the same way ==')
    at(CHEWS_ZH, 1440)
    served_guard(CHEWS_ZH)
    shoot_sel('la-flavor-zh-1440', FLAVOR, 14, 14)
    where_z, after_z = click_marked_chip()
    print('        clicked at %s,%s -> %s' % ((where_z or {}).get('x'),
                                               (where_z or {}).get('y'), after_z))
    ck('the mouse landed on the Custom chip (ZH)',
       bool((where_z or {}).get('hitOnChip')), where_z)
    ck('clicking it checks its radio (ZH)',
       (after_z or {}).get('checkedRadio') == 'Custom',
       (after_z or {}).get('checkedRadio'))
    ck('...and the chip reads as selected (ZH)',
       (after_z or {}).get('on') == [8], (after_z or {}).get('on'))
    ck('...and the text box is open, not hidden (ZH)',
       (after_z or {}).get('boxHidden') is False
       and (after_z or {}).get('boxVisible') is True, after_z)
    shoot_sel('la-flavor-zh-custom-open-1440', FLAVOR, 14, 14, 90)

    print()
    flat = [r for r in FRAMES if not r[4]]
    print('%d frames, %d flat' % (len(FRAMES), len(flat)))
    for r in flat:
        print('   FLAT: %s' % r[0])
    return flat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default=None)
    args = ap.parse_args()

    print('== 1. the flavour group, EN and ZH, off the live bytes ==')
    en = check_flavor(CHEWS, 'EN')
    zh = check_flavor(CHEWS_ZH, 'ZH')
    if en is not None and zh is not None:
        ck('the two locales render the same group markup',
           en == zh, 'EN %d bytes vs ZH %d bytes' % (len(en), len(zh)))

    print()
    print('== 2. the quality band ==')
    check_quality_html()

    print()
    print('== 3. the version, over the whole catalogue ==')
    home = fetch('/')
    d, v = theme_and_version(home)
    ck('live serves %s from %s' % (EXPECT_VER, d),
       (d, v) == ('sinofresh-theme', EXPECT_VER), (d, v))
    all_vers = check_sweep()
    check_footer(home)
    ck('no stale theme token anywhere on the site',
       not [t for t in all_vers if THEME_TOKEN.match(t) and t != EXPECT_VER],
       [t for t in all_vers if THEME_TOKEN.match(t) and t != EXPECT_VER])

    print()
    browser_pass()

    if args.json:
        with open(args.json, 'w', encoding='utf-8') as fh:
            json.dump({'checks': COUNT, 'failed': FAILED, 'results': RESULTS,
                       'frames': [{'name': f[0], 'w': f[1], 'h': f[2],
                                   'colours': f[3], 'flat': not f[4]}
                                  for f in FRAMES]}, fh, indent=1)
        print('\n(wrote %s)' % args.json)

    print()
    print('%d checks, %d failed' % (COUNT, len(FAILED)))
    for f in FAILED:
        print('  FAILED: %s' % f)
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
