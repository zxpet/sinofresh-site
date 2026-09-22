#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H2b2 — stop enqueueing the configurator, then delete its two assets.

This is a pure-deletion batch, so the risk is not "the edit is wrong" but
"the edit is *more* than declared". Three habits from earlier batches carry
straight over:

  * **Locate by structure, not by line number.** The plan says lines 187-190
    of functions.php. Those numbers are cross-checked here, but the region is
    actually found by anchoring on `$dosage_pages = [` and walking forward
    through the `$is_dosage_page` assignment, the `if (...) {` guard, its two
    enqueue calls, and the closing brace. If a line drifts, this fails loudly
    instead of slicing the wrong four lines out of a PHP file.

  * **An edit receipt is not bytes on disk.** Every write is followed by a
    re-read in the same process and compared to the intended text.

  * **Validate before write.** The post-conditions are evaluated on the
    candidate text *first*, so a wrong expectation can never leave the file
    half-edited.

The `$is_dosage_page` trap is worth stating out loud, because the inherited
plan had it wrong: deleting "the two enqueue lines" would have left an empty
`if ($is_dosage_page) { }` shell, and deleting the whole block naively would
have taken `$dosage_pages` / `$is_dosage_page` with it — but line 205 still
enqueues formulas.js behind `if ($is_dosage_page || is_singular('sf_formula')
|| is_post_type_archive('sf_formula'))`. So the assertion is two-sided: the
guard's *users* survive, and its *one* use for the configurator does not.

usage:
    python3 tools/b2d_h2b2_patch.py --check     # read-only, prints the report
    python3 tools/b2d_h2b2_patch.py --apply     # edits functions.php, deletes the assets
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
THEME = os.path.join(ROOT, 'sinofresh-theme')
FUNC = os.path.join(THEME, 'functions.php')
CSS = os.path.join(THEME, 'assets', 'css', 'configurator.css')
JS = os.path.join(THEME, 'assets', 'js', 'configurator.js')

# Measured in the Step 0 scan; asserted before anything is removed so the files
# being deleted are provably the ones the scan classified.
CSS_BYTES, CSS_LINES = 21808, 831
JS_BYTES, JS_LINES = 31276, 875

DOSAGE_DECL = "$dosage_pages = ["
IS_DOSAGE = "$is_dosage_page = is_page("
GUARD = "if ($is_dosage_page) {"
CFG_CSS = "wp_enqueue_style('sinofresh-configurator'"
CFG_JS = "wp_enqueue_script('sinofresh-configurator'"
# The formulas.js enqueue that must keep working (K1 contract).
FORMULAS_GUARD = "if ($is_dosage_page || is_singular('sf_formula') || is_post_type_archive('sf_formula'))"

EXPECT_LINES = (187, 190)          # cross-check only — the search is structural


def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def write(path, text):
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def sha256(path):
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


BLOCK_COMMENT = re.compile(r'/\*.*?\*/', re.S)


def strip_block_comments(text):
    """Blank out `/* … */` bodies, preserving line count.

    A continuation line inside a block comment does not start with `*` (see
    functions.php:1231 and :1237), so a line-prefix test calls them code. This
    removes the whole comment instead, which is what "is this token live?"
    actually means.
    """
    return BLOCK_COMMENT.sub(lambda m: '\n' * m.group(0).count('\n'), text)


def find_region(lines):
    """Return (i0, j) 0-based inclusive for the four-line guard block."""
    hits = [k for k, ln in enumerate(lines) if ln.strip() == DOSAGE_DECL.strip()
            or ln.startswith('\t' + DOSAGE_DECL)]
    if len(hits) != 1:
        return None, '$dosage_pages declaration appears %d times' % len(hits)
    d = hits[0]
    if not lines[d + 1].startswith('\t' + IS_DOSAGE):
        return None, 'line after the declaration is not the $is_dosage_page assignment: %r' % lines[d + 1]
    g = d + 2
    if lines[g].strip() != GUARD:
        return None, 'line %d is not the guard %r: %r' % (g + 1, GUARD, lines[g])
    if CFG_CSS not in lines[g + 1]:
        return None, 'L%d is not the configurator style enqueue: %r' % (g + 2, lines[g + 1])
    if CFG_JS not in lines[g + 2]:
        return None, 'L%d is not the configurator script enqueue: %r' % (g + 3, lines[g + 2])
    if lines[g + 3].strip() != '}':
        return None, 'L%d does not close the guard: %r' % (g + 4, lines[g + 3])
    # nothing else may be inside the guard
    if lines[g + 4].strip() == '':
        return None, 'a blank line follows the guard — the region is not self-contained'
    return (g, g + 3), ''


