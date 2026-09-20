#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务 2.2 uploads 零引用图 —— 备份 / 删除（含断言）
用法：python3 tools/t22_do.py backup | delete
"""
import os, sys, shutil, hashlib, json

HOME = os.path.expanduser('~')
UP = HOME + '/Local Sites/sinofresh/app/public/wp-content/uploads'
BK = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/_backup/img-cleanup-20260920-062700/uploads'

REL = [
    # A. 微信图片族（8）—— 附件 42 自身记录外，全站零外部引用
    '2026/09/微信图片_20260629142652_11_458.jpg',
    '2026/09/微信图片_20260629142652_11_458-scaled.jpg',
    '2026/09/微信图片_20260629142652_11_458-2048x1535.jpg',
    '2026/09/微信图片_20260629142652_11_458-1536x1152.jpg',
    '2026/09/微信图片_20260629142652_11_458-1024x768.jpg',
    '2026/09/微信图片_20260629142652_11_458-768x576.jpg',
    '2026/09/微信图片_20260629142652_11_458-300x225.jpg',
    '2026/09/微信图片_20260629142652_11_458-150x150.jpg',
    # B. 剂型 PNG 原图（9）—— 站点一律用 .webp 同名兄弟；媒体记录 100/102/104/106/108/110 指向 .webp 自身
    '2026/09/hero-facility.png', '2026/09/powders.png', '2026/09/soft-chews.png',
    '2026/09/dental-chews.png', '2026/09/fish-oil.png', '2026/09/pastes.png',
    '2026/09/drops.png', '2026/09/liquids.png', '2026/09/tablets.png',
    # C. 被新图取代的 webp（4）
    '2026/09/hero-line.webp', '2026/09/hero-facility.webp', '2026/09/hero-lab.webp',
    '2026/09/world-map.webp',
]

def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()

mode = sys.argv[1]
total = 0

if mode == 'backup':
    for rel in REL:
        src = os.path.join(UP, rel)
        assert os.path.isfile(src), 'MISSING: ' + rel
        dst = os.path.join(BK, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        a, b = md5(src), md5(dst)
        assert a == b, 'MD5 MISMATCH ' + rel
        total += os.path.getsize(src)
        print(f'  OK {os.path.getsize(src):>10,} {md5(dst)}  {rel}')
    print(f'\n备份完成：{len(REL)} 个 / {total:,} B → {BK}')

elif mode == 'delete':
    for rel in REL:
        src = os.path.join(UP, rel)
        assert os.path.isfile(src), 'MISSING: ' + rel
        bdir = os.path.join(BK, rel)
        assert os.path.isfile(bdir), 'NO BACKUP for ' + rel
        assert md5(src) == md5(bdir), 'BACKUP DIFFERS ' + rel
        sz = os.path.getsize(src)
        os.remove(src)
        assert not os.path.exists(src), 'FAILED to remove ' + rel
        total += sz
        print(f'  DEL {sz:>10,}  {rel}')
    print(f'\n删除完成：{len(REL)} 个 / {total:,} B')

else:
    sys.exit('mode must be backup|delete')
