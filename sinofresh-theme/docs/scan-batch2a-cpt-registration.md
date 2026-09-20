# 批次 2A 第一步 · 扫描报告（注册 CPT / 2 taxonomy / 4 meta / shortcode）

- **日期**：2026-09-20
- **性质**：**只读扫描**。改 0 行代码、写 0 行 DB（含内存注册预演，`rewrite_rules` 选项未落盘）
- **范围**：`sinofresh-theme/functions.php` 的结构定位、现有先例、rewrite 现状、插入点与风险
- **工具**：`tools/_cpt2a_probe{1..7}.php` + `_cpt2a_probe5b.php`
- **证据**：`docs/scan-evidence-batch2a-20260920/`（本文档生成时导出）

---

## 0. 结论速览

| # | 结论 |
|---|---|
| 1 | `functions.php` 2534 行、**16 个 `wp_enqueue_*` 句柄**、**3 个 `sf_*` shortcode**、**10 个 block pattern**。无 `register_post_type` / `register_taxonomy` / `register_post_meta` / `add_meta_box` —— **CPT 面全为绿地** |
| 2 | **⚠️ 重要纠正**：`sf_last_reviewed` **没有** `register_post_meta` 写法可参考（全站 `register_post_meta` = 0 处）。它只被 `get_post_meta()` 裸读，靠 WP 内置「自定义字段」面板写入。**2A 的 4 个 meta 是本主题第一次 `register_post_meta`** |
| 3 | 8 剂型页 slug **全部一致**：`soft-chews`(20) `tablets`(21) `powders`(22) `pastes`(23) `drops`(24) `liquids`(25) `fish-oil`(26) `dental-chews`(27)，父页 `products`(19)，URL 形态 `/products/<slug>/` |
| 4 | **无任何自定义 rewrite 规则**（112 条全为 WP 默认；主题与插件侧 `add_rewrite_rule`/`add_permastruct` 均 0 处）。唯一额外 permastruct 是 TranslatePress 的 `language_switcher` |
| 5 | **`flush_rewrite_rules` 当前无人触发**：`after_switch_theme` 上只有 WP 核心的 `_wp_menus_changed` / `_wp_sidebars_changed`；主题与插件均未挂钩。⇒ 「只在 theme activation 时 flush」**在本站永远不会执行**，必须用一次性守卫式 flush |
| 6 | 内存注册预演：CPT 规则落在 **#42–#64（`extra_rules_top`）**，先于 #116 页面兜底规则 → `/formulas/<slug>/` 解析为 `index.php?sf_formula=$1&page=$2` ✓；`/formulas/`、`/formulas/page/2/`、`/formulas/feed/` 均正确命中；**页面规则（#116）不受影响** |
| 7 | `/zh/formulas/<slug>/` **可解析**：TP 的前缀剥离发生在 `parse_request` 之前、与 post type 无关（实测 `/zh/products/soft-chews/` → 200 `lang="zh-CN"`） |
| 8 | **⚠️ 2A 有一个立即生效的可见副作用**：`has_archive => true` 使 `/formulas/` 立刻上线，而 `archive-sf_formula.html` 尚未存在 → 回退到 **`archive.html`（博客归档版式，含 `[sf_archive_count]`/`[sf_blog_chips]`）**；`/formulas/<slug>/` 同理回退到 **`single.html`** |
| 9 | **⚠️ 核验项 6「debug.log 无新条目」是无效探测器**：`WP_DEBUG_LOG = false`、CLI `log_errors=0`；`wp-content/debug.log`（594 B）是**过期 CLI 残留**（来自另一目录的 `t23_diag.php`）。真实 Web 日志是 **`~/Local Sites/sinofresh/logs/php/error.log`** |
| 10 | 发现 **1 处必须修正的 2A.5 参数语义**（`form` 默认值的取法）与 **4 项新风险**（见 §7） |

---

## 1. `functions.php` 结构地图（行号）

文件 2534 行 / 106,973 B / sha256 `65038aa0…860d4c`（源码 == Local ✓）

### 1.1 顶层声明骨架（节选，按行号）

| 行 | 内容 | 2A 相关性 |
|---|---|---|
| 5 / 10 | `require inc/config-pdf.php` / `inc/cert-download.php` | — |
| 12 | `add_action('after_setup_theme')` — `wp-block-styles` / `editor-styles` / `custom-logo` | — |
| **25** | `add_action('wp_enqueue_scripts')` — 全站句柄 | **版本号句柄位置** |
| 48 | `add_editor_style('style.css')` | — |
| 55 | `wp_head` prio **1** — `:has()` 能力探针 | — |
| **65** | `filter pre_get_block_template` — **模板权威守卫（单数）** | 2B 建 `single-sf_formula.html` 自动生效 |
| **102** | `filter get_block_templates` — **模板权威守卫（复数）** | 同上，防 DB 副本遮蔽 |
| 131 | `wp_enqueue_scripts` — front-page `interactions.js` 1.2.0 | — |
| 143 | `wp_enqueue_scripts` — about `about.js` 1.3.0 | — |
| 157 | `wp_enqueue_scripts` — quality `quality.js` 1.1.0 | — |
| 171 | `wp_enqueue_scripts` — quality `cert-modal.js` 1.2.0 | — |
| **177–188** | `wp_enqueue_scripts` — 8 剂型页：`configurator.css` **2.9** / `configurator.js` **2.2** / `formulas.js` **1.0.0** | **2A 不改**（见 §7 R5） |
| **204–230** | `sinofresh_explore_chips()` + `add_shortcode('sf_explore_chips', …)` | **shortcode 先例 ①** |
| **238–243** | `add_shortcode('sf_archive_count', closure)` | **先例 ②** |
| **265–306** | `sinofresh_blog_chips()` + `add_shortcode('sf_blog_chips', …)` | **先例 ③** |
| 317 | `register_block_pattern_category('sinofresh-patterns')` | — |
| 322–1154 | `register_block_pattern(...)` × 10 | — |
| 1155 / 1180 / 1257 | `render_block_data` / `query_loop_block_query_vars` / `render_block` | — |
| 1298 | `wp_head` prio **20** — **FAQPage** JSON-LD（`is_front_page()` / `is_page()`；CPT 直接 return） | 无 CPT 影响 ✓ |
| **1403** | **`sinofresh_template_placeholders()`** — 占位符引擎 | **2A.6 编辑点 ①** |
| 1446 | `filter render_block` — 占位符应用（仅 `core/html` 含 `{{`） | — |
| **1457–1538** | `wp_head` prio **21** — **BreadcrumbList** JSON-LD | **2A.7 编辑点** |
| 1541 | `wp_head` prio 2 — favicon | — |
| 1558–1600 | `sf_social_networks()` / `sf_site_settings_defaults()` / `sf_default_certifications()` | — |
| 1602 / 1614 / 1652 | Settings API 后台页（`admin_menu` / `admin_init` / render） | 后台先例 |
| 1737 | `sf_render_cert_badges()` | — |
| 1757 / 1848 | `render_block` 证书/社交替换 | — |
| 1880 | `wp_head` — Organization JSON-LD（`!is_page()` → CPT 直接 return） | 无 CPT 影响 ✓ |
| 2055 | **`sinofresh_reviewed_iso($post_id)`** — 读 `sf_last_reviewed` | meta 先例（见 §2.2） |
| 2063–2128 | `wp_head` prio **23** — Article JSON-LD（`!is_singular('post')` → CPT 直接 return） | 无 CPT 影响 ✓ |
| 2136 | `rest_api_init` — `/sinofresh/v1/article-feedback` | — |
| 2190 | `gform_submit_button_2` | — |
| **2203** | `filter rest_endpoints` — 仅摘除 `/wp/v2/users*`（登出态） | **不拦新 CPT 的 REST 路由** ✓ |
| 2216 / 2219 | `remove_action wp_generator` / `xmlrpc_enabled → false` | — |
| 2230 | `wp_head` — Service JSON-LD（`is_page('services')`） | — |
| 2273–2533 | Gravity Forms 证书发放 / 确认 / 提交钩子 | — |

