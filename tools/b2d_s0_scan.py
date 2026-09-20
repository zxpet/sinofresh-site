#!/usr/bin/env python3
"""Batch2D Step0 — read-only structural scan of the 8 dosage-form page templates.

Reports, per template:
  * top-level block signature (name + anchor + className)
  * ordered "module" list (section anchors, H2/H3 headings, shortcodes, svg/img)
  * whether key reusable components / data sources appear
  * image references and their basename

Usage: python3 tools/b2d_s0_scan.py
"""
import json
import re
import os
import sys
from collections import OrderedDict, Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, 'sinofresh-theme', 'templates')

FORMS = [
    ('soft-chews', 'Soft Chews'),
    ('tablets', 'Tablets'),
    ('powders', 'Powders'),
    ('pastes', 'Pastes'),
    ('drops', 'Drops'),
    ('liquids', 'Liquids'),
    ('fish-oil', 'Fish Oil'),
    ('dental-chews', 'Dental Chews'),
]

OPEN = re.compile(r'<!--\s*wp:([a-z0-9/-]+)\s*(\{.*?\})?\s*(/?)-->', re.S)


def top_level_blocks(src):
    """Return list of (name, attrs_dict, start, end) for depth-0 blocks."""
    events = []
    for m in OPEN.finditer(src):
        selfc = bool(m.group(3))   # self-closing: never opens a level
        events.append((m.start(), 'open', m.group(1), m.group(2), selfc, m.end()))
    for m in re.finditer(r'<!--\s*/wp:([a-z0-9/-]+)\s*-->', src):
        events.append((m.start(), 'close', m.group(1), None, False, m.end()))
    events.sort(key=lambda e: e[0])

    depth = 0
    out = []
    cur = None
    for pos, kind, name, attrs, selfc, m_end in events:
        if kind == 'open':
            if depth == 0:
                a = {}
                if attrs:
                    try:
                        a = json.loads(attrs)
                    except Exception:
                        a = {'_badjson': attrs[:60]}
                cur = {'name': name, 'attrs': a, 'start': pos,
                       'end': m_end if selfc else None, 'selfclose': selfc}
                out.append(cur)
            if not selfc:
                depth += 1
        else:
            if not selfc:
                depth -= 1
            if depth == 0 and cur and not cur['selfclose'] and cur['end'] is None:
                cur['end'] = pos
                cur = None
    return out


def signature(blocks):
    sig = []
    for b in blocks:
        a = b['attrs']
        tag = b['name']
        anchor = a.get('anchor')
        cn = a.get('className')
        if anchor:
            tag += f'#{anchor}'
        if cn:
            tag += f'.{cn}'
        if b['selfclose']:
            tag += '/'
        sig.append(tag)
    return sig


def inner(src, b):
    return src[b['start']:b['end']]


report = OrderedDict()
for slug, label in FORMS:
    path = os.path.join(TPL, f'page-{slug}.html')
    src = open(path, encoding='utf-8').read()
    blocks = top_level_blocks(src)
    sig = signature(blocks)

    # headings h2/h3 in order with their block index
    heads = []
    for i, m in enumerate(re.finditer(r'<h([23])[^>]*>(.*?)</h\1>', src, re.S)):
        txt = re.sub(r'<[^>]+>', '', m.group(2))
        txt = re.sub(r'\s+', ' ', txt).strip()
        heads.append((m.group(1), txt))

    # shortcodes
    shorts = re.findall(r'\[(sf_[a-z_]+)([^\]]*)\]', src)
    # images
    imgs = re.findall(r'<img[^>]*src="([^"]+)"[^>]*>', src)
    svgs = len(re.findall(r'<svg[\s>]', src))
    # component probes
    probes = {
        'sf-lb': 'sf-lb' in src,
        'sf-coa': 'sf-coa' in src,
        'sf-certbar': 'sf-certbar' in src,
        'sf-certgrid': 'sf-certgrid' in src,
        'sf-certcard': 'sf-certcard' in src,
        'sf-statbar': 'sf-statbar' in src,
        'sf-spec-list': 'sf-spec-list' in src,
        'sf-spectable': 'sf-spectable' in src,
        'sf-panel': 'sf-panel' in src,
        'sf-strip': 'sf-strip' in src,
        'sf-section': 'sf-section' in src,
        'sf-faq': 'sf-faq' in src,
        'sf-dosage-grid': 'sf-dosage-grid' in src,
        'sf-cell': 'sf-cell__' in src,
        'configurator': 'configurator__' in src,
        'gf-formId': 'formId' in src,
        'sf-toc': 'sf-toc' in src,
        'data-group': 'data-group' in src,
    }
    report[slug] = {
        'label': label,
        'bytes': len(src.encode('utf-8')),
        'blocks': len(blocks),
        'sig': sig,
        'heads': heads,
        'shorts': shorts,
        'imgs': imgs,
        'svg': svgs,
        'probes': probes,
    }

# ---- print ----
print('=' * 78)
print('PER-PAGE TOP-LEVEL SIGNATURE')
print('=' * 78)
for slug, r in report.items():
    print(f"\n### page-{slug}.html  [{r['label']}]  {r['bytes']} B, {r['blocks']} top-level blocks")
    for i, s in enumerate(r['sig']):
        print(f'   {i:>2}  {s}')

print('\n' + '=' * 78)
print('SIGNATURE UNIFORMITY (no anchor/className -> structural skeleton)')
print('=' * 78)
skeletons = {}
for slug, r in report.items():
    sk = re.sub(r'#\w+|\.\S+', '', ' | '.join(r['sig']))
    skeletons.setdefault(sk, []).append(slug)
for sk, slugs in skeletons.items():
    print(f'\n  [{len(slugs)} pages] {slugs}\n    {sk}')

print('\n' + '=' * 78)
print('HEADING SEQUENCE (H2/H3) PER PAGE')
print('=' * 78)
for slug, r in report.items():
    print(f'\n### {slug}')
    for lvl, txt in r['heads']:
        print(f'   h{lvl}  {txt}')

print('\n' + '=' * 78)
print('SHORTCODES PER PAGE')
print('=' * 78)
for slug, r in report.items():
    print(f'  {slug:<14} {r["shorts"]}')

print('\n' + '=' * 78)
print('IMAGES PER PAGE')
print('=' * 78)
for slug, r in report.items():
    print(f'\n### {slug}  ({len(r["imgs"])} img, {r["svg"]} svg)')
    for u in r['imgs']:
        print(f'   {u}')

print('\n' + '=' * 78)
print('COMPONENT PROBES')
print('=' * 78)
keys = list(next(iter(report.values()))['probes'].keys())
hdr = 'probe'.ljust(16) + ''.join(s[:11].ljust(13) for s in report.keys())
print(hdr)
for k in keys:
    row = k.ljust(16) + ''.join(
        ('YES' if report[s]['probes'][k] else '-').ljust(13) for s in report.keys())
    print(row)

print('\n' + '=' * 78)
print('DIFF SUMMARY')
print('=' * 78)
for k in keys:
    have = [s for s in report if report[s]['probes'][k]]
    if 0 < len(have) < 8:
        print(f'  {k}: only in {have}')
