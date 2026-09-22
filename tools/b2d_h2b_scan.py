#!/usr/bin/env python3
"""Batch H2b Step 0 — read-only scan of the 8 dosage-form page templates.

Measures, per page:
  * the configurator block boundaries (start / end line, and every nested
    wp:group / section / div level that opens and closes inside it)
  * where [sf_explore_chips] sits relative to the block
  * the hero CTA line and its href
  * a structural fingerprint of what remains once the block is removed

Nothing is written anywhere except stdout / an optional JSON dump.
"""
import json
import os
import re
import sys

THEME = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sinofresh-theme')
TPL = os.path.join(THEME, 'templates')

PAGES = ['soft-chews', 'tablets', 'dental-chews', 'powders', 'pastes',
         'drops', 'liquids', 'fish-oil']


def read(name):
    with open(os.path.join(TPL, name), encoding='utf-8') as fh:
        return fh.read().splitlines()


def depth_delta(line):
    """Net effect of one line on the block-comment nesting level.

    A self-closing block (`<!-- wp:x {...} /-->`) opens AND closes on the same
    line, so it must contribute 0. Counting it as +1 accumulates a phantom
    depth equal to the number of self-closing blocks in the file, which is
    exactly what a naive implementation reports (measured: +3 on every one of
    the 8 pages, from the header / footer template-parts and the GF form).
    """
    opens = len(re.findall(r'<!--\s+wp:', line))
    closes = len(re.findall(r'<!--\s+/wp:', line))
    if line.rstrip().endswith('/-->'):
        opens -= 1
    return opens - closes


def scan(name):
    lines = read(name)
    out = {'page': name, 'total_lines': len(lines)}

    # ---- hero CTA -------------------------------------------------------
    hero_line = next((i for i, l in enumerate(lines) if l.startswith('<!-- wp:group')
                      and 'sf-hero-inner' in l), None)
    out['hero_marker_line'] = hero_line + 1 if hero_line is not None else None

    # ---- configurator block --------------------------------------------
    start = next(i for i, l in enumerate(lines) if 'id="configurator"' in l)
    # back up to the opening block comment for that section
    while start > 0 and not lines[start].startswith('<!-- wp:'):
        start -= 1
    end = start
    level = 0
    while end < len(lines):
        level += depth_delta(lines[end])
        if end > start and level <= 0:
            break
        end += 1
    out['block'] = {'start': start + 1, 'end': end + 1, 'lines': end - start + 1}

    # every distinct asset / marker inside the block
    body = '\n'.join(lines[start:end + 1])
    out['block_markers'] = {
        'svg_sprite': body.count('configurator__sprite'),
        'symbol': body.count('<symbol'),
        'form_tag': len(re.findall(r'<form\b', body)),
        'input_tag': len(re.findall(r'<input\b', body)),
        'select_tag': len(re.findall(r'<select\b', body)),
        'chips_shortcode': body.count('[sf_explore_chips]'),
        'configurator_class': len(re.findall(r'configurator', body)),
        'buttons': len(re.findall(r'wp-block-button', body)),
    }
    out['block_bytes'] = sum(len(l.encode('utf-8')) + 1 for l in lines[start:end + 1])

    # top-level children of the block: lines that start a wp: block at depth 1
    children = []
    lvl = 0
    for i in range(start, end + 1):
        before = lvl
        lvl += depth_delta(lines[i])
        if before == 1 and lines[i].startswith('<!-- wp:'):
            tag = re.search(r'<!-- wp:([a-z0-9/-]+)', lines[i])
            cls = re.search(r'"className":"([^"]*)"', lines[i])
            children.append({'line': i + 1, 'block': tag.group(1) if tag else '?',
                             'class': cls.group(1) if cls else ''})
    out['block_children'] = children

    # ---- chips ----------------------------------------------------------
    out['chips_lines'] = [i + 1 for i, l in enumerate(lines) if 'sf_explore_chips' in l]
    # neighbours around the first chips line
    if out['chips_lines']:
        c = out['chips_lines'][0] - 1
        out['chips_context'] = [{'line': j + 1, 'text': lines[j][:150]}
                                for j in range(max(0, c - 3), min(len(lines), c + 4))]

    # ---- hero CTA -------------------------------------------------------
    cta = [{'line': i + 1, 'href': h.group(1) if (h := re.search(r'href="([^"]*)"', lines[i])) else '',
            'text': re.sub(r'<[^>]+>', '', lines[i]).strip()[:60]}
           for i, l in enumerate(lines) if 'wp-block-button__link' in l or 'sf-hero' in l and 'href' in l]
    out['cta_lines'] = cta

    # ---- any other #configurator anchors --------------------------------
    out['anchor_lines'] = [{'line': i + 1, 'text': lines[i][:160]}
                           for i, l in enumerate(lines) if '#configurator' in l]

    # ---- residual structure after removal --------------------------------
    rest = lines[:start] + lines[end + 1:]
    out['after'] = {
        'total_lines': len(rest),
        'wp_blocks': len([l for l in rest if l.startswith('<!-- wp:')]),
        'balance': sum(depth_delta(l) for l in rest),
        'has_configurator': sum('configurator' in l for l in rest),
        'has_chips': sum('sf_explore_chips' in l for l in rest),
    }
    return out


def main():
    rows = [scan('page-%s.html' % p) for p in PAGES]
    if '--json' in sys.argv:
        path = sys.argv[sys.argv.index('--json') + 1]
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(rows, fh, indent=2, ensure_ascii=False)
        print('wrote', path)
    for r in rows:
        b = r['block']
        print('%-13s total=%-4d  block [%d..%d] = %d lines  bytes=%-6d  after=%d lines (balance %d)'
              % (r['page'], r['total_lines'], b['start'], b['end'], b['lines'],
                 r['block_bytes'], r['after']['total_lines'], r['after']['balance']))
        print('    markers: %s' % json.dumps(r['block_markers'], sort_keys=True))
        print('    chips at %s | anchors %s | after has configurator=%d chips=%d'
              % (r['chips_lines'], [a['line'] for a in r['anchor_lines']],
                 r['after']['has_configurator'], r['after']['has_chips']))
        print('    children: %s' % ', '.join('L%d:%s%s' % (c['line'], c['block'],
              ('(%s)' % c['class']) if c['class'] else '') for c in r['block_children'][:12]))
        for c in r['cta_lines'][:4]:
            print('    CTA  L%-4d href=%-18s %s' % (c['line'], c['href'], c['text']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
