# Batch 2D · Step 0 — 8 个剂型页现状扫描（只读，零改动）

> **范围**：`/products/soft-chews/`、`/tablets/`、`/powders/`、`/pastes/`、`/drops/`、`/liquids/`、`/fish-oil/`、`/dental-chews/`
> **目标**：为「产品详情页线」定基线，回答 13 类模块的存量、图片资源现状、配置器骨架、8 页差异、可复用资源。
> **性质**：本次为**只读扫描**。主题 `git status` 为空、工作区 commit 仍为 `c0308af`、临时装置已清。
> **核验双源**：模板真值 = `sinofresh-theme/templates/page-{slug}.html`（磁盘模板永远胜出 DB，见 §6.5）；
> 渲染真值 = 云端 `/products/soft-chews/`（173,737 B）+ 云端 uploads 目录清单。

---

## 0. TL;DR

1. **8 页共用同一套 10 块骨架**，顶层签名逐块一致（§1.2）。差异只在「块内文案/选项/条数」，不在结构。
2. **13 类模块里 5 类已有、2 类半有、6 类完全缺失**（§2）。缺的正好是「详细介绍 / 活性成分 / 保证值表 / 文献 / 图集」，以及独立的「样品申请」。
3. **活性成分 + 保证值表的数据 100% 已存在**：21 条配方 × 3 字段（Ingredients / Guaranteed Analysis / Standard Specs）全部非空，且已镜像进 K2 JSON（§7.1）。这是本批最便宜的两个模块。
4. **抽查 18 张图 100% 带 AI 水印**，且 `equip-placeholder` / `fac-placeholder` **是同一个场景抠出来的两张**、**同样带水印**（§3.3、§3.4）。水印多数落在画面内部 ⇒ CSS 裁切不可靠。「先用占位图做结构」在结构上可行，但**干净图片必须单列为上线阻塞项**。
5. **`.sf-spec-list` 是唯一现成但零引用的组件**：CSS 已定义、K6 的 Product JSON-LD 解析器在等它，**当前 8 个剂型页的 `additionalProperty` 是空的**（§6.3、§8.2）。用它与不用它都会留下后账，第 1 批方案里必须正面处理。
6. **配置器是整块裸 `wp:html`**（27,096 B，含 39 个 SVG 符号），摘要卡在右栏 `aside.configurator__summary`，不是 sticky（§4）。

---

## 1. 模板结构

### 1.1 文件与共用情况

| 项 | 值 |
|---|---|
| 文件 | `templates/page-{slug}.html` × 8（**一剂型一文件，不共用**） |
| 体积 | soft-chews 54,689 B／dental-chews 49,124 B／tablets 46,380 B／powders 45,832 B／liquids 44,673 B／drops 44,330 B／fish-oil 44,161 B／pastes 43,918 B |
| 顶层块数 | **10 块，8 页全等** |
| 文件头 | 第 1 行 `<!-- wp:template-part {"slug":"header","tagName":"header"} /-->`（自闭合，`/-->` 紧贴） |
| 文件尾 | `<!-- wp:template-part {"slug":"footer"} /-->` |

> ⚠ 8 个文件**没有共用模板**，也没有 `templates/page-products.html` 之外的中间层 → 任何「统一改动」都要落到 8 个文件上，
> 这也是第 1 批必须选 shortcode（而非复制 HTML）的技术理由之一（§6.2）。

### 1.2 顶层块签名（8 页一致，逐字相同）

| # | 块 | 关键属性 | 职责 |
|---|---|---|---|
| 0 | `template-part` self-close | `slug:header` | 导航 |
| 1 | `group` | `tagName:section` `className:sf-hero-inner` pad 80/80 | 标题区（面包屑 + H1 + 副标题 + 2 按钮） |
| 2 | `group` | `anchor:formulas` `className:sf-formulas` pad 80/80 | Standard Formulas：H2 + 导语 + `[sf_formula_grid]` + `Browse All Formulas →` |
| 3 | `group` | `tagName:section` 内嵌 `id="configurator"` pad 80/80 | 配置器（整块裸 `wp:html`） |
| 4 | `group` | `className:sf-spectable` pad 60/60 | 5 列参数表（**无标题**，见 §1.4） |
| 5 | `group` | `backgroundColor:bg-light` pad 80/80 | How We Work：7 步（`01`–`07`） |
| 6 | `group` | pad 80/80，内层 `className:sf-faq` | FAQ：H2 + `details.sf-faq__item` ×2–3 |
| 7 | `group` | `backgroundColor:bg-light` pad 80/80 | Related Dosage Forms：7 张兄弟剂型瓦片 |
| 8 | `group` | `anchor:inquiry-form` `backgroundColor:primary` pad 80/80 | 底部 CTA + `wp:gravityforms/form {"formId":"2","ajax":true}` |
| 9 | `template-part` self-close | `slug:footer` | 页脚 |

**读页顺序**：深色 hero → 白 → 白 → 白 → **浅底(How We Work)** → 白 → **浅底(Related)** → **深色(询价)**。
8 页背景/内边距**完全一致**（§5 表），节奏不存在页间漂移。

### 1.3 逐块字节数（同构性证据）

