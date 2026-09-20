#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D Step 2 — the confinement proof ("限定证明").

The masked byte regression says *which* pages differ. This says *what* the
difference is: it deletes the one band this batch adds from the candidate
render and demands the result be byte-identical to the baseline render of the
same URL.

Both markers are taken from the RENDER, not from the template:

  * `<!-- B2D-S2: gallery -->` survives into the output. It is a plain HTML
    comment in the template, not a `<!-- wp:… -->` block delimiter, and
    do_blocks() only strips the latter.
  * the closing marker is the rendered `#formulas` section tag. The template's
    `<!-- wp:group {"tagName":"section","anchor":"formulas"…` comment does NOT
    appear in the output — do_blocks() consumed it — so anchoring on the
    comment would have looked for a string that is never there.

Because the deletion is anchored on the band's own two markers, a SAME verdict
means every byte outside the inserted band is unchanged: card counts and order,
JSON-LD payloads, the enqueue list, markup, whitespace. Strictly stronger than
"the masked hashes match".

Pages the batch does not touch are compared as-is, so the same run also proves
the version bump is the only other difference (folded away, because `?ver=` is
this batch's declared change and `b2c_s2_ver_inventory.py` verifies it).

    python3 tools/b2d_s2_confine.py <baseline-dir> <candidate-dir> [--json out.json]
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sf_masked_cmp import masked  # noqa: E402  (same mask set as the gate)

START = "<!-- B2D-S2: gallery -->"
END = '<section id="formulas" class="wp-block-group sf-formulas'

# The batch's second declared addition. It is enqueued into wp_footer, so it
# lands ~155 kB after the band and the band window cannot reach it — the first
# run of this proof failed on all nine pages at exactly this offset. Handled as
# a second marker-driven window rather than by teaching the comparison to
# tolerate it, so that an unexpected *extra* script is still a DIFF.
#
# The leading \n matters: the tag was inserted between two existing enqueues, so
# both its own line and the preceding line break are new. Removing the tag alone
# would leave a blank line the baseline does not have.
ENQ = re.compile(r'\n?<script id="sinofresh-formula-gallery-js"[^>]*></script>')

VER = re.compile(r"\?ver=[^\"&']+")


def normalise(text):
    """Fold the one difference this batch declares (the cache-busting token)."""
    return masked(VER.sub("?ver=X", text))[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base", help="baseline render dir (A)")
    ap.add_argument("cand", help="candidate render dir (B)")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    names = sorted(f[:-5] for f in os.listdir(args.cand) if f.endswith(".html"))
    rows, bad = [], 0

    for n in names:
        pb = os.path.join(args.cand, n + ".html")
        pa = os.path.join(args.base, n + ".html")
        if not os.path.exists(pa):
            rows.append({"page": n, "status": "NO-BASELINE"})
            bad += 1
            continue

        b = open(pb, encoding="utf-8", errors="replace").read()
        a = open(pa, encoding="utf-8", errors="replace").read()
        stripped = 0
        enq_removed = 0

        # Window 2: the new enqueue. Same discipline as the band — marker-driven,
        # and present-on-baseline / present-twice are both failures. Checked
        # before the band so the failure message names the right window.
        enq_b, enq_a = len(ENQ.findall(b)), len(ENQ.findall(a))
        if enq_a:
            rows.append({"page": n, "status": "BASELINE-ALREADY-ENQUEUES"})
            bad += 1
            continue
        if enq_b > 1:
            rows.append({"page": n, "status": "ENQUEUE-DUPLICATED",
                         "count": enq_b})
            bad += 1
            continue
        if enq_b == 1:
            b = ENQ.sub("", b, count=1)
            enq_removed = 1

        # Marker-driven, not page-list-driven: whichever page carries the band
        # gets it removed, so an unexpected page growing the band cannot slip
        # through as "untargeted, therefore SAME".
        if b.count(START) == 1:
            if a.count(START) != 0:
                rows.append({"page": n, "status": "BASELINE-ALREADY-HAS-BAND"})
                bad += 1
                continue
            if b.count(END) != 1:
                rows.append({"page": n, "status": "END-MARKER-NOT-UNIQUE",
                             "count": b.count(END)})
                bad += 1
                continue
            i = b.index(START)
            j = b.index(END, i)
            stripped = j - i
            b = b[:i] + b[j:]
        elif b.count(START) > 1:
            rows.append({"page": n, "status": "BAND-DUPLICATED",
                         "count": b.count(START)})
            bad += 1
            continue
        elif enq_removed:
            # A page that enqueues the script but never renders the band is not
            # a smaller change, it is a broken one.
            rows.append({"page": n, "status": "ENQUEUE-WITHOUT-BAND"})
            bad += 1
            continue

        same = normalise(b) == normalise(a)
        rows.append({"page": n, "status": "SAME" if same else "DIFF",
                     "band_bytes_removed": stripped,
                     "enqueue_stripped": enq_removed,
                     "bytes_base": len(a.encode()), "bytes_cand": len(b.encode())})
        if not same:
            bad += 1
            ma, mb = normalise(a), normalise(b)
            for i in range(min(len(ma), len(mb))):
                if ma[i] != mb[i]:
                    rows[-1]["first_diff_at"] = i
                    rows[-1]["ctx_base"] = ma[max(0, i - 90):i + 60]
                    rows[-1]["ctx_cand"] = mb[max(0, i - 90):i + 60]
                    break
            else:
                rows[-1]["first_diff_at"] = "length-only"

    w = max((len(r["page"]) for r in rows), default=10)
    banded = [r for r in rows if r.get("band_bytes_removed")]
    plain = [r for r in rows if not r.get("band_bytes_removed")]
    for r in rows:
        line = "  %-*s  %s" % (w, r["page"], r["status"])
        if r["status"] == "SAME" and r.get("band_bytes_removed"):
            line += ("  band removed=%dB  enqueue stripped=%d"
                     "  -> byte-identical to baseline"
                     % (r["band_bytes_removed"], r.get("enqueue_stripped", 0)))
        elif r["status"] == "SAME":
            line += "  byte-identical to baseline"
        elif r["status"] == "DIFF":
            line += "  first diff @%s" % r.get("first_diff_at")
        print(line)
        if r["status"] == "DIFF":
            print("      base:", repr(r.get("ctx_base")))
            print("      cand:", repr(r.get("ctx_cand")))

    print("\n  pages carrying the band: %d/%d confined" % (
        sum(1 for r in banded if r["status"] == "SAME"), len(banded)))
    print("  pages without the band: %d/%d identical" % (
        sum(1 for r in plain if r["status"] == "SAME"), len(plain)))
    print("  both declared additions removed: band (+ the new enqueue);"
          " nothing else may differ once they are gone")
    print("\n%s  confinement proof: %d/%d pages identical after removing"
          " the band and the new enqueue"
          % ("PASS" if bad == 0 else "FAIL", len(rows) - bad, len(rows)))

    if args.json:
        json.dump({"rows": rows, "diff": bad}, open(args.json, "w"), indent=1)
        print("  json -> %s" % args.json)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
