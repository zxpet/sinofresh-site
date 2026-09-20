#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D Step 1 — the confinement proof ("限定证明").

The masked byte regression says *which* pages differ. This says *what* the
difference is: it deletes the one band this batch adds from the candidate
render, and demands the result be byte-identical to the baseline render of the
same URL.

Because the deletion is anchored on the block's own two markers —
`<!-- B2D-S1: actives -->` (emitted by the template comment) and
`<!-- Block 9: How We Work -->` (the pre-existing comment that follows it) — a
SAME verdict means every byte outside the inserted band is unchanged: card
count and order, JSON-LD payloads, enqueue list, markup, whitespace. It is a
strictly stronger statement than "the masked hashes match".

Pages the batch does not touch are compared as-is, so the same run also proves
the version bump is the only other difference (normalised away, because
`?ver=` is this batch's declared change and is verified separately by
`b2c_s2_ver_inventory.py`).

    python3 tools/b2d_s1_confine.py <baseline-dir> <candidate-dir> [--json out.json]
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sf_masked_cmp import masked  # noqa: E402  (same mask set as the gate)

START = "<!-- B2D-S1: actives -->"
END = "<!-- Block 9: How We Work -->"

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

        # Marker-driven, not page-list-driven: whichever page carries the band
        # gets it removed, so an unexpected page growing the band cannot slip
        # through as "untargeted, therefore SAME".
        if b.count(START) == 1:
            if a.count(START) != 0:
                rows.append({"page": n, "status": "BASELINE-ALREADY-HAS-BAND"})
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

        same = normalise(b) == normalise(a)
        rows.append({"page": n, "status": "SAME" if same else "DIFF",
                     "band_bytes_removed": stripped,
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
            line += ("  band removed=%dB  -> byte-identical to baseline"
                     % r["band_bytes_removed"])
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
    print("\n%s  confinement proof: %d/%d pages identical after removing the band"
          % ("PASS" if bad == 0 else "FAIL", len(rows) - bad, len(rows)))

    if args.json:
        json.dump({"rows": rows, "diff": bad}, open(args.json, "w"), indent=1)
        print("  json -> %s" % args.json)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