| # | soft-chews | tablets | powders | pastes | drops | liquids | fish-oil | dental-chews |
|---|---|---|---|---|---|---|---|---|
| 0/9 | 63 | 63 | 63 | 63 | 63 | 63 | 63 | 63 |
| 1 hero | 2,591 | 2,600 | 2,584 | 2,589 | 2,580 | 2,601 | 2,576 | 2,617 |
| 2 formulas | 1,054 | 1,051 | 1,051 | 1,050 | 1,049 | 1,051 | 1,052 | 1,056 |
| 3 config | **27,096** | 18,362 | 17,860 | 15,901 | 16,018 | 16,355 | 15,878 | 20,767 |
| 4 specs | 974 | 972 | 956 | 960 | 963 | 962 | 964 | 981 |
| 5 how-we-work | **8,064** | 8,064 | 8,064 | 8,064 | **8,524** | 8,524 | 8,524 | 8,524 |
| 6 faq | **1,558** | 1,993 | 1,964 | 1,994 | 2,095 | 2,086 | 2,083 | 2,106 |
| 7 related | 9,267 | 9,260 | 9,271 | 9,281 | 9,023 | 9,014 | 9,003 | 8,988 |
| 8 inquiry | 3,581 | 3,578 | 3,578 | 3,577 | 3,576 | 3,578 | 3,579 | 3,583 |

块 1/2/4/8 的字节差只是剂型名词长度（"Soft Chews" vs "Drops"）。**真正的页间分叉只有三处**：块 3（配置器选项）、块 5（两种写法）、块 6（FAQ 条数）。详见 §5。

### 1.4 模板内注释编号**不可信**（定位陷阱）

`page-soft-chews.html` 里只有 6 条块注释，编号是 `Block 2 / 4 / 9 / 10 / 11 / 12`：

| 注释写的 | 实际顶层序号 |
|---|---|
| `Block 2: Hero` | 1 |
| `Block 4: Configurator` | 3 |
| `Block 9: How We Work` | 5 |
| `Block 10: FAQ` | 6 |
| `Block 11: Related Dosage Forms` | 7 |
| `Block 12: CTA Inquiry Form` | 8 |

**编号来自上一代模板，删块后没重排**（块 1「Standard Formulas」、块 4「sf-spectable」没有注释）。
→ **禁止按注释编号定位**；一律按 `anchor`／`className`／H2 文本定位。
另：block template 的 HTML 注释**会输出到页面源码**，新增注释必须短。

---

## 2. 13 类模块盘点

图例：**✓ 已有** ／ **△ 半有**（有素材、无模块）／ **✗ 无**

| # | 模块 | 状态 | 位置 / 证据 |
|---|---|---|---|
| 1 | 产品图集 | **✗** | hero 无图（块 1 `<img>` = 0）。本页自己的剂型图只作为**配方卡内部配图**重复出现（soft-chews 页 4 张卡同图）+ Product JSON-LD；其余图片是块 7 的 7 张**兄弟剂型**瓦片。**没有任何独立产品图展示位**（§3.5） |
| 2 | 标题区 | **✓** | 块 1 `.sf-hero-inner`：`sf-breadcrumb--d3` + H1 + 18px 副标题 + 2 按钮（`#formulas` / `#configurator`）；另带 `<!-- sf-schema-desc: … -->` 供 Product JSON-LD 取 description |
| 3 | 核心参数表 | **✓** | 块 4 `.sf-spectable`：`Unit size / Pack options / Shelf life / MOQ / Lead time`，1 行 5 列 + `<caption>Typical specifications` |
| 4 | 配置器 | **✓** | 块 3，`id="configurator"`，单块 `wp:html`（§4） |
| 5 | 样品申请 | **△** | 无独立模块。仅两处痕迹：① How We Work 第 03 步文案 `Detailed quotation plus samples delivered in 3–7 days.`（8 页相同）；② 块 8 询价表单 |
| 6 | 产品详细介绍 | **✗** | 无长文案区。仅 hero 的 `sf-schema-desc` 一行 + 各块导语。注：配方详情页有 `[sf_formula_body]`，但 21 条 `post_content` **全空** → 恒不输出 |
| 7 | 活性成分 | **✗** | 数据齐（§7.1），页面上零渲染 |
| 8 | 保证值表 | **✗** | 同上 |
| 9 | 基础参数表 | **△** | 块 4 已覆盖「剂型级」5 字段；K2 里的 `Standard Specs`（配方级规格串，如 `2g/piece · 60/90/120 per bottle · 18 months shelf life`）**未渲染** |
| 10 | 文献 / 科学引用 | **✗** | 全页无 `References` / `Citations` / 外部研究链接 |
| 11 | 相关产品 | **✓**（两处） | ① 块 2 `[sf_formula_grid form=…]` → 2–4 张**同剂型配方卡**；② 块 7 `Related Dosage Forms` → 7 张**兄弟剂型瓦片**（`href="/products/{slug}/"`） |
| 12 | FAQ | **✓** | 块 6 `details.sf-faq__item`，**soft-chews 2 条、其余 7 页 3 条**；配 FAQPage JSON-LD（线上实测存在） |
| 13 | 底部 CTA | **✓** | 块 8 `#inquiry-form`，深底(`primary`) + `✓` 承诺清单 + GF `formId=2`（`ajax:true`，title/description 关） |

**JSON-LD 实测**（线上 `/products/soft-chews/`）：`FAQPage`、`BreadcrumbList`、`Product`、`Organization`、`ItemList` 共 5 段；
其中 `Product` 键为 `name/description/image/brand/manufacturer/category` —— **`additionalProperty` 缺失**（§8.2）。