### 1.2 版本号句柄全集（如需 bump 时查这里）

| 行 | 句柄 | 版本 |
|---|---|---|
| 26 | `sinofresh-style`（style.css） | **2.10.39** |
| 28 / 29 / 35 | `sinofresh-sticky-header` / `ui-components` / `quote-cta` | `1.0.0` ×3 |
| 31 / 33 | `sinofresh-mobile-nav` / `basket` | 1.1.0 / 1.3.0 |
| 41 / 44 | `sinofresh-toc-nav` / `hero-slider` | 2.0.0 / 1.1.1 |
| 133 / 145 / 159 / 173 | `interactions` / `about` / `quality` / `cert-modal` | 1.2.0 / 1.3.0 / 1.1.0 / 1.2.0 |
| **183 / 184 / 186** | `configurator`(css) / `configurator`(js) / **`formulas`(js)** | 2.9 / 2.2 / **1.0.0** |

> **2A 结论**：`functions.php` 自身无版本号；不引入新 CSS/JS ⇒ **不需要 bump**。与你的判断一致。

### 1.3 条件判定点全表（评估 CPT 副作用）

| 行 | 判定 | CPT 副作用 |
|---|---|---|
| 40 | `is_front_page() \|\| is_page([...12 个...]) \|\| is_singular('post')` → `toc-nav.js` | CPT 单条**不加载** toc-nav ✓（预期） |
| 181 | `$is_dosage_page` → 配置器三件套 | CPT **不加载** ✓ |
| 1181 | `!is_singular('post')` → related query vars | CPT 跳过 ✓ |
| 1308–1315 | FAQPage：`is_front_page()` / `is_page()` | CPT 提前 return ✓ |
| **1406** | `$post_id = is_singular('post') ? … : 0` | **2A.6 编辑点 ①** |
| 1415 | `$permalink = is_singular() ? get_permalink() : home_url('/')` | CPT 走 `get_permalink()` ✓ 正确 |
| 1426 | `is_archive()` → `{{ARCHIVE_TITLE}}` | `/formulas/` 归档 → `get_the_archive_title()` = `Formulas` ✓ |
| **1465** | BreadcrumbList `is_singular('post')` 分支 | **2A.7 编辑点**；CPT 落到 L1483 `else { return; }` ⇒ **不出面包屑 JSON-LD** |
| 1881 | `!is_page()` → Organization | CPT 提前 return ✓ |
| 2064 | `!is_singular('post')` → Article | CPT 提前 return ✓ |
| 2234 | `is_page('services')` | ✓ |

> **结论：只需在 1406 与 1465 两处加 CPT 分支**，无隐藏的第三处。

---

## 2. 现有 shortcode 与 meta 的写法样例

### 2.1 shortcode 先例（三种形态，可直接沿用约定）

**① `sf_explore_chips`（`functions.php:204–230`）—— 最贴近 2A.5 的模式**

```php
function sinofresh_explore_chips() {
    $pages = get_pages(array(
        'parent'      => 19,          // Products
        'post_status' => 'publish',
        'sort_column' => 'menu_order',
        'sort_order'  => 'ASC',
    ));
    if (!$pages) { return ''; }                      // ← 空数据返回空串（同 2A.5 的 empty=hide）
    $current_id = (int) get_queried_object_id();     // ← 当前页判定用 get_queried_object_id()
    …
    return '<nav class="sf-explore__chips" aria-label="Explore dosage forms">' . $chips . '</nav>';
}
add_shortcode('sf_explore_chips', 'sinofresh_explore_chips');
```

要点：**函数命名 `sinofresh_*` + 具名函数 + `add_shortcode` 紧随其后**；`sprintf` 拼 HTML；`esc_url` / `esc_html` 逐字段转义；**空数据返回 `''`**。

**② `sf_archive_count`（`238–243`）—— 闭包形态**，用于极短逻辑；`_n()` + `esc_html`。

**③ `sf_blog_chips`（`265–306`）—— 自撑容器先例**，且在 docblock 里明确写出**根因**：

