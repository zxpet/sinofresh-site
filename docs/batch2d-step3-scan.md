# 批次 2D 第 3 批 —— 扫描实证（配方详情页图集 + 成分表）

> 只读扫描，未改任何文件。时间 2026-09-21 00:3x CST。
> 目标域：`dev.zxpet.com`（`65.49.215.152`，Apache + MariaDB + PHP 8.3，docroot
> `/var/www/dev.zxpet.com/public`，仓库 `…/site-repo`）。所有访问带 Basic Auth。
> 口径：**能实测的一律实测**；文档/记忆里的数字只作线索。

---

## 0. 扫描清单 vs 用户六项

| # | 用户要的 | 本章节 |
|---|---|---|
| 1 | 第 2 批 commit 列表，剂型页图集插入点 | §1 |
| 2 | `single-sf_formula.html` 当前结构 | §2 |
| 3 | `formula-gallery.js` 和 `.sf-gallery` CSS 现状 | §3 |
| 4 | 21 条配方现有 post meta 字段清单 | §4 |
| 5 | 成分保证值 / 原料配料的数据来源（有还是没有） | §5 |
| 6 | 配方详情页插入点锚点 | §6 |

---

## 1. 第 2 批 commit 列表 + 剂型页图集插入点

### 1.1 commit（`origin/main`，本地与云端 `site-repo` 均为 `cb63af6`）

```
cb63af6  Batch2D Step2: product gallery band on the eight dosage pages   ← 实施
cfbd5e4  Batch2D Step2 plan: gallery band, native switcher and four corrections
2298b4a  Batch2D Step2: evidence images behind the placeholder pick
e8dbfd2  Batch2D Step2 scan: gallery baseline, image inventory and four blocking decisions
```

`cb63af6` 的改动面（`git show --stat`）：**11 文件 / +542 / −2**
`assets/js/formula-gallery.js`(新 187 行)、`functions.php`、`style.css`、
`templates/page-{8 个剂型}.html` 各 **+10 行 0 删除**。

### 1.2 未提交的残留（本批开工前要处理）

- `tools/b2d_s2_*.py`（6 个）+ `tools/b2d_paths.txt` + `docs/b2d-step2-shots/*.png`（7 张）**仍未跟踪**
- ⛔ **上一批的预检脚手架还装在线上**，未拆：
  ```
  mu-plugins/zz-sf-preflight.php        （过滤器：命中 X-SF-Preflight: 1 时换 stylesheet/template）
  mu-plugins/zz-sf-preflight.log  +  .prev
  themes/sinofresh-theme-preflight/     （副本目录）
  ```
  这是上一批"待完成 ②"没做完的尾巴。它是一层 `stylesheet`/`template` 过滤器，
  **留着会让本批的基线抓取不干净** ⇒ 第 0 步先 `remove`，复验匿名 401 / `www` 302 / 带凭据 200。

### 1.3 图集插入点（8 页逐页实测，完全同构）

- marker 与短代码：8 页**各命中 1 次** `<!-- B2D-S2: gallery -->` + `[sf_formula_gallery form="…"]`
- 块所在行：8 页**都是第 30–37 行**（块注释在 31 行，`<section id="gallery"…>` 在 32 行）
- 前后字节（以 `page-soft-chews.html` 为例）：

```
26  </section>
27  <!-- /wp:group -->
28  (空行)                     ← 原始状态只有这一行空行
29  (空行)                     ← 第 2 批插入块时补的"字节中性"空行
30  <!-- B2D-S2: gallery -->
31  <!-- wp:group {"tagName":"section","anchor":"gallery","className":"sf-gallery", …} -->
32  <section id="gallery" class="wp-block-group sf-gallery has-bg-light-background-color has-background" …>
33  <!-- wp:html -->
34  [sf_formula_gallery form="soft-chews"]
35  <!-- /wp:html -->
36  </section>
37  <!-- /wp:group -->
38  (空行)
39  <!-- wp:group {"tagName":"section","anchor":"formulas","className":"sf-formulas", …} -->
```

- ✅ **撤除可被 git 逐字节证明**（最强证据，比任何掩码都硬）：
  `git diff cfbd5e4 HEAD -- sinofresh-theme/templates/` 现为 **8 文件 / +10 / −0**；
  改完后 `git diff cfbd5e4 -- sinofresh-theme/templates/page-*.html` **必须输出为空**。
- ✅ **`#gallery` 无任何引用**：`grep -rnE '#gallery|anchor":"gallery' templates/ parts/ assets/js/`
  命中的 8 条**全是块自己那一行**。没有导航、点轨、内链、深链依赖它。
