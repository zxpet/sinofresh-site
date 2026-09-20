# 批次 1（修订版）扫描报告 —— Hero 极简 / 区块重排 / Custom Formula 过渡区

扫描时间：2026-09-20 09:5x　范围：8 个剂型页　**本次未改任何代码**
数据来源：`templates/page-{8}.html` 源码 + `sinofresh.local` 实测渲染（桌面 1440 预滚动逼懒加载 + 移动 375）+ `functions.php` enqueue + JS 源码
原始几何数据：`/tmp/b1s/scan.json`（桌面）、`/tmp/b1s/mobile.json`（移动）、`/tmp/b1s/related2.json`（Related 网格自检）
工作副本脚本：`tools/_b1r_scan.js`、`tools/_b1r_related2.js`、`tools/_b1r_mobile.js`
**前一版报告**：`docs/scan-batch1-hero-section-order-configurator.md`（08:5x，7 段版）——本报告是其**修订版**，差异见 §0

---

## 0. 四条前置事实纠偏（必读，直接影响工作量）

| # | 事实 | 影响 |
|---|---|---|
| **A** | **现网不是原始态**。`阶段 1`（Hero 三层按钮 + 参数速览表）与 `阶段 2A`（配置器桌面折叠 + Lead time 措辞）**已全部落盘并部署** | 本报告「现状」= **8 段**；原报告 §2 的 7 段已作废 |
| **B** | **新计划第 4 点「配置器保持默认展开（现有结构不变）」与已部署的阶段 2A 折叠方案方向相反** | ⚠️ **必须先裁定**：回滚折叠 / 保留折叠 / 折中。回滚有现成备份（见 §9.3） |
| **C** | **新计划第 2 点「Standard Formulas 移到配置器之前」现状已满足** —— `#formulas` 一直位于 `#configurator` 之前 | 该项**无需改动**。真正的新变化是「Key Facts 被 Stage 1 插到 Hero 正后方」，即第 5 点要处理的对象 |
| **D** | 8 页 section 序列仍是**完全同构**（顺序 + class 一致），差异仅在**内容量**（配方数 / FAQ 数）与**一处 DOM 分裂**（Related 网格，见 §6.2） | 改动仍可脚本化批量改写 + 逐页校验 |

> 关于 B：阶段 2A 已实测通过（桌面折叠 466/492px、移动 Δ=0、源码↔Local 一致），**只差子阶段 B 的 JS（`configurator-fold.js` + `formulas.js` 联动 + `functions.php` enqueue）未做**。若第 4 点成立，这部分不再继续，且需回滚模板与 CSS。

---

## 1. 8 页 Hero 现状

### 1.1 结构（8 页骨架完全一致）

```
section.sf-hero-inner  ·  bg #2E6B54  ·  padding 48px/48px  ·  实测高 726px
├ nav.sf-breadcrumb            Home / Products / {剂型}
└ div.wp-block-columns
  ├ column (垂直居中, 实测 385–471px)
  │ ├ h1                                    52px / card-white
  │ ├ p  副标题                             18px
  │ ├ p  认证行                             13px / 600 / letter-spacing 2px
  │ └ div.wp-block-buttons                  3 个按钮（见 1.3）
  └ column (垂直居中, 实测 588px)
    └ div.sf-product-hero-image  白卡 radius 12px
      └ div.sf-pslider  588×588   4 slide + prev/next + dots + progress
```

### 1.2 H1 / 副标题 / 认证行

| 剂型 | H1 | 副标题（全文） |
|---|---|---|
| soft-chews | Private Label Soft Chews for Dogs & Cats | Custom soft chews for joint, skin, calming, and digestive support. OEM/ODM with flexible MOQ, fast sampling, and full regulatory support. |
| tablets | Private Label Pet Tablets for Dogs & Cats | Custom tablets for joint, multivitamin, skin, digestive, and urinary support. OEM/ODM with flexible MOQ, fast sampling, and full regulatory support. |
| powders | Private Label Pet Supplement Powders | Custom powders for probiotics, digestive support, and daily nutrition. OEM/ODM with flexible MOQ, fast sampling, and full regulatory support. |
| pastes | Private Label Pet Supplement Pastes | Custom pastes for hairball control, digestive support, and nutrient delivery. OEM/ODM with flexible MOQ, fast sampling, and full regulatory support. |
| drops | Private Label Pet Supplement Drops | Custom liquid drops for calming, oral care, immune, and joint support. OEM/ODM with flexible MOQ, fast sampling, and full regulatory support. |
| liquids | Private Label Liquid Pet Supplements | Custom liquid supplements for multivitamin, joint, immune, and skin & coat support. OEM/ODM with flexible MOQ, fast sampling, and full regulatory support. |
| fish-oil | Private Label Fish Oil for Dogs & Cats | Omega-3 fish oil in softgels, liquid, and pump formats. OEM/ODM with flexible MOQ, fast sampling, and full regulatory support. |
| dental-chews | Private Label Dental Chews & Sticks for Dogs | Custom dental chews and sticks for plaque control, tartar reduction, and fresh breath. OEM/ODM with flexible MOQ, fast sampling, and full regulatory support. |