> *"The container self-styles its flex layout: the old wp:buttons block relied on a per-instance generated hash class (`wp-container-core-buttons-is-layout-…`) that a **shortcode cannot reproduce**."*

这条注释是 2A.5「自撑容器 CSS」的**既有依据**，直接引用即可。

### 2.2 meta 先例 —— ⚠️ 与上一份扫描报告的表述需要纠正

| 说法 | 实测 |
|---|---|
| 上一份报告 §3 写「有 1 个原生 meta 先例 `sf_last_reviewed`」 | 该表述**容易被误读为"有 register_post_meta 写法可抄"** |
| 实测 | `register_post_meta` / `register_meta` / `add_meta_box` 在**主题与插件中均为 0 处**；`get_registered_meta_keys('post')` = **0 条** |
| `sf_last_reviewed` 的真实形态 | `functions.php:1410` 与 `:2056` 两次裸读 `get_post_meta($post_id,'sf_last_reviewed',true)`；`postmeta` 表有 **6 行**数据 → 由 WP 内置「自定义字段」面板写入 |
| 对 2A 的影响 | **没有任何现成 `register_post_meta` 模板可参照**；2A 的 4 个 meta 是主题首次。风险等级从「照抄」升为「首次引入，需自证」 |

### 2.3 内存注册预演的实际解析结果（`probe2` / `probe6`）

**post_type**

```
name=sf_formula  label=Formulas  public=true  publicly_queryable=true
exclude_from_search=false  show_ui=true  show_in_menu=true  show_in_rest=true
has_archive=true  hierarchical=false  query_var=sf_formula
menu_position=21  menu_icon=dashicons-clipboard
capability_type=post  map_meta_cap=true
supports=[title,editor,thumbnail,excerpt,revisions,page-attributes,custom-fields,autosave]
rewrite={slug:formulas, with_front:false, pages:true, feeds:true, ep_mask:1}   ← 后三项由 WP 补默认
REST base=sf_formula
```

**taxonomy（两个都解析为「无前台归档」✓）**

| 属性 | `sf_formula_form` | `sf_formula_use` | 判定 |
|---|---|---|---|
| `public` | false | false | ✓ |
| `publicly_queryable` | false | false | ✓ |
| `show_ui` / `show_in_menu` | true / true | true / true | ✓ 后台可管 |
| `show_in_nav_menus` | false | false | ✓ |
| `show_in_rest` | true | true | ✓ 块编辑器可管 |
| **`query_var`** | **false** | **false** | ✓ **WP 在 `public:false` 时自动置 false，无需显式声明** |
| **`rewrite`** | **false** | **false** | ✓ |
| `rest_base` | false | false | REST 路由回退为 `/wp/v2/sf_formula_form` |
| `object_type` | `["sf_formula"]` | `["sf_formula"]` | ✓ |

`extra_permastructs` 注册后 = `category, post_tag, post_format, language_switcher, sf_formula`
→ **taxonomy 未进 permastruct ⇒ 无 term 前台 URL，`public:false` 意图达成** ✓

**meta（4 条全部注册成功）**

```
sf_formula_ingredients  type=string  single=true  rest=true  auth=Closure
sf_formula_analysis     type=string  single=true  rest=true  auth=Closure
sf_formula_specs        type=string  single=true  rest=true  auth=Closure
sf_formula_source       type=string  single=true  rest=true  auth=Closure
auth 过滤器已挂：auth_post_meta_sf_formula_ingredients_for_sf_formula = true
```

**`auth_callback` 语义核对（WP 7.1.1 源码 `capabilities.php:477–518` + `meta.php:1511–1518`）**

1. `$allowed = ! is_protected_meta($meta_key, 'post')` → 4 个键均**无 `_` 前缀** ⇒ 默认 `true`。
2. 若 `auth_callback` **省略** → `meta.php:1516` 注册 `__return_true` ⇒ `$allowed` 仍为 `true`。
3. `$allowed === true` 的语义（官方注释原话）：*"Return true to have the mapped meta caps from `edit_{$object_type}` apply."* ⇒ **仍会走 `map_meta_cap('edit_post', $post_id)`**。
4. 你的 spec 写 `current_user_can('edit_posts')` ⇒ 返回 `true`（Contributor 起） ⇒ 同样落到 `edit_post` 映射能力。

> **结论：spec 的 `auth_callback` 与「省略不写」在实践中等价，既不弱于 WP 默认，也无安全退化。** 无需修改 spec（若要写到最紧，可换成 `current_user_can('edit_post', $post_id)`，但差别仅在 Subscriber 级用户上提前拒绝，而他们本来也被映射能力拒绝）。
>
> 附带核对：闭包声明 0 个形参而 WP 传 6 个 —— PHP 对用户定义函数的多余实参静默忽略，**不会报错** ✓

---

## 3. 8 个剂型页 slug 核对

**与扫描报告一致 ✓**（`probe2` E 段实测）

| slug | page ID | 父页 | 实际 URL |
|---|---|---|---|
| `soft-chews` | 20 | 19 | `/products/soft-chews/` |
| `tablets` | 21 | 19 | `/products/tablets/` |
| `powders` | 22 | 19 | `/products/powders/` |
| `pastes` | 23 | 19 | `/products/pastes/` |
| `drops` | 24 | 19 | `/products/drops/` |
| `liquids` | 25 | 19 | `/products/liquids/` |
| `fish-oil` | 26 | 19 | `/products/fish-oil/` |
| `dental-chews` | 27 | 19 | `/products/dental-chews/` |

- 父页 `products` = **ID 19**，published 子页 **8 个** ✓
- 全站页面 **22 个**（含 `privacy-policy`(3) `home`(11) `about`(14) `quality`(15) `factory-tour`(17) `contact`(28) `services`(29) `cooperation`(30) `blog`(31) `cookie-policy`(37) `terms`(38) `faq`(76) `feedback`(97)）
- **⚠️ 探测陷阱（已记录）**：`get_page_by_path('soft-chews')` 返回 `null` —— 因为它是**子页**，`get_page_by_path()` 必须传完整路径 `products/soft-chews`。第一版探针的「**缺失**」是假阴性，不是真缺陷。

