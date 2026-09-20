# Standard Formulas 卡片化 + CPT 架构 —— 扫描报告（未改任何代码）

- **日期**：2026-09-20
- **范围**：8 个剂型页的 `section.sf-formulas`（21 个配方）→ CPT + shortcode 卡片网格 + 配方详情页
- **性质**：**只读扫描**。本报告不改任何源码、不写 DB。
- **产物**：`tools/_sf_cpt_scan.py`（配方抽取）、`tools/_sf_img_scan.py`（图片盘点）、`tools/_sf_formula_probe.js`（运行时几何）、`tools/_sf_trp_probe.php`（TranslatePress 设置）
- **数据**：`docs/scan-evidence-formulas-cpt-20260920/{formulas,images,probe,slugs}.json`（持久副本；生成时落于 `/tmp/b1/cpt_scan/`）

---

## 0. 结论速览

| # | 结论 |
|---|---|
| 1 | 21 个配方数据**完整可抽**，8 页 `ItemList` 与 DOM **逐项一致**；`name ≡ data-formula` 21/21 通过 |
| 2 | **0 张配方级图片**；8 张剂型图统一 720×720（其中 liquids / dental-chews 缺 300/150 变体）；`fac-*` 可用 7 张 |
| 3 | 主题**从未注册过 CPT/分类法/meta**；有 **3 个 shortcode 先例**（`sf_explore_chips` / `sf_archive_count` / `sf_blog_chips`）；`sf_last_reviewed` 只是**裸读 `get_post_meta()`**（**无 `register_post_meta` 写法可抄**，见 §3）；**无 ACF** |
| 4 | `sf-formulas` 8 页**结构 100% 同构**，全部位于模板第 58 行；区内容 = `h2` + 引导句 + N×`wp:html`(details) + 1×`wp:html`(ItemList) |
| 5 | **块主题下 CPT 模板无需注册**：`templates/single-sf_formula.html` 自动生效；fallback 链 `single-sf_formula-{slug}` → `single-sf_formula` → `single` → `singular` → `index`（**`single.html` 已存在**，是兜底也是错版风险） |
| 6 | **已定位 3 处必须处理的耦合**（见 §8）：`.sf-toast` 4 脚本共用、`configurator.js readFormula()` DOM 抓取、`ItemList` 实体泄漏（3/21 条） |
| 7 | 建议 URL：**`/formulas/<slug>/`**（扁平）。`/products/soft-chews/<formula>/` 这种嵌套**在单个 CPT 上无法原生实现**（见 §6.6） |

---

## 1. 21 个配方完整数据

抽取脚本 `tools/_sf_cpt_scan.py`，从 8 个 `page-*.html` 的 `<section id="formulas">` 内逐个 `<details class="sf-formula__item">` 解析。

### 1.1 数量与门禁

| 剂型 | 配方数 | 预期 | 区块字节 | ItemList 条数 | ItemList ≡ DOM |
|---|---:|---:|---:|---:|:---:|
| soft-chews | 4 | 4 | 4,714 | 4 | ✅ |
| tablets | 3 | 3 | 3,720 | 3 | ✅ |
| powders | 3 | 3 | 3,520 | 3 | ✅ |
| pastes | 2 | 2 | 2,619 | 2 | ✅ |
| drops | 2 | 2 | 2,512 | 2 | ✅ |
| liquids | 2 | 2 | 2,688 | 2 | ✅ |
| fish-oil | 2 | 2 | 2,619 | 2 | ✅ |
| dental-chews | 3 | 3 | 3,693 | 3 | ✅ |
| **合计** | **21** | 21 | **26,085** | 21 | **8/8** |

三字段（Ingredients / Guaranteed Analysis / Standard Specs）齐备 **21/21**；`name` 与 CTA 的 `data-formula` **21/21 一致**（后者是配方身份锚，`formulas.js` 依赖它）。

### 1.2 完整清单（按剂型）

#### soft-chews（4）

| # | 配方名 | 分类标签 | Ingredients | Guaranteed Analysis | Standard Specs |
|---|---|---|---|---|---|
| 1 | Joint Support Soft Chews | Joint care | Glucosamine HCl, Chondroitin Sulfate, MSM, Green-lipped Mussel, Chicken Flavor | Glucosamine ≥500mg/chew, Chondroitin ≥200mg/chew, MSM ≥100mg/chew | 2g/piece · 60/90/120 per bottle · 18 months shelf life |
| 2 | Calming Soft Chews | Calming | L-Tryptophan, Kelp, Ginger Root, Valerian Root, Chamomile, Thiamine | L-Tryptophan ≥120mg/chew, Chamomile ≥20mg/chew | 2g/piece · 60/90/120 per bottle · 18 months shelf life |
| 3 | Digestive Soft Chews | Digestive care | Alpha-Amylase, Lipase, Cellulase, Protease, Bacillus coagulans, FOS | Total microorganisms ≥1 billion CFU/chew | 2g/piece · 60/90/120 per bottle · 18 months shelf life |
| 4 | Skin & Coat Soft Chews | Skin & coat | Marine Fish Oil, Safflower Oil, Coconut Oil, Biotin, Vitamin C, Vitamin E, Kelp | Omega-3 ≥50mg/chew, Biotin ≥50mcg/chew | 2g/piece · 60/90/120 per bottle · 18 months shelf life |

#### tablets（3）

| # | 配方名 | 分类标签 | Ingredients | Guaranteed Analysis | Standard Specs |
|---|---|---|---|---|---|
| 5 | Joint Support Tablets | Joint care | Glucosamine HCl, MSM, Chondroitin, Green-lipped Mussel | Glucosamine ≥500mg/tablet, MSM ≥500mg/tablet, Chondroitin ≥200mg/tablet | 1g/tablet · 60/120/180 per bottle · 24 months shelf life |
| 6 | Multivitamin Tablets | Daily nutrition | Vitamin A, D3, E, B-complex, Zinc, Iron, Methionine, EPA, DHA | Vitamin E ≥50 IU/tablet, Zinc ≥5mg/tablet | 1g/tablet · 60/120/180 per bottle · 24 months shelf life |
| 7 | Calcium & Phosphorus Tablets | Bone health | Dicalcium Phosphate, Dried Yeast, Whey, Hydrolyzed Soy Protein, Vitamin D3 | Calcium ≥200mg/tablet, Phosphorus ≥100mg/tablet | 1g/tablet · 60/120/180 per bottle · 24 months shelf life |

#### powders（3）

| # | 配方名 | 分类标签 | Ingredients | Guaranteed Analysis | Standard Specs |
|---|---|---|---|---|---|
| 8 | Probiotic Powder | Digestive care | Inulin, Spinach Extract, Bacillus subtilis DE111, L. acidophilus, L. plantarum, B. coagulans | Total microorganisms ≥5 billion CFU/scoop | 4oz/8oz/16oz jar · 24 months shelf life |
| 9 | Pumpkin Digestive Powder | Digestive care | 100% Pumpkin Powder (fiber source) | Crude Fiber ≥15% | 4oz/8oz/16oz jar · 18 months shelf life |
| 10 | Bladder Support Powder | Urinary care | Cranberry, D-Mannose, Herbal Blend | Cranberry ≥500mg/scoop | 4oz/8oz/16oz jar · 24 months shelf life |

#### pastes（2）

