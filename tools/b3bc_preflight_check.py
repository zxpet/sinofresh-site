#!/usr/bin/env python3
"""Batch 3b close-out — the served-byte check, run against the preflight copy.

The local checker reads the working tree. This one reads what the theme
ACTUALLY SERVES, which is the only way to see the two things a static read
cannot: that post 158's flavour group really comes out at eight chips, and
that the fix is a no-op on the pages whose records never carried the word.

It compares the candidate (installed at fcc7bdc) with the live theme over the
same host, and that pairing is what makes it a control rather than a
self-portrait: live serves 2.10.78 and the candidate serves 2.10.79, so a byte
comparison of a group neither change touched is a real before/after. Anything
that shows up there is a regression this batch caused.

  python3 tools/b3bc_preflight_check.py [--json /tmp/x.json]

Two limits this run states rather than papers over, both measured:

  * The flavour group renders on ONE page in the whole catalogue (post 158).
    The other twenty records carry no sf_formula_flavors meta at all, so there
    is no second flavour group to compare against.
  * The species and stage groups render on NO page: no record carries
    sf_formula_species or sf_formula_lifestage. Those two call sites therefore
    cannot be exercised from the served layer at all; they are covered by
    tools/b3bc_flavor_unit.php (which runs the shipped helper) and by the
    static check that all five call sites route through it.

The no-op control is run on the two group types that DO cover the catalogue:
piece weight (all 21 pages) and pack size (10 of them).
"""

import argparse
import base64
import html as htmllib
import json
import re
import sys
import urllib.error
import urllib.request

USER, PASS = 'sfdev', 'VkEws18Kl5V1qp3TpZ6s'
BASE = 'https://dev.zxpet.com'
AUTH = 'Basic ' + base64.b64encode(('%s:%s' % (USER, PASS)).encode()).decode()

# The inventory, from wp-cli on the dev box (wp post list --post_type=sf_formula).
# Named here rather than discovered, so a page that disappears shows up as a 404
# in this run instead of quietly leaving the sweep.
FORMULAS = [
    'joint-support-soft-chews', 'calming-soft-chews', 'digestive-soft-chews',
    'skin-coat-soft-chews', 'joint-support-tablets', 'multivitamin-tablets',
    'calcium-phosphorus-tablets', 'probiotic-powder', 'pumpkin-digestive-powder',
    'bladder-support-powder', 'hairball-remedy-paste', 'nutrition-paste',
    'ear-care-drops', 'urinary-care-drops', 'liquid-joint-support',
    'liquid-skin-coat', 'wild-alaskan-salmon-oil', 'pure-fish-oil-blend',
    'plaque-control-dental-chews', 'oral-care-dental-sticks',
    'natural-cleaning-dental-sticks',
]

RECORD_GROUPS = ['flavor', 'weight', 'pack', 'species', 'stage']

# Pages used for the no-op control. Any page but post 158 will do for weight;
# the pack group only exists on ten, so the control names ones that have it.
NOOP_WEIGHT = ['probiotic-powder', 'calming-soft-chews', 'ear-care-drops']
NOOP_PACK = ['multivitamin-tablets', 'oral-care-dental-sticks']

OVERVIEW_H2 = ['OEM or ODM \u2014 Choose Your Path',
               'Key Facts: MOQ, Lead Time, Payment & Trade Terms',
               'What We Handle \u2014 R&D, Compliance & Export Documentation',
               'Custom Formulation Capability',
               'How We Work \u2014 From Inquiry to Delivery in 5 Steps',
               'Manufacturing Capability',
               'Frequently Asked Questions',
               'Request a Sample']

STAGES = ['Brief & reference match', 'Prototype & sample round',
          'Palatability & stability trials', 'Scale-up & packaging validation']
OLD_STAGES = ['Custom formula development', 'Custom active ingredient levels',
              'Palatability testing', 'Stability testing']

FAILED = []
COUNT = 0
RESULTS = []


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


def fetch(path, preflight=False):
    headers = {'Authorization': AUTH, 'User-Agent': 'sf-b3bc-preflight-check/1'}
    if preflight:
        headers['X-SF-Preflight'] = '1'
    req = urllib.request.Request(BASE + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=35) as rsp:
            return rsp.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as exc:
        return '__HTTP_%d__' % exc.code


