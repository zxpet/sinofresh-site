# 批次 2D · 第 1 批 实施方案（实施前扫描 + 待确认）

> 状态：**方案，未落任何改动**。`sinofresh-theme/ git status` 为空，云端仍 `c0308af`，8 页块配平 lint 全 PASS。
> 三个决策点已拍板：`<dt>/<dd>` + `.sf-spec-list`／成分药丸行／导语由 shortcode 生成。
> 本文件只覆盖**预实施扫描结论**与**可逐项核对的实施内容**；写完停下等确认。

---

## 0. 预实施扫描（只读，零写入）

| # | 核查项 | 实测结果 |
|---|---|---|
| 1 | 工作区 / 主题 git | 主题目录**零改动**；HEAD `c0308af`；新增未跟踪文件只有 `docs/b2d-step0-shots/`、`docs/batch2d-step0-scan.md`、`tools/b2d_s0_scan.py` |
| 2 | 8 页块配平基线 | `b2c_s2_block_lint.py` **8/8 PASS**（"block delimiters and HTML tags balanced, no malformed self-close"） |
| 3 | **插入锚点唯一性** | 锚点 `</table>\n<!-- /wp:html -->\n</section>\n<!-- /wp:group -->\n\n` 在 8 页**各命中 1 次**，sha256(前 16) = `e2c5d61e6997f0d3`，**8 页完全同字节**；其后紧跟 `<!-- Block 9: How We Work -->` |
| 4 | `</table>` 总数 | 8 页各 **1 个** ⇒ 锚点无歧义；`Block 9: How We Work` 注释各 1 处 |
| 5 | 渲染后 section 序列 | `sf-hero-inner` → `#formulas.sf-formulas` → `#configurator` → `.sf-spectable` → (How We Work) → (FAQ) → (Related) → `#inquiry-form`，共 8 个顶层 `<section>`；新块插在第 4、5 个之间 |
| 6 | 页面 H2 | 8 页各 **6 个**；顺序 `Standard Formulas / Build Your … Formula / How We Work / Frequently Asked Questions / Related Dosage Forms / Request a … Quote`。新 H2 → **第 3 个**，点轨 6 → 7 |
| 7 | `toc-nav.js` 关联 | 剂型页**在入队清单内**（`functions.php:40`）。`SKIP` 正则 = `formulated clean` / `from inquiry to after-sales` / `trusted by 30+` / `ready to launch your product?` → **不含**新标题 ⇒ 会成为第 7 个点。页面**没有 `<main>`** ⇒ 脚本回落 `document.body`，但 header/footer 内无 H2，故计数恰好是 6 |
| 8 | `#sf-sec-N` 依赖 | 全仓 **无任何硬编码 `#sf-sec-` 引用**（`grep` 于 `templates/ assets/ functions.php`）⇒ 序号后移只影响运行时点轨顺序，无深链断裂 |
| 9 | **K6 Product JSON-LD** | `functions.php:2773/2784` 的 `wp_head` 回调 **`file_get_contents` 读磁盘模板**（不是渲染结果），`additionalProperty` 正则写的是 `<span class="sf-spec-term">…</span><span class="sf-spec-value">…</span>`（两 span 之间零空白）⇒ **双重安全**：① 读的是文件，文件里不出现 `sf-spec-*`；② 即便读渲染结果，`<dt>` 也不匹配 |
| 10 | JS 侧数据抽取锚点 | `assets/js/*.js` 全部 `querySelectorAll` 已盘点：**无任何脚本消费 `.sf-spec-*`**（`grep -rn "sf-spec" assets/js/ inc/` 空）。`interactions.js`（唯一会扫 `.wp-site-blocks > .wp-block-group` 的脚本）只 `is_front_page()` 入队；`formula-filter.js` 只认 `.sf-fgrid .sf-fcard[data-sf-form]`；`configurator.js` 只认 `.configurator__*` / `script.sf-formulas-data` / `.sf-formula__*`。⇒ 本批新增结构不在任何选择器射程内 |
| 11 | 容器类副作用 | 新块用 `layout:{"type":"constrained"}`。实测：**constrained 组不产生 `wp-container-core-*` 类**（只有 flex 组才产生），页内 `core-block-supports-inline-css` 仅 809 B / 11 条规则且都是 flex 组 ⇒ **预期该 style 块字节不变**（回归项 5 会验） |
| 12 | 版本号出现处 | `grep 2.10.44` 全主题**仅 2 处**：`functions.php:26`（enqueue）、`style.css:5`（头部 `Version:`）。无第三处读取 |
| 13 | 调色板 / 间距 token | `text-primary #1C2B24`／`text-secondary #5F6B65`／`bg-light #F3F6F4`／`card-white #FFFFFF`／`border-light #DCE2DF`；`spacing--80 = 48px`（与块④/⑤ 同值；`60` 也是 48px） |
| 14 | 药丸圆角惯例 | `border-radius: 999px` 全站 **8 处**已在用（含 `.sf-topbar-badges` 的 certificate pill：`padding:1px 8px` + `1px solid border-light` + `999px`）。⇒ 本批沿用 **outline pill**（border-light + 999px），不发明新的填充色块词汇 |
| 15 | `dl/dt/dd` 全局样式 | `theme.json` 的 `styles.elements` 只有 `heading/h1..h4/link/button`，**无 `dl/dt/dd`**；`style.css` 也**无** `dl/dt/dd` 规则 ⇒ UA 默认值必须自己归零（见 §2.3） |
| 16 | 自闭合块纪律 | 8 页现有自闭合块各 3 个，全部形如 ` /-->`；`grep '/ -->'` **8 页全 0**。本批新增的 `wp:group` 是容器块，**不产生自闭合**，纪律不受影响 |