认证行 8 页统一：`FDA · cGMP · ISO 9001 · FSSC 22000 · HACCP · BRC`

### 1.3 按钮 —— 现为 **3 个**（Stage 1 已把原 `Download Catalog` 换成 `Browse Standard Formulas`，死链已归零）

| 层 | 文案 | 样式 | href | 实测高 |
|---|---|---|---|---|
| 主 | `Build Custom Formula` | 实色 `has-cta-background-color` | `#configurator` | 48px |
| 次 | `Browse Standard Formulas` | `is-style-outline` 描边 | `#formulas` | 48px |
| 三 | `Request a Quote` | 去按钮外观，纯文字链（下划线） | `#inquiry-form` | 44px |

> `Request a Quote` 的 44px 是因为 `sf-hero-textlink` 把 padding 压成 `10px 2px`（`style.css:1878`）。若 Hero 极简后要「只留 1–2 个按钮」，这里是现成的删减点。

### 1.4 右侧轮播

- 组件：`.sf-pslider`（`product-slider.js` 1.0.1 驱动），**4 张统一图**：
  `{剂型}.webp` → `fac-line.webp` → `fac-lab.webp` → `fac-cleanroom.webp`
- 尺寸：渲染框 **588×588**（左栏同为 588）；源图标注 800×600
- ⚠️ **只有第 1 张带 `loading="lazy"`**，第 2–4 张**无 loading 属性**（浏览器默认 eager）→ 首屏额外拉 3 张图，是 LCP 隐性成本。Hero 极简若删轮播，此处自然消解；若不删，建议一并补 `loading="lazy"`。

### 1.5 Hero 高度

| 视口 | 高度 |
|---|---|
| 桌面 1440 | **726px（8/8 恒定）** |
| 移动 375 | 975 / 1003 / 1014 / 1042px（随标题行数浮动） |

---

## 2. 当前完整区块顺序 + 每区块高度

### 2.1 顺序（8 页完全一致，共 **8 段**）

| # | 区块 | 模板标记 | id | 备注 |
|---|---|---|---|---|
| 1 | Hero | `section.sf-hero-inner` | — | bg `#2E6B54` |
| 2 | **Key Facts（参数速览表）** | `section.sf-spectable` | — | ⚠️ **Stage 1 新增**，就是第 5 点要「下移」的对象 |
| 3 | Standard Formulas | `section.sf-formulas` | `#formulas` | Stage 1 新增 id |
| 4 | Configurator | `section` + `wp:group` | `#configurator` | ⚠️ 已包 `<details class="configurator__fold">` |
| 5 | How We Work | `has-bg-light` 带背景 | — | 7 步 |
| 6 | FAQ | 无附加 class | — | 3 段（soft-chews 仅 2） |
| 7 | Related Dosage Forms | `has-bg-light` 带背景 | — | 7 tile |
| 8 | CTA / 询盘表单 | `has-primary` 主色背景 | `#inquiry-form` | GF form id=2 |

### 2.2 高度（桌面 1440，**已预滚动逼出懒加载**）

> ⚠️ 量法说明：**必须先整页预滚动再测**。首访问页的 below-the-fold 图片未加载会让 tile 高度从 350px 塌到 140px（实测 soft-chews 首访 Related=503px vs 等图后 923px）—— 这是一条**假差异**来源，任何后续回归测量都要沿用「预滚动 + 等 img complete」。

| # | 区块 | soft-chews | tablets | powders | pastes | drops | liquids | fish-oil | dental-chews | 极差 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Hero | 726 | 726 | 726 | 726 | 726 | 726 | 726 | 726 | **0** |
| 2 | Key Facts | 149 | 149 | 149 | 149 | 149 | 149 | 149 | 149 | **0** |
| 3 | `#formulas` | 440 | 378 | 378 | 316 | 316 | 316 | 316 | 378 | 124（配方数 4/3/3/2/2/2/2/3） |
| 4 | `#configurator`（**折叠态**） | 492 | 466 | 492 | 466 | 492 | 492 | 492 | 492 | 26（描述 1 vs 2 行） |
| 5 | How We Work | 606 | 606 | 606 | 606 | 682 | 682 | 682 | 682 | 76（步骤文案换行） |
| 6 | FAQ | 287 | 344 | 344 | 344 | 344 | 344 | 344 | 344 | 57（= 1 行 FAQ，soft-chews 少 1 条） |
| 7 | Related | 923 | 923 | 923 | 923 | 915 | 915 | 915 | 915 | 8 |
| 8 | `#inquiry-form` | 803 | 803 | 803 | 803 | 803 | 803 | 803 | 803 | **0** |

**桌面文档总高**：5054（pastes）– 5210（dental-chews）px —— **注意这是「配置器折叠态」**；若按新计划第 4 点恢复默认展开，则约 **+750px**（配置器回到 ~1217px），文档总高回到 ~5800–5960px。