| # | 配方名 | 分类标签 | Ingredients | Guaranteed Analysis | Standard Specs |
|---|---|---|---|---|---|
| 11 | Hairball Remedy Paste | Hairball control | Malt Extract (43%), Oils and Fats (30%), Chicken Meal (4%), Yeast, Minerals | Crude Fat ≥30%, Crude Fiber ≥5% | 50g/60g/100g/120g tube · 24 months shelf life |
| 12 | Nutrition Paste | Daily nutrition | Oils and Fats, Milk and Dairy, Malt Extract (12%), Yeast (MOS 1%) | Crude Fat ≥25%, Crude Protein ≥5% | 50g/60g/100g/120g tube · 24 months shelf life |

#### drops（2）

| # | 配方名 | 分类标签 | Ingredients | Guaranteed Analysis | Standard Specs |
|---|---|---|---|---|---|
| 13 | Ear Care Drops | Ear care | Organic Aloe Vera, Tea Tree Oil, Calendula | Aloe Vera ≥10% | 30ml/50ml dropper bottle · 24 months shelf life |
| 14 | Urinary Care Drops | Urinary care | Cranberry Extract, Marshmallow Root, Dandelion | Cranberry ≥200mg/ml | 30ml/50ml dropper bottle · 24 months shelf life |

#### liquids（2）

| # | 配方名 | 分类标签 | Ingredients | Guaranteed Analysis | Standard Specs |
|---|---|---|---|---|---|
| 15 | Liquid Joint Support | Joint care | Glucosamine Sulfate, MSM, Chondroitin Sulfate, Vitamin C, L-Proline, Grape Seed Extract, CoQ10, Hyaluronic Acid | Glucosamine ≥1600mg/oz, MSM ≥1500mg/oz, Chondroitin ≥1200mg/oz | 8oz/16oz/32oz pump bottle · 24 months shelf life |
| 16 | Liquid Skin & Coat | Skin & coat | Cod Liver Oil, Pollock Oil, Mixed Tocopherols | Omega-3 ≥30%, EPA ≥10%, DHA ≥12% | 8oz/16oz/32oz pump bottle · 24 months shelf life |

#### fish-oil（2）

| # | 配方名 | 分类标签 | Ingredients | Guaranteed Analysis | Standard Specs |
|---|---|---|---|---|---|
| 17 | Wild Alaskan Salmon Oil | Skin & coat | Wild-caught Salmon Oil, Mixed Tocopherols | Omega-3 ≥30%, EPA ≥10%, DHA ≥12%, Omega-6 ≥3%, Omega-9 ≥16% | 8oz/16oz/32oz pump bottle · 24 months shelf life |
| 18 | Pure Fish Oil Blend | Skin & coat | Sardine, Anchovy, Herring, Mackerel Oil | Omega-3 ≥35%, EPA ≥18%, DHA ≥12% | 8oz/16oz/32oz pump bottle · 24 months shelf life |

#### dental-chews（3）

| # | 配方名 | 分类标签 | Ingredients | Guaranteed Analysis | Standard Specs |
|---|---|---|---|---|---|
| 19 | Plaque Control Dental Chews | Plaque control | Coconut Oil, Parsley, Shiitake Mushroom, Organic Honey | Coconut Oil ≥5% | 15g/piece · 14/28/56 per bag · 18 months shelf life |
| 20 | Oral Care Dental Sticks | Oral care | Wheat Flour, Wheat Starch, Corn Flour, Glycerin, Natural Flavors, Sodium Tripolyphosphate | Crude Protein ≥10%, Crude Fat ≥2% | 20g/piece · 7/14/28 per bag · 18 months shelf life |
| 21 | Natural Cleaning Dental Sticks | Oral care | Tapioca (46%), Peas (29%), Vegetable Glycerin (12%), Cheddar Cheese (6%), Hydrolyzed Yeast (4%) | Crude Protein ≥8%, Crude Fiber ≥2% | 18g/piece · 7/14/28 per bag · 18 months shelf life |

### 1.3 分类标签（`use`）分布

| 标签 | 配方数 | 归属 |
|---|---:|---|
| Skin & coat | **4** | soft-chews#4 / liquids#16 / fish-oil#17 / fish-oil#18 |
| Joint care | **3** | soft-chews#1 / tablets#5 / liquids#15 |
| Digestive care | **3** | soft-chews#3 / powders#8 / powders#9 |
| Daily nutrition | 2 | tablets#6 / pastes#12 |
| Urinary care | 2 | powders#10 / drops#14 |
| Oral care | 2 | dental-chews#20 / dental-chews#21 |
| Calming / Bone health / Hairball control / Ear care / Plaque control | 各 1 | — |
| **合计** | **11 类** | 21 个配方 |

> ★ **关键事实**：`Joint care`（3）与 `Digestive care`（3）**跨剂型**。这意味着分类标签是**跨剂型的聚合维度**（可以做"按功效浏览"），而不是剂型内的子标签 —— 直接影响 §6.2 的分类法设计。

---

## 2. 图片资源盘点

uploads 下 `2026/09/` 共 **71 张图**（64 webp + 7 png），总分族：

| 族 | 张数 | 总体积 | 典型尺寸 |
|---|---:|---:|---|
| 剂型图 | 20 | 0.38 MB | 720×720（主图）+ 300×300 + 150×150 |
| 工厂图 `fac-*` | 7 | 0.52 MB | 800×600（`fac-placeholder` 1100×733） |
| Logo | 7 | 0.17 MB | 1024×127 → 2048×255 |
| 头像 `avatar-*` | 6 | 0.03 MB | 200×200 |
| 博客配图 `blog-*` | 6 | 0.43 MB | 1200×900 |
| 质检图 `qc-*` | 6 | 0.34 MB | 800×600 |
| 团队照 `team-*` | 5 | 0.15 MB | 600×600 |
| 证书缩略图 `cert-*` | 4 | 0.06 MB | 400×550 |
| 设备图 `equip-*` | 4 | 0.18 MB | 800×600 |
| 首页轮播 `hero*` | 4 | 0.58 MB | 1920×1080 |
| 样张 / 视频封面 | 各 1 | 0.25 MB | 800×1100 / 1920×1080 |

### 2.1 三个直接回答问题

**Q1：8 张剂型图的实际尺寸？**

全部 **720 × 720（1:1）**，无一例外：
`soft-chews` `tablets` `powders` `pastes` `drops` `liquids` `fish-oil` `dental-chews`。

⚠️ 附带发现：**尺寸变体不全** —— `liquids` 与 `dental-chews` **没有** `-300x300` / `-150x150` 变体（其余 6 个都有）。若卡片需要小图，这 2 张要走原图。

⚠️ 另一处**既有不一致**（非本次引入）：模板里 `.sf-tile` 的 `<img>` 写的是 `width="800" height="600"`，而实际源图是 720×720。CSS 用 `width:100%; height:auto; aspect-ratio:1/1; object-fit:cover` 覆盖，所以**渲染无影响**（属性只影响无 CSS 兜底与固有比例提示）。**结论：无需修，但别照抄这组属性。**

**Q2：是否有为每个"配方"单独准备的图？**

**没有。** 21 个 `<details>` 内 `<img>` 数量为 **0**（运行时探针同样确认 `img=0`）。即：**配方级图片资源 = 0 张**。

**Q3：工厂图 `fac-*` 有多少张可用？**

**7 张**，其中 **6 张为真实素材**（`fac-cleanroom` `fac-lab` `fac-line` `fac-packaging` `fac-retention` `fac-warehouse`，各 800×600 / 1.333），1 张为占位图 `fac-placeholder`（1100×733）。**卡片视觉不需要工厂图**（工厂图属于工厂/质检叙事）。

### 2.2 卡片图推荐