### 0.1 干跑：解析器在 21 条真实数据上的行为（已跑，工具已落盘）

新增工具 **`tools/b2d1_parser_dryrun.php`**（自包含固件 + 对抗性探针，任意机器可重跑）。
固件已用**逐字节**方式对过数据库导出：**21/21 配方 × 3 字段全等**。

```
== 1. split_top_level vs 朴素 ', ' 切分 ==         differing rows: 0/21
== 2. 畸形 analysis 段 ==                          without ≥: 0   多于一个 ≥: 0
== 3. 某一侧为空的 pair ==                          bad pairs: 0
== 4. 每页预期渲染计数（回归判据）==
  form           items  pills  analysis rows
  soft-chews     4      24     8
  tablets        3      18     7
  powders        3      10     3
  pastes         2      9      4
  drops          2      6      2
  liquids        2      11     6
  fish-oil       2      6      8
  dental-chews   3      15     5
  TOTAL pills=99  analysis_rows=43
```
对抗性探针（13 例）全部不抛异常；只有「有水平无分析项」（`≥5%`）会丢弃该行，其余返回 `value=''` 的无害行 —— 真实数据里不可达（第 2 节 0 例畸形）。

---

## 1. ⚠ 必须先更正：上一批扫描里的一条误报（我自己的转录错误）

第 0 批扫描文档 `docs/batch2d-step0-scan.md` §7.2 与 `RULES-sinofresh.md` §6 都写着：

> 成分串有一条数据缺陷：`Hairball Remedy Paste` = `Malt Extract (43%), Oils and Fats (30%), Chicken Meal (4%, Yeast, Minerals` —— **少一个右括号**。

**实测推翻（本轮 HEX 取证）**：

```
HEX 尾部 = ...436869636B656E204D65616C20283425292C2059656173742C204D696E6572616C73
解码     = "Chicken Meal (4%), Yeast, Minerals"        ← 右括号在
LENGTH   = 75       post_modified_gmt = 2026-09-20 06:28:47（**早于当天扫描**）
```
- 75 字节 = **配平版**长度；缺括号版是 74 字节。
- `post_modified_gmt` 06:28:47 早于扫描时刻 ⇒ **数据没被改过**，是**我在上一轮把这条字符串抄漏了一个 `)`**。
- 该文档自己的表格里 `Hairball / Nutrition = 75 / 65` 用的正是 SQL 的 `LENGTH()` ⇒ 扫描时库里就已经是 75。

