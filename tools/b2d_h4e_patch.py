#!/usr/bin/env python3
"""Batch H4e (email prerequisite) — the theme-side swap, info@ -> sales@.

One anchor per occurrence, located by structure rather than line number
so that the tool keeps working if the files around them move. Each anchor must
appear exactly once before the edit and zero times after it, and the file is
read back from disk inside the same process to prove the write landed.

--check prints the plan and changes nothing; --apply performs it. Nothing here
touches the database — the option and the three legal pages are a separate tool
(b2d_h4e_dbpatch.php) because they need a snapshot for rollback.

usage:
    b2d_h4e_patch.py --check
    b2d_h4e_patch.py --apply
"""
import argparse
import pathlib
import subprocess
import sys

THEME = pathlib.Path(__file__).resolve().parent.parent / "sinofresh-theme"
OLD = "info@zxpet.com"
NEW = "sales@zxpet.com"

# (relative path, anchor containing OLD, what this occurrence drives)
EDITS = [
    ("functions.php",
     "\t\t'sf_contact_email'    => '" + OLD + "',",
     "the sf_contact_email default — feeds the top bar, the footer contact line, "
     "the floating email button and the Organization schema"),
    ("functions.php",
     "\t\t\treturn ($v !== '') ? $v : '" + OLD + "';",
     "the sanitize_callback fallback for sf_contact_email"),
    ("functions.php",
     "\t\t'email'        => get_option('sf_contact_email', '" + OLD + "'),",
     "the Organization schema email fallback"),
    ("functions.php",
     "\t\t$lines[] = '" + OLD + " \u00b7 +86 539 866 9539 \u00b7 zxpet.com';",
     "the certificate email signature the customer receives"),
    ("inc/config-pdf.php",
     "\t\t. '<li><strong>Request samples</strong><br>" + OLD
     + " &middot; +86 539 866 9539</li>'",
     "the configurator PDF footer (samples)"),
    ("inc/config-pdf.php",
     "\t\t. '<li><strong>Request a sample</strong><br>" + OLD
     + " &middot; +86 539 866 9539</li>'",
     "the configurator PDF footer (single sample)"),
    ("inc/cert-download.php",
     "Please email " + OLD + ".",
     "the 404 message a visitor sees when a certificate link has expired"),
    ("templates/page-contact.html",
     '<p><a href="mailto:' + OLD + '">' + OLD + "</a></p>",
     "the contact page's visible address and its mailto"),
    ("tools/make_coa_sample.php",
     " &middot; www.zxpet.com &middot; " + OLD + "'",
     "the COA generator's footer — customer-facing, though not served by the site "
     "(found on the second pass: the first scan's file list stopped at "
     "functions.php/style.css/assets/inc/templates/parts/patterns and missed tools/)"),
]

PHP_FILES = ["functions.php", "inc/config-pdf.php", "inc/cert-download.php"]
LOCAL_PHP = ("/Users/meng/Library/Application Support/Local/lightning-services/"
             "php-8.2.29+0/bin/darwin-arm64/bin/php")


def plan(apply):
    failures = []
    for rel, anchor, why in EDITS:
        path = THEME / rel
        if not path.exists():
            failures.append("%s: missing" % rel)
            continue
        text = path.read_text(encoding="utf-8")
        n_old, n_new = text.count(anchor), text.count(anchor.replace(OLD, NEW))

        if n_old == 0 and n_new == 1:
            print("  SKIP  already applied  %s  (%s)" % (rel, why[:48]))
            continue
        if n_old != 1:
            failures.append("%s: anchor appears %d times, expected 1  [%s]"
                            % (rel, n_old, why[:48]))
            continue
        if n_new != 0:
            failures.append("%s: target string already present  [%s]" % (rel, why[:48]))
            continue

        print("  %s  %s" % ("EDIT " if apply else "PLAN ", rel))
        print("        why: %s" % why)
        print("        old: %s" % anchor.strip()[:96])
        if not apply:
            continue

        path.write_text(text.replace(anchor, anchor.replace(OLD, NEW)), encoding="utf-8")

        # Read back from disk, in this process, and re-assert both directions.
        # The delta is the number of occurrences the anchor itself carries, not
        # one: the contact-page anchor holds the address twice (mailto: and the
        # link text), so replacing it removes two.
        back = path.read_text(encoding="utf-8")
        if back.count(anchor.replace(OLD, NEW)) != 1 or back.count(anchor) != 0:
            failures.append("%s: read-back failed after write  [%s]" % (rel, why[:48]))
        delta = anchor.count(OLD)
        if back.count(OLD) != text.count(OLD) - delta:
            failures.append("%s: %d -> %d occurrences, expected to lose %d"
                            % (rel, text.count(OLD), back.count(OLD), delta))

    # Residue. A file is legitimate in exactly two states: untouched (it holds
    # the declared number of occurrences) or swapped (it holds none). Anything
    # else means a write was interrupted part-way, which is the failure mode
    # worth catching — an assertion that only accepted one of the two would
    # simply fail on a correct tree after the swap, as the first draft did.
    print("\n--- residue ---")
    states = set()
    for rel, declared in sorted(COUNTS.items()):
        text = (THEME / rel).read_text(encoding="utf-8")
        n = text.count(OLD)
        if n == 0:
            state, verdict = "swapped", "ok  "
        elif n == declared:
            state, verdict = "untouched", "ok  "
        else:
            state, verdict = "PARTIAL", "FAIL"
            failures.append("%s: %d occurrence(s) — neither untouched (%d) nor "
                            "swapped (0); a write was interrupted"
                            % (rel, n, declared))
        states.add(state)
        print("  %s %s: %d left -> %s" % (verdict, rel, n, state))
    if states == {"untouched", "swapped"}:
        failures.append("tree is half swapped: some files untouched, some swapped")
    if not apply and "swapped" in states and states == {"swapped"}:
        print("  note: the tree is already fully swapped — nothing for --apply to do")

    if apply and not failures:
        print("\n--- php -l ---")
        php = LOCAL_PHP if pathlib.Path(LOCAL_PHP).exists() else "php"
        for rel in PHP_FILES:
            proc = subprocess.run([php, "-l", str(THEME / rel)],
                                  capture_output=True, text=True)
            line = (proc.stdout or proc.stderr).strip().splitlines()
            print("  %s %s" % ("ok  " if proc.returncode == 0 else "FAIL", rel),
                  ("— " + line[0]) if line else "")
            if proc.returncode != 0:
                failures.append("%s: php -l failed" % rel)

    return failures


# How many live occurrences each file holds before the swap, and therefore how
# many the plan claims to remove. Zero is expected everywhere afterwards: every
# live occurrence in the theme is declared, and the occurrences we deliberately
# leave alone (the recipient at functions.php:4925, the two Cc headers, the two
# explanatory comments) are already sales@, so they are not counted here.
COUNTS = {
    "functions.php": 4,
    "inc/config-pdf.php": 2,
    "inc/cert-download.php": 1,
    "templates/page-contact.html": 2,
    "tools/make_coa_sample.php": 1,
}


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    print("=== batch H4e theme patch — %s ===" % ("APPLY" if args.apply else "CHECK"))
    print("theme: %s\n" % THEME)
    failures = plan(args.apply)

    print()
    if failures:
        for f in failures:
            print("FAIL  %s" % f)
        print("VERDICT: FAIL — %d problem(s), nothing else written" % len(failures))
        return 1
    print("VERDICT: %s" % (("PASS — %d anchors swapped, php -l clean" if args.apply
                            else "PASS — %d anchors unique, ready to apply") % len(EDITS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