---

## 3. 图片资源现状

### 3.1 目录与命名

- 唯一目录：`/wp-content/uploads/2026/09/`（`ls | grep -v '^\._'` = **66 个文件**；另有 66 个 macOS `._*` 影子文件）
- 剂型图命名：`<form-slug>.webp`（即 `soft-chews.webp`、`drops.webp`…），与 `sf_formula_card_image()` 的 glob 约定一致
- 变体命名：`<slug>-150x150.webp`、`<slug>-300x300.webp`

### 3.2 8 张剂型图

| slug | 基图 | 尺寸 | 150 变体 | 300 变体 |
|---|---|---|---|---|
| soft-chews | 62,570 B | **720×720** | ✓ | ✓ |
| tablets | 33,902 B | 720×720 | ✓ | ✓ |
| powders | 95,306 B | 720×720 | ✓ | ✓ |
| pastes | 9,974 B | 720×720 | ✓ | ✓ |
| drops | 18,610 B | 720×720 | ✓ | ✓ |
| liquids | 13,422 B | 720×720 | **✗ 缺** | **✗ 缺** |
| fish-oil | 36,820 B | 720×720 | ✓ | ✓ |
| dental-chews | 42,998 B | 720×720 | **✗ 缺** | **✗ 缺** |

- 8 张全部 **1:1、720×720**（lossy webp）。
- **声明式属性与实际不符**：块 7 瓦片写 `width="800" height="600"`，实际文件 720×720；CSS `.sf-related-grid .sf-tile__media img{aspect-ratio:4/3}` 又把 1:1 源裁成 4:3。→ 属性是陈旧的，不影响渲染，但**不要拿它当尺寸真值**。
- `liquids` / `dental-chews` 无 150/300 变体 → 这两页相关瓦片的 `srcset` 更薄。

### 3.3 ⚠ 水印（实测，非推测）

取证方式：从云端取回原图 → 裁出「右下 34% 宽 × 20% 高」→ 17 张拼成一张蒙太奇逐格目视。
**取证文件**：`docs/b2d-step0-shots/watermark-montage-18img.png`（17 格 + 标签）、
`fac-placeholder-corner-zoom.png`、`equip-placeholder-corner-zoom.png`、`soft-chews-still.png`。

抽查 18 个对象（8 张剂型图 + 2 张 placeholder + 8 张厂区/设备/QC 图）：
**每一个都在右下象限带 `AI生成 / WORKBUDDY` 水印，无一例外。**

| 水印形态 | 对象 |
|---|---|
| 完整落在画面内（文字可读） | `soft-chews`、`pastes`、`fac-placeholder`、`fac-line`、`hero3-line`、`fac-packaging`、`tablets` |
| 被画框切掉一部分（贴边缘） | `equip-placeholder`、`liquids`、`drops`、`fish-oil`、`dental-chews`、`qc-inprocess`、`fac-cleanroom`、`equip-hplc`、`fac-lab` |

**逐张清单的取证陷阱（我踩过一次，记下来）**：水印**不在最角落**。以 `hero3-line`（1920×1080）为例，
水印文字落在约 `x≈1460, y≈965` 处 —— 距右边缘 ~24%、距下边缘 ~11%。
只裁「右下 300×100 极角」会**漏判成"干净"**，必须按比例裁足够大的右下象限。

**决策影响**：因为多数图上水印在画面内部，「靠 CSS `object-fit: cover` 裁掉一角」**不可靠** ——
要稳定裁掉得吃掉约 30% 宽 × 20% 高，构图会被破坏。
⇒ 这不是样式能解决的问题，**只能重出图 / 裁图生成干净副本 / 换实拍**。

### 3.4 两张「占位图」的实测结论（与既定决策直接相关）

| 文件 | 尺寸 | 大小 | 内容 | 水印 |
|---|---|---|---|---|
| `equip-placeholder.webp` | 800×600（4:3） | 69,698 B | GMP 洁净车间 + 三台不锈钢配液罐 + 灌装线（透视纵深） | **带**，压在右下边缘，被画框切掉约一半 |
| `fac-placeholder.webp` | 1100×733（≈3:2） | 121,516 B | **同一场景**（同角度、同机位、同罐体布局），分辨率更高 | **带**，完整落在画面内、清晰可读 |

两条硬事实：
1. **两张是同场景**。同页并排使用会呈现「重复图」，观感上像渲染错误。
2. **两张都不干净**（见取证图 `*-placeholder-corner-zoom.png`）。

→ 结论：**「用占位图做结构」在结构层面成立**（验证几何/间距/灯箱完全够用），
但必须把「**干净图片**」写成**独立的上线阻塞项**，而不是隐含在「后续实拍图好了再替换」里。

### 3.5 素材用途现状（实测，含一次自我更正）

线上 `/products/soft-chews/` 实际引用的 uploads 图（按出现次数）：

| 图 | 次数 | 出处 |
|---|---|---|
| `soft-chews.webp` | **5** | 块 2 的 4 张配方卡 `figure.sf-fcard__media`（4×，因为 4 条配方同属 soft-chews）× 1（Product JSON-LD 的 `image`） |
| `tablets / powders / pastes / drops / liquids / fish-oil / dental-chews.webp` | 各 1 | 块 7 的兄弟剂型瓦片 |

