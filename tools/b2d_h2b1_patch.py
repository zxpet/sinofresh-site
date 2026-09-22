#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H2b1 — delete the configurator block and move the `.sf-explore` band.

Two things make this script worth existing instead of a handful of `sed`
calls, and both are scars from earlier batches in this project:

  * An edit's success message is not evidence the bytes changed. Twice already
    (H1, and the H2b scanner's `depth_delta` fix) an `Edit` reported success
    while the file on disk was untouched. So every page is re-read from disk
    inside the same process and checked against hard assertions before the
    script is allowed to report success.

  * The delete region must be located by *structure*, not by line number. The
    plan carries line numbers (55-271, 55-220, …) and they are used here only
    as a cross-check: the region is actually found by balancing
    `<!-- wp:group -->` … `<!-- /wp:group -->` from the
    `<!-- Block 4: Configurator -->` marker. A page whose numbers drifted is
    then a loud failure instead of a silently wrong slice.

The `.sf-explore` band is not rewritten, it is *moved*: the five band lines are
copied byte-for-byte out of the block being deleted, so the band's sha256 stays
`835c81666e2a` on all eight pages before and after. That hash is the hard
assertion that the move was a move and not a re-typing.

usage:
    python3 tools/b2d_h2b1_patch.py --check      # read-only, prints the report
    python3 tools/b2d_h2b1_patch.py --apply      # writes the eight pages
"""

import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
THEME = os.path.join(ROOT, 'sinofresh-theme')
SCAN = os.path.join(ROOT, '_backup', 'b2d-h2b-scan.json')

BLOCK_MARK = '<!-- Block 4: Configurator -->'
NEXT_MARK = '<!-- Block 9: How We Work -->'
GROUP_OPEN = '<!-- wp:group '
GROUP_CLOSE = '<!-- /wp:group -->'

# The eight pages and the block end line the scan recorded. The line numbers are
# a cross-check on the structural search, never the search itself.
PAGES = [
    ('page-soft-chews.html', 271),
    ('page-tablets.html', 207),
    ('page-dental-chews.html', 220),
    ('page-powders.html', 203),
    ('page-fish-oil.html', 203),
    ('page-pastes.html', 190),
    ('page-liquids.html', 190),
    ('page-drops.html', 189),
]

# The replacement block, twelve lines, identical on all eight pages. The band
# lines (7-11 below) are asserted to equal the bytes lifted out of the deleted
# region, so `[sf_explore_chips]` and the `&rarr;` entity survive verbatim.
NEW_BLOCK = [
    '<!-- Block 4: Explore more dosage forms (moved out of the configurator, batch H2b1) -->',
    '<!-- wp:group {"tagName":"section","className":"sf-explore-band","layout":{"type":"constrained"},'
    '"style":{"spacing":{"padding":{"top":"0","bottom":"var:preset|spacing|80"}}}} -->',
    '<section class="wp-block-group sf-explore-band" '
    'style="padding-top:0;padding-bottom:var(--wp--preset--spacing--80)">',
    '<!-- wp:html -->',
    '    <div class="sf-explore">',
    '      <h3 class="sf-explore__title">Explore more dosage forms</h3>',
    '      [sf_explore_chips]',
    '      <a class="sf-explore__btn" href="/products/">Browse All Products &rarr;</a>',
    '    </div>',
    '<!-- /wp:html -->',
    '</section>',
    '<!-- /wp:group -->',
]
BAND_FIRST, BAND_LAST = 4, 8          # index range of the band inside NEW_BLOCK

BAND_SHA12 = '835c81666e2a'
BAND_OPEN = '    <div class="sf-explore">'
BAND_CLOSE = '    </div>'

# The band section's opening tag. `class="sf-explore-band"` alone matches
# NOTHING: the renderer prefixes the group's own class, so the attribute reads
# `class="wp-block-group sf-explore-band"`. Checking the short form silently
# returned 0 and read as "the band vanished" — the word `sf-explore-band` also
# appears in the wp:group JSON, so the needle has to be the tag itself.
BAND_SECTION = '<section class="wp-block-group sf-explore-band" '

# The hero CTA, on the eight dosage pages and on the detail-page template.
CTA_OLD_DOSE = ('<a class="wp-block-button__link has-card-white-color has-text-color '
                'wp-element-button" href="#configurator">Build Custom Formula</a>')
CTA_NEW_DOSE = ('<a class="wp-block-button__link has-card-white-color has-text-color '
                'wp-element-button sf-quote-cta" href="/contact/#quote">Build Custom Formula</a>')
CTA_OLD_DETAIL = ('<a class="sf-formula-hero__build" href="{{FORM_HREF}}#configurator">'
                  'Build Custom Formula</a>')
CTA_NEW_DETAIL = ('<a class="sf-formula-hero__build sf-quote-cta" href="/contact/#quote">'
                  'Build Custom Formula</a>')

DETAIL_TPL = 'templates/single-sf_formula.html'
SELF_CLOSING = re.compile(r'<!--\s*wp:[^>]*?/\s*-->')


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def write(path, text):
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def sha12(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def block_balance(text):
    """(opens, closes, balance) for the block-comment delimiters.

    Self-closing delimiters (`<!-- wp:foo /-->`) open and close at once, so
    counting them as opens alone leaves a phantom imbalance. The H2b scanner
    shipped exactly that bug (balance = +3) and it was only caught by reading
    the source back, so the delimiters are stripped before counting.
    """
    body = SELF_CLOSING.sub('', text)
    opens = len(re.findall(r'<!--\s*wp:', body))
    closes = len(re.findall(r'<!--\s*/wp:', body))
    return opens, closes, opens - closes


def stack_ok(text):
    """True when every non-self-closing `<!-- wp:x -->` is closed in order."""
    stack = []
    pos = 0
    token = re.compile(r'<!--\s*(/?)wp:([A-Za-z0-9/_-]+)(.*?)-->', re.S)
    for m in token.finditer(text):
        closing, name, rest = m.group(1), m.group(2), m.group(3)
        if not closing and rest.rstrip().endswith('/'):
            continue                     # self-closing
        if closing:
            if not stack or stack.pop() != name:
                return False, 'close %s with stack %s' % (name, stack[-3:])
        else:
            stack.append(name)
    if stack:
        return False, 'unclosed %s' % stack[-3:]
    return True, ''


def find_block(lines, expect_end):
    """Locate the block-4 region by marker + delimiter balance."""
    try:
        i0 = lines.index(BLOCK_MARK)
    except ValueError:
        return None, 'marker %r not found' % BLOCK_MARK
    depth = 0
    for j in range(i0 + 1, len(lines)):
        ln = lines[j]
        if ln.startswith(GROUP_OPEN) or re.match(r'<!--\s*wp:group\s', ln):
            depth += 1
        elif ln.startswith(GROUP_CLOSE):
            depth -= 1
            if depth == 0:
                end1 = j + 1                 # 1-based line number
                if end1 != expect_end:
                    return None, ('balanced close lands on L%d, scan says L%d'
                                  % (end1, expect_end))
                return (i0, j), ''           # 0-based [start, end] inclusive
    return None, 'no balanced %s after the marker' % GROUP_CLOSE


def band_lines(lines, span):
    """The five band lines inside the deleted region."""
    i0, j = span
    hits = [k for k in range(i0, j + 1) if lines[k] == BAND_OPEN]
    if len(hits) != 1:
        return None, 'band open tag appears %d times in the region' % len(hits)
    b = hits[0]
    chunk = lines[b:b + 5]
    if chunk[4] != BAND_CLOSE:
        return None, 'band is not five lines (L%d closes with %r)' % (b + 5, chunk[4])
    return (b, chunk), ''


def check_page(name, expect_end, verbose=True):
    """Return (ok, report dict). Read-only."""
    path = os.path.join(THEME, 'templates', name)
    raw = read(path)
    lines = raw.split('\n')
    rep = {'page': name, 'errors': [], 'notes': []}

    def bad(msg):
        rep['errors'].append(msg)

    if not raw.endswith('\n'):
        bad('file does not end with a newline')

    span, err = find_block(lines, expect_end)
    if err:
        bad(err)
        return False, rep
    i0, j = span
    rep['region'] = 'L%d-L%d' % (i0 + 1, j + 1)
    rep['deleted_lines'] = j - i0 + 1

    # the region must contain exactly one `id="configurator"` and one band
    region = '\n'.join(lines[i0:j + 1])
    if region.count('id="configurator"') != 1:
        bad('id="configurator" appears %d times in the region' % region.count('id="configurator"'))
    if raw.count('id="configurator"') != 1:
        bad('id="configurator" appears %d times in the file' % raw.count('id="configurator"'))
    if raw.count('href="#configurator"') != 1:
        bad('href="#configurator" appears %d times in the file' % raw.count('href="#configurator"'))
    if len(re.findall(r'<!--\s*wp:group\s', region)) < 1:
        bad('region holds no wp:group opener')

    bhits, err = band_lines(lines, span)
    if err:
        bad(err)
    else:
        b, chunk = bhits
        rep['band'] = 'L%d-L%d' % (b + 1, b + 5)
        rep['band_sha12'] = sha12('\n'.join(chunk) + '\n')
        if rep['band_sha12'] != BAND_SHA12:
            bad('band sha %s != %s' % (rep['band_sha12'], BAND_SHA12))
        if chunk != NEW_BLOCK[BAND_FIRST:BAND_LAST + 1]:
            bad('band lines differ from the declared five lines')

    # the marker of the next block must follow the deleted region
    tail = lines[j + 1:j + 4]
    if NEXT_MARK not in tail:
        bad('next block marker not within three lines after the region: %r' % tail[:2])

    if raw.count(CTA_OLD_DOSE) != 1:
        bad('hero CTA (old form) appears %d times' % raw.count(CTA_OLD_DOSE))
    for n, l in enumerate(lines, 1):
        if CTA_OLD_DOSE in l:
            rep['cta_line'] = 'L%d' % n

    return not rep['errors'], rep


def check_detail():
    path = os.path.join(THEME, DETAIL_TPL)
    raw = read(path)
    rep = {'page': DETAIL_TPL, 'errors': []}
    if raw.count(CTA_OLD_DETAIL) != 1:
        rep['errors'].append('detail CTA (old form) appears %d times' % raw.count(CTA_OLD_DETAIL))
    if raw.count('#configurator') != 1:
        rep['errors'].append('#configurator appears %d times (expect 1, the CTA)' % raw.count('#configurator'))
    for n, l in enumerate(raw.split('\n'), 1):
        if CTA_OLD_DETAIL in l:
            rep['cta_line'] = 'L%d' % n
    return not rep['errors'], rep


def validate_applied(name, raw, text):
    """Semantic post-conditions for a patched dosage page. Pure: no I/O.

    Runs on the candidate text BEFORE the write, and again on the bytes read
    back from disk, so a wrong expectation can never leave a half-applied file
    behind.
    """
    errs = []
    bl = text.split('\n')
    if text.count('id="configurator"') != 0:
        errs.append('id="configurator" survives')
    if text.count('#configurator') != 0:
        errs.append('#configurator survives')
    if text.count(CTA_NEW_DOSE) != 1:
        errs.append('new hero CTA not present exactly once')
    if BLOCK_MARK in text:
        errs.append('old block marker survives')
    if text.count(BAND_SECTION) != 1:
        errs.append('band section appears %d times' % text.count(BAND_SECTION))
    ob, oc, obal = block_balance(raw)
    nb, nc, nbal = block_balance(text)
    if obal != nbal:
        errs.append('block balance moved %+d -> %+d' % (obal, nbal))
    sok, why = stack_ok(text)
    if not sok:
        errs.append('block stack broken: %s' % why)
    hits = [k for k in range(len(bl)) if bl[k] == BAND_OPEN]
    if len(hits) != 1:
        errs.append('band open tag appears %d times' % len(hits))
    else:
        band = '\n'.join(bl[hits[0]:hits[0] + 5]) + '\n'
        if sha12(band) != BAND_SHA12:
            errs.append('band sha %s != %s' % (sha12(band), BAND_SHA12))
    if len(re.findall(r'<!--\s*wp:group\s', text)) != len(re.findall(r'<!--\s*wp:group\s', raw)):
        errs.append('wp:group opener count moved')
    return errs


def apply_page(name, expect_end):
    path = os.path.join(THEME, 'templates', name)
    raw = read(path)
    lines = raw.split('\n')
    span, err = find_block(lines, expect_end)
    if err:
        return None, err
    i0, j = span

    new = lines[:i0] + NEW_BLOCK + lines[j + 1:]
    text = '\n'.join(new)
    if text.count(CTA_OLD_DOSE) != 1:
        return None, 'hero CTA (old form) appears %d times' % text.count(CTA_OLD_DOSE)
    text = text.replace(CTA_OLD_DOSE, CTA_NEW_DOSE, 1)

    errs = validate_applied(name, raw, text)
    if errs:
        return None, '; '.join(errs)

    write(path, text)

    # re-read from disk in this same process: "the edit reported success" is
    # not evidence the bytes moved (twice bitten already in this project).
    back = read(path)
    if back != text:
        return None, 'disk bytes differ from what was written'
    errs = validate_applied(name, raw, back)
    if errs:
        return None, 'read-back: ' + '; '.join(errs)
    bl = back.split('\n')
    hits = [k for k in range(len(bl)) if bl[k] == BAND_OPEN]
    band = '\n'.join(bl[hits[0]:hits[0] + 5]) + '\n'
    delta = len(bl) - len(lines)
    if delta != -(len(lines[i0:j + 1]) - len(NEW_BLOCK)):
        return None, 'line delta %+d inconsistent' % delta
    ob, oc, obal = block_balance(raw)
    return {'page': name, 'delta': delta, 'band_sha12': sha12(band),
            'balance_before': obal, 'balance_after': block_balance(back)[2]}, ''


def apply_detail():
    path = os.path.join(THEME, DETAIL_TPL)
    raw = read(path)
    errs = []
    if raw.count(CTA_OLD_DETAIL) != 1:
        return None, 'detail CTA (old form) appears %d times' % raw.count(CTA_OLD_DETAIL)
    text = raw.replace(CTA_OLD_DETAIL, CTA_NEW_DETAIL, 1)

    # Validate the RESULT before writing anything. The first version of this
    # function asserted after the write and got the {{FORM_HREF}} count wrong
    # (2 -> 1, not 2 -> 2), so a correct edit was reported as a failure on a
    # file that had already been rewritten. Asserting on the candidate text
    # first makes a bad expectation harmless.
    if text.count('#configurator') != 0:
        errs.append('#configurator survives on the detail template')
    if text.count(CTA_NEW_DETAIL) != 1:
        errs.append('new detail CTA not present exactly once')
    if text.count('{{FORM_HREF}}') != 1:
        errs.append('{{FORM_HREF}} count is %d, expected 1 (breadcrumb keeps it, '
                    'the hero CTA no longer uses it)' % text.count('{{FORM_HREF}}'))
    if text.count('href="{{FORM_HREF}}">{{FORM_CRUMB}}</a>') != 1:
        errs.append('breadcrumb crumb lost its {{FORM_HREF}}')
    if errs:
        return None, '; '.join(errs)

    write(path, text)
    back = read(path)
    if back != text:
        return None, 'disk bytes differ from what was written'
    return {'page': DETAIL_TPL}, ''


def load_scan_ends():
    ends = {}
    if os.path.exists(SCAN):
        for e in json.load(open(SCAN, encoding='utf-8')):
            ends[e['page']] = e['block']['end']
    return ends


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--check', action='store_true', help='verify only, write nothing')
    g.add_argument('--apply', action='store_true', help='verify, then write')
    ap.add_argument('--json', help='write the report here as JSON')
    args = ap.parse_args(argv)

    if not os.path.isdir(THEME):
        print('theme directory not found: %s' % THEME, file=sys.stderr)
        return 2

    scan = load_scan_ends()
    report = {'mode': 'apply' if args.apply else 'check', 'pages': [], 'detail': {},
              'errors': []}

    # ---------- static checks (always) -----------------------------------
    for name, end in PAGES:
        if scan.get(name, end) != end:
            report['errors'].append('%s: scan end %s != table end %s'
                                    % (name, scan.get(name), end))
    if report['errors']:
        for e in report['errors']:
            print('  FAIL %s' % e)
        return 1

    ok_detail, drep = check_detail()
    report['detail'] = drep
    print('%-26s %-12s %s' % (drep['page'], drep.get('cta_line', '-'),
                              'OK' if ok_detail else 'FAIL ' + '; '.join(drep['errors'])))

    total_before = total_delta = 0
    all_ok = ok_detail
    for name, end in PAGES:
        ok, rep = check_page(name, end)
        all_ok = all_ok and ok
        report['pages'].append(rep)
        if not ok:
            print('%-26s FAIL %s' % (name, '; '.join(rep['errors'])))
            continue
        total_before += rep['deleted_lines']
        print('%-26s region %-12s %3d lines  band %-11s sha %s  cta %s' % (
            name, rep['region'], rep['deleted_lines'], rep['band'],
            rep['band_sha12'], rep.get('cta_line', '-')))
    if not all_ok:
        print('\nCHECK FAILED — nothing written.')
        return 1

    print('\nanchors OK on all %d pages + the detail template; region total %d lines;'
          % (len(PAGES), total_before))
    print('expected after apply: delete %d + insert %d = net %+d lines'
          % (total_before, len(NEW_BLOCK) * len(PAGES),
             len(NEW_BLOCK) * len(PAGES) - total_before))

    if not args.apply:
        print('--check only: no file was modified.')
        if args.json:
            json.dump(report, open(args.json, 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=2)
        return 0

    # ---------- apply -----------------------------------------------------
    print('\n--- apply ---')
    results = []
    for name, end in PAGES:
        res, err = apply_page(name, end)
        if err:
            print('%-26s FAIL %s' % (name, err))
            report['errors'].append('%s: %s' % (name, err))
            all_ok = False
            continue
        results.append(res)
        print('%-26s delta %+4d  band sha %s  balance %d -> %d' % (
            name, res['delta'], res['band_sha12'], res['balance_before'],
            res['balance_after']))
    res, err = apply_detail()
    if err:
        print('%-26s FAIL %s' % (DETAIL_TPL, err))
        report['errors'].append('%s: %s' % (DETAIL_TPL, err))
        all_ok = False
    else:
        print('%-26s CTA rewritten, {{FORM_HREF}} kept for the breadcrumb' % DETAIL_TPL)
    report['applied'] = results
    report['ok'] = all_ok

    if args.json:
        json.dump(report, open(args.json, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
    if not all_ok:
        print('\nAPPLY INCOMPLETE — see the failures above.')
        return 1
    print('\nAPPLIED: %d pages, net %+d lines' % (len(results),
                                                  sum(r['delta'] for r in results)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
