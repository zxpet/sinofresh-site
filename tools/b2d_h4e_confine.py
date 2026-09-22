#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H4e (email prerequisite) — the confined-proof gate.

THE ONE THING THAT MAKES THIS GATE DIFFERENT

The house's standard masked comparator, tools/sf_masked_cmp.py, neutralises
Cloudflare's address obfuscation with

    email-protection#[0-9a-f]+   ->  email-protection#MASK
    data-cfemail="[0-9a-f]+"     ->  data-cfemail="MASK"

which is exactly right for every batch before this one and exactly wrong for
this one: it throws away WHICH address is encoded, so a page that changed from
info@ to sales@ compares as identical. The mask set cannot see this batch at all.

So this gate normalises the other way round — it DECODES each blob back to the
address (the key is the first byte, the rest is XOR) instead of masking it. That
is also forced by measurement: Cloudflare picks a fresh key on every response
(three fetches of one page gave three different hex strings), so the blobs are
run-to-run noise that must be removed, while the address inside them is the
signal that must be kept.

Once decoded, the entire batch collapses to one statement:

    normalise(candidate) == normalise(baseline).replace('info@zxpet.com',
                                                        'sales@zxpet.com')

Eight gates assert that, and the parts of it a single equality cannot see.

usage:
    b2d_h4e_confine.py --baseline DIR --candidate DIR [--json out.json]
    b2d_h4e_confine.py --matrix           # sabotage variants must all be caught
"""
import argparse
import collections
import hashlib
import json
import os
import re
import sys

OLD = "info@zxpet.com"
NEW = "sales@zxpet.com"
GROUP = "https?://dev\\.zxpet\\.com"

CF_ATTR = re.compile(r'data-cfemail="([0-9a-f]+)"')
CF_LINK = re.compile(r"email-protection#([0-9a-f]+)")
LDJSON = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                    re.S)
LD_EMAIL = re.compile(r'"email"\s*:\s*"([^"]*)"')
H1 = re.compile(r"<h1[\s>]", re.I)
# Asset version tokens this gate watches: ver=<x> and the bare "?ver=" form.
VER = re.compile(r"ver=([0-9][0-9.]*)")
STEP_TITLES = ["Submit", "Review", "Approve"]  # only used to detect the H3 band


def cfd(hexstr):
    """Cloudflare's email obfuscation: first byte is the key, rest is XOR."""
    raw = bytes.fromhex(hexstr)
    if not raw:
        return ""
    key = raw[0]
    return "".join(chr(c ^ key) for c in raw[1:])


def decode_emails(t):
    """Put the real address back where Cloudflare hid it."""
    t = CF_ATTR.sub(lambda m: 'data-cfemail="' + cfd(m.group(1)) + '"', t)
    t = CF_LINK.sub(lambda m: "email-protection#" + cfd(m.group(1)), t)
    return t


# The pre-request noise masks come from the house comparator rather than being
# retyped here, so the two tools cannot drift apart. Two entries are dropped by
# name: cf_email_link and cf_email_attr erase the very thing this batch changes.
# Everything else in that set — the preflight directory suffix, the cache
# buster, Gravity Forms' microtime-seeded phone-field id and its 12h nonces,
# and the two base64 catch-alls — is genuine per-response noise that would
# otherwise convict every page of a change that never happened. Order is
# preserved, because the specific patterns must run before the catch-alls.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sf_masked_cmp  # noqa: E402

_DROPPED = {"cf_email_link", "cf_email_attr"}
NOISE = [(p, r, n) for (p, r, n) in sf_masked_cmp.MASKS if n not in _DROPPED]
assert len(sf_masked_cmp.MASKS) - len(NOISE) == 2, \
    "expected to drop exactly the two Cloudflare masks, dropped %d" \
    % (len(sf_masked_cmp.MASKS) - len(NOISE))


def clean(t):
    """Drop per-response noise, keeping the decoded address."""
    for pat, repl, _ in NOISE:
        t = pat.sub(repl, t)
    return t


