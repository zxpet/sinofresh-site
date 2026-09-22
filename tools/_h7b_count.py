#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print (pages, total) for a list of literal needles across a capture dir.

A throwaway measuring stick for writing a declaration: the counts a batch
declares have to come from a measurement, not from an expectation. Reads only.
"""
import os
import sys

PATTERNS = [
    'href="/contact/#quote" data-sf-inquiry-open',
    'href="/zh/contact/#quote" data-sf-inquiry-open',
    'href="/contact/#quote"',
    'href="/zh/contact/#quote"',
    'sf-formula__cta--solid',
    'data-sf-inquiry-open',
    'class="sf-formula__cta sf-formula__cta--solid"',
    'data-form="',
    'data-sf-inquiry-open>Send Inquiry</a>',
    '?ver=2.10.63',
    '?ver=2.10.62',
    'formulas.js?ver=1.3.0',
    'inquiry.js?ver=1.1.0',
    'Reference this formula',
    'class="sf-formula__cta"',
    'sf-formula-hero__actions',
    'sf-quote-cta',
    'class="sf-inquiry-modal"',
    'sf-float-btn--inquiry',
    'sf-fdetail2__title',
]


def main():
    d = sys.argv[1]
    files = sorted(f for f in os.listdir(d) if f.endswith('.html'))

    def rd(f):
        with open(os.path.join(d, f), encoding='utf-8', errors='replace') as fh:
            return fh.read()

    text = {f: rd(f) for f in files}
    print('== %s (%d pages) ==' % (d, len(files)))
    for p in PATTERNS:
        tot = sum(t.count(p) for t in text.values())
        pg = sum(1 for t in text.values() if p in t)
        print('  %-52s pages=%-3d tot=%d' % (p, pg, tot))


if __name__ == '__main__':
    main()