| 方案 | 评价 |
|---|---|
| **A. 纯文字卡（不配图）** | ✅ **推荐**。理由：① 配方级图 0 张；② 一页内 2–4 张卡若都配"同剂型图"会**同一张图重复 4 次**；③ 配图会把卡片从 ~150px 抬到 ~350px，与刚做完的 Hero 瘦身方向相反 |
| B. 复用剂型图（8 张） | ❌ 同页重复；且 liquids / dental-chews 无小尺寸变体 |
| C. 用 `use` 功效做**线性图标**（11 个 SVG） | ⭕ **后续推荐**。与站点既有 SVG 图标体系一致（`sf-claim__check`、`.sf-formula__icon` 等），零位图依赖、可正常翻译。本批可先只做文字 chip |
| D. CPT 特色图（`has_post_thumbnail()`） | ⭕ 作为**渐进增强**：后台可传图则出图，未传则不出图 → 零强制素材 |

**建议组合：A + D**（默认纯文字卡；后台传了特色图才出图），视觉差异化交给 C 的图标（下一批）。

---

## 3. WordPress CPT 基础设施现状

### 3.1 结论：**绿地**（greenfield）

| 能力 | 现状 |
|---|---|
| `register_post_type` | **0 处** |
| `register_taxonomy` | **0 处** |
| `register_rest_field` / `show_in_rest` | **0 处** |
| `add_meta_box` / `register_meta` / `register_post_meta` | **0 处** |
| **ACF 或任何字段插件** | **无**（`grep acf_` → 0） |
| 自定义字段用法 | **1 处在用**：`get_post_meta($post_id, 'sf_last_reviewed', true)`（functions.php:1410、2056）。**⚠️ 该字段没有任何 `register_post_meta()` / `add_meta_box()`**，靠 WP 内置「自定义字段」面板写入（`postmeta` 表有 6 行数据）⇒ **没有现成的 meta 注册写法可照抄**，批次 2A 的 4 个 meta 将是本主题首次 `register_post_meta()` |
| `register_block_pattern` | **10 个**（`sinofresh/*`，functions.php:317–）→ 有「在 PHP 里用代码产出结构化内容」的先例 |
| shortcode | **3 个在用的先例**（见 3.2） |
| `WP_Query` / `get_posts` | 2 处（相关文章），`post_type => 'post'` |

### 3.2 三个 shortcode 先例（**这就是要照抄的模板**）

| shortcode | 函数 | 关键做法 |
|---|---|---|
| `[sf_explore_chips]` | `sinofresh_explore_chips()` L204 | `get_pages(['parent'=>19, 'sort_column'=>'menu_order'])` — **父页 ID 19 = Products**；用 `get_queried_object_id()` 标记 `aria-current` |
| `[sf_archive_count]` | 匿名函数 L238 | 读 `$wp_query->found_posts`；`_n()` 单复数 |
| `[sf_blog_chips]` | `sinofresh_blog_chips()` L265 | **自撑容器**（自己写 flex 内联样式的 `<div class="wp-block-buttons sf-blog-chips">`），因为「per-instance 的 `wp-container-core-buttons-is-layout-…` 哈希类 shortcode 无法复现」 |

三处 docblock 明确记录了**执行时机**（已实测复核）：

> `wp-includes/block-template.php:262` → `$content = do_shortcode( $content );`
> 紧接着 L291/L294 → `$content = do_blocks( $content );`
> 即 **`do_shortcode()` 在区块解析之前**跑完；`wp:html` 块内的裸 shortcode 无需额外接线即可解析。

**→ 对本次设计的硬约束**：
1. shortcode 无法依赖 `wp:columns` / `wp:group` 的布局支撑类（WP 不会为 shortcode 产出的 HTML 生成 `wp-container-core-*`）→ **卡片网格必须自撑容器 CSS**（照 `sf_blog_chips` 的既定做法）。
2. shortcode 输出**仍会被 `render_block`(core/html) 过滤器看到** → `{{...}}` 占位符引擎对它同样生效（可用，但**不要**在配方文案里出现 `{{`）。
3. `get_the_block_template_html()` 后续还有 `wptexturize()`（L297）→ 配方文案会经智能引号/破折号处理，与现有模板行为**一致**（现有值已在受同一处理），但**插值必须 `esc_html()`**，否则 `&` 会产出非法 HTML。

### 3.3 环境事实（影响设计）

| 项 | 值 |
|---|---|
| WP | **7.1.1** |
| 主题类型 | 块主题（FSE），`theme.json` v2，`layout: contentSize 1200 / wideSize 1440` |
| `customTemplates` / 自定义 `templateParts` | 均**未声明** → `templates/*.html` **自动注册**，加 CPT 模板**不需要**动 theme.json |
| 固定链接 | `/%postname%/` |
| 首页 / 文章页 | `page_on_front = 11`、`page_for_posts = 31` |
| **TranslatePress** | **3.3.6 Business（license valid）已启用**；语言 = **en_US（默认，根路径）+ zh_CN（`/zh/`）**；`force-language-to-custom-links: yes`、`add-subdirectory-to-default-language: no` |
| TranslatePress 相关表 | `wp_trp_dictionary_en_us_zh_cn`、`wp_trp_original_strings`、`wp_trp_original_meta`、`wp_trp_slug_originals`、`wp_trp_slug_translations` 等 10 张 |
| `trp_post_type_base_slug_translation` / `trp_taxonomy_slug_translation` | **当前均为空数组** → 新 CPT 的归档 slug 若需本地化，要往这里注册 |
| SEO pack 插件 | `trp_seopack_version 1.4.6` 已启用 |

> ⚠️ **TranslatePress 是本次的"隐形第三套渲染层"**：它按**运行时渲染结果**抓字符串（`disable_dynamic_translation: no`）。CPT 的标题/配料文字只要**前台渲染出来**就能被翻译，但：
> ① 迁移后必须让它重新收录这些串（否则 zh 站是英文）；
> ② 详情页新增的 URL 需要 slug 翻译或至少确认它出现在 sitemap / hreflang 里；
> ③ 它会把**动态内容**写进 `wp_trp_original_strings`，所以「改文案 → 影响翻译记忆」是必然的（与既有 FAQ 改文案同理）。

---

## 4. `section.sf-formulas` 的 DOM 结构与替换范围

### 4.1 现状结构（8 页 100% 同构，全部起于模板第 58 行）

```
<!-- wp:group {"tagName":"section","anchor":"formulas","className":"sf-formulas","layout":{"type":"constrained"},
                "style":{"spacing":{"padding":{"top":spacing-80,"bottom":spacing-80}}}} -->
<section id="formulas" class="wp-block-group sf-formulas" style="padding-top:…80;padding-bottom:…80">
  <!-- wp:heading -->                          ← <h2>Standard Formulas</h2>
  <!-- wp:paragraph {"textColor":"text-secondary"} -->   ← 引导句 "Proven recipes from our existing OEM production…"
  <!-- wp:html --> <details class="sf-formula__item"> … </details> <!-- /wp:html -->   × N
  <!-- wp:html --> <script type="application/ld+json">{"@type":"ItemList",…}</script> <!-- /wp:html -->
</section>
<!-- /wp:group -->
```

单个 `<details>` 的内部结构（**同时是 JS 契约**）：

```html
<details class="sf-formula__item">
  <summary>
    <span class="sf-formula__head">
      <span class="sf-formula__name">Liquid Joint Support</span>
      <span class="sf-formula__use">Joint care</span>
    </span>
    <span class="sf-formula__icon" aria-hidden="true"></span>
  </summary>
  <div class="sf-formula__body">
    <h4 class="sf-formula__label">Ingredients</h4>
    <p class="sf-formula__value">Glucosamine Sulfate, MSM, …</p>      ← label 的 nextElementSibling
    <h4 class="sf-formula__label">Guaranteed Analysis</h4>
    <p class="sf-formula__value">Glucosamine ≥1600mg/oz, …</p>
    <h4 class="sf-formula__label">Standard Specs</h4>
    <p class="sf-formula__value">8oz/16oz/32oz pump bottle · 24 months shelf life</p>
    <button type="button" class="sf-formula__cta" data-formula="Liquid Joint Support">Reference this formula →</button>
  </div>
</details>
```