**⚠️ 对 2A.6 的关键影响**：`{{FORM_HREF}}` 不能拼 `/{term_slug}/`，必须拼 **`/products/{term_slug}/`**。
**约定（必须写进代码注释）**：`sf_formula_form` 的 **term slug 必须等于剂型页 slug**，`{{FORM_CRUMB}}` 用 term name、`{{FORM_HREF}}` 用 `get_permalink(get_page_by_path('products/'.$slug))`（回落 `/products/{slug}/`）。

---

## 4. rewrite 现状与 flush 时机

### 4.1 现状（`probe1` / `probe2`）

```
permalink_structure          = '/%postname%/'
rewrite_rules 选项条目数      = 112   sha256=b814f789…031e
use_verbose_page_rules       = true
extra_permastructs（注册前）  = category, post_tag, post_format, language_switcher
额外规则（对基线 diff）       = 0 条真正自定义（14 条"非标准"实为 WP 默认的 sitemap/robots/日期/页面）
主题侧 add_rewrite_rule      = 0 处
插件侧 add_rewrite_rule      = 0 处（全插件目录 grep 无命中）
```

**⇒ 当前无任何自定义 rewrite 规则。** 唯一额外 permastruct `language_switcher` 来自 TranslatePress（`public=false` 的伪 CPT）。

### 4.2 注册预演：规则落位与路径解析（`probe2` C/D 段）

注册后生成规则 **112 → 135（+23）**，`option rewrite_rules` **仍为 112** ⇒ **预演未落盘 ✓**

CPT 规则落在 **#42–#64**，全部在 `extra_rules_top`（**先于 #116 页面兜底规则**）：

```
#42  formulas/?$                        → index.php?post_type=sf_formula          （归档）
#45  formulas/page/([0-9]{1,})/?$       → index.php?post_type=sf_formula&paged=$1  （归档分页）
#44  formulas/(feed|rdf|…)/?$           → index.php?post_type=sf_formula&feed=$1   （归档 feed）
#58  formulas/([^/]+)(?:/([0-9]+))?/?$  → index.php?sf_formula=$1&page=$2           （单条）
```

逐条 `preg_match` 预演结果：

| 路径 | 命中规则 | 解析 |
|---|---|---|
| `/formulas/liquid-joint-support/` | #58 | `sf_formula=liquid-joint-support` ✓ |
| `/formulas/` 、`/formulas` | #42 | `post_type=sf_formula` ✓ |
| `/formulas/page/2/` | #45 | `+paged=2` ✓ |
| `/formulas/feed/` | #44 | `+feed=feed` ✓ |
| `/products/soft-chews/` | #116 | `pagename=products/soft-chews` ✓ **未受影响** |
| `/products/`、`/blog/`、`/about/` | #116 | 未受影响 ✓ |
| `/category/manufacturing/` | #14 | 未受影响 ✓ |
| `/2019/01/01/` | #93 | 未受影响 ✓ |

### 4.3 `/zh/` 前缀（经验判定，非推断）

`trp_settings`：`url-slugs = {"en_US":"en","zh_CN":"zh"}`、`add-subdirectory-to-default-language = "no"`、`force-language-to-custom-links = "yes"`

实测 HTTP：

| URL | 状态 | `<html lang>` |
|---|---|---|
| `/about/` | 200 | `en-US` |
| **`/zh/about/`** | **200** | **`zh-CN`** |
| **`/zh/products/soft-chews/`** | **200** | **`zh-CN`** |
| `/formulas/` | 404 | —（CPT 未注册，预期） |
| `/zh/formulas/` | 404 | `zh-CN`（404 页也被翻译 ⇒ TP 层工作正常） |

**判定**：TP 的语言前缀剥离发生在 `parse_request` **之前**，且**与 post type 无关**（页面能过，CPT 就能过，因为剥离后的路径由同一套 rewrite 规则匹配）。**静态 preg_match 预演里 `/zh/formulas/…` 落到 #116 是假阴性**——它没模拟 TP 的请求阶段剥离。

**残留待验（执行步必做）**：`trp_post_type_base_slug_translation = []`、`wp_trp_slug_translations` **空表** ⇒ CPT base 不会被翻译，`/zh/formulas/<slug>/` 中的 `formulas` 保持英文。这是**可接受**的（不要求 zh 有独立 CPT base），但**执行步必须实测 `/zh/formulas/<slug>/` 返回 200**，不能只靠本节推断。

### 4.4 flush 触发时机 —— 你的方案需要一处修正

实测 `$wp_filter['after_switch_theme']`：

```
prio 10  _wp_menus_changed      wp-includes/nav-menu.php:1214
prio 10  _wp_sidebars_changed   wp-includes/widgets.php:1294
```

**⇒ 主题与插件均未挂钩 `after_switch_theme`，当前无人 flush rewrite。** `did_action('after_switch_theme')` = **0**（本次请求从未触发）。

由于主题已处于激活态且没有换主题计划，**「只在 theme activation 时 flush」这一条在本站永远不会执行** ⇒ CPT 规则永不写入 `rewrite_rules` 选项 ⇒ `/formulas/<slug>/` 永远 404。

**建议方案（取代纯 `after_switch_theme`）**：

```php
/* A. 保留 activation 钩子（未来换主题时自动生效，零成本） */
add_action('after_switch_theme', function () { flush_rewrite_rules(); });

/* B. 一次性守卫式 flush：仅在规则版本号不一致时执行一次
      —— 幂等、自愈（未来再加 CPT/taxonomy 只需改版本串）、非每次请求 */
add_action('init', function () {
    if (get_option('sinofresh_rewrite_version') !== '2A.1') {
        flush_rewrite_rules(false);      // false = 软刷新：只写 option，不动 .htaccess
        update_option('sinofresh_rewrite_version', '2A.1');
    }
}, 99);
```

