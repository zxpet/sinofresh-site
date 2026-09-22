#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Throw-away: name the elements behind a geometry count difference.

A "610 -> 634" with an example of two shifted siblings says almost nothing —
the example is just the first key that moved. This prints the actual set, in
document order, so the mechanism can be named instead of guessed.
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('g', os.path.join(HERE, 'b2d_h6_geom.py'))
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)


def norm(page):
    kept, removed = G.strip_payload(page['els'])
    els, masked = G.renumber(kept)
    return els, page['nAll'] - removed, removed, len(masked)


def main():
    base = json.load(open(sys.argv[1]))
    cand = json.load(open(sys.argv[2]))
    want = sys.argv[3] if len(sys.argv) > 3 else None
    for k in sorted(base['page']):
        if want and want not in k:
            continue
        ea, na, ra, _ = norm(base['page'][k])
        eb, nb, rb, _ = norm(cand['page'][k])
        only_a = [x for x in ea if x not in eb]
        only_b = [x for x in eb if x not in ea]
        if not only_a and not only_b and na == nb:
            continue
        print('=' * 78)
        print('%s   nAll %d -> %d   (declared removals %d/%d)' % (k, na, nb, ra, rb))
        print('  present on the CANDIDATE only: %d' % len(only_b))
        for x in only_b[:30]:
            print('    + %s' % x)
        if len(only_b) > 30:
            print('    + ... %d more' % (len(only_b) - 30))
        print('  present on the BASELINE only: %d' % len(only_a))
        for x in only_a[:30]:
            print('    - %s' % x)
        if len(only_a) > 30:
            print('    - ... %d more' % (len(only_a) - 30))
        # where, in document order, does the divergence start?
        for n in range(min(len(ea), len(eb))):
            ka = [x for x in ea if x.split('|', 1)[0] == ''] # unused
            pass
        ka = sorted(ea, key=lambda x: int(x.split('|', 1)[0]))
        kb = sorted(eb, key=lambda x: int(x.split('|', 1)[0]))
        for n in range(min(len(ka), len(kb))):
            if ka[n] != kb[n]:
                print('  first divergence at ordinal %d:' % n)
                print('    base: %s' % ka[n])
                print('    cand: %s' % kb[n])
                for m in range(max(0, n - 3), min(len(kb), n + 8)):
                    print('      [%d] base=%s' % (m, ka[m] if m < len(ka) else '<end>'))
                    print('      [%d] cand=%s' % (m, kb[m] if m < len(kb) else '<end>'))
                break


if __name__ == '__main__':
    main()
