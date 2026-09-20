#!/usr/bin/env python3
"""任务 2.3 —— uploads/burst/ 整目录 + uploads/js/ 空壳 备份与删除

用法:
    python3 tools/t23_do.py backup     # 备份（保留相对路径 + md5 + 体积校验）
    python3 tools/t23_do.py delete     # 删除（删前逐条断言备份一致；rmdir 前断言目录为空）
    python3 tools/t23_do.py verify     # 核验（文件/目录均已消失，白名单在位）
"""
import hashlib
import os
import shutil
import sys

UP = os.path.expanduser('~/Local Sites/sinofresh/app/public/wp-content/uploads')
BK = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/_backup/img-cleanup-20260920-062700/burst'

# burst/ 下 8 个文件（相对 uploads/）
REL = [
    'burst/exports/08b225703c7ecba772a67e0bdd5c8b2c/.htaccess',
    'burst/exports/08b225703c7ecba772a67e0bdd5c8b2c/index.php',
    'burst/exports/976b388173eced78f4181049707c6c17/.htaccess',
    'burst/exports/976b388173eced78f4181049707c6c17/index.php',
    'burst/js/burst.min.js',
    'burst/maxmind/.htaccess',
    'burst/maxmind/GeoLite2-Country.mmdb',
    'burst/maxmind/index.php',
]

# 待删目录（自深向浅，确保 rmdir 时为空）
DIRS = [
    'burst/exports/08b225703c7ecba772a67e0bdd5c8b2c',
    'burst/exports/976b388173eced78f4181049707c6c17',
    'burst/exports',
    'burst/js',
    'burst/maxmind',
    'burst',
    'js',
]

# 白名单：绝不能动
WHITELIST = [
    '2026/09/sino-fresh-logo-1.png',
    '2026/09/sino-fresh-logo-1-scaled.png',
    'wp-statistics/.htaccess',
]


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def assert_whitelist(tag):
    for rel in WHITELIST:
        p = os.path.join(UP, rel)
        assert os.path.isfile(p), f'[{tag}] 白名单缺失: {rel}'
    print(f'  白名单 {len(WHITELIST)}/{len(WHITELIST)} 在位 ✅  ({tag})')


def cmd_backup():
    os.makedirs(BK, exist_ok=True)
    total = 0
    print(f'=== 备份 {len(REL)} 个文件 → {BK} ===')
    for rel in REL:
        src = os.path.join(UP, rel)
        dst = os.path.join(BK, rel)
        assert os.path.isfile(src), '缺失源文件: ' + rel
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        a, b = md5(src), md5(dst)
        assert a == b, f'md5 不一致: {rel} {a} != {b}'
        sz = os.path.getsize(src)
        total += sz
        print(f'  BK  {sz:>10,} B  {a}  {rel}')
    print(f'\n备份合计 {total:,} B = {total/1024/1024:.2f} MB')
    # 空目录记录（备份时目录尚在）
    for d in DIRS:
        p = os.path.join(UP, d)
        if os.path.isdir(p):
            print(f'  DIR {p}')


def cmd_delete():
    assert_whitelist('删除前')
    print('\n=== 步骤 1/2：删除 8 个文件（逐条校验备份一致）===')
    total = 0
    for rel in REL:
        src = os.path.join(UP, rel)
        bak = os.path.join(BK, rel)
        assert os.path.isfile(src), '缺失源文件: ' + rel
        assert os.path.isfile(bak), '缺失备份: ' + rel
        assert md5(src) == md5(bak), '备份与源不一致，拒绝删除: ' + rel
        sz = os.path.getsize(src)
        os.remove(src)
        assert not os.path.exists(src), '删除失败: ' + rel
        total += sz
        print(f'  DEL {sz:>10,} B  {rel}')
    print(f'  文件删除合计 {total:,} B = {total/1024/1024:.2f} MB')

    print('\n=== 步骤 2/2：删除空目录（rmdir 前断言为空）===')
    for d in DIRS:
        p = os.path.join(UP, d)
        if not os.path.isdir(p):
            print(f'  SKIP 不存在  {d}')
            continue
        left = os.listdir(p)
        assert left == [], f'目录非空，拒绝 rmdir: {d} → {left}'
        os.rmdir(p)
        assert not os.path.exists(p), 'rmdir 失败: ' + d
        print(f'  RMDIR  {d}')
    assert_whitelist('删除后')


def cmd_verify():
    print('=== 文件核验 ===')
    live = [r for r in REL if os.path.exists(os.path.join(UP, r))]
    print(f'  应删文件 {len(REL)} 个，仍存在 {len(live)} 个', live if live else '✅')
    print('=== 目录核验 ===')
    lv = [d for d in DIRS if os.path.exists(os.path.join(UP, d))]
    print(f'  应删目录 {len(DIRS)} 个，仍存在 {len(lv)} 个', lv if lv else '✅')
    print('=== 备份在册 ===')
    bkf = sum(len(fs) for _, _, fs in os.walk(BK))
    print(f'  备份文件数 {bkf} / {len(REL)}', '✅' if bkf >= len(REL) else '❌')
    print('=== 白名单 ===')
    assert_whitelist('核验')
    print('=== uploads 现状 ===')
    n = sum(len(fs) for _, _, fs in os.walk(UP))
    print(f'  文件数 {n}')
    for r, ds, fs in os.walk(UP):
        depth = r[len(UP):].count(os.sep)
        if depth <= 1 and not fs and not ds:
            print(f'  空目录: {r}')


if __name__ == '__main__':
    act = sys.argv[1] if len(sys.argv) > 1 else 'verify'
    {'backup': cmd_backup, 'delete': cmd_delete, 'verify': cmd_verify}[act]()