更正一处早先的推断：**本页自己的剂型图确实出现在自己页面上**，但只出现在**配方卡内部的配图槽**里（4 张卡重复同一张），
以及 Product JSON-LD 里 —— **hero 无图（块 1 `<img>` = 0），全页没有任何"产品图集"性质的展示**。
⇒ 「图集」缺口的准确表述是：**该剂型唯一的实拍/渲染图只被当成卡片的占位配图重复 4 次，没有独立展示位**。

其它引用点：`/formulas/`（21 张卡）、`single-sf_formula.html:42` 的 `[sf_formula_grid limit="4"]`（相关配方卡）、
配方详情页 Product JSON-LD（`sinofresh_formula_card_image`，由剂型 slug 解析）。
⚠ `single-sf_formula.html` **模板里没有任何 `<img>`** —— 详情页 hero 是纯文字，图片全部由 shortcode / PHP 注入。

库内其它可复用实景（同样带水印，§3.3）：`fac-cleanroom / fac-lab / fac-line / fac-packaging / fac-retention / fac-warehouse`（800×600）、
`equip-hplc / equip-gc / equip-aas`（800×600）、`qc-*`（6 张 800×600）、`hero1-exterior / hero2-lab / hero3-line / hero4-warehouse`（`hero3-line` 为 1920×1080）。

---

## 4. 配置器 DOM 骨架

块 3 是**一个** `<!-- wp:html -->`（27 KB），内部结构（缩进为嵌套近似）：

```
<section id="configurator" class="wp-block-group">
  h2  Build Your {Form} Formula
  p   导语（text-secondary）
  <svg class="configurator__sprite"> … 39 个 <symbol id="i-*"> … </svg>   ← 图标雪碧图（bone/star/heart/…）
  <div class="configurator">
    <div class="configurator__options">
      × 6~8  <div class="configurator__group" data-group="{g}" data-multi="false">
                <div class="configurator__label">
                  <h4>{Shape|Color|Flavor|…}</h4>
                  <p class="configurator__tip">{面向买家的提示句}</p>
                </div>
                <div class="configurator__items">
                  <button type="button" class="configurator__item" data-value="{值}">
                      [<svg class="configurator__icon"><use href="#i-*"/></svg> | <span class="configurator__dot configurator__dot--{色}">]
                      {标签}
                  </button>
                  … 末项恒为 data-value="Custom"（带 #i-plus 图标）
                </div>
              </div>
      <div class="sf-explore">
        <h3 class="sf-explore__title">Explore more dosage forms</h3>
        [sf_explore_chips]                                ← 短代码，页内唯一
        <a class="sf-explore__btn" href="/products/">Browse All Products →</a>
      </div>
    </div>
    <div class="configurator__summary-col">
      <aside class="configurator__summary">              ← 摘要卡（右栏，非 sticky）
        <h3>Your Configuration</h3>
        <div class="configurator__progress" aria-live="polite"></div>
        × 6~8 <div class="configurator__summary-row" data-group="{与左栏同名的 g}"></div>
        <button type="button" class="configurator__submit">
        <div class="configurator__cta-row">
          <div class="configurator__pdf-mail" hidden>
          <div class="configurator__actions">
            <button type="button" class="configurator__reset">
            <button type="button" class="configurator__copy" aria-label="Copy configuration summary">
        <p class="configurator__note">
      </aside>
    </div>
    <div class="configurator__mobilebar"><button class="configurator__submit configurator__submit--bar"></div>
    <div class="configurator__bar">
      <button class="configurator__bar-trigger" aria-expanded="false" aria-controls="configurator-drawer">
      <button class="configurator__bar-submit configurator__submit">
    </div>
    <div class="configurator__drawer" id="configurator-drawer" hidden>
      <div class="configurator__drawer-header">
      <div class="configurator__drawer-content">
        <div class="configurator__cta-row">
          <div class="configurator__pdf-mail" hidden>
          <div class="configurator__drawer-actions">
    </div>
  </div>
</section>
```

关键事实：
- **摘要卡 DOM 位置**：`.configurator > .configurator__summary-col > aside.configurator__summary`（右栏），
  与左栏 `.configurator__options` 并列；移动端另有 `__mobilebar` 与 `__drawer` 两套 CTA 面。
  **不是 `position: sticky`**（真正 sticky 的是顶部导航）。
- 左右栏通过 **`data-group` 字符串**耦合（左 `div[data-group]` ↔ 右 `.configurator__summary-row[data-group]`），
  组名 8 页各不相同 —— **改任一侧必须同步改另一侧**。
- `h4` 用于组标题：H2 序列不受污染（K3 同款理由），toc-nav 只吃 `h2`。
- 提交按钮 `configurator__submit` 在 **4 个地方**（aside / mobilebar / bar / drawer）出现，靠同一 class 驱动。
- `[sf_explore_chips]` **在配置器的裸 `wp:html` 里**（第 219 行），不在块 2 —— 定位 chips 时别找错块。

---

## 5. 8 页差异点

### 5.1 三处真实分叉

| # | 分叉 | soft-chews | tablets | powders | pastes | drops | liquids | fish-oil | dental-chews |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 配置器组数 | **8** | 7 | 7 | 6 | 6 | 6 | 6 | **8** |
| 1b | 配置器选项按钮总数 | 68 | 39 | 35 | 31 | 30 | 31 | 35 | 43 |
| 2 | How We Work 写法 | **A** | A | A | A | **B** | B | B | B |
| 3 | FAQ 条数 | **2** | 3 | 3 | 3 | 3 | 3 | 3 | 3 |