**由此连带失效的论据**：上一轮据此写下的「**解析器必须做括号配平**」。干跑实测 **21/21 条与朴素 `', '` 切分结果完全相同**；`grep` 全量数据 **没有任何一条成分串的括号内含逗号**（`Natural Cleaning Dental Sticks` 的 `Tapioca (46%), Peas (29%)…` 逗号都在括号**外**，朴素切分本就正确）。

**同步动作**（本轮已做，属更正历史归档，非实施改动）：
- 改 `docs/batch2d-step0-scan.md` §7.2 与「三点如实说明」中的对应条目；
- 改 `RULES-sinofresh.md` §6 的同一条；
- 把「**文档必须先对 HEX 再引用数据**」写进教训。

**留给你的一个小决策**（见 §5 Q1）：括号配平函数保留还是删掉。

---

## 2. 实施内容（逐字节可核对）

### 2.1 `functions.php` — 新增 2 个纯函数 + 1 个 shortcode

**插入点**：第 918 行 `add_shortcode('sf_formula_grid', 'sinofresh_formula_grid');` **之后**、`[sf_formula_filters]` 的 docblock **之前**（即紧接同侪公式短代码，不插在文件其它位置）。

```php
/**
 * Split a "a, b, c" meta value on its top-level commas.
 *
 * The comma is the separator the 21 records use (sf_formula_ingredients), and
 * it can also legitimately appear INSIDE a parenthesised share — "Tapioca
 * (46%), Peas (29%)" separates at depth 0 only. Today every one of the 21
 * values splits identically either way (tools/b2d1_parser_dryrun.php §1), so
 * this is defensive, not load-bearing: it costs a depth counter and removes a
 * silent wrong-split if content ever writes "X (a, b), Y".
 *
 * Byte-wise on purpose: "(" ")" "," are ASCII and UTF-8 continuation bytes
 * are all >= 0x80, so multi-byte terms pass through untouched.
 */
function sinofresh_formula_split_top_level($value) { … }

/**
 * Turn "Glucosamine ≥500mg/chew, Chondroitin ≥200mg/chew" into term/value
 * pairs for the guaranteed-analysis table.
 *
 * Splits on the FIRST ≥ of a segment: the level half keeps any further text
 * verbatim ("Omega-3 ≥30%" → term "Omega-3", value "≥30%"). A segment with no
 * ≥ returns a term with an empty value — the caller decides what to do with it
 * — and a segment with an empty term is dropped, because a value with no
 * subject is not a row.
 */
function sinofresh_formula_analysis_pairs($value) { … }

/**
 * [sf_formula_actives] — the "Active Ingredients & Guaranteed Analysis" band
 * on the eight dosage pages.
 *
 * Reads the same post meta [sf_formula_detail] reads (sf_formula_ingredients,
 * sf_formula_analysis), so the formula record stays the single source of
 * truth, and it stays editable in wp-admin (the template files are behind the
 * authority guard; post meta is not).
 *
 * Server-side by necessity: the K2 JSON mirror is a [sf_formula_grid]
 * by-product, so reading it would require keeping the grid on the page, would
 * paint nothing without JavaScript, and would leave this band coupled to the
 * grid. A shortcode that queries the records directly is crawlable, degrades
 * to plain HTML, and cannot be disturbed by editing the cards.
 *
 * Emits no JSON and no ItemList of its own: the page already carries the
 * grid's ItemList and the dosage Product schema, and a second copy would only
 * duplicate them. Returns '' when the dosage form has no published formula,
 * so the band collapses instead of leaving an empty padded section — the same
 * convention as sf_formula_body.
 *
 * Labels are plain English literals, not gettext: that is how the eight
 * templates' own copy is written (and how [sf_formula_grid] writes
 * "View formula →"), so these strings land on the same TranslatePress path as
 * the rest of the page. No TP strings are registered in this batch.
 */
function sinofresh_formula_actives($atts = array()) { … }
add_shortcode('sf_formula_actives', 'sinofresh_formula_actives');
```

**查询参数**（与 `[sf_formula_grid]` 严格同形，保证卡序与表格行序一致）：