def theme_and_version(page):
    """The stylesheet's theme directory and version.

    Read as a pair: the directory name is what says WHICH theme answered (the
    preflight copy is a second directory, not a flag in the HTML), and the two
    together are the cheapest proof that the header really switched copies.
    Matched without quote characters because core prints these links with
    single quotes, and a double-quote pattern reads as "no stylesheet at all"
    rather than as a mistake.
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
    """The chip labels, read off the radio VALUE rather than the visible span:
    a chip with no picture renders its label in __empty-label, and a check that
    only read __text would under-count exactly those."""
    out = []
    for m in re.finditer(r'<label[^>]*class="[^"]*sf-fdetail-config__opt[^"]*"([^>]*)>'
                         r'(.*?)</label>', segment, re.S):
        attrs, inner = m.group(1), m.group(2)
        v = re.search(r'value="([^"]*)"', inner)
        out.append({'label': htmllib.unescape(v.group(1)) if v else '',
                    'marked': 'data-sf-config-custom="1"' in attrs})
    return out


def band_after(page, heading):
    """The markup from one h2 to the next.

    NOT delimited by block comments: a served page carries none (the parser
    strips them), so a `<!-- /wp:group -->` sentinel matches nothing and every
    assertion written against it passes on an empty string. Measured
    here rather than assumed.
    """
    i = page.find('>%s</h2>' % heading)
    if i == -1:
        return ''
    j = page.find('<h2', i)
    return page[i:j if j != -1 else len(page)]


def audit(segment):
    """(option count, Custom labels, owners, whether the owner is the Custom)."""
    opts = option_labels(segment)
    customs = [o for o in opts if o['label'] == 'Custom']
    owners = [o for o in opts if o['marked']]
    return (len(opts), len(customs), len(owners),
            bool(owners) and owners[0]['label'] == 'Custom')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default=None)
    args = ap.parse_args()

    print('== 1. the candidate is the new theme, and live is untouched ==')
    pre_dir, pre_ver = theme_and_version(fetch('/', preflight=True))
    live_dir, live_ver = theme_and_version(fetch('/'))
    ck('the preflight header switches to the copy theme directory',
       pre_dir == 'sinofresh-theme-preflight', pre_dir)
    ck('that copy serves 2.10.79', pre_ver == '2.10.79', pre_ver)
    ck('live still serves sinofresh-theme at 2.10.78 (the pull is held back)',
       (live_dir, live_ver) == ('sinofresh-theme', '2.10.78'),
       (live_dir, live_ver))

    print()
    print('== 2. post 158 — nine chips become eight, one owner for the box ==')
    chews = fetch('/formulas/joint-support-soft-chews/', preflight=True)
    seg = group_segment(chews, 'flavor')
    opts = option_labels(seg)
    labels = [o['label'] for o in opts]
    ck('the flavour group draws eight chips', len(opts) == 8, len(opts))
    ck('exactly one of them says Custom',
       sum(1 for x in labels if x == 'Custom') == 1, labels)
    ck('exactly one of them owns the text box',
       sum(1 for o in opts if o['marked']) == 1, labels)
    ck('and the chip that owns it is the one that says Custom',
       [o['label'] for o in opts if o['marked']] == ['Custom'],
       [o['label'] for o in opts if o['marked']])
    ck('the box is still rendered, once',
       seg.count('data-sf-config-custom-input') == 1,
       seg.count('data-sf-config-custom-input'))
    ck('the record spelling and order survive',
       labels == ['Chicken', 'Beef', 'Lamb', 'Salmon', 'Peanut Butter',
                  'Cheese', 'Mint', 'Custom'], labels)
    ck('the group still prints its meta line',
       'sf-fdetail-config__meta' in seg)

    print()
    print('== 3. post 158 — every record-driven group it carries agrees ==')
    present = []
    for key in RECORD_GROUPS:
        s = group_segment(chews, key)
        if not s:
            continue
        present.append(key)
        count, customs, owners, owner_is_custom = audit(s)
        ck("'%s': %d chips, one Custom, one owner on it"
           % (key, count),
           customs == 1 and owners == 1 and owner_is_custom,
           (count, customs, owners, owner_is_custom))
    ck('the groups this record carries are the three it has meta for',
       present == ['flavor', 'weight', 'pack'], present)
    absent = [k for k in RECORD_GROUPS if k not in present]
    print('        note: %s do not render — the record carries no meta for '
          'them, and no page in the catalogue does' % ', '.join(absent))

    print()
    print('== 4. the no-op control: groups on records that never said Custom ==')
    for key, slugs in (('weight', NOOP_WEIGHT), ('pack', NOOP_PACK)):
        for slug in slugs:
            path = '/formulas/%s/' % slug
            live_seg = group_segment(fetch(path), key)
            pre_seg = group_segment(fetch(path, preflight=True), key)
            ck('%s on %s: the group is byte-identical live vs candidate'
               % (key, slug),
               bool(live_seg) and live_seg == pre_seg,
               ('live %d bytes, candidate %d bytes'
                % (len(live_seg), len(pre_seg))) if live_seg != pre_seg else None)

    print()
    print('== 5. the sweep: every rendered record group, all 21 pages ==')
    bad = []
    per_key = {k: 0 for k in RECORD_GROUPS}
    for slug in FORMULAS:
        page = fetch('/formulas/%s/' % slug, preflight=True)
        if page.startswith('__HTTP_'):
            bad.append((slug, page))
            continue
        for key in RECORD_GROUPS:
            s = group_segment(page, key)
            if not s:
                continue
            per_key[key] += 1
            count, customs, owners, owner_is_custom = audit(s)
            if not (customs == 1 and owners == 1 and owner_is_custom):
                bad.append((slug, key, count, customs, owners, owner_is_custom))
    total = sum(per_key.values())
    ck('all 21 pages serve and all %d record groups draw exactly one Custom, '
       'with the box on it' % total, not bad, bad[:4])
    print('        by group: %s' % ', '.join('%s x%d' % (k, per_key[k])
                                             for k in RECORD_GROUPS))

    print()
    print('== 6. the overview — the four stages in, the old four out ==')
    svc = fetch('/services/', preflight=True)
    band = band_after(svc, 'Custom Formulation Capability')
    ck('the C1 band is served', bool(band))
    for stage in STAGES:
        # The template writes & as &amp;; the served bytes keep it that way.
        ck('served: %s' % stage,
           ('<li>%s</li>' % htmllib.escape(stage, quote=False)) in band,
           band[-200:])
    for old in OLD_STAGES:
        # Asserted in its LIST form, not as a bare substring: the band runs to
        # the next h2 and therefore also holds the two buttons, one of which
        # reads "Palatability testing -> /quality/" and is meant to stay. A
        # substring check would call that kept button a regression.
        ck('not served as a C1 stage any more: %s' % old,
           ('<li>%s</li>' % old) not in band)
    ck('both C1 buttons are served',
       'Custom formulation \u2192' in band and 'Palatability testing \u2192' in band)
    ck('the band keeps the panel checklist, not a new component',
       'sf-checklist sf-checklist--panel' in band)
    heads = [htmllib.unescape(re.sub(r'<[^>]+>', '', t)).strip()
             for t in re.findall(r'<h2[^>]*>(.*?)</h2>', svc, re.S)]
    ck('the overview still carries its eight headings, in order',
       heads == OVERVIEW_H2, heads)

    print()
    print('== 7. the quality band — all six steps still served ==')
    quality = fetch('/quality/', preflight=True)
    ck('six steps are served',
       len(re.findall(r'<article class="sf-qs__step">', quality)) == 6,
       len(re.findall(r'<article class="sf-qs__step">', quality)))
    nums = [re.sub(r'<[^>]+>', '', x).strip()
            for x in re.findall(r'<div class="sf-qs__num">(.*?)</div>', quality, re.S)]
    ck('the numbers run 01..06', nums == ['01', '02', '03', '04', '05', '06'], nums)
    ck('every step still carries its photo and its copy',
       len(re.findall(r'class="sf-qs__media"', quality)) == 6
       and len(re.findall(r'class="sf-qs__num"', quality)) == 6)
    # The layout is a stylesheet rule, so what the served HTML can carry is
    # asserted here and the geometry is measured in the browser
    # (tools/b3b_qs_measure.py).

    if args.json:
        with open(args.json, 'w', encoding='utf-8') as fh:
            json.dump({'checks': COUNT, 'failed': FAILED, 'results': RESULTS},
                      fh, indent=1)
        print('\n(wrote %s)' % args.json)

    print()
    print('%d checks, %d failed' % (COUNT, len(FAILED)))
    for f in FAILED:
        print('  FAILED: %s' % f)
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