运行时探针实测（`tools/_sf_formula_probe.js`）：

| 页 | 配方数 | 折叠合计高 | 区块 top / 高 | label 数 | label→兄弟值合法 | `<img>` 数 | `.sf-formula__cta` |
|---|---:|---:|---|---:|---|---:|---|
| soft-chews@1440 | 4 | 209px | 645 / **440px** | 3×4 | ✅ 4/4 | 0 | ✅ |
| tablets@1440 | 3 | 157px | 645 / **378px** | 3×3 | ✅ 3/3 | 0 | ✅ |
| liquids@1440 | 2 | 105px | 645 / **316px** | 3×2 | ✅ 2/2 | 0 | ✅ |
| fish-oil@1440 | 2 | 105px | 645 / **316px** | 3×2 | ✅ 2/2 | 0 | ✅ |

页面在 1440 下有 **6 个 `<h2>`**（TOC 契约，见 §8.1）。

### 4.2 替换范围

| 项 | 现状 | 替换后 |
|---|---|---|
| 模板内区块数 | `h2` + 引导句 + **N 个 `wp:html`(details)** + **1 个 `wp:html`(ItemList)**（soft-chews 共 5 个 `wp:html`） | `h2` + 引导句 + **1 个 shortcode** |
| **建议**：`h2` + 引导句**保留在模板** | — | 保住 TOC 契约（`#sf-sec-0` 的 id/label 完全不变），零风险 |
| 8 页区块字节 | 26,085 B | **6,358 B**（−19,727 B，−75.6%） |
| 删掉的 `wp:html` 块 | 29 个（21 details + 8 ItemList） | 0 |

逐页瘦身：

| 页 | 现字节 | 替换后 | 省 | 原 `wp:html` 数 |
|---|---:|---:|---:|---:|
| soft-chews | 4,714 | 797 | −3,917 | 5 |
| tablets | 3,720 | 794 | −2,926 | 4 |
| powders | 3,520 | 794 | −2,726 | 4 |
| pastes | 2,619 | 793 | −1,826 | 3 |
| drops | 2,512 | 792 | −1,720 | 3 |
| liquids | 2,688 | 794 | −1,894 | 3 |
| fish-oil | 2,619 | 795 | −1,824 | 3 |
| dental-chews | 3,693 | 799 | −2,894 | 4 |
| **合计** | **26,085** | **6,358** | **−19,727** | **29** |

### 4.3 `ItemList` JSON-LD 现状 —— **模板硬编码 + 已存在 3/21 条实体泄漏**

**生成方式**：`functions.php` **完全不生成 ItemList**（`grep ItemList functions.php` → 0）。它是**逐页硬编码在模板 `wp:html` 块里**的，例如 liquids：

```html
<script type="application/ld+json">{"@context":"https://schema.org","@type":"ItemList","name":"Standard Formulas — Liquids","itemListElement":[{"@type":"ListItem","position":1,"name":"Liquid Joint Support"},{"@type":"ListItem","position":2,"name":"Liquid Skin &amp; Coat"}]}</script>
```

⚠️ **实测缺陷**：`<script>` 是 raw text 节点，**HTML 实体不会被解码** → `json.loads()` 后名字变成 `Liquid Skin &amp; Coat`。Google 会读到带 `&amp;` 的产品名。

| 页 | ItemList 条数 | 受影响条目 |
|---|---:|---|
| soft-chews | 4 | `Skin &amp; Coat Soft Chews` |
| tablets | 3 | `Calcium &amp; Phosphorus Tablets` |
| liquids | 2 | `Liquid Skin &amp; Coat` |
| 其余 5 页 | — | — |
| **合计** | 21 | **3 条** |

**交接给 shortcode 的收益**：shortcode 用 `wp_json_encode()` 生成 → 输出**裸 `&`**，既合法 JSON 又文本正确 → **顺手修掉这 3 条**。同时必须保住 `name` 值 `Standard Formulas — <Dosage Form 首字母大写>` 与 `position` 1..N 的既有形状。

其余 4 个 JSON-LD（`FAQPage` / `BreadcrumbList` / `Product` / `Organization`）**全部由 `functions.php` 生成**，与本次改动无直接冲突，但**详情页需要新增分支**（见 §6.4）。

---

## 5. 详情页模板现状

### 5.1 现有模板清单（`templates/`，25 个文件）

| 类别 | 文件 |
|---|---|
| 通用 | `index.html` `home.html` `front-page.html` `single.html` `archive.html` `search.html` `404.html` |
| 页面 | `page.html` + 16 个 `page-{slug}.html`（含 8 个剂型页） |
| **无** | ❗**没有任何 `single-*.html` / `archive-*.html` 变体** |

### 5.2 CPT 模板 fallback 路径（WP 7.1.1 实测核对 `wp-includes/block-template-utils.php:1603` `get_template_hierarchy()`）

对 CPT `sf_formula`（`rewrite.slug = formulas`）：

| 视图 | 解析顺序 |
|---|---|
| **单篇** | `single-sf_formula-{slug}.html` → **`single-sf_formula.html`** → `single.html` → `singular.html` → `index.html` |
| **归档** | `archive-sf_formula.html` → `archive.html` → `index.html` |

**两个直接结论**：
1. **块主题下新增 CPT 模板不需要在 theme.json 注册** —— 放 `templates/` 下即自动生效（与页面模板同机制）。
2. ⚠️ **`single.html` 已存在**：这是**兜底**，也是**错版风险** —— 忘建 `single-sf_formula.html` 时，配方详情页会套用**博客文章版式**（`post-terms` 分类 + `post-date` + 分享行 + `Related Articles` 查询），不是报错而是"看起来能跑但其实错了"。**详情页模板属必做项，不是可选项。**

### 5.3 可复用性：`single.html` 是**高价值蓝本**

`single.html`（150 行）已经是「A 型详情页」的完整骨架，可直接剪裁：

| 区 | `single.html` 现状 | 配方详情页复用处 |
|---|---|---|
| Hero 段 | breadcrumb（`sf-breadcrumb--d3`）→ `post-terms` → `post-title`(h1) → 元信息行 | ✅ 面包屑 + h1(配方名) + `use` chip + 剂型归属 |
| 面包屑 | 含占位符 `{{MID_HREF}}` / `{{MID_CRUMB}}` / `{{TITLE}}` | ⚠️ **需要多一级**（Home / Products / 剂型 / 配方名）→ 现有占位符引擎只有**一层中间级**，需扩 |
| 正文 | `sf-single-body` → `sf-single-cover-wrap`(特色图 16/9) → 800px 容器 → `post-content` | ✅ 换成「三字段规格块 + 可选长描述」 |
| 前后导航 | `sf-prevnext`（`post-navigation-link`） | ⭕ 可复用为**同剂型内上一/下一配方** |
| 相关 | `sf-related` + `wp:query`(perPage 3, postType post) → **改 `postType: sf_formula` + 同剂型过滤** | ✅ 直接可用 |
| CTA | `Ready to Launch Your Product?` + `Request a Quote` → `/contact/` | ✅ 原样保留 |
| 页脚 | `template-part footer` | ✅ |
| 内联脚本 | 读字数算 `1 min read` | ❌ 删除（配方页不需要） |

### 5.4 占位符引擎（**必须扩展**）