```php
'post_type' => 'sf_formula', 'post_status' => 'publish', 'posts_per_page' => -1,
'orderby' => array('menu_order' => 'ASC', 'title' => 'ASC'),
'ignore_sticky_posts' => true, 'no_found_rows' => true,
'tax_query' => array(array('taxonomy' => 'sf_formula_form', 'field' => 'slug', 'terms' => $form)),
```
`$form = sinofresh_formula_current_form($atts['form'])`（复用现有解析，`form` 缺省时自动落当前页 slug）。

**渲染出的 DOM**（由 shortcode 产出，模板里只有 1 行短代码）：

```html
<div class="sf-actives__inner">
  <h2 class="sf-actives__title">Active Ingredients &amp; Guaranteed Analysis</h2>
  <p class="sf-actives__intro">Every Soft Chews recipe in our standard range, with the
     ingredient list and the guaranteed analysis we hold to in production. Use one as a
     starting point, or ask us to adjust the actives and the levels for your own label.</p>
  <div class="sf-actives__list">
    <article class="sf-actives__item">
      <h3 class="sf-actives__name">Joint Support Soft Chews</h3>
      <p class="sf-actives__label">Ingredients</p>
      <ul class="sf-actives__ing">
        <li class="sf-actives__pill">Glucosamine HCl</li> …
      </ul>
      <p class="sf-actives__label">Guaranteed Analysis</p>
      <dl class="sf-spec-list">
        <div class="sf-spec-row">
          <dt class="sf-spec-term">Glucosamine</dt>
          <dd class="sf-spec-value">≥500mg/chew</dd>
        </div> …
      </dl>
    </article> …
  </div>
</div>
```

要点：
- 名字取 `html_entity_decode(get_the_title())` 后 `esc_html()`（`Skin & Coat Soft Chews` 等含 `&`，与 grid 同一套单一权威写法）；
- 所有插值一律 `esc_html()`（输出落在 `core/html` 内，`render_block` / `wptexturize` 仍会作用）；
- H2 文本里 `&` 走 `esc_html()` → `&amp;`；
- 导语按 `sinofresh_formula_label($form)` 拼，8 页自动不同；
- `dl > div > (dt, dd)` 是 HTML 规范的合法内容模型（`dl` 允许 `div` 分组）；
- **不输出** K2 副本、**不输出** ItemList JSON-LD。

### 2.2 8 个模板 — 插入 8 行（+1 空行），逐字节相同

**插入锚点**（8 页同字节、各命中 1 次）：

```
</table>
<!-- /wp:html -->
</section>
<!-- /wp:group -->

```
→ 紧随其后写入下列 8 行 + 1 个空行，再接原有的 `<!-- Block 9: How We Work -->`：

```
<!-- B2D-S1: actives -->
<!-- wp:group {"tagName":"section","anchor":"actives","className":"sf-actives","layout":{"type":"constrained"},"style":{"spacing":{"padding":{"top":"var:preset|spacing|80","bottom":"var:preset|spacing|80"}}}} -->
<section id="actives" class="wp-block-group sf-actives" style="padding-top:var(--wp--preset--spacing--80);padding-bottom:var(--wp--preset--spacing--80)">
<!-- wp:html -->
[sf_formula_actives form="soft-chews"]
<!-- /wp:html -->
</section>
<!-- /wp:group -->

```

- 唯一逐页差异：`form="…"` 的值（`soft-chews` / `tablets` / `powders` / `pastes` / `drops` / `liquids` / `fish-oil` / `dental-chews`）。
- 写法与块② `#formulas` **逐字对齐**（`anchor` + `className` + 同样的 padding 序列化）——这是主题里唯一被 Site Editor 反复保存过的容器写法，最稳。
- **无自闭合块**，故不涉及 ` /-->` 纪律。
- 注释写成短标记 `<!-- B2D-S1: actives -->`（**会输出到页面源码**，与既有 `<!-- Block 9 … -->` 同族），同时给回归归一化脚本一个稳定锚点。
- **不重排既有块注释编号**（现值 `2/4/9/10/11/12` 与实际 1/3/5/6/7/8 不符，属历史残留，重排只会制造大 diff）。
- **不碰**：块②配方卡、块③配置器、块⑤ How We Work 的 A/B 两种写法、块⑥⑦⑧。

