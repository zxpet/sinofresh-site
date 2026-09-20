#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch2C Step2 sub-item 5 — normalise the ONE difference this batch adds.

Sub-item 5 appends a single centred paragraph to each of the eight dosage-form
page templates:

  <!-- wp:paragraph {"align":"center", ...margin top spacing 40...} -->
  <p class="has-text-align-center" ...><a class="sf-explore__btn" href="/formulas/">Browse All Formulas →</a></p>
  <!-- /wp:paragraph -->

Rendered, that lands between the formula grid's `</div>` and the section's
`</section>`, wrapped in the blank lines WordPress emits around a block:

  candidate : </div> \\n\\n\\n <p …></p> \\n\\n </section>
  baseline  : </div> \\n\\n </section>

So the normaliser deletes the paragraph together with the *leading* blank run;
the trailing blank run is exactly the one the baseline already had. The result
is byte-identical to the baseline render — which is the proof that in these
eight pages NOTHING ELSE moved: same cards, same order, same JSON-LD, same
enqueues, same grid markup.

Anything the pattern does not match survives into the comparator and still
shows as DIFF, so a second stray edit cannot hide behind this.

  python3 tools/b2c_s2s5_norm.py <in-dir> <out-dir> [--expect none]

Prints, per file, how many times the pattern fired. The default policy is the
candidate's: exactly 1 hit on each of the eight dosage pages, 0 elsewhere — a
miss there is a FAIL. Pass `--expect none` for the baseline capture, where the
pattern must not fire anywhere; that asymmetry is itself part of the evidence
(the link really is new).

Pre-flight-only tool; it is not part of the site.
"""

import os
import re
import sys

PARA = (
    r'\n{2,}<p class="has-text-align-center wp-block-paragraph" '
    r'style="margin-top:var\(--wp--preset--spacing--40\)">'
    r'<a class="sf-explore__btn" href="/formulas/">Browse All Formulas →</a></p>'
)
PATTERN = re.compile(PARA)

FORMS = ["soft-chews", "tablets", "powders", "pastes",
         "drops", "liquids", "fish-oil", "dental-chews"]
# pages that must carry the new link
WANT_ONE = {"products-" + f for f in FORMS}


def main():
    argv = sys.argv[1:]
    policy = "one"
    if "--expect" in argv:
        i = argv.index("--expect")
        policy = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
    args = argv
    if len(args) != 2 or policy not in ("one", "none"):
        sys.exit(__doc__)
    src, dst = args
    want_one = WANT_ONE if policy == "one" else set()
    os.makedirs(dst, exist_ok=True)
    bad = 0
    for name in sorted(os.listdir(src)):
        if not name.endswith(".html"):
            continue
        slug = name[:-5]
        raw = open(os.path.join(src, name), encoding="utf-8").read()
        out, hits = PATTERN.subn("", raw)
        expect = 1 if slug in want_one else 0
        ok = hits == expect
        if not ok:
            bad += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {slug:<42} hits={hits} expect={expect}")
        open(os.path.join(dst, name), "w", encoding="utf-8").write(out)
    print(f"\n{'PASS' if bad == 0 else 'FAIL'}  normalised {len(os.listdir(dst))} pages "
          f"(policy={policy}), {bad} unexpected hit count(s)")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