**分叉 1 —— 配置器组名逐页不同**（`data-group` 值）：

| 页 | 组序列 |
|---|---|
| soft-chews | `shape · color · flavor · weight · count · packaging · functions · shelf_life` |
| tablets | `shape · color · flavor · functions · weight · count · packaging` |
| powders | `appearance · color · flavor · functions · serving_size · net_weight · packaging` |
| pastes | `texture · color · flavor · functions · tube_weight · packaging` |
| drops | `appearance · flavor · functions · bottle_size · drops_per_dose · packaging` |
| liquids | `appearance · flavor · functions · bottle_size · serving_size · packaging` |
| fish-oil | `form · source · functions · count · bottle_size · packaging` |
| dental-chews | `shape · size · color · flavor · functions · weight_per_piece · count · packaging` |

→ 差异是**刻意按剂型定制**的（软咀嚼有 shape/color/flavor，粉末有 serving_size/net_weight）。
**不是待修的 bug**，任何「统一 8 页」的方案都必须绕开配置器。

**分叉 2 —— How We Work 两种写法**（同样 7 步、同样文案，只有外层容器与节奏不同）：

| | 变体 A（soft-chews / tablets / powders / pastes，8,064 B） | 变体 B（drops / liquids / fish-oil / dental-chews，8,524 B） |
|---|---|---|
| `wp:columns` 属性 | `className:"sf-panel sf-panel--4 sf-panel--bare"` + `margin-top:32px` | 无 className + `margin-top:var:preset\|spacing\|60` |
| 每列内 `wp:group` | `className:"sf-cell"`（**无** padding 设定） | 无 className，`spacing.padding.top = var:preset\|spacing\|20` |
| `sf-panel` 探针 | ✓ | ✗（全站仅这 4 页有 `sf-panel`） |

CSS 侧 `sf-panel--bare` 有专门的 `:has(> .sf-cell)::before` 竖分隔线与 `@media` 覆盖（`style.css` 543–599）。
→ 两种写法都**外观成立**，是历史分叉。改 one 页时不要顺手「统一」，会动到 `:has()` 分隔线。**≤1239px 内页 hero 贴边**的待办也在这一族 CSS 附近。

**分叉 3 —— FAQ 条数**：soft-chews 只有 2 条（MOQ / 自定义），其余 7 页 3 条。

### 5.2 表里看不出但要知道的差异

- 块 2 的 `[sf_formula_grid form="…"]` 每页值不同（`soft-chews`/`tablets`/…/`dental-chews`），故卡片数 4/3/3/2/2/2/2/3 = **21**。
- 块 7 的 7 张瓦片**排除自己**，顺序按 `menu_order`（soft-chews→tablets→powders→pastes→drops→liquids→fish-oil→dental-chews 去掉自身）。
- 块 4 的 `Pack options` 在 `liquids` 上是 `—`（数据列可为空，需容忍）。
- 块 8 的 H2 文案 `Request a {Form} Quote` 逐页不同。

---

## 6. 可复用资源清单

### 6.1 `single-sf_formula.html`（配方详情页，63 行 / 4,568 B）

| 部件 | 契约 | 可否被剂型页复用 |
|---|---|---|
| `[sf_formula_detail]` | 输出 `.sf-fdetail__grid > .sf-fdetail__card > h3.sf-fdetail__label + p.sf-fdetail__value`，3 卡（Ingredients / Guaranteed Analysis / Standard Specs），空字段跳卡 | ⚠ 只在 `is_singular('sf_formula')` 内输出（否则返回 `''`）。**不可直接搬到剂型页**，但其 **`post meta` 读法可照抄**（`sf_formula_ingredients` / `_analysis` / `_specs`） |
| `[sf_formula_body]` | `post_content` 为空时整块隐藏 —— 21 条全空 ⇒ 恒不输出 | 剂型页无意义 |
| `.sf-formula__cta` | **K1**：`data-formula` + `data-form`，formulas.js → sessionStorage → configurator.js | 已由 `[sf_formula_grid]` 自动产出，勿手写 |
| Product JSON-LD | 由配方记录生成（D4），无 `offers/price` | 与剂型页的 Product schema **是两段独立脚本**，改一个不影响另一个 |

### 6.2 `archive-sf_formula.html`（`/formulas/`，51 行 / 3,500 B）

| 部件 | 契约 | 可否复用 |
|---|---|---|
| `.sf-fcard` | **K7**：`.sf-fcard > [.sf-fcard__media]? + .sf-fcard__body > (.sf-fcard__use, h3.sf-fcard__name, p.sf-fcard__spec, .sf-fcard__actions)` | 卡片解剖可直接借用视觉，但**不可复用其 JSON-LD**（ItemList 会重复） |
| `<script class="sf-formulas-data">` | **K2**：21 条 `{name, slug, url, form, use, sections[3]}`；`sections` = Ingredients / Guaranteed Analysis / Standard Specs | ✅ **本批的数据源**。但它是 `sinofresh_formula_grid()` 的**副产物**，只有页面调用该短代码时才存在 → 依赖它 = 依赖网格在场（§8.1 讨论） |
| `[sf_formula_filters]` | 9 按钮 + `formula-filter.js`（`is-sf-off`）+ `data-sf-form` | 档案页专用 |
| Product/ItemList JSON-LD | ItemList + BreadcrumbList | 不适用于剂型页 |