### 2.3 `style.css` — 追加 1 段（**追加到文件末尾**，现 7908 行之后）

```css
/* B2D Step1 — Active Ingredients & Guaranteed Analysis band on the eight
   dosage pages. One recipe per block, hairline-separated: the band sits on
   the white section, so card chrome would not read. The guaranteed-analysis
   table is the compact .sf-spec-list grid defined above (section "Compact
   8-row spec list"), reused here with <dt>/<dd> — the correct semantics for a
   term/value pair, and structurally out of reach of the dosage-page Product
   JSON-LD parser, which matches <span class="sf-spec-term">…</span>
   <span class="sf-spec-value">…</span> on the template file. ------------- */
.sf-actives__title { margin: 0; }
.sf-actives__intro {
	max-width: 720px;
	margin-top: 10px;
	font-size: 15px;
	color: var(--wp--preset--color--text-secondary);
}
.sf-actives__list { margin-top: 30px; }
.sf-actives__item + .sf-actives__item {
	margin-top: 28px;
	padding-top: 28px;
	border-top: 1px solid var(--wp--preset--color--border-light);
}
.sf-actives__name { margin: 0; font-size: 17px; }
.sf-actives__label {
	margin: 16px 0 0;
	font-size: 11px;
	font-weight: 600;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--wp--preset--color--text-secondary);
}
/* Ingredient pills. Deliberately NOT .sf-fchip: that class carries
   cursor:pointer and a hover/.is-active state because it is a filter button —
   the wrong affordance on a static term. Outline pill mirrors the
   .sf-topbar-badges certificate pill, the site's existing pill vocabulary. */
.sf-actives__ing {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin: 10px 0 0;
	padding: 0;
	list-style: none;
}
.sf-actives__pill {
	padding: 3px 10px;
	border: 1px solid var(--wp--preset--color--border-light);
	border-radius: 999px;
	font-size: 13px;
	line-height: 1.5;
	color: var(--wp--preset--color--text-primary);
}
/* <dl> ships margin-block 1em and <dd> margin-inline-start 40px — the reused
   .sf-spec-list grid needs both neutralised inside this band. */
.sf-actives .sf-spec-list { margin: 10px 0 0; }
.sf-actives .sf-spec-term,
.sf-actives .sf-spec-value { margin: 0; }
```

- **净新增 55 行**：其中 **14 行是解释性注释**，实际选择器/声明 **41 行**。
  你的授权口径是「成分药丸行约 12 行」—— 药丸那两条规则（`.sf-actives__ing` + `.sf-actives__pill`）**16 行**，量级一致；余下 25 行是标题/导语/分隔线/`dl` 归零，逐条都不可省到 0：
  | 规则 | 为什么不能省 |
  |---|---|
  | `.sf-actives__title { margin: 0 }` | `h2` 有 UA 默认 `margin-block: 0.83em`，不清掉会在 48px 段距上再叠 margin |
  | `.sf-actives__intro` | 需要限宽（720px，否则 B2B 长句在 1440 下铺满一行）与次级色 |
  | `.sf-actives__item + .sf-actives__item` | 4 条配方之间需要可读分隔；白底上不用卡框，改用站内已有的 hairline |
  | `.sf-actives__label` | `Ingredients` / `Guaranteed Analysis` 两个小标题，否则表格无标题（`[sf_formula_detail]` 用 `<h3 class="sf-fdetail__label">` 做同一件事） |
  | `.sf-actives__name { font-size: 17px }` | 与 `theme.json` 的 h3 层级一致，单列时不至于过大 |
  | `dl` 归零 2 条 | 见下 |
- 相对你原来的 2 行（`.sf-actives .sf-spec-term, .sf-actives .sf-spec-value { margin: 0 }`）**多出 1 条 `dl` 规则**：`<dl>` 的 UA 默认是 `margin-block: 1em`，而 `.sf-spec-list` 只覆盖了 `margin-top`，不归零就会在表格下方多出 16px。
- **刻意不加 `@media` 断点**：28 / 10 / 16px 这些值在 375 下本来就成立，加一层响应式只会多一处需要回归的变量。
- 另一个可选视觉分支（**不采用**，仅记录）：药丸改 `background-color: var(--wp--preset--color--bg-light)` 填充版。改用现有 token，一行之差。

