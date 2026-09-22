#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H4 (inquiry dialog + Send Inquiry capsule) — the confined-proof gate.

WHAT THIS GATE HAS TO PROVE

The batch adds exactly three things to a page:

  1. an <a class="sf-float-btn sf-float-btn--inquiry" ...> as the FIRST child of
     .sf-float-stack,
  2. a <script id="sinofresh-inquiry-js"> tag in the footer,
  3. the dialog: one <div class="sf-inquiry-modal"> block containing the
     "Your Selection" rows, the four sampling steps and the five-field form.

...on exactly the 42 pages that carry .sf-fdetail2__params, and nothing else
anywhere. Plus a version token bump (2.10.57 -> 2.10.58) on all 75, which is a
declared change and not a finding: style.css is one file and it moved.

So the whole batch collapses to one statement, per page:

    strip_declared(candidate) == fold_ver(baseline)

where strip_declared removes those three things byte-exactly (asserting how
many it removed) and fold_ver normalises the version token. Anything else that
moved shows up as a difference, which is what the limited proof is for.

Two things carried in from batch H4e and not optional here:

  * the noise masks are IMPORTED from tools/sf_masked_cmp.py, minus the two
    Cloudflare entries that erase which address is encoded — retyping the set
    would let the two tools drift, and the assertion that exactly two were
    dropped is what stops someone "helpfully" putting them back;
  * every blob Cloudflare obfuscated is DECODED before comparing, because the
    key is fresh on every response. This batch changes no address, so the
    decoded addresses must come out identical — which is also how gate [8]
    proves the H4e change survived.

usage:
    b2d_h4_confine.py --baseline DIR --candidate DIR [--json out.json]
    b2d_h4_confine.py --baseline DIR --candidate DIR --aa
    b2d_h4_confine.py --baseline DIR --candidate DIR --matrix
    b2d_h4_confine.py --baseline DIR --candidate DIR --negctl
"""
import argparse
import collections
import copy
import hashlib
import html
import json
import os
import re
import shutil
import sys

HOST = "https://dev.zxpet.com"
VER_TOKEN = "ver=<TOKEN>"
OLD_VER = "2.10.57"
NEW_VER = "2.10.59"
STATIC_DIR = "sinofresh-theme"
PREFLIGHT_DIR = "sinofresh-theme-preflight"

CAPSULE_START = '<a class="sf-float-btn sf-float-btn--inquiry"'
SCRIPT_START = '<script id="sinofresh-inquiry-js"'
DIALOG_START = '<div class="sf-inquiry-modal" hidden>'
# The parameter band's marker is the exact quoted attribute, not the bare class
# name: a rename to "...paramsX" still contains the bare name as a substring,
# and a presence test would then score the band as untouched (A.9 #13).
PARAMS = 'class="sf-fdetail2__params"'
STACK = '<div class="sf-float-stack">'

CF_ATTR = re.compile(r'data-cfemail="([0-9a-f]+)"')
CF_LINK = re.compile(r"email-protection#([0-9a-f]+)")
LDJSON = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S)
H1 = re.compile(r"<h1[\s>]", re.I)
VER = re.compile(r"ver=([0-9][0-9.]*)")
STEP_TITLE = re.compile(r"'title'\s*=>\s*'([^']*)'")

SELECTION_LABELS = {
    "Flavor", "Piece Weight", "Pack Size",
    "Suitable For", "Life Stage", "Quantity & Pricing",
}
SELECTION_RE = re.compile(
    r'<dt class="sf-inquiry-modal__term">([^<]*)</dt>'
    r'<dd class="sf-inquiry-modal__value">([^<]*)</dd>')
STEP_RE = re.compile(
    r'<span class="sf-inquiry-modal__step-title">([^<]*)</span>')

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(os.path.dirname(FILE_DIR), "sinofresh-theme")


def cfd(hexstr):
    """Cloudflare's email obfuscation: first byte is the key, rest is XOR."""
    raw = bytes.fromhex(hexstr)
    if not raw:
        return ""
    key = raw[0]
    return "".join(chr(c ^ key) for c in raw[1:])


