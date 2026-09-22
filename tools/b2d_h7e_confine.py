#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7e — the confinement proof for a batch that adds no CSS and no script.

WHY THIS IS NOT b2d_h7c_confine.py, AND WHY THAT IS NOT DUPLICATION

H7c's proof is shaped like H7c: it asserts that style.css gains EXACTLY ONE
CONTIGUOUS BLOCK, that every selector opened inside that block names the
batch's namespace, and that functions.php's additions are one contiguous run.
Those are the right claims for a batch whose whole product is a new band of
styled markup. They are the wrong claims here, and not marginally:

  * H7e adds no CSS rule at all. Its style.css diff is the version header and
    one line of it. H7c's "exactly one contiguous block" assertion reads
    `len(block_runs) == 1` and would report that as FAIL — correctly, for H7c's
    claim, and pointlessly for this one.
  * H7c asserts PHP's additions are contiguous. H7e's functions.php changes in
    FOUR separate places (the enqueue, the renderer's doc table, the renderer's
    body, the defaults array), so contiguity is not the shape of the edit and
    asserting it would be asserting a property the batch has no reason to have.
  * and H7e puts its new code in two files H7c's proof has never heard of.

What both batches need is the SAME underlying claim, stated in the terms of the
file it is about: NOTHING CHANGED THAT THE DECLARATION DOES NOT NAME. For a
file whose bytes never reach a page — every one of the four here — that claim
is the only proof there is, because the byte gate compares pages and a page is
not a stylesheet, a script envelope, or a settings page. An edit to an existing
rule, or a function added beside the declared one, leaves all 75 captured pages
byte-identical and still ships.

So the claim is written out per file, and it is deliberately over-specified:

  * the FILE SET is compared for equality, so a fifth file is caught;
  * the REMOVALS are compared line for line, so a sixth deleted line is caught;
  * the ADDITIONS are compared as the list of run SIZES, so the shape of every
    added block is pinned even though its content is free;
  * and the FUNCTION NAMES are compared for equality on both sides, so a
    function added anywhere in a file cannot hide behind a diff that happens to
    be the right size.

The last one is the one that matters most here, and it is the reason a size
check alone would not do. H7e's product is two new functions and two new
settings fields; a batch that also slipped a third function into
inc/formula-admin.php while keeping the run sizes plausible would pass every
byte comparison in the gate. It cannot pass this.

usage:
    b2d_h7e_confine.py --base SHA --cand SHA [--repo DIR] [--negctl]