### 6.3 CSS 现成组件（`style.css`，已定义、可直接引用）

| 类 | 位置 | 形状 | 现状 |
|---|---|---|---|
| `.sf-spec-list` / `.sf-spec-row` / `.sf-spec-term` / `.sf-spec-value` | 2,064 起 | 两列 term/value 栅格（38% / 1fr），紧凑行、hairline | ⚠ **零模板引用**。CSS 在，K6 解析器在等它，`additionalProperty` 因此为空 |
| `.sf-spectable*` | 1,894 起 | 5 列表格，`nth-child(1..5)` 固定宽度 19/19/13/19/30%，绿底表头 | 用于块 4 |
| `.sf-panel` / `--3 / --4 / --bare` / `.sf-cell` | 543–599 | `wp:columns` 变体栅格 + `:has(> .sf-cell)::before` 竖线 | 块 5 变体 A |
| `.sf-explore__chips` / `.sf-explore__chip` / `.is-current` | — | 剂型 chips（`[sf_explore_chips]` 产出） | 配置器内 |
| `.wp-block-columns.sf-dosage-grid` | 482 起（媒体查询 1234/2451） | 瓦片栅格列数 | 块 7 |
| `.sf-related-grid` / `.sf-tile` / `.sf-tile__media` | 2089 起 | `aspect-ratio:4/3` + 遮罩修边 + `(hover:none)` `:active` 反馈 | 块 7 |
| `.sf-faq` / `.sf-faq__item` / `.sf-faq__icon` | 288 起 | `details` 手风琴 | 块 6 |
| `.sf-coa` / `__preview` / `__frame` / `__pdf` / `__btn(--primary/--ghost)` | 6,653 起 | COA 预览 + PDF 下载（配 `coa-sample.pdf`，29,747 B 已上传） | **仅 `page-quality.html`** → 样品申请批次的候选 |
| `.sf-certcard / .sf-certgrid / .sf-certbar` | — | 证书卡与栅格 | **仅 `front-page.html`**；同类 `.sf-certrow` 在 `page-quality.html` |
| `.sf-statbar` | — | 数字条 | `front-page.html` + `page-factory-tour.html` |
| `.sf-lb*` | 4,705 起 | 灯箱（CSS **全局**；DOM 由 JS 建，**JS 仅 /about/ 与 /quality/ 入队**） | 见 §7.3 —— 复用要新增入队，非零成本 |
| `.sf-lb` / `.sf-lb__stage` / `__img` / `__bar` / `__btn(--prev/--next/--close)` / `__count` | `about.js:107+`、`quality.js:66+` | **灯箱**：JS 运行时现建 DOM，`html.sf-lb-open` 锁滚动，键盘 + 点击遮罩关闭，prev/next + 计数 | **零模板静态引用**（纯 JS 生成）→ 图集批次可直接用，**不需要新 JS**，但要确认 `about.js`/`quality.js` 的入队页面（§8.3） |

### 6.4 短代码

| 短代码 | 定义位置 | 剂型页用途 |
|---|---|---|
| `[sf_formula_grid form=…]` | `functions.php:744`（注册 `:918`） | **K1 + K2** 唯一产出点 |
| `[sf_explore_chips]` | `functions.php:216`（注册 `:242`） | 配置器内 cross-sell |
| `[sf_formula_detail]` / `[sf_formula_body]` | `functions.php:1049` / `:1099`（注册 `:1079` / `:1116`） | 详情页专用 |
| `[sf_archive_count]` / `[sf_formula_filters]` / `[sf_blog_chips]` | — | 非剂型页 |

**调用顺序陷阱**（已记入 K3 注释）：block template 先 `do_shortcode()` 后 `do_blocks()` ⇒
**短代码属性里不能写 `{{占位符}}`**（此时仍是字面 token）；短代码也**拿不到** `wp-container-core-*` 布局类，必须自带容器与列数（如 `--sf-fgrid-cols`）。

### 6.5 结构/机制类

- **模板权威守卫**（`functions.php:59` 单数 + `:97` 复数）：磁盘模板存在时永远胜出 DB。注释原文：
  「Remove this filter if you ever want to edit templates from the Site Editor again.」
  → 这就是「**删守卫后用 Edit Site 替换**」所指的守卫。实测当前 DB 里的 `wp_template` **全部是 `trash`**
  （`front-page__trashed` ×4、`index__trashed`、`page-products__trashed`）⇒ **今天删掉它不会立刻造成回滚**，但删完一旦有人在 Site Editor 保存，就会新建 DB 副本并开始遮蔽文件（注释记录已发生过两次）。
- **toc-nav.js 2.0**（入队条件含这 8 个 slug，`functions.php:40`）：吃**全部 `h2`**，逐条补 `id="sf-sec-N"`，**≥3 个 H2 才出点轨**。
  → 剂型页新增一个 H2 = 点轨多一颗点 + 其后所有 `#sf-sec-N` 序号后移。这些 id 是**运行时注入**、不落库、无外部深链，
  现有 `#formulas` / `#configurator` / `#inquiry-form` 是**显式 anchor，不受影响**。但仍需浏览器复核点轨。
