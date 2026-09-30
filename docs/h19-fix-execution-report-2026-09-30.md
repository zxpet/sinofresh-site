# H19 执行报告 — Gallery images 字段只能选一张

日期：2026-09-30 ｜ 状态：**已上线生产，全部验收通过（含双向负对照）**
提交：`12adbdf`（修复 + 门）｜ dev 已 `git pull --ff-only` 同步
生产回滚备份：`/root/_h19_rollback_20260930-203638/`

---

## 1. 一句话

`Media → Gallery images` 的媒体选择器向 `wp.media` 请求了 `multiple: true`。
在 WordPress 7.1.2 里 **`true` 的语义是「必须按住 Shift 或 Cmd 才能多选」**，
单击的默认行为是**把整个选择替换成你刚点的那一张** —— 要累加，唯一正确的值
是字符串 **`'add'`**。

改一行取值 + 把后台包版本从 `1.1.0` 提到 `1.2.0`（不换号，已取过旧文件的后台
浏览器会带着坏文件用满一年）。**保存逻辑与前台读取本来就是对的**，没有动。

---

## 2. 根因（读核心代码判定，不是猜）

版本：WordPress **7.1.2**（`wp core version` 实测）。

| 位置 | 事实 |
|---|---|
| `wp-includes/js/media-views.js:1321` | `wp.media.controller.Library.defaults.multiple = false` |
| `media-views.js:1358`（`Library.initialize`） | `this.set('selection', new wp.media.model.Selection(null, { multiple: this.get('multiple'), props: props }))` —— **传进来的值被原样交给 selection** |
| `media-views.js:3121`（`Attachment#toggleSelection`） | `method = _.isUndefined(method) ? selection.multiple : method;` 然后 `if (!method) method = 'add'; if (method !== 'add') method = 'reset';` → `selection[method](model)` |
| `media-views.js:3098-3104`（缩略图点击处理） | 普通单击**不带 method**；只有 `shiftKey` → `'between'`、`ctrlKey/metaKey` → `'toggle'` |
| `media-views.js:26-28`（文档原话） | `multiple: true` → "requires Shift or Cmd/Ctrl to select multiple items"；`multiple: 'add'` → "allows selecting multiple items by clicking thumbnails" |
| `media-models.js:1303 / 1317` | `this.multiple = options && options.multiple;` ＋ `add()` 里 `if (!this.multiple) { this.remove(this.models); }` |

**推导链**：`multiple: true` ⇒ `selection.multiple === true` ⇒ 单击 method 归一成
`'reset'` ⇒ `selection.reset(刚点的那张)` ⇒ **替换**。三处"看起来对"的地方：
`multiple: true` 会真的打开多选能力（Shift/Cmd 可用），所以肉眼与代码形状都像
"设了多选"，只有把核心的 method 分流读出来才能看出单击走的是 reset。

### 为什么 H18 的门没拦住

`h18_gate.py` 只有一条 `"multiple: false" in js` —— 而 H18 自己新增的**单图槽**
（`singleFrameFor`）单独就满足了它。**图集帧的 `multiple` 取值从来没被断言过**，
所以 `true` 一路通过。本批已把这条盲区补上（见 §4）。

---

## 3. 三处环节的实测结论（回答原始 5 问）

| 环节 | 结论 | 证据 |
|---|---|---|
| ① JS 的 `wp.media` 调用 | **设了 `multiple: true`**（不是没设）；**没有**别的代码覆盖 selection —— 全站只有这一处图集 handler，`sf-site-settings.js` 是另一个字段（`multiple: false`，单图，正确） | `grep -rn "wp.media" sinofresh-theme/assets/` 只有 3 处：图集帧、单图槽、容器单图 |
| ② 保存分支（`formula-admin.php:610`） | 存的是 **CSV 单值字符串**（既不是数组也不是 JSON）；`explode(',') → array_filter(array_map('absint')) → implode(',')` ⇒ **选多张不会被截断** | 实测：把 5 个 id 交给**真实** `save_post_sf_formula` 处理器，原样回读 5 个 |
| ③ 前台读取（`functions.php:1988`） | `foreach (explode(',', get_post_meta(..., 'sf_formula_gallery_ids', true)) as $id)` ⇒ **逐 id 全读**，没有只取第一个 | 实测：注入 5 个 id，**5 张全部进入图集**；对照（关掉注入）0 张 |
| ④ 修复 | 取值 `true → 'add'`（1 行）+ 后台包版本 `1.1.0 → 1.2.0` | §4 |
| ⑤ 验证 | 见 §5、§6 | — |