### 2.4 版本号（两处同步）

| 文件 | 行 | 现值 | 改为 |
|---|---|---|---|
| `functions.php` | 26 | `'2.10.44'` | `'2.10.45'` |
| `style.css` | 5 | `Version: 2.10.44` | `Version: 2.10.45` |

（全仓仅此 2 处出现 `2.10.44`，已核。）

### 2.5 实施方式

沿用主题惯例：写一个**幂等改写脚本** `tools/b2d_s1_apply.py`（`insert` 处带 `assert count == 1`；`functions.php` / `style.css` 用文本块插入 + 回读断言），而**不是** 8 次手工编辑。
理由：8 处必须逐字节相同；脚本可断言「插入后 8 页新块 md5 全等（除 `form=` 值）」并留档。

---

## 3. 回归点（12 项，逐项给判据与命令）

| # | 项 | 判据 / 命令 | 预期 |
|---|---|---|---|
| 1 | PHP 语法 | `php -l functions.php` | 干净 |
| 2 | 块配平 × 8 | `tools/b2c_s2_block_lint.py templates/page-*.html` | 8/8 PASS；另 `grep -E '"/ -->"'` 8 页 0 |
| 3 | **新块 8 页同构** | 抽 `<!-- B2D-S1: actives -->` 到 `<!-- /wp:group -->` 段，把 `form="…"` 归一后算 md5 | 8/8 相等 |
| 4 | **掩码字节回归** | 预检 A/B（基线 commit vs 候选 commit，同一副本目录名，均带门 + `--bust`）→ `b2c_s2_norm_attrs.py`（抹 `?ver=` / 主题目录名）→ `sf_masked_cmp.py`。**先跑 `--aa` 自检** | 8 剂型页 `DIFF`，**其余页 `SAME`**（页集 = 8 剂型 + 21 详情 = 29 页，另加首页/`/formulas/`/`/zh/` 等做外圈） |
| 5 | **限定证明（纯加法最强证明）** | 写 `tools/b2d_s1_confine.py`：从候选页里**只删** `<!-- B2D-S1: actives -->` → 匹配的 `<!-- /wp:group -->` 段（含后随空行），归一 `?ver=` 与副本目录名，再与基线逐字节比 | 8 页**逐字节相同** ⇒ 除新增块外，卡数/卡序/JSON-LD/入队/markup 一字未动 |
| 6 | 入队资源清单 | `tools/b2c_s2_ver_inventory.py` | **只有 `sinofresh-style` 2.10.44 → 2.10.45**；资源集合无增减 |
| 7 | **JSON-LD 单独核验（数据层）** | 8 页抽全部 `<script type="application/ld+json">`：Product 的 `additionalProperty` **仍应缺失**；`FAQPage`/`BreadcrumbList`/`ItemList`/`Organization` 段数与内容不变 | 与基线 deep-equal |
| 8 | K2 不受影响 | `.sf-formulas-data` 的条数与三字段值 | 逐字节相同（4/3/3/2/2/2/2/3 条） |
| 9 | 新块渲染计数 | 8 剂型页 DOM 计数：`article.sf-actives__item` / `li.sf-actives__pill` / `.sf-spec-row` | soft-chews 4/24/8；tablets 3/18/7；powders 3/10/3；pastes 2/9/4；drops 2/6/2；liquids 2/11/6；fish-oil 2/6/8；dental-chews 3/15/5 |
| 10 | 配置器不回归 | 浏览器：`.sf-formula__cta` 4 处，点击 → `sessionStorage` → 摘要卡回填 | 4 处仍在、回填正常 |
| 11 | toc-nav 点轨 | 浏览器实测：点轨项数 6 → 7，新项在**第 3 位**且能滚到 `#actives`；`#formulas` / `#configurator` / `#inquiry-form` 仍准；`document.body` 根（无 `<main>`）下计数恰为 7 | 通过 |
| 12 | 响应式 + i18n + 图片 | 375/768 下无横向滚动、药丸换行正常；`/zh/products/soft-chews/` 200 且无 PHP 报错（英文原文，本批不补 TP 串）；**本批完全不碰图片** | 通过 |

