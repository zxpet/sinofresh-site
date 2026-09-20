#!/usr/bin/env python3
"""Batch2C Step0 verification: card markup, K1/K7 contracts, JSON payload,
ItemList, still repetition, and cross-check against the DB meta.

Read-only: HTTP fetch + one `wp db query` for the meta side.
"""
import html as htmlmod
import json
import re
import subprocess
import sys

HOST = "https://dev.zxpet.com"
SLAVES = ["soft-chews", "tablets", "powders", "liquids",
          "pastes", "dental-chews", "drops", "fish-oil"]

CARD_RE = re.compile(r'<article class="sf-fcard">(.*?)</article>', re.S)
META_RE = re.compile(r'<figure class="sf-fcard__media">(.*?)</figure>', re.S)
IMG_RE = re.compile(r'<img\b[^>]*>')
JSON_RE = re.compile(r'<script type="application/json" class="sf-formulas-data">(.*?)</script>', re.S)
LD_RE = re.compile(r'<script[^>]*application/ld[+]json[^>]*>(.*?)</script>', re.S)

fails = []


def check(cond, label, detail=""):
    if cond:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}  {detail}")
        fails.append(f"{label} {detail}")


def fetch(url):
    r = subprocess.run(["curl", "-s", "-L", url], capture_output=True, text=True)
    return r.stdout


def attr(tag, name):
    m = re.search(name + r'="([^"]*)"', tag)
    return m.group(1) if m else None


def db_meta():
    """name -> specs, per form, straight from the DB."""
    sql = ("SELECT p.post_title, t.slug, m.meta_value "
           "FROM wp_posts p "
           "JOIN wp_term_relationships tr ON tr.object_id=p.ID "
           "JOIN wp_term_taxonomy tt ON tt.term_taxonomy_id=tr.term_taxonomy_id "
           "AND tt.taxonomy='sf_formula_form' "
           "JOIN wp_terms t ON t.term_id=tt.term_id "
           "JOIN wp_postmeta m ON m.post_id=p.ID AND m.meta_key='sf_formula_specs' "
           "WHERE p.post_type='sf_formula' AND p.post_status='publish'")
    out = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=10", "root@65.49.215.152",
         f"cd /var/www/dev.zxpet.com/public && wp db query \"{sql}\" --skip-column-names"],
        capture_output=True, text=True).stdout
    rows = {}
    for line in out.strip().splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            rows[htmlmod.unescape(parts[0])] = (parts[1], parts[2])
    return rows


