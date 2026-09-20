#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务 2.2 uploads 零引用取证（五层）—— 通用化自 2.1 方法
层1 主题运行时源码 token 检索（含 assets/js|css；排除 docs/ 与 *.md —— 非 WP 加载物，仅审计报告自身会复述文件名）
层2 DB 三源（wp_posts / wp_postmeta / wp_options）全量 LIKE
层3 19 页渲染 HTML 全文
层4 运行时网络请求采集（/tmp/t22/runtime_urls.txt，由 Playwright 产生；缺则标 PENDING）
层5 HTTP 可达性基线（另行 curl）
"""
import os, sys, re, json, urllib.parse, hashlib

HOME = os.path.expanduser('~')
UPLOADS = HOME + '/Local Sites/sinofresh/app/public/wp-content/uploads'
SRC     = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme'
LOCAL   = HOME + '/Local Sites/sinofresh/app/public/wp-content/themes/sinofresh-theme'

TEXT_EXT = {'.php', '.js', '.css', '.html', '.json', '.txt', '.xml', '.scss', '.po', '.pot', '.sql'}

def read_tree(root, skip_dirs=(), skip_md=True):
    """返回 {relpath: text}"""
    out = {}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in skip_dirs and not d.startswith('.')]
        for fn in fns:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in TEXT_EXT:
                continue
            if skip_md and ext == '.md':
                continue
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) > 8 * 1024 * 1024:
                    continue
                out[os.path.relpath(p, root)] = open(p, encoding='utf-8', errors='replace').read()
            except Exception:
                pass
    return out

def read_file(p):
    try:
        return open(p, encoding='utf-8', errors='replace').read()
    except Exception:
        return ''

print('=== 构建取证语料 ===')
corp = {}

# 层1a：主题运行时源码（WP 实际加载的目录）
src_tree = read_tree(SRC, skip_dirs={'docs', 'node_modules', '_backup', '.git'}, skip_md=True)
corp['L1_src_theme'] = ('\n'.join(f'@@{k}\n{v}' for k, v in src_tree.items()), len(src_tree))
print(f'  层1a 主题运行时源码：{len(src_tree)} 个文本文件（已排除 docs/ 与 *.md）')

# 层1b：Local 侧主题目录（部署副本，独立复核）
loc_tree = read_tree(LOCAL, skip_dirs={'docs', 'node_modules', '_backup', '.git'}, skip_md=True)
corp['L1b_src_local'] = ('\n'.join(f'@@{k}\n{v}' for k, v in loc_tree.items()), len(loc_tree))
print(f'  层1b Local 主题目录：{len(loc_tree)} 个文本文件')

# 层1c（附加）：整个仓库含 docs/_backup —— 仅作信息参考，不参与零引用判定
print('  （附加）仓库全文本语料跳过：docs/_backup 非运行时物，其复述不算引用')

# 层2
corp['L2_db_posts']    = (read_file('/tmp/t22/db_posts_all.txt'), 1)
corp['L2_db_postmeta'] = (read_file('/tmp/t22/db_postmeta_all.txt'), 1)
corp['L2_db_options']  = (read_file('/tmp/t22/db_options_all.txt'), 1)
for k in ('L2_db_posts', 'L2_db_postmeta', 'L2_db_options'):
    print(f'  {k}：{len(corp[k][0]):,} 字符')

# 层3
pages = sorted(os.listdir('/tmp/t22/pages'))
render = '\n'.join(read_file('/tmp/t22/pages/' + f) for f in pages)
corp['L3_render'] = (render, len(pages))
print(f'  层3 渲染 HTML：{len(pages)} 页 / {len(render):,} 字符')

# 层4
rt_path = '/tmp/t22/runtime_urls.txt'
if os.path.exists(rt_path):
    rt = read_file(rt_path)
    corp['L4_runtime'] = (rt, len([l for l in rt.splitlines() if l.strip()]))
    print(f'  层4 运行时请求：{corp["L4_runtime"][1]} 个唯一 URL')
else:
    corp['L4_runtime'] = ('', 0)
    print('  层4 运行时请求：PENDING（尚未采集）')

# ---- 枚举 uploads 全部文件 ----
files = []
for dp, dns, fns in os.walk(UPLOADS):
    for fn in fns:
        p = os.path.join(dp, fn)
        rel = os.path.relpath(p, UPLOADS)
        files.append((rel, os.path.getsize(p), p))
files.sort()
print(f'\n=== uploads 共 {len(files)} 个文件 ===')

def variants(name):
    """精确 basename 的检索变体"""
    vs = {name}
    vs.add(urllib.parse.quote(name))                      # 整体百分号编码
    vs.add(urllib.parse.quote(name, safe=''))              # 更激进编码
    vs.add(name.replace(' ', '%20'))
    return {v for v in vs if v}

rows = []
for rel, size, p in files:
    name = os.path.basename(rel)
    vs = variants(name)
    res = {}
    for key, (text, _) in corp.items():
        hits = []
        for v in vs:
            for m in re.finditer(re.escape(v), text):
                ctx = text[max(0, m.start() - 60): m.start() + len(v) + 40].replace('\n', ' ')
                hits.append(ctx)
                if len(hits) >= 3:
                    break
            if len(hits) >= 3:
                break
        res[key] = hits
    rows.append({'rel': rel, 'name': name, 'size': size, 'hits': res})

# 附加：同族文件名在语料中的任何出现（家族级）
def family_stem(name):
    s = re.sub(r'-\d+x\d+(?=\.)', '', name)
    s = re.sub(r'-scaled(?=\.)', '', s)
    return s

json.dump(rows, open('/tmp/t22/evidence_rows.json', 'w'), ensure_ascii=False, indent=1)

# ---- 分类输出 ----
zero, used = [], []
for r in rows:
    tot = sum(len(v) for v in r['hits'].values())
    (used if tot else zero).append(r)

print(f'\n=== 零命中（全部 4~5 层 0 引用）：{len(zero)} 个 / {sum(r["size"] for r in zero):,} B ===')
for r in zero:
    print(f'  {r["size"]:>10,}  {r["rel"]}')
print(f'\n=== 有引用：{len(used)} 个 / {sum(r["size"] for r in used):,} B ===')
for r in used:
    tag = ' '.join(f'{k.split("_",1)[1]}={len(v)}' for k, v in r['hits'].items() if v)
    print(f'  {r["size"]:>10,}  {r["rel"]}   [{tag}]')
