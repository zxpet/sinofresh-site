#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Throw-away: print the FULL key of every element that differs between two
A/A runs, so an unstable element can be named instead of half-described."""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('g', os.path.join(HERE, 'b2d_h6_geom.py'))
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)


def norm(p):
    kept, _ = G.strip_payload(p['els'])
    els, _ = G.renumber(kept)
    return els


def main():
    a = json.load(open(sys.argv[1]))
    b = json.load(open(sys.argv[2]))
    for k in sorted(a['page']):
        ea, eb = norm(a['page'][k]), norm(b['page'][k])
        for x in ea:
            if x in eb and ea[x] != eb[x]:
                av, bv = ea[x].split('|'), eb[x].split('|')
                props = [G.PROPS[i - 1] for i in range(1, min(len(av), len(bv)))
                         if av[i] != bv[i]]
                print('%s\n  key : %s\n  base: %s\n  cand: %s\n  props: %s\n'
                      % (k, x, av[0], bv[0], props))


if __name__ == '__main__':
    main()