def main():
    print("=== fetching DB meta ===")
    meta = db_meta()
    print(f"  publish formulas with specs meta: {len(meta)}")
    check(len(meta) == 21, "DB has 21 publish formulas", f"got {len(meta)}")

    total_cards = 0
    for slug in SLAVES:
        url = f"{HOST}/products/{slug}/"
        h = fetch(url)
        print(f"\n=== /products/{slug}/  ({len(h)} bytes) ===")
        m = re.search(r'<div class="sf-fgrid"[^>]*>', h)
        if not m:
            check(False, f"{slug}: .sf-fgrid present")
            continue
        cols = attr(m.group(0), "style")
        cards = CARD_RE.findall(h)

        # --- payload ----------------------------------------------------
        jm = JSON_RE.search(h)
        payload = json.loads(jm.group(1)) if jm else []
        check(jm is not None, f"{slug}: .sf-formulas-data present")
        check(len(payload) == len(cards),
              f"{slug}: payload count == card count ({len(payload)}/{len(cards)})")
        check(all(p["form"] == slug for p in payload),
              f"{slug}: payload form == page slug")
        check(not any("&amp;" in json.dumps(p) for p in payload),
              f"{slug}: K4 payload entity-free")

        # --- ItemList (the page carries several ld+json blocks) ----------
        ld = {}
        for block in LD_RE.findall(h):
            try:
                cand = json.loads(block)
            except Exception:
                continue
            if isinstance(cand, dict) and cand.get("@type") == "ItemList":
                ld = cand
                break
        check(bool(ld), f"{slug}: ItemList block present")
        check(ld.get("numberOfItems") == len(cards),
              f"{slug}: ItemList numberOfItems == {len(cards)}",
              f"got {ld.get('numberOfItems')}")
        check(ld.get("name") == f"Standard Formulas — "
              + {"soft-chews": "Soft Chews", "tablets": "Tablets", "powders": "Powders",
                 "liquids": "Liquids", "pastes": "Pastes", "dental-chews": "Dental Chews",
                 "drops": "Drops", "fish-oil": "Fish Oil"}[slug],
              f"{slug}: ItemList name", f"got {ld.get('name')!r}")

        srcs, ratios, fits, alts, media_n = [], [], [], [], 0
        for idx, c in enumerate(cards):
            name_m = re.search(r'<h3 class="sf-fcard__name">(?:<a [^>]*>)?(.*?)(?:</a>)?</h3>', c)
            name = htmlmod.unescape(name_m.group(1)) if name_m else None
            use_m = re.search(r'<span class="sf-fcard__use">(.*?)</span>', c)
            use = use_m.group(1) if use_m else None
            spec_m = re.search(r'<p class="sf-fcard__spec">(.*?)</p>', c)
            spec = htmlmod.unescape(spec_m.group(1)) if spec_m else None
            cta_m = re.search(r'<button type="button" class="sf-formula__cta" data-formula="([^"]*)">', c)
            body = '<div class="sf-fcard__body">' in c
            media = META_RE.findall(c)

            # K7: media (optional) then exactly one body, body last
            check(body, f"{slug}#{idx+1}: .sf-fcard__body present")
            check(c.startswith("<figure") or c.startswith("<div"), f"{slug}#{idx+1}: media-first anatomy")

            # K1
            check(cta_m is not None and htmlmod.unescape(cta_m.group(1)) == name,
                  f"{slug}#{idx+1}: K1 data-formula == name", f"{cta_m and cta_m.group(1)!r} vs {name!r}")

            # meta cross-check
            db = meta.get(name)
            check(db is not None and db[0] == slug, f"{slug}#{idx+1}: DB form slug", f"{db}")
            check(db is not None and db[1] == spec, f"{slug}#{idx+1}: spec text == DB meta",
                  f"{spec!r} vs {db and db[1]!r}")

            if media:
                media_n += 1
                img = IMG_RE.search(media[0])
                check(img is not None, f"{slug}#{idx+1}: media has <img>")
                if img:
                    srcs.append(attr(img.group(0), "src"))
                    alts.append(attr(img.group(0), "alt"))
                    check(attr(img.group(0), "src") not in (None, ""),
                          f"{slug}#{idx+1}: img has non-empty src")
                    check(attr(img.group(0), "loading") == "lazy",
                          f"{slug}#{idx+1}: img lazy")
                    # no empty figure: media must contain exactly one img
                    check(len(IMG_RE.findall(media[0])) == 1,
                          f"{slug}#{idx+1}: exactly one img")

        check(media_n == len(cards), f"{slug}: every card has a media block ({media_n}/{len(cards)})")
        check(len(set(srcs)) == 1 and srcs and srcs[0].endswith(f"{slug}.webp"),
              f"{slug}: same-page still repetition == own dosage render", f"{set(srcs)}")
        check(all(f"SINO FRESH " in a and "private label pet supplement product" in a
                  for a in alts), f"{slug}: alt follows dosage-tile convention")
        total_cards += len(cards)
        print(f"  -> cols={cols} cards={len(cards)} media={media_n} src={srcs[0] if srcs else None}")

    check(total_cards == 21, "total cards across 8 pages == 21", f"got {total_cards}")

    print("\n=== result ===")
    if fails:
        print(f"{len(fails)} FAILURE(S):")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("ALL CHECKS PASS")


if __name__ == "__main__":
    main()