- `flush_rewrite_rules(false)` 用**软刷新**：本站 Web 服务器是 **nginx**，`.htaccess` 本就不生效 ⇒ `true` 无意义且多余写盘。✅
- 必须挂 `init` **prio 99**（在 CPT/taxonomy 注册之后）。
- **DB 影响（须披露）**：写 `rewrite_rules`（112 → 135 条）+ 新建 `sinofresh_rewrite_version` 选项 1 条。这是 2A.8 自身的必要产物，不属于「迁移数据」。
- **回滚**：`delete_option('sinofresh_rewrite_version')` + `flush_rewrite_rules(false)`；或直接从 `_backup` 恢复 `functions.php` 后访问一次站点触发重算。

---

## 5. 2A 的改动面（精确到「影响 / 不影响」）

### 5.1 零影响（必须自证）

| 面 | 判定依据 |
|---|---|
| 现有 19 个页面 + 首页 + 博客 + 归档的 HTML | 2A 不改任何模板、不加任何 enqueue、短代码无调用方 ⇒ `render_block`/占位符/JSON-LD 输入不变 |
| `{{TITLE}}` 等 6 个现有占位符 | 新增 `{{FORM_CRUMB}}`/`{{FORM_HREF}}` 无冲突（实测两令牌**不存在**）；`is_singular('post')` 行为不变（只加 `\|\|`） |
| BreadcrumbList / FAQPage / Organization / Article / Service JSON-LD | CPT 各自 `return` 提前退出，现有页面判定未改（L1465 只**追加** elseif） |
| 3 个现有 shortcode | 不同名、不覆盖 `$shortcode_tags` |
| 12 个 enqueue 句柄版本 | 不 bump |
| `style.css` / `theme.json` | 不碰 |

### 5.2 非零影响（2A 的可见副作用，需在核验中接受）

| # | 影响 | 说明 |
|---|---|---|
| 1 | **后台出现 "Formulas" 菜单**（pos 21） | 核验项 1 的目标 |
| 2 | **`/formulas/` 归档上线** | 回退 **`archive.html`**（博客归档版式，含 `[sf_archive_count]` / `[sf_blog_chips]`）—— 2B 建 `archive-sf_formula.html` 前是「版式不对但 200」 |
| 3 | **`/formulas/<slug>/` 可访问** | 回退 **`single.html`**；面包屑显示 **`Home / Blog / <Formula>`**（`{{MID_CRUMB}}` 因 `$post_id=0` 回落 `Blog`），且带 `sf-article` 文章版式 —— 这是**已知且可接受**的过渡态（核验项 2 已预设） |
| 4 | `wp-sitemap.xml` 新增 `sf_formula` 条目 | WP 核心 sitemap provider 自动纳入公开 CPT |
| 5 | `rewrite_rules` 112 → 135 + `sinofresh_rewrite_version` 新 option | 4.4 的必要产物 |

### 5.3 模板回退链（`probe7` 权威裁决，非推断）

```
get_template_hierarchy('single-sf_formula')
  = single-sf_formula → single → singular → index
get_template_hierarchy('single-sf_formula-liquid-joint-support')
  = single-sf_formula-liquid-joint-support → single-sf_formula → single → singular → index
get_template_hierarchy('archive-sf_formula')
  = archive-sf_formula → archive → index

resolve_block_template('single',  ['single-sf_formula-{slug}.php','single-sf_formula.php','single.php'], '')
  → slug=single      source=theme   id=sinofresh-theme//single      ← 命中 single.html
resolve_block_template('archive', ['archive-sf_formula.php','archive.php'], '')
  → slug=archive     source=theme   id=sinofresh-theme//archive     ← 命中 archive.html
```

现有模板 26 个（`templates/*.html`），`single-sf_formula.html` / `archive-sf_formula.html` **均不存在** ✓（2A 不建）

**模板权威守卫（`functions.php:65` / `:102`）的作用**：2B 建出 `single-sf_formula.html` 后**自动生效**，且**不会被 DB 里的 `wp_template` 副本遮蔽** ⇒ 2B **无需**任何额外接线，也无需在 `theme.json` 的 `customTemplates` 注册。✅

### 5.4 你的核验项 6 需要换探测器

| | 现状 |
|---|---|
| `WP_DEBUG` / `WP_DEBUG_LOG` | `false` / `false` |
| CLI `php.ini` | `log_errors=0`、`display_errors=1`、`error_reporting=4983` |
| **PHP-FPM `php.ini`** | **`log_errors=On`、`display_errors=On`、`error_reporting=E_ALL & ~E_DEPRECATED`、`error_log="~/Local Sites/sinofresh/logs/php/error.log"`** |
| `wp-content/debug.log` | 594 B，mtime **2026-09-19 22:56**，内容为 `Call to undefined function wp_delete_option() in /Users/meng/Workbuddy/…/tools/t23_diag.php:44` → **CLI 残留，与 Web 无关** |

**⇒ 「debug.log 无新条目」恒成立，是假阴性探测器。**

**正确探测器（三选二即可）**：
1. **字节基线 + 追加段断言**：`~/Local Sites/sinofresh/logs/php/error.log` 基线 **69,385 B / mtime 2026-09-19 17:32**（尾 4096 B sha256 `9ddc8e6b…e8c8`）；改动后断言**体积不变**，且任何追加段不含 `sinofresh-theme/functions.php`。
2. **HTTP 正文扫描**：`display_errors=On` ⇒ 错误会打进行内。抓取页面后 grep `Fatal error|Warning:|Notice:|Deprecated:|Uncaught`。**带对照组**：同时扫一个未受影响页（如 `/about/`），证明扫描器能命中。
3. **CLI `E_ALL` 渲染**：用探针在 `error_reporting(E_ALL)` 下驱动渲染，捕获 `E_DEPRECATED`（FPM 配置把 DEPRECATED 排除了，CLI 能补上）。

---

## 6. 建议插入点（精确到行）

### 6.1 插入 A —— 新代码块（CPT + 2 taxonomy + 4 meta + shortcode + flush 守卫）

**位置：`functions.php` 第 306 行之后、第 308 行之前**（即 `add_shortcode('sf_blog_chips', …);` 与 `/** Article pattern library … */` 之间，现有第 307 行为空行）

