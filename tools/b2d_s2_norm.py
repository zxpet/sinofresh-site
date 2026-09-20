#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D Step 2 — fold away the one difference this batch declares.

Bumping `style.css` from 2.10.45 to 2.10.46 rewrites its <link href> on all 47
pages, so a whole-site byte comparison can never come back SAME afterwards —
the signal ("what else moved?") drowns in 47 expected diffs.

The project already has a token-folding tool, `b2c_s2_norm_attrs.py`, and it is
deliberately NOT reused here: it also deletes `data-form` / `data-sf-form`
attributes, which was right for the batch that declared them and is a pure
blind spot for this one — the K1 CTA buttons work off exactly those attributes.
A normaliser must fold only what its own batch declared.

So this one folds `?ver=<token>` and nothing else. `b2c_s2_ver_inventory.py`
then answers the complementary question — *which* tokens moved, and on which
pages — so the pair proves "the only bytes that moved are these two tokens".

    python3 tools/b2d_s2_norm.py <dir> [<dir> ...]

Rewrites each *.html in place; prints how many tokens were folded per directory.
"""

import os
import re
import sys

# WordPress quotes this markup with single quotes (<link rel='stylesheet'
# href='…?ver=2.10.46' />), so both quote styles have to be handled.
VER = re.compile(r"\?ver=[^\"'&\s]+")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    grand = 0
    for directory in sys.argv[1:]:
        if not os.path.isdir(directory):
            print("FATAL: not a directory: %s" % directory)
            return 1
        total, files = 0, 0
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".html"):
                continue
            path = os.path.join(directory, name)
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            folded = len(VER.findall(text))
            if folded:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(VER.sub("?ver=", text))
            total += folded
            files += 1
        print("  %-28s %2d files, %3d ver tokens folded" % (directory, files, total))
        grand += total

    print("\n  total folded: %d" % grand)
    if grand == 0:
        print("  WARNING: nothing was folded — the compared dirs may not be renders")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
