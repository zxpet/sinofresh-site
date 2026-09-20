#!/usr/bin/env python3
"""Batch2C Step0 — end-to-end proof that a missing still yields NO <img>.

Renames uploads/2026/09/soft-chews.webp aside on the dev box, fetches the
dosage page, asserts the card grid degrades to the text-only 2B shape, and
always restores the file (try/finally) — the page is left exactly as found.

Checks, with the file absent:
  1. zero .sf-fcard__media blocks and zero <img> inside any .sf-fcard
  2. no <img ... src=""> anywhere in the grid (the failure mode the gate
     exists to prevent)
  3. card count, .sf-fcard__body count and the K1 CTA contract unchanged,
     i.e. the card is still complete and usable
  4. after restore: 4 media blocks again
"""
import re
import subprocess
import sys

HOST = "https://dev.zxpet.com"
PAGE = f"{HOST}/products/soft-chews/"
UPLOADS = "/var/www/dev.zxpet.com/public/wp-content/uploads/2026/09"
FILE = "soft-chews.webp"
ASIDE = FILE + ".b2s0held"

CARD_RE = re.compile(r'<article class="sf-fcard">(.*?)</article>', re.S)
SELF_IMG_RE = re.compile(r'<img[^>]*src=""[^>]*>')

# Two consecutive fetches of the SAME page already differ (see aa_check):
# Cloudflare rewrites every mailto into /cdn-cgi/l/email-protection#<hex> with a
# fresh token per response, and Gravity Forms stamps a random state blob plus
# per-request hidden values. None of that is ours, so a byte comparison must
# mask it first — otherwise the "restored" assertion is a guaranteed false
# negative. masks are: email-protection tokens, data-cfemail payloads, quoted
# form values >= 16 chars, and any bare base64-ish run >= 40 chars.
MASKS = [
    (re.compile(r'email-protection#[0-9a-f]+'), 'email-protection#MASK'),
    (re.compile(r'data-cfemail="[0-9a-f]+"'), 'data-cfemail="MASK"'),
    (re.compile(r"'[A-Za-z0-9+/=]{16,}'"), "'MASK'"),
    (re.compile(r'[A-Za-z0-9+/]{40,}={0,2}'), 'MASK'),
]


def masked(s):
    for pat, repl in MASKS:
        s = pat.sub(repl, s)
    return s


def aa_check():
    """A/A self-test: two fetches, no change in between, must be masked-equal."""
    a, b = fetch(), fetch()
    ok = masked(a) == masked(b)
    print(f"  {'PASS' if ok else 'FAIL'}  A/A masked self-test "
          f"({len(a)} / {len(b)} bytes)")
    if not ok:
        ha, hb = masked(a), masked(b)
        for i in range(min(len(ha), len(hb))):
            if ha[i] != hb[i]:
                print("    first diff at", i, repr(ha[i - 80:i + 40]), "VS",
                      repr(hb[i - 80:i + 40]))
                break
    return ok


fails = []


def sh(cmd):
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=15", "root@65.49.215.152", cmd],
                       capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


def fetch():
    r = subprocess.run(["curl", "-s", "-L", PAGE], capture_output=True, text=True)
    return r.stdout


def check(cond, label, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + ("  " + detail if not cond else ""))
    if not cond:
        fails.append(label)


def snapshot(tag):
    h = fetch()
    cards = CARD_RE.findall(h)
    print(f"[{tag}] bytes={len(h)} cards={len(cards)} "
          f"media={h.count('sf-fcard__media')} body={h.count('sf-fcard__body')} "
          f"cta={h.count('class=\"sf-formula__cta\"')} empty_src={len(SELF_IMG_RE.findall(h))}")
    return h, cards


def main():
    print("=== A/A self-test (masks must make two identical fetches equal) ===")
    check(aa_check(), "A/A masked self-test")

    before_h, before_cards = snapshot("before")
    before_masked = masked(before_h)
    check(len(before_cards) == 4 and before_h.count('sf-fcard__media') == 4,
          "baseline: 4 cards with 4 media blocks")

    print(f"\n--- renaming {FILE} aside on the dev box ---")
    print(sh(f"cd {UPLOADS} && mv -f {FILE} {ASIDE} && ls -la {ASIDE}"))
    try:
        h, cards = snapshot("file-absent")
        check(h.count('sf-fcard__media') == 0, "absent: zero .sf-fcard__media blocks")
        check(not any('<img' in c for c in cards), "absent: zero <img> inside any .sf-fcard")
        check(len(SELF_IMG_RE.findall(h)) == 0, "absent: no <img src=\"\"> anywhere")
        check(len(cards) == 4, "absent: card count unchanged (4)", f"got {len(cards)}")
        check(h.count('sf-fcard__body') == 4, "absent: 4 .sf-fcard__body blocks")
        check(h.count('class="sf-formula__cta"') >= 4, "absent: K1 CTA still present on every card")
        check("Joint Support Soft Chews" in h and "sf-fcard__spec" in h,
              "absent: name + spec copy still rendered")
    finally:
        print(f"\n--- restoring {FILE} ---")
        print(sh(f"cd {UPLOADS} && mv -f {ASIDE} {FILE} && ls -la {FILE}"))
        h2, c2 = snapshot("restored")
        check(h2.count('sf-fcard__media') == 4, "restored: 4 media blocks again")
        check(masked(h2) == before_masked,
              "restored: masked-identical to the pre-test render")

    print("\n=== result ===")
    if fails:
        print(f"{len(fails)} FAILURE(S): " + "; ".join(fails))
        sys.exit(1)
    print("ALL CHECKS PASS")


if __name__ == "__main__":
    main()