- ✅ **`sf-gallery` 全仓引用**＝8 个剂型模板 + `assets/js/formula-gallery.js`，无第三处。
- ✅ 8 页自闭合块各 **3 个**（图集块是容器块，撤除不改变自闭合计数 ⇒ ` /-->` 纪律不受影响）。

---

## 2. `templates/single-sf_formula.html` 当前结构

文件 4,568 B。**一份模板服务全部 21 条配方**（不是每配方一份）。

| # | 行 | 块 | 现状 |
|---|---|---|---|
| 1 | 1 | `template-part header` | — |
| 2 | 3–16 | Hero（面包屑 + eyebrow + h1 + meta + 两个按钮） | `<section class="… sf-hero-inner sf-formula-hero">`，`textColor: card-white`，底色由 `.sf-hero-inner` 给 `#2E6B54` |
| 3 | 18–28 | `sf-fdetail` + `<h2>Specification</h2>` + `[sf_formula_detail]` | `backgroundColor: card-white`，间距 80/80 |
| 4 | 30–33 | `[sf_formula_body]`（**裸 `wp:html`，无容器块**） | 无 `wp:group` 包装 |
| 5 | 35–45 | `sf-fdetail-more` + `<h2>More {{FORM_CRUMB}} Formulas</h2>` + `[sf_formula_grid limit="4"]` | `backgroundColor: bg-light` |
| 6 | 47–61 | CTA（`<h2>Ready to Launch Your Product?</h2>` + 按钮） | `backgroundColor: primary`，`textColor: card-white` |
| 7 | 63 | `template-part footer` | — |

### 2.1 渲染实测（`/formulas/joint-support-soft-chews/`，HTTP 200 / 107,344 B）

- 顶层 `<section>` **4 个**：`sf-hero-inner sf-formula-hero` → `sf-fdetail` → `sf-fdetail-more` → CTA band
- 渲染 `<h2>` **3 个**：`Specification` / `More Soft Chews Formulas` / `Ready to Launch Your Product?`
- 渲染 `<img>` 7 个：logo×2（header/footer）+ **`soft-chews.webp`×3**（Related 网格 3 张卡）+ 语言旗×2
- `<p class="sf-formula-hero__meta">` = `Soft Chews · MOQ from 500–1,000 units · Lead time 7–15 working days after packaging is ready`
- JSON-LD 4 块：`BreadcrumbList` / **`Product`（含 `additionalProperty` 3 条 PropertyValue）** / `Organization` / `ItemList`（`Standard Formulas — Soft Chews`，3 项）
- ⛔ **`[sf_formula_body]` 在 hero 与 Specification 之间不产生任何输出** ⇒ 证实 §5.1 的"21/21 post_content 为空"

### 2.2 关键工程约束

- **占位符引擎**（`functions.php:2577 sinofresh_template_placeholders()`，经 `render_block` 过滤
  `core/html` 块）提供 `{{TITLE}} / {{FORM_CRUMB}} / {{FORM_HREF}} / {{FORM_SLUG}} / {{FORMULA_USE}} /
  {{FORMULA_META}} …`。⇒ **一份模板可以按记录出不同文案**，这是"21 条共用一份模板"能成立的原因。
- **hero 必须是第一个元素**：`style.css:1856 .wp-site-blocks > header.wp-block-template-part + *`
  ⇒ 新模块只能插在 hero **之后**。
- **本页没有点轨**：`toc-nav.js` 入队条件是
  `is_front_page() || is_page([quality, about, services, factory-tour, 8 个剂型]) || is_singular('post')`
  （`functions.php:40`）——**不含 `is_singular('sf_formula')`** ⇒ 在详情页加 H2 **不影响任何点轨**。
- **`formula-gallery.js` 当前不入队到详情页**：它只在 `$is_dosage_page` 分支里
  （`functions.php:182-189`）⇒ **复用 JS 必须先把入队条件改到 `is_singular('sf_formula')`**。

### 2.3 图集 JS 的 DOM 契约（决定容器怎么写）

`formula-gallery.js:178` 用 `document.querySelectorAll('.sf-gallery')` 找 **root**，
root 内再找 `.sf-gallery__inner` / `.sf-gallery__stage` / `.sf-gallery__slide`。
⇒ **新页面上的容器 section 必须带 `sf-gallery` 类**，否则 JS 找不到 root、缩略图条不生成
（无 JS 时仍能看主图，不会报错——这是既有的降级契约）。

---

## 3. `formula-gallery.js` 与 `.sf-gallery` CSS 现状

### 3.1 JS — `assets/js/formula-gallery.js`