`functions.php:1403 sinofresh_template_placeholders()` + `add_filter('render_block', …)`（L1446）：

- 只处理 `core/html` 块中含 `{{` 的内容
- `$post_id = is_singular('post') ? …` ← **CPT 下为 false** → `{{LAST_UPDATED}}` 等元信息会静默失效
- 已支持：`{{TITLE}}` `{{ARCHIVE_TITLE}}` `{{MID_HREF}}` `{{MID_CRUMB}}` `{{LAST_UPDATED}}` `{{SHARE_URL}}` `{{SHARE_URL_ENC}}` `{{SHARE_TITLE_ENC}}`
- `{{TITLE}}` 用 `get_the_title()` → **对 CPT 天然可用**

→ 详情页所需的**新增占位符建议**：`{{FORM_CRUMB}}` / `{{FORM_HREF}}`（由 `sf_formula_form` 项映射到剂型页）。

---

## 6. 建议方案

### 6.1 CPT 字段设计（原生 meta，无 ACF）

**Post type key：`sf_formula`**（沿用 `sf_` 前缀，与 `sf_last_reviewed` / `sf_explore_chips` 同一命名族）

```php
register_post_type('sf_formula', array(
  'labels'        => array( /* Formula / Formulas */ ),
  'public'        => true,
  'has_archive'   => true,
  'menu_icon'     => 'dashicons-clipboard',
  'menu_position' => 21,
  'supports'      => array('title', 'editor', 'thumbnail', 'excerpt',
                           'revisions', 'page-attributes', 'custom-fields'),
  'taxonomies'    => array('sf_formula_form', 'sf_formula_use'),
  'rewrite'       => array('slug' => 'formulas', 'with_front' => false),
  'show_in_rest'  => true,     // 块编辑器 + TranslatePress + REST 都需要
  'hierarchical'  => false,
));
```

**`supports` 的选择理由**

| support | 为什么 |
|---|---|
| `title` | 配方名（= H1 = ItemList 的 name = `data-formula`） |
| `editor` | **详情页长描述**（可选）：工艺说明、适用场景。列表页不取正文 |
| `thumbnail` | 特色图（§2.2 方案 D 的渐进增强） |
| `excerpt` | 卡片副文案（可选；未填则回落到 Standard Specs） |
| `revisions` | 配方是合规物料，需留改动痕迹 |
| `page-attributes` | 提供 `menu_order` → **排序用它，不再自造 `sf_formula_order`** |
| `custom-fields` | 便于后台临时核对 meta |

**Meta 字段（`register_post_meta`，`show_in_rest` + `auth_callback`）**

| meta key | 类型 | 说明 | 与现状对应 |
|---|---|---|---|
| `sf_formula_ingredients` | `string` | 完整配料表（**单行、逗号分隔，与现状逐字一致**） | `Ingredients` 值 |
| `sf_formula_analysis` | `string` | 保证值 | `Guaranteed Analysis` 值 |
| `sf_formula_specs` | `string` | 规格（含 `·` 分隔的包装/保质期） | `Standard Specs` 值 |
| `sf_formula_source` | `string` | 迁移来源锚：`<剂型slug>#<序号>`（便于回滚与对账） | 新增（非展示） |

**三个"价值字段"刻意保持单行字符串**，理由：
1. 与现状**逐字一致** → 迁移可做**字节级对账**（改成分行数组会引入不可见差异）；
2. 这些是"配方事实"，不是自由排版 → 结构化到数组反而增加后台录入摩擦；
3. `≥` / `·` / `%` / `(43%)` 这类符号原样保留，**不做任何归一化**。

> ⚠️ **不要**把这三个字段塞进 `post_content`：`wptexturize` / `wpautop` 会改写排版（`--` → `–`、连续空格、换行→`<p>`），破坏与现状的字节对账。

### 6.2 分类法设计（2 个）

#### ① `sf_formula_form` —— 剂型归属（**必做，taxonomy**）

| 项 | 值 |
|---|---|
| 复用为 | 剂型归属（soft-chews / tablets / …，8 个项） |
| `hierarchical` | `false` |
| **`public`** | **`false`** ← 关键 |
| `show_ui` / `show_in_rest` | `true` / `true` |
| `rewrite` | **不设**（`public:false` 下不产生前台归档） |
| term slug | **与剂型页 slug 完全对齐**（`soft-chews`…`dental-chews`）→ 可零成本映射到页面 URL |

**为什么必须用 taxonomy 而不是 meta**：① 列表页要按剂型过滤（`tax_query` 比 `meta_query` 走 `term_relationships` 索引，更快）；② 后台可加筛选器；③ TP 有 `trp_taxonomy_slug_translation` 通道。

**为什么 `public: false`**：8 个剂型**已经有页面**（`/products/soft-chews/`，page ID 20–27）。若把 taxonomy 设为 public，会再生成 `/<taxonomy>/soft-chews/` 归档，与页面**内容重复 + 制造 URL 竞争**。关掉前台归档，只留后台管理能力。

#### ② `sf_formula_use` —— 功效分类（**建议做，taxonomy**）

| 项 | 值 |
|---|---|
| 值 | **11 个**：Joint care / Skin & coat / Digestive care / Daily nutrition / Urinary care / Oral care / Calming / Bone health / Hairball control / Ear care / Plaque control |
| `hierarchical` | `false` |
| **`public`** | **`false`**（同理由：避免与剂型页/未来分类页冲突） |
| `show_ui` / `show_in_rest` | `true` / `true` |
| term slug | `joint-care` `skin-coat` `digestive-care` `daily-nutrition` `urinary-care` `oral-care` `calming` `bone-health` `hairball-control` `ear-care` `plaque-control` |

**为什么用 taxonomy 而不是一个 `select` meta**：Skin & coat（4）/ Joint care（3）/ Digestive care（3）**跨剂型聚合**，这是站点唯一现成的"按功效浏览"维度；将来做 `/formulas/?use=joint-care` 或聚合页时，taxonomy 是零改造成本，meta 则要重建。

**若本轮明确不做按功效聚合** → 可降级为 `select` meta（`sf_formula_use`，取值白名单 11 项），少 1 个 taxonomy。**这是一个待裁定点（见 §9-Q3）。**

### 6.3 shortcode 设计与**必须守住的 DOM 契约**

**名称：`[sf_formula_grid]`**

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `form` | string | **当前页 slug**（`is_page()` 时取 `post_name`） | 剂型过滤；显式传入可跨页复用 |
| `use` | string | 空 | 功效过滤（`sf_formula_use` term slug） |
| `limit` | int | `-1` | 条数上限 |
| `columns` | int | `4` | 桌面列数（仅影响 `--sf-fgrid-cols`） |
| `cta` | enum | `reference` | `reference`＝保现状（复制配方名 + 滚到 `#configurator`）；`link`＝跳详情页 |
| `links` | bool | `true` | 卡片标题是否链接到详情页 |
| `empty` | enum | `hide` | 无结果时：`hide`（整块不输出）/ `text`（输出提示句） |

**必须守住的 DOM / 数据契约（4 条，缺一即静默回归）**

