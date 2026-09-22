#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7c — the confinement proof for the stylesheet.

The byte gate folds the declared section out of the candidate and compares what
is left to the baseline, page by page. That covers every file whose bytes reach
the page -- the template, the renderer's output -- and it covers them well. It
cannot cover style.css, and not by accident: a stylesheet never appears in a
page's byte string. An edit to an EXISTING rule the batch never declared would
leave all 75 pages byte-identical and still change what a reader sees.

So the stylesheet gets the claim stated in its own terms instead: the two
commits differ by the version header and one added block, and by nothing else.

  * style.css loses exactly one line, the old version header.
  * style.css gains the new version header and one contiguous block, and every
    selector opened inside that block belongs to the declared namespace.
  * functions.php loses exactly the one enqueue line, and what it gains is the
    new renderer.
  * the template only gains.

Contiguity is the load-bearing part. "Every added line mentions the namespace"
would be satisfied by edits scattered through the file as long as each one
happened to carry the token -- and the failure this exists to catch is an edit
somewhere else entirely, which by definition does not.

usage:
    b2d_h7c_confine.py --base SHA --cand SHA [--repo DIR] [--negctl]
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

DEFAULT_NS = ('.sf-fdetail-specs',)
STYLE = 'sinofresh-theme/style.css'
PHP = 'sinofresh-theme/functions.php'
TPL = 'sinofresh-theme/templates/single-sf_formula.html'


def run(cmd, cwd=None, timeout=120):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or ''), (p.stderr or '')


def diff_files(base, cand, repo):
    """{path: (removed_lines, added_runs)} for the three files this batch owns.

    added_runs is a list of runs, each a list of lines, in file order. With -U0
    there is no context, so a run ends at the first line that is neither added
    nor a hunk header -- which is what makes "contiguous" mean contiguous.
    """
    rc, out, err = run(['git', '-C', repo, 'diff', '--no-color', '-U0', base, cand],
                       timeout=180)
    if rc != 0:
        raise SystemExit('FATAL git diff %s..%s: %s' % (base, cand, err[:300]))
    files, cur, removed, runs, run_ = {}, None, [], [], None
    for line in out.splitlines():
        if line.startswith('diff --git '):
            if cur:
                files[cur] = (removed, runs)
            cur = None
            removed, runs, run_ = [], [], None
            m = re.search(r' b/(\S+)$', line)
            if m:
                cur = m.group(1)
            continue
        if cur is None or line.startswith('+++') or line.startswith('---'):
            continue
        if line.startswith('@@'):
            run_ = None
            continue
        if line.startswith('+'):
            if run_ is None:
                run_ = []
                runs.append(run_)
            run_.append(line[1:])
        elif line.startswith('-'):
            run_ = None
            removed.append(line[1:])
        else:
            run_ = None
    if cur:
        files[cur] = (removed, runs)
    return files


VERSION_LINE = re.compile(r'^\s*Version:\s*([0-9][0-9A-Za-z._-]*)\s*$')
ENQUEUE_LINE = re.compile(r"wp_enqueue_style\(\s*'sinofresh-style'.*?'([0-9][0-9A-Za-z._-]*)'\s*\)")
FN_DECL = re.compile(r'^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(')


def _openers(block):
    """Every selector or at-rule the added block opens, plus the containers.

    Line-ending punctuation is not enough to find a rule: `.a { color: red; }`
    on one line opens a selector and ends with a brace that closes it, so an
    opener test keyed on `endswith('{')` sees nothing at all -- which is exactly
    what NC5 caught when this was written. So the test is "a line that mentions
    `{`, outside a comment", and the text before that brace decides whether it is
    a selector (must name the namespace) or an at-rule (must be media/supports).
    Comments are tracked rather than skipped by prefix, because a comment is
    where a selector-shaped string is most likely to appear innocently.
    """
    selectors, at_rules = [], []
    in_comment = False
    for raw in block:
        line = raw
        while line:
            if in_comment:
                end = line.find('*/')
                if end < 0:
                    line = ''
                    continue
                in_comment, line = False, line[end + 2:]
                continue
            start = line.find('/*')
            brace = line.find('{')
            if start >= 0 and (brace < 0 or start < brace):
                in_comment, line = True, line[start + 2:]
                continue
            break
        if '{' not in line:
            continue
        head = line.split('{', 1)[0].strip()
        if not head:
            continue
        if head.startswith('@'):
            at_rules.append(head)
        else:
            selectors.append(head)
    return selectors, at_rules