- **187 行 / 6,902 B**，句柄 `sinofresh-formula-gallery`，版本 **`1.0.0`**，`$in_footer = true`
- IIFE，`"use strict"`，零依赖
- 数据源唯一：stage 里的 4 个 `<figure class="sf-gallery__slide">` ⇒ 缩略图条、无障碍名、切换目标**全部派生**
- 切换只 `classList.toggle('sf-gallery__slide--off')` + `aria-hidden` / `aria-selected` / roving tabindex，
  **不移动、不重建、不克隆 DOM**
- 键盘：`ArrowRight/ArrowLeft/Home/End`；事件委托一次
- 手势：Pointer Events，`SWIPE_MIN = 40`、`SWIPE_RATIO = 1.5`；`PointerDown` 时 `setPointerCapture`
- `slides.length < 2` 直接 return（单图不加增强）
- **不需要任何改动就能服务详情页**（同样的 markup）⇒ 版本保持 `1.0.0`

### 3.2 CSS — `style.css:7965–8080`

- **116 行 / 3,903 B**，紧接在文件最后一个块（文件共 8,080 行）
- `:has(` = **0** ⇒ 不改变 `163 / 7 / 170` 这个不变量
- 声明级 `!important` = **0**（段内那 2 处 `!important` 出现在**注释**里，是"刻意不抄 `.sf-fac`"的说明）
- `url(` = **0**（零外部资源）
- 主结构：`.sf-gallery__title` / `__stage`（`aspect-ratio:1/1`、`max-width:680px`、`touch-action: pan-y pinch-zoom`、
  静置阴影 `0 2px 12px rgba(0,0,0,.08)`）/ `__slide`（`position:absolute;inset:0` + `opacity` 过渡）/
  `__slide[hidden]` / `__slide--off` / `__slide img`（`object-fit:cover`）/ `__thumbs` / `__thumb`（104×104、
  1px `border-light`、6px 圆角）/ `__thumb[aria-selected="true"]`（accent 边 + 1px 环）/
  `__thumb:focus-visible`（2px accent outline，
  `@media (max-width:768px)`：`__thumbs` 横向 `overflow-x:auto` + `scroll-snap-type:x mandatory`、
  `__thumb` 84×84 + `scroll-snap-align:start`；`@media (prefers-reduced-motion:reduce)` 关过渡

### 3.3 资产可用性（服务端实测）

四个槽位的文件**全部存在**于 `uploads/2026/09/`：
`fac-placeholder.webp`(1100×733) / `fac-packaging.webp`(800×600) / `fac-line.webp`(800×600) /
`{剂型}.webp`(720×720)。槽位表在 `functions.php:1170 sinofresh_formula_gallery_slots()`，
尺寸是 `getimagesize` 实测值（不是抄模板里那条陈旧的 `width="800" height="600"`）。

---

## 4. 21 条配方现有 post meta 字段清单

**只读全量枚举**（`tools/b2d_s3_probe_meta.php` → `wp eval-file`）。21 条全部 `publish`，
`menu_order` 1–4，ID `158–178`。

### 4.1 实际存在的 meta（5 个，无第 6 个）

| meta_key | 行数 | 非空 | 样例 |
|---|---|---|---|
| `sf_formula_analysis` | 21 | **21** | `Aloe Vera ≥10%` |
| `sf_formula_ingredients` | 21 | **21** | `Organic Aloe Vera, Tea Tree Oil, Calendula` |
| `sf_formula_source` | 21 | **21** | `page-drops.html #1 (pre-2B template, extracted 2026-09-20)`（**后台注记**） |
| `sf_formula_specs` | 21 | **21** | `30ml/50ml dropper bottle · 24 months shelf life` |
| `wp_statistics_words_count` | 21 | 21 | `0`（WP Statistics 插件写的，非业务字段） |

### 4.2 用户方案里提到/暗示、但**不存在**的字段（逐个查了 `metadata_exists`）

全部 **`present=0` / `MISSING ENTIRELY`**：

```
sf_formula_base               sf_formula_other_ingredients    sf_formula_characteristics
sf_formula_recommended_use    sf_formula_warnings             sf_formula_studies
sf_formula_intro_paragraphs   sf_formula_form                 sf_formula_use
sf_formula_documents          sf_formula_serving_size         sf_formula_pack_count
sf_formula_shelf_life
```

- ⛔ **`sf_formula_form` / `sf_formula_use` 不是缺失的 meta，而是 taxonomy**（见 4.3）。
- 已注册到 REST/AE 的 meta 只有 4 个（`functions.php:439-454`）：
  `sf_formula_ingredients` / `sf_formula_analysis` / `sf_formula_specs` / `sf_formula_source`。