```php
306: add_shortcode('sf_blog_chips', 'sinofresh_blog_chips');
307:
     ← ← ← 在这里插入新章节（约 +230～260 行）
308: /**
309:  * Article pattern library (block patterns).
```

**理由**
1. **与 3 个现有 shortcode 同区**：`sf_formula_grid` 落在 shortcode 注册带的末尾，后来者一眼能找到全部 shortcode。
2. **仍是纯新增**：不触碰 L204–306 任何一行，也不要求重排后面的 pattern 库（pattern 的行号会整体下移，但那是插入的必然结果，不是"改现有逻辑"）。
3. **在 pattern 库之前**：保持"数据源 / 短代码 → 内容模板（pattern）→ 渲染过滤器"的现有阅读顺序。
4. **若你更希望「新章节一律追加到文件末尾」**，也可放在 **L2533 之后**（GF 钩子之后）；功能完全等价 —— 差异仅是阅读顺序。二选一，我倾向前者。

**插入块内的建议顺序**

```
A1  docblock：批次 2A 说明 + 数据源约定（term slug == 剂型页 slug）
A2  add_action('init', 'sinofresh_register_formula_cpt', 9)      // 容器函数
A3  add_action('init', 'sinofresh_register_formula_taxonomies', 9)
A4  add_action('init', 'sinofresh_register_formula_meta', 9)
A5  add_action('after_switch_theme', fn() => flush_rewrite_rules())
A6  add_action('init', 'sinofresh_formula_rewrite_guard', 99)     // 一次性软刷新
A7  function sinofresh_formula_grid($atts) { … }                  // 2A.5
A8  add_shortcode('sf_formula_grid', 'sinofresh_formula_grid')
A9  辅助纯函数：sinofresh_formula_card_html($post) / sinofresh_formula_grid_data($posts) / sinofresh_formula_dosage_form_of($post_id)
```

> **优先级 9（而非默认 10）的理由**：让 CPT/taxonomy 在**任何** prio-10 的 `init` 消费者（含第三方）之前就绪；prio 9 < 99，flush 守卫仍在最后。

### 6.2 编辑 B —— 占位符引擎（2A.6）

| 位置 | 现状 | 改法 |
|---|---|---|
| **`1406`** | `$post_id = is_singular('post') ? (int) get_queried_object_id() : 0;` | `$post_id = (is_singular('post') \|\| is_singular('sf_formula')) ? (int) get_queried_object_id() : 0;` |
| **1433–1442**（`$map`） | 8 个令牌 | 尾部追加 `{{FORM_CRUMB}}` / `{{FORM_HREF}}` 两项 |
| **1432 之前** | — | 新增 3 行：取 `sf_formula_form` 主 term → `$form_slug`、`$form_name`；`$form_href = get_page_by_path('products/'.$form_slug)` 的 permalink，回落 `/products/{slug}/` |

**注意**：`$case` 的判定（`in_array('case-studies', $terms)`）在 CPT 下会因 `$terms` 从 `category` 取而无意义 → 追加 `is_singular('sf_formula')` 后，**必须同时确保 CPT 分支不污染 `$case`**（CPT 无 category → `$terms` 为空 → `$case=false` ✓，天然安全）。

### 6.3 编辑 C —— BreadcrumbList 模板候选（2A.7）

**位置：`functions.php:1465`**

```php
1465:  } elseif (is_singular('post')) {
1466:      $candidates = array('single');
         ← ← ← 在此之后追加：
         } elseif (is_singular('sf_formula')) {
             $candidates = array('single-sf_formula', 'single');
```

**为什么需要**：CPT 单条当前落到 **L1483 `else { return; }`** ⇒ 整块 BreadcrumbList 不输出（实测确认）。加分支后它会去读 `templates/single-sf_formula.html` 里的 `.sf-breadcrumb`。**该文件在 2A 尚未存在** ⇒ 内层 `if (!$file) return;`（L1492）会安全退出，**不报错、不输出**。⇒ **2A 加分支是「预置」而非「生效」**，零风险；2B 建模板后自动开始输出。✅

`$candidates` 里带 `'single'` 作兜底，是为了 2B 之前的过渡期也能生成面包屑（虽然过渡期面包屑内容是错的——但那是既有过渡态，不是 2A 引入）。

### 6.4 2A **不**改（明确列出，避免执行步顺手扩范围）

| 项 | 原因 |
|---|---|
| L177–188 的 enqueue 条件 | 2A 无任何模板调用 shortcode；详情页是否需 `formulas.js` 属 **2B** |
| `style.css` 任何行 | 约束「不改 CSS」；`.sf-fgrid` 样式属 **2C** |
| `templates/*.html` 任何文件 | 约束「不改模板」 |
| 3 个现有 shortcode 的实现 | 约束「不改现有逻辑」 |
| `theme.json` | 块主题**不需要**在其中注册 CPT 模板 |

---

## 7. 风险提示

### 7.1 必须处理（3 项）

**R1 · `form` 参数的默认值取法 —— 你的 spec 需要一处修正**

spec 写 `form（默认当前页 slug）`。若按 URL 末段取：`/products/soft-chews/` → `soft-chews` ✓；但 `/zh/products/soft-chews/` → 末段仍是 `soft-chews` ✓（zh 在**首段**）。**URL 末段法在两个语言下都正确**，但它对「页面被改到别的父级」或「同一短代码用在非剂型页」会静默取到错误 slug。

**建议**（仅加固，不改变语义）：

```php
if ($atts['form'] === '') {
    $qo = get_queried_object();
    $atts['form'] = ($qo instanceof WP_Post && $qo->post_type === 'page')
        ? $qo->post_name                       // 权威来源
        : basename(untrailingslashit(wp_parse_url($_SERVER['REQUEST_URI'] ?? '', PHP_URL_PATH)));  // 回落
}
```

**R2 · 页数为 0 时 shortcode 的行为**
`empty（默认 hide）` ⇒ 无匹配时返回 `''`。但要注意：**回落分支必须与 `empty` 开关耦合**——若 `empty=notice`，应输出一条提示而不是空串。spec 只定义了 `hide`，2A 建议**只实现 `hide`**，把 `notice` 留给 2B 再定（避免实现一个无人验证的分支）。

