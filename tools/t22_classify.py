#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务 2.2 精化分类：区分「自引用」与「外部引用」
自引用 = 该文件作为媒体库附件自身记录中的出现（wp_posts 中 post_type=attachment 的 guid/post_content，
         以及 wp_postmeta 中该附件的 _wp_attached_file / _wp_attachment_metadata）。
         这不构成「被页面使用」。
外部引用 = 其它任何位置的出现（主题源码 / 其它文章内容 / 其它 meta / 渲染 HTML / 运行时请求）。
"""
import os, re, json, urllib.parse

HOME = os.path.expanduser('~')
UPLOADS = HOME + '/Local Sites/sinofresh/app/public/wp-content/uploads'

# ---- 读取附件自引用映射 ----
att = {}   # attachment_id -> set(basenames)
for line in open('/tmp/t22/db_postmeta_all.txt', encoding='utf-8', errors='replace'):
    parts = line.rstrip('\n').split('\t')
    if len(parts) < 3:
        continue
    pid, key, val = parts[0], parts[1], parts[2]
    if key in ('_wp_attached_file', '_wp_attachment_metadata'):
        # 抓出所有形如 2026/09/xxx.ext 的片段
        for m in re.finditer(r'(\d{4}/\d{2}/)?([^";:]+?\.(?:png|jpe?g|webp|gif|svg|avif|pdf))', val):
            att.setdefault(pid, set()).add(os.path.basename(m.group(2)))
att_guid = {}  # attachment_id -> basenames in guid
for line in open('/tmp/t22/db_posts_all.txt', encoding='utf-8', errors='replace'):
    parts = line.rstrip('\n').split('\t')
    if len(parts) < 7:
        continue
    pid, ptype, pstatus, title, guid, content, excerpt = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6]
    if ptype == 'attachment':
        for m in re.finditer(r'([^/"]+?\.(?:png|jpe?g|webp|gif|svg|avif|pdf))(?:"|$|\s)', guid):
            att_guid.setdefault(pid, set()).add(m.group(1))

# ---- 语料（与 t22_evidence.py 同口径，但 posts/postmeta 逐行带归属）----
src_root = '/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme'
TEXT_EXT = {'.php', '.js', '.css', '.html', '.json', '.txt', '.xml', '.scss', '.po', '.pot', '.sql'}
src_chunks = []
for dp, dns, fns in os.walk(src_root):
    dns[:] = [d for d in dns if d not in ('docs', 'node_modules', '_backup', '.git') and not d.startswith('.')]
    for fn in fns:
        if os.path.splitext(fn)[1].lower() in TEXT_EXT and not fn.endswith('.md'):
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) < 8 * 1024 * 1024:
                    src_chunks.append(('SRC:' + os.path.relpath(p, src_root), open(p, encoding='utf-8', errors='replace').read()))
            except Exception:
                pass
SRC_TXT = '\n'.join(c for _, c in src_chunks)

render = '\n'.join(open('/tmp/t22/pages/' + f, encoding='utf-8', errors='replace').read()
                   for f in sorted(os.listdir('/tmp/t22/pages')) if f.endswith('.html'))
rt = open('/tmp/t22/runtime_urls.txt', encoding='utf-8', errors='replace').read() if os.path.exists('/tmp/t22/runtime_urls.txt') else ''

EXT_SCAN = {'L1_src_theme': SRC_TXT, 'L3_render': render, 'L4_runtime': rt}
DB_OPT = open('/tmp/t22/db_options_all.txt', encoding='utf-8', errors='replace').read()

def ctx(t, i, n):
    return t[max(0, i - 70): i + n + 50].replace('\n', ' ').replace('\t', ' ')

files = []
for dp, dns, fns in os.walk(UPLOADS):
    for fn in fns:
        p = os.path.join(dp, fn)
        files.append((os.path.relpath(p, UPLOADS), os.path.getsize(p)))
files.sort()

def variants(name):
    return {name, urllib.parse.quote(name), urllib.parse.quote(name, safe='')}

out = []
for rel, size in files:
    name = os.path.basename(rel)
    vs = variants(name)
    ext, self_hits = [], []

    # posts / postmeta 逐行
    for srcfile, is_meta in (('/tmp/t22/db_posts_all.txt', False), ('/tmp/t22/db_postmeta_all.txt', True)):
        for line in open(srcfile, encoding='utf-8', errors='replace'):
            pl = line.rstrip('\n').split('\t')
            if not any(v in line for v in vs):
                continue
            if is_meta:
                pid, key, val = (pl + ['', '', ''])[:3]
                if pid in att and name in att[pid] and key in ('_wp_attached_file', '_wp_attachment_metadata'):
                    self_hits.append(f'postmeta#{pid}:{key}')
                else:
                    ext.append(f'postmeta#{pid}:{key} :: ' + ctx(line, line.find(name), len(name))[:120])
            else:
                pid, ptype, pstatus = (pl + ['', '', ''])[:3]
                if ptype == 'attachment' and pid in att_guid and name in att_guid[pid]:
                    self_hits.append(f'posts#{pid}:attachment-guid')
                else:
                    ext.append(f'posts#{pid}:{ptype}/{pstatus} :: ' + ctx(line, line.find(name), len(name))[:120])

    for k, t in EXT_SCAN.items():
        for v in vs:
            i = t.find(v)
            if i >= 0:
                ext.append(f'{k} :: {ctx(t, i, len(v))[:130]}')
                break

    # options（burstable 等）
    for v in vs:
        i = DB_OPT.find(v)
        if i >= 0:
            ext.append(f'L2_db_options :: {ctx(DB_OPT, i, len(v))[:130]}')
            break

    out.append({'rel': rel, 'name': name, 'size': size, 'ext': ext, 'self': self_hits})

json.dump(out, open('/tmp/t22/classify.json', 'w'), ensure_ascii=False, indent=1)

zero = [r for r in out if not r['ext']]
nz = [r for r in out if r['ext']]
print(f'=== 零「外部引用」：{len(zero)} 个 / {sum(r["size"] for r in zero):,} B ===')
for r in zero:
    print(f'  {r["size"]:>10,}  {r["rel"]:<58} 自引用={len(r["self"])}')
print(f'\n=== 有外部引用：{len(nz)} 个 ===')
for r in nz:
    if r['size'] > 4000:
        print(f'  {r["size"]:>10,}  {r["rel"]:<52} ext={len(r["ext"])} self={len(r["self"])}')
print('\n=== 疑似「仅自引用」明细（候选真零引用）===')
for r in zero:
    if r['self']:
        print(f'  {r["rel"]}  ← 自引用: {", ".join(sorted(set(r["self"]))[:6])}')