> 注：`$photo_cap = 7` / `$frame_cap = 8` 是 H18c 定的**帧数上限**，与本次的多选
> 缺陷无关。前台"全读"成立，上限之外的部分由 H18c 的规则裁尾。

---

## 4. 改动清单

| 文件 | 前 md5 | 后 md5 | 内容 |
|---|---|---|---|
| `sinofresh-theme/assets/admin/sf-mb-tables.js` | `506cb28c…`（5648 B） | `ab1b7b15…`（6481 B） | 图集帧 `multiple: true` → `multiple: 'add'`；头部 docblock 写明「为什么必须是 `'add'`」（防止后人"整理"回去） |
| `sinofresh-theme/inc/formula-admin.php` | `62eb11a4…` | `99b8fcdc…` | 后台包 enqueue `1.1.0` → `1.2.0`；注释记录「版本不动，immutable 缓存让旧文件活一年」 |
| `sinofresh-theme/functions.php` | `13582d32…` | **未动** | 读取段本来就对 |
| `tools/h18_gate.py` | — | — | 补 **6b 段**：逐帧断言 `multiple` 取值（`'Choose images', multiple: 'add'` 存在、`multiple: true` 不存在、两种帧各一）；`ADMIN_JS_VER → 1.2.0` |
| `tools/h18c_gate.py` | — | — | `ADMIN_JS_VER → 1.2.0` + docstring 记录因果 |
| `tools/h19_gate.py` | 新 | — | 本批的门（source 15 条 / live 18 条） |
| `tools/h19_admin_e2e.js` | 新 | — | 浏览器 E2E（22 条） |
| `tools/h19_e2e.php` | 新 | — | E2E 脚手架：签发 cookie + 一次性记录 / 拆除 |

**前台版本不 bump**（未改 CSS/JS 前台资产；`style.css` 仍 `2.10.89`）。

---

## 5. 验收

| # | 标准 | 结果 |
|---|---|---|
| ① | 门 source 半场 | ✅ `h19_gate.py --source` **15/15** |
| ② | 门 live 半场（dev） | ✅ **18/18** —— 含 HTTP 取真实下发字节比 md5、真实保存处理器跑 5-id CSV、读取段注入对照、postmeta 指纹前后相等 |
| ③ | 门 live 半场（**生产**） | ✅ **18/18** |
| ④ | 浏览器 E2E（dev，真实后台） | ✅ **22/22** |
| ⑤ | 显式部署生产 | ✅ 备份 → `php -l` → 原子 `install`+`mv` → 三方 md5 一致、`apache:apache 644`、无残留 |
| ⑥ | 缓存层（HTTP 实测） | ✅ 公网边缘 `cf-cache-status: MISS`、6481 B、md5 与工作区一致、含 `multiple: 'add'`、无 `multiple: true` |

### ④ 浏览器 E2E 逐条（`tools/h19_admin_e2e.js`）

真实登录生产同构的 dev 后台，在一条一次性记录上走完用户的验收剧本：

```
PASS A0 编辑页 200（不是 staging 锁的 401 页）
PASS A1 编辑页请求 sf-mb-tables.js?ver=1.2.0
PASS A2 该 URL 对浏览器可用
PASS A3 浏览器拿到的字节带累加多选        ← 页面里 fetch 同一 URL，走真实 host
PASS A4 一次性记录初始无图集
PASS B0 媒体库列出 ≥4 张
PASS B1 第 1 次普通单击 → 选中 1 张
PASS B2 第 2 次普通单击 → 选中 2 张       ← 旧代码这里恒为 1
PASS B3 第 3 次普通单击 → 选中 3 张
PASS B4 第 4 次普通单击 → 选中 4 张
PASS C0/C0b 确认按钮找到、弹层关闭无遮挡
PASS C1 隐藏域持有全部 4 个 id（不是只有第一个）
PASS C2 隐藏域与所点 id 完全一致
PASS C3/C4 预览条 4 张、每 id 一张源
PASS D1 真实保存 + 重新载入后后台读回全部 id
PASS D2 重载后预览条仍显示全部
PASS E1 前台 200
PASS E2 前台渲染 ≥4 帧
PASS E3 点过的每一张图都出现在前台
PASS F1 全程无页面 JS 错误
NOTE 重开选择器预选 0 / 4 —— 见 §7
```

截图：`docs/h19-shots/`（`admin-modal-4-selected.png`、`admin-after-save.png`、
`front-end-gallery.png`）。

---

## 6. 负对照（两组，证明断言真的能抓住这个 bug）

### 6.1 代码侧：`h19_gate.py --source` 跑修复前的树

把 `HEAD = 4ebaec8`（修复前）checkout 成独立 worktree，同一套断言跑：

