#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch 1 · 步骤 1 —— 回滚阶段 2A 的配置器折叠。

Stage 2A 在 8 个剂型模板里捆了两件事：
  (a) <details class="configurator__fold"> 包裹 + sf-explore 移出配置器   -> 回滚
  (b) Lead time 措辞 "after packaging ready" -> "... is ready"          -> 保留（用户决策 ⑥）

所以不能盲 cp 覆盖：从阶段 2A 备份恢复 (a)，然后重放 (b)。

安全模型：
  1. 先把「当前（折叠态）」快照复制到新的 _backup/batch1-s2-rollback-<TS>/
  2. 读出备份内容 -> 变换 -> 全部断言通过 -> 才写盘（断言失败则磁盘不动）
  3. 输出 md5 对照 JSON 供后续核验

用法：python3 tools/_b1r_step1_rollback.py
"""
import difflib
import datetime
import hashlib
import json
import os
import shutil
import sys

def _find_proj(start):
    """向上探测含 sinofresh-theme 的目录，避免依赖脚本自身深度。"""
    d = start
    for _ in range(6):
        if os.path.isdir(os.path.join(d, 'sinofresh-theme')):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    raise SystemExit(f'[ABORT] 无法从 {start} 向上定位项目根（含 sinofresh-theme/）')


PROJ = _find_proj(os.path.dirname(os.path.abspath(__file__)))
THEME = os.path.join(PROJ, 'sinofresh-theme')
BK = os.path.join(PROJ, '_backup', 'batch1-stage2-20260920-093741')
TS = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
RB = os.path.join(PROJ, '_backup', f'batch1-s2-rollback-{TS}')
OUT = '/tmp/b1/step1'
os.makedirs(OUT, exist_ok=True)

SLUGS = ['soft-chews', 'tablets', 'powders', 'pastes', 'drops', 'liquids',
         'fish-oil', 'dental-chews']
TEMPLATES = [f'templates/page-{s}.html' for s in SLUGS]
CSS = ['assets/css/configurator.css', 'style.css']
FILES = TEMPLATES + CSS

OLD_PHRASE = 'after packaging ready'
NEW_PHRASE = 'after packaging is ready'

# 阶段 2A 备份时记录的 pre-md5（独立第三方校验锚点）
PRE_MD5 = {
    'style.css': 'db80b6533ce316f2c8046bbcdfcc50a6',
    'assets/css/configurator.css': '75091298a6edf7cbe63b594b87e14b86',
    'functions.php': '46382246ef369cd8ae4bb6cfc48c0a6b',
    'assets/js/formulas.js': '0979eb587d9453bba9eebb9d34a3eeba',
}

FAIL = []


def md5(b):
    return hashlib.md5(b).hexdigest()


def md5f(p):
    with open(p, 'rb') as fh:
        return md5(fh.read())


def check(cond, msg):
    if cond:
        print(f'  OK   {msg}')
    else:
        print(f'  FAIL {msg}')
        FAIL.append(msg)


print('=' * 78)
print('Batch 1 · 步骤 1 —— 回滚配置器折叠')
print('=' * 78)
print(f'theme : {THEME}')
print(f'backup: {BK}')
print(f'safety: {RB}')
print()

if not os.path.isdir(BK):
    sys.exit(f'[ABORT] 备份目录不存在: {BK}')

# ---------------------------------------------------------------- 0. 前置：备份完整性
print('--- 0. 备份目录完整性 ---')
for f in FILES:
    p = os.path.join(BK, f)
    if not os.path.isfile(p):
        sys.exit(f'[ABORT] 备份缺文件: {p}')
check(True, f'阶段 2A 备份 12 项齐全（本次用到 {len(FILES)} 项）')

# 备份里的 style.css / configurator.css 必须等于 pre-md5（否则恢复出来的不是 Stage 1 基线）
for f, want in PRE_MD5.items():
    got = md5f(os.path.join(BK, f))
    check(got == want, f'备份 {f} md5 == pre-md5 ({got})')

# ---------------------------------------------------------------- 1. 当前态快照
print()
print('--- 1. 回滚前快照（折叠态 -> 新备份）---')
for f in FILES:
    dst = os.path.join(RB, f)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(os.path.join(THEME, f), dst)
check(all(os.path.isfile(os.path.join(RB, f)) for f in FILES),
      f'已快照 {len(FILES)} 个文件到 {os.path.relpath(RB, PROJ)}')

before_md5 = {f: md5f(os.path.join(THEME, f)) for f in FILES}
for f in FILES:
    print(f'       cur {before_md5[f]}  {f}')

# ---------------------------------------------------------------- 2. 构造目标内容（不落盘）
print()
print('--- 2. 构造目标内容（备份恢复 + 措辞重放）---')
NEW = {}
for f in FILES:
    with open(os.path.join(BK, f), encoding='utf-8') as fh:
        NEW[f] = fh.read()

wording_n = 0
for f in TEMPLATES:
    t = NEW[f]
    n = t.count(OLD_PHRASE)
    if n != 1:
        FAIL.append(f'{f}: 备份中 {OLD_PHRASE!r} 出现 {n} 次，期望 1')
        continue
    NEW[f] = t.replace(OLD_PHRASE, NEW_PHRASE)
    wording_n += 1
check(wording_n == 8, f'8 个剂型模板重放 Lead time 措辞（{wording_n}/8）')

# ---------------------------------------------------------------- 3. 断言（写盘前）
print()
print('--- 3. 写盘前断言 ---')

# 3.1 模板：折叠痕迹必须彻底消失
for f in TEMPLATES:
    t = NEW[f]
    check('configurator__fold' not in t, f'{os.path.basename(f)}: 无 configurator__fold')
    check('configurator__explore-row' not in t, f'{os.path.basename(f)}: 无 explore-row')
    check('configurator__explore-col' not in t, f'{os.path.basename(f)}: 无 explore-col')

# 3.2 模板：sf-explore 回到 .configurator__options 内部（顺序判据）
for f in TEMPLATES:
    t = NEW[f]
    i_opt = t.find('<div class="configurator__options">')
    i_exp = t.find('<div class="sf-explore">')
    i_sum = t.find('<div class="configurator__summary-col">')
    ok = (i_opt != -1 and i_exp != -1 and i_sum != -1
          and i_opt < i_exp < i_sum and t.count('<div class="sf-explore">') == 1)
    check(ok, f'{os.path.basename(f)}: sf-explore 在 options 内且唯一 '
             f'(opt={i_opt} exp={i_exp} sum={i_sum})')

# 3.3 模板：区块对/标签计数回到备份水平
#     ⚠️ 页面本身就有 5–6 个 <details>/<summary>（配方手风琴 + FAQ 行），
#        所以不能断言为 0；判据是「== 备份计数」（自我校准，不写死数字）。
FOLD_CLASSES = ['configurator__fold', 'configurator__fold-head',
                'configurator__fold-body', 'configurator__fold-icon',
                'configurator__fold-desc']
for f in TEMPLATES:
    bn = os.path.basename(f)
    with open(os.path.join(BK, f), encoding='utf-8') as fh:
        old = fh.read()
    t = NEW[f]
    for probe, label in [
        ('<!-- wp:heading {"textAlign":"center"} -->', 'wp:heading(textAlign:center)'),
        ('<!-- wp:paragraph {"align":"center","textColor":"text-secondary"} -->',
         'wp:paragraph(center/secondary)'),
        ('</summary>', '</summary>'),
        ('<details', '<details'),
        ('<div class="sf-explore">', 'sf-explore'),
    ]:
        check(t.count(probe) == old.count(probe),
              f'{bn}: {label} 计数 == 备份 ({t.count(probe)})')
    for probe in FOLD_CLASSES:
        check(probe not in t, f'{bn}: 折叠残留 "{probe}" 为 0')
    # 阶段 2A 的足迹：当前态恰好比备份多 1 个 <details>（这就是要回滚的那一层）
    with open(os.path.join(THEME, f), encoding='utf-8') as fh:
        cur = fh.read()
    check(cur.count('<details') == old.count('<details') + 1,
          f'{bn}: 阶段 2A 足迹 == +1 <details> '
          f'(cur={cur.count("<details")} bk={old.count("<details")})')

# 3.4 模板：措辞
for f in TEMPLATES:
    t = NEW[f]
    check(t.count(NEW_PHRASE) == 1 and t.count(OLD_PHRASE) == 0,
          f'{os.path.basename(f)}: 措辞 == "{NEW_PHRASE}" ×1，旧措辞 ×0')

# 3.5 模板：相对阶段 2A 备份只差 1 行（措辞那一行）
for f in TEMPLATES:
    with open(os.path.join(BK, f), encoding='utf-8') as fh:
        old = fh.read()
    d = [l for l in difflib.unified_diff(old.splitlines(), NEW[f].splitlines(),
                                         lineterm='', n=0)
         if l[:1] in '+-' and not l.startswith(('+++', '---'))]
    check(len(d) == 2, f'{os.path.basename(f)}: 相对备份恰好 1 行差异（{len(d)} 行 +/-）')

# 3.6 模板：div 配平（与备份相同）
for f in TEMPLATES:
    with open(os.path.join(BK, f), encoding='utf-8') as fh:
        old = fh.read()
    check(NEW[f].count('<div') == old.count('<div')
          and NEW[f].count('</div>') == old.count('</div>'),
          f'{os.path.basename(f)}: div 计数与备份一致')

# 3.7 CSS：折叠样式全部消失
t = NEW['assets/css/configurator.css']
check('configurator__fold' not in t, 'configurator.css: 无 .configurator__fold')
check('desktop-only fold' not in t, 'configurator.css: 无折叠段落注释')
check('details-content' not in t, 'configurator.css: 无 ::details-content 覆盖')
check(md5(NEW['assets/css/configurator.css'].encode('utf-8')) == PRE_MD5['assets/css/configurator.css'],
      'configurator.css: 内容 md5 == pre-md5')

s = NEW['style.css']
check('configurator__fold' not in s, 'style.css: 无 .configurator__fold-desc')
check(md5(NEW['style.css'].encode('utf-8')) == PRE_MD5['style.css'],
      'style.css: 内容 md5 == pre-md5')

if FAIL:
    print()
    print('=' * 78)
    print(f'[ABORT] {len(FAIL)} 项断言失败，磁盘未改动：')
    for m in FAIL:
        print('   -', m)
    sys.exit(1)

# ---------------------------------------------------------------- 4. 落盘
print()
print('--- 4. 写入主题源码 ---')
for f in FILES:
    with open(os.path.join(THEME, f), 'w', encoding='utf-8') as fh:
        fh.write(NEW[f])
    print(f'       wrote {f}')

after_md5 = {f: md5f(os.path.join(THEME, f)) for f in FILES}

# ---------------------------------------------------------------- 5. 汇总
print()
print('--- 5. 汇总 ---')
rows = []
for f in FILES:
    row = {'file': f, 'before': before_md5[f], 'after': after_md5[f],
           'changed': before_md5[f] != after_md5[f]}
    rows.append(row)
    print(f'  {"CHANGED" if row["changed"] else "same   "} {f}  {row["before"]} -> {row["after"]}')

report = {
    'ts': TS,
    'backup_source': os.path.relpath(BK, PROJ),
    'backup_safety': os.path.relpath(RB, PROJ),
    'files': rows,
    'wording_replayed': wording_n,
}
with open(os.path.join(OUT, 'rollback.json'), 'w', encoding='utf-8') as fh:
    json.dump(report, fh, ensure_ascii=False, indent=2)
print()
print(f'JSON -> {OUT}/rollback.json')
print(f'安全备份 -> {os.path.relpath(RB, PROJ)}')
print('DONE')