def _inject_inside_media(files, one_line=False):
    """NC3/NC5's mutant: a foreign rule hidden inside the batch's own @media.

    It sits in the same contiguous run, so contiguity cannot see it; only the
    selector rule can. `one_line` writes it as `.a { color: red; }` instead of a
    three-line block, which is the shape an opener test keyed on line endings
    misses entirely.
    """
    _, runs = files.get(STYLE, ([], []))
    for r in runs:
        if len(r) == 1 and VERSION_LINE.match(r[0]):
            continue
        for i, l in enumerate(r):
            if l.strip().startswith('@media'):
                if one_line:
                    r.insert(i + 1, '\t.some-existing-rule { color: red; }')
                else:
                    r[i + 1:i + 1] = ['\t.some-existing-rule {', '\t\tcolor: red;', '\t}']
                return True
    return False


def _inject_second_run(files):
    """NC4's mutant: a foreign edit somewhere else in the file entirely.

    Appended as a second run, which is what a stray edit elsewhere in a 290KB
    stylesheet looks like in a unified diff.
    """
    if STYLE not in files:
        return False
    removed, runs = files[STYLE]
    runs.append(['.sf-header-inner { color: red; }'])
    return True


def check(base, cand, repo, namespaces, verbose=True, inject=None,
          expect_php='sf_formula_specs_table', tpl_line='[sf_formula_specs_table]',
          js_removed_ok=None, allowed_files=None, fns=None):
    """The confinement claim, per file.

    WHICH FILES THIS GUARDS, AND WHY IT IS NOT ALL OF THEM. A stylesheet or a
    script reaches a page as a URL: the page carries a link and the bytes live
    elsewhere. So an edit to an EXISTING rule or an existing branch changes what
    a reader sees and leaves every one of the 75 captured pages byte-identical —
    the main proof cannot see it, and neither can coverage. That is the class of
    file this proof exists for, and H7d widened it from style.css to include the
    scripts.

    PHP is the other case: functions.php's output IS the page's bytes, so a
    deletion or an edit there moves the candidate. Those changes are owned by
    the main proof (everything outside the declared region must be identical)
    and by the coverage counts (a row that stopped being printed drops a count).
    This proof still asserts the two things PHP can hide: that the file retires
    the old style token through its enqueue line, and that its additions are ONE
    contiguous block containing the declared symbol. What it does not do is
    pretend to enumerate the removals, because a rule that says "every removed
    line must be listed here" over a 40-line renderer rewrite is a rule that
    gets satisfied by a catch-all regex — a rubber stamp wearing a check's
    clothes.
    """
    rows = []

    def ok(label, cond, detail=''):
        rows.append({'label': label, 'ok': bool(cond), 'detail': str(detail)})
        if verbose:
            print('  %s  %-64s %s' % ('ok  ' if cond else 'FAIL', label, detail))
        return bool(cond)

    files = diff_files(base, cand, repo)
    if allowed_files is None:
        allowed_files = {STYLE, PHP, TPL}
    if inject in ('media', 'media1line'):
        if not _inject_inside_media(files, one_line=(inject == 'media1line')):
            raise SystemExit('FATAL %s could not build its mutant' % inject)
    elif inject == 'run':
        if not _inject_second_run(files):
            raise SystemExit('FATAL NC4 could not build its mutant')

    # ---- style.css ------------------------------------------------------
    removed, runs = files.get(STYLE, ([], []))
    ok('style.css is in the diff at all', STYLE in files)
    bad = [l for l in removed if not VERSION_LINE.match(l)]
    ok('style.css loses the version header and nothing else',
       len(removed) == 1 and not bad,
       'removed=%d %s' % (len(removed), bad[:3] or ''))

    version_runs, block_runs = [], []
    for r in runs:
        if len(r) == 1 and VERSION_LINE.match(r[0]):
            version_runs.append(r)
        else:
            block_runs.append(r)
    ok('style.css gains the version header once', len(version_runs) == 1,
       'runs=%r' % ([r[0].strip() for r in version_runs],))
    ok('and exactly one contiguous block of rules', len(block_runs) == 1,
       '%d block run(s): %s' % (len(block_runs),
                                ' | '.join('+%d lines' % len(r) for r in block_runs)))
    if len(block_runs) == 1:
        block = block_runs[0]
        selectors, at_rules = _openers(block)
        # An at-rule is a container, not a selector: `@media (max-width: 900px)`
        # cannot carry a class name, and the rules INSIDE it can and must. So
        # at-rules are allowed only from a small allow-list, and every other
        # opener has to name the namespace -- which is what stops a foreign rule
        # from hiding inside one of this batch's media queries.
        foreign_at = [o for o in at_rules if not re.match(r'@(media|supports)\b', o)]
        ok('the block opens only @media/@supports containers',
           not foreign_at, 'at-rules=%d foreign=%s' % (len(at_rules), foreign_at[:4] or 'none'))
        foreign = [s for s in selectors if not any(ns in s for ns in namespaces)]
        ok('every selector opened in it belongs to the namespace',
           selectors and not foreign,
           '%d selector(s), %d at-rule(s), foreign=%s'
           % (len(selectors), len(at_rules), foreign[:4] or 'none'))
        ok('the block carries the namespace at all',
           any(any(ns in l for ns in namespaces) for l in block),
           'ns=%s' % (list(namespaces),))
    # The DECLARED FILE SET, exactly. Named for what it is: a batch also commits
    # documents, and pretending otherwise would mean either an implicit
    # exclusion list or a check that fails on its own batch record. Declaring
    # every path is the point — the set is a claim, not a filter.
    ok('the diff touches only the declared files',
       set(files) <= allowed_files, 'files=%s' % sorted(files))

    # ---- the scripts: linked, not contained -----------------------------
    # The same hazard as the stylesheet, and the reason H7d has these rules:
    # inquiry.js lost exactly one line, and that line decides which band the
    # reveal watches. A page cannot see it.
    js_removed_ok = js_removed_ok or {}
    for rel, (jrem, jruns) in sorted(files.items()):
        if not rel.endswith('.js'):
            continue
        allowed = [re.compile(p) for p in js_removed_ok.get(rel, [])]
        bad = [l for l in jrem if not any(p.search(l) for p in allowed)]
        ok('%s loses only its declared lines' % rel, not bad,
           'removed=%d, undeclared=%s' % (len(jrem), bad[:3] or 'none'))
        if rel in js_removed_ok:
            ok('  ...and that declaration is used, not vacuous',
               bool(jrem), 'removed=%d' % len(jrem))

    # ---- functions.php --------------------------------------------------
    removed, runs = files.get(PHP, ([], []))
    enc = [l for l in removed if ENQUEUE_LINE.search(l)]
    ok('functions.php retires the old style token', len(enc) == 1,
       'enqueue lines removed = %d' % len(enc))
    if enc:
        m = ENQUEUE_LINE.search(enc[0])
        ok('...and it is the old style token', bool(m) and m.group(1) == old_ver,
           'token=%r' % (m.group(1) if m else None))
    ok('functions.php loses %d line(s), owned by the byte proof' % len(removed), True,
       'the main proof and coverage see every PHP change; this proof does not '
       're-enumerate them')

    # WHICH FUNCTIONS THE BATCH ADDS -- the PHP analogue of "every selector
    # belongs to the namespace". The set must be EQUAL, not merely contained:
    # a stray function added on a path no captured page exercises (the REST
    # endpoint is exactly that) leaves every byte on disk unchanged, so this is
    # the only check that would see it.
    added_fns = set()
    for r in runs:
        for l in r:
            m = FN_DECL.match(l)
            if m:
                added_fns.add(m.group(1))
    declared_fns = set(fns) if fns else {expect_php}
    ok('functions.php adds exactly the declared functions',
       added_fns == declared_fns,
       'added=%s declared=%s' % (sorted(added_fns), sorted(declared_fns)))

    # NOT a claim: the number of change sites. With -U0 an addition is split
    # wherever a removal falls, so "one contiguous block" measures the editor's
    # diff shape rather than the batch's blast radius — it held for H7c, whose
    # edit was one insertion, and is 11 for H7d, whose edit also REWRITES a
    # renderer. Printed so the shape is visible, not asserted, and the PHP side
    # is owned by the byte proof plus the equality above.
    ok('functions.php change sites (informational)', True,
       '%d added run(s), %d removed line(s), %d added line(s)'
       % (len(runs), len(removed), sum(len(r) for r in runs)))
    ok('the declared symbol is among the additions',
       any(expect_php in '\n'.join(r) for r in runs),
       'expects %r' % expect_php)

    # ---- the template ---------------------------------------------------
    removed, runs = files.get(TPL, ([], []))
    ok('the template only gains, and loses nothing', not removed,
       'removed=%d' % len(removed))
    ok('the template gains the shortcode call once',
       sum(1 for r in runs for l in r if l.strip() == tpl_line) == 1,
       tpl_line)

    return rows