### 4.3 剂型与功效走 taxonomy（**不是 post meta**）

```
taxonomies = sf_formula_form, sf_formula_use
sf_formula_form : Soft Chews×4, Tablets×3, Powders×3, Pastes×2, Drops×2,
                  Liquids×2, Fish Oil×2, Dental Chews×3
sf_formula_use  : Joint care / Skin & coat / Digestive care / Oral care / … （21 条各不相同）
```

⇒ **剂型是 term，不是 meta**。`sinofresh_formula_current_form('')`（`functions.php:509`）
在 `is_singular('sf_formula')` 上已经用 `wp_get_post_terms($id,'sf_formula_form')` 解析出剂型 slug。

### 4.4 `post_content` —— **21/21 全为 0 字节**

| | 值 |
|---|---|
| 21 条 `strlen(post_content)` | 全部 **0** |

---

## 5. 成分保证值 / 原料配料的数据来源

### 5.1 ⑤「成分保证值」——**数据有，21/21**

- `sf_formula_ingredients` 21/21 非空、`sf_formula_analysis` 21/21 非空 ⇒ **可直接复用**
- 既有解析器（`functions.php`）**零新逻辑**：
  - `sinofresh_formula_split_top_level($v)`（`:940`）—— 括号配平切 `', '`（`Tapioca (46%)` 这类安全）
  - `sinofresh_formula_analysis_pairs($v)`（`:978`）—— 切 `', '` 再切 `≥` 成 `term/value`
- 既有产出样式（`[sf_formula_actives]`，`:1026`）：成分＝`ul.sf-actives__ing > li.sf-actives__pill` 药丸；
  保证值＝`dl.sf-spec-list > div.sf-spec-row > (dt.sf-spec-term + dd.sf-spec-value)`
- ⛔ **但 `[sf_formula_actives]` 不能直接搬到详情页**：它按 `tax_query` 拉**整个剂型**的全部配方
  （详情页会印 2–4 条配方的成分）。详情页需要**单条**版本。

### 5.2 ⑥「原料与配料表」——**数据没有（0/21）**

- `sf_formula_base` / `sf_formula_other_ingredients` / `sf_formula_composition` ⇒ 全部 `present=0`
- 唯一沾边的 `sf_formula_ingredients` 是**一个自由文本成分串**，语义**逐条不等**：
  - `Ear Care Drops`：`Organic Aloe Vera, Tea Tree Oil, Calendula` ← 活性物清单
  - `Hairball Remedy Paste`：`Malt Extract (43%), Oils and Fats (30%), Chicken Meal (4%), Yeast, Minerals`
    ← **带百分比的完整配料**（≈ composition）
  - `Natural Cleaning Dental Sticks`：`Tapioca (46%), Peas (29%), Vegetable Glycerin (12%), …`
    ← 同上
  ⇒ 同名字段在不同记录上分别扮演"活性成分"与"配料表"两种角色，**库内没有把两者分开的数据**。
- ⛔ 且该字段**已被 ④（Specification 卡）与 ⑤ 消费**；再拿它做 ⑥ 会在**同一页把同一串印三遍**。

### 5.3 ③「产品详细介绍（复用 `[sf_formula_body]`）」——**数据没有（21/21 空）**

`[sf_formula_body]`（`functions.php:1445`）读 `post_content`；实测 **21 条全 0 字节**
⇒ 该模块在**今天渲染 100% 为空**（§2.1 已在线上复现：hero 与 Specification 之间没有 `<section>`）。
数据要出现，只能靠后台给 21 条记录补正文（受 authority guard 守卫的是**块模板**，
`post_content` **在 wp-admin 可编辑、不受影响**）。

### 5.4 ④ Specification 3 字段卡 —— `[sf_formula_detail]`（`:1395`）

`is_singular('sf_formula')` 才输出；读 `sf_formula_ingredients` / `sf_formula_analysis` /
`sf_formula_specs` 三个 meta，渲染 3 张 `.sf-fdetail__card`（**纯文本**，标签
`Ingredients` / `Guaranteed Analysis` / `Standard Specs`），任一为空则跳过该卡，全空返回 `''`。
⚠️ **信息重叠点**：④ 的卡里已含"成分"与"保证值"的纯文本，⑤ 是同一份数据的**药丸 + 表格**版。

---

## 6. 配方详情页插入点锚点（逐条实测唯一）

文件 `templates/single-sf_formula.html`（4,568 B）。

