# 批次 2A 执行报告 —— 注册 CPT 基础设施（不迁移数据）

> 站点：sinofresh.local（LocalWP / nginx + PHP 8.2.29 + WP 7.1.1）
> 唯一改动文件：`sinofresh-theme/functions.php`
> 备份：`_backup/batch2a-cpt-20260920-122640/`（`functions.php` + `functions-local.php`，均 106,973 B / `65038aa0…860d4c`）
> 执行时间：2026-09-20 12:26 – 12:45（CST）

---

## 1. 交付物

| # | 产出 | 位置 |
|---|---|---|
| 1 | CPT / taxonomy / meta / shortcode 代码块（+437 行） | `sinofresh-theme/functions.php` L308–L711 |
| 2 | 占位符 `{{FORM_CRUMB}}` / `{{FORM_HREF}}` 扩展 | 同上 L1798–L1899 |
| 3 | BreadcrumbList 模板候选分支 | 同上 L1894–L1899 |
| 4 | 回滚基线备份 | `_backup/batch2a-cpt-20260920-122640/` |
| 5 | 核验脚本（可重跑） | `sinofresh-theme/tools/_cpt2a_{verify_state,render_check,cleanup,mint_cookie,shots}.php`、`tools/_cpt2a_ab_{cmp,confine}.py` |
| 6 | 截图 5 张 | `sinofresh-theme/screenshots/batch2a-cpt/01–05*.png` |

---

## 2. 改动范围

`diff -u 备份 现状` 结果：**5 个 hunk、1 行既有代码被改写、+437 行**（2534 行 → 2970 行）。

```
@@ -304,6 +304,411 @@     ← 主代码块（CPT / taxonomy / meta / shortcode）
@@ -1393,6 +1798,10 @@    ← 占位符 docblock 增补 {{FORM_CRUMB}} / {{FORM_HREF}}
@@ -1403,7 +1812,10 @@    ← $post_id 判定（唯一被改写的既有行）
@@ -1429,12 +1841,30 @@   ← form_crumb / form_href 求值
@@ -1464,6 +1894,12 @@   ← BreadcrumbList 分支
```

唯一被改写的既有行（`sinofresh_template_placeholders()` 内）：

```php
- $post_id = is_singular('post') ? (int) get_queried_object_id() : 0;
+ $post_id = (is_singular('post') || is_singular('sf_formula')) ? (int) get_queried_object_id() : 0;
```

除该行外，既有逻辑零改动。`find sinofresh-theme -newermt "12:27"` 确认本批只落手 `functions.php` 一个生产文件（`style.css` / `theme.json` 哈希未变）。

---

## 3. 代码结构

### 3.1 注册项（L337–L421）

| 对象 | 关键参数 | WP 实际解析值（`get_post_type_object()` 读回，非源码字面） |
|---|---|---|
| `sf_formula` | `public=true`、`has_archive=true`、`rewrite.slug='formulas'`、`with_front=false`、`menu_position=21`、`show_in_rest=true`、`hierarchical=false`、`supports=[title,editor,thumbnail,excerpt,revisions,page-attributes,custom-fields]` | `public=true` / `has_archive=true` / `query_var='sf_formula'` / `menu_position=21` / 后台菜单 `$menu[21]='Formulas'`，位于 Pages(20) 与 Comments(25) 之间 |
| `sf_formula_form`（Dosage Forms） | `public=false`、`publicly_queryable=false`、`rewrite=false`、`show_ui=true`、`show_in_rest=true` | `public=false` → 自动派生 `publicly_queryable=false` / `query_var=false` / `rewrite=false` / `show_in_nav_menus=false` |
| `sf_formula_use`（Functions） | 同上 | 同上 |

注册顺序：`add_action('init', 'sinofresh_register_formula_types', 9)` → 早于所有 `init` 默认优先级消费者。

### 3.2 meta（4 个，本主题首次使用 `register_post_meta()`）

`sf_formula_ingredients` / `sf_formula_analysis` / `sf_formula_specs` / `sf_formula_source`
统一 `type=string`、`single=true`、`show_in_rest=true`、`auth_callback=fn() => current_user_can('edit_posts')`。

`get_registered_meta_keys('post','sf_formula')` 读回 **5 条** = 上述 4 条 + 既有 `footnotes`（全站已注册）。
键名不带前导下划线 → 与既有 `sf_last_reviewed` 一致，保留在内置「自定义字段」面板中可编辑。
`sf_formula_source` 按 Q3 定义：**数据来源标注，仅后台可见**，短代码不输出到前端。