def decode_emails(t):
    t = CF_ATTR.sub(lambda m: 'data-cfemail="' + cfd(m.group(1)) + '"', t)
    t = CF_LINK.sub(lambda m: "email-protection#" + cfd(m.group(1)), t)
    return t


# The pre-request noise masks come from the house comparator rather than being
# retyped here, so the two tools cannot drift apart. Two entries are dropped by
# name: cf_email_link and cf_email_attr erase which address is encoded, and
# this gate decodes the blobs instead.
sys.path.insert(0, FILE_DIR)
import sf_masked_cmp  # noqa: E402

_DROPPED = {"cf_email_link", "cf_email_attr"}
NOISE = [(p, r, n) for (p, r, n) in sf_masked_cmp.MASKS if n not in _DROPPED]
assert len(sf_masked_cmp.MASKS) - len(NOISE) == 2, \
    "expected to drop exactly the two Cloudflare masks, dropped %d" \
    % (len(sf_masked_cmp.MASKS) - len(NOISE))


def clean(t):
    for pat, repl, _ in NOISE:
        t = pat.sub(repl, t)
    return t


def norm(t):
    return clean(decode_emails(t))


def fold_ver(t):
    return VER.sub(VER_TOKEN, t)


def balanced_end(t, start):
    """Index just past the </div> that closes the <div ...> opening at start."""
    depth = 0
    i = start
    while i < len(t):
        nxt_open = t.find("<div", i)
        nxt_close = t.find("</div>", i)
        if nxt_close < 0:
            return -1
        if 0 <= nxt_open < nxt_close:
            depth += 1
            i = nxt_open + 4
            continue
        depth -= 1
        i = nxt_close + 6
        if depth == 0:
            return i
    return -1


def strip_declared(t, counts=None):
    """Remove the three declared additions, byte-exactly.

    counts, when passed, accrues how many of each were removed — the census
    gate reads it, and an off-by-one in the strip would otherwise show up as a
    page that "differs" instead of as a broken tool.
    """
    def bump(key):
        if counts is not None:
            counts[key] += 1

    # 1. the capsule. No nested <a>, so the first </a> after the marker is its
    #    own close tag.
    out = []
    i = 0
    while True:
        j = t.find(CAPSULE_START, i)
        if j < 0:
            out.append(t[i:])
            break
        k = t.find("</a>", j)
        if k < 0:
            out.append(t[i:])
            break
        out.append(t[i:j])
        i = k + 4
        bump("capsule")
    t = "".join(out)

    # 2. the footer script tag, with the newline WP prints after it.
    while True:
        j = t.find(SCRIPT_START)
        if j < 0:
            break
        k = t.find("</script>", j)
        if k < 0:
            break
        k += len("</script>")
        if t[k:k + 1] == "\n":
            k += 1
        t = t[:j] + t[k:]
        bump("script")

    # 3. the dialog. wp_footer echoes it as "\n" . <block> . "\n", so exactly
    #    one newline on each side belongs to it.
    while True:
        j = t.find(DIALOG_START)
        if j < 0:
            break
        end = balanced_end(t, j)
        if end < 0:
            break
        lo = j - 1 if j > 0 and t[j - 1] == "\n" else j
        hi = end + 1 if t[end:end + 1] == "\n" else end
        t = t[:lo] + t[hi:]
        bump("dialog")
    return t


def page_facts(t):
    return {
        "capsule": t.count(CAPSULE_START),
        "script": t.count(SCRIPT_START),
        "dialog": t.count(DIALOG_START),
        "params": t.count(PARAMS),
        "stack": t.count(STACK),
        "h1": len(H1.findall(t)),
        "literal": t.count("[sf_inquiry_button]"),
        "cf_attrs": [cfd(m.group(1)) for m in CF_ATTR.finditer(t)],
        "addresses": sorted(set(
            [cfd(m.group(1)) for m in CF_ATTR.finditer(t)]
            + [cfd(m.group(1)) for m in CF_LINK.finditer(t)])),
        "ldjson": sorted(norm(b) for b in LDJSON.findall(t)),
        "ver": sorted(set(VER.findall(t))),
        "theme_dirs": sorted(set(re.findall(r"/themes/([A-Za-z0-9_.-]+)/", t))),
    }


