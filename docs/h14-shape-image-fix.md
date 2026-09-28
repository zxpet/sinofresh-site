# H14 — Shape / Container Library 图片存取修复

日期：2026-09-28 · 版本：theme 2.10.87 → **2.10.88** · `sf-site-settings.js` 1.0.2 → **1.0.3**
状态：**代码与门已完成并本地验证；等待用户授权 pull 上线（未动 dev、未动生产）**

---

## 1. 结论

两个独立断点已按确认的方案修好，并新增 **h14 门**补齐 h13 门的结构性盲区。

| 环节 | 结果 |
|---|---|
| `h14_gate.py --source`（工作区静态） | **23 / 0** |
| `h14_gate.py --preverify`（新代码在 dev 上跑真实 WP 函数） | **23 / 0** |
| `h14_gate.py --live`（改动前 dev，**负对照**） | **10 / 12**（必须红，已红） |
| `h13_gate.py --source`（无新增红） | 16 / 0 |
| `h12_gate.py --source`（既有陈旧版本钉，非本轮引入） | 22 / 2（与改动前一致） |
| PHP 语法 `php -l`（两个文件） | 无错误 |
| JS 语法 `node --check` | 无错误 |

`--preverify` 是本次新增模式：它把**工作区里新的 sanitize 闭包逐字抽出来**，送到 dev 上用**真实 WordPress 的**
`sanitize_title / sanitize_text_field / absint` 跑同一组载荷。因此「修复本身是对的」在 pull 之前就已经被证明，
不是等上线后才知道。它不注册任何设置、不写任何 option、不留服务器文件。

---

## 2. 改动清单

### 断点① JS 选择器少两个方括号

`sinofresh-theme/assets/admin/sf-site-settings.js`

| 行 | 改动 |
|---|---|
| 94 | Add 行重置：`input[name$="[attachment_id]"]` → `input[name$="[attachment_id][]"]` |
| 125 | wp.media 选图回填：同上 |

渲染出来的字段名是 `sf_shapes[attachment_id][]`（追加数组元素），**以 `[]` 结尾**；
`$=` 后缀匹配 `[attachment_id]` 永远不成立 ⇒ `att` / `attInput` 为 `null`，赋值整句跳过。
预览缩略图走的是类选择器，所以照常更新 —— 这就是它**看起来像选成功了**的原因。

> Add 行重置用的是同一个坏选择器：若不一起修，修好 picker 后新行会**继承上一行的图片 ID**。

### 断点② PHP sanitize 按行数组读平行数组载荷

`sinofresh-theme/inc/formula-admin.php`

两个回调（`sf_containers`、`sf_shapes`）从

```php
foreach ((array) $v as $row) { $slug = sanitize_title($row['slug']); if ($slug === '') continue; … }
```

改为按**平行数组**定位读取（语法与 `sf_global_faq` 的 `q[]/a[]` 完全同构）：

```php
$slugs  = isset($v['slug']) && is_array($v['slug']) ? $v['slug'] : array();
$labels = isset($v['label']) && is_array($v['label']) ? $v['label'] : array();
$atts   = isset($v['attachment_id']) && is_array($v['attachment_id']) ? $v['attachment_id'] : array();
$n      = max(count($slugs), count($labels), count($atts));
for ($i = 0; $i < $n; $i++) { … }
```

旧代码读 `$row['slug']` 时，`$row` 是「slug 字段的整个数组」，`$row['slug']` 恒为空 ⇒ 每行都被判空丢弃 ⇒
`$out = array()` ⇒ **H13 的写侧 delete_option 钩子把 option 抹掉** ⇒ 前台表现为「点了保存什么都没存」。
错误源自 H7g 的注释（写着 "rows with a slug survive"，但表单从不送这个结构），H13 只是把症状从
「存成空表」变成「静默没存」。

### Add 行重置

见上表第 94 行，与 picker 同批修。

### 版本

- `sinofresh-theme/style.css:5`：`Version: 2.10.87` → `2.10.88`
- `sinofresh-theme/functions.php:37`：主样式 enqueue `2.10.87` → `2.10.88`
- `sinofresh-theme/inc/formula-admin.php:772`：`sf-site-settings.js` enqueue `1.0.2` → `1.0.3`
- `tools/h13_gate.py`：3 处版本自证常量同步到 `2.10.88` / `1.0.3`（**见 §5**）

---

## 3. 新增 h14 门

`tools/h14_gate.py`（＋ `tools/h14_live_pick.js`，浏览器环节）。三个模式：

### `--source` — 静态断言（23 条）
1. 版本三处同步；
2. **JS 选择器**：带 `[]` 的形态恰好 2 处、裸形态 0 处（防再次少写方括号）；两个 handler 仍在；
3. **PHP**：两个回调都读三条平行数组、无行主序读取残留、只丢全空行、空 slug 从 label 派生；
4. **标记**：两个选项各渲染 3 个平行 input 数组（若有人把表单改回行主序，这条会红）；
5. **不得回退 H13**：四选项空存守卫与双钩子仍在；Certifications 未被动过；
6. 无 CHANGEME/FIXME 残留。

> 断言一律先剥 PHP 注释再比对代码 —— 否则注释里提到的 `$row['slug']` 会被当成残留（H13 门踩过同型坑：
> 注释里出现的 `sf_admin_table_rows` 被计成了调用点）。