预检装置（老规矩）：
- mu-plugin **头门** `X-SF-Preflight: 1`（不用 query 门）；副本装成 `wp-content/themes/sinofresh-theme-preflight/` 并过滤 **`stylesheet` + `template`**（验 CSS/JS 必须如此，否则验的是线上文件）；
- 副本用 `git -C site-repo archive <commit> sinofresh-theme | tar -x` 取，**A 趟装基线 commit、B 趟换装候选 commit**（同目录名 ⇒ 目录名差异天然抵消）；
- **带门访问排在任何不带门访问之前**，点击类测试放最后；
- 诊断日志写 `mu-plugins/` 自己旁边（**不写 `/tmp`**，`open_basedir` 会静默拦住）；
- 用完连日志一起删净，**再复读线上基线**证明未被动过。

---

## 4. 回滚

| 项 | 值 |
|---|---|
| 改动性质 | **纯新增**：不改 post meta、不改模板路由、不碰 K1/K2/K7、无 option/transient 写入 ⇒ 数据层零风险 |
| 单 commit 整体回退 | 10 个文件（8 模板 + `functions.php` + `style.css`）一个 commit，`git revert <sha>` 即可 |
| 备份 | 实施前 10 个文件存 `_backup/b2d-step1-<ts>/`（含 `MANIFEST.md`；该目录不进仓库） |
| 云端 | `pull` 后只 `chown -R apache:apache sinofresh-theme`（**不要整仓 chown**，会让 root 的 git 报 dubious ownership）；回滚后复验基线 md5 全等 |
| 回滚后硬指标 | 8 页回到 `c0308af` 的字节数；`#actives` 段与 H2 消失；点轨回到 6 项 |

---

## 5. 三处实现内部取舍 —— 已按下列裁决定案，不留待回答

### 5.1 括号配平：**保留**，但论据降级（不再是「必须」）

你在本批规格里**明确点名** `sinofresh_formula_split_top_level()`（括号配平感知），按规格实现。
同时如实记录：它的必要性论据（§1 的「缺右括号」）已被推翻，干跑证明它在现有 21 条数据上是 **no-op**。
保留理由只有两条，且都成立：① 约 10 行纯函数、零运行时风险、已有 13 例对抗性探针覆盖；
② 一旦内容侧写出 `X (a, b), Y`，朴素切分会**静默**产出错误词条（错在数据里，页面不会报错）。
⇒ 实施时按你的规格写，**不额外解释为「必要」**；`tools/b2d1_parser_dryrun.php §1` 会一直把这条实测钉在 0/21。

### 5.2 药丸形态：**outline**（`1px solid border-light` + `999px`）

选它的依据是站内已有先例而不是偏好：`.sf-topbar-badges` 的 certificate pill 就是
`padding: 1px 8px` + `1px solid var(--wp--preset--color--border-light)` + `border-radius: 999px`。
填充版（`bg-light` 底）在同页会与块⑤ How We Work 的浅底段形成两种"浅色块"词汇，故不采用。
一行之差即可切换，已在 §2.3 末尾记录为备选分支。

### 5.3 CSS 净增：**接受 55 行**（实际声明 41 行），不压缩

原本设想「压到 ≈20 行的极简版」需要砍掉 `Ingredients` / `Guaranteed Analysis` 两个小标题，
代价是保证值表**没有标题**（4 条配方连续排下来读者分不清哪张表是什么）。
`[sf_formula_detail]` 用 `<h3 class="sf-fdetail__label">` 做同一件事，即站内惯例就是给这两个小节加标题。
⇒ 采用 55 行版本。另已**刻意删掉 `@media` 断点**（§2.3 末条），把需要回归的变量从 2 个降回 1 个。

---

## 6. 下一步

方案就绪，**主题目录仍是零改动**（`git status` 空，云端 `c0308af`）。
按你定的工作约定（先扫描 → 报告方案 → 停下等确认 → 再动手），此步停在这里。
你说开工，我按 §2 实施、按 §3 过 12 项回归、按 §4 留回滚点，完成后再停下汇报。
