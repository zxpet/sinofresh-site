#!/usr/bin/env python3
"""H6 Step 0 — the PHP shortcode and JS asset inventory. Read only.

Two of H6's items are "a thing was deregistered or deleted; is its other half
still here?". Both have the same trap: the half that survives is defined in one
place and used in another, so counting definitions or counting usages alone
answers nothing. Each is reported with both sides.

  A. shortcodes: every `add_shortcode('tag', ...)` against every `[tag` usage
     in the block templates AND in the rendered capture. A shortcode used
     nowhere is dead; a shortcode used but not registered is a live bug, which
     is why the two directions are printed separately.

  B. scripts and styles: every file in assets/js and assets/css against the
     enqueue calls in functions.php. A file nobody enqueues cannot run.

The rendered capture is the tiebreaker for A: a shortcode can be used from
stored post content, which no template grep would see.

Usage: python3 tools/b2d_h6_inventory.py [--theme sinofresh-theme] [--pages DIR]
"""

import argparse
import os
import re
import sys

SHORTCODE_DEF = re.compile(r"add_shortcode\(\s*'([a-z0-9_]+)'")
ENQUEUE_CALL = re.compile(
    r"(?:wp_enqueue_script|wp_enqueue_style|wp_register_script|wp_register_style)\s*\(\s*"
    r"'([^']+)'(.*?)\)\s*;", re.S)
ASSET_IN_ARGS = re.compile(r"['\"](?:assets|/assets)/(js|css)/([A-Za-z0-9._-]+)")


def walk(root, exts):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in ('_backup', '_backup_x', 'screenshots', '.git')]
        for name in sorted(filenames):
            if os.path.splitext(name)[1].lower() in exts:
                yield os.path.join(dirpath, name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--theme', default='sinofresh-theme')
    ap.add_argument('--pages', default='_backup/b2d-h5-candidates')
    args = ap.parse_args()

    theme = args.theme
    funcs = os.path.join(theme, 'functions.php')
    if not os.path.isfile(funcs):
        sys.exit('no functions.php at %s' % funcs)
    src = open(funcs, encoding='utf-8', errors='replace').read()

    print('#' * 78)
    print('# A. shortcodes')
    print('#' * 78)
    defined = sorted(set(SHORTCODE_DEF.findall(src)))
    print('registered in functions.php: %d' % len(defined))

    # Usage in every block template the theme can render, which is both
    # `templates/` and `parts/` -- the H4 capsule lives in parts/footer.html, so
    # a scan of templates/ alone reports a live shortcode as dead.
    tpl_hits = {}
    for sub in ('templates', 'parts'):
        d = os.path.join(theme, sub)
        if not os.path.isdir(d):
            continue
        for path in walk(d, {'.html'}):
            raw = open(path, encoding='utf-8', errors='replace').read()
            for tag in defined:
                if '[' + tag in raw or '[ ' + tag in raw:
                    tpl_hits.setdefault(tag, []).append(
                        '%s/%s' % (sub, os.path.basename(path)))

    # A shortcode can also be called from PHP, but only through do_shortcode().
    # Scanning .php for a bare `[tag` self-matches the registration file: the
    # docblock, shortcode_atts' third argument and add_shortcode itself all name
    # the tag, so every shortcode reads "used" and the dead ones hide. Only a
    # do_shortcode() call is a call site.
    for path in walk(theme, {'.php'}):
        raw = open(path, encoding='utf-8', errors='replace').read()
        for m in re.finditer(r'do_shortcode\(\s*[\'"](.*?)[\'"]', raw, re.S):
            for tag in defined:
                if '[' + tag in m.group(1):
                    tpl_hits.setdefault(tag, []).append(
                        'do_shortcode@' + os.path.basename(path))

    # Anything left as a literal [tag in the rendered output is a shortcode that
    # FAILED to expand -- a bug indicator, not a usage count.
    page_hits = {}
    if os.path.isdir(args.pages):
        for path in walk(args.pages, {'.html'}):
            raw = open(path, encoding='utf-8', errors='replace').read()
            for tag in defined:
                if '[' + tag in raw:
                    page_hits[tag] = page_hits.get(tag, 0) + 1

    dead, live = [], []
    for tag in defined:
        t, p = tpl_hits.get(tag, []), page_hits.get(tag, 0)
        if t or p:
            live.append((tag, len(t), p))
        else:
            dead.append(tag)

    print('used somewhere : %d' % len(live))
    for tag, nt, np in live:
        print('   %-34s templates=%-3d rendered_pages=%d' % (tag, nt, np))
    print()
    print('USED NOWHERE   : %d' % len(dead))
    for tag in dead:
        print('   %s' % tag)
    print()

    # The other direction: a shortcode in use that nothing registered would
    # render as literal text on the page.
    registered = set(defined)
    unregistered = set()
    for sub in ('templates', 'parts'):
        d = os.path.join(theme, sub)
        if not os.path.isdir(d):
            continue
        for path in walk(d, {'.html'}):
            raw = open(path, encoding='utf-8', errors='replace').read()
            for m in re.finditer(r'\[([a-z][a-z0-9_]{3,})\]', raw):
                if m.group(1) not in registered:
                    unregistered.add(m.group(1))
    if unregistered:
        print('LIVE BUG -- bracket tags in templates with no registration:')
        for tag in sorted(unregistered):
            print('   [%s]' % tag)
    else:
        print('no unregistered [bracket-tag] survives in the templates')
    print()

    print('#' * 78)
    print('# B. assets')
    print('#' * 78)
    on_disk = {}
    for sub in ('js', 'css'):
        d = os.path.join(theme, 'assets', sub)
        if os.path.isdir(d):
            for name in sorted(os.listdir(d)):
                if name.endswith('.' + sub):
                    on_disk[name] = sub

    enq_paths, enq_all = set(), {}
    for m in ENQUEUE_CALL.finditer(src):
        handle, rest = m.group(1), m.group(2)
        enq_all[handle] = rest.strip().splitlines()[0][:60]
        for a in ASSET_IN_ARGS.finditer(rest):
            enq_paths.add(a.group(2))

    print('files on disk: %d   enqueue calls: %d' % (len(on_disk), len(enq_all)))
    print()
    print('enqueue call sites in functions.php:')
    for h in sorted(enq_all):
        print('   %-28s %s' % (h, enq_all[h].replace('\t', ' ')))
    print()
    orphans = [n for n in sorted(on_disk) if n not in enq_paths]
    print('ASSETS ON DISK WITH NO ENQUEUE: %d' % len(orphans))
    for n in orphans:
        print('   assets/%s/%s' % (on_disk[n], n))
    print()
    missing = [p for p in sorted(enq_paths)
               if not os.path.isfile(os.path.join(theme, 'assets', on_disk.get(p, ''), p))
               and p not in on_disk]
    print('ENQUEUED PATHS WITH NO FILE: %d' % len(missing))
    for p in missing:
        print('   %s' % p)


if __name__ == '__main__':
    main()
