#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7f — the confinement proof for the inquiry basket's removal.

THE CLASS OF FILE THIS EXISTS FOR. The byte gate folds the declared edits out of
the candidate and compares the rest to the baseline, page by page, over all 75
captured pages. That is a strong claim and it is the right one -- for every file
whose bytes reach a page. Two kinds of file escape it, and this batch has both:

  * style.css and basket.js reach a page as a URL. The page carries a <link> or
    a <script src>, and the bytes live elsewhere. A deletion -- or, worse, an
    over-reaching deletion that also takes a neighbouring rule -- leaves all 75
    captured pages byte-identical and still changes what a reader sees. The main
    proof cannot see it. Neither can coverage: coverage counts strings, and a
    rule that stopped applying never appears in a byte string at all.
  * inc/config-pdf.php registers a REST route that no captured page calls. This
    batch deletes two functions from it. If a surviving caller still names one,
    nothing on disk moves and all 75 pages stay green -- the endpoint 500s at
    runtime only, on a path the batch's own diff set does not include.

So the claim is stated in each file's own terms, and it is a claim about the
DIFF rather than about the file:

  * style.css's 404 removed lines are exactly the 15 declared baseline
    intervals, and the interval boundaries are pinned by their first and last
    non-blank removed line. "Every removed line mentions basket" would be the
    weak form: a catch-all that a stray edit happens to satisfy. Naming the
    intervals is the strong form, and it is what makes an edit somewhere else in
    a 9,691-line stylesheet fail.
  * and inside those intervals every `{` has a `}`. 45 and 45. A carve that
    opened a block it did not close, or closed one it had already half-taken,
    leaves the file balanced but wrong, and no page can see it.
  * what the batch did NOT mean to remove is named and counted: the header CTA
    alignment rule, the certificate and inquiry dialog families they shared a
    selector list with, and the section 45 banner that survived the rewrite.
  * the candidate's stylesheet with its comments blanked out does not contain
    the word "basket" at all. The only four surviving mentions are prose inside
    comments -- which is the honest way to say "no basket selector survives",
    since the raw file does still say the word four times.
  * functions.php retires the old style token through its one enqueue line, and
    its brace structure -- open minus close -- does not move.
  * inc/config-pdf.php's function set is exactly the baseline's minus the two
    declared names, its route still registers, and, over the whole theme, every
    `sinofresh_*` name that is still called is still defined. That last clause is
    the only check in the batch that would see a dangling call on the endpoint.
  * basket.js is the only deleted file, and nothing enqueues or links it.

usage:
    b2d_h7f_confine.py --base SHA --cand SHA [--repo DIR] [--negctl]
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

THEME = 'sinofresh-theme'
CSS = THEME + '/style.css'
PHP = THEME + '/functions.php'
PDF = THEME + '/inc/config-pdf.php'
HDR = THEME + '/parts/header.html'
FTR = THEME + '/parts/footer.html'
JS = THEME + '/assets/js/basket.js'

OLD_TOKEN = '2.10.66'
NEW_TOKEN = '2.10.67'

# ---- what the batch may touch ------------------------------------------
# A claim, not a filter. Every path the two commits differ by has to be named
# here, including the batch record and the two tools, so that "the diff touches
# only the declared files" is a sentence that can be wrong.
DECLARED_FILES = {
    CSS, PHP, PDF, HDR, FTR, JS,
    'docs/batch2d-stepH7f.md',
    'tools/b2d_h7_gate.py',
    'tools/b2d_h7f_carve.py',
    'tools/b2d_h7f_confine.py',
    'tools/b2d_h7f_e2e.py',
    'tools/b2d_h7f_shots.py',
}
# Prefixes, for the one declared path that is a directory. The frames are six
# PNGs written by the browser pass; naming them one by one would be a list that
# goes stale the moment a frame is added, and the property that matters -- the
# batch put pictures there and nowhere else -- is a prefix.
DECLARED_PREFIXES = ('docs/batchH7f-shots/',)

