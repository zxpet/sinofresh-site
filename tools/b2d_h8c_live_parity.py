#!/usr/bin/env python3
"""Batch H8c — does what dev SERVES now equal the bytes the gate validated?

The gate proved that the theme a pull would install transforms the old live
pages into exactly the pages the preflight layer already served. That proof is
about files. This one is about the install: it fetches the same path list with
no preflight header, from the docroot the site answers from, and compares page
by page against the preflight capture the gate signed off on.

One licence is granted, and it is named in the output rather than quietly
applied: the preflight layer serves the theme from a directory with a different
name, so `sinofresh-theme-preflight` is folded to `sinofresh-theme` on the
preflight side. Nothing else is normalised. Both sides go through the same
mask the gate uses for the values that are per-request by design (analytics hit
ids and signatures, the generation blob), so a page that differs after masking
differs for a reason the batch has to explain.

`mask()` returns (text, count) — comparing the tuples, or reading the count as
the text, is the trap this file exists not to fall into. It compares text[0]
and reports the count separately, because a differing count with identical text
would mean the two captures masked a different number of things.
"""

import argparse
import glob
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load_gate():
    spec = importlib.util.spec_from_file_location(
        'gate', os.path.join(HERE, 'b2d_h7_gate.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def firstdiff(a, b):
    """Offset of the first differing character, or -1 when equal."""
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return -1 if len(a) == len(b) else n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pre', required=True, help='the preflight capture')
    ap.add_argument('--live', required=True, help='the capture taken after the pull')
    ap.add_argument('--pre-new', help='the four new routes, preflight side')
    ap.add_argument('--live-new', help='the four new routes, served side')
    ap.add_argument('--show', type=int, default=5)
    ap.add_argument('--json', metavar='OUT')
    args = ap.parse_args()

    gate = load_gate()

    def masked(path):
        t = gate.read(path).replace('sinofresh-theme-preflight',
                                    'sinofresh-theme')
        return gate.mask(t)

    def compare(pre_dir, live_dir, label):
        names = sorted(os.path.basename(p)
                       for p in glob.glob(os.path.join(pre_dir, '*.html')))
        rows, same = [], 0
        for name in names:
            pt, pn = masked(os.path.join(pre_dir, name))
            lt, ln = masked(os.path.join(live_dir, name))
            row = {'page': name, 'identical': pt == lt,
                   'bytes_pre': len(pt), 'bytes_live': len(lt),
                   'masks_pre': pn, 'masks_live': ln}
            if pt == lt:
                same += 1
            else:
                i = firstdiff(pt, lt)
                row['first_diff'] = i
                row['pre_ctx'] = pt[max(0, i - 110):i + 110]
                row['live_ctx'] = lt[max(0, i - 110):i + 110]
            rows.append(row)
        print(f'{label}: {len(names)} pages, identical={same}, '
              f'differing={len(names) - same}')
        shown = 0
        for r in rows:
            if r['identical'] or shown >= args.show:
                continue
            shown += 1
            print(f"   DIFF {r['page']}  masks {r['masks_pre']}/{r['masks_live']}"
                  f"  first diff @{r['first_diff']}")
            print(f"      pre : {r['pre_ctx']!r}")
            print(f"      live: {r['live_ctx']!r}")
        return rows

    out = {}
    out['pages'] = compare(args.pre, args.live, 'the 75-page path list')
    if args.pre_new and args.live_new:
        out['pages_new'] = compare(args.pre_new, args.live_new,
                                   'the four new routes')
    bad = [r['page'] for k in ('pages', 'pages_new')
           for r in out.get(k, []) if not r['identical']]
    out['ok'] = not bad
    out['differing'] = bad
    print('\nTOTAL differing: %d %s' % (len(bad), bad[:12]))
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print('   json -> %s' % args.json)
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
