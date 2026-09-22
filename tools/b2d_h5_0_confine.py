#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H5-0 (h1 -> parameters column, aside -> div) — the confined-proof gate.

WHAT THIS GATE HAS TO PROVE

The batch moves the product name from the hero band into the parameters
column and demotes the hero's heading to a div, on the 42 pages that carry the
two-column band. Per detail page the declared change is exactly:

  1. the hero heading swaps element, keeping its class:
     <h1 class="sf-formula-hero__title">T</h1>
     -> <div class="sf-formula-hero__title">T</div>
  2. one line is inserted at the top of the parameters column:
     <h1 class="sf-fdetail2__title">T</h1>  (T = the same string)
  3. the column's own element changes, keeping its class:
     <aside class="wp-block-group sf-fdetail2__side ..."> -> <div ...>, and
     its matching close tag;
  4. the hero's comment is rewritten, and a new comment is placed above the
     column, both of which the block parser passes through verbatim;
  5. the theme version token moves 2.10.59 -> 2.10.60, on all 75 pages,
     because style.css is one file and it moved.

So the whole batch collapses to one statement, per page:

    undo_declared(candidate) == fold_ver(baseline)

after norm() on BOTH sides. Anything else that moved shows up as a difference,
which is what a limited proof is for.

Three things are carried in from earlier batches and are not optional:

  * the noise masks are IMPORTED from tools/sf_masked_cmp.py, minus the two
    Cloudflare entries that erase which address is encoded — retyping the set
    would let the two tools drift, and the assertion that exactly two were
    dropped stops someone "helpfully" putting them back;
  * every blob Cloudflare obfuscated is DECODED before comparing, because the
    key is fresh on every response;
  * the declared change set is DERIVED from the two commits
    (git show <sha>:templates/single-sf_formula.html), not retyped. The two
    comment blocks in particular are long; a transcription slip in a constant
    would show up as 42 "changed" pages and read like a product defect.

WHY THERE IS A JSON-LD GATE HERE AND NOT A BYTE GATE

Batch H5 stopped at step 0 partly because a byte gate cannot express "this
schema change is legitimate". This batch changes no schema at all, so the
strongest available claim is the semantic one: parse every ld+json block on
all 75 pages and require deep equality. That also happens to be the check that
would catch the one plausible way this batch could have broken schema — the
eight dosage pages keep their hero h1, and functions.php:4765 reads it out of
templates/page-{slug}.html for their Product name.

usage:
    b2d_h5_0_confine.py --baseline DIR --candidate DIR [--json out.json]
    b2d_h5_0_confine.py --baseline DIR --candidate DIR --aa
    b2d_h5_0_confine.py --baseline DIR --candidate DIR --matrix
    b2d_h5_0_confine.py --baseline DIR --candidate DIR --negctl