# ---- style.css: the removal set, in the baseline's own line numbers ------
# (base_start, length, first non-blank removed line, last non-blank removed
# line). The text is a confirmation of the number, not a substitute for it: the
# numbers have to tile the removed set exactly, so a boundary that moved by one
# fails on the length AND on the text.
CSS_INTERVALS = [
    (5, 1, 'Version: 2.10.66',
     'Version: 2.10.66'),
    (2174, 2, '\t/* Hide only the Get a Quote button on phones (it wrapped onto its own',
     '\t   40px row); the inquiry basket icon inside the same container stays. */'),
    (2182, 6, '\t/* Hug the basket: under space-between the auto margin soaks up all free',
     '\t   menu column to the right edge. */'),
    (5950, 7, '/* === 45. Inquiry basket: header bag + badge + slide-in drawer ============',
     '/* --- Header bag button --------------------------------------------------- */'),
    (5960, 51, '.sf-basket-btn {',
     '.sf-basket-overlay,'),
    (6021, 1, '.sf-basket-overlay.is-open,',
     '.sf-basket-overlay.is-open,'),
    (6027, 1, '.sf-basket-overlay[hidden],',
     '.sf-basket-overlay[hidden],'),
    (6033, 253, '.sf-basket-drawer {',
     'body.sf-basket-lock,'),
    (6291, 23, '/* --- Responsive ------------------------------------------------------------ */',
     '}'),
    (6315, 10, '\t.sf-basket-btn,',
     '\t.sf-basket-drawer,'),
    (6330, 38, '/* === 46. Basket pre-fill notice (contact page, stage 3) ==================',
     '}'),
    (6709, 2, "   are the inquiry basket's — section 45 carries both class names on those",
     '   rules, so there is one definition and no drift. A centred dialog needs the'),
    (6727, 4, '\t/* The backdrop rules at section 45 hand out 10000 and the basket drawer',
     '\t   relying on document order to break the tie. */'),
    (9283, 3, "   drawer's: the outer element is the backdrop AND the centring box (flex,",
     '   definition, three components. */'),
    (9352, 2, '\t/* One generous step above the basket stack (10000/10001): the dialog is',
     '\t   the active layer whenever it is up. */'),
]
CSS_REMOVED_TOTAL = 404
CSS_REMOVED_OPEN = 45
CSS_REMOVED_CLOSE = 45

# The other half of "confined": what shared a selector list or a section with the
# basket and has to be here afterwards. A carve range that reaches one line too
# far lands on exactly these, and the byte proof cannot see any of them.
CSS_SURVIVORS = [
    ('.sf-header .sf-header__cta {', 1, 'the header CTA alignment rule'),
    ('.sf-certmodal,', 2, 'the certificate dialog backdrop list'),
    ('.sf-inquiry-modal {', 3, 'the inquiry dialog backdrop list'),
    ('.sf-certmodal.is-open,', 1, 'the dialog open state'),
    ('.sf-certmodal[hidden],', 1, 'the dialog hidden state'),
    ('body.sf-certmodal-lock,', 1, 'the dialog scroll lock'),
    ('/* === 45. Header CTA alignment', 1, 'the rewritten section 45 banner'),
    ('.sf-toast', 3, 'the toast, shared by formulas.js and toc-nav.js'),
]
CSS_ABSENT = [
    ('/* === 46', 'the basket pre-fill notice section banner'),
    ('sf-basket', 'a basket selector'),
]
CSS_PROSE_MENTIONS = 4          # lines in the raw candidate that say "basket"

# ---- inc/config-pdf.php -------------------------------------------------
PHP_LOST_FNS = ('sinofresh_basket_pdf_render', 'sinofresh_config_pdf_parse_summary')
PHP_ROUTE = re.compile(r"register_rest_route\(\s*'sinofresh/v1'\s*,\s*'/config-pdf'")

# ---- parts ---------------------------------------------------------------
# (path, removed length, first removed line, last removed line)
PART_RUNS = [
    (HDR, 3, '<!-- wp:html -->', '<!-- /wp:html -->'),
    (FTR, 19, '<div class="sf-basket-overlay" hidden></div>', '</aside>'),
]
HDR_SEAM = 'class="wp-block-buttons sf-header__cta"'
FTR_SEAM = '<div class="sf-cookie-banner"'

REF_RE = re.compile(r'basket\.js|sinofresh-basket')
FN_DECL = re.compile(r'^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(', re.M)
SF_CALL = re.compile(r'\b(sinofresh_[A-Za-z0-9_]+)\s*\(')
HUNK = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')
VERSION_LINE = re.compile(r'^\s*Version:\s*([0-9][0-9A-Za-z._-]*)\s*$')
ENQUEUE_LINE = re.compile(
    r"wp_enqueue_style\(\s*'sinofresh-style'.*?'([0-9][0-9A-Za-z._-]*)'\s*\)")