**移动 375 逐区块高度**（供对照，折叠方案在移动端不生效，配置器保持完整展开）

| # | 区块 | soft-chews | tablets | powders | pastes | drops | liquids | fish-oil | dental-chews |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Hero | 1014 | 1014 | 1014 | 1003 | 975 | 1003 | 975 | 1042 |
| 2 | Key Facts | 314 | 314 | 314 | 314 | 314 | 314 | 314 | 314 |
| 3 | `#formulas` | 442 | 383 | 413 | 324 | 295 | 295 | 295 | 413 |
| 4 | `#configurator` | 3035 | 2224 | 2161 | 1844 | 1932 | 1914 | 2091 | 2522 |
| 5 | How We Work | 842 | 842 | 842 | 842 | 845 | 845 | 845 | 845 |
| 6 | FAQ | 353 | 395 | 382 | 395 | 395 | 395 | 382 | 395 |
| 7 | Related | 1392 | 1373 | 1392 | 1411 | 1393 | 1393 | 1374 | 1393 |
| 8 | `#inquiry-form` | 1295 | 1295 | 1295 | 1265 | 1265 | 1295 | 1295 | 1295 |

**移动文档总高**：8191 – 9481px。

---

## 3. Standard Formulas 现状

### 3.1 DOM 结构（手风琴，原生 `<details>`）

```html
<section id="formulas" class="wp-block-group sf-formulas">
  <h2>Standard Formulas</h2>
  <p class="has-text-secondary-color">Proven recipes from our existing OEM production. Use as reference or request customization.</p>
  <!-- wp:html -->
  <details class="sf-formula__item">                  ← 每个配方一个 details，默认闭合
    <summary>
      <span class="sf-formula__head">
        <span class="sf-formula__name">Liquid Joint Support</span>
        <span class="sf-formula__use">Joint care</span>
      </span>
      <span class="sf-formula__icon"></span>
    </summary>
    <div class="sf-formula__body">
      <h4 class="sf-formula__label">Ingredients</h4>
      <p class="sf-formula__value">…</p>
      <h4 class="sf-formula__label">Guaranteed Analysis</h4>
      <p class="sf-formula__value">…</p>
      <h4 class="sf-formula__label">Standard Specs</h4>
      <p class="sf-formula__value">…</p>
      <button class="sf-formula__cta" data-formula="Liquid Joint Support">Reference this formula →</button>
    </div>
  </details>
  <!-- /wp:html -->
  …（每个配方一个独立 wp:html 块）
  <!-- wp:html -->
  <script type="application/ld+json">ItemList…</script>   ← 与配方同源的 JSON-LD
  <!-- /wp:html -->
</section>
```

### 3.2 字段（每个配方恒定 3 字段 + 1 个 CTA）

`Ingredients` / `Guaranteed Analysis` / `Standard Specs` + 按钮 `Reference this formula →`（`data-formula` 携带配方名）

### 3.3 配方清单（**合计 21 个**，逐页数量不等 = 8 页唯一的内容级不一致）

| 页 | 数量 | 配方（名称〔用途〕） |
|---|---|---|
| soft-chews | **4** | Joint Support Soft Chews〔Joint care〕· Calming Soft Chews〔Calming〕· Digestive Soft Chews〔Digestive care〕· Skin & Coat Soft Chews〔Skin & coat〕 |
| tablets | 3 | Joint Support Tablets〔Joint care〕· Multivitamin Tablets〔Daily nutrition〕· Calcium & Phosphorus Tablets〔Bone health〕 |
| powders | 3 | Probiotic Powder〔Digestive care〕· Pumpkin Digestive Powder〔Digestive care〕· Bladder Support Powder〔Urinary care〕 |
| pastes | 2 | Hairball Remedy Paste〔Hairball control〕· Nutrition Paste〔Daily nutrition〕 |
| drops | 2 | Ear Care Drops〔Ear care〕· Urinary Care Drops〔Urinary care〕 |
| liquids | 2 | Liquid Joint Support〔Joint care〕· Liquid Skin & Coat〔Skin & coat〕 |
| fish-oil | 2 | Wild Alaskan Salmon Oil〔Skin & coat〕· Pure Fish Oil Blend〔Skin & coat〕 |
| dental-chews | 3 | Plaque Control Dental Chews〔Plaque control〕· Oral Care Dental Sticks〔Oral care〕· Natural Cleaning Dental Sticks〔Oral care〕 |

### 3.4 高度

- 桌面：**316 / 378 / 440px**，精确对应 2 / 3 / 4 个配方（每个约 **62px**）
- 移动：295 / 324 / 383 / 413 / 442px
- 与 `#configurator` 的关系：**`#formulas` 在 `#configurator` 之前（现状已满足新计划第 2 点）**

---

## 4. 配置器现状

### 4.1 DOM 结构（`section#configurator` 内）

