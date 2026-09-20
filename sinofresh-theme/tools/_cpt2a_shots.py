#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2A —— 后台 / 前台截图交付（单会话）

驱动 agent-browser（子进程顺序调用，不用 shell 循环：shell 侧命令替换会让
会话漂移，eval 会打到 about:blank）。

登录不走口令：调用 _cpt2a_mint_cookie.php 铸造真实会话 cookie，再以
`agent-browser cookies set` 注入。

⚠️ 两个实测要点：
  · cookie 必须在本脚本内注入；另起一个脚本跑后台 URL 会因为 `close` 清掉
    上下文而被打回 wp-login.php?...&reauth=1
  · 视口必须在 open 之后设置（open 会重置视口）
  · 展开编辑器侧栏面板用 eval 点 .components-panel__body-toggle；用
    `find text ... click` 会命中别的元素并导航走（实测落到了 about.php）

用法：python3 tools/_cpt2a_shots.py
"""
import json
import os
import re
import subprocess
import sys

NODE_BIN = '/Users/meng/.workbuddy/binaries/node/versions/22.22.2-3/bin'
AB = os.path.join(NODE_BIN, 'agent-browser')
PHP = os.path.expanduser('~/Library/Application Support/Local/lightning-services/php-8.2.29+0/bin/darwin-arm64/bin/php')
SOCK = os.path.expanduser('~/Library/Application Support/Local/run/cVn1NjBpB/mysql/mysqld.sock')
THEME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(THEME, 'screenshots', 'batch2a-cpt')
BASE = 'http://sinofresh.local'
POST_ID = 152

os.makedirs(OUT, exist_ok=True)
ENV = dict(os.environ)
ENV['PATH'] = NODE_BIN + ':' + ENV.get('PATH', '')
log = []


def ab(*args, timeout=120):
    r = subprocess.run([AB, *args], capture_output=True, text=True, env=ENV, timeout=timeout)
    out = (r.stdout or '') + (r.stderr or '')
    log.append((' '.join(args), r.returncode, out.strip()[:300]))
    return r.returncode, out


def mint():
    r = subprocess.run([PHP, '-d', 'mysqli.default_socket=' + SOCK,
                        os.path.join(THEME, 'tools', '_cpt2a_mint_cookie.php')],
                       capture_output=True, text=True)
    kv = dict(l.split('=', 1) for l in r.stdout.strip().splitlines() if '=' in l)
    if 'AUTH_VALUE' not in kv:
        print('*** cookie 铸造失败:\n' + r.stdout + r.stderr)
        sys.exit(1)
    return kv


def goto(path, settle=1500):
    ab('open', BASE + path)
    ab('wait', '--load', 'load')
    ab('wait', str(settle))
    url = ab('get', 'url')[1].strip()
    title = ab('get', 'title')[1].strip()
    ok = 'wp-login' not in url
    print(f'  url   : {url}')
    print(f'  title : {title}')
    if not ok:
        print('  *** 未登录 / 被重定向到登录页')
    return ok


def shot(name):
    rc, out = ab('screenshot', '--screenshot-dir', OUT, '--json')
    m = re.findall(r'"(/[^"]+\.png)"', out) or re.findall(r'(/[^\s"]+\.png)', out)
    if not m:
        print(f'  *** {name}: 未拿到路径 {out.strip()[:200]}')
        return
    dst = os.path.join(OUT, name + '.png')
    os.replace(m[0], dst)
    print(f'  [shot] {name}.png  {os.path.getsize(dst):,} B')


kv = mint()
print(f"cookie: {kv['AUTH_NAME']}  user={kv['USER']}  expires={kv['EXPIRES']}")

print('\n0. 启动会话 + 注入 cookie + 设视口')
ab('open', BASE + '/')
ab('cookies', 'set', kv['AUTH_NAME'], kv['AUTH_VALUE'], '--url', BASE + '/', '--path', '/', '--httpOnly')
ab('cookies', 'set', kv['LOGGED_IN_NAME'], kv['LOGGED_IN_VALUE'], '--url', BASE + '/', '--path', '/', '--httpOnly')
ab('set', 'viewport', '1440', '900')
print('  cookies get:', ab('cookies', 'get')[1].strip()[:200])

print('\n1. 后台仪表盘（左侧菜单 Formulas 应位于 页面 与 评论 之间）')
goto('/wp-admin/', 2500)
shot('01-admin-menu-formulas')

print('\n2. Formulas 列表页')
goto('/wp-admin/edit.php?post_type=sf_formula', 1500)
shot('02-formulas-list')

print('\n3. 测试配方编辑页（eval 展开两个 taxonomy 面板）')
goto(f'/wp-admin/post.php?post={POST_ID}&action=edit', 5000)
js = ("(()=>{const t=[...document.querySelectorAll('.components-panel__body-toggle')];"
      "const hit=t.filter(b=>/Dosage Forms|Functions/i.test(b.textContent));"
      "hit.forEach(b=>{if(b.getAttribute('aria-expanded')==='false')b.click();});"
      "return JSON.stringify({panels:t.map(b=>b.textContent.trim()).slice(0,16),"
      "expanded:hit.map(b=>b.textContent.trim()+'='+b.getAttribute('aria-expanded'))});})()")
print('  panel eval:', ab('eval', js)[1].strip()[:400])
ab('wait', '1200')
shot('03-test-formula-edit')

print('\n4. /formulas/ 归档页（回退 archive.html）')
goto('/formulas/', 1500)
shot('04-formulas-archive')

print('\n5. 配方详情页（回退 single.html）')
goto('/formulas/test-joint-coat-soft-chews/', 1500)
shot('05-formula-detail')

print('\n6. 关闭浏览器')
ab('close', '--all')

print('\n=== 失败调用 ===')
bad = [x for x in log if x[1] != 0]
print('  无' if not bad else '\n'.join(f'  rc={c} {cmd}\n      {o[:200]}' for cmd, c, o in bad))
print(f'\n产出目录 {OUT}')
for f in sorted(os.listdir(OUT)):
    print(f'  {f}  {os.path.getsize(os.path.join(OUT, f)):,} B')
