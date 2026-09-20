#!/usr/bin/env python3
"""批次1 步骤2（Hero 极简）—— 改动前备份。

备份清单（11 项，用户指派）：
  templates/page-{8 剂型}.html   (8)
  style.css                      (1)
  functions.php                  (1)
  assets/js/product-slider.js    (1)  <- 本步将删除

产出：
  _backup/batch1-s2-hero-<TS>/…  按相对路径还原结构
  _backup/batch1-s2-hero-<TS>/MANIFEST.md
  /tmp/b1/step2/bkpath.txt       备份路径
  /tmp/b1/step2/pre_md5.txt      改动前指纹（含体积）
"""
import hashlib
import os
import shutil
import sys
from datetime import datetime

SL = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids',
      'fish-oil', 'dental-chews']

FILES = [f'templates/page-{t}.html' for t in SL] + [
    'style.css',
    'functions.php',
    'assets/js/product-slider.js',
]


def find_root(start):
    cur = os.path.abspath(start)
    while True:
        cand = os.path.join(cur, 'sinofresh-theme')
        if os.path.isdir(cand):
            return cur
        nxt = os.path.dirname(cur)
        if nxt == cur:
            sys.exit('[ABORT] 未找到 sinofresh-theme 目录')
        cur = nxt


def md5f(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    root = find_root(os.getcwd())
    theme = os.path.join(root, 'sinofresh-theme')
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    bk = os.path.join(root, '_backup', f'batch1-s2-hero-{ts}')

    print(f'项目根 : {root}')
    print(f'备份到 : {bk}\n')

    # ---- 闸 0：源文件齐备 + 回滚态断言（写盘前） ----
    src = {}
    for rel in FILES:
        p = os.path.join(theme, rel)
        if not os.path.isfile(p):
            sys.exit(f'[ABORT] 源文件缺失: {rel}')
        src[rel] = p

    for t in SL:
        s = open(os.path.join(theme, f'templates/page-{t}.html'), encoding='utf-8').read()
        if s.count('configurator__fold') != 0:
            sys.exit(f'[ABORT] {t}: 回滚未生效（仍有 configurator__fold）')
        if s.count('after packaging is ready') != 1:
            sys.exit(f'[ABORT] {t}: Lead time 措辞不是 1 处')
    print('闸0 前置断言: ✅ 11 文件齐备 + 8 页回滚态完整\n')

    # ---- 复制（按相对路径还原结构） ----
    os.makedirs(bk, exist_ok=True)
    rows = []
    for rel in FILES:
        dst = os.path.join(bk, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src[rel], dst)
        a, b = md5f(src[rel]), md5f(dst)
        size = os.path.getsize(src[rel])
        same = (a == b) and size == os.path.getsize(dst)
        rows.append((rel, size, a, same))
        print(f"  {'OK  ' if same else 'FAIL'} {rel:<40} {size:>8,} B  {a}")

    if not all(r[3] for r in rows):
        sys.exit('[ABORT] 复制校验失败')

    # ---- MANIFEST ----
    man = [
        '# 批次 1 · 步骤 2（Hero 极简）改动前备份',
        '',
        f'- 时间：{ts}',
        f'- 来源：`sinofresh-theme/`（唯一真源）',
        f'- 用途：步骤 2 = 删 Hero 轮播 + 单栏居中 + 按钮 2 个 + 删 `product-slider.js` + CSS 清理 + `style.css` 版本 bump',
        '',
        '## 清单（11 项）',
        '',
        '| # | 相对路径 | 字节 | MD5 |',
        '|---|---|---|---|',
    ]
    for i, (rel, size, h, _) in enumerate(rows, 1):
        man.append(f'| {i} | `{rel}` | {size:,} | `{h}` |')
    man += [
        '',
        '## 回滚方式',
        '',
        '```bash',
        f'cd <项目根> && for f in {" ".join(FILES)}; do',
        f'  cp -p "{os.path.join(bk, "")}$f" "sinofresh-theme/$f"; done',
        '```',
        '',
        '> ⚠️ 本备份是**整文件快照**。步骤 2 与后续步骤（3–6）共享同一份源码，',
        '> 若需单独回退本步，请比对 `_backup/` 中其它快照，避免覆盖后续步骤成果。',
        '',
    ]
    with open(os.path.join(bk, 'MANIFEST.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(man))

    # ---- 记录路径与指纹 ----
    ev = '/tmp/b1/step2'
    os.makedirs(ev, exist_ok=True)
    with open(os.path.join(ev, 'bkpath.txt'), 'w') as f:
        f.write(bk + '\n')
    with open(os.path.join(ev, 'pre_md5.txt'), 'w') as f:
        for rel, size, h, _ in rows:
            f.write(f'{h}  {size:>8}  {rel}\n')

    total = sum(r[1] for r in rows)
    print(f'\n✅ 备份完成：{len(rows)} 文件 / {total:,} B')
    print(f'   {bk}/MANIFEST.md')
    print(f'   证据：{ev}/bkpath.txt, {ev}/pre_md5.txt')


if __name__ == '__main__':
    main()