### 3.3 重写规则

| 指标 | 基线 | 现状 |
|---|---|---|
| `rewrite_rules` 条数 | 112 | **135（+23）** |

规则落位（按规则数组真实顺序）：

| 路径 | 命中规则 # | 目标 |
|---|---|---|
| `formulas/` | #1 `formulas/?$` | `index.php?post_type=sf_formula` |
| `formulas/page/2/` | #4 `formulas/page/([0-9]{1,})/?$` | `…&paged=2` |
| `formulas/<slug>/` | #58 `formulas/([^/]+)(?:/([0-9]+))?/?$` | `index.php?sf_formula=<slug>` |
| `products/soft-chews/` | **#116（未变）** `(.?.+?)(?:/([0-9]+))?/?$` | `index.php?pagename=soft-chews` |
| `products/dental-chews/` | #116（未变） | 同上 |

即 CPT 归档路由在 #1–#7、单条路由在 #52–#58，**全部早于 #116 的页面兜底**，但 `products/*` 未被劫持。

`sinofresh_formula_flush_rewrite_rules()`（L442）与既有 3 个 shortcode 同区插入：

- 护栏**读回已存规则**判断是否需要刷新（自愈），而不是锁一个版本 flag —— `flush_rules()` 把实活推迟到 `wp_loaded`，若在 `init` 写 flag，请求中途死掉会永久 404 且不再重试。
- 调用 `flush_rewrite_rules(false)` **软刷新**：推迟执行在 `save_mod_rewrite_rules()` 之前返回，nginx 下不写 `.htaccess`，安全。
- 双挂载：`init` prio 99（所有 permastruct 注册完之后）+ `after_switch_theme`。

### 3.4 shortcode `[sf_formula_grid]`（L585–L711）

| 属性 | 默认 | 行为 |
|---|---|---|
| `form` | `''` | 空则调 `sinofresh_formula_current_form()`；**权威来源是 queried object**，URL 末段仅兜底 |
| `use` | `''` | `sanitize_title()` 后按 slug 过滤 |
| `limit` | `-1` | 直接进 `posts_per_page` |
| `columns` | `4` | `max(1, min(6, (int)))` 夹取 |
| `cta` | `reference` | `none` 时不渲染 `.sf-formula__cta` |
| `links` | `true` | `false` 时不渲染 `<a href>` |
| `empty` | `hide` | **本批只实现 `hide`**（返回空串） |

排序：`menu_order ASC, title ASC`；只取 `publish`；`no_found_rows=true`。

输出骨架：

```html
<div class="sf-fgrid" style="--sf-fgrid-cols:4">
  <script type="application/json" class="sf-formulas-data">[…name/slug/url/form/use/sections…]</script>
  <script type="application/ld+json">{"@type":"ItemList",…}</script>
  <article class="sf-fcard"><span class="sf-fcard__use">…</span><h3 class="sf-fcard__name">…</h3><p class="sf-fcard__spec">…</p><div class="sf-fcard__actions">…</div></article>
</div>
```

**为什么容器自带 inline 样式**：`do_shortcode()` 在 `do_blocks()` **之前**执行，短代码产出永远拿不到 `wp-container-core-*` 布局类，所以列数用 inline 自定义属性 `--sf-fgrid-cols` 自带，不依赖块编辑器注入的样式。

三条硬约束已内建：

- **R3（`</script>` 护栏）** `sinofresh_formula_script_json()`（L541）：`wp_json_encode(…, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES)` → `preg_replace('#</(?=script)#i','<\\/')` → 断言 `strpos($json,'</script')===false`，不通过则 `error_log` 并返回空串（整个 shortcode 放弃输出，不吐半截）。
- **R6（三处同源）** 循环内单点取 `$name = html_entity_decode(get_the_title($formula), ENT_QUOTES, 'UTF-8')`，`<h3>` / JSON `.name` / `data-formula` 全部从它派生；`data-formula` 经 `esc_attr()` 落回实体形式，与旧模板逐字节一致。
- **K1–K4** `data-formula` 保留裸 `&`（JSON 用 `JSON_UNESCAPED_*`）、卡片标题只允许 `<h3>`（`toc-nav.js` 按 `<h2>` 序列编号页码，`<h2>` 会污染目录）。

### 3.5 占位符与 BreadcrumbList