**9 过 / 6 红**，且 6 条红**全部**落在描述修复的条目上
（图集帧取值、`multiple: true` 残留、帧数、enqueue 版本、注释、头部说明）；
9 条「本批不该改」的（保存分支、读取段、卫生）保持绿。

### 6.2 浏览器侧：把修复前的 JS 临时放回 dev（**版本号不变**）

把 `4ebaec8` 的 `sf-mb-tables.js` 装回 dev（`506cb28c…`），enqueue 仍是 `1.2.0`
⇒ **URL 不变**，纯粹测 JS 行为：

```
FAIL A3 the bytes the browser receives carry the accumulating multi-select
        {"status":200,"len":5640,"hasAdd":false,"hasTrue":true}
PASS B1 plain click #1 leaves 1 thumbnail(s) selected
FAIL B2 ... leaves 2 ... — selected=1      ← 复现用户报告的症状
FAIL B3 ... leaves 3 ... — selected=1
FAIL B4 ... leaves 4 ... — selected=1
FAIL C2 the field holds the exact ids that were clicked — 329（只剩 1 个）
```

**17 过 / 5 红**，红的正是「多选不成立」本身 ⇒ 这组断言是有效探测器，不是绿灯
装饰。随后已 `git checkout --` 还原并复核 md5 `ab1b7b15…`、仓库干净，复跑回
**22/22**。

---

## 7. 已知行为 / 遗留

- ⚠️ **实测（不是推断）**：**重开选择器时预选数为 0 / 4** —— 选择器每次都是新建
  的，不带上该记录已有的图；而 `hidden.value = items.map(...)` 是整体覆盖。
  ⇒ 按钮文案是 "Choose / update images"，但语义是**替换整套**，不是"在原有基础上增删"。
  典型踩坑：记录已有 4 张 → 点开 → 只补选 1 张 → 保存后**只剩 1 张**。
  - 这是**本批之前就有的行为**，非本批回归；修多选缺陷后仍然存在（修的是"一次能否选多张"）。
  - 若要去掉这个坑，需要下一批做**预选**（打开时把 `sf_formula_gallery_ids` 的 id
    装进 frame 的 selection）。届时建议同时把取值换成 `'toggle'`，否则预选进来的图
    **点不掉**（`'add'` 只加不减），只能靠 "Remove all" 重来。
- `sf_formula_gallery_ids` 相册框不限个数，但**只有前 6 个能上竖列**（H18c 上限语义，
  见 `docs/h18c-fix-execution-report-2026-09-30.md` §6）。
- 兄弟门红集合（`--live`，与 H19 之前逐条相同 ⇒ **零新增红**）：
  h9=4／h10=1／h11=4／h12=4／h14=1；h13 12/12、h18 8/8、h18c 27/27、h19 18/18 全绿。
  （h9–h12 的门输出格式不同，红数取自各自的汇总行：`RESULT 20 ok, 4 FAIL`、
  `22/23 passed`、`19 passed, 4 failed`、`18 checks, 4 failed`。）
- 生产与 dev 的一次性记录（`h19-e2e-temporary` / `h19-probe-temporary`）实测残留
  **0 / 0**；服务器 `/tmp/h19*` 已清；E2E 的会话令牌已 `WP_Session_Tokens::destroy`。

---

## 8. 复跑命令

```bash
# 门
PY=/Users/meng/.workbuddy/binaries/python/versions/3.13.12/bin/python3
$PY tools/h19_gate.py --source
$PY tools/h19_gate.py --live                     # dev
H19_WP_ROOT=/var/www/zxpet-v2 \
H19_THEME_DIR=/var/www/zxpet-v2/wp-content/themes/sinofresh-theme \
H19_SITE=www.zxpet.com H19_BASIC= $PY tools/h19_gate.py --live   # 生产

# 浏览器 E2E（dev）
scp tools/h19_e2e.php root@65.49.215.152:/tmp/
ssh root@65.49.215.152 'cd /var/www/dev.zxpet.com/public && wp eval-file /tmp/h19-e2e.php setup --allow-root'
scp root@65.49.215.152:/tmp/h19-e2e.json /tmp/
NODE_PATH=/Users/meng/.workbuddy/binaries/node/workspace/node_modules \
  /Users/meng/.workbuddy/binaries/node/versions/22.22.2-3/bin/node tools/h19_admin_e2e.js
ssh root@65.49.215.152 'cd /var/www/dev.zxpet.com/public && wp eval-file /tmp/h19-e2e.php teardown --allow-root'
```

回滚：`cp -p /root/_h19_rollback_20260930-203638/{sf-mb-tables.js,formula-admin.php}`
到生产对应目录（`assets/admin/` 与 `inc/`），或重新执行本批提交前的显式部署。