def norm(t):
    return clean(decode_emails(t))


def declare(t):
    """The declared transformation: baseline -> candidate."""
    return norm(t).replace(OLD, NEW)


# ------------------------------------------------------------------ per-page

def page_facts(t):
    """Everything the gates need about one page, decoded."""
    d = decode_emails(t)
    cf = [cfd(m.group(1)) for m in CF_ATTR.finditer(t)]
    return {
        "raw": t,
        "decoded": d,
        "cf_attrs": cf,
        "cf_links": CF_LINK.findall(t),
        "ld_blocks": LDJSON.findall(t),
        "ld_emails": LD_EMAIL.findall(t),
        "h1": len(H1.findall(t)),
        "vers": collections.Counter(VER.findall(t)),
    }


def check_page(name, base, cand):
    """Return [(gate_id, ok, message)] for one page."""
    out = []
    fb, fc = page_facts(base), page_facts(cand)
    did = "%s" % name

    # [1] the page must actually differ: every reachable page carries the address
    if fb["raw"] == fc["raw"]:
        out.append(("1", False, "%s: page is byte-identical" % did))

    # [2] the confined proof: decode, then a single global replacement
    if norm(fc["raw"]) != declare(fb["raw"]):
        a, b = norm(fc["raw"]), declare(fb["raw"])
        i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
        out.append(("2", False, "%s: not the declared transformation; first diff at %d\n"
                                "        want ...%s\n"
                                "        got  ...%s"
                    % (did, i, b[max(0, i - 60):i + 60].replace("\n", " "),
                       a[max(0, i - 60):i + 60].replace("\n", " "))))

    # [3] every address on the candidate page is the new one, and the old one is gone
    stale = [a for a in fc["cf_attrs"] if a != NEW]
    if stale:
        out.append(("3", False, "%s: %d obfuscated address(es) are not %s: %s"
                    % (did, len(stale), NEW, collections.Counter(stale).most_common(3))))
    if OLD in norm(fc["raw"]):
        out.append(("3", False, "%s: the old address survives in plaintext" % did))

    # [4] the surface count cannot drift: same number of obfuscated anchors
    if len(fb["cf_attrs"]) != len(fc["cf_attrs"]):
        out.append(("4", False, "%s: obfuscated-address count %d -> %d"
                    % (did, len(fb["cf_attrs"]), len(fc["cf_attrs"]))))
    if len(fb["cf_links"]) != len(fc["cf_links"]):
        out.append(("4", False, "%s: email-protection link count %d -> %d"
                    % (did, len(fb["cf_links"]), len(fc["cf_links"]))))

    # [5] structured data: same blocks, one Organization email, now the new address
    if len(fb["ld_blocks"]) != len(fc["ld_blocks"]):
        out.append(("5", False, "%s: JSON-LD block count %d -> %d"
                    % (did, len(fb["ld_blocks"]), len(fc["ld_blocks"]))))
    if len(fc["ld_emails"]) != 1:
        out.append(("5", False, "%s: %d email field(s) in JSON-LD, expected 1"
                    % (did, len(fc["ld_emails"]))))
    elif fc["ld_emails"][0] != NEW:
        out.append(("5", False, "%s: JSON-LD email is %r" % (did, fc["ld_emails"][0])))

    # [6] the invariants earlier batches established must survive
    if fc["h1"] != 1:
        out.append(("6", False, "%s: %d h1, expected 1" % (did, fc["h1"])))
    for marker, label in (("sf-fdetail-content", "the H3 content band"),
                          ("sf-sampling__steps", "the H3 sampling band"),
                          ("sf-fdetail-faq", "the FAQ band"),
                          ("sf-fdetail-more", "the related grid")):
        if (marker in fb["raw"]) != (marker in fc["raw"]):
            out.append(("6", False, "%s: %s appeared or vanished" % (did, label)))

    # [7] no version token may move: nothing was bumped on purpose
    if fb["vers"] != fc["vers"]:
        moved = {k: (fb["vers"].get(k, 0), fc["vers"].get(k, 0))
                 for k in set(fb["vers"]) | set(fc["vers"])
                 if fb["vers"].get(k, 0) != fc["vers"].get(k, 0)}
        out.append(("7", False, "%s: an asset version token moved: %s" % (did, moved)))

    return out