def read_dir(d):
    pages, manifest, header = {}, None, None
    if not os.path.isdir(d):
        return pages, manifest, header
    for fn in sorted(os.listdir(d)):
        if fn == "MANIFEST.tsv":
            manifest = os.path.join(d, fn)
            with open(manifest, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.startswith("# header:"):
                        header = line.split(":", 1)[1].strip()
            continue
        if not fn.endswith(".html"):
            continue
        with open(os.path.join(d, fn), encoding="utf-8", errors="replace") as fh:
            pages[fn] = fh.read()
    return pages, manifest, header


def manifest_codes(path):
    codes = {}
    if not path or not os.path.exists(path):
        return codes
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or line.startswith("path\t"):
                continue
            bits = line.rstrip("\n").split("\t")
            if len(bits) >= 2:
                codes[bits[0]] = bits[1]
    return codes


# ---------------------------------------------------------------------- gates

class Report:
    def __init__(self):
        self.lines = []
        self.fails = []
        self.data = {}

    def ok(self, msg):
        self.lines.append("  ok  " + msg)

    def fail(self, msg):
        self.lines.append("  FAIL " + msg)
        self.fails.append(msg)

    def note(self, msg):
        self.lines.append("       " + msg)


def run(base_dir, cand_dir, expect_change=True):
    rep = Report()
    base, base_manifest, base_header = read_dir(base_dir)
    cand, cand_manifest, cand_header = read_dir(cand_dir)
    base_codes = manifest_codes(base_manifest)
    cand_codes = manifest_codes(cand_manifest)

    # [0] the two sides themselves
    if len(base) != 75 or len(cand) != 75:
        rep.fail("[0] sides are not 75/75 (baseline %d, candidate %d)" % (len(base), len(cand)))
    else:
        rep.ok("[0] both sides hold 75 pages")
    if not base_codes:
        rep.fail("[0] baseline MANIFEST.tsv is missing")
    if not base:
        rep.note("baseline directory holds no pages — check --baseline. "
                 "H4's baseline is the previous batch's pre-flight copy, "
                 "_backup/b2d-h4e-candidates (ver=%s)." % OLD_VER)
    if not cand_codes:
        rep.fail("[0] candidate MANIFEST.tsv is missing")
    bad = [p for p, c in cand_codes.items() if c != "200"]
    if bad:
        rep.fail("[0] candidate has %d non-200 paths: %s" % (len(bad), bad[:5]))
    if cand_header is None:
        rep.fail("[0] the candidate manifest records no request header")
    elif "X-SF-Preflight" not in cand_header:
        rep.fail("[0] the candidate was fetched without the pre-flight header: %r" % cand_header)
    else:
        rep.ok("[0] candidate manifest records the pre-flight header")
    if base_header is not None and "X-SF-Preflight" not in base_header:
        rep.note("baseline header: %r" % base_header)

    if not cand or not base:
        return rep

    # candidate provenance: the served stylesheet must come from the copy.
    # Both modes serve the pre-flight copy — the A/A "baseline" is a second
    # capture of the candidate state, not the live theme — so the expectation
    # is the same in both. The bytes under test are never sinofresh-theme/.
    want_dir = PREFLIGHT_DIR
    dirs = collections.Counter()
    for t in cand.values():
        for d in re.findall(r"/themes/([A-Za-z0-9_.-]+)/", t):
            dirs[d] += 1
    if set(dirs) != {want_dir}:
        rep.fail("[0] candidate assets do not come from %s: %s" % (want_dir, dict(dirs)))
    else:
        rep.ok("[0] every candidate asset resolves into %s/" % want_dir)

    # [1] the declared change, as a census
    capsule = [fn for fn, t in cand.items() if CAPSULE_START in t]
    dialog = [fn for fn, t in cand.items() if DIALOG_START in t]
    script = [fn for fn, t in cand.items() if SCRIPT_START in t]
    band = [fn for fn, t in cand.items() if PARAMS in t]
    rep.data["capsule"] = len(capsule)
    rep.data["dialog"] = len(dialog)
    rep.data["script"] = len(script)
    rep.data["band"] = len(band)
    if expect_change:
        if len(band) != 42:
            rep.fail("[1] the parameter band is on %d pages, expected 42" % len(band))
        if sorted(capsule) != sorted(band):
            rep.fail("[1] capsule and parameter band disagree: %d vs %d pages"
                     % (len(capsule), len(band)))
        if sorted(dialog) != sorted(band):
            rep.fail("[1] dialog and parameter band disagree: %d vs %d pages"
                     % (len(dialog), len(band)))
        if sorted(script) != sorted(band):
            rep.fail("[1] inquiry.js and parameter band disagree: %d vs %d pages"
                     % (len(script), len(band)))
        if not (sorted(capsule) == sorted(dialog) == sorted(script) == sorted(band)):
            rep.note("capsule %d / dialog %d / script %d / band %d"
                     % (len(capsule), len(dialog), len(script), len(band)))
        else:
            rep.ok("[1] capsule = dialog = inquiry.js = parameter band = 42 pages, same set")

        old_left = [fn for fn, t in cand.items() if OLD_VER in page_facts(t)["ver"]]
        bumped = [fn for fn, t in cand.items() if NEW_VER in page_facts(t)["ver"]]
        if old_left:
            rep.fail("[1] %d candidate pages still advertise ver=%s" % (len(old_left), OLD_VER))
        elif len(bumped) != 75:
            rep.fail("[1] only %d of 75 candidate pages advertise ver=%s" % (len(bumped), NEW_VER))
        else:
            rep.ok("[1] all 75 candidate pages advertise ver=%s, none advertises ver=%s"
                   % (NEW_VER, OLD_VER))
    else:
        # A/A: two captures of one state must look identical, so nothing here
        # is expected to have changed — gate [1] is the deliberate failure.
        rep.fail("[1] pages that differ from themselves: %d (expected 75 — the gate asserts a change happened)"
                 % len(base))

    # [2] the limited proof.
    #     norm() on BOTH sides, because every page carries Cloudflare blobs
    #     (the footer mailto, the topbar mailto, the Organization schema) whose
    #     key is fresh on every response — comparing the raw bytes would convict
    #     all 75 pages of a change that never happened. norm() decodes the blobs
    #     and masks the remaining per-response noise; the two sides are the same
    #     state, so what survives decoding must be byte-identical.
    diff_pages = []
    counts = collections.Counter()
    base_counts = collections.Counter()
    for fn in sorted(cand):
        if fn not in base:
            rep.fail("[2] candidate page missing from the baseline: %s" % fn)
            continue
        stripped = norm(fold_ver(strip_declared(cand[fn], counts)))
        # Strip BOTH sides. On the main run the baseline predates the batch and
        # carries none of the declared additions, so its call is a no-op; on the
        # A/A run the baseline is a second capture of the candidate state and
        # carries all of them, and stripping only one side would convict all 42
        # dialog pages of a change that never happened.
        other = norm(fold_ver(strip_declared(base[fn], base_counts)))
        if stripped != other:
            diff_pages.append(fn)
    rep.data["stripped"] = dict(counts)
    rep.data["diff_pages"] = len(diff_pages)
    if diff_pages:
        rep.fail("[2] %d pages differ beyond the declared additions: %s"
                 % (len(diff_pages), ", ".join(diff_pages[:6])))
    else:
        rep.ok("[2] strip_declared(candidate) == baseline byte-for-byte after norm on all 75 pages")
    if expect_change and counts["capsule"] != 42:
        rep.fail("[2] stripped %d capsules, expected 42" % counts["capsule"])
    if expect_change and counts["dialog"] != 42:
        rep.fail("[2] stripped %d dialogs, expected 42" % counts["dialog"])
    if expect_change and counts["script"] != 42:
        rep.fail("[2] stripped %d inquiry.js tags, expected 42" % counts["script"])

    # [3] the 33 pages that must be untouched
    untouched = [fn for fn in cand if CAPSULE_START not in cand[fn]]
    if expect_change:
        if len(untouched) != 33:
            rep.fail("[3] %d pages carry no capsule, expected 33" % len(untouched))
        else:
            rep.ok("[3] 33 pages carry neither the capsule nor the dialog nor the script")
        for fn in untouched:
            if DIALOG_START in cand[fn] or SCRIPT_START in cand[fn]:
                rep.fail("[3] %s carries a dialog or script without the capsule" % fn)
                break

    # [4] the capsule's own structure
    struct_bad = []
    for fn in capsule:
        t = cand[fn]
        j = t.find(STACK)
        k = t.find(CAPSULE_START)
        if j < 0:
            struct_bad.append((fn, "no float stack"))
            continue
        if k != j + len(STACK):
            struct_bad.append((fn, "not the first child of the stack"))
        seg = t[k:k + 900]
        if "contact/#quote" not in seg:
            struct_bad.append((fn, "href is not the contact fallback"))
        if ' hidden>' not in seg:
            struct_bad.append((fn, "hidden is missing"))
        if ">Send Inquiry</span>" not in seg:
            struct_bad.append((fn, "label is not Send Inquiry"))
    if struct_bad:
        rep.fail("[4] capsule structure wrong on %d pages: %s" % (len(struct_bad), struct_bad[:3]))
    else:
        rep.ok("[4] capsule is the stack's first child, hidden, labelled, on all %d pages" % len(capsule))

    # [5] the three buttons already in the stack must read exactly as before.
    #     norm() again: the email button's href is a Cloudflare blob. Both
    #     sides are stripped for the same reason as [2]: on the A/A run the
    #     baseline stack already holds the capsule.
    stack_bad = []
    for fn in sorted(base):
        t = base[fn]
        j = t.find(STACK)
        if j < 0:
            continue
        seg_b = norm(strip_declared(t[j:balanced_end(t, j)]))
        t2 = cand.get(fn, "")
        j2 = t2.find(STACK)
        if j2 < 0:
            stack_bad.append((fn, "stack vanished"))
            continue
        seg_c = norm(strip_declared(t2[j2:balanced_end(t2, j2)]))
        if seg_c != seg_b:
            stack_bad.append((fn, "stack contents moved"))
    if stack_bad:
        rep.fail("[5] the float stack changed on %d pages: %s" % (len(stack_bad), stack_bad[:3]))
    else:
        rep.ok("[5] the three pre-existing float buttons are byte-identical on all 75 pages")

    # [6] the sampling steps are single-sourced
    titles = []
    src = os.path.join(THEME, "functions.php")
    if os.path.exists(src):
        with open(src, encoding="utf-8", errors="replace") as fh:
            php = fh.read()
        anchor = php.find("function sinofresh_sampling_steps()")
        if anchor >= 0:
            end = php.find("\n}", anchor)
            titles = STEP_TITLE.findall(php[anchor:end])
    if len(titles) != 4:
        rep.fail("[6] could not read the four step titles out of functions.php (got %d)" % len(titles))
    else:
        bad = []
        for fn in dialog:
            got = [html.unescape(s) for s in STEP_RE.findall(cand[fn])]
            if got != titles:
                bad.append((fn, got))
        if bad:
            rep.fail("[6] dialog steps are not the shared copy on %d pages: %s" % (len(bad), bad[:2]))
        else:
            rep.ok("[6] all 42 dialogs print the four titles from sinofresh_sampling_steps(): %s"
                   % " / ".join(titles))

    # [7] the selection rows
    label_census = collections.Counter()
    row_bad = []
    for fn in dialog:
        rows = SELECTION_RE.findall(cand[fn])
        for label, value in rows:
            label_census[label] += 1
            if label not in SELECTION_LABELS:
                row_bad.append((fn, "unexpected label %r" % label))
            if not value.strip():
                row_bad.append((fn, "empty value for %s" % label))
    rep.data["selection_rows"] = dict(label_census)
    if row_bad:
        rep.fail("[7] selection rows are wrong on %d pages: %s" % (len(row_bad), row_bad[:3]))
    else:
        rep.ok("[7] selection labels all come from the declared set: %s"
               % ", ".join("%s x%d" % (k, v) for k, v in sorted(label_census.items())))

    # [8] no address moved, and the H4e change is intact
    addr_bad = []
    for fn in sorted(base):
        a = page_facts(base[fn])["addresses"]
        b = page_facts(cand.get(fn, ""))["addresses"]
        if a != b:
            addr_bad.append((fn, a, b))
        for addr in b:
            if addr and addr != "sales@zxpet.com":
                addr_bad.append((fn, "unexpected address", addr))
    if addr_bad:
        rep.fail("[8] the decoded addresses changed on %d pages: %s" % (len(addr_bad), addr_bad[:3]))
    else:
        rep.ok("[8] every decoded Cloudflare address is sales@zxpet.com on both sides")

    # [9] structured data unchanged
    ld_bad = [fn for fn in sorted(base)
              if page_facts(base[fn])["ldjson"] != page_facts(cand.get(fn, ""))["ldjson"]]
    if ld_bad:
        rep.fail("[9] JSON-LD changed on %d pages: %s" % (len(ld_bad), ld_bad[:5]))
    else:
        rep.ok("[9] JSON-LD blocks are identical on all 75 pages")

    # [10] the invariants the older batches left behind
    inv_bad = []
    for fn in sorted(base):
        fb, fc = page_facts(base[fn]), page_facts(cand.get(fn, ""))
        if fb["literal"] or fc["literal"]:
            inv_bad.append((fn, "unrendered [sf_inquiry_button]"))
        if fb["h1"] != fc["h1"]:
            inv_bad.append((fn, "h1 count %d -> %d" % (fb["h1"], fc["h1"])))
        if fb["params"] != fc["params"]:
            inv_bad.append((fn, "parameter band %d -> %d" % (fb["params"], fc["params"])))
    if inv_bad:
        rep.fail("[10] invariants broken on %d pages: %s" % (len(inv_bad), inv_bad[:4]))
    else:
        rep.ok("[10] h1 count, parameter band and shortcode rendering unchanged on all 75 pages")

    # [11] the form itself has to be complete
    need = ['name="formula"', 'name="ts"', 'name="website"', 'name="name"',
            'name="email"', 'name="company"', 'name="country"', 'name="message"',
            'type="submit"', 'class="sf-inquiry-form__trap"']
    form_bad = []
    for fn in dialog:
        j = cand[fn].find(DIALOG_START)
        seg = cand[fn][j:balanced_end(cand[fn], j)]
        for n in need:
            if n not in seg:
                form_bad.append((fn, n))
    if form_bad:
        rep.fail("[11] the dialog is missing form parts on %d counts: %s"
                 % (len(form_bad), form_bad[:4]))
    else:
        rep.ok("[11] all 42 dialogs carry the honeypot, the two hidden fields, the five fields and a submit")

    return rep


# ----------------------------------------------------------------- sabotage

def mutate(fn, t, kind):
    if kind == "capsule-missing":
        j = t.find(CAPSULE_START)
        if j < 0:
            return t
        return t[:j] + t[t.find("</a>", j) + 4:]
    if kind == "dialog-missing":
        j = t.find(DIALOG_START)
        if j < 0:
            return t
        end = balanced_end(t, j)
        return t[:j] + t[end:]
    if kind == "capsule-on-a-plain-page":
        if CAPSULE_START in t:
            return t
        j = t.find(STACK)
        if j < 0:
            return t
        return t[:j + len(STACK)] + CAPSULE_START_FULL + t[j + len(STACK):]
    if kind == "dialog-on-a-plain-page":
        if DIALOG_START in t:
            return t
        return t.replace("</body>", DIALOG_SNIPPET + "</body>")
    if kind == "ver-not-bumped":
        return t.replace("ver=" + NEW_VER, "ver=" + OLD_VER)
    if kind == "step-title-reworded":
        return t.replace(">Confirm Details<", ">Confirm the Details<")
    if kind == "steps-reduced-to-three":
        j = t.find(DIALOG_START)
        if j < 0:
            return t
        k = t.find('<li class="sf-inquiry-modal__step">', t.find('sf-inquiry-modal__steps'))
        if k < 0:
            return t
        end = t.find("</li>", k) + 5
        return t[:k] + t[end:]
    if kind == "selection-label-invented":
        return t.replace('>Piece Weight</dt>', '>Unit Weight</dt>')
    if kind == "capsule-not-first-child":
        j = t.find(CAPSULE_START)
        if j < 0:
            return t
        end = t.find("</a>", j) + 4
        return t[:j] + t[end:] + t[j:end]
    if kind == "capsule-loses-hidden":
        j = t.find(CAPSULE_START)
        if j < 0:
            return t
        end = t.find("</a>", j) + 4
        return t[:j] + t[j:end].replace(" hidden>", ">") + t[end:]
    if kind == "honeypot-input-removed":
        j = t.find('name="website"')
        if j < 0:
            return t
        lo = t.rfind("<div class=\"sf-inquiry-form__trap\"", 0, j)
        hi = t.find("</div>", j) + 6
        return t[:lo] + t[hi:]
    if kind == "unrelated-word-changed":
        return t.replace("SINO FRESH", "SINO-FRESH", 1)
    if kind == "params-band-removed":
        return t.replace(PARAMS, 'class="sf-fdetail2__paramsX"')
    if kind == "address-reverted":
        return CF_ATTR.sub(lambda m: 'data-cfemail="' + cf_reencode(cfd(m.group(1)).replace("sales@", "info@")) + '"', t) \
            if "data-cfemail" in t else t
    if kind == "ldjson-email-injected":
        return t.replace('"email":"sales@zxpet.com"', '"email":"team@zxpet.com"', 1)
    if kind == "asset-from-live-dir":
        return t.replace("/themes/" + PREFLIGHT_DIR + "/", "/themes/" + STATIC_DIR + "/")
    if kind == "literal-shortcode-left":
        j = t.find(CAPSULE_START)
        if j < 0:
            return t
        end = t.find("</a>", j) + 4
        return t[:j] + "[sf_inquiry_button]" + t[end:]
    return t


CAPSULE_START_FULL = (
    '<a class="sf-float-btn sf-float-btn--inquiry" href="/contact/#quote" '
    'data-sf-inquiry-open hidden><span class="sf-float-btn__label">Send Inquiry</span></a>'
)
DIALOG_SNIPPET = (
    '<div class="sf-inquiry-modal" hidden><div class="sf-inquiry-modal__panel">'
    '<div class="sf-inquiry-modal__body"></div></div></div>'
)


def cf_reencode(text):
    """Re-obfuscate an address the way Cloudflare would, with a fixed key."""
    key = 0x5A
    return ("%02x" % key) + "".join("%02x" % (ord(c) ^ key) for c in text)


def matrix(base_dir, cand_dir):
    base, _, _ = read_dir(base_dir)
    cand, _, _ = read_dir(cand_dir)
    import tempfile
    scratch = tempfile.mkdtemp(prefix="b2d-h4-matrix-")
    kinds = [
        "capsule-missing", "dialog-missing", "capsule-on-a-plain-page",
        "dialog-on-a-plain-page", "ver-not-bumped", "step-title-reworded",
        "steps-reduced-to-three", "selection-label-invented",
        "capsule-not-first-child", "capsule-loses-hidden",
        "honeypot-input-removed", "unrelated-word-changed",
        "params-band-removed", "address-reverted", "ldjson-email-injected",
        "asset-from-live-dir", "literal-shortcode-left",
    ]
    lines, caught = [], 0
    for kind in kinds:
        victim_dir = os.path.join(scratch, kind)
        os.makedirs(victim_dir, exist_ok=True)
        for fn, t in cand.items():
            with open(os.path.join(victim_dir, fn), "w", encoding="utf-8") as fh:
                fh.write(mutate(fn, t, kind))
        # The manifest travels with the pages; without it gate [0] would fail on
        # every variant for a reason that has nothing to do with the mutation,
        # and "CAUGHT" would stop meaning anything.
        manifest = os.path.join(cand_dir, "MANIFEST.tsv")
        if os.path.exists(manifest):
            shutil.copyfile(manifest, os.path.join(victim_dir, "MANIFEST.tsv"))
        rep = run(base_dir, victim_dir)
        gates = sorted({m.split("]")[0].lstrip("[") for m in rep.fails})
        mark = "CAUGHT" if rep.fails else "ESCAPED"
        if rep.fails:
            caught += 1
        lines.append("  %-28s %-8s %s" % (kind, mark, " ".join("[" + g + "]" for g in gates)))
    lines.append("  %d/%d variants caught" % (caught, len(kinds)))
    return "\n".join(lines), caught == len(kinds)


def negcontrol(base_dir, cand_dir):
    """Five named controls: each must fail for its own stated reason."""
    import tempfile
    out, passed = [], 0

    def attempt(label, bdir, cdir, needle):
        nonlocal passed
        rep = run(bdir, cdir)
        hit = [m for m in rep.fails if needle in m]
        if hit:
            passed += 1
            out.append("  %-32s FAIL (as required)  %s" % (label, hit[0]))
        else:
            out.append("  %-32s NOT CAUGHT  (wanted %r, got %s)"
                       % (label, needle, rep.fails[:2] or "no failures"))

    tmp = tempfile.mkdtemp(prefix="b2d-h4-negctl-")

    # 1. the served manifest is gone
    d = os.path.join(tmp, "no-manifest")
    shutil.copytree(cand_dir, d)
    os.remove(os.path.join(d, "MANIFEST.tsv"))
    attempt("served-manifest-missing", base_dir, d, "MANIFEST.tsv is missing")

    # 2. the baseline directory is empty
    d = os.path.join(tmp, "empty-base")
    os.makedirs(d)
    attempt("baseline-empty", d, cand_dir, "sides are not 75/75")

    # 3. the candidate is a copy of the baseline
    d = os.path.join(tmp, "same-as-base")
    shutil.copytree(base_dir, d)
    attempt("candidate-equals-baseline", base_dir, d, "capsule and parameter band disagree")

    # 4. one page is missing from the candidate
    d = os.path.join(tmp, "missing-page")
    shutil.copytree(cand_dir, d)
    victims = [f for f in sorted(os.listdir(d)) if f.endswith(".html")]
    os.remove(os.path.join(d, victims[0]))
    attempt("page-missing-from-candidate", base_dir, d, "sides are not 75/75")

    # 5. the version token never moved
    d = os.path.join(tmp, "ver-unchanged")
    shutil.copytree(cand_dir, d)
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".html"):
            continue
        p = os.path.join(d, fn)
        with open(p, encoding="utf-8", errors="replace") as fh:
            t = fh.read()
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(t.replace("ver=" + NEW_VER, "ver=" + OLD_VER))
    attempt("ver-token-unchanged", base_dir, d, "still advertise ver=" + OLD_VER)

    out.append("  %d/5 controls failed as required" % passed)
    return "\n".join(out), passed == 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline")
    ap.add_argument("--candidate")
    ap.add_argument("--json")
    ap.add_argument("--aa", action="store_true")
    ap.add_argument("--matrix", action="store_true")
    ap.add_argument("--negctl", action="store_true")
    args = ap.parse_args()

    if args.matrix:
        text, good = matrix(args.baseline, args.candidate)
        print(text)
        print("MATRIX VERDICT: " + ("PASS" if good else "FAIL"))
        return 0 if good else 1

    if args.negctl:
        text, good = negcontrol(args.baseline, args.candidate)
        print(text)
        print("NEGCONTROL VERDICT: " + ("PASS" if good else "FAIL"))
        return 0 if good else 1

    rep = run(args.baseline, args.candidate, expect_change=not args.aa)
    print("\n".join(rep.lines))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"fails": rep.fails, "data": rep.data}, fh, indent=2, sort_keys=True)
    label = "A/A" if args.aa else "MAIN"
    if args.aa:
        print("%s VERDICT: %s — %d failures (%s)"
              % (label, "PASS" if len(rep.fails) == 1 else "FAIL", len(rep.fails),
                 "only the deliberate [1]" if len(rep.fails) == 1 else "spurious"))
        return 0 if len(rep.fails) == 1 else 1
    print("%s VERDICT: %s — %d failed assertions"
          % (label, "PASS" if not rep.fails else "FAIL", len(rep.fails)))
    return 0 if not rep.fails else 1


if __name__ == "__main__":
    sys.exit(main())