- **占位符引擎** `sinofresh_template_placeholders()`：只处理含 `{{` 的 `core/html` 块；剂型页当前**未使用**任何 `{{}}`（面包屑是静态链）。
- **K6 dosage Product JSON-LD**（`functions.php:2773` 注释 / `:2784` `add_action('wp_head', …)`，priority 21）：**读磁盘模板文件**（不是渲染结果），`additionalProperty` 先找
  `<span class="sf-spec-term">…</span><span class="sf-spec-value">…</span>`（**两 span 之间必须零空白**），
  找不到才走 `flex-basis:35%` 老表回退 —— 8 页**都没有** `flex-basis:35%` ⇒ **`additionalProperty` 恒为空**（线上实测确认）。
- **`esc_sql()` 令牌化 `%`**：本批不写库则不触发；若写 `.sql` 落盘必须用 `mysqli_real_escape_string($wpdb->dbh,$v)`。
- **CLI 改含内联 SVG 的 `post_content` 会被 kses 剥离** → 本批若动数据须先 `wp_set_current_user(1)` 或 `$wpdb->update` + md5 校验。

---

## 7. 三点如实说明

### 7.1 数据已有：21 条配方 × 3 字段，全部非空

`post meta` 实测（`sf_formula_ingredients` / `sf_formula_analysis` / `sf_formula_specs`，字符长度）：

| 剂型 | 配方（菜单序） | Ingredients | Guaranteed Analysis | Standard Specs |
|---|---|---|---|---|
| soft-chews | Joint Support / Calming / Digestive / Skin & Coat | 78 / 67 / 67 / 79 | 71 / 50 / 42 / 42 | 56 / 56 / 56 / 56 |
| tablets | Joint Support / Multivitamin / Calcium & Phosphorus | 54 / 61 / 74 | 77 / 45 / 51 | 58 / 58 / 58 |
| powders | Probiotic / Pumpkin Digestive / Bladder Support | 92 / 34 / 34 | 43 / 18 / 24 | 40 / 40 / 40 |
| pastes | Hairball Remedy / Nutrition | 75 / 65 | 35 / 37 | 46 / 46 |
| drops | Ear Care / Urinary Care | 42 / 46 | 16 / 21 | 48 / 48 |
| liquids | Liquid Joint Support / Liquid Skin & Coat | 111 / 45 | 68 / 38 | 49 / 49 |
| fish-oil | Wild Alaskan Salmon Oil / Pure Fish Oil Blend | 41 / 39 | 69 / 38 | 49 / 49 |
| dental-chews | Plaque Control / Oral Care / Natural Cleaning | 54 / 89 / 95 | 17 / 37 / 38 | 53 / 52 / 52 |

同样的三条已在**线上 K2 JSON** 中验证（`/products/soft-chews/` 的 `.sf-formulas-data` = 4 条，每条 `sections` 三项，值原样）。

**数据形状（决定渲染方式）**：

| 字段 | 分隔 | 样例 | 可直接表化？ |
|---|---|---|---|
| Ingredients | `, ` | `Glucosamine HCl, Chondroitin Sulfate, MSM, Green-lipped Mussel, Chicken Flavor` | 可 → 列表/chips |
| Guaranteed Analysis | `, `，每段 `<分析项> ≥<水平>` | `Glucosamine ≥500mg/chew, Chondroitin ≥200mg/chew` | **可 → 两列 term/value 表**（解析验证见下） |
| Standard Specs | ` · ` | `2g/piece · 60/90/120 per bottle · 18 months shelf life` | 可 → 三段 |

**解析边界（已用真值跑过，不是推测）**：
- `≥` 拆分：21 条全部命中；`Total microorganisms ≥5 billion CFU/scoop`、`Cranberry ≥200mg/scoop`、`Vitamin E ≥50 IU/tablet`
  这类"水平含空格/多词"也正确落在右列。**无一条缺 `≥`**。
- ✅ **更正（2026-09-20 晚，批次 2D Step1 预实施扫描）**：本节原写「`Hairball Remedy Paste` 少一个右括号、
  括号内有逗号」——**那是本文档的转录错误，不是数据缺陷**。HEX 取证：该字段 75 字节、
  尾部解码为 `Chicken Meal (4%), Yeast, Minerals`（右括号在），`post_modified_gmt = 2026-09-20 06:28:47`
  **早于本文档的扫描时刻** ⇒ 数据从未被改过，是引用时抄漏了一个 `)`（本文档表格里的 `LENGTH()` 值 75
  本就是配平版长度）。**连带失效**：由此推出的「解析器必须做括号配平」不成立 ——
  `tools/b2d1_parser_dryrun.php` 干跑证明 **21/21 条与朴素 `', '` 切分结果完全相同**，
  且**没有任何一条成分串的括号内含逗号**（`Tapioca (46%), Peas (29%)…` 的逗号都在括号外）。
  括号配平在 Step1 中**降级为防御性实现**，不再是必要条件。教训：**文档引用数据前必须先对 HEX。**

### 7.2 图片全带水印（抽查 18 个对象，零例外）

见 §3.3。8 张剂型图 + 8 张厂区/设备/QC 图 + 2 张 placeholder **全部带 `AI生成 / WORKBUDDY` 水印**，
且多数水印落在**画面内部**（不是贴边）⇒ CSS 裁切救不了。
`equip-placeholder` 与 `fac-placeholder` **还是同一场景**（§3.4）。
⇒ 「先用占位图做结构」可行；但**「干净图片」是独立的上线阻塞项**，且**两张 placeholder 不能同页并排**。