```
section#configurator  ·  padding 80px/80px  ·  wp:group constrained
└ wp:html
  ├ details.configurator__fold            ← ⚠️ 阶段 2A 新增（桌面默认闭合、移动端强制可见）
  │ ├ summary.configurator__fold-head
  │ │ ├ h2  "Build Your {剂型} Formula"
  │ │ ├ span.configurator__fold-desc      （原副标题 <p> 改成 <span>，因 summary 只收 phrasing content）
  │ │ └ span.configurator__fold-icon
  │ └ div.configurator__fold-body
  │   ├ svg.configurator__sprite          （16 个 <symbol> 图标：#i-joint / #i-heart / …）
  │   └ div.configurator
  │     ├ div.configurator__options
  │     │ └ div.configurator__group[data-group][data-multi]  × N
  │     │   ├ div.configurator__label
  │     │   └ div.configurator__items → div.configurator__item[data-value]
  │     ├ div.configurator__summary-col
  │     │ ├ h3 "Your Configuration"
  │     │ ├ div.configurator__progress  "0 of N selected"
  │     │ ├ div.configurator__summary-row[data-group] × N
  │     │ ├ div.configurator__cta-row   → button.configurator__basket / button.configurator__submit
  │     │ ├ div.configurator__pdf-mail[hidden]
  │     │ └ div.configurator__actions   → .configurator__reset / .configurator__copy / .configurator__pdf
  │     ├ div.configurator__mobilebar
  │     ├ div.configurator__bar         → .configurator__bar-count / .configurator__bar-trigger
  │     └ div.configurator__drawer#configurator-drawer[hidden]
  │       ├ .configurator__drawer-header（h3 + .configurator__drawer-close）
  │       ├ .configurator__drawer-content
  │       ├ .configurator__cta-row / .configurator__pdf-mail
  │       └ .configurator__drawer-actions（.configurator__drawer-reset / -submit）
  └ div.configurator__explore-row        ← 阶段 2A 把 .sf-explore 提到折叠区之外（内链不可藏）
    └ div.configurator__explore-col
      └ div.sf-explore
        ├ h3.sf-explore__title "Explore more dosage forms"
        ├ [sf_explore_chips]  → 8 个 .sf-explore__chip（当前页带 aria-current + is-current）
        └ a.sf-explore__btn "Browse All Products →"
```

### 4.2 选项组（逐页不同，**全部 `data-multi="false"` 单选**）

| 页 | 组数 | 组顺序 |
|---|---|---|
| soft-chews | **8** | shape · color · flavor · weight · count · packaging · functions · shelf_life |
| dental-chews | **8** | shape · size · color · flavor · functions · weight_per_piece · count · packaging |
| tablets | 7 | shape · color · flavor · functions · weight · count · packaging |
| powders | 7 | appearance · color · flavor · functions · serving_size · net_weight · packaging |
| fish-oil | 7 | form · source · functions · omega3_per_unit · count · bottle_size · packaging |
| pastes | 6 | texture · color · flavor · functions · tube_weight · packaging |
| drops | 6 | appearance · flavor · functions · bottle_size · drops_per_dose · packaging |
| liquids | 6 | appearance · flavor · functions · bottle_size · serving_size · packaging |

### 4.3 锚点与展开状态（**实测**）

| 项 | 实测值 |
|---|---|
| `#configurator` 存在 | ✅ |
| **桌面 1440 默认展开？** | ❌ **已折叠**（`fold.open = false`，段高 466/492px） |
| 移动 375 | `fold.open=false` 但 `fold-body` **可见**（`checkVisibility=true`，CSS 强制）；`summary` `pointer-events:none`；折叠图标 `display:none` |
| 移动端底部条 | `.configurator__bar` = `display:flex`（固定条）；`.configurator__mobilebar` = `display:none` |
| 移动端抽屉 | `#configurator-drawer` `hidden=true`，点击 bar 打开 |
| 移动端摘要列 | `.configurator__summary-col` = `position:sticky` |

> **这正是新计划第 4 点的冲突点**：现状「桌面折叠」，新计划要求「保持默认展开（现有结构不变）」。

### 4.4 JS 初始化逻辑

| 文件 | 版本 | 职责 |
|---|---|---|
| `assets/js/configurator.js` | 2.2 | **主逻辑**（843 行 IIFE）。`var root = document.querySelector('.configurator'); if (!root) return;` 无 DOM 时安全退出。绑定 `.configurator__group` / `__item` / `__submit` / `__reset` / `__copy` / `__pdf` / `__basket` / `__summary-row[data-group]`；末尾第 842 行另有**独立压缩 IIFE** 处理移动端 bar + drawer（count / open / close / Reset 后行刷新） |
| `assets/js/formulas.js` | 1.0.0 | 配方 CTA：复制配方名 → `sessionStorage` 落盘 → `scrollIntoView(#configurator)`（**当前未展开折叠容器**，是阶段 2B 待做项） |
| `assets/js/product-slider.js` | 1.0.1 | Hero 轮播 |
| `assets/css/configurator.css` | 2.9 | 配置器 + 阶段 2A 折叠样式（`min-width:1024px` 生效） |