"""
import argparse
import collections
import json
import os
import re
import shutil
import subprocess
import sys

HOST = "https://dev.zxpet.com"
VER_TOKEN = "ver=<TOKEN>"
NEW_VER = "2.10.60"
OLD_VER = "2.10.59"
STATIC_DIR = "sinofresh-theme"
PREFLIGHT_DIR = "sinofresh-theme-preflight"

# The two commits the declared change is read out of. BASE is the pre-flight
# copy this batch was gated against (the H4 tree, ver=2.10.59); CAND is the
# batch itself. An abbreviated sha is refused by the dev box, so these are full.
BASE_SHA = "92dee472239edcaf8f209efa561ac3016a45a564"
CAND_SHA = "084b24692e716b62514ab9190f88ead1e38e5944"
TEMPLATE = "sinofresh-theme/templates/single-sf_formula.html"

HERO_COMMENT_MARKER = "<!-- Hero:"
COL_COMMENT_MARKER = "<!-- Batch H5-0:"

# The column and the heading are matched through their class rather than
# through a literal tag string: WordPress appends its own layout classes
# (is-layout-flow, wp-block-group-is-layout-flow) to the saved markup, so a
# literal <div class="wp-block-group sf-fdetail2__side"> never appears in a
# rendered page and a literal-based strip would silently do nothing.
HERO_TITLE = re.compile(r'<(h1|div) class="sf-formula-hero__title">([^<]*)</(h1|div)>')
SIDE_OPEN = re.compile(r'<(div|aside)\b([^>]*class="[^"]*\bsf-fdetail2__side\b[^"]*"[^>]*)>')
NEW_TITLE = re.compile(r'\n<h1 class="sf-fdetail2__title">([^<]*)</h1>')
NEW_TITLE_TAG = '<h1 class="sf-fdetail2__title">'
INTRO_P = '<p class="sf-fdetail2__intro"'
# \b keeps a rename to sf-fdetail2__paramsX from scoring as the band.
BAND = re.compile(r'class="[^"]*\bsf-fdetail2__params\b[^"]*"')
COLUMN = re.compile(r'class="[^"]*\bsf-fdetail2__side\b[^"]*"')
H1 = re.compile(r"<h1[\s>]", re.I)
VER = re.compile(r"ver=([0-9][0-9.]*)")
LDJSON = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S)
CF_ATTR = re.compile(r'data-cfemail="([0-9a-f]+)"')
CF_LINK = re.compile(r"email-protection#([0-9a-f]+)")

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(os.path.dirname(FILE_DIR), STATIC_DIR)


def git_show(sha, path):
    p = subprocess.run(["git", "show", "%s:%s" % (sha, path)],
                       cwd=os.path.dirname(FILE_DIR),
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("git show %s:%s failed: %s" % (sha, path, p.stderr.strip()))
    return p.stdout


def template_comment(sha, marker):
    """The comment block starting at `marker`, up to and including its -->.

    Read out of the commit rather than retyped: these blocks are five and six
    lines long and carry em dashes, and a one-character slip would present as
    42 changed pages.
    """
    t = git_show(sha, TEMPLATE)
    i = t.find(marker)
    if i < 0:
        raise SystemExit("marker %r not found in %s:%s" % (marker, sha, TEMPLATE))
    j = t.find("-->", i)
    if j < 0:
        raise SystemExit("unterminated comment at %r in %s" % (marker, sha))
    return t[i:j + 3]


def declared():
    """The declared change set, derived from the two commits."""
    old_hero = template_comment(BASE_SHA, HERO_COMMENT_MARKER)
    new_hero = template_comment(CAND_SHA, HERO_COMMENT_MARKER)
    new_col = template_comment(CAND_SHA, COL_COMMENT_MARKER)
    base_tpl = git_show(BASE_SHA, TEMPLATE)
    cand_tpl = git_show(CAND_SHA, TEMPLATE)
    if old_hero == new_hero:
        raise SystemExit("the hero comment did not change between the two commits")
    if new_col in base_tpl or new_col not in cand_tpl:
        raise SystemExit("the column comment is not new in %s" % CAND_SHA)
    if new_hero in base_tpl or new_hero not in cand_tpl:
        raise SystemExit("the rewritten hero comment is not new in %s" % CAND_SHA)
    if old_hero not in base_tpl or old_hero in cand_tpl:
        raise SystemExit("the old hero comment did not leave the template")
    return {"old_hero": old_hero, "new_hero": new_hero, "new_col": new_col}


D = declared()


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


def matching_div_close(t, start):
    """Index of the </div> that closes the <div ...> opening at `start`."""
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
            return i - 6
    return -1


def undo_declared(t, counts=None, titles=None):
    """Reverse the declared change, byte-exactly.

    counts, when passed, accrues how many of each were reversed — the census
    gate reads it, and an off-by-one in the undo would otherwise show up as 42
    "changed" pages instead of as a broken tool. On the MAIN run the baseline
    predates the batch, so every call here is a no-op there, which is why the
    baseline side is passed through this function too: on the A/A run the
    baseline IS a second capture of the candidate and carries all of it, and
    undoing only one side would convict all 42 pages of a change that never
    happened.
    """
    def bump(key):
        if counts is not None:
            counts[key] += 1

    # 1. the inserted heading, with the newline that precedes it.
    while True:
        m = NEW_TITLE.search(t)
        if not m:
            break
        if titles is not None:
            titles.append(m.group(1))
        t = t[:m.start()] + t[m.end():]
        bump("title")

    # 2. the column's element, open and close.
    while True:
        m = SIDE_OPEN.search(t)
        if not m:
            break
        if m.group(1) != "div":
            break
        close = matching_div_close(t, m.start())
        if close < 0:
            break
        t = t[:close] + "</aside>" + t[close + 6:]
        t = t[:m.start()] + "<aside" + m.group(2) + ">" + t[m.end():]
        bump("column")

    # 3. the hero heading's element.
    def hero_sub(m):
        if m.group(1) != "div":
            return m.group(0)
        bump("hero")
        return '<h1 class="sf-formula-hero__title">%s</h1>' % m.group(2)
    t = HERO_TITLE.sub(hero_sub, t)

    # 4. the comments.
    #    The column comment was inserted as a whole line, so the newline that
    #    followed it comes back out with it: the template ran
    #    "... </section> \n <!-- /wp:group --> \n <!-- Batch H5-0: --> \n
    #     <!-- wp:group --> \n <div ...>", the two block delimiters are
    #    consumed, and the rendered text between the gallery's close and the
    #    column is "\\n\\n" + comment + "\\n\\n". Removing the comment alone would
    #    leave three newlines where the baseline has two and fail all 42 pages
    #    for a reason that is not a product defect.
    if D["new_col"] + "\n" in t:
        t = t.replace(D["new_col"] + "\n", "")
        bump("col_comment")
    elif D["new_col"] in t:
        t = t.replace(D["new_col"], "")
        bump("col_comment")
    if D["new_hero"] in t:
        t = t.replace(D["new_hero"], D["old_hero"])
        bump("hero_comment")

    return t


def ld_objects(t):
    """Every ld+json block, parsed and canonicalised.

    Parsed, not compared as text: the EN pages emit compact JSON and the ZH
    pages emit it pretty-printed, so a literal comparison is blind on half the
    site (batch H3 measured 21/21 pages that way)."""
    out = []
    for b in LDJSON.findall(t):
        b = norm(b)
        try:
            out.append(json.dumps(json.loads(b), sort_keys=True, ensure_ascii=False))
        except Exception:
            out.append("UNPARSEABLE:" + b[:80])
    return out


def page_facts(t):
    return {
        "band": len(BAND.findall(t)),
        "column": len(COLUMN.findall(t)),
        "new_title": len(NEW_TITLE.findall(t)),
        "hero_div": len(re.findall(r'<div class="sf-formula-hero__title">', t)),
        "hero_h1": len(re.findall(r'<h1 class="sf-formula-hero__title">', t)),
        "aside": len(re.findall(r"<aside\b", t)),
        "h1": len(H1.findall(t)),
        "ldjson": ld_objects(t),
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


# ---------------------------------------------------------------------- gates

def run(base_dir, cand_dir, expect_change=True):
    rep = Report()
    base, base_manifest, base_header = read_dir(base_dir)
    cand, cand_manifest, cand_header = read_dir(cand_dir)
    base_codes = manifest_codes(base_manifest)
    cand_codes = manifest_codes(cand_manifest)

    # [0] the two sides themselves, and where their bytes came from
    if len(base) != 75 or len(cand) != 75:
        rep.fail("[0] sides are not 75/75 (baseline %d, candidate %d)" % (len(base), len(cand)))
    else:
        rep.ok("[0] both sides hold 75 pages")
    if not base_codes:
        rep.fail("[0] baseline MANIFEST.tsv is missing")
        rep.note("this batch's baseline is the previous batch's pre-flight copy "
                 "(ver=%s, commit %s)." % (OLD_VER, BASE_SHA[:7]))
    if not cand_codes:
        rep.fail("[0] candidate MANIFEST.tsv is missing")
    bad = [p for p, c in cand_codes.items() if c != "200"]
    if bad:
        rep.fail("[0] candidate has %d non-200 paths: %s" % (len(bad), bad[:5]))
    for label, header in (("candidate", cand_header), ("baseline", base_header)):
        if header is None:
            rep.fail("[0] the %s manifest records no request header" % label)
        elif "X-SF-Preflight" not in header:
            rep.fail("[0] the %s was fetched without the pre-flight header: %r" % (label, header))
    if cand_header and base_header and "X-SF-Preflight" in cand_header and "X-SF-Preflight" in base_header:
        rep.ok("[0] both manifests record the pre-flight header")

    if not cand or not base:
        return rep

    # Both sides must have been served by the copy, never by sinofresh-theme/:
    # what is under test is a theme directory, and a capture that quietly came
    # from the live theme would pass every gate while proving nothing. In A/A
    # the "baseline" is a second capture of the candidate state, so the
    # expectation is the same in both modes.
    dirs = collections.Counter()
    for t in list(cand.values()) + list(base.values()):
        for d in re.findall(r"/themes/([A-Za-z0-9_.-]+)/", t):
            dirs[d] += 1
    if set(dirs) != {PREFLIGHT_DIR}:
        rep.fail("[0] assets do not all resolve into %s: %s" % (PREFLIGHT_DIR, dict(dirs)))
    else:
        rep.ok("[0] every asset on both sides resolves into %s/" % PREFLIGHT_DIR)

    band = [fn for fn, t in cand.items() if page_facts(t)["band"]]
    column = [fn for fn, t in cand.items() if page_facts(t)["column"]]
    with_title = [fn for fn, t in cand.items() if page_facts(t)["new_title"]]
    rep.data["band"] = len(band)
    rep.data["column"] = len(column)
    rep.data["with_title"] = len(with_title)

    # [1] the declared change, as a census on the candidate alone
    if expect_change:
        if len(band) != 42:
            rep.fail("[1] the parameters band is on %d candidate pages, expected 42" % len(band))
        if sorted(band) != sorted(column):
            rep.fail("[1] band and column disagree: %d vs %d pages" % (len(band), len(column)))
        if sorted(with_title) != sorted(band):
            rep.fail("[1] the new h1 is on %d pages but the band is on %d, and they are not the same set"
                     % (len(with_title), len(band)))
        if sorted(band) == sorted(column) == sorted(with_title):
            rep.ok("[1] band = column = new h1 = 42 pages, the same set")

        # The site carries one legitimately-different aside on every page — the
        # inquiry basket drawer — so "no asides left anywhere" would be the
        # wrong claim, and asserting it is how this gate first failed on all 75
        # pages. What the change does claim is narrower and checkable: the
        # element carrying sf-fdetail2__side stops being an aside, on exactly
        # the 42 band pages, and nothing else moves.
        side_aside = re.compile(r'<aside\b[^>]*\bsf-fdetail2__side\b')
        cand_side = [fn for fn, t in cand.items() if side_aside.search(t)]
        base_side = [fn for fn in cand if side_aside.search(base.get(fn, ""))]
        if cand_side:
            rep.fail("[1] %d candidate pages still carry the column as an aside: %s"
                     % (len(cand_side), cand_side[:4]))
        elif len(base_side) != 42:
            rep.fail("[1] the baseline shows the column as an aside on %d pages, expected 42"
                     % len(base_side))
        else:
            rep.ok("[1] the column is no longer an aside on any candidate page "
                   "(in the baseline it was one on all 42)")

        aside_shift = []
        for fn in sorted(cand):
            fb = page_facts(base.get(fn, ""))
            fc = page_facts(cand[fn])
            want = fb["aside"] - (1 if fb["column"] else 0)
            if fc["aside"] != want:
                aside_shift.append((fn, fb["aside"], fc["aside"], want))
        if aside_shift:
            rep.fail("[1] the aside census moved by more than the column on %d pages: %s"
                     % (len(aside_shift), aside_shift[:3]))
        else:
            rep.ok("[1] exactly one aside disappeared per band page and nowhere else "
                   "(the basket drawer survives on all 75)")

        still_h1 = [fn for fn, t in cand.items() if page_facts(t)["hero_h1"]]
        as_div = [fn for fn, t in cand.items() if page_facts(t)["hero_div"]]
        if still_h1:
            rep.fail("[1] the hero heading is still an h1 on %d pages: %s" % (len(still_h1), still_h1[:4]))
        if sorted(as_div) != sorted(band):
            rep.fail("[1] the hero div is on %d pages, the band on %d, and they are not the same set"
                     % (len(as_div), len(band)))
        if not still_h1 and sorted(as_div) == sorted(band):
            rep.ok("[1] the hero heading is a div on exactly the 42 band pages, an h1 on none")

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
    #     norm() on BOTH sides: every page carries Cloudflare blobs (the footer
    #     mailto, the topbar mailto, the Organization schema) whose key is fresh
    #     on every response, so comparing raw bytes would convict all 75 pages.
    diff_pages = []
    counts = collections.Counter()
    base_counts = collections.Counter()
    titles = []
    for fn in sorted(cand):
        if fn not in base:
            rep.fail("[2] candidate page missing from the baseline: %s" % fn)
            continue
        stripped = norm(fold_ver(undo_declared(cand[fn], counts, titles)))
        other = norm(fold_ver(undo_declared(base[fn], base_counts)))
        if stripped != other:
            diff_pages.append(fn)
    rep.data["stripped"] = dict(counts)
    rep.data["titles"] = sorted(set(titles))
    rep.data["diff_pages"] = len(diff_pages)
    if diff_pages:
        rep.fail("[2] %d pages differ beyond the declared change: %s"
                 % (len(diff_pages), ", ".join(diff_pages[:6])))
    else:
        rep.ok("[2] undo_declared(candidate) == baseline byte-for-byte after norm on all 75 pages")
    if expect_change:
        for key, want in (("title", 42), ("column", 42), ("hero", 42), ("col_comment", 42), ("hero_comment", 42)):
            if counts[key] != want:
                rep.fail("[2] reversed %d of the %s, expected %d" % (counts[key], key, want))
        if all(counts[k] == 42 for k in ("title", "column", "hero", "col_comment", "hero_comment")):
            rep.ok("[2] each of the five declared edits was reversed exactly 42 times")
        if not titles:
            rep.fail("[2] no inserted heading was found to read a title from")
        else:
            rep.ok("[2] the inserted heading is on 42 pages and carries %d distinct title(s)"
                   % len(set(titles)))

    # [3] the 33 pages that must be untouched but for the version token
    plain = [fn for fn in cand if not page_facts(cand[fn])["band"]]
    rep.data["plain"] = len(plain)
    if expect_change:
        if len(plain) != 33:
            rep.fail("[3] %d pages carry no parameters band, expected 33" % len(plain))
        else:
            rep.ok("[3] 33 pages carry no parameters band")
        moved = []
        for fn in plain:
            if page_facts(cand[fn])["new_title"] or page_facts(cand[fn])["hero_div"]:
                moved.append(fn)
        if moved:
            rep.fail("[3] the change leaked onto %d pages without the band: %s"
                     % (len(moved), moved[:4]))
        else:
            rep.ok("[3] no page without the band carries either edit")

    # [4] the new heading is the column's first element and names the record
    struct_bad = []
    for fn in with_title:
        t = cand[fn]
        m = SIDE_OPEN.search(t)
        if not m:
            struct_bad.append((fn, "no column"))
            continue
        seg = t[m.end():m.end() + 80]
        if not re.match(r'\s*<h1 class="sf-fdetail2__title">', seg):
            struct_bad.append((fn, "the heading is not the column's first child"))
            continue
        k = t.find(NEW_TITLE_TAG, m.end())
        j = t.find(INTRO_P, m.end())
        if j < 0:
            struct_bad.append((fn, "no intro paragraph in the column"))
        elif not (m.end() < k < j):
            struct_bad.append((fn, "the heading does not precede the intro"))
    if struct_bad:
        rep.fail("[4] the heading's place in the column is wrong on %d pages: %s"
                 % (len(struct_bad), struct_bad[:3]))
    else:
        rep.ok("[4] on all 42 pages the heading is the column's first child, ahead of the intro")

    # [5] one string, three places: the breadcrumb's current crumb, the hero and
    #     the new heading must be the same text as the baseline's hero heading.
    text_bad = []
    for fn in with_title:
        hero = HERO_TITLE.search(cand[fn])
        new = NEW_TITLE.search(cand[fn])
        crumb = re.search(r'<span class="sf-breadcrumb__crumb sf-breadcrumb__current"[^>]*>([^<]*)</span>',
                          cand[fn])
        base_hero = HERO_TITLE.search(base.get(fn, ""))
        if not hero or not new:
            text_bad.append((fn, "a heading is missing"))
            continue
        got = {hero.group(2), new.group(1), crumb.group(1) if crumb else None}
        if len(got) != 1:
            text_bad.append((fn, "the three headings disagree: %s" % sorted(str(g) for g in got)))
        elif base_hero and base_hero.group(2) != hero.group(2):
            text_bad.append((fn, "the title changed: %r -> %r" % (base_hero.group(2), hero.group(2))))
    if text_bad:
        rep.fail("[5] the product name is not one string across the page on %d pages: %s"
                 % (len(text_bad), text_bad[:3]))
    else:
        rep.ok("[5] breadcrumb, hero and column heading carry one identical string, unchanged "
               "from the baseline, on all 42 pages")

    # [6] structured data, compared as parsed objects
    ld_bad = []
    for fn in sorted(base):
        fb, fc = page_facts(base[fn]), page_facts(cand.get(fn, ""))
        if fb["ldjson"] != fc["ldjson"]:
            ld_bad.append(fn)
    if ld_bad:
        rep.fail("[6] parsed JSON-LD changed on %d pages: %s" % (len(ld_bad), ld_bad[:5]))
    else:
        rep.ok("[6] every ld+json block parses and is deeply equal on all 75 pages")

    # [6b] ...and the blocks are actually there, so "equal" cannot mean "both empty"
    empty = [fn for fn in sorted(cand) if not page_facts(cand[fn])["ldjson"]]
    if empty:
        rep.fail("[6] %d candidate pages carry no JSON-LD at all: %s" % (len(empty), empty[:4]))
    else:
        rep.ok("[6] all 75 candidate pages carry at least one ld+json block")

    # [7] the h1 census, both sides
    census_bad = []
    for fn in sorted(base):
        hb = page_facts(base[fn])["h1"]
        hc = page_facts(cand.get(fn, ""))["h1"]
        if hc != 1:
            census_bad.append((fn, "candidate has %d h1" % hc))
        elif hb != hc:
            census_bad.append((fn, "h1 count moved %d -> %d" % (hb, hc)))
    if census_bad:
        rep.fail("[7] the h1 census is wrong on %d pages: %s" % (len(census_bad), census_bad[:4]))
    else:
        rep.ok("[7] exactly one h1 on all 75 pages on both sides, unchanged in count")

    # [8] the eight dosage pages keep their own hero h1, which is what their
    #     Product schema reads out of templates/page-{slug}.html
    dosage = [fn for fn in sorted(cand) if re.match(r"(zh__)?products__", fn)]
    dosage_bad = []
    for fn in dosage:
        t = cand[fn]
        m = re.search(r'<h1[^>]*>([^<]*)</h1>', t)
        b = re.search(r'<h1[^>]*>([^<]*)</h1>', base.get(fn, ""))
        if not m or not b or m.group(1) != b.group(1):
            dosage_bad.append(fn)
    rep.data["dosage"] = len(dosage)
    if dosage_bad:
        rep.fail("[8] a dosage page's hero h1 changed: %s" % dosage_bad[:4])
    else:
        rep.ok("[8] all %d dosage pages keep their own hero h1, byte-identical" % len(dosage))

    return rep


# ----------------------------------------------------------------- sabotage

def mutate(fn, t, kind):
    if kind == "title-line-missing":
        m = NEW_TITLE.search(t)
        return t[:m.start()] + t[m.end():] if m else t
    if kind == "title-on-a-plain-page":
        if NEW_TITLE.search(t):
            return t
        return t.replace("<body", '<h1 class="sf-fdetail2__title">Bogus</h1><body', 1)
    if kind == "hero-div-reverted":
        return HERO_TITLE.sub(lambda m: '<h1 class="sf-formula-hero__title">%s</h1>' % m.group(2), t)
    if kind == "column-still-aside":
        m = SIDE_OPEN.search(t)
        if not m:
            return t
        close = matching_div_close(t, m.start())
        if close < 0:
            return t
        t = t[:close] + "</aside>" + t[close + 6:]
        return t[:m.start()] + "<aside" + m.group(2) + ">" + t[m.end():]
    if kind == "ver-not-bumped":
        return t.replace("ver=" + NEW_VER, "ver=" + OLD_VER)
    if kind == "second-h1-injected":
        return t.replace(INTRO_P, '<h1 class="sf-extra">Second</h1>' + INTRO_P, 1)
    if kind == "title-text-changed":
        m = NEW_TITLE.search(t)
        if not m:
            return t
        return t[:m.start()] + '\n<h1 class="sf-fdetail2__title">Changed Name</h1>' + t[m.end():]
    if kind == "title-not-first-in-column":
        m = NEW_TITLE.search(t)
        if not m:
            return t
        line = t[m.start():m.end()]
        t = t[:m.start()] + t[m.end():]
        j = t.find("</dl>", m.start())
        return t[:j + 5] + line + t[j + 5:] if j > 0 else t
    if kind == "ldjson-email-injected":
        return t.replace('"email":"sales@zxpet.com"', '"email":"team@zxpet.com"', 1)
    if kind == "ldjson-name-reworded":
        return t.replace('"name":"Joint', '"name":"Joints', 1) if "Joint" in t else t
    if kind == "unrelated-word-changed":
        return t.replace("SINO FRESH", "SINO-FRESH", 1)
    if kind == "asset-from-live-dir":
        return t.replace("/themes/" + PREFLIGHT_DIR + "/", "/themes/" + STATIC_DIR + "/")
    if kind == "hero-comment-stale":
        return t.replace(D["new_hero"], D["old_hero"])
    if kind == "dosage-hero-h1-demoted":
        if NEW_TITLE.search(t):
            return t
        m = re.search(r'<h1([^>]*)>([^<]*)</h1>', t)
        return t[:m.start()] + "<div%s>%s</div>" % (m.group(1), m.group(2)) + t[m.end():] if m else t
    return t


def matrix(base_dir, cand_dir):
    base, _, _ = read_dir(base_dir)
    cand, _, _ = read_dir(cand_dir)
    import tempfile
    scratch = tempfile.mkdtemp(prefix="b2d-h5-0-matrix-")
    kinds = [
        "title-line-missing", "title-on-a-plain-page", "hero-div-reverted",
        "column-still-aside", "ver-not-bumped", "second-h1-injected",
        "title-text-changed", "title-not-first-in-column", "ldjson-email-injected",
        "ldjson-name-reworded", "unrelated-word-changed", "asset-from-live-dir",
        "hero-comment-stale", "dosage-hero-h1-demoted",
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

    tmp = tempfile.mkdtemp(prefix="b2d-h5-0-negctl-")

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
    attempt("candidate-equals-baseline", base_dir, d, "the new h1 is on")

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
    ap.add_argument("--declared", action="store_true",
                    help="print the declared change set derived from the commits and exit")
    args = ap.parse_args()

    if args.declared:
        for k in ("old_hero", "new_hero", "new_col"):
            print("--- %s (%d bytes) ---" % (k, len(D[k])))
            print(D[k])
        return 0

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