| # | 契约 | 谁依赖 | 处置 |
|---|---|---|---|
| K1 | 卡片主按钮保留 `class="sf-formula__cta"` + `data-formula="<配方名>"` | `formulas.js:67-70`（复制名 + `sessionStorage['sinofresh_formula_<页slug>']` + 滚 `#configurator`） | **原样保留**（类名/属性不改 → `formulas.js` 零改动） |
| K2 | 页面上仍有 `.sf-formula__item` / `.sf-formula__name` / `.sf-formula__label` 且 label 的 `nextElementSibling` 是值节点 | `configurator.js:637-642` `readFormula()`（PDF 摘要的 "Standard formula" 段） | ⚠️ **卡片化后三字段移入详情页，此结构在列表页消失** → 见 §8.2 的两种方案 |
| K3 | 卡片标题若是 h2 会**顶掉 TOC 序号** | `toc-nav.js:84 collectH2s`（`#sf-sec-N` 按 h2 顺序注入） | **卡片标题一律 `h3`**；`h2` 仍只由模板出 1 个 |
| K4 | `<script>` 内 JSON 不得含 HTML 实体 | Google 结构化数据 | shortcode 用 `wp_json_encode()`（输出裸 `&`）→ 顺手修掉 §4.3 的 3 条 |

**输出形状（建议）**

```html
<!-- 由 shortcode 输出，自撑容器（不依赖 wp-container-core-*） -->
<div class="sf-fgrid" style="--sf-fgrid-cols:4">
  <script type="application/json" class="sf-formulas-data">
    [{"name":"Liquid Joint Support","use":"Joint care","form":"liquids",
      "ingredients":"…","analysis":"…","specs":"…","url":"/formulas/liquid-joint-support/"}, …]
  </script>
  <script type="application/ld+json">{"@context":"https://schema.org","@type":"ItemList","name":"Standard Formulas — Liquids","itemListElement":[…]}</script>
  <article class="sf-fcard">
    <span class="sf-fcard__use">Joint care</span>
    <h3 class="sf-fcard__name"><a href="/formulas/liquid-joint-support/">Liquid Joint Support</a></h3>
    <p class="sf-fcard__spec">8oz/16oz/32oz pump bottle · 24 months shelf life</p>
    <div class="sf-fcard__actions">
      <a class="sf-fcard__more" href="/formulas/liquid-joint-support/">View formula →</a>
      <button type="button" class="sf-formula__cta" data-formula="Liquid Joint Support">Reference this formula →</button>  <!-- K1 -->
    </div>
  </article>
  …
</div>
```

> `sf-formulas-data` 这个 JSON 块是 §8.2 的 **K2 解法载体**：把三字段以机器可读形式随卡片一起输出，`configurator.js` 改为优先读它、回落到旧 DOM 抓取 → **旧结构消失也不丢功能，且不再依赖 DOM 形状**。

### 6.4 详情页模板设计

**新建 `templates/single-sf_formula.html`**（必需），结构：

| 顺序 | 区块 | 来源 |
|---|---|---|
| 1 | `template-part header` | 复用 |
| 2 | Hero 段（`primary` 底）：面包屑 `Home / Products / {剂型} / {配方名}` → `sf-fcard__use` chip → `<h1>` 配方名 → 一行"剂型 + 起订量"→ 2 按钮（`Reference this formula`〔`cta` 橙实心〕/ `Build Custom Formula`〔描边〕） | 剪裁 `single.html` Hero |
| 3 | 规格段（白底）：三字段卡片（Ingredients / Guaranteed Analysis / Standard Specs），沿用现有 `.sf-formula__label` / `.sf-formula__value` 的视觉 | 现有 CSS 可留 |
| 4 | 正文（可选）：`post-content`（工艺说明等），800px 容器 | `single.html` |
| 5 | 同剂型其他配方：`wp:query {postType: sf_formula}` + `tax_query sf_formula_form = 当前剂型`，`perPage 4`，复用 `.sf-tile`/卡片 | 改自 `single.html` 的 `sf-related` |
| 6 | CTA 段：`Ready to Launch Your Product?` + `Request a Quote` → `/contact/` | 原样 |
| 7 | `template-part footer` | 复用 |

**配套的 `functions.php` 改动（详情页运行所必需）**

| 改动 | 位置 | 为什么 |
|---|---|---|
| `sinofresh_template_placeholders()`：`$post_id` 判定加 `sf_formula` | L1406 | 否则 CPT 页 `{{LAST_UPDATED}}` 等静默失效 |
| 新增 `{{FORM_CRUMB}}` / `{{FORM_HREF}}` | L1433 `$map` | 面包屑多一级（剂型） |
| **BreadcrumbList JSON-LD 的模板候选列表**加分支 | L1465 附近 `if (is_singular('post'))` | 该生成器按视图类型解析模板文件 → 不加分支时详情页拿不到 `single-sf_formula`，面包屑结构化数据会缺/错 |
| （可选）`toc-nav.js` enqueue 条件加 `is_singular('sf_formula')` | L40 | 详情页若 ≥3 个 h2 才需要；建议**先不加**（配方页信息密度低，dot-rail 反而干扰） |
| （可选）详情页 `Product` JSON-LD | 新增 | 见 §9-Q4 |

**`archive-sf_formula.html`**（建议做，非必需）：不做则 `/formulas/` 回落到 `archive.html`（博客式列表 + `post-terms` 分类 + 日期），**观感不符**。建议做一个极简归档：h1 + 按剂型分组的卡片网格（直接复用同一 shortcode，传 `form=""` 出全部 21 条）。

### 6.5 数据迁移脚本思路

**工具：`tools/_sf_formula_migrate.php`（新建），通过 WP 引导运行，不用裸 SQL。**

```
阶段 1  抽取（只读）
  · 复用 tools/_sf_cpt_scan.py 的正则，或直接在 PHP 里 parse 8 个模板
  · 产出 21 条记录，逐条带「来源锚」<剂型slug>#<序号>
  · 门禁：每条必须有 name/use/三字段；总数必须 == 21

阶段 2  干跑（不写库）
  · 计算 post_name = sanitize_title(name)（已预检：21/21 唯一，最长 30 字符）
  · 打印「将创建 / 将更新 / 冲突」三类清单
  · 门禁：冲突数 == 0；新建 == 21（首跑）

阶段 3  写入（幂等）
  · 按 post_name 查找已有 sf_formula：存在 → wp_update_post，不存在 → wp_insert_post
  · post_status = publish；menu_order = 页内序号（1..N）
  · update_post_meta × 3（ingredients / analysis / specs）+ sf_formula_source
  · wp_set_object_terms：sf_formula_form = 剂型 slug；sf_formula_use = use slug
  · 门禁：三次写入后逐条回读，与阶段 1 抽取结果**逐字符比对**

阶段 4  对账（DB → 渲染）
  · 清 rewrite 规则（flush_rewrite_rules）
  · 抓 8 个剂型页，从渲染 HTML 反抽 21 条，与阶段 1 的 JSON **deep-equal**
  · 抓 21 个详情页（/formulas/<slug>/）确认 200 且三字段齐全
  · ItemList 逐页比对（含验证 §4.3 的 3 条 `&amp;` 已修正）

阶段 5  回滚准备
  · 备份 8 个模板 + functions.php + style.css
  · 记录 21 个 post ID + 3 个 meta 的值 → 可精确回退（wp_delete_post 或改 status 为 draft）
```

**21 个 `post_name` 预检结果（已算好）**