**关键约束**：`configurator.js` 在 IIFE 求值时即绑定（脚本 footer 加载），**依赖 DOM 元素存在**，但**不依赖可见性**。因此 `<details>` 包裹是安全的（阶段 2A 已验证）；但任何 `getBoundingClientRect()` 派生的定位逻辑（如 `flagEmptyCustom` 的 `scrollIntoView`）在元素隐藏时会失准 —— 阶段 2A 已用「移动端 CSS 强制可见」规避。

---

## 5. 锚点清单 + 滚动机制

### 5.1 页面真实锚点（业务 id，摘除 WP 自动生成的 CSS/JS `id`）

| id | 标签 | 来源 |
|---|---|---|
| `#formulas` | SECTION | 模板（Stage 1 新增） |
| `#configurator` | SECTION | 模板 |
| `#configurator-drawer` | DIV | 模板 |
| `#inquiry-form` | SECTION | 模板 |
| **`#sf-sec-0` … `#sf-sec-5`** | H2 | **toc-nav.js 运行时注入**（按 DOM 顺序编号 6 个 H2） |
| `#modal-1` / `#modal-1-content` | DIV | cert-modal |
| `#gform_wrapper_2` / `#gf_2` / `#gform_2` / `#field_2_*` … | GF 表单 | Gravity Forms |
| `#tp-language` | TEMPLATE | TranslatePress |

> `sf-sec-N` 由 JS 按 **H2 在 DOM 中的出现顺序**分配 → **重排区块会让序号整体平移**。因为运行时自愈，页面本身不会坏；但**任何指向 `#sf-sec-N` 的外链/记录会失效**。8 页目前均为 6 个 H2 → `sf-sec-0…5`。

### 5.2 滚动机制（三套并存）

| 机制 | 文件 | 作用域 | 行为 |
|---|---|---|---|
| `html { scroll-padding-top }` | style.css:2997 | **仅移动 ≤1023px** | `64px`，让原生锚点跳转避开 57px 手机条 |
| `scroll-margin-top: 96px` | style.css:1620 | `#inquiry-form, #quote, #booking-form` | 桌面避开 81px 吸顶栏 |
| `scroll-margin-top: 0` | style.css:3001 | 同上三目标 | 移动端归零，避免与 `scroll-padding-top` 叠加成 160px 死空 |
| `scroll-margin-top: 96px` | style.css:7209 | `.sf-toc-target` | TOC 目标 |
| `quote-cta.js` | 1.0.0 | `a.sf-quote-cta` → `#inquiry-form/#quote/#booking-form` | 平滑滚动 + `settleAndCorrect()` 二次校正（对付懒加载把文档拉长）+ load 时深链重锚 |
| `toc-nav.js` | 2.0.0 | `.sf-toc` | 平滑滚动 + 事后 `scrollTo` 校正 |
| `formulas.js` / `configurator.js` | 1.0.0 / 2.2 | `#configurator` | `scrollIntoView(block:'start')` |

### 5.3 ⚠️ 发现的两个真实缺陷

**缺陷 1：`#formulas` 与 `#configurator` 的 `scroll-margin-top` 实测为 `0px`**

```
#inquiry-form    scroll-margin-top = 96px   ✅
#formulas        scroll-margin-top = 0px    ❌
#configurator    scroll-margin-top = 0px    ❌
```

后果：Hero 主按钮 `Build Custom Formula → #configurator`、次按钮 `Browse Standard Formulas → #formulas`、以及配方 CTA `Reference this formula →` 三者跳转后，**目标区块的顶部会被 81px 吸顶栏盖住**。Stage 1 报告 §12 已把它列入 `style.css` 改动（「`#formulas` / `#configurator` 的 `scroll-margin-top`：桌面 96px」），但**至今未落地**。→ 本批必做。

**缺陷 2：Hero 轮播第 2–4 张图缺 `loading="lazy"`**（见 §1.4）。非阻断，但属 CWV 优化项。

---

## 6. 8 页结构一致性报告

### 6.1 结论：**顺序与骨架 8/8 同构**，差异只在三处

| 差异 | 明细 | 性质 |
|---|---|---|
| 配方数量 | 4 / 3 / 3 / 2 / 2 / 2 / 2 / 3（合计 21） | 内容差异，**正常** |
| FAQ 数量 | soft-chews **2**，其余 7 页 **3** | 内容差异，**正常**（soft-chews 少一段） |
| 配置器组数 | 8 / 7 / 7 / 6 / 6 / 6 / 7 / 8 | 内容差异，**正常** |
| 高度极差 | Hero/KeyFacts/CTA = 0；其余由文案行数解释（见 §2.2） | 全部可解释，**非缺陷** |

### 6.2 ⚠️ **DOM 分裂（唯一真不一致，需处理）**

Related Dosage Forms 区块的 `wp:columns` **块数不一致**：

| 页 | `.sf-related-grid` 块数 | 各块列数 |
|---|---|---|
| soft-chews / tablets / powders / pastes | **2** | `[4, 3]` |
| drops / liquids / fish-oil / dental-chews | **1** | `[7]` |