**R3 · `<script>` 内的 `</script>` 注入面（现在无害，必须预置护栏）**

`wp_json_encode()` 在 house style 下带 `JSON_UNESCAPED_SLASHES` ⇒ `/` 不被转义 ⇒ 若某条标题含 `</script>`，**两个 JSON 块都会被提前闭合**。

- **2A 风险 = 0**（CPT 里 0 条数据，shortcode 无调用方）
- **但必须现在就定护栏**，否则 2B 迁移 21 条真实数据后才会暴露。建议：

```php
$json = wp_json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
$json = preg_replace('#</(?=script)#i', '<\\/', $json);   // 仅闭合序列，不改其他斜杠
```

并加**断言**：`assert(strpos($json, '</script') === false)`。

### 7.2 需注意（4 项）

**R4 · K1 的 `formulas.js` 只在 8 剂型页 enqueue**
`.sf-formula__cta` 的点击处理在 `assets/js/formulas.js`（L67 `querySelectorAll('.sf-formula__cta')`），而该脚本**仅**在 `$is_dosage_page` 时加载（L182–187）。
⇒ 若 2B/2C 把 `[sf_formula_grid]` 放到**非剂型页**（例如某个总览页或详情页自身），CTA 会**静默无响应**（不报错、无视觉异常）。2A 不触发（无调用方），但**2B 换模板时必须同时决定是否放宽 enqueue 条件**。

**R5 · `formulas.js` / `configurator.js` 的 sessionStorage 键在详情页会算错**（已实测）

```js
// formulas.js:74-78
var segments = window.location.pathname.replace(/\/+$/, '').split('/');
var slug = (segments[segments.length - 1] || '').toLowerCase();
sessionStorage.setItem('sinofresh_formula_' + slug, name);

// configurator.js:21-32 currentSlug()：同样取末段，仅额外排除 'products'
```

| 页面 | 末段 | 键 | 判定 |
|---|---|---|---|
| `/products/soft-chews/` | `soft-chews` | `sinofresh_formula_soft-chews` | ✓ |
| `/zh/products/soft-chews/` | `soft-chews` | 同上 | ✓ |
| **`/formulas/liquid-joint-support/`** | `liquid-joint-support` | **`sinofresh_formula_liquid-joint-support`** | **✗ 多了一个无意义的键** |
| **`/zh/formulas/liquid-joint-support/`** | `liquid-joint-support` | 同上 | **✗** |

当前**无实际危害**：`formulas.js` 在详情页未加载；`configurator.js` 在 L15–18 因找不到 `.configurator` 根节点直接 `return`。**但若将来在详情页放配置器或公式卡，两个脚本都会算错页键。** 不改，仅登记。

**R6 · K2 的 JSON 匹配口径必须与现有语义**「按配方名精确匹配」**一致**

`configurator.js:637-651` 现按 **name 精确匹配**（`nameEl.textContent.replace(/\s+/g,' ').trim() === name`）。`.sf-formulas-data` JSON 的 `name` 字段必须与之逐字一致，而 `name` 又来自 sessionStorage（由 `formulas.js` 写 `data-formula` 的原值）。

⇒ **唯一权威字符串**必须是：

```php
$name = html_entity_decode(get_the_title($post), ENT_QUOTES, 'UTF-8');
```

同一变量同时用于：`data-formula="' . esc_attr($name) . '"`、JSON 的 `name`、卡片 `<h3>` 文本。**三处同源**，否则 2B 会出现「名字对不上 → 三字段静默丢空」——正是 Phase B 扫描报告 §8.2 记录的那类回归。

**R7 · K4 的实体泄漏修复必须带回溯断言**

Phase B 扫描报告 §4.3 记录了模板硬编码 ItemList 的 **3/21 条实体泄漏**（`Skin &amp; Coat Soft Chews` / `Calcium &amp; Phosphorus Tablets` / `Liquid Skin & Coat`）。2A 的 shortcode 用 `wp_json_encode()` 天然输出裸 `&` ⇒ 修复是**自然结果**。
**但必须加断言**：生成后 `assert(strpos($json,'&amp;') === false && strpos($json,'&') !== false 当存在 & 数据时)`。否则未来有人把 `esc_html()` 套在编码前，泄漏会悄悄回来。

### 7.3 可接受（2 项，需在核验报告中显式承认）

**A1 · 过渡期 `/formulas/` 用博客归档版式**（§5.2 #2）。若你希望 2A 期间 `/formulas/` 直接 404，唯一办法是 2A 先设 `has_archive => false`、2B 建好 `archive-sf_formula.html` 再翻成 `true`。**但这与已确认 spec 冲突**，且 Local 环境无对公暴露，我建议**保持 spec**。

**A2 · 过渡期 `/formulas/<slug>/` 面包屑显示 `Home / Blog / <Formula>`**（`{{MID_CRUMB}}` 回落 `Blog`）。已在 R1 的 2A.6 编辑点里预留了 CPT 分支，但**只有当 `templates/single-sf_formula.html` 用了 `{{FORM_CRUMB}}` 才生效** —— 而 `single.html` 用的是 `{{MID_CRUMB}}`，2A 不改模板 ⇒ 过渡期必然错。2B 建模板即解决。

### 7.4 已排除的伪风险（避免执行步做多余改动）

| 曾疑似的问题 | 实测结论 |
|---|---|
| `rest_endpoints` 过滤器（L2203）会拦新 CPT 的 REST 路由 | **不会** —— 它只摘 `/wp/v2/users*`（且仅登出态） |
| `register_taxonomy` 需要显式 `query_var => false` | **不需要** —— `public:false` 时 WP 自动置 `false`（实测） |
| spec 的 `auth_callback` 比 WP 默认宽松 | **不是** —— 与省略等价，且 `$allowed=true` 仍走 `edit_post` 映射能力（源码核对） |
| `menu_position = 21` 与其他菜单冲突 | **不冲突** —— 实测 17–24 全空（Pages=20，Comments=25） |
| 短代码输出拿不到 `wp-container-core-*` 布局类 → 卡片会塌 | 根因**成立**（`block-template.php:262` `do_shortcode` 先于 `do_blocks`），但 **2A 不加 CSS、无调用方 ⇒ 零影响**；自撑容器在 2C 落地 |
| `wptexturize()` 会把 JSON 里的引号/`&` 变体 | **不会** —— `<script>` 在 `wptexturize` 的 `$no_texturize_tags` 白名单内 |
| `get_page_by_path('soft-chews')` 返回 null ⇒ slug 有问题 | **假阴性** —— 子页须传 `products/soft-chews`，8 个 slug 全部正确 |
| 静态预演中 `/zh/formulas/…` 未命中 CPT 规则 | **假阴性** —— 未模拟 TP 的请求阶段剥离；HTTP 实测证明 `/zh/` 前缀机制与 post type 无关 |