### 7.3 `sf-lb` 灯箱是现成组件 —— 但 **JS 未在剂型页入队**，不是零成本复用

- **CSS 是全局的**：`.sf-lb` / `__stage` / `__img` / `__bar` / `__count` / `__btn(--prev/--next/--close)` 定义在
  `style.css:4705` 起（含 `html.sf-lb-open` / `body.sf-lb-open` 锁滚动 @4701）——**不按页加载，剂型页本来就有**。
- **DOM 全部由 JS 运行时创建**：`assets/js/about.js:107` 起、`assets/js/quality.js:66` 起。
  模板里搜不到任何 `sf-lb` 静态标记（这就是 §6.3 探针全 `-` 的原因，**不是"组件不存在"**）。
  功能完整：遮罩 + stage + 大图 + prev/next + 计数 + close，`is-open`/`is-closing` 过渡，Esc/遮罩关闭，焦点管理。
- ⚠ **但入队是页级白名单**：
  - `about.js`（v1.3.0）→ `is_page('about') || is_page_template('page-about')`，**仅 /about/**
  - `quality.js`（v1.1.0）→ `is_page('quality') || is_page_template('page-quality')`，**仅 /quality/**
  - 两个脚本各自还绑定了本页私有用例（About 的 reveal + 视频海报 / Quality 的证书条 + 证书弹窗）
  ⇒ **不能直接在剂型页入队**（会连带跑本页无关逻辑）。
- 结论：图集批次要用灯箱**可行，但要新增一个专用入队条件/独立小脚本**（或把灯箱逻辑抽成共享文件 + 三个页级入口），
  **这是工作量，不是"零成本复用"**。请把它算进第 2 批的估价，别按"组件已存在 = 免费"理解。

---

## 8. 未决 / 风险（留给第 1 批方案正面处理）

### 8.1 数据源耦合
K2 JSON 是 `[sf_formula_grid]` 的副产物。若新模块靠读 `.sf-formulas-data` 渲染，则
① 无 JS 不显示（SEO 与降级都吃亏）；② 页面必须保留网格；③ 与 2B「改用 JSON 驱动」的方向一致但把渲染推给客户端。
→ 倾向 **新 shortcode 直读 `post meta`（与 `[sf_formula_detail]` 同源同法）**。

### 8.2 `.sf-spec-list` 的双刃
用它的类名 = 零 CSS + 免费喂 K6；但剂量页的 Product `name` 是「Private Label Soft Chews」，
把 4 个配方的 10~20 行成分/保证值灌进同一个 `additionalProperty` 会**语义错误**（一个 product 的属性里混 4 个配方）。
→ 要么**显式收窄解析器**，要么**不喂**。两案都要在方案里写清，不能默认。

### 8.3 守卫与「后续替换」路径
「删守卫后用 Edit Site 替换」可行（当前 DB 模板全为 trash），但**整条删除全局守卫**会让 `front-page` / `header` 一族重新暴露在 DB 遮蔽风险下。
→ 建议按 **slug 白名单**放开这 8 个模板，而不是删整个 filter；或在实拍图到位时直接改模板 `src`（一行 diff，零守卫风险）。

### 8.4 其它待办（与 2C 遗留对齐）
- ≤1239px 内页 hero 文字贴边：`style.css` 27s 段 `max-width:1024px → 1239px`（影响 22 个挂 `.sf-hero-inner` 的模板/部件）。
- 首页 `<title>` 仍是 `sinofresh`。
- `_backup/` 历史清理暂缓（不执行 `git rm -r --cached`）。
- 本批新增/删除 CSS 段时逐选择器判断：`.sf-slider-progress`（首页 hero 共用）、`.sf-toast`（4 脚本共用）。

---

## 附：复现命令

```bash
# 结构扫描（本文件的 §1/§5 数据来源）
/Users/meng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 tools/b2d_s0_scan.py

# 静态块校验（自闭合必须 /-->；HTML 标签配平）
/Users/meng/.workbuddy/binaries/python/versions/3.13.12/bin/python3 tools/b2c_s2_block_lint.py \
  sinofresh-theme/templates/page-soft-chews.html

# 线上真值（K2 / JSON-LD / 图片清单）
curl -sL https://dev.zxpet.com/products/soft-chews/ -o /tmp/sc.html
ssh root@65.49.215.152 "ls /var/www/dev.zxpet.com/public/wp-content/uploads/2026/09/"

# 数据完整度
ssh root@65.49.215.152 "mysql -usinofresh -p<DBPASS> sinofresh -e \"
  SELECT p.ID, p.post_title,
         LENGTH(i.meta_value) ing, LENGTH(a.meta_value) ana, LENGTH(s.meta_value) spec
  FROM wp_posts p
  LEFT JOIN wp_postmeta i ON i.post_id=p.ID AND i.meta_key='sf_formula_ingredients'
  LEFT JOIN wp_postmeta a ON a.post_id=p.ID AND a.meta_key='sf_formula_analysis'
  LEFT JOIN wp_postmeta s ON s.post_id=p.ID AND s.meta_key='sf_formula_specs'
  WHERE p.post_type='sf_formula' AND p.post_status='publish'\""
```

*本文件为只读扫描存档，未修改任何主题文件、模板或数据。*