- 桌面 1440 两者视觉**等价**（CSS `grid-template-columns: repeat(4, minmax(0,1fr))` 把 7 列重排成 4+3）
- 移动 375 两者都变 2 列 → 单块 7 列排出 2+2+2+1，双块排出 (2+2)+(2+1)，视觉亦等价
- **风险**：DOM 不同构 ⇒ 任何「按块」的批量改写脚本（含本批将写的重排脚本）会在这 4 页/那 4 页产生不同结果；也让回归比对更难判定。**建议本批顺手归并为单块 7 列**（与后 4 页对齐），归并后 `cmp`/sha 回归才干净。

---

## 7. 现有 CSS 可复用性

**规模**：`style.css` 455 个类 / `assets/css/configurator.css` 77 个类。

| 族 | 定义 | 可复用性判断 |
|---|---|---|
| **`.sf-section` / `--large` / `--medium` / `--xl`** | 分档 padding | ⚠️ **仅移动端断点生效**（`!important` 覆盖），桌面靠模板内联 `var(--wp--preset--spacing--80)`。**新建区块建议沿用同一内联 padding 模式**，保持一致 |
| **`.sf-dosage-grid`** | `display:grid; repeat(4,minmax(0,1fr)); gap:24px`；≤1023 → 2 列；≤768 → 1 列（gap 16） | ✅ **可直接复用**，专为剂型卡片网格设计 |
| **`.sf-related-grid`** | `.sf-dosage-grid` 的修饰类：media `aspect-ratio:4/3`、`.sf-tile{overflow:hidden}`、移动 `:active{scale(.98)}` | ✅ 可复用 |
| **`.sf-tile`** | flex 纵向卡 + 1px 边框 + radius 6 + hover 抬升 2px + media 框 + `p:last-child{margin-top:auto}`（等高对齐） | ✅ **「Custom Formula 过渡区」若要做卡片，直接用这个** |
| **`.sf-card` / `--flush` / `--roomy` / `--quote` / `__title-link` / `__more`** | 通用卡片 + 整卡点击（`::after` 覆盖）+ 焦点环 | ✅ 可复用；`--flush` 用于图文卡 |
| **`.sf-panel` / `--3` / `--4` / `--bare`** | 网格面板 + 上边框分隔 + 竖分隔线 | ✅ 可复用（How We Work 目前**未使用**，是**内联 `border-top`** 手写的 —— 若重排，可顺手切到 `sf-panel`） |
| **`.sf-spectable` / `__table` / `__caption`** | 速览表（`table-layout:fixed` + 5 列宽 + 品牌绿表头 + `--bg-light` 下移动端转块级 `data-label`） | 🔒 Key Facts 专用，下移只需移动 DOM，**样式无需改** |
| **`.sf-formulas` / `.sf-formula__*`（9 类）** | 手风琴 | 🔒 专用 |
| **`.sf-explore` / `__title` / `__chips` / `__chip` / `__btn`** | 内链 chips 行 | 🔒 专用，**不可藏进折叠区** |
| **`.sf-hero-inner`** | bg `#2E6B54`（深绿）+ 移动 padding 40/20 | 深色 Hero 底 |
| **深色区块** | Hero = `#2E6B54` 硬编码；CTA = `has-primary-background-color`（区块样式）；`has-bg-light` = 浅底交替 | ✅ 两种都在用；**新增过渡区块建议用 `has-bg-light` 或纯白，避免第三个深色** |

**结论**：新需求（Hero 极简、Custom Formula 过渡区）**不需要新建 CSS 族** —— `.sf-section` 内联 padding + `.sf-tile`/`.sf-card` + `has-bg-light` 足以覆盖；只有「Hero 无图版排版」可能需要 1 段新规则。

---

## 8. 建议方案

### 8.1 Hero 极简（删轮播 + 缩短高度）

**现状**：726px，其中右栏轮播 588px 撑起了整个高度；左栏文案区仅 385–471px。

**三个可选路径**（需你选一个）：

| 方案 | 做法 | 预估高度 | 取舍 |
|---|---|---|---|
| **A. 单栏居中（最彻底）** | 删 `wp:columns` + 右栏 + `sf-pslider`；H1/副标题/认证行/按钮居中，最大宽 ~800px | **~330px**（减 ~396px，-55%） | 首屏极快、LCP 大幅改善；但失去产品/工厂图，**品牌视觉变弱** |
| **B. 左文右图（静态单图，替换轮播）** | 保留两栏，把 `.sf-pslider` 换成 1 张静态 `<img>`（剂型图 `{剂型}.webp`），尺寸从 588 压到 ~440 | **~560px**（减 ~166px，-23%） | 保住视觉与图片；删掉 carousel JS + 3 张额外图 |
| **C. 双栏 + 背景图（Hero 背景化）** | 删右栏，把剂型图做 Hero 背景（深绿 `#2E6B54` + 图片叠加），文案左对齐 | **~440px**（减 ~286px，-39%） | 视觉最强、无额外 DOM；但需处理好文字对比度与移动端裁切 |