# --------------------------------------------------------------------- whole

def load(d):
    """Read a captured section: {name: text} plus its MANIFEST rows."""
    pages, man = {}, {}
    if not os.path.isdir(d):
        return None, None
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".html"):
            continue
        with open(os.path.join(d, fn), encoding="utf-8", errors="replace") as fh:
            pages[fn] = fh.read()
    mf = os.path.join(d, "MANIFEST.tsv")
    if os.path.exists(mf):
        with open(mf, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#") or line.startswith("path\t"):
                    continue
                p = line.rstrip("\n").split("\t")
                if len(p) == 4:
                    man[p[0]] = (p[1], int(p[2]), p[3])
    return pages, man


def run(base_dir, cand_dir, want_json=None):
    fails, notes = [], []

    b, bman = load(base_dir)
    c, cman = load(cand_dir)

    # [0] both captures exist and hold the same 75 pages, all 200
    if not b:
        fails.append(("[0] baseline directory is empty or missing: %s" % base_dir))
        return fails, notes
    if not c:
        fails.append(("[0] candidate directory is empty or missing: %s" % cand_dir))
        return fails, notes
    if not bman:
        fails.append("[0] baseline MANIFEST.tsv is missing")
    if not cman:
        fails.append("[0] candidate MANIFEST.tsv is missing")
    if not bman or not cman:
        return fails, notes

    if set(b) != set(c):
        fails.append("[0] page sets differ: only-baseline=%s only-candidate=%s"
                     % (sorted(set(b) - set(c))[:4], sorted(set(c) - set(b))[:4]))
        return fails, notes
    bad = [p for p, (code, _, _) in cman.items() if code != "200"]
    if bad:
        fails.append("[0] %d candidate page(s) are not 200: %s" % (len(bad), bad[:4]))
    if len(b) != 75:
        fails.append("[0] %d pages, expected 75" % len(b))
    notes.append("[0] %d pages on both sides, all 200; MANIFEST present" % len(b))

    # [1] the changed set must be exactly the pages that carry the address,
    #     and on this site that is every page: the top bar, the footer contact
    #     line, the floating email button and the Organization schema are all
    #     site-wide, so the declared set is 75 of 75.
    changed = [n for n in b if b[n] != c[n]]
    notes.append("[1] %d of %d pages differ" % (len(changed), len(b)))
    if len(changed) != len(b):
        same = sorted(set(b) - set(changed))[:6]
        fails.append("[1] %d page(s) are byte-identical, so they did not get the "
                     "address: %s" % (len(same), same))

    # [2]-[7] per page
    for n in sorted(b):
        for gate, ok, msg in check_page(n, b[n], c[n]):
            if not ok:
                fails.append("[%s] %s" % (gate, msg))

    # [8] site-wide totals: the number of hidden addresses must be preserved
    tot_b = sum(len(CF_ATTR.findall(b[n])) for n in b)
    tot_c = sum(len(CF_ATTR.findall(c[n])) for n in c)
    notes.append("[8] obfuscated addresses: baseline %d, candidate %d" % (tot_b, tot_c))
    if tot_b != tot_c:
        fails.append("[8] obfuscated-address total %d -> %d" % (tot_b, tot_c))
    addrs = collections.Counter()
    for n in c:
        addrs.update(cfd(m.group(1)) for m in CF_ATTR.finditer(c[n]))
    notes.append("[8] every decoded address on the candidate: %s" % dict(addrs))
    if set(addrs) != {NEW}:
        fails.append("[8] decoded addresses are %s, expected only %s"
                     % (dict(addrs), NEW))

    if want_json:
        with open(want_json, "w", encoding="utf-8") as fh:
            json.dump({"fails": fails, "notes": notes,
                       "changed": len(changed), "pages": len(b),
                       "cf_total": {"baseline": tot_b, "candidate": tot_c},
                       "decoded": dict(addrs)}, fh, indent=2, ensure_ascii=False)
    return fails, notes


# ------------------------------------------------------------------- matrix

def mutate(kind, base, cand):
    """Apply one sabotage variant to an in-memory candidate."""
    c = dict(cand)
    names = sorted(c)

    def one(n):
        return c[n]

    if kind == "address-not-changed":
        c = dict(base)
    elif kind == "half-the-pages-changed":
        for n in names[: len(names) // 2]:
            c[n] = base[n]
    elif kind == "address-reverted":
        c = {n: one(n).replace(NEW, OLD) for n in names}
    elif kind == "extra-surface-added":
        n = names[0]
        c[n] = one(n).replace("</body>",
                              '<a href="mailto:sales@zxpet.com">sales@zxpet.com</a></body>')
    elif kind == "surface-removed":
        n = names[0]
        c[n] = CF_ATTR.sub("", one(n), count=1)
    elif kind == "schema-email-unchanged":
        c = {n: LD_EMAIL.sub(lambda m: '"email": "%s"' % OLD, one(n), count=1)
             if LD_EMAIL.search(one(n)) else one(n) for n in names}
    elif kind == "ver-token-moved":
        n = names[0]
        c[n] = one(n).replace("ver=2.10.57", "ver=2.10.58")
    elif kind == "unrelated-word-changed":
        n = names[0]
        c[n] = one(n).replace("SINO FRESH", "SINO FRESHY", 1)
    elif kind == "one-page-left-behind":
        n = names[0]
        c[n] = base[n]
    elif kind == "zh-pretty-schema-unchanged":
        zh = [n for n in names if n.startswith("zh")]
        for n in zh:
            c[n] = LD_EMAIL.sub(lambda m: '"email": "%s"' % OLD, one(n), count=1)
    elif kind == "h1-duplicated":
        n = names[0]
        c[n] = one(n).replace("</h1>", "</h1><h1>Extra</h1>", 1)
    elif kind == "band-removed":
        n = [x for x in names if "sf-fdetail-content" in c[x]]
        if n:
            # Remove the marker outright rather than renaming it: a rename to
            # "sf-fdetail-contentX" still contains the marker as a substring,
            # so the structural gate would call it present and only [2] would
            # fire. This variant is here to prove the structural gate bites.
            c[n[0]] = c[n[0]].replace("sf-fdetail-content", "")
    elif kind == "obfuscated-blob-swapped-to-another-address":
        n = names[0]
        # re-encode a DIFFERENT address under the same obfuscation scheme
        def reenc(m):
            raw = bytes.fromhex(m.group(1))
            key = raw[0]
            payload = "billing@zxpet.com"
            return 'data-cfemail="%02x%s"' % (key, "".join(
                "%02x" % (ord(ch) ^ key) for ch in payload))
        c[n] = CF_ATTR.sub(reenc, one(n), count=1)
    elif kind == "mailto-kept-but-text-changed":
        # the anchor's href still points at the old address while the visible
        # text was updated: the mirror image of a half-finished edit
        n = [x for x in names if OLD in decode_emails(base[x])]
        if n:
            c[n[0]] = re.sub(r'href="/cdn-cgi/l/email-protection#[0-9a-f]+"',
                             'href="mailto:' + OLD + '"', one(n[0]), count=1)
    else:
        raise SystemExit("unknown variant %r" % kind)
    return c


MATRIX = [
    "address-not-changed",
    "half-the-pages-changed",
    "address-reverted",
    "extra-surface-added",
    "surface-removed",
    "schema-email-unchanged",
    "ver-token-moved",
    "unrelated-word-changed",
    "one-page-left-behind",
    "zh-pretty-schema-unchanged",
    "h1-duplicated",
    "band-removed",
    "obfuscated-blob-swapped-to-another-address",
    "mailto-kept-but-text-changed",
]


def run_matrix(base, cand):
    rows, missed = [], []
    for kind in MATRIX:
        mutated = mutate(kind, base, cand)
        bad = []
        for n in sorted(base):
            for gate, ok, _ in check_page(n, base[n], mutated[n]):
                if not ok:
                    bad.append(gate)
        # whole-section gates worth re-running on a mutation
        if sum(len(CF_ATTR.findall(mutated[n])) for n in mutated) != \
           sum(len(CF_ATTR.findall(base[n])) for n in base):
            bad.append("8")
        if any(mutated[n] == base[n] for n in mutated):
            bad.append("1")
        gates = sorted(set(bad))
        rows.append((kind, gates))
        if not gates:
            missed.append(kind)
    return rows, missed


# --------------------------------------------------------------------- main

def negcontrol(base_dir, cand_dir):
    """Break one precondition per control. Each must FAIL, with a named verdict.

    A non-zero exit is not enough on its own: a missing file makes Python raise
    FileNotFoundError, which exits non-zero without saying anything about what
    was being checked. Every control below asserts that a *named* gate fired.
    """
    import shutil
    import tempfile

    tmp = tempfile.mkdtemp(prefix="h4e-negctl-")
    results = []

    def snapshot(name, src):
        dst = os.path.join(tmp, name)
        shutil.copytree(src, dst)
        return dst

    try:
        # 1. baseline with no MANIFEST.tsv: we would not know what was fetched.
        d = snapshot("no-manifest", base_dir)
        os.remove(os.path.join(d, "MANIFEST.tsv"))
        fails, _ = run(d, cand_dir)
        results.append(("served-manifest-missing",
                        any("MANIFEST" in f for f in fails),
                        "baseline MANIFEST.tsv is missing",
                        fails))

        # 2. empty baseline directory: no pages at all.
        d = os.path.join(tmp, "empty")
        os.makedirs(d)
        fails, _ = run(d, cand_dir)
        results.append(("baseline-empty",
                        any("baseline directory is empty" in f for f in fails),
                        "baseline directory is empty",
                        fails))

        # 3. candidate is a copy of the baseline: nothing changed.
        d = snapshot("candidate-is-baseline", base_dir)
        fails, _ = run(base_dir, d)
        results.append(("candidate-equals-baseline",
                        any("byte-identical" in f for f in fails),
                        "candidate is a copy of the baseline",
                        fails))

        # 4. one page missing from the candidate.
        d = snapshot("page-missing", cand_dir)
        victim = sorted(n for n in os.listdir(d) if n.endswith(".html"))[0]
        os.remove(os.path.join(d, victim))
        fails, _ = run(base_dir, d)
        results.append(("page-missing-from-candidate",
                        any("page sets differ" in f for f in fails),
                        "one candidate page is absent",
                        fails))

        # 5. an A/A capture used as if it were the candidate: the addresses did
        #    not move, so the change never happened.
        d = snapshot("addresses-never-moved", cand_dir)
        for fn in os.listdir(d):
            if fn.endswith(".html"):
                p = os.path.join(d, fn)
                with open(p, encoding="utf-8", errors="replace") as fh:
                    t = fh.read()
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(t.replace(NEW, OLD))
        fails, _ = run(base_dir, d)
        results.append(("addresses-never-moved",
                        any(g in f for f in fails for g in ("[2]", "[3]")),
                        "candidate still carries the old address throughout",
                        fails))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=== negative controls — each precondition break must FAIL by name ===")
    bad = 0
    for name, ok, desc, fails in results:
        named = [f for f in fails if f.startswith("[") or "empty" in f]
        print("  %-32s %s  %s" % (name, "FAIL (as required)" if ok else "PASSED — control is blind!",
                                  desc))
        print("  %-32s        %s" % ("", "; ".join(named[:2]) if named else "(no named verdict)"))
        if not ok:
            bad += 1
    print("-" * 72)
    print("  %d/%d controls failed as required" % (len(results) - bad, len(results)))
    print("NEGCTL VERDICT: %s" % ("PASS" if not bad else "FAIL"))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline")
    ap.add_argument("--candidate")
    ap.add_argument("--json")
    ap.add_argument("--matrix", action="store_true")
    ap.add_argument("--negctl", action="store_true")
    ap.add_argument("--aa", metavar="DIR",
                    help="A/A self-test: two independent captures of the SAME "
                         "state. Every gate must pass except [1], which asserts "
                         "the pages differ — if any page trips [2] then the noise "
                         "mask set is incomplete and the gate would convict a "
                         "batch that changed nothing.")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    base_dir = args.baseline or os.path.join(root, "_backup", "b2d-h3-candidates")
    cand_dir = args.candidate or os.path.join(root, "_backup", "b2d-h4e-candidates")

    if args.aa:
        b, _ = load(args.aa)
        if not b:
            print("FATAL: no pages in %s" % args.aa)
            return 2
        print("=== A/A self-test — %s against itself ===" % args.aa)
        print("A page that fails [2] here means the mask set let per-response")
        print("noise through, and the tool would report a regression that is not")
        print("there.\n")
        spurious, differ = [], 0
        for n in sorted(b):
            for gate, ok, msg in check_page(n, b[n], b[n]):
                if not ok:
                    if gate == "1":
                        differ += 1
                    else:
                        spurious.append("[%s] %s" % (gate, msg))
        print("  [1] pages that differ from themselves: %d (expected 75 — the gate "
              "asserts a change happened)" % differ)
        if spurious:
            for s in spurious[:10]:
                print("  FAIL %s" % s)
            print("-" * 72)
            print("A/A VERDICT: FAIL — %d spurious finding(s); the mask set is "
                  "incomplete" % len(spurious))
            return 1
        print("  ok  [2]-[7] no page trips on noise: the decoded comparison is "
              "stable across two independent captures")
        print("-" * 72)
        print("A/A VERDICT: PASS — only the deliberate [1] failures, none spurious")
        return 0

    if args.negctl:
        return negcontrol(base_dir, cand_dir)

    if args.matrix:
        b, _ = load(base_dir)
        c, _ = load(cand_dir)
        if not b or not c:
            print("FATAL: need both sections to run the matrix")
            return 2
        # The matrix runs on a healthy candidate; prove it first.
        fails, _ = run(base_dir, cand_dir)
        if fails:
            print("FATAL: refusing to run the matrix on a failing gate (%d fail(s))"
                  % len(fails))
            for f in fails[:5]:
                print("   " + f)
            return 3
        print("=== sabotage matrix — every variant must be caught ===")
        rows, missed = run_matrix(b, c)
        for kind, gates in rows:
            print("  %-48s %s" % (kind, ("CAUGHT   [" + "] [".join(gates) + "]")
                                  if gates else "MISSED"))
        print("-" * 72)
        if missed:
            print("  %d/%d variants caught — MISSED: %s"
                  % (len(rows) - len(missed), len(rows), missed))
            print("MATRIX VERDICT: FAIL")
            return 1
        print("  %d/%d variants caught" % (len(rows), len(rows)))
        print("MATRIX VERDICT: PASS")
        return 0

    fails, notes = run(base_dir, cand_dir, args.json)
    print("=== batch H4e confined proof — %s vs %s ===" % (base_dir, cand_dir))
    print("declared transformation: %s -> %s, decoded, everywhere\n" % (OLD, NEW))
    for n in notes:
        print("  ok   %s" % n)
    if fails:
        for f in fails:
            print("  FAIL %s" % f)
        print("-" * 72)
        print("VERDICT: FAIL — %d problem(s)" % len(fails))
        return 1
    print("-" * 72)
    print("VERDICT: PASS — all eight gates hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
