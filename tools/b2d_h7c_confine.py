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
          expect_php='sf_formula_specs_table', tpl_line='[sf_formula_specs_table]'):
    rows = []

    def ok(label, cond, detail=''):
        rows.append({'label': label, 'ok': bool(cond), 'detail': str(detail)})
        if verbose:
            print('  %s  %-64s %s' % ('ok  ' if cond else 'FAIL', label, detail))
        return bool(cond)

    files = diff_files(base, cand, repo)
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
    ok('no page-reaching file besides the three is touched',
       set(files) <= {STYLE, PHP, TPL}, 'files=%s' % sorted(files))

    # ---- functions.php --------------------------------------------------
    removed, runs = files.get(PHP, ([], []))
    bad = [l for l in removed if not ENQUEUE_LINE.search(l)]
    ok('functions.php loses the enqueue line and nothing else',
       len(removed) == 1 and not bad,
       'removed=%d %s' % (len(removed), bad[:3] or ''))
    if removed:
        m = ENQUEUE_LINE.search(removed[0])
        ok('...and it is the old style token', bool(m) and m.group(1) == old_ver,
           'token=%r' % (m.group(1) if m else None))
    block_runs = [r for r in runs
                  if not (len(r) == 1 and ENQUEUE_LINE.search(r[0]))]
    ok('functions.php gains exactly one contiguous block', len(block_runs) == 1,
       '%d block run(s)' % len(block_runs))
    if len(block_runs) == 1:
        body = '\n'.join(block_runs[0])
        ok('and that block is the new renderer',
           expect_php in body,
           '%d lines, expects %r' % (len(block_runs[0]), expect_php))

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
    ap.add_argument('--negctl', action='store_true')
    args = ap.parse_args()

    global old_ver
    old_ver = _ver_of(args.base, args.repo)
    namespaces = tuple(args.ns) if args.ns else DEFAULT_NS
    extra = {'expect_php': args.expect_php, 'tpl_line': args.tpl_line}

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

    print('\n%s  batch H7c confinement' % ('PASS' if ok else 'FAIL'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