| 占位符 | 解析规则 |
|---|---|
| `{{FORM_CRUMB}}` | 取 `sf_formula_form` 首个 term 的 slug → `sinofresh_formula_label()` → **剂型页标题**（`Soft Chews`） |
| `{{FORM_HREF}}` | 同 slug → `/products/<slug>/`；**无对应 term（Q2）→ `/products/`** |
| `{{TITLE}}` | 详情页现走 `sf_formula` 分支，输出 `esc_html()` 后的配方标题 |

`sinofresh_formula_label($slug, $fallback)`（L506）以**剂型页标题为权威**、调用方 fallback 次之、humanized slug 兜底 —— 见 §5 勘误 1。

BreadcrumbList 分支在 `is_singular('post')` 之后新增：

```php
} elseif (is_singular('sf_formula')) {
    $candidates = array('single-sf_formula', 'single');
} elseif (is_search()) {
```

2A 不建 `templates/single-sf_formula.html`（留 2C），此分支只保证面包屑在回落到 `single` 模板时仍能取到正确标题。

### 3.6 本批未做（按指令边界）

不建 `single-sf_formula.html`、不引入新 CSS/JS、不迁移 21 条配方数据、不动 8 个剂型模板、不改 `configurator.js`。`formulas.js`（`1.0.0`）与 `formulas.css` 沿用既有 enqueue，**无版本号改动**。

---

## 4. 12 项核验结果

| # | 核验项 | 结果 | 证据 |
|---|---|---|---|
| 1 | 后台菜单出现 Formulas，位于 Pages 与 Comments 之间 | ✅ | `$menu[21]='Formulas'`；截图 `01-admin-menu-formulas.png` |
| 2 | 测试配方 `/formulas/<slug>/` 与 `/zh/formulas/<slug>/` 均 200 | ✅ | 发布态实测 200 / 200，中文页 `<html lang="zh-CN"` |
| 3 | 8 个剂型页仍 200 | ✅ | 真实 slug：`soft-chews` `tablets` `powders` `liquids` `pastes` `dental-chews` `drops` `fish-oil`；中英双版 **16/16 = 200** |
| 4 | 现有 shortcode 未受影响 | ✅ | `sf_explore_chips` 810 B / `sf_archive_count` "1 article" / `sf_blog_chips` 1962 B，全部正常输出 |
| 5 | 现有占位符未受影响 | ✅ | `{{TITLE}}`/`{{MID_CRUMB}}`/`{{LAST_UPDATED}}` 正常；`{{FORM_HREF}}` 无 term → `/products/`（Q2 生效） |
| 6 | 无 PHP 报错 | ✅ | `~/Local Sites/sinofresh/logs/php/error.log` = **69,385 B / mtime 2026-09-19 17:32:01**，体积与 mtime 与基线逐字节一致（无追加段） |
| 7 | `rewrite_rules` 条数 +23 | ✅ | 112 → **135**；含 `sf_formula=` 的规则 7 条（#52–#58），另 7 条归档路由（#1–#7） |
| 8 | `/products/soft-chews/` 仍解析为 `pagename` | ✅ | 实测 #116 `index.php?pagename=soft-chews`，与基线同一规则 |
| 9 | `/formulas/` 归档页 200 | ✅ | 200；截图 `04-formulas-archive.png` |
| 10 | 源码 == Local | ✅ | `cmp -s` IDENTICAL；`diff -rq` 的 `Files differ` = **0**；两侧 `functions.php` 同 sha256 `6272dcba…b88f835` |
| 11 | `"/ -->"` 零残留 | ✅ | 全主题扫描命中 12 处**全在 `docs/` 与 `tools/`**（文档引用 + 测试脚本），生产文件 0 |
| 12 | 截图交付 | ✅ | 5 张：后台菜单 / Formulas 列表 / 测试配方编辑页（Dosage Forms + Functions 面板均展开，可见 `soft-chews`、`Joint care`）/ `/formulas/` 归档 / 配方详情 |

### 4.1 渲染契约核验（`_cpt2a_render_check.php`，可重跑）

忠实管线 `do_shortcode → do_blocks → wptexturize → convert_smilies`，对**渲染后字节**断言：

```
===== 结果：PASS 45 / FAIL 0 =====
```

覆盖：K1（`.sf-formula__cta` + `data-formula`）、K2（`.sf-formulas-data` 顶层键 `name,slug,url,form,use,sections`；3 条 section 的 label 与旧模板同名 `Ingredients`/`Guaranteed Analysis`/`Standard Specs`）、K3（只出 `<h3>`，无 `<h2>`）、K4（JSON 正文裸 `&`、无 `&amp;`，ItemList 可 `json_decode`）、R3（恶意 `</script>` 载荷被转义且仍可解码）、R6（`<h3>` / `data-formula` / JSON `.name` 三处解码后逐字节相同，源侧 `data-formula="Test Joint &amp; Coat Soft Chews"` 与旧模板一致）、R1（queried object 权威 / 显式参数优先）、R2（`empty` 只实现 hide）、以及 `cta=none`、`links=false`、`columns` 1–6 夹取、`limit`、不存在 form / use 未命中 的边界。

