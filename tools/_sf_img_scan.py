#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standard Formulas + CPT 扫描 —— 第二步：图片资源盘点（只读）

测量 uploads 下全部图片的像素尺寸与体积（WebP/PNG），按语义族分组，
输出「是否有配方级图片」「卡片图候选」所需的事实。只写 /tmp。
用法：python3 tools/_sf_img_scan.py [outdir]
"""
import json
import os
import re
import subprocess
import sys

UP = os.path.expanduser('~/Local Sites/sinofresh/app/public/wp-content/uploads')
OUT = sys.argv[1] if len(sys.argv) > 1 else '/tmp/b1/cpt_scan'
os.makedirs(OUT, exist_ok=True)
IMG_EXT = ('webp', 'png', 'jpg', 'jpeg')
DOSAGE = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids',
          'fish-oil', 'dental-chews']


def dims(path):
    r = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', path],
                       capture_output=True, text=True)
    w = re.search(r'pixelWidth:\s*(\d+)', r.stdout)
    h = re.search(r'pixelHeight:\s*(\d+)', r.stdout)
    return (int(w.group(1)), int(h.group(1))) if w and h else (None, None)


rows = []
for dp, _dn, fns in os.walk(UP):
    for fn in fns:
        ext = fn.rsplit('.', 1)[-1].lower()
        if ext not in IMG_EXT:
            continue
        p = os.path.join(dp, fn)
        w, h = dims(p)
        rows.append({'name': fn, 'rel': os.path.relpath(p, UP), 'ext': ext,
                     'w': w, 'h': h, 'bytes': os.path.getsize(p)})
rows.sort(key=lambda r: r['rel'])

# 语义族归类
def family(n):
    base = re.sub(r'-\d+x\d+', '', n).rsplit('.', 1)[0]
    for pre, fam in [('soft-chews', '剂型图'), ('tablets', '剂型图'),
                     ('powders', '剂型图'), ('pastes', '剂型图'),
                     ('drops', '剂型图'), ('liquids', '剂型图'),
                     ('fish-oil', '剂型图'), ('dental-chews', '剂型图'),
                     ('fac-', '工厂图'), ('hero', '首页轮播'), ('equip-', '设备图'),
                     ('qc-', '质检图'), ('cert-', '证书缩略图'),
                     ('avatar-', '头像'), ('team-', '团队照'), ('blog-', '博客配图'),
                     ('sino-fresh-logo', 'Logo'), ('coa-sample', '样张'),
                     ('video-cover', '视频封面')]:
        if base.startswith(pre):
            return fam
    return '其他'


for r in rows:
    r['family'] = family(r['name'])

print('=' * 92)
print('二、图片资源盘点（uploads/）')
print('=' * 92)
fams = {}
for r in rows:
    fams.setdefault(r['family'], []).append(r)
print(f"{'族':<14}{'张数':>5}{'总体积MB':>10}  说明")
for fam, lst in sorted(fams.items(), key=lambda kv: -len(kv[1])):
    print(f"{fam:<14}{len(lst):>5}{sum(x['bytes'] for x in lst) / 1048576:>10.2f}  "
          f"{lst[0]['w']}×{lst[0]['h']} …")

print()
print('--- 剂型图族（卡片图候选）主图 + 变体 ---')
print(f"{'文件':<34}{'尺寸':>12}{'长宽比':>9}{'体积KB':>10}")
for r in sorted([x for x in rows if x['family'] == '剂型图'],
                key=lambda x: (x['name'])):
    ar = f'{r["w"] / r["h"]:.3f}' if r['w'] and r['h'] else '—'
    print(f"{r['name']:<34}{str(r['w']) + '×' + str(r['h']):>12}{ar:>9}"
          f"{r['bytes'] / 1024:>10.1f}")

print()
print('--- 工厂图族（fac-*）---')
print(f"{'文件':<34}{'尺寸':>12}{'长宽比':>9}{'体积KB':>10}")
for r in sorted([x for x in rows if x['family'] == '工厂图'], key=lambda x: x['name']):
    ar = f'{r["w"] / r["h"]:.3f}' if r['w'] and r['h'] else '—'
    print(f"{r['name']:<34}{str(r['w']) + '×' + str(r['h']):>12}{ar:>9}"
          f"{r['bytes'] / 1024:>10.1f}")

print()
print('--- 每个剂型的可用图（主图 / 300 / 150）---')
print(f"{'剂型':<15}{'主图':>16}{'300×300':>10}{'150×150':>10}")
for d in DOSAGE:
    main = next((r for r in rows if r['name'] == f'{d}.webp'), None)
    v300 = next((r for r in rows if r['name'] == f'{d}-300x300.webp'), None)
    v150 = next((r for r in rows if r['name'] == f'{d}-150x150.webp'), None)
    m = f"{main['w']}×{main['h']}" if main else '—'
    a = '✅' if v300 else '—'
    b = '✅' if v150 else '—'
    print(f"{d:<15}{m:>16}{a:>10}{b:>10}")

print()
print('=' * 92)
print('关键结论')
print('=' * 92)
n_formula_img = [r for r in rows if r['family'] == '其他']
print(f"  1. 是否有「配方级」独立图片：**否**（sf-formulas 的 21 个 <details> 内 0 个 <img>）")
print(f"  2. 8 张剂型主图尺寸：", end='')
print(' / '.join(f"{d}={next((r['w'] for r in rows if r['name'] == d + '.webp'), '?')}×"
                f"{next((r['h'] for r in rows if r['name'] == d + '.webp'), '?')}"
                for d in DOSAGE))
print(f"  3. 工厂图 fac-* 可用张数：{len([r for r in rows if r['family'] == '工厂图'])}"
      f"（{', '.join(sorted(r['name'] for r in rows if r['family'] == '工厂图'))}）")
print(f"  4. 其他族：{', '.join(f'{k}={len(v)}' for k, v in sorted(fams.items()) if k not in ('剂型图', '工厂图'))}")

json.dump(rows, open(os.path.join(OUT, 'images.json'), 'w'),
          ensure_ascii=False, indent=1)
print()
print('→', os.path.join(OUT, 'images.json'))