def run(cmd, cwd=None, timeout=180):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or ''), (p.stderr or '')


def show(rev, path, repo):
    rc, out, err = run(['git', '-C', repo, 'show', '%s:%s' % (rev, path)])
    if rc != 0:
        raise SystemExit('FATAL git show %s:%s: %s' % (rev, path, err[:200]))
    return out


def ls(rev, repo):
    rc, out, err = run(['git', '-C', repo, 'ls-tree', '-r', '--name-only', rev])
    if rc != 0:
        raise SystemExit('FATAL git ls-tree %s: %s' % (rev, err[:200]))
    return [p for p in out.splitlines() if p]


def diff_files(base, cand, repo):
    """{path: {'removed': [...], 'runs': [[...]], 'intervals': [(start, len)]}}

    With -U0 there is no context, so an addition run ends at the first line that
    is neither added nor a hunk header. The intervals are the base-side spans a
    hunk claims -- which is the shape this proof needs, because what it has to
    say about style.css is "the removed lines are these spans and no others".
    """
    rc, out, err = run(['git', '-C', repo, 'diff', '--no-color', '-U0', base, cand])
    if rc != 0:
        raise SystemExit('FATAL git diff %s..%s: %s' % (base, cand, err[:300]))
    files, cur, cur_f = {}, None, None
    for line in out.splitlines():
        if line.startswith('diff --git '):
            cur = None
            m = re.search(r' b/(\S+)$', line)
            if m:
                cur = m.group(1)
                cur_f = {'removed': [], 'runs': [], 'intervals': []}
                files[cur] = cur_f
            continue
        if cur is None or line.startswith('---') or line.startswith('+++'):
            continue
        if line.startswith('@@'):
            m = HUNK.match(line)
            if m:
                cur_f['intervals'].append((int(m.group(1)), int(m.group(2) or 1)))
            cur_f['runs'].append(None)
            continue
        if line.startswith('+'):
            if cur_f['runs'][-1] is None:
                cur_f['runs'][-1] = []
            cur_f['runs'][-1].append(line[1:])
        elif line.startswith('-'):
            cur_f['removed'].append(line[1:])
        else:
            if cur_f['runs']:
                cur_f['runs'][-1] = None
    for f in files.values():
        f['runs'] = [r for r in f['runs'] if r is not None]
    return files


def strip_css_comments(src):
    """Blank every /* ... */ span, in place, preserving byte offsets.

    Blanking rather than deleting matters: the claim is about what a selector
    would be, and keeping the offsets means a line-oriented count downstream
    still counts the same lines.
    """
    out, i, n = [], 0, len(src)
    while i < n:
        if src.startswith('/*', i):
            j = src.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out.append(' ' * (j - i))
            i = j
        else:
            out.append(src[i])
            i += 1
    return ''.join(out)


def strip_php_comments(src):
    """Blank every PHP comment span, leaving strings and code alone.

    A quote-aware scan rather than a regex, because the interesting strings here
    -- '/assets/js/basket.js', 'sinofresh-basket' -- live inside single quotes
    and a regex that blanked from `//` to end of line would happily eat one.
    """
    out, i, n, q = [], 0, len(src), None
    while i < n:
        c = src[i]
        if q:
            out.append(c)
            if c == '\\' and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if c == q:
                q = None
            i += 1
            continue
        if c in '\'"':
            q = c
            out.append(c)
            i += 1
            continue
        if src.startswith('/*', i):
            j = src.find('*/', i + 2)
            j = n if j < 0 else j + 2
            out.append(' ' * (j - i))
            i = j
            continue
        if src.startswith('//', i) or c == '#':
            j = src.find('\n', i)
            j = n if j < 0 else j
            out.append(' ' * (j - i))
            i = j
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def theme_php(rev, repo):
    """Every .php the theme actually loads at `rev`.

    tools/ and _backup/ are excluded, and for the same reason: neither is
    reached by a request. Leaving the archives in would make this claim WEAKER
    rather than stronger -- a 2024 snapshot of functions.php declares functions
    today's file no longer has, and a dangling call would happily resolve against
    a definition that stopped being loaded two batches ago.
    """
    pages = {}
    for p in ls(rev, repo):
        if not p.startswith(THEME + '/') or not p.endswith('.php'):
            continue
        if p.startswith(THEME + '/tools/') or p.startswith(THEME + '/_backup/'):
            continue
        pages[p] = show(rev, p, repo)
    return pages