### 4.2 既有页面回归（A/B 掩码对比）

| 项 | 结果 |
|---|---|
| 抓取页面 | 19 页，A（改动前）/ B（改动后）各一轮 |
| 页面体积 | 每页两侧均 **2,845,486 B**，全部 200，无 PHP 错误 |
| 掩码 sha256 | **19/19 完全一致** |
| 原始 diff | 2,656 B，跨 14 页，**全部 diff 偏移 ⊂ 掩码区间**（类型 `gf_hidden_val` / `gf_phone_uid`，即 Gravity Forms 的按请求令牌） |
| **A/A 对照组** | 同代码连抓两轮 → 同样 14 页 / 2,658 B / 同样掩码类型 → 判定为**仪器噪声** |

结论：批次 2A 对既有页面的渲染增量为 **0**。对照组是关键——没有它，那 2,656 B 会被误读成真实回归。

### 4.3 REST 与清理

- `/wp/v2/sf_formula`、`/wp/v2/types/sf_formula`、两个 taxonomy 的 collection 路由均 200；4 个 meta 键出现在 `meta` 中（`≥` 未被转义）。
- 测试配方 `wp_trash_post()` 入回收站（非永久删除），meta 保留、可恢复；`/formulas/<slug>/` 归 404。
- 探针建的 2 个 term 已 `wp_delete_term` 删除，词条计数回到 **0 / 0**（pre-2A 基线）。
- 临时会话已销毁，`session_tokens` 只剩 1 条长期会话。

### 4.4 收尾状态

```
functions.php          6272dcba832235e7d3b591d222afe2847b92b6c53d312b6ef611d9350b88f835  125,009 B
style.css              6a9261ee4b53b3eb5436ff05294fa86bf21c680a3fe9d638fe00da32b323befa  （未改动）
theme.json             88b7cd8d00c40afed25712fe38b910e01274c59c5977a524cb12a27fc60e1657  （未改动）
rewrite_rules          135
sf_formula             publish=0  trash=2   ← 见 §6
sf_formula_form/use    terms 0 / 0
error.log              69,385 B / 2026-09-19 17:32:01（与基线一致）
/formulas/             200        /products/*  16/16 = 200
/                      200        /blog/  200    /test-article/  200
```

---

## 5. 执行中发现并修复的问题

**1）term 的 `name` ≠ `slug`，不能当显示标签用（真实缺陷，非测试假象）**

`wp_set_object_terms($id, 'soft-chews', 'sf_formula_form')` 传裸字符串时，WP 建出的 term **name 就等于 slug**（`soft-chews`），name 与 slug 是两套独立字段。因此 `sinofresh_formula_list_name()` 曾输出 `Standard Formulas — soft-chews`。

修复：新增 `sinofresh_formula_label()`（L506），以**剂型页标题为权威**，其次调用方 fallback，最后 humanized slug；`list_name()` 与 `{{FORM_CRUMB}}` 全部改走它。复验：`Standard Formulas — Soft Chews` ✅。**2B 建 term 时必须显式传 `slug` + `name` 两个参数**，否则卡片 eyebrow / 面包屑会退化成 slug。

**2）`</script>` 护栏必须有反例测试**

正向断言（正常标题不含 `</script`）永远通过，证明不了护栏有效。已加反例：直接喂 `Evil</script><script>alert(1)</script>`，断言输出不含 `</script`、含 `<\/script`、且仍可 `json_decode`。

**3）探测器选错文件**

`wp-content/debug.log` 是 CLI 残留，不能当 Web 运行时错误证据。本批一律以 `~/Local Sites/sinofresh/logs/php/error.log`（PHP-FPM `log_errors=On`）为准，以「① 体积不变 ② 追加段不含 `functions.php`」双条件判定。

**4）`WP_Session_Tokens::get_all()` 是数字下标 LIST，不是 verifier 映射**

