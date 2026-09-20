#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务 2.4.4 —— 删除 burst-statistics 语言包（38 文件 / 417.28 KB）

设计要点（沿用本项目铁律）：
  * **不用通配符删除**：glob 只用于「枚举 + 白名单自检」，删除一律逐条 os.remove(绝对路径)
  * **白名单门禁**：枚举结果若出现任何不以 'burst-statistics-' 开头的名字 → 中止
  * **备份门禁**：备份后逐文件 md5 与源 1:1 复核，任一不符 → 中止
  * **删除门禁**：删除前后 md5 清单必须与备份清单完全一致（证明删的正是备份的那些）
  * 清单落盘（md5 manifest），供事后审计与恢复校验

用法：
  t244_lang.py list
  t244_lang.py backup
  t244_lang.py delete
  t244_lang.py verify
"""
import os
import sys
import glob
import shutil
import hashlib
import json
import time

SITE = os.path.expanduser("~/Local Sites/sinofresh/app/public")
PLUGDIR = os.path.join(SITE, "wp-content/languages/plugins")
PREFIX = "burst-statistics-"
BACKUP = os.path.expanduser(
    "~/WorkBuddy/sinofresh外贸网站建设/_backup/img-cleanup-20260920-062700/burst-languages"
)
MODE = sys.argv[1] if len(sys.argv) > 1 else "list"


def md5(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def enumerate_targets():
    """枚举 + 白名单自检。返回 [(name, abspath, size, md5)] 排序后。"""
    pat = os.path.join(PLUGDIR, PREFIX + "*")
    names = sorted(os.path.basename(p) for p in glob.glob(pat) if os.path.isfile(p))
    bad = [n for n in names if not n.startswith(PREFIX)]
    if bad:
        sys.exit(f"[ABORT] 白名单门禁：枚举到非 {PREFIX}* 名字 {bad}")
    rows = []
    for n in names:
        p = os.path.join(PLUGDIR, n)
        rows.append((n, p, os.path.getsize(p), md5(p)))
    return rows


def man_path():
    return os.path.join(BACKUP, "manifest-md5.json")


def cmd_list():
    rows = enumerate_targets()
    tot = sum(r[2] for r in rows)
    print(f"目录: {PLUGDIR}")
    print(f"枚举模式: {PREFIX}*")
    print(f"文件数: {len(rows)}")
    print(f"体积: {tot:,} B = {tot/1024:.2f} KB = {tot/1048576:.4f} MB")
    print(f"\n{'#':>3} {'size(B)':>9}  md5                              文件")
    for i, (n, p, s, m) in enumerate(rows, 1):
        print(f"{i:>3} {s:>9,}  {m}  {n}")
    # 对照组：目录里其他插件语言包仍在（证明 find 口径有效、未误伤）
    others = sorted(
        os.path.basename(p)
        for p in glob.glob(os.path.join(PLUGDIR, "*.mo"))
        if not os.path.basename(p).startswith(PREFIX)
    )
    print(f"\n[对照组] 目录内其他插件 .mo（须保留）: {others}")
    print(f"[白名单] 非 {PREFIX}* 命中: 0 ✅")
    return 0


def cmd_backup():
    rows = enumerate_targets()
    os.makedirs(BACKUP, exist_ok=True)
    ok = 0
    for n, p, s, m in rows:
        dst = os.path.join(BACKUP, n)
        shutil.copy2(p, dst)
        if md5(dst) != m:
            sys.exit(f"[ABORT] 备份门禁：{n} 备份后 md5 不符")
        ok += 1
    man = {
        "task": "2.4.4 burst 语言包",
        "backup_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source_dir": PLUGDIR,
        "backup_dir": BACKUP,
        "count": len(rows),
        "total_bytes": sum(r[2] for r in rows),
        "files": [{"name": n, "size": s, "md5": m} for n, p, s, m in rows],
    }
    with open(man_path(), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
    print(f"备份目录: {BACKUP}")
    print(f"备份完成: {ok}/{len(rows)} 个文件，md5 1:1 复核通过 ✅")
    print(f"合计: {man['total_bytes']:,} B = {man['total_bytes']/1024:.2f} KB")
    print(f"清单: {man_path()}")
    # 可执行恢复脚本
    sh = os.path.join(BACKUP, "restore.sh")
    with open(sh, "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\n# 回滚：把备份语言包复制回原位（逐文件，无通配符）\nset -e\n")
        f.write(f'D="{PLUGDIR}"\n')
        for n, p, s, m in rows:
            f.write(f'cp -p "{BACKUP}/{n}" "$D/{n}"\n')
        f.write(f'echo "restored {len(rows)} files"\n')
    os.chmod(sh, 0o755)
    print(f"回滚脚本: {sh}")
    return 0


def cmd_delete():
    if not os.path.isfile(man_path()):
        sys.exit("[ABORT] 未找到 manifest-md5.json —— 必须先 backup")
    man = json.load(open(man_path(), encoding="utf-8"))
    want = {f["name"]: f["md5"] for f in man["files"]}
    rows = enumerate_targets()
    # 删除门禁：待删集合必须与备份集合完全一致
    got = {n: m for n, p, s, m in rows}
    if set(got) != set(want):
        sys.exit(f"[ABORT] 删除门禁：集合不一致\n  仅在源: {sorted(set(got)-set(want))}\n  仅在备份: {sorted(set(want)-set(got))}")
    diff = [n for n in want if got[n] != want[n]]
    if diff:
        sys.exit(f"[ABORT] 删除门禁：md5 不一致 {diff}")
    print(f"删除门禁通过：{len(rows)} 个文件与备份 md5 1:1 相同，开始逐条 os.remove\n")
    removed, failed = 0, []
    for i, (n, p, s, m) in enumerate(rows, 1):
        try:
            os.remove(p)  # 逐文件精确路径，无通配符
            if os.path.exists(p):
                failed.append((n, "remove 后仍存在"))
            else:
                removed += 1
                print(f"  [{i:>2}/{len(rows)}] ✅ 已删  {n}")
        except Exception as e:
            failed.append((n, repr(e)))
            print(f"  [{i:>2}/{len(rows)}] ❌ 失败  {n}  {e}")
    print(f"\n删除结果: {removed}/{len(rows)} 成功")
    if failed:
        print("失败明细:", failed)
        return 1
    print("byte 释放:", f"{man['total_bytes']:,} B = {man['total_bytes']/1024:.2f} KB")
    return 0


def cmd_verify():
    # ① 目标已清除
    left = sorted(os.path.basename(p) for p in glob.glob(os.path.join(PLUGDIR, PREFIX + "*")))
    print(f"① 残留 {PREFIX}* : {len(left)} {left if left else '✅'}")
    # ② 备份完整性
    man = json.load(open(man_path(), encoding="utf-8"))
    bad = []
    for f in man["files"]:
        bp = os.path.join(BACKUP, f["name"])
        if not os.path.isfile(bp) or md5(bp) != f["md5"]:
            bad.append(f["name"])
    print(f"② 备份完整性: {len(man['files'])-len(bad)}/{len(man['files'])} md5 一致 {'✅' if not bad else bad}")
    # ③ 对照组：其他插件语言包未被误伤
    others = sorted(os.path.basename(p) for p in glob.glob(os.path.join(PLUGDIR, "*.mo")))
    print(f"③ [对照组] 目录内 .mo: {others}")
    # ④ 目录总文件数
    n = len([x for x in os.listdir(PLUGDIR) if os.path.isfile(os.path.join(PLUGDIR, x))])
    print(f"④ 目录内文件总数: {n}")
    ok = (not left) and (not bad)
    print(f"\n{'✅ 核验通过' if ok else '❌ 核验失败'}")
    return 0 if ok else 1


CMDS = {"list": cmd_list, "backup": cmd_backup, "delete": cmd_delete, "verify": cmd_verify}
if MODE not in CMDS:
    sys.exit(f"未知子命令 {MODE}；可用: {list(CMDS)}")
sys.exit(CMDS[MODE]())