def _ver_of(rev, repo):
    """The style token style.css carried in `rev` -- the one the batch retires."""
    rc, out, err = run(['git', '-C', repo, 'show', '%s:%s' % (rev, STYLE)])
    if rc != 0:
        raise SystemExit('FATAL git show %s:%s: %s' % (rev, STYLE, err[:200]))
    for line in out.splitlines():
        m = VERSION_LINE.match(line)
        if m:
            return m.group(1)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--cand', required=True)
    ap.add_argument('--repo', default=ROOT)
    ap.add_argument('--ns', action='append', default=None,
                    help='a class the added block is allowed to own (repeatable)')
    ap.add_argument('--expect-php', default='sf_formula_specs_table',
                    help='the symbol the added PHP block must contain')
    ap.add_argument('--tpl-line', default='[sf_formula_specs_table]',
                    help='the template line the batch adds exactly once')
    ap.add_argument('--js-removed-ok', action='append', default=None,
                    metavar='FILE=REGEX',
                    help='a removed line in FILE that the batch declares '
                         '(repeatable). Every JS file in the diff must have '
                         'each of its removed lines declared.')
    ap.add_argument('--allow-file', action='append', default=None, metavar='PATH',
                    help='a file this batch is allowed to touch IN ADDITION to '
                         'style.css, functions.php and the template (repeatable). '
                         'Use it for the batch record and for any scratch file it '
                         'commits. The flag used to REPLACE the default three, so '
                         'the first batch that also committed a document reported '
                         'its own theme files as unexpected -- and a check whose '
                         'declaration silently narrows to one path is one that can '
                         'never fail on the files it was written for.')
    ap.add_argument('--fn', action='append', default=None, metavar='NAME',
                    help='a function this batch adds (repeatable); the set must '
                         'match exactly. Default: --expect-php alone.')
    ap.add_argument('--negctl', action='store_true')
    args = ap.parse_args()

    global old_ver
    old_ver = _ver_of(args.base, args.repo)
    namespaces = tuple(args.ns) if args.ns else DEFAULT_NS
    js_removed_ok = {}
    for spec in args.js_removed_ok or []:
        if '=' not in spec:
            raise SystemExit('FATAL --js-removed-ok wants FILE=REGEX, got %r' % spec)
        f, pat = spec.split('=', 1)
        js_removed_ok.setdefault(f, []).append(pat)
    extra = {'expect_php': args.expect_php, 'tpl_line': args.tpl_line,
             'js_removed_ok': js_removed_ok,
             # `--allow-file` ADDS to the theme's own three, which is what its
             # help has always said it does. Passing it must not be a way to
             # shrink the declaration to a single path.
             'allowed_files': (({STYLE, PHP, TPL} | set(args.allow_file))
                               if args.allow_file else None),
             'fns': args.fn}

    print('== confinement: %s -> %s ==' % (args.base[:8], args.cand[:8]))
    print('   namespace: %s   old token: %s' % (', '.join(namespaces), old_ver))
    rows = check(args.base, args.cand, args.repo, namespaces, **extra)
    ok = all(r['ok'] for r in rows)

    if args.negctl:
        print('== named negative controls ==')
        # NC1 -- the same check over a range that ALSO contains an earlier
        # batch's stylesheet edits. Those rules are real, shipped, and not part
        # of this namespace, so the confinement claim must fail. This is the
        # control that proves the check can see a foreign selector: without it,
        # "every selector belongs to the namespace" is a claim never watched to
        # fail.
        rc, out, _ = run(['git', '-C', args.repo, 'log', '--format=%H', '-3', args.base])
        if rc == 0 and len(out.split()) >= 3:
            wide = out.split()[2]
            try:
                r2 = check(wide, args.cand, args.repo, namespaces, verbose=False, **extra)
                caught = not all(x['ok'] for x in r2)
                why = [x['label'] for x in r2 if not x['ok']][:2]
            except SystemExit as e:
                caught, why = True, [str(e)[:80]]
            print('  %s  NC1 a wider range with foreign rules fails  %s'
                  % ('ok  ' if caught else 'FAIL', why or ''))
            ok &= caught
        # NC2 -- an empty namespace must fail on the real pair: the check
        # cannot be satisfied by claiming nothing.
        r3 = check(args.base, args.cand, args.repo, ('ZZ_NO_SUCH_TOKEN',), verbose=False, **extra)
        caught = not all(x['ok'] for x in r3)
        print('  %s  NC2 a namespace that matches nothing fails  %s'
              % ('ok  ' if caught else 'FAIL',
                 [x['label'] for x in r3 if not x['ok']][:1]))
        ok &= caught

        # NC3/NC5 -- a foreign rule hidden INSIDE this batch's own media query.
        # Same contiguous run, so only the selector rule can catch it, and the
        # second form -- written on one line -- is the shape an opener test keyed
        # on `endswith('{')` misses. Both must fail.
        for tag, label in (
                ('media', 'NC3 a foreign rule opened inside @media fails'),
                ('media1line', 'NC5 the same rule written on one line fails'),
                ('run', 'NC4 a foreign rule added as a second run fails')):
            r4 = check(args.base, args.cand, args.repo, namespaces,
                       verbose=False, inject=tag, **extra)
            caught = not all(x['ok'] for x in r4)
            print('  %s  %-56s %s'
                  % ('ok  ' if caught else 'FAIL', label,
                     [x['label'] for x in r4 if not x['ok']][:1]))
            ok &= caught

        # NC6 -- the JS rule is a signal, not a comment. Dropping the batch's
        # own declaration must make the same diff fail. It is only meaningful
        # when the batch declares something, so when it declares nothing this
        # control says so out loud rather than passing quietly: a control that
        # reports success for "there was nothing to test" is the shape this
        # project has been bitten by before.
        if js_removed_ok:
            r5 = check(args.base, args.cand, args.repo, namespaces, verbose=False,
                       **dict(extra, js_removed_ok={}))
            why = [x['label'] for x in r5
                   if not x['ok'] and x['label'].endswith('loses only its declared lines')]
            print('  %s  NC6 an undeclared script removal fails  %s'
                  % ('ok  ' if why else 'FAIL', why[:1] or 'the rule did not fire'))
            ok &= bool(why)
        else:
            print('  %s  NC6 an undeclared script removal fails  (not applicable: '
                  'this batch declares no JS removals)' % 'ok  ')

        # NC7 -- the function-set equality is a signal. A batch that adds a
        # function it did not declare must fail, which is the only check that
        # would see a stray function on a path no captured page exercises.
        r6 = check(args.base, args.cand, args.repo, namespaces, verbose=False,
                   **dict(extra, fns=(list(args.fn or []) + ['zz_not_declared'])))
        why = [x['label'] for x in r6
               if not x['ok'] and x['label'].startswith('functions.php adds exactly')]
        print('  %s  NC7 an undeclared function in the diff fails  %s'
              % ('ok  ' if why else 'FAIL', why[:1] or 'the rule did not fire'))
        ok &= bool(why)

    print('\n%s  batch confinement' % ('PASS' if ok else 'FAIL'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