| 锚点 | 字节串 | 命中 | sha256[:16] | 长度 |
|---|---|---|---|---|
| **A** hero 之后 / Specification 之前 | `<!-- /wp:group -->\n\n<!-- Block 2: Specification -->` | **1** | `537efc7c8f087119` | 51 B |
| **B** `[sf_formula_body]` 那一整块 | `<!-- Block 3: long copy (emitted only when the record has some) -->\n<!-- wp:html -->\n[sf_formula_body]\n<!-- /wp:html -->\n` | **1** | `d4a5491e24ad7400` | 121 B |
| **C** Specification 段末（③④ 段落之后的新模块位） | `<!-- /wp:html -->\n</section>\n<!-- /wp:group -->\n\n<!-- Block 3: long copy` | **1** | — | — |
| **D** Related 段开头 | `<!-- wp:group {"tagName":"section","className":"sf-fdetail-more"` | **1** | `efd5779c929676b3` | 64 B |
| **E** `[sf_formula_body]` 短代码本体 | `[sf_formula_body]` | **1** | `c431f4f533dbef35` | 17 B |
| **F** `[sf_formula_detail]` 短代码本体 | `[sf_formula_detail]` | **1** | `0463a72ead980e5c` | 19 B |

逐字节上下文（用于改写脚本的等值断言）：

```
'…</section>\n<!-- /wp:group -->\n\n'                     ← hero 段末（锚点 A 的前半）
'<!-- Block 3: long copy … -->\n<!-- wp:html -->\n[sf_formula_body]\n<!-- /wp:html -->\n\n'
'<!-- Block 4: related formulas -->\n<!-- wp:group {"tagName":"section","className":"sf-fdetail-more",…'
```

---

## 7. 回归门现状（本批必须扩）

### 7.1 现有 47 页清单 `tools/b2d_paths.txt` 的构成

| 分组 | 条数 |
|---|---|
| 营销/法务等普通页 | 15（`/`、`/formulas/`、`/blog/`、`/about/`、`/quality/`、`/contact/`、`/faq/`、`/services/`、`/cooperation/`、`/factory-tour/`、`/products/`、`/privacy-policy/`、`/terms/`、`/cookie-policy/`、`/feedback/`） |
| EN 剂型页 | **8/8** |
| EN 配方详情页 | **21/21** |
| zh | **3**（`/zh/`、`/zh/formulas/`、`/zh/products/soft-chews/`） |

### 7.2 本批覆盖面缺口（实测可达性）

- 实测 `/zh/products/{8 个剂型}/` **8/8 = 200**（现清单只含 1 个）
- 实测 `/zh/formulas/{21 条}/` **21/21 = 200**（现清单含 **0** 个）
- ⇒ **建议把清单扩到 75 页**：47 + 7（补 zh 剂型）+ 21（zh 详情）。
  本批的改动面正是"8 剂型 + 21 详情"，zh 侧同模板同输出，**必须一起锁进回归门**。

### 7.3 已固化的两把锁（沿用，勿改）

1. **限定证明**（marker-driven）：`tools/b2d_s1_confine.py` 的思路 —— 删新块后与基线**逐字节**比
2. **掩码回归**：`tools/sf_masked_cmp.py`（**必带 `-u`**，**先跑 `--aa` 自检**）
   ＋ `tools/b2d_s2_norm.py`（**只归一化 `?ver=` 令牌**）
   ＋ `tools/b2c_s2_ver_inventory.py`（资源清单）
3. ⛔ **不要复用 `b2c_s2_norm_attrs.py`**（它会顺手删 `data-form`／`data-sf-form`，是 K1 的盲区）
4. ⛔ **不要改 `sf_masked_cmp.py`**（已为它修过两次，已认证的门不动）

---

## 8. 扫描结论（一句话版）

1. 8 页图集可**零风险撤除**，且有 git 逐字节证明；`#gallery` 无任何外部引用。
2. 详情页只有一份模板、没有点轨、hero 之前不能插块；**图集 JS 可 100% 复用**，
   但必须在模板里给容器 `sf-gallery` 类 + 把 enqueue 迁到 `is_singular('sf_formula')`。
3. **⑤ 有数据**（`sf_formula_ingredients` / `sf_formula_analysis` 各 21/21），但**必须做单条版短代码**。
4. **③ 无数据**（`post_content` 21/21 空）、**⑥ 无数据**（三个候选 meta 全 `present=0`）——
   两个模块今天都会渲染为空。
5. 剂型**不在 post meta**，是 taxonomy `sf_formula_form`。
6. 上一批的预检脚手架**还没拆**，本批开工前先清。