**文案精简建议**（8 页同步，三方案通用）：

| 元素 | 现文案 | 建议 |
|---|---|---|
| H1 | 保留（SEO 主词，勿动） | — |
| 副标题 | `Custom … OEM/ODM with flexible MOQ, fast sampling, and full regulatory support.`（~200 字符） | 截到「前半句 + OEM/ODM」：`Custom soft chews for joint, skin, calming, and digestive support. OEM/ODM, flexible MOQ, fast sampling.`（~110 字符，省 1–2 行） |
| 认证行 | `FDA · cGMP · ISO 9001 · FSSC 22000 · HACCP · BRC` | 保留（6 项信任状，一行不换行） |
| 按钮 | 3 个 | 建议压到 **2 个**：主 `Build Custom Formula`，次 `Browse Standard Formulas`；`Request a Quote` 作为细文字链保留或并入 CTA 区（**Hero 与页尾 CTA 功能重复**） |
| 面包屑 | `Home / Products / {剂型}` | 保留（SEO + 导航） |

> `Build Custom Formula → #configurator` 在新计划下是「展开态」目标 → 跳转高度更准，`scroll-margin-top` 修复后落点干净。

### 8.2 区块顺序调整方式

**目标顺序（按新计划）**：

| 现 | → | 目标 |
|---|---|---|
| 1 Hero | | 1 **Hero（极简）** |
| 2 **Key Facts** | ⬇️ 下移 | 2 **Standard Formulas**（自动回到 Hero 之后 = 第 2 点「移到配置器之前」） |
| 3 Standard Formulas | | 3 **Configurator** |
| 4 Configurator | | 4 **Custom Formula 过渡区块（新增）** |
| 5 How We Work | | 5 **Key Facts（下移到此）** |
| 6 FAQ | | 6 How We Work |
| 7 Related | | 7 FAQ |
| 8 CTA | | 8 Related |
| | | 9 CTA |

**两种实施方式**：

| 方式 | 做法 | 优点 | 风险 |
|---|---|---|---|
| **模板级移动（推荐）** | 在 8 个 `page-*.html` 里把整个 `wp:group` 块（含区块注释）**剪切到新位置** | 结构清晰、与现有模板一致、无运行时耦合 | 需同步改 8 个文件；`sf-sec-N` 序号平移（运行时自愈） |
| JS 运行时重排 | 用脚本 `insertBefore` 移动 DOM | 不动模板 | ❌ **不推荐**：SEO/无 JS 场景失效、CLS、与 toc-nav 竞争 |

**实施要点**：
1. **必须连同 `<!-- wp:group -->` 注释一起移动**（只移 HTML 会导致编辑器再保存时被注释覆盖回去 —— Stage 1 已踩过同类坑）。
2. `Key Facts` 段**不含 H2**（用 `<caption>` 做标题）→ 移动它**不影响 `sf-sec-N` 数量**，但仍会平移序号（因它在 Formulas 之前）。重排后 8 页仍应为 6 个 H2（`sf-sec-0…5`）。
3. `Key Facts` 现在紧跟 Hero（浅色/白底），下移后到 How We Work（`has-bg-light`）之前 → 需检查**底色相邻**：Hero(`#2E6B54`) → Formulas(白) → Configurator(白) → **Custom 过渡(建议 `has-bg-light`)** → **Key Facts(白)** → How We Work(`has-bg-light`) → …；相邻同底会糊成一片，建议过渡区用 `has-bg-light` 或 Key Facts 段补底色/上边框。
4. **顺带修复**：`#formulas` / `#configurator` 加 `scroll-margin-top: 96px`（桌面）+ 接入移动端归零规则。

### 8.3 Custom Formula 过渡区块设计（新增，8 页同步）

**定位**：Configurator 之后、Key Facts 之前。承接「标准配方不满意 → 走定制」的心理转折。

**建议形态（复用现有类，零新 CSS 族）**：

```
section.wp-block-group.has-bg-light-background-color        ← 浅底，与前后白底拉开
  h2（居中）"Need Something Different?"                      ← ⚠️ 会新增第 7 个 H2 → sf-sec 变 0…6
  p（居中，text-secondary）一句过渡文案
  wp:columns.sf-panel--3（3 列，复用 .sf-panel）
    ├ column → .sf-cell：大号编号/图标 + h3 + 一句说明
    ├ column → .sf-cell
    └ column → .sf-cell
  wp:buttons（居中）：主 CTA 「Start Your Custom Formula」→ #configurator
                     次（可选）「Send Requirements」→ #inquiry-form
```

**三列内容建议**（呼应现有 How We Work 的 7 步，不要重复）：

| # | 标题 | 说明方向 |
|---|---|---|
| 1 | `Your Spec, Our Formula` | 按你的成分/规格/风味目标做配方开发 |
| 2 | `R&D + Free Sample` | 1000㎡ 研发实验室 + 打样流程 |
| 3 | `Private Label Ready` | 包装/标签/合规文件一站式 |