---

## 8. 与上一份扫描报告的差异（需并入基线）

| 项 | 上一份报告 | 本次实测 | 处置 |
|---|---|---|---|
| `sf_last_reviewed` 的描述 | 「有 1 个原生 meta 先例」 | **无任何 `register_post_meta` 可参考**；仅裸 `get_post_meta` | **纠正措辞**，2A 首次引入 |
| 详情页模板回退链 | `single-sf_formula-{slug}` → `single-sf_formula` → `single` → `singular` → `index` | **一致**（`probe7` 用正确调用确认） | 无需改 |
| 「核验项：debug.log 无新条目」 | 隐含可作为探测器 | **无效**（`WP_DEBUG_LOG=false`；`debug.log` 是 CLI 残留） | **换成 `logs/php/error.log` 基线** |
| `after_switch_theme` flush | 「activate_theme？」 | **全站无人 flush**；`after_switch_theme` 只有 WP 核心两个回调 | **必须加守卫式一次性 flush** |
| `/zh/` CPT 可达性 | 「新 CPT slug 要本地化需注册」 | TP 前缀剥离与 post type 无关 ⇒ **`/zh/formulas/<slug>/` 会工作**；base slug 保持英文 | 执行步实测确认 |
| 剂型页 URL | 未明写 `/products/` 前缀的影响 | `{{FORM_HREF}}` **必须**用 `/products/{slug}/` | **写入代码注释** |

---

## 9. 工具与证据索引

| 工具 | 用途 | 关键产出 |
|---|---|---|
| `tools/_cpt2a_probe.php` | 注册面 / rewrite / 页面 / 环境 / 日志现状 | `sf_formula` 不存在；`register_*` 全 0；112 条规则；22 页 |
| `tools/_cpt2a_probe2.php` | **内存注册预演** + 规则落位 + 路径解析 + slug 冲突 | 规则 #42–#64；`/formulas/<slug>/` → #58 ✓；**未落盘**（仍 112） |
| `tools/_cpt2a_probe3.php` | TP 设置 + 菜单静态扫描 + 日志位置 + 模板行号 | `url-slugs={en,zh}`；真实日志 = `logs/php/error.log` |
| `tools/_cpt2a_probe4.php` | TP 完整设置面 + **文件/日志/rewrite 基线** | `functions.php` sha256、日志 69,385 B、8 页 200 |
| `tools/_cpt2a_probe5.php` / `5b.php` | 后台菜单**动态**占位 | pos 21 可用；17–24 全空 |
| `tools/_cpt2a_probe6.php` | 注册后**实际属性**解析 + meta auth 语义 | taxonomy `query_var=false`；meta 4/4 挂 auth |
| `tools/_cpt2a_probe7.php` | **模板回退链权威裁决** | `resolve_block_template` → `single` / `archive` |

**基线快照（执行步改动前须复核）**

| 对象 | 基线 |
|---|---|
| `functions.php` | 106,973 B / sha256 `65038aa0fb7a231eae7d896972db19e32062bd7e874cc497350be4abe860d4c` |
| `style.css` | 237,655 B / sha256 `6a9261ee4b53b3eb5436ff05294fa86bf21c680a3fe9d638fe00da32b323befa` |
| `theme.json` | 6,523 B / sha256 `88b7cd8d00c40afed25712fe38b910e01274c59c5977a524cb12a27fc60e1657` |
| 源码 == Local | 三者**全部为「是」**（sha256 逐字节一致） |
| `rewrite_rules` 选项 | 112 条 / sha256 `b814f789dd2eb49da6498e5f4ea30a912a3462ee355e3959013a2876d241031e` |
| `logs/php/error.log` | 69,385 B / mtime 2026-09-19 17:32 CST / 尾 4096 B sha256 `9ddc8e6ba16742542900d068c564c10b0ca8cd114c0df91b36e2efd0dbf3e8c8` |
| 8 剂型页 + 首页 + 博客 | 全部 **HTTP 200**（改动前基线） |

**本次扫描未改动任何源码、未写 DB。**
（`docs/`、`tools/` 为非部署目录 —— `diff -rq` 显示它们 `Only in` 源码侧，不在站点根）

---

## 10. 待你确认（3 项）

| # | 问题 | 我的建议 |
|---|---|---|
| **Q1** | 插入点：`L306` 之后（与现有 3 个 shortcode 同区）还是 `L2533` 之后（文件末尾）？ | **L306 之后** —— 全部 shortcode 集中一处，后来者一眼可寻 |
| **Q2** | `{{FORM_HREF}}` 的容错：剂型 term 缺失时输出 `/products/` 还是**整条面包屑不渲染**？ | **输出 `/products/`** —— 与 `sf_explore_chips` 的「空则返回 `''`」不同：面包屑缺一级比整条消失更好；且 term 缺失属数据异常，2B 迁移时会加断言兜住 |
| **Q3** | `sf_formula_source` 这个 meta 的语义？spec 只给了 key 名（另 3 个对应 Ingredients / Guaranteed Analysis / Standard Specs） | 我按字面理解为**「数据来源标注」**（例如 `Migrated from page-soft-chews.html §formulas`），`type=string`、`single=true`，仅后台可见不前台渲染。若你要的是「原料供应商」之类别的语义，请指定 |

---

**扫描完成。等你确认后进入第二步执行。**