`get_all()` = `array_values( get_sessions() )`。把它的键传给 `destroy()` 会被二次哈希、查不到、**静默无操作**（无报错无警告，唯一症状是会话数不变）。verifier 只存在于 `session_tokens` user meta，而 `hash_token()` 单向不可逆。修复：铸造脚本记录**原始 token** 到 `/tmp/_cpt2a_tokens.txt`，清理时先按原始 token 调 `destroy()`，再兜底按 verifier 从 meta 裁剪；断言必须**重读 meta**，不能读同请求内已陈旧的 `get_all()`。新进程复验：meta 1 条、临时会话 0 条 ✅。

**5）探针记录被重复创建（本轮新发现）**

`wp_trash_post()` 会把 `post_name` 改写为 `<slug>__trashed`。`get_page_by_path()` 跳过 trash，而 `get_posts(post_status='any')` 里 `any` 会排除 `exclude_from_search=true` 的 trash —— 两条路都查不到已入回收站的记录，于是「复用」逻辑失效、又建了一条新记录。修复：`_cpt2a_render_check.php` 改为按 `post_name` **前缀**枚举全部状态（`LIKE '<slug>%'`）并优先复用 publish 记录，`_cpt2a_cleanup.php` 同步改为遍历清理。复跑验证：正确复用 ID=154，未再新增。

**6）同文件并行编辑会静默丢写**

同一轮里对 `functions.php` 连发 5 个 Edit，只有第 1、5 个落地，第 2/3/4 个无声丢失（`diff` 显示 0 行变化、`grep` 确认缺失）。本批起改为**逐个串行 Edit，每个 Edit 后立刻 `grep` + `php -l` 验证再发下一个**。

---

## 6. 遗留项

| # | 项 | 说明 |
|---|---|---|
| 1 | **`sf_formula` trash = 2（ID 152、154）** | 均为本批核验探针记录（标题 `Test Joint & Coat Soft Chews`），因 §5-5 的重复创建 bug 产生 2 条。两条都完整保留 meta、可从回收站恢复。**未做永久删除**（遵守指令）。建议在 2B 数据迁移时一并「清空回收站」处置，届时单独确认。 |
| 2 | `sf_formula` 尚无 `single-sf_formula.html` | 详情页目前回落 `single` 模板，页面 200、占位符全部解析、无残留 `{{`；卡片化版式属 2C。 |
| 3 | `[sf_formula_grid]` 尚未接入任何模板 | 8 个剂型页仍为硬编码 21 个 `<details>` + 手写 ItemList，属 2B。 |
| 4 | `configurator.js readFormula()` 仍抓 DOM | 仍读 `.sf-formula__name` / `.sf-formula__label`，未切到 `.sf-formulas-data`，属 2B。 |
| 5 | `empty` 参数只实现 `hide` | 按 R2 约束；`show-message` 等模式留待有真实需求时再加。 |
| 6 | 历史遗留（与本批无关） | `wp_options.wpai_version='1.3.0'` 孤儿 option；`sinofresh-theme/_backup_x/` 空目录；`sinofresh-theme/_backup/`（22.86 MB / 90 快照）建议归档出主题目录。`style.css` 当前头版本 `2.10.39`（批次 1 步骤 2 已 bump，与 enqueue 一致）。 |

---

## 7. 与批次 2B 的接口

2B 需要的最少输入，本批已就位：

| 2B 动作 | 依赖的本批产出 |
|---|---|
| 迁移 21 条配方 | CPT `sf_formula` + 2 taxonomy + 4 meta 已注册 |
| term 建立 | `sf_formula_form` 的 term **slug 必须等于剂型页 slug**；**必须显式传 `slug` 与 `name`**（§5-1） |
| 模板替换 `<details>` 块 | `[sf_formula_grid form="<dosage-slug>"]`；列数用 `columns` |
| 替换手写 ItemList | shortcode 已内建 ItemList JSON-LD + `.sf-formulas-data` |
| 切 `configurator.js` 数据源 | `.sf-formulas-data` 形状已锁定：`{name, slug, url, form, use, sections[3]{label,value}}`，label 与旧模板同名 |
| 面包屑 | `{{FORM_CRUMB}}` / `{{FORM_HREF}}` 已可按剂型解析 |

---

## 8. 回滚

```bash
cp _backup/batch2a-cpt-20260920-122640/functions.php sinofresh-theme/functions.php
cp _backup/batch2a-cpt-20260920-122640/functions-local.php \
   "$HOME/Local Sites/sinofresh/app/public/wp-content/themes/sinofresh-theme/functions.php"
```

回滚后 `rewrite_rules` 里的 CPT 路由会失效，需在「设置 → 固定链接」点一次保存（或恢复备份前的 `rewrite_rules` option）。备份内 `rewrite_rules` 基线 = 112 条。