### `--preverify` — pull 前的功能证明（23 条）
- 抽取工作区两个新闭包 → dev 上以真实 WP 函数跑 11 条载荷断言（与 `--live` 同一套）；
- 外加浏览器环节里**与 JS 版本无关**的那半：新选择器是否命中渲染出的每一行 input、旧选择器是否命中 0 个（页面事实）。

### `--live` — pull 后（24 条）
- dev 主题版本 = 2.10.88；
- 走**注册后的** `sanitize_option()` 跑同一组载荷；
- 真实浏览器：打开两个库页 → 点 Choose → 选中媒体库第一张图 → 确认 → **隐藏字段必须拿到非 0 的 attachment ID**；
- 断言主题自身资源无 4xx；非主题 4xx 只报不断言（该后台页带着并非本主题的请求）。

载荷断言覆盖：3 行平行载荷保留两行且索引正确位移、**只有图片 ID 的行必须存活**（＝诊断里问的那一条）、
只有 label 的行 slug 派生成 `paw-print`、全空载荷仍归零、Container 同四项、
**负对照：行主序载荷必须产出 0 行**（证明契约已是平行唯一）、探针零写入（前后 option 快照相等）。

---

## 4. 负对照（改动前的 dev）

| 断言 | 结果 |
|---|---|
| dev 主题版本 = 2.10.88 | 红（实际 2.10.87，符合预期） |
| 平行载荷存活行数 | 红（**0 行**，期望 2） |
| 只有图片 ID 的行存活 | 红（0 行） |
| 行主序载荷产出 0 行 | 红（产出 1 行） |
| 选图后隐藏字段有值 | 红（`before=全 0 → after=全 0`） |

**10 通过 / 12 失败**，每一条红都能归因到改动前的那两处代码 —— 门确实能看见它要守的 bug。

---

## 5. 对既有门的影响

- **`h12_gate.py` 的 2 条版本钉**（`VERSION = "2.10.86"`）在 H13 bump 到 2.10.87 时就已经是红的，
  本轮**未触碰**，改动前后都是 22 检查 / 2 失败 —— 既有的陈旧自证常量，不是本轮引入。
  （`h12 --live` 的行为面不读版本号，所以例行验收不受影响。）
- **`tools/h13_gate.py` 的 3 处版本常量已同步**到 2.10.88 / 1.0.3。理由：该门的 `--live` 有一句
  `dev theme version is 2.10.87`，不同步则 **pull 后必红**；这是版本自证常量的同步，不是放宽断言
  （其余 12 条行为断言一字未动，仍 16/0）。
  `b3b_local_check.py` 故意停旧版，按纪律未动。

---

## 6. 超出原方案的一处（待裁决）

原方案的存活判据是「有 slug 才存活」。实施时改成 **FAQ 写法**：只要行上还有任何值（slug / label / 图片）就存活，
只有三项全空才丢弃；并且 **slug 为空而 label 非空时，slug 自动派生**（`sanitize_title($label)`）。

理由两条：
1. 你在诊断问题 3 里明确问过「一行只有图片 ID、label 空、slug 空，会不会被判成空行丢掉」——
   FAQ 写法正是让这种行存活；
2. 若坚持「有 slug 才存活」，Add 出来、只填了图片的新行仍会被静默丢弃 —— 正是本轮要消灭的那类「保存不了」。

若你倾向严格保留原契约，这是两行改动，pull 前可以撤。

---

## 7. 遗留与观察

1. **一张媒体库图片的缩略图 404**（门在浏览器环节报 info）：
   `uploads/2026/09/微信图片_20260629142652_11_458-300x225.jpg`。这是媒体库里某个附件的
   `300x225` 尺寸文件缺失，与 H14 无关（改前就有）。修复方式是让 WP 重新生成缩略图。
2. **`_export/`（407M 迁移包）未被 .gitignore 覆盖**，会一直出现在 `git status` 里；
   建议加一行 `/_export/`，否则将来 `git add -A` 会把它带进仓库。
3. **h13 门的结构性盲区已补**，但同类「标记 ↔ sanitize 结构错配」仍是人工检查项：
   h14 门只覆盖 shapes / containers 两个选项。
4. `docs/batch3b-live-accept-shots/` 下两张 PNG 有历史改动，与本轮无关，未纳入提交。

---

## 8. pull 后验收步骤（等授权）

```bash
# 1. dev 拉取（用户执行）
ssh root@65.49.215.152 'cd /var/www/dev.zxpet.com/site-repo && git pull --ff-only'

# 2. 权威门
python3 tools/h14_gate.py --live     # 期望 24/0（含浏览器选图落值）
python3 tools/h13_gate.py --live     # 期望 12/0
python3 tools/h12_gate.py --live     # 期望 18/0（零漂移，本批不动前台）

# 3. 后台人工抽查（可选）
Shape Library / Container Library → Choose → 选图 → Save → 重新加载看图片还在
```

本批**不改前台输出、不改 CSS 内容、不改模板**，`h12 --live` 的零漂移预期不受影响。

---

## 附件

- 门：`tools/h14_gate.py`、`tools/h14_live_pick.js`
- 只读诊断报告：`docs/h14-shape-image-save-diagnosis.md`
- 诊断期脚本（未入库）：`tools/_h14_picker_check.js`、`tools/_h14_selector_check.js`、`tools/_h14_sanitize_probe5.php`
