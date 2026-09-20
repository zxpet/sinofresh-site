#!/usr/bin/env python3
"""Rewrite the three Quality-page blocks (QC lab / QC steps / palatability).

Line-number based with hard assertions on both edges, applied back-to-front so
earlier edits cannot shift the indices of later ones. Exits non-zero without
writing if any anchor does not match exactly.
"""
import sys

P = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme/templates/page-quality.html"

src = open(P, encoding="utf-8").read()
lines = src.split("\n")


def seg(a, b):
    """1-based inclusive slice."""
    return "\n".join(lines[a - 1:b])


# ---- anchors ---------------------------------------------------------------
CHECKS = [
    (97, "<!-- wp:columns -->"),
    (151, "<!-- /wp:columns -->"),
    (160, "<!-- wp:columns -->"),
    (287, "<!-- /wp:columns -->"),
    (348, "<!-- wp:columns -->"),
    (403, "<!-- /wp:columns -->"),
]
for ln, want in CHECKS:
    got = lines[ln - 1].strip()
    if got != want:
        sys.exit(f"ANCHOR FAIL line {ln}: expected {want!r}, got {got!r}")

BLOCKS = {
    (97, 151): ["equip-hplc.webp", "equip-gc.webp", "equip-aas.webp"],
    (160, 287): ["qc-raw-material.webp", "qc-retention.webp"],
    (348, 403): ["Panel Selection", "Data Review"],
}
for (a, b), needles in BLOCKS.items():
    body = seg(a, b)
    for n in needles:
        if n not in body:
            sys.exit(f"CONTENT FAIL in {a}-{b}: {n} not found")

# ---- new markup ------------------------------------------------------------
EQ = [
    ("equip-hplc.webp", "SINO FRESH HPLC analytical instrument in the QC laboratory",
     "HPLC", "High-Performance Liquid Chromatography verifies active ingredient content against specification for every batch."),
    ("equip-gc.webp", "SINO FRESH gas chromatography instrument in the QC laboratory",
     "GC", "Gas Chromatography screens fatty acid profiles and detects residual solvents."),
    ("equip-aas.webp", "SINO FRESH atomic absorption spectrometer in the QC laboratory",
     "AAS", "Atomic Absorption Spectroscopy tests heavy metals to safe limits."),
    ("equip-placeholder.webp", "Placeholder photo - replace with a real SINO FRESH microscopy image",
     "Microscopy", "Microscopic examination confirms particle uniformity and screens for foreign matter."),
    ("equip-placeholder.webp", "Placeholder photo - replace with a real SINO FRESH stability chamber image",
     "Stability Chamber", "Accelerated and real-time stability studies support every shelf-life claim."),
    ("equip-placeholder.webp", "Placeholder photo - replace with a real SINO FRESH sample preparation image",
     "Sample Preparation", "Samples are homogenised, weighed and labelled to protocol before analysis."),
]

qc_lab = ['<!-- wp:gallery {"className":"sf-eq","columns":3,"linkTo":"none"} -->',
          '<figure class="wp-block-gallery has-nested-images columns-3 sf-eq">']
for src_name, alt, name, desc in EQ:
    qc_lab += [
        '<!-- wp:image {"sizeSlug":"large","linkDestination":"none","className":"sf-eq__item"} -->',
        f'<figure class="wp-block-image size-large sf-eq__item"><img src="/wp-content/uploads/2026/09/{src_name}" alt="{alt}" width="800" height="600" loading="lazy"/><figcaption class="wp-element-caption"><strong>{name}</strong>{desc}</figcaption></figure>',
        '<!-- /wp:image -->',
    ]
qc_lab += ["</figure>", "<!-- /wp:gallery -->"]

STEPS = [
    ("01", "Raw Material Inspection", "Every incoming ingredient is verified against its COA and specification.",
     "qc-raw-material.webp", "SINO FRESH raw material inspection - pet supplement quality control"),
    ("02", "Batching &amp; Weighing", "Two-person verification ensures formula accuracy at dosing.",
     "qc-batching.webp", "SINO FRESH batching and weighing - GMP supplement production"),
    ("03", "In-Process QC", "Critical control points are monitored throughout production.",
     "qc-inprocess.webp", "SINO FRESH in-process quality check on the production line"),
    ("04", "Finished Product Testing", "Each batch is tested for potency, moisture, and safety.",
     "qc-finished.webp", "SINO FRESH finished product testing in the QC laboratory"),
    ("05", "COA Issuance", "A Certificate of Analysis is issued for every single batch.",
     "qc-coa.webp", "SINO FRESH certificate of analysis issuance"),
    ("06", "Retention Sampling", "Samples from every batch are retained under controlled conditions.",
     "qc-retention.webp", "SINO FRESH retention sample storage room"),
]

qc_steps = ["<!-- wp:html -->", '<div class="sf-qs">']
for num, title, desc, img, alt in STEPS:
    qc_steps += [
        '\t<article class="sf-qs__step">',
        f'\t\t<div class="sf-qs__num">{num}</div>',
        '\t\t<div class="sf-qs__content">',
        '\t\t\t<div class="sf-qs__text">',
        f'\t\t\t\t<h3 class="wp-block-heading">{title}</h3>',
        f'\t\t\t\t<p>{desc}</p>',
        '\t\t\t</div>',
        f'\t\t\t<figure class="sf-qs__media"><img src="/wp-content/uploads/2026/09/{img}" alt="{alt}" width="800" height="600" loading="lazy"/></figure>',
        '\t\t</div>',
        '\t</article>',
    ]
qc_steps += ["</div>", "<!-- /wp:html -->"]

PAL = [
    ("01", "Panel Selection", "Dogs and cats of different breeds and ages join the panel."),
    ("02", "Two-Bowl Test", "Our product versus a competitor, offered side by side."),
    ("03", "Acceptance Scoring", "Intake ratio and first-choice rate are measured."),
    ("04", "Data Review", "Formulas are adjusted until acceptance passes our benchmark."),
]

pal = ["<!-- wp:html -->", '<div class="sf-pal">']
for num, title, desc in PAL:
    pal += [
        '\t<div class="sf-pal__step">',
        f'\t\t<span class="sf-pal__dot">{num}</span>',
        f'\t\t<h3 class="wp-block-heading">{title}</h3>',
        f'\t\t<p>{desc}</p>',
        '\t</div>',
    ]
pal += ["</div>", "<!-- /wp:html -->"]

# ---- apply back-to-front ---------------------------------------------------
for (a, b), new in sorted([(k, v) for k, v in [((97, 151), qc_lab), ((160, 287), qc_steps), ((348, 403), pal)]],
                          key=lambda kv: kv[0][0], reverse=True):
    lines[a - 1:b] = new

out = "\n".join(lines)
open(P, "w", encoding="utf-8").write(out)

print("written", len(out), "chars")
print("wp:gallery      ", out.count("wp:gallery"))
print("sf-eq__item     ", out.count("sf-eq__item"))
print("sf-qs__step     ", out.count('class="sf-qs__step"'))
print("sf-pal__step    ", out.count('class="sf-pal__step"'))
print("equip-hplc      ", out.count("equip-hplc.webp"))
print("equip-placeholder", out.count("equip-placeholder.webp"))
print("qc-retention    ", out.count("qc-retention.webp"))
print("leftover bg-light card groups in lab/steps:", out.count('"backgroundColor":"bg-light","layout":{"type":"flex","justifyContent":"center","verticalAlignment":"center"}'))