| 剂型 | 配方名 | `post_name` | use slug |
|---|---|---|---|
| soft-chews | Joint Support Soft Chews | `joint-support-soft-chews` | `joint-care` |
| soft-chews | Calming Soft Chews | `calming-soft-chews` | `calming` |
| soft-chews | Digestive Soft Chews | `digestive-soft-chews` | `digestive-care` |
| soft-chews | Skin & Coat Soft Chews | `skin-coat-soft-chews` | `skin-coat` |
| tablets | Joint Support Tablets | `joint-support-tablets` | `joint-care` |
| tablets | Multivitamin Tablets | `multivitamin-tablets` | `daily-nutrition` |
| tablets | Calcium & Phosphorus Tablets | `calcium-phosphorus-tablets` | `bone-health` |
| powders | Probiotic Powder | `probiotic-powder` | `digestive-care` |
| powders | Pumpkin Digestive Powder | `pumpkin-digestive-powder` | `digestive-care` |
| powders | Bladder Support Powder | `bladder-support-powder` | `urinary-care` |
| pastes | Hairball Remedy Paste | `hairball-remedy-paste` | `hairball-control` |
| pastes | Nutrition Paste | `nutrition-paste` | `daily-nutrition` |
| drops | Ear Care Drops | `ear-care-drops` | `ear-care` |
| drops | Urinary Care Drops | `urinary-care-drops` | `urinary-care` |
| liquids | Liquid Joint Support | `liquid-joint-support` | `joint-care` |
| liquids | Liquid Skin & Coat | `liquid-skin-coat` | `skin-coat` |
| fish-oil | Wild Alaskan Salmon Oil | `wild-alaskan-salmon-oil` | `skin-coat` |
| fish-oil | Pure Fish Oil Blend | `pure-fish-oil-blend` | `skin-coat` |
| dental-chews | Plaque Control Dental Chews | `plaque-control-dental-chews` | `plaque-control` |
| dental-chews | Oral Care Dental Sticks | `oral-care-dental-sticks` | `oral-care` |
| dental-chews | Natural Cleaning Dental Sticks | `natural-cleaning-dental-sticks` | `oral-care` |

**唯一性：✅ 21/21 唯一**（注意 `Skin &` → `-`，`&` 被丢弃，因此 `skin-coat-soft-chews` 而非 `skin-amp-coat-…`）。**与现有 slug 冲突检查：无**（现有 `page/soft-chews` 等 9 个 slug 与这 21 个均不重合）。

**迁移后必做**：让 TranslatePress **重新收录**新串（否则 zh 站显示英文）。做法：访问 `settings → TranslatePress → 翻译编辑`（或触发它自己的字符串扫描），确认 21 个配方名 + 63 个字段值进入 `wp_trp_original_strings`。

### 6.6 URL 结构建议（含"为什么不能嵌套"）

**推荐：`/formulas/<slug>/`**

| 项 | 值 |
|---|---|
| 单篇 | `/formulas/liquid-joint-support/` |
| 归档 | `/formulas/` |
| 中文站 | `/zh/formulas/liquid-joint-support/`（TP 自动加前缀） |
| `rewrite` | `array('slug' => 'formulas', 'with_front' => false)` |

**为什么不建议你提的第二方案 `/products/soft-chews/joint-support/`**

三条硬事实：

1. **单个 CPT 只能有一个 `rewrite.slug`** —— 21 个配方分属 **8 个不同剂型**，要让前缀各自不同，只能注册 8 个 CPT（不可维护）或写自定义 `rewrite_rules` + `post_type_link` 过滤器（脆弱、每次改结构都要重写规则）。
2. **嵌套在页面下不是 WP 原生能力** —— `/products/soft-chews/` 是 **page**（ID 20），不是 taxonomy term；WordPress 没有"CPT 归属页面"的原生机制。
3. **前缀设成 `products` 会与页面子树打架** —— `/products/<formula-slug>/` 与 `/products/soft-chews/` 同处一个前缀，解析靠 rewrite 规则优先级，**任何一侧新增页面都可能改变归属**；且 `/products/`（page）会与 CPT 归档争同一个 URL。

**另有一个可接受的变体（可选）**：`rewrite.slug = 'products/formulas'` → `/products/formulas/<slug>/`。因为 `/products/formulas/` 与现有 9 个页面**都不冲突**，能保留"隶属于 Products"的语义。代价：需要 `flush_rewrite_rules` 后逐条验证与页面子树的解析优先级。**若你要这个语义，我按变体做并在核验里加"21 条 URL 与 9 个页面 URL 无冲突且解析正确"的断言。**

> **slug 本身已自描述剂型**（`liquid-joint-support` / `plaque-control-dental-chews`）→ 扁平 URL 不丢失上下文。

**与锚点 `#formulas` 的关系**：剂型页里的区块 id 是 `#formulas`（fragment），与路径 `/formulas/`（path）**不在同一命名空间，不冲突**。

### 6.7 卡片网格的列数与高度预算

**实测基准**（`tools/_sf_formula_probe.js`）：

| 项 | 1440 桌面 | 375 移动 |
|---|---|---|
| 现有 `.sf-dosage-grid`（Related）列宽 | **282px × 4 列**（gap 24px） | 142.5px × 2 列 |
| 现有 `.sf-tile` 卡片高（带 1:1 图） | **350px** | 312px |
| `sf-formulas` 区块现高 | soft-chews **440** / tablets 378 / liquids 316 | 442 / 383 / 295 |

**建议**：`grid-template-columns: repeat(var(--sf-fgrid-cols, 4), minmax(0, 1fr))` + `gap: 24px`，**与 `.sf-dosage-grid` 完全一致的轨道尺寸** → 卡片 282px，视觉秩序与既有目录页一致。

**高度影响（诚实交代）**：

| 页 | 区块现高（手风琴） | 卡片化预估 | Δ |
|---|---:|---:|---:|
| soft-chews | 440 | ~581（48 + h2 + 24 + 引导句 + 24 + 卡片 ~350 + 48） | **+141** |
| tablets | 378 | ~581 | +203 |
| liquids | 316 | ~581 | +265 |

⚠️ **必须让你知道**：卡片化会让该区块**变高**（手风琴折叠态最省高度，卡片必然展开）。用 **纯文字卡**（不配图，卡片 ~150–180px 而非 350px）可把增量压到 **+30～+80px**；若配 1:1 图则回到 +141～+265px。

**与步骤 2 的净账**：Hero 刚减 **−398px**（726→328），本步若用纯文字卡 +30～+80 → **整页仍净减 318～368px**。这正好支持 §2.2 选"纯文字卡"。

**2 张卡的页（pastes/drops/liquids/fish-oil）在 4 列轨道里会有 2 个空列** —— 与 `.sf-dosage-grid` 的既定观感一致（固定轨道、左对齐），**不建议**用 `auto-fit` 让 2 张卡各自撑到 588px（会显得像 banner 而非卡片）。**这是一个待裁定点（见 §9-Q5）。**

---

## 7. 改动文件清单