def check(base, cand, repo, verbose=True, inject=None, survivors=None,
          intervals=None, declared_files=None, lost_fns=None):
    rows = []

    def ok(label, cond, detail=''):
        rows.append({'label': label, 'ok': bool(cond), 'detail': str(detail)})
        if verbose:
            print('  %s  %-62s %s' % ('ok  ' if cond else 'FAIL', label, detail))
        return bool(cond)

    files = diff_files(base, cand, repo)
    survivors = CSS_SURVIVORS if survivors is None else survivors
    intervals = CSS_INTERVALS if intervals is None else intervals
    declared_files = DECLARED_FILES if declared_files is None else declared_files
    lost_fns = set(PHP_LOST_FNS if lost_fns is None else lost_fns)

    # ---- the declared file set, and the one deletion --------------------
    if inject == 'stray':
        files.setdefault(THEME + '/assets/css/zz-stray.css',
                         {'removed': [], 'runs': [['.sf-header { color: red; }']],
                          'intervals': []})
    ok('the diff touches only the declared files',
       all(p in declared_files or p.startswith(DECLARED_PREFIXES) for p in files),
       'undeclared=%s' % (sorted(p for p in files
                                 if p not in declared_files and
                                 not p.startswith(DECLARED_PREFIXES)) or 'none'))
    rc, out, _ = run(['git', '-C', repo, 'diff', '--name-status', '--no-color', base, cand])
    deleted = sorted(l.split('\t', 1)[1].strip() for l in out.splitlines()
                     if l.startswith('D\t'))
    ok('basket.js is the only file the batch deletes', deleted == [JS], 'deleted=%s' % deleted)
    ok('and the candidate tree no longer has it', JS not in ls(cand, repo))
    ok('and it was 535 lines when it left',
       len(files.get(JS, {}).get('removed', [])) == 535,
       'removed lines = %d' % len(files.get(JS, {}).get('removed', [])))

    # ---- nothing points at it -------------------------------------------
    # Scoped to the files WordPress can actually load, which is not the same as
    # the files the theme ships. Two directories inside the theme are archives,
    # not code: `tools/` (the harness, which names the basket on purpose) and
    # `_backup/` (348 tracked snapshots of earlier theme versions, old
    # functions.php among them, whose enqueue lines name a basket.js that had a
    # different lineage). Neither is ever loaded by a request, so a reference in
    # one is not a dangling reference -- but it IS 348 stale PHP files shipping
    # with the theme, which is a pre-existing condition this batch did not
    # create and did not fix. Printed rather than silently filtered.
    ARCHIVE = (THEME + '/tools/', THEME + '/_backup/')
    refs, prose, archive_refs = [], [], 0
    for p in ls(cand, repo):
        if not p.startswith(THEME + '/'):
            continue
        if p.startswith(ARCHIVE):
            if p.endswith(('.php', '.html')) and REF_RE.search(show(cand, p, repo)):
                archive_refs += 1
            continue
        if not p.endswith(('.php', '.html', '.js')):
            continue
        src = show(cand, p, repo)
        code = strip_php_comments(src) if p.endswith('.php') else src
        # Blanking preserves offsets, so a mention at src[start:] is in code iff
        # the same span still matches there. That is what makes "prose" mean
        # "inside a comment" rather than "near a comment".
        for m in REF_RE.finditer(src):
            line = src[:m.start()].count('\n') + 1
            (refs if REF_RE.match(code, m.start()) else prose).append('%s:%d' % (p, line))
    ok('no code the theme loads enqueues or links basket.js any more',
       not refs, 'refs=%s' % (refs[:4] or 'none'))
    ok('...and the one place it is still named is a note that it left',
       len(prose) == 1, '%d prose mention(s): %s' % (len(prose), prose or 'none'))
    ok('the archives under _backup/ still name it, and that is not this batch',
       archive_refs > 0,
       '%d archived file(s) mention basket.js -- shipping with the theme, not '
       'loaded by any request' % archive_refs)

    # ---- style.css: the removal set --------------------------------------
    css = files.get(CSS)
    ok('style.css is in the diff at all', css is not None)
    css = css or {'removed': [], 'runs': [], 'intervals': []}
    removed = list(css['removed'])
    actual = [(s, n) for s, n in css['intervals'] if n > 0]
    want = [(s, n) for s, n, _a, _b in intervals]

    if inject == 'extra-interval':
        actual = actual + [(99000, 2)]
    if inject == 'widen':
        actual = [(s + 1 if (s, n) == actual[4] else s, n) for s, n in actual]
    if inject == 'drop-interval':
        actual = actual[1:]
    if inject == 'half-block':
        # Turn one removed `}` into a selector line: same interval, same total,
        # same first and last non-blank line (the anchor check reads the base
        # blob, not this list) -- only the brace composition moves. Getting this
        # wrong is the easy way to write a control that fires for the wrong
        # reason: shortening the interval instead made the INTERVAL rule catch
        # it, which proved nothing about the brace rule at all.
        for i, l in enumerate(removed):
            if l.strip() == '}':
                removed[i] = '.sf-zz-orphan {'
                break

    ok('the removed lines are exactly the declared intervals, and no others',
       sorted(actual) == sorted(want),
       'actual=%d intervals / %d lines; declared=%d / %d; extra=%s missing=%s'
       % (len(actual), sum(n for _s, n in actual), len(want),
          sum(n for _s, n, _a, _b in intervals),
          sorted(set(actual) - set(want))[:2] or 'none',
          sorted(set(want) - set(actual))[:2] or 'none'))

    # The number and the text both have to hold. The number says no boundary
    # moved; the text says it did not move onto a different line that happens to
    # be the same length away.
    base_css = show(base, CSS, repo).split('\n')
    bad_anchor = []
    for s, n, first, last in intervals:
        span = base_css[s - 1:s - 1 + n]
        got_first = next((l for l in span if l.strip()), '')
        got_last = next((l for l in reversed(span) if l.strip()), '')
        if got_first != first or got_last != last:
            bad_anchor.append((s, got_first[:40], first[:40]))
    ok('every interval still starts and ends where it was declared to',
       not bad_anchor, 'mismatched=%s' % (bad_anchor[:2] or 'none'))

    ok('the batch removed the declared number of lines',
       len(removed) == CSS_REMOVED_TOTAL,
       'removed=%d declared=%d' % (len(removed), CSS_REMOVED_TOTAL))
    nopen = sum(1 for l in removed if '{' in l)
    nclose = sum(1 for l in removed if '}' in l)
    ok('every `{` the batch removed has its `}` beside it',
       nopen == CSS_REMOVED_OPEN and nclose == CSS_REMOVED_CLOSE and nopen == nclose,
       'removed open=%d close=%d, declared %d/%d' % (nopen, nclose,
                                                     CSS_REMOVED_OPEN, CSS_REMOVED_CLOSE))

    ver = [l for l in removed if VERSION_LINE.match(l)]
    ok('style.css loses its version header, once, and it is the old token',
       len(ver) == 1 and VERSION_LINE.match(ver[0]).group(1) == OLD_TOKEN,
       'version lines removed = %r' % [v.strip() for v in ver])

    # ---- style.css: what has to still be there ---------------------------
    src = show(cand, CSS, repo)
    for needle, want_n, label in survivors:
        got = src.count(needle)
        ok('style.css still carries %s' % label, got == want_n,
           '%r x%d (want %d)' % (needle, got, want_n))
    for needle, label in CSS_ABSENT:
        ok('style.css no longer carries %s' % label, src.count(needle) == 0,
           '%r x%d' % (needle, src.count(needle)))

    # The honest form of "no basket selector survives". The raw file DOES still
    # say the word four times -- as prose in the comments that explain why the
    # neighbour survived. So the claim is made against the comment-blanked text,
    # where a selector would be, and the prose is then counted so that a fifth
    # mention -- the shape a real leftover rule takes -- cannot hide among them.
    stripped = strip_css_comments(src)
    ok('with comments blanked, the stylesheet never says "basket"',
       stripped.count('basket') == 0,
       'raw=%d lines / stripped=%d' % (src.count('basket'), stripped.count('basket')))
    mentions = [l for l in src.splitlines() if 'basket' in l]
    ok('and the four surviving mentions are the declared prose',
       len(mentions) == CSS_PROSE_MENTIONS and not stripped.count('basket'),
       '%d mention line(s)' % len(mentions))

    # ---- functions.php ---------------------------------------------------
    php = files.get(PHP, {'removed': [], 'runs': [], 'intervals': []})
    enc = [l for l in php['removed'] if ENQUEUE_LINE.search(l)]
    ok('functions.php retires the old style token through its enqueue line',
       len(enc) == 1 and ENQUEUE_LINE.search(enc[0]).group(1) == OLD_TOKEN,
       'enqueue lines removed=%d token=%s'
       % (len(enc), ENQUEUE_LINE.search(enc[0]).group(1) if enc else None))
    new_enc = [l for r in php['runs'] for l in r if ENQUEUE_LINE.search(l)]
    ok('...and enqueues the new one, once',
       len(new_enc) == 1 and ENQUEUE_LINE.search(new_enc[0]).group(1) == NEW_TOKEN,
       'enqueue lines added=%d token=%s'
       % (len(new_enc), ENQUEUE_LINE.search(new_enc[0]).group(1) if new_enc else None))

    def braces(rev):
        s = show(rev, PHP, repo)
        return s.count('{'), s.count('}')
    bo, bc = braces(base)
    no, nc = braces(cand)
    ok('functions.php brace structure does not move', (no - nc) == (bo - bc),
       'base %d-%d=%+d  cand %d-%d=%+d' % (bo, bc, bo - bc, no, nc, no - nc))

    # ---- inc/config-pdf.php ---------------------------------------------
    fn_base = set(FN_DECL.findall(show(base, PDF, repo)))
    fn_cand = set(FN_DECL.findall(show(cand, PDF, repo)))
    ok('inc/config-pdf.php loses exactly the declared functions',
       fn_base - fn_cand == lost_fns and not (fn_cand - fn_base),
       'lost=%s gained=%s declared=%s'
       % (sorted(fn_base - fn_cand), sorted(fn_cand - fn_base), sorted(lost_fns)))
    ok('...and that declaration is used, not vacuous', bool(fn_base - fn_cand),
       '%d function(s) named' % len(fn_base - fn_cand))
    pdf_src = show(cand, PDF, repo)
    ok('the config-pdf route is still registered',
       len(PHP_ROUTE.findall(pdf_src)) == 1,
       'matches=%d' % len(PHP_ROUTE.findall(pdf_src)))

    # THE ONE THAT ONLY THIS PROOF CAN MAKE. The route is not on any of the 75
    # captured pages, so a surviving caller of a deleted helper leaves every byte
    # on disk exactly where it was. Asked over the whole theme rather than over
    # this one file, because the caller could be anywhere.
    pages = theme_php(cand, repo)
    declared_names, called = set(), {}
    for p, s in pages.items():
        declared_names |= set(FN_DECL.findall(s))
        for m in SF_CALL.finditer(s):
            called.setdefault(m.group(1), set()).add(p)
    dangling = {k: sorted(v) for k, v in called.items() if k not in declared_names}
    if inject == 'dangling':
        dangling = dict(dangling)
        dangling.setdefault('sinofresh_basket_pdf_render', ['<injected>'])
    ok('every sinofresh_* name the theme still calls is still defined',
       not dangling,
       'declared=%d called=%d dangling=%s'
       % (len(declared_names), len(called), dangling or 'none'))
    ok('...and the two deleted names are among the calls that went away',
       not (lost_fns & set(called)),
       'still called=%s' % sorted(lost_fns & set(called)) or 'none')

    # ---- the parts -------------------------------------------------------
    for path, want_n, first, last in PART_RUNS:
        f = files.get(path, {'removed': [], 'runs': [], 'intervals': []})
        rem = f['removed']
        ok('%s loses exactly the declared run' % path,
           len(rem) == want_n and rem[0] == first and rem[-1] == last,
           'removed=%d want=%d first=%r last=%r'
           % (len(rem), want_n, rem[0][:40] if rem else None,
              rem[-1][:40] if rem else None))
    hdr_src, ftr_src = show(cand, HDR, repo), show(cand, FTR, repo)
    ok('the header CTA container closes straight onto the button that is left',
       HDR_SEAM in hdr_src, '%r' % HDR_SEAM)
    ok('the footer closes straight onto the cookie banner that shared its block',
       FTR_SEAM in ftr_src, '%r' % FTR_SEAM)
    ok('neither part still says "basket"',
       'basket' not in hdr_src and 'basket' not in ftr_src,
       'hdr=%d ftr=%d' % (hdr_src.count('basket'), ftr_src.count('basket')))

    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--cand', required=True)
    ap.add_argument('--repo', default=ROOT)
    ap.add_argument('--negctl', action='store_true')
    args = ap.parse_args()

    print('== confinement: %s -> %s ==' % (args.base[:8], args.cand[:8]))
    print('   old token: %s   new token: %s   declared intervals: %d'
          % (OLD_TOKEN, NEW_TOKEN, len(CSS_INTERVALS)))
    rows = check(args.base, args.cand, args.repo)
    ok = all(r['ok'] for r in rows)

    if args.negctl:
        print('== named negative controls ==')

        def fails(label, pair=None, want=None, **kw):
            """A control passes when the check refuses -- and, when `want` is
            given, when it refuses FOR THE NAMED REASON. A control that fires
            because a neighbouring rule tripped is a control that proves nothing
            about the rule it was written for, which is how seven failures once
            turned out to be one defect talking through seven mouths."""
            b = pair[0] if pair else args.base
            c = pair[1] if pair else args.cand
            try:
                r = check(b, c, args.repo, verbose=False, **kw)
                bad = [x['label'] for x in r if not x['ok']]
            except SystemExit as e:
                bad = [str(e)[:70]]
            if want:
                good = any(want in x for x in bad)
            else:
                good = bool(bad)
            print('  %s  %-58s %s'
                  % ('ok  ' if good else 'FAIL', label,
                     (bad[:1] or 'nothing fired') if good else
                     ('fired, but not on %r: %s' % (want, bad[:2]))))
            return good

        # NC1 -- a range that also contains an earlier batch's stylesheet edits.
        # Those rules are real, shipped, and not this batch's, so the interval
        # claim must fail. Two things are arranged so that the interval rule is
        # the one that has to speak. First, the range is picked by measurement
        # rather than by "two commits back": the H7e commit that bumped the
        # token three lines above this one's reach leaves style.css's diff the
        # SAME 15 intervals, so that range failed on the anchor text and never
        # touched the claim. Second, every path the wider diff touches is
        # declared, so the file-set rule is satisfied and cannot answer first.
        rc, out, _ = run(['git', '-C', args.repo, 'log', '--format=%H', '-8',
                          args.base, '--', CSS])
        wide = None
        for c in out.split():
            try:
                f = diff_files(c, args.cand, args.repo)
            except SystemExit:
                continue
            if len(f.get(CSS, {}).get('removed', [])) > CSS_REMOVED_TOTAL + 5:
                wide = c
                break
        if wide:
            ok &= fails('NC1 a wider range with foreign removals fails',
                        pair=(wide, args.cand),
                        declared_files=set(diff_files(wide, args.cand, args.repo)),
                        want='the removed lines are exactly the declared intervals')
        else:
            print('  FAIL  NC1 a wider range with foreign removals fails'
                  '  no range in the last 8 commits touches style.css enough')
        # NC2 -- a survivor that is not there. Without this, "the survivors
        # survive" is a list never watched to fail.
        ok &= fails('NC2 a survivor that has gone fails',
                    survivors=list(CSS_SURVIVORS) + [('.sf-nothing-here {', 1, 'invented')])
        # NC3 -- one interval boundary pushed out by a line, which is what an
        # over-reaching carve looks like.
        ok &= fails('NC3 a boundary that moved by one line fails', inject='widen')
        # NC4 -- the declaration missing an interval the diff actually has.
        ok &= fails('NC4 an interval left out of the declaration fails',
                    inject='extra-interval')
        # NC5 -- and the mirror: a declared interval the diff does not have.
        ok &= fails('NC5 an interval the diff does not have fails', inject='drop-interval')
        # NC6 -- a half-block: the closing brace left behind. Only the brace rule
        # can see this, which is why the control names the rule it wants.
        ok &= fails('NC6 a removed block that kept its closing brace fails',
                    inject='half-block', want='every `{` the batch removed')
        # NC7 -- a dangling call on the endpoint path. Named, because the
        # call-graph rule is the only check in the batch that can see it.
        ok &= fails('NC7 a call to a deleted function fails',
                    inject='dangling', want='still calls is still defined')
        # NC8 -- an undeclared file in the diff.
        ok &= fails('NC8 a file outside the declaration fails', inject='stray')

    print('\n%s  batch H7f confinement' % ('PASS' if ok else 'FAIL'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