def validate(func_text, raw):
    """Pure post-conditions for the edited functions.php.

    Note what is *not* asserted: `configurator.js` as a bare token survives in
    five comment lines (L511, 1088, 1090, 1231, 1237). Those comments are the
    recorded rationale for the K2 `.sf-formulas-data` block and the session
    keys — both of which keep existing this batch. They are the H6 dead-code
    items, so they are counted and left exactly as they are; only the two
    *enqueue paths* are required to be gone.
    """
    errs = []
    if 'sinofresh-configurator' in func_text:
        errs.append('sinofresh-configurator still enqueued somewhere')
    for needle in ("'/assets/css/configurator.css'", "'/assets/js/configurator.js'"):
        if needle in func_text:
            errs.append('enqueue path %s survives' % needle)
    if strip_block_comments(func_text).count('configurator.js') != 0:
        errs.append('configurator.js is still live in code')
    if func_text.count('configurator.js') != raw.count('configurator.js') - 1:
        errs.append('configurator.js comment mentions moved by %+d, expected exactly -1 '
                    '(the enqueue line only)' % (func_text.count('configurator.js')
                                                 - raw.count('configurator.js')))
    # the guard's data must survive for formulas.js
    if func_text.count('$is_dosage_page') != 2:
        errs.append('$is_dosage_page appears %d times, expected 2 (declaration + '
                    'the formulas.js guard)' % func_text.count('$is_dosage_page'))
    if func_text.count(DOSAGE_DECL) != 1:
        errs.append('$dosage_pages declaration count is %d' % func_text.count(DOSAGE_DECL))
    if func_text.count(FORMULAS_GUARD) != 1:
        errs.append('the formulas.js guard is gone')
    if GUARD in func_text:
        errs.append('the empty guard shell survives')
    # an enqueue block that lost its body would leave a bare `if (...) {` with a
    # blank line inside; catch the shape rather than trusting the delete.
    if re.search(r'\n\t\}\n\t\n\t//', func_text):
        errs.append('a blank line sits where the block used to be')
    # The raw brace counts do NOT balance in this file (braces appear inside
    # strings and comments), so comparing them to each other is meaningless.
    # What matters is that the file's raw balance is unchanged: the deleted
    # region carried one `{` and one `}`.
    if func_text.count('{') - raw.count('{') != -1:
        errs.append('open braces moved by %+d, expected -1'
                    % (func_text.count('{') - raw.count('{')))
    if func_text.count('}') - raw.count('}') != -1:
        errs.append('close braces moved by %+d, expected -1'
                    % (func_text.count('}') - raw.count('}')))
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--check', action='store_true', help='verify only, write nothing')
    g.add_argument('--apply', action='store_true', help='verify, then write')
    ap.add_argument('--json', help='write the report here as JSON')
    args = ap.parse_args(argv)

    report = {'mode': 'apply' if args.apply else 'check', 'errors': [], 'notes': []}

    def bad(m):
        report['errors'].append(m)
        print('  FAIL ' + m)

    def ok(m):
        report['notes'].append(m)
        print('  ok   ' + m)

    # ---- preconditions: the assets are the ones the scan classified ---------
    for path, want_b, want_l, label in ((CSS, CSS_BYTES, CSS_LINES, 'configurator.css'),
                                        (JS, JS_BYTES, JS_LINES, 'configurator.js')):
        if not os.path.exists(path):
            bad('%s is already gone' % label)
            continue
        size = os.path.getsize(path)
        lines = read(path).count('\n') + (0 if read(path).endswith('\n') else 1)
        report[label] = {'bytes': size, 'lines': lines, 'sha256': sha256(path)}
        if (size, lines) != (want_b, want_l):
            bad('%s is %d B / %d lines, scan said %d B / %d lines'
                % (label, size, lines, want_b, want_l))
        else:
            ok('%s is %d B / %d lines (scan-identical)' % (label, size, lines))

    # ---- structural find ---------------------------------------------------
    raw = read(FUNC)
    lines = raw.split('\n')
    span, err = find_region(lines)
    if err:
        bad('functions.php: ' + err)
    else:
        i0, j = span
        report['region'] = 'L%d-L%d' % (i0 + 1, j + 1)
        if (i0 + 1, j + 1) != EXPECT_LINES:
            bad('region lands on L%d-L%d, the scan declared L%d-L%d'
                % (i0 + 1, j + 1, EXPECT_LINES[0], EXPECT_LINES[1]))
        else:
            ok('guard block found structurally at exactly L%d-L%d' % (i0 + 1, j + 1))
        deleted = lines[i0:j + 1]
        report['deleted'] = [ln.strip()[:60] for ln in deleted]
        # `configurator.js` must survive as a bare token in comments only: those
        # lines are the recorded rationale for K2 and the session keys, which
        # keep existing this batch (H6 owns them).
        code_only = strip_block_comments(raw)
        live = code_only.count('configurator.js')
        report['js_live_refs'] = live
        refs = [n for n, ln in enumerate(lines, 1) if 'configurator.js' in ln]
        report['comment_refs'] = refs
        if live != 1:
            bad('configurator.js appears %d times in live code, expected exactly 1 '
                '(the enqueue being deleted)' % live)
        else:
            ok('configurator.js is live in exactly 1 place (the enqueue); it also sits '
               'in %d comment line(s) at %s — H6 dead-code rationale, untouched'
               % (len(refs), refs))

    if report['errors']:
        print('\nCHECK FAILED — nothing written.')
        if args.json:
            json.dump(report, open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        return 1

    # ---- validate before write --------------------------------------------
    new = lines[:i0] + lines[j + 1:]
    text = '\n'.join(new)
    errs = validate(text, raw)
    if errs:
        for e in errs:
            bad('candidate: ' + e)
        print('\nCANDIDATE REJECTED — nothing written.')
        if args.json:
            json.dump(report, open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        return 1
    delta = len(new) - len(lines)
    ok('candidate text passes all post-conditions (line delta %+d)' % delta)

    if not args.apply:
        print('\n--check only: no file was modified.')
        if args.json:
            json.dump(report, open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        return 0

    # ---- apply -------------------------------------------------------------
    print('\n--- apply ---')
    before_sha = sha256(FUNC)
    write(FUNC, text)
    back = read(FUNC)
    if back != text:
        bad('disk bytes differ from what was written')
    else:
        errs = validate(back, raw)
        if errs:
            for e in errs:
                bad('read-back: ' + e)
        else:
            ok('functions.php read-back matches and re-validates (sha %s -> %s)'
               % (before_sha[:12], sha256(FUNC)[:12]))
    report['functions'] = {'sha_before': before_sha, 'sha_after': sha256(FUNC),
                           'delta': delta}
    report['applied'] = ['functions.php']
    report['ok'] = not report['errors']

    # assets: removed last, so a failed edit cannot leave a page enqueueing a
    # file that no longer exists.
    for path, label in ((CSS, 'configurator.css'), (JS, 'configurator.js')):
        if report['errors']:
            break
        os.remove(path)
        if os.path.exists(path):
            bad('%s still present after remove' % label)
        else:
            ok('%s removed' % label)
            report['applied'].append(label)
    css_dir = os.path.dirname(CSS)
    if not report['errors']:
        if os.path.isdir(css_dir) and not os.listdir(css_dir):
            os.rmdir(css_dir)
        if os.path.isdir(css_dir):
            bad('assets/css/ still exists with %s' % os.listdir(css_dir))
        else:
            ok('assets/css/ is gone (it held only configurator.css)')

    # php -l as the last line of defence — a structural find that produced
    # syntactically valid but semantically wrong PHP would still parse, but a
    # mangled delete will not.
    php = shutil_which_php()
    if php and not report['errors']:
        p = subprocess.run([php, '-l', FUNC], capture_output=True, text=True)
        if p.returncode != 0:
            bad('php -l: %s' % (p.stderr or p.stdout).strip())
        else:
            ok('php -l functions.php clean')

    if args.json:
        json.dump(report, open(args.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    if report['errors']:
        print('\nAPPLY INCOMPLETE — see the failures above.')
        return 1
    print('\nAPPLIED: functions.php -%d lines, 2 assets deleted' % abs(delta))
    return 0


def shutil_which_php():
    for p in ('/usr/bin/php', '/opt/homebrew/bin/php', '/usr/local/bin/php'):
        if os.path.exists(p):
            return p
    return None


if __name__ == '__main__':
    sys.exit(main())