| # | 文件 | 动作 | 内容 | 规模（估） |
|---|---|---|---|---|
| 1 | `sinofresh-theme/functions.php` | 改 | ① `register_post_type('sf_formula')` ② `register_taxonomy` × 2 ③ `register_post_meta` × 4 ④ `add_shortcode('sf_formula_grid')` ⑤ `sinofresh_template_placeholders()` 扩展（CPT `$post_id` + `{{FORM_CRUMB}}`/`{{FORM_HREF}}`） ⑥ BreadcrumbList 模板候选加 `is_singular('sf_formula')` 分支 ⑦ `sinofresh-formulas` enqueue 条件（详情页是否需 `formulas.js`） | +380～450 行 |
| 2 | `templates/page-{8}.html` | 改 | `section#formulas` 内 N 个 `wp:html`(details) + 1 个 `wp:html`(ItemList) → 1 个 `[sf_formula_grid form="…"]`；**保留 `h2` 与引导句** | 8 文件 / −19,727 B |
| 3 | `style.css` | 改 | ① 新增「37. Formula card grid」段（自撑容器 + 卡片 + 响应式）→ 约 +110 行 ② **删** 36 段手风琴选择器 ③ **保留** `.sf-toast` ④ **保留** `#configurator{padding-top}` | +110 / −129 行 |
| 4 | `templates/single-sf_formula.html` | **新建** | 配方详情页（§6.4） | ~120 行 |
| 5 | `templates/archive-sf_formula.html` | 新建（建议） | `/formulas/` 归档：按剂型分组的卡片网格 | ~60 行 |
| 6 | `assets/js/configurator.js` | 改 | `readFormula()` 改为**优先读 `.sf-formulas-data` JSON**、回落旧 `.sf-formula__item` DOM 抓取 | ~20 行 |
| 7 | `assets/js/formulas.js` | **不改** | `.sf-formula__cta` + `data-formula` 契约保持 → 零改动 | 0 |
| 8 | `theme.json` | **不改** | 块主题自动注册 `templates/`（已核对 `customTemplates: []` 不影响） | 0 |
| 9 | `tools/_sf_formula_migrate.php` | **新建** | 迁移脚本（§6.5，含干跑 + 对账 + 回滚准备） | ~260 行 |
| 10 | `_backup/formulas-cpt-<ts>/` | **新建** | 8 模板 + functions.php + style.css + 2 个 JS + 21 条数据的 JSON 快照 | — |
| 11 | `wp_options` / `wp_posts` / `wp_term_*` | DB 改 | 21 个 `sf_formula` + 2 taxonomy 项 + 63 条 meta + rewrite 规则刷新；**导航菜单（ID 16）可选加 `Formulas` 入口** | — |
| 12 | `screenshots/formulas-cpt/` | 新建 | 8 页卡片网格 + 21 个详情页截图 | — |

---

## 8. ⚠️ 三处必须处理的耦合（**本次扫描最重要的产出**）

### 8.1 `.sf-toast` 被 **4 个脚本**共用 —— 清理 36 段时**绝不能删**

`style.css` 36 段（L5563–5728，共 166 行）里混着**不属于配方手风琴**的共享资产：

| 行段 | 内容 | 处置 |
|---|---|---|
| 5563–5573 | 段头注释（11 行） | **改写** |
| **5574–5696** | `.sf-formulas*` / `.sf-formula__*` 选择器（123 行） | **可删** |
| **5697–5718** | **`.sf-toast` + `.sf-toast.is-visible`（22 行）** | **⛔ 保留** |
| 5719–5728 | `@media ≤768`：5720–5722 是 `.sf-formula__*`（可删）／**5726 `.sf-formulas{padding-bottom:0}`（区块类保留则保留）**／**5727 `#configurator{padding-top:32px}`（⛔ 保留，属配置器间距）** | 部分 |

**`.sf-toast` 的 4 个消费者**（实测 grep）：

```
assets/js/formulas.js:24        toastEl.className = 'sf-toast'
assets/js/configurator.js:506   document.querySelector('.sf-toast')   （PDF 段共用）
assets/js/toc-nav.js:148        toastEl.className = "sf-toast"
assets/js/basket.js:113         document.querySelector('.sf-toast')
+ style.css:7529                （另一处媒体查询里的 .sf-toast 规则）
```

> 与步骤 2 的 `.sf-slider-progress` **完全同类**的陷阱（那次是"别删首页共用的进度条"，这次是"别删 4 脚本共用的 toast"）。**删 CSS 段时必须以选择器为单位逐条判断，不能按行号整段切。**

### 8.2 `configurator.js readFormula()` 依赖 `.sf-formula__item` 的 DOM 形状

```js
// configurator.js:637-642
var items = document.querySelectorAll('.sf-formula__item');
   … items[i].querySelector('.sf-formula__name').textContent.trim() === name   // 用名字匹配
   … items[i].querySelectorAll('.sf-formula__label')                          // 三字段
        labels[j].nextElementSibling.textContent                              // label 的**相邻兄弟**才是值
```

**风险**：卡片化后三字段移入详情页 → 列表页**没有** `.sf-formula__item` / `.sf-formula__label` → 匹配失败 → 静默返回 `{name, sections: []}` → **PDF 摘要的 "Standard formula" 段只剩配方名、三个字段全丢**。**没有任何视觉表现，截图/几何回归都会"通过"。**

这与刚修完的 **Product JSON-LD 回归**是**同一类**问题（删 DOM 架构前未扫数据抽取依赖）。

**两个解法**

| 方案 | 做法 | 评价 |
|---|---|---|
| **A（推荐）** | shortcode 输出 `.sf-formulas-data` JSON（含 name + 三字段）；`readFormula()` **优先读 JSON**，失败时回落旧 DOM 抓取 | 一次改动永久解耦；旧结构消失也不丢功能；向后兼容 |
| B | 卡片里保留一套**不可见的** `.sf-formula__item`/`__label` 结构 | ❌ 用隐藏 DOM 欺骗消费方，后续维护者会当死代码删掉 |

**方案 A 附带收益**：详情页也能复用同一份 JSON 形状（`readFormula()` 在详情页天然可用，若将来详情页加配置器）。

### 8.3 `ItemList` 3/21 条实体泄漏（见 §4.3）

`Skin &amp; Coat Soft Chews` / `Calcium &amp; Phosphorus Tablets` / `Liquid Skin & Coat` —— 交给 shortcode 的 `wp_json_encode()` 顺手修正，**但必须在核验里加断言**（否则"顺手修"会变成"默默又错"）。

---

## 9. 待你裁定（5 项）

| # | 问题 | 我的建议 |
|---|---|---|
| **Q1** | CPT 的 `rewrite.slug`：`formulas`（扁平）还是 `products/formulas`（保留隶属语义）？ | **`formulas`** —— 零冲突风险；slug 已自描述剂型 |
| **Q2** | 卡片是否配图？ | **纯文字卡**（+ 特色图渐进增强）。让整页续减高度，且避免同页 4 张重复图 |
| **Q3** | `sf_formula_use` 用 taxonomy 还是 `select` meta？ | **taxonomy + `public:false`** —— 为"按功效浏览"留零成本升级位 |
| **Q4** | 详情页是否输出 `Product` JSON-LD？ | **输出，但只用 `additionalProperty`（三个 `PropertyValue`），不加 `offers`/`price`** —— 无价格时给 `offers` 会触发 Google 商家警告 |
| **Q5** | 2 张卡的页（pastes/drops/liquids/fish-oil）在 4 列轨道里留 2 个空列，还是让 2 张卡各自撑半宽？ | **留空列**（固定轨道、左对齐，与 `.sf-dosage-grid` 一致） |

---

## 10. 工具与证据索引

| 工具 | 用途 | 输出 |
|---|---|---|
| `tools/_sf_cpt_scan.py` | 21 个配方抽取 + 数量/`name≡data-formula`/`ItemList≡DOM` 三门禁 | `docs/scan-evidence-formulas-cpt-20260920/formulas.json` |
| `tools/_sf_img_scan.py` | uploads 全图尺寸/体积 + 语义分族 | `docs/scan-evidence-formulas-cpt-20260920/images.json` |
| `tools/_sf_formula_probe.js` | 运行时几何：TOC 契约 / 区块高度 / 卡片高度基准 / JS 契约 | `docs/scan-evidence-formulas-cpt-20260920/probe.json` |
| `tools/_sf_trp_probe.php` | TranslatePress 设置 + `wp_trp_*` 表 + 内容清单 | stdout（摘要见 §6.7） |

证据 JSON 已从 `/tmp/b1/cpt_scan/` 复制为仓库内持久副本 `docs/scan-evidence-formulas-cpt-20260920/`（4 文件，43 KB，非部署资产）。

**本次扫描未改动任何源码、未写 DB。**（`docs/` 与 `tools/` 均为非部署目录：`diff -rq` 显示它们 `Only in` 源码侧，不在站点根）