> ⚠️ **H2 数量变化的影响**：新增 H2 → `sf-sec-0…6`（7 个）。若希望 TOC 干净，可**不用 H2 而用 `h2` 之外的语义容器 + `role="heading" aria-level="2"`**（与 Key Facts 用 `<caption>` 的既有做法一致），这样 TOC 保持 6 项。**需你裁定**。
>
> 另：不必新增深色底 —— 目前深色只有 Hero(`#2E6B54`) 与 CTA(`primary`)，中间插第三个深色会稀释「深色=行动点」的语义。

---

## 9. 改动文件清单

### 9.1 若采纳「Hero 极简 A/B/C + 重排 + Custom 过渡区」

| 文件 | 改动内容 | 处数 |
|---|---|---|
| `templates/page-{8 剂型}.html` | ① Hero 极简（删/换轮播 + 缩小高度 + 副标题精简；`wp:button` 与 HTML **同步**）② **移动 Key Facts 段**到 How We Work 之前 ③ **新增 Custom Formula 过渡区块** ④ 归并 Related 的 2 块→1 块 | 8 × 4 |
| `style.css` | ① `#formulas` / `#configurator` `scroll-margin-top: 96px`（桌面）+ 移动端归零 ② Hero 极简版排版规则（仅方案 A/C 需要）③ Custom 过渡区块微调（优先复用，尽量 0 改动） | 2–3 段 |
| `functions.php` | 版本号：`sinofresh-style` **2.10.38 → 2.10.39** | 1 行 |
| `assets/js/product-slider.js` / `hero-slider.js` | **方案 A：移除 enqueue**（Hero 无轮播）；方案 B/C：保留 | 0–1 行 |
| `assets/js/toc-nav.js` | **不动**（`if(!el.id)` 已兼容固定 id） | 0 |

### 9.2 若第 4 点「配置器保持默认展开」成立 → **额外需回滚阶段 2A**

| 回滚项 | 文件 | 备份 |
|---|---|---|
| 8 个模板的 `<details class="configurator__fold">` 包裹 + `.configurator__explore-row` | `templates/page-*.html` | ✅ |
| 折叠样式段（~150 行） | `assets/css/configurator.css` | ✅ |
| `.configurator__fold-desc` 并入 27m 移动字号规则 | `style.css` | ✅ |
| Lead time 措辞 `after packaging is ready` | `templates/page-*.html` | ⚠️ **此项与折叠无关，建议保留勿回滚** |

**备份位置**：`_backup/batch1-stage2-20260920-093741/`（12 文件：8 模板 + `style.css` + `functions.php` + `configurator.css` + `formulas.js`），改动前 md5 存于 `/tmp/b1/s2/pre_md5.txt`。

> 附带：`page-faq.html` 与 `page-services.html` 也含 `after packaging ready`（Stage 2A 只改了 8 个剂型模板）→ 若回滚/继续都请一并裁定是否统一为 `is ready`。

### 9.3 若继续阶段 2B（保留折叠）

`assets/js/configurator-fold.js`（新增 1.0.0）+ `assets/js/formulas.js`（1.0.0→**1.0.1**，跳转前展开）+ `functions.php`（enqueue 1 行，仅 `$is_dosage_page` 分支；`configurator.css` **2.9→2.10**）。

---

## 10. 待你确认（阻塞下一步）

| # | 问题 | 选项 |
|---|---|---|
| **1** | **冲突裁定**：新计划第 4 点「配置器保持默认展开」与已部署的阶段 2A 折叠冲突 | ① **回滚折叠**（放弃 2B）② **保留折叠**，第 4 点作废 ③ 折中：桌面折叠但默认 `open`（首屏展开，仍可手动收起） |
| **2** | Hero 极简走哪个方案 | A 单栏居中(~330px) / B 静态单图(~560px) / C 背景图(~440px) |
| **3** | Hero 按钮是否从 3 个压到 2 个（`Request a Quote` 去哪） | 保留 3 个 / 压到 2 个 / 文字链并入 |
| **4** | Custom 过渡区块是否用 `<h2>` | 用（TOC 变 7 项）/ 不用（`role=heading`，TOC 保持 6 项） |
| **5** | Related 区块 2 块→1 块 是否本批归并 | 归并（推荐）/ 不动 |
| **6** | `page-faq.html` / `page-services.html` 的 `after packaging ready` 是否统一 | 统一 / 不动 |
| **7** | `#formulas` / `#configurator` 的 `scroll-margin-top: 96px` 修复 | 本批顺手修（推荐） |

**本批核验门**（沿用既有标准）：8 页结构断言 → `cp` + `cmp -s` 源码↔Local 零差 → `grep "/ -->"` 零残留 → 19/19 页 HTTP 200 无 PHP 报错 → 掩码 sha256 回归（**注意 `<?php` nonce 12h 窗 + 必须预滚动量法**）→ 桌面 1440 + 移动 375 截图交付 → 5 条交互路径（Hero 主/次按钮、配方 CTA、TOC、深链）实测。