Both SHAs are required and neither has a default: a confinement proof run
against the wrong range is a proof of nothing, printed as a row of green ticks.
"""

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

STYLE = 'sinofresh-theme/style.css'
PHP   = 'sinofresh-theme/functions.php'
POOLS = 'sinofresh-theme/inc/formula-pools.php'
ADMIN = 'sinofresh-theme/inc/formula-admin.php'

# The only four theme files this batch may touch. Compared for EQUALITY.
OWNED = (STYLE, PHP, POOLS, ADMIN)

FN_DECL = re.compile(r'^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(', re.M)

# ---------------------------------------------------------------- declarations

# style.css: the version header, and not one CSS byte. Both sides are stated
# EXACTLY, as lists of lines, because "one line changed in style.css" is the
# claim and a regex that merely matched `Version:` would accept a header
# rewritten on a different line, in a different case, beside a stray rule.
STYLE_REMOVED = ['Version: 2.10.65']
STYLE_ADDED = [['Version: 2.10.66']]

# functions.php: seven deleted lines, five added runs, and no function gained
# or lost. The deletions are listed character for character — including the
# leading tabs — so that a sixth removal, or the same removal at a different
# indent, is a FAIL and not a rounding error.
PHP_REMOVED = [
    "\twp_enqueue_style('sinofresh-style', get_stylesheet_uri(), array(), '2.10.65');",
    " *   Place of Origin    hard-coded, until batch H7e moves it to Site Settings",
    " *   OEM / ODM          hard-coded, until batch H7e moves it to Site Settings",
    "\t/* Batch H7e moves both of these to Site Settings. Until then they are",
    "\t   constants, and a constant is still a value the page can prove. */",
    "\t$rows['Place of Origin'] = esc_html('Linyi, Shandong, China');",
    "\t$rows['OEM / ODM'] = esc_html('Available');",
]
PHP_RUN_LENGTHS = [1, 3, 16, 8, 4]

# inc/formula-pools.php: additions only, one run, one new function.
POOLS_FNS = {'sf_formula_factory_value'}
POOLS_RUN_LENGTHS = [28]

# inc/formula-admin.php: additions only, four runs, one new function.
ADMIN_FNS = {'sf_render_factory_info_page'}
ADMIN_RUN_LENGTHS = [5, 14, 4, 46]


def run(cmd, cwd=None, timeout=180):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or ''), (p.stderr or '')


def diff_files(base, cand, repo):
    """{path: (removed_lines, added_runs)} for the range, theme directory only.

    -U0 so that "a run" means a contiguous run: with no context a run ends at
    the first line that is neither added nor a hunk header, which is what makes
    the run sizes in the declaration mean what they say.
    """
    rc, out, err = run(['git', '-C', repo, 'diff', '--no-color', '-U0',
                        base, cand, '--', 'sinofresh-theme/'], timeout=180)
    if rc != 0:
        raise SystemExit('FATAL git diff %s..%s: %s' % (base, cand, err[:300]))
    files, cur, removed, runs, run_ = {}, None, [], [], None
    for line in out.splitlines():
        if line.startswith('diff --git '):
            if cur:
                files[cur] = (removed, runs)
            cur, removed, runs, run_ = None, [], [], None
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


def changed_names(base, cand, repo):
    """Every path the range touches, at any depth — not just the theme's.

    The theme files get the strict claims; everything else is reported so the
    reader can see what the batch committed beside its code, which is how a
    document commit gets noticed instead of being mistaken for a theme edit.
    """
    rc, out, _ = run(['git', '-C', repo, 'diff', '--name-only', base, cand], timeout=180)
    if rc != 0:
        raise SystemExit('FATAL git diff --name-only %s..%s' % (base, cand))
    return {l for l in out.splitlines() if l.strip()}


def show(sha, path, repo):
    rc, out, err = run(['git', '-C', repo, 'show', '%s:%s' % (sha, path)], timeout=180)
    if rc != 0:
        raise SystemExit('FATAL git show %s:%s — %s' % (sha, path, err[:200]))
    return out


def fns_in(blob):
    return set(FN_DECL.findall(blob))


def fn_sets(base, cand, repo, paths):
    return {p: (fns_in(show(base, p, repo)), fns_in(show(cand, p, repo))) for p in paths}


def judge(files, names, fns, verbose=True):
    """The confinement claim, over an already-parsed diff.

    Separated from the git read on purpose: every control below hands this
    function a mutant, and a control that had to build a real repository to
    test one assertion would be a control nobody runs. What it must NOT be is
    injectable for the real run — the caller below computes `files`, `names`
    and `fns` from the commits and nothing else.
    """
    rows = []

    def ok(label, cond, detail=''):
        rows.append({'label': label, 'ok': bool(cond), 'detail': str(detail)})
        if verbose:
            print('  %s  %-66s %s' % ('ok  ' if cond else 'FAIL', label, detail))
        return bool(cond)

    theme_files = {n for n in names if n.startswith('sinofresh-theme/')}
    other = sorted(n for n in names if n not in theme_files)
    ok('the batch touches the four declared theme files and no others',
       theme_files == set(OWNED),
       'theme=%s | also committed=%s' % (sorted(theme_files), other[:5] or 'nothing'))
    # The file set is read TWICE — once from `git diff --name-only`, once from
    # the -U0 parse that produces every per-file claim below — and the two must
    # agree. NC7 passed the first time this ran, and this is why: the fifth-file
    # mutant was built into the parse and not into the name list, the equality
    # above never saw it, and the proof reported a file it had not been told
    # about as fine. A cross-check is the missing assertion, and it is cheap:
    # if the two readings disagree, one of them dropped or invented a file and
    # every claim below is about a file set nobody can name.
    ok('the two readings of the file set agree',
       set(files) == theme_files,
       'parsed=%s named=%s' % (sorted(files), sorted(theme_files)))

    # ---- style.css: the version header, and not one CSS byte -------------
    rm, runs = files.get(STYLE, ([], []))
    ok('style.css is in the diff at all', STYLE in files)
    ok('style.css deletes the old version header and only it',
       rm == STYLE_REMOVED, 'removed=%r' % (rm,))
    ok('...and adds back the new header and nothing else',
       runs == STYLE_ADDED, 'runs=%r' % (runs,))

    # ---- functions.php: the swap, with no function gained or lost ---------
    rm, runs = files.get(PHP, ([], []))
    ok('functions.php deletes exactly the seven declared lines',
       sorted(rm) == sorted(PHP_REMOVED),
       'removed=%d undeclared=%s' % (len(rm), sorted(set(rm) - set(PHP_REMOVED))[:3] or 'none'))
    ok('...and adds back five runs of exactly the declared sizes',
       [len(r) for r in runs] == PHP_RUN_LENGTHS,
       'run sizes=%r want %r' % ([len(r) for r in runs], PHP_RUN_LENGTHS))
    fb, fc = fns.get(PHP, (set(), set()))
    ok('...and neither declares nor loses a function',
       fb == fc, 'base=%d cand=%d gained=%s lost=%s'
       % (len(fb), len(fc), sorted(fc - fb)[:3] or 'none', sorted(fb - fc)[:3] or 'none'))

    # ---- inc/formula-pools.php: the reader, added ------------------------
    rm, runs = files.get(POOLS, ([], []))
    ok('formula-pools.php only gains — not a character is deleted',
       POOLS in files and rm == [], 'removed=%d' % len(rm))
    ok('...in one run of the declared size',
       [len(r) for r in runs] == POOLS_RUN_LENGTHS,
       'run sizes=%r want %r' % ([len(r) for r in runs], POOLS_RUN_LENGTHS))
    fb, fc = fns.get(POOLS, (set(), set()))
    ok('...and the set of functions it declares grows by the reader, exactly',
       (fc - fb) == POOLS_FNS and not (fb - fc),
       'gained=%s lost=%s' % (sorted(fc - fb), sorted(fb - fc)))

    # ---- inc/formula-admin.php: the page, added --------------------------
    rm, runs = files.get(ADMIN, ([], []))
    ok('formula-admin.php only gains — not a character is deleted',
       ADMIN in files and rm == [], 'removed=%d' % len(rm))
    ok('...in four runs of the declared sizes',
       [len(r) for r in runs] == ADMIN_RUN_LENGTHS,
       'run sizes=%r want %r' % ([len(r) for r in runs], ADMIN_RUN_LENGTHS))
    fb, fc = fns.get(ADMIN, (set(), set()))
    ok('...and the set of functions it declares grows by the page, exactly',
       (fc - fb) == ADMIN_FNS and not (fb - fc),
       'gained=%s lost=%s' % (sorted(fc - fb), sorted(fb - fc)))

    passed = all(r['ok'] for r in rows)
    if verbose:
        print('  %s  confinement: nothing changed that the declaration does not name'
              % ('PASS' if passed else 'FAIL'))
    return passed, rows


def negctl(base, cand, repo, verbose=True):
    """Each control must break the claim, and each must actually have changed
    something. Same discipline as the gate's matrix: a mutant that changes
    nothing is reported INVALID rather than counted as a caught one."""
    real = diff_files(base, cand, repo)
    names = changed_names(base, cand, repo)
    fns = fn_sets(base, cand, repo, (PHP, POOLS, ADMIN))
    rows = []

    def report(label, verdict, why=''):
        rows.append({'label': label, 'verdict': verdict, 'why': why})
        if verbose:
            print('  %-58s %-8s %s' % (label, verdict, why))

    def control(label, files=None, names_=None, fns_=None):
        f = dict(real) if files is None else files
        n = names if names_ is None else names_
        s = dict(fns) if fns_ is None else fns_
        changed = (f != real) or (n != names) or (s != fns)
        passed, _ = judge(f, n, s, verbose=False)
        if not changed:
            report(label, 'INVALID', 'the mutant changed nothing')
            return False
        if passed:
            report(label, 'PASSED', 'the proof let this through')
            return False
        report(label, 'caught', '')
        return True

    ok = True

    # NC1 — the batch grows a CSS rule. It has none, so this is the exact
    # failure the style.css claim exists for: a second run beside the header.
    f = dict(real)
    f[STYLE] = (list(STYLE_REMOVED), [list(STYLE_ADDED[0]), ['.sf-header-inner { color: red; }']])
    ok &= control('NC1 a stray CSS rule is caught', files=f)

    # NC2 — and a rule that already existed goes away. Same file, same size
    # diff, opposite direction: only the line-for-line removal check sees it.
    f = dict(real)
    f[STYLE] = (STYLE_REMOVED + ['\tcolor: red;'], [list(STYLE_ADDED[0])])
    ok &= control('NC2 a deleted existing CSS rule is caught', files=f)

    # NC3 — a sixth run in functions.php. The deletions are untouched and each
    # run is still plausible; only the run-size list notices.
    f = dict(real)
    rm, runs = f[PHP]
    f[PHP] = (list(rm), [list(r) for r in runs] + [['\t/* stray */']])
    ok &= control('NC3 a sixth added run in functions.php is caught', files=f)

    # NC4 — an undeclared deletion in functions.php.
    f = dict(real)
    rm, runs = f[PHP]
    f[PHP] = (list(rm) + ['\t$foo = 1;'], [list(r) for r in runs])
    ok &= control('NC4 an undeclared deletion in functions.php is caught', files=f)

    # NC5 — THE FUNCTION-SET CLAIM ITSELF, and the reason it is here: a third
    # function slipped into formula-admin.php at a line count that keeps the
    # run sizes indistinguishable. Every byte in the gate stays green; this is
    # the only assertion that can see it. Built by moving the DECLARED set, so
    # the control tests the comparison rather than a string match.
    f = dict(real)
    s = dict(fns)
    fb, fc = s[ADMIN]
    s[ADMIN] = (fb, fc | {'sf_something_else'})
    ok &= control('NC5 an undeclared function in formula-admin.php is caught', files=f, fns_=s)

    # NC6 — and the same for a function that leaves functions.php.
    f = dict(real)
    s = dict(fns)
    fb, fc = s[PHP]
    s[PHP] = (fb, fc - {'sinofresh_formula_specs_table'})
    ok &= control('NC6 a function lost from functions.php is caught', files=f, fns_=s)

    # NC7 — a fifth file, reported by BOTH readings. This is the file-set claim,
    # and it is the cheapest way for a batch to ship something nobody declared.
    f = dict(real)
    n = set(names)
    f['sinofresh-theme/inc/extra.php'] = ([], [['<?php', '// stray']])
    n.add('sinofresh-theme/inc/extra.php')
    ok &= control('NC7 a fifth theme file is caught', files=f, names_=n)

    # NC8 — and a fifth file reported by only ONE reading, which is what a
    # parser that dropped or invented a hunk looks like. This is the control
    # that was missing when NC7 first passed; it is the reason the cross-check
    # above exists rather than being assumed.
    f = dict(real)
    f['sinofresh-theme/inc/extra.php'] = ([], [['<?php', '// stray']])
    ok &= control('NC8 a file seen by one reading and not the other is caught', files=f)

    if verbose:
        print('  %s  negative controls: every control that must fail, failed'
              % ('PASS' if ok else 'FAIL'))
    return ok, rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--cand', required=True)
    ap.add_argument('--repo', default=ROOT)
    ap.add_argument('--negctl', action='store_true')
    ap.add_argument('--json')
    args = ap.parse_args(argv)

    print('== H7e confinement: %s..%s ==' % (args.base[:9], args.cand[:9]))
    files = diff_files(args.base, args.cand, args.repo)
    names = changed_names(args.base, args.cand, args.repo)
    fns = fn_sets(args.base, args.cand, args.repo, (PHP, POOLS, ADMIN))

    ok, rows = judge(files, names, fns)
    out = {'base': args.base, 'cand': args.cand, 'rows': rows}

    if args.negctl:
        print('== named negative controls ==')
        nok, nrows = negctl(args.base, args.cand, args.repo)
        out['negctl'] = nrows
        ok &= nok

    print('\n%s  H7e confinement' % ('PASS' if ok else 'FAIL'))
    if args.json:
        import json
        json.dump(out, open(args.json, 'w'), indent=1)
        print('  json -> %s' % args.json)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
