# 批次 1 扫描报告 —— Hero 改造 / 区块顺序 / 配置器折叠

扫描时间：2026-09-20 08:5x　范围：8 个剂型页　**本次未改任何代码**
数据来源：`templates/page-{8}.html` 源码 + `sinofresh.local` 实测渲染（1440 / 375）+ `functions.php` enqueue + JS 源码
几何原始数据：`_backup/batch1-scan-20260920/geometry.json`、`_backup/batch1-scan-20260920/toc.json`
（同目录含测量脚本 `_b1_scan_measure.js` / `_b1_toc_probe.js`；主题 `tools/` 下为工作副本）

---

## 0. 三条先决结论（影响批次 1 的工作量）

| # | 结论 | 影响 |
|---|---|---|
| **A** | **目标 2「Standard Formulas 移到配置器之前」—— 现状已经满足。** 模板与渲染实测均为 Formulas(②) → Configurator(③) | 该项**无需改动**；需确认你看的是否旧截图 |
| **B** | 8 页结构**完全同构**，且是模板复制关系：section 序列 7 段逐页字节级同构、Hero 标签骨架 8/8 同（66 标签） | 改动**必须 8 页同步**，适合脚本化批量改写 + 逐页校验 |
| **C** | 现网**无任何 `<main>` 语义标签**（`hasMain=false`）；header template-part 后直接跟 section | 附带发现，非本批范围，仅记录 |

---

## 1. 8 页 Hero 现状

**结构（8 页骨架完全一致，66 个标签）**
`section.sf-hero-inner` → `nav.sf-breadcrumb`(Home / Products / 当前剂型) → `columns` →
├ 左栏 `column`(垂直居中)：`h1` → 副标题 `p`(18px) → 认证行 `p`(13px/600/letter-spacing:2px) → `wp-block-buttons`
└ 右栏 `column`：`group.sf-product-hero-image`(白卡/radius 12px) → `div.sf-pslider`(track + 4 slide + prev/next + dots + progress)

| 剂型 | H1 | 副标题（前 60 字） | 轮播首图 |
|---|---|---|---|
| soft-chews | Private Label Soft Chews for Dogs & Cats | Custom soft chews for joint, skin, calming, and… | soft-chews.webp |
| tablets | Private Label Pet Tablets for Dogs & Cats | Custom tablets for joint, multivitamin, skin,… | tablets.webp |
| powders | Private Label Pet Supplement Powders | Custom powders for probiotics, digestive… | powders.webp |
| pastes | Private Label Pet Supplement Pastes | Custom pastes for hairball control, digestive… | pastes.webp |
| drops | Private Label Pet Supplement Drops | Custom liquid drops for calming, oral care… | drops.webp |
| liquids | Private Label Liquid Pet Supplements | Custom liquid supplements for multivitamin, joint… | liquids.webp |
| fish-oil | Private Label Fish Oil for Dogs & Cats | Omega-3 fish oil in softgels, liquid, and pump… | fish-oil.webp |
| dental-chews | Private Label Dental Chews & Sticks for Dogs | Custom dental chews and sticks for plaque… | dental-chews.webp |

认证行 8 页统一：`FDA · cGMP · ISO 9001 · FSSC 22000 · HACCP · BRC`
轮播 8 页统一 4 张：`{剂型}.webp` + `fac-line.webp` + `fac-lab.webp` + `fac-cleanroom.webp`
Hero 渲染高度 8 页**恒为 726px**（桌面 1440）／935–974px（移动 375）

**按钮：当前 2 个（8 页相同）**

| 按钮 | 文案 / 样式 | href | 状态 |
|---|---|---|---|
| 1 | `Request a Quote` — `has-cta-background-color` 实色 | `#inquiry-form` | 生效（原生锚点 + `scroll-margin-top:96px`） |
| 2 | `Download Catalog` — `is-style-outline` | `#` | **占位，指向空**（模板内有 `TODO: 指向 PDF Catalog` 注释） |

> `Download Catalog` 的 `href="#"` 是 8 页唯一的无效链接，批次 1 顺手可一并处理。

---

## 2. 当前完整区块顺序（模板 = 渲染，已验证一致）

| # | 区块 | 模板标记 | id | 桌面高 (liquids) | 移动高 |
|---|---|---|---|---|---|
| 1 | Hero | `section.sf-hero-inner` | — | 726 | 935 |
| 2 | **Standard Formulas** | `section.sf-formulas` | **无 id** | **316** | 295 |
| 3 | **Configurator** | `section` + `wp:group` | `#configurator` | **1217** | 1914 |
| 4 | How We Work | `has-bg-light` 带背景 | — | 682 | 845 |
| 5 | FAQ | 无附加 class | — | 344 | 372 |
| 6 | Related Dosage Forms | `has-bg-light` 带背景 | — | 915 | 1393 |
| 7 | CTA / 询盘表单 | `has-primary` 主色背景 | `#inquiry-form` | 803 | 1295 |

**8 页 section 序列逐页比对 = 7/7 全同**（`id`/`class` 归一化后完全一致）。
文档总高 5611–6188px（桌面）；soft-chews 最长、pastes 最短。

> **你列的顺序「Hero → 首屏信息表 → 配置器 → Standard Formulas」与实测不符**：
> ① 配置器在 Formulas **之后**；② 页面里没有「首屏信息表」区块 —— 8 页 Hero 之后直接就是 Formulas，
> 且剂型页**完全没有 `<table>`**（全站只有 cooperation / services 两页有表格）。
> 「首屏信息表」最可能指的是 Hero 左栏的**信息块**（副标题 + 认证行），或是你记忆中另一版布局 —— 需你确认。

---

## 3. 配置器现状

**DOM 结构**（`section#configurator` → `h2` + `p` + `wp:html` 内 `div.configurator`）

```
h2「Build Your {剂型} Formula」          ← toc-nav 动态注入 id="sf-sec-1"
p（说明文案，居中）
svg.configurator__sprite                  ← <symbol> 图标库（13–34 个/页）
div.configurator                          ← flex row，gap 40px
├ div.configurator__options  (flex 65%)
│  ├ div.configurator__group[data-group] × 6–8   ← 维度组，每组 label + items
│  │  ├ div.configurator__label   (h4 + p.configurator__tip)
│  │  └ div.configurator__items   (button.configurator__item × N)
│  └ div.sf-explore   ← 「Explore more dosage forms」+ [sf_explore_chips] + Browse All Products
├ div.configurator__summary-col (flex 35%)
│  └ aside.configurator__summary   ← h3 + progress + 6–8 summary-row + submit
│                                    + cta-row(basket/pdf) + pdf-mail + actions(reset/copy) + note
├ div.configurator__mobilebar      ← 平板用 sticky Submit（≤1023px 显示）
├ div.configurator__bar            ← 手机底部条（trigger + count + Submit）
└ div.configurator__drawer[hidden] ← 手机抽屉（id=configurator-drawer）
```

**关键状态**

| 项 | 实测结果 |
|---|---|
| 默认展开 / 折叠 | **桌面完全展开**，无任何折叠容器（`.configurator` 全量渲染） |
| 桌面高度 | **967px（6 维）– 1710px（8 维）**，是全页最高区块 |
| 锚点 id | `#configurator`（section 上）—— **`scroll-margin-top: 0px`** ⚠️ |
| 移动端 | `≤1023px` 转纵向堆叠；`≤767px` 显示 `.configurator__bar`（`display:flex`）+ `#configurator-drawer`（默认 `hidden=true`）；`≤768px` `.configurator__summary-col` 改 `position:sticky; bottom:0` |
| 平板 769–1023 | 保留 `.configurator__mobilebar`（sticky Submit） |
| 抽屉/条状态 | 桌面 `bar=none / mobilebar=none / drawer.hidden=true`；移动 `bar=flex / mobilebar=none / drawer.hidden=true` |
| 维度数 | 6–8 个/页（soft-chews、dental-chews 最多 8） |
| 选项按钮数 | 30–68 个/页 |
| Submit 按钮数 | 每页恒 5 个（summary / mobilebar / bar / drawer 内 ×2） |

**JS 初始化**：`assets/js/configurator.js`（v2.2，30 KB，IIFE + ES5）
- 主逻辑绑定 `.configurator__group` / `.configurator__item` / `.is-selected` 状态同步、Custom 输入框 `setCustomOpen()`、summary 行刷新、Reset / Copy（含 clipboard 降级）、提交写回 GF 隐藏域
- 末尾另有 **minified IIFE（移动 bar+drawer）**：仅当 `.configurator__bar` 与 `#configurator-drawer` 同时存在时启动；负责计数、开合抽屉（`is-open` + `hidden` + 300ms 延时）、Reset 后刷新行
- ⚠️ 折叠改造的硬约束：**不能把元素移出 DOM**（事件已绑定），只能用 `hidden` / `max-height` / `<details>` 内容区

---

## 4. Standard Formulas 现状

| 项 | 结果 |
|---|---|
| DOM | `section.sf-formulas` → `h2` + `p` + N 个 `wp:html` 包 `<details class="sf-formula__item">` + 1 个 JSON-LD `ItemList` |
| 交互 | **原生 `<details>/<summary>` 手风琴**，**默认全部收起**（8 页 `anyOpen=false`） |
| 条目数 | 2–4 条（soft-chews 4 / tablets·powders·dental-chews 3 / 其余 2） |
| 区块高度 | **316px（2 条）– 440px（4 条）** ← 折叠态高度 |
| 单行 summary | 51px（`min-height:48px` + `padding:12px 0`） |
| 首条 details | 53px |
| 锚点 id | **无**（section 与 h2 都无 id）⚠️ |
| scroll-margin-top | 0px（section）；**但 h2 被 toc-nav 注入 `sf-toc-target` → 96px** |
| 展开后内容 | Ingredients / Guaranteed Analysis / Standard Specs 三段 + `button.sf-formula__cta[data-formula]` |
| 已有 JS | `assets/js/formulas.js`（v1.0.0）：CTA 点击 → 复制配方名到剪贴板（+ toast）→ `sessionStorage` 记 `sinofresh_formula_{slug}` → `scrollIntoView` 到 **`#configurator`** |

---

## 5. 现有锚点与滚动机制

**静态 id 清单（8 页一致，仅 3 个）**

| id | 位置 | 桌面 scroll-margin-top | 移动 scroll-margin-top |
|---|---|---|---|
| `#configurator` | 配置器 section | **0px** ⚠️ | **0px** ⚠️ |
| `#configurator-drawer` | 手机抽屉 | —（非跳转目标） | — |
| `#inquiry-form` | CTA section | 96px | 0px（由 `html{scroll-padding-top:64px}` 覆盖） |

**动态 id（toc-nav.js v2.0.0 运行时注入）** —— 剂型页确有 TOC（6 个 H2 ≥ 3 阈值）

| 动态 id | 对应标题 | 所在 section |
|---|---|---|
| `sf-sec-0` | Standard Formulas | `section.sf-formulas` |
| `sf-sec-1` | Build Your {剂型} Formula | `#configurator` 内 |
| `sf-sec-2` | How We Work | — |
| `sf-sec-3` | Frequently Asked Questions | — |
| `sf-sec-4` | Related Dosage Forms | — |
| `sf-sec-5` | Request a {剂型} Quote | `#inquiry-form` 内 |

注入逻辑：`toc-nav.js:105` `if (!item.el.id) item.el.id = "sf-sec-" + i;` + `:106` 加 class `sf-toc-target`
→ **序号 `i` 由 H2 顺序决定，脆弱**：任何 H2 增删/换序都会让 `sf-sec-N` 漂移。**Hero 锚点不得依赖它。**
→ 反向好消息：`if (!el.id)` 意味着**给 section 加固定 id 不会与 toc 冲突**。

**滚动机制清单**

| 机制 | 位置 | 行为 |
|---|---|---|
| `html{scroll-padding-top}` | style.css:2863 | **移动端 64px**；**桌面 = `auto`（即 0）** |
| `#inquiry-form{scroll-margin-top:96px}` | style.css:1623 | 桌面锚点偏移（sticky header 78px + 余量） |
| 移动端归零规则 | style.css:2865–2870 | `@media` 内把 `#inquiry-form/#quote/#booking-form` 的 margin 置 0，避免与 64px padding 叠加 |
| `.sf-toc-target{scroll-margin-top:96px}` | style.css:7076 | 所有被 toc 收录的 H2 |
| `.sf-toc` 隐藏断点 | style.css:7082 | `≤1100px` TOC 隐藏（**但 id/class 注入仍发生**） |
| `quote-cta.js` v1.0.0 | 全局 | `a.sf-quote-cta` → `#inquiry-form,#quote,#booking-form`；**`settleAndCorrect()`** 处理懒加载回流（滚动停止后重测 + 二次平滑），并 `history.replaceState` 更新 hash；load 时对深链再 anchor 一次 |
| `toc-nav.js` scroll | :55 / :136 | TOC 点击平滑滚动 + settle 后校正 |
| `formulas.js` scroll | :91–94 | 配方 CTA → `#configurator` 平滑滚动（**无 settle 校正**） |

**⚠️ 已确认的真 bug**：`#configurator` 的 `scroll-margin-top = 0`，而 sticky header 桌面 78px / 移动 65px
→ 现有 formulas.js 的「Reference this formula →」跳转会**把 `Build Your … Formula` 标题顶到 header 底下被遮住**。
批次 1 无论是否折叠，都应一并修正。

---

## 6. 8 页结构一致性报告

| 比对项 | 结果 |
|---|---|
| section 序列（7 段，id + class 归一化） | ✅ **8/8 全同** |
| Hero 标签骨架（66 标签） | ✅ **8/8 全同** |
| Hero 高度 | ✅ 恒 726px |
| Hero 按钮数与目标 | ✅ 8/8 均 2 个（1 实色 CTA + 1 outline 占位） |
| 配置器容器存在性 | ✅ 8/8 均含 options / summary-col / mobilebar / bar / drawer / sf-explore |
| 配置器维度数 | ⚠️ 6–8 不等（按剂型属性而定，**非结构差异**） |
| Formulas 手风琴结构 | ✅ 同构（均为 details + JSON-LD），条目数 2–4 不等 |
| FAQ 条目数 | 2–3（soft-chews 2，其余 3） |
| 差异化的只有文案与图片 | H1 / 副标题 / 配置器维度与选项 / 配方条目 / FAQ 问答 / Related 卡片 / `sf-explore` 芯片 |

**结论：8 页是同一模板的 8 份实例，改动可脚本化，但必须 8 页同批处理 + 逐页 `cmp` 校验。**

---

## 7. 建议方案

### 7.1 Hero 按钮

当前 2 个按钮中，`Request a Quote` 与拟新增的 `Build Custom` **语义高度重叠**（都指向转化/配置）。
建议按「主 / 次 / 第三」三层排布，而非简单追加成 4 个（移动端 4 个按钮会占掉两行，Hero 高度涨约 60–90px）：

| 序 | 文案 | 样式 | href | 说明 |
|---|---|---|---|---|
| 主 | `Build Custom Formula` | 实色 `has-cta-background-color` | `#configurator` | 替换原 `Request a Quote`；转化主路径更前置 |
| 次 | `Browse Standard Formulas` | `is-style-outline` | `#formulas` | **需给 section 新增 id** |
| 第三 | `Request a Quote` | 纯文本链接或 outline | `#inquiry-form` | 保留直接询盘入口（老访客习惯） |
| — | ~~`Download Catalog`~~ | — | — | 占位链接，建议**移出 Hero**（等 PDF 就绪再放回，或放到 CTA 区块） |

若你坚持保留 4 个按钮，需同步评估移动端换行后的 Hero 高度与轮播卡比例。

**锚点落地细节**
- 给 `section.sf-formulas` 加 `id="formulas"`（不与 toc-nav 冲突）
- 两个锚点都要处理 **sticky header 遮挡**与**懒加载回流**：
  - CSS：桌面 `#formulas, #configurator { scroll-margin-top: 96px }`；移动端接入现有归零规则
  - 更稳：复用 `quote-cta.js` 的 `settleAndCorrect()` 思路，让锚点按钮也走「平滑滚动 + 停止后重测校正」

**注意**：`section.sf-formulas` 自带 `padding-top: 48px`（spacing-80），若锚点落在 section 顶部，
标题会离 header 再低 48px。建议锚点落点以「H2 可见且不被遮」为准 —— 这一项需要实机视觉校验后再定 96 / 144。

### 7.2 区块顺序

**无需改动**（现状即 Formulas → Configurator）。若你的本意是「配置器要更靠后」（例如移到 How We Work 之后），
那是**另一种顺序**，需要你明确目标序列 —— 这会改变 toc 的 `sf-sec-N` 序号，属较大改动。

### 7.3 配置器「点击后展开」实现路径

推荐 **方案 A：原生 `<details>`**（与页面既有 Formulas / FAQ 手风琴同族，零 JS 依赖，可访问性最好）

```
<details class="configurator__fold">           ← 新增
  <summary> h2「Build Your {剂型} Formula」+ 说明 p </summary>
  <div class="configurator"> … 现有内容原样不动 … </div>
</details>
```

必做的五件事（缺一项就会出问题）：

| # | 事项 | 原因 |
|---|---|---|
| 1 | **把 `div.sf-explore`（Explore more dosage forms + 8 个内链芯片）留在折叠区之外** | 它在 `configurator__options` 末尾；折进去等于把内链整块藏起，内链/SEO 直接损失 |
| 2 | **深链自动展开**：load / `hashchange` 时若 hash 命中 `#configurator` 或 `#sf-sec-1`，置 `open = true` | 否则 Hero「Build Custom」和 TOC 点进来只看到一个收起条 |
| 3 | **`formulas.js` 跳转前确保已展开** | 「Reference this formula →」现在跳 `#configurator`，折叠后必须同步展开 |
| 4 | **修正 `scroll-margin-top`** | 折叠后目标高度变了，落点必须重算；同时修掉现有 0px 的遮挡 bug |
| 5 | **移动端重新验证** | `≤768px` 的 `.configurator__summary-col{position:sticky;bottom:0}` 与 `body:has(.configurator__bar)` 规则都依赖配置器高度，折叠后 sticky 行为会变 |

**预期收益**：桌面单页减少约 **1050–1570px**（配置器 1217 → 约 140px），文档总高从 5611–6188 降到约 4500 —— 这是本批对 CWV/首屏最实质的贡献。

**不推荐方案 B（JS + aria-expanded 自定义折叠）**：可控性更强但要新写 CSS + JS，且与 `configurator.js` 已有的
custom 输入框开合、抽屉开合两套状态机叠加，回归面大。

### 7.4 版本号策略（缓存破坏）

按现有规矩**只改对应行，不做全局替换**：

| 资源 | 句柄 | 现值 | 建议 |
|---|---|---|---|
| style.css | `sinofresh-style` | 2.10.38 | → 2.10.39 |
| configurator.css | `sinofresh-configurator` | 2.9 | → 2.10（若折叠样式写在此文件） |
| configurator.js | `sinofresh-configurator` | 2.2 | → 2.3（若加自动展开） |
| formulas.js | `sinofresh-formulas` | 1.0.0 | → 1.0.1（若加展开联动） |
| 新折叠脚本（若采用） | 新增句柄 | — | 1.0.0；**须仅在 8 剂型页 enqueue**（`functions.php:177–190` 的 `$is_dosage_page` 分支） |

---

## 8. 改动文件清单（预估）

| 文件 | 改动内容 | 页数/处数 |
|---|---|---|
| `templates/page-{8 剂型}.html` | ① Hero 按钮区改文案/顺序（`wp:button` 注释 + HTML 同步）② `section.sf-formulas` 加 `id="formulas"` ③ 配置器外包 `<details class="configurator__fold">` + `summary` 包裹 h2/p ④ 移出 `sf-explore` | 8 文件 × 4 处 |
| `style.css` | 折叠容器样式（若无现成手风琴样式可复用）＋ `#formulas`/`#configurator` 的 `scroll-margin-top`（桌面 96 段 + 移动归零段） | 2–3 段 |
| `assets/css/configurator.css` | 折叠态与展开态布局微调（`summary` 内 h2 间距、折叠后 `summary-col` sticky 兜底） | 1–2 段 |
| `assets/js/configurator.js` | 深链命中时自动展开 + `hashchange` 处理（若走方案 A 且用 JS 增强） | 1 段 |
| `assets/js/formulas.js` | 跳转 `#configurator` 前先展开折叠容器 | 1 处 |
| `assets/js/toc-nav.js` | 一般**不动**（`if(!el.id)` 已兼容固定 id）；仅当 TOC 点击折叠目标需联动时改 | 0–1 处 |
| `functions.php` | 新脚本 enqueue（若新增折叠脚本）＋ 版本号更新 | 1–2 行 |
| `theme.json` | 一般不动（`spacing-60` 与 `spacing-80` 同为 48px 的冗余非本批范围） | 0 |

**核验门（沿用你的既有标准）**：8 页 `grep` 结构断言一致 → `cp` + `cmp -s` 源码↔Local 双向零差 → `grep "/ -->"` 零残留 →
8 页全 200 无 PHP 报错 → 折叠前后掩码 sha256 基线对比（注意 nonce 12h 窗，需重取基线）→ 桌面 + 移动截图交付。

---

## 9. 扫描阶段的待确认项（★ 已于 09:0x 全部确认 —— 结论见「第二部」，本节保留作追溯）

1. **区块顺序**：现状已是 Formulas → Configurator。是「保持现状、不做改动」，还是你实际想要别的顺序（请给目标序列）？
2. **Hero 按钮**：接受 7.1 的「主 `Build Custom` / 次 `Browse Standard Formulas` / 保留直接询盘入口 / `Download Catalog` 移出 Hero」三层排布，还是要**追加**成 4 个按钮？
3. **配置器折叠**：桌面与移动端**都**默认折叠？还是桌面折叠、移动端保持现状（已有底部条 + 抽屉）？
4. **「首屏信息表」指什么**：Hero 左栏信息块（副标题 + 认证行）？还是你希望**新增**一个参数速览表（那属于新增需求，不在本次扫描范围内）？

---

# 第二部：确认结果与落地方案（2026-09-20 09:0x 用户已确认）

| 项 | 决定 |
|---|---|
| 区块顺序 | **保持现状，不改**（现状已满足） |
| Hero 按钮 | **三层排布**（3 个按钮，`Download Catalog` 移出） |
| 配置器折叠 | **仅桌面折叠**；移动端保持现状（底部条 + 抽屉不变） |
| 「首屏信息表」 | **确认为新增需求** → 参数速览表，见 §11 |

## 10. 落地方案

### 10.1 Hero 按钮（三层）

| 层 | 文案 | 样式 | href |
|---|---|---|---|
| 主 | `Build Custom Formula` | 实色 `has-cta-background-color` | `#configurator` |
| 次 | `Browse Standard Formulas` | `is-style-outline` | `#formulas`（**新增 id**） |
| 三 | `Request a Quote` | 去按钮外观，改纯文字链（保留下划线／箭头） | `#inquiry-form` |
| — | ~~`Download Catalog`~~ | **移除** | — |

- 模板改动：`wp:buttons` 内 **`wp:button` 块注释与 HTML 必须同步改**（只改 HTML 会导致编辑器再保存时被注释覆盖回去）
- 移除后 8 页 `href="#"` 死链**归零**（`Download Catalog` 是剂型页唯一的无效链接）
- `section.sf-formulas` 新增 `id="formulas"`（`if(!el.id)` 逻辑保证不与 toc-nav 冲突）

### 10.2 「仅桌面折叠」的实现细节（需你知晓）

**「仅桌面折叠」不能只靠 CSS** —— `<details>` 的 `open` 是 DOM 属性，无法用媒体查询强制展开。
需要一个约 25 行的断点联动脚本：

```js
const mq = matchMedia('(min-width: 1024px)');           // 与配置器现有断点一致
function sync() {
  if (mq.matches) { fold.open = false; summary.style.pointerEvents = ''; }
  else { fold.open = true; summary.style.pointerEvents = 'none'; }  // 移动端不可收起
}
mq.addEventListener('change', sync); sync();
```
外加三项：① `hashchange` / load 命中 `#configurator` 时桌面自动 `open`　② `formulas.js` 跳转前展开　③ 移动端 `summary` 设 `cursor:default` 且不显示开合图标。

**折叠后必须重验的移动端项**（虽然移动端不折叠，但 DOM 多了一层 `<details>`）：
`≤768px` 的 `.configurator__summary-col{position:sticky;bottom:0}`、`body:has(.configurator__bar)` 规则、抽屉开合。

**预期收益（桌面）**：配置器 1217 → 约 140px，单页减约 **1080px**（8 页合计约 8600px 文档瘦身）。

## 11. 参数速览表草案（新增需求）

**位置**：Hero（①）之后、Standard Formulas（原②，顺延为③）。**不放 H2**（避免改变 TOC 结构与 `sf-sec-N` 序号）；用 `h2` 之外的语义容器 + 表格定义标题。

**字段（4 项）与 8 页真实取值** —— 全部来自页面现有数据（FAQ 首问 + Formulas `Standard Specs`），**无新编造**：

| 剂型 | Unit size | Pack options | Shelf life | MOQ |
|---|---|---|---|---|
| Soft Chews | 2 g/piece | 60/90/120 per bottle | 18 months | from 500–1,000 units |
| Tablets | 1 g/tablet | 60/120/180 per bottle | 24 months | from 1,000 units |
| Powders | 4/8/16 oz jar | — | ⚠️ 18 **或** 24（源数据冲突） | from 500 units |
| Pastes | 50/60/100/120 g tube | — | 24 months | from 500 units |
| Drops | 30/50 ml dropper bottle | — | 24 months | from 500 units |
| Liquids | 8/16/32 oz pump bottle | — | 24 months | from 500 units |
| Fish Oil | 8/16/32 oz pump bottle | — | 24 months | from 1,000 units |
| Dental Chews | 15–20 g/piece | 7/14/28 或 14/28/56 per bag | 18 months | from 1,000 units |

**实现建议**：语义 `<table>`（便于搜索引擎与 AI 抽取结构化数据）+ 极简无竖线样式，表头用品牌绿 `#5ab735`。
而非卡片网格 —— 这是「参数对照」语义，表格更准确，也正好补上剂型页目前**完全没有表格**的空白。

**两处源数据问题需你裁定**：
1. **powders 保质期冲突**：该页两种配方分别写 18 与 24 months，速览表该取哪个？
2. **MOQ 答案措辞不统一**：`liquids` / `fish-oil` / `dental-chews` 缺后半句 `New brands can start with small trial orders.`，其余 5 页有 → 建议统一补齐。

**还需你定**：是否加第 5 个字段（如 `Certifications`、`Lead time`、`Dosage form`）？

## 12. 确认后的最终改动清单（替代 §8 的「预估」）

| 文件 | 改动内容 | 处数 |
|---|---|---|
| `templates/page-{8 剂型}.html` | ① Hero 按钮改三层（`wp:button` 注释与 HTML **同步**）② `section.sf-formulas` 加 `id="formulas"` ③ **新增参数速览表区块**（Hero 后）④ 配置器外包 `<details class="configurator__fold">` + `summary` 包裹 h2/p | 8 文件 × 4 处 |
| `style.css` | ① 速览表样式（极简无竖线、表头品牌绿）② `#formulas` / `#configurator` 的 `scroll-margin-top`：桌面 96px、移动端接入现有归零规则（style.css:2865 段） | 3 段 |
| `assets/css/configurator.css` | 折叠容器样式（**仅 `min-width:1024px` 生效**）+ `summary` 内 h2 间距 + 移动端 `summary` 不可收起外观 | 2 段 |
| `assets/js/configurator-fold.js`（**新增**） | 断点联动（≥1024 收起 / <1024 强制展开且 `pointer-events:none`）+ load/`hashchange` 深链自动展开 | 新文件 1.0.0 |
| `assets/js/formulas.js` | 跳转 `#configurator` 前先展开折叠容器 | 1 处；版本 1.0.0 → **1.0.1** |
| `functions.php` | 新脚本 enqueue（**仅** `$is_dosage_page` 分支）+ 版本号 | 1–2 行 |
| `assets/js/toc-nav.js` | **不动**（`if(!el.id)` 已兼容固定 id；速览表不放 H2 故 TOC 不受影响） | 0 |

**版本号**：`sinofresh-style` 2.10.38→**2.10.39**；`sinofresh-configurator`(css) 2.9→**2.10**；`formulas` 1.0.0→**1.0.1**；新增 fold 脚本 **1.0.0**。
严格**按句柄整行改 + grep 复核**（4 个句柄共用 `'1.0.0'`，严禁全局替换）。

**核验门**：8 页结构断言 → `cp` + `cmp -s` 源码↔Local 零差 → `grep "/ -->"` 零残留 → 8 页全 200 无 PHP 报错 →
掩码 sha256 对比（**注意 nonce 12h 窗，需重取基线**）→ 桌面 1440 + 移动 375 截图交付 → 折叠/展开/深链/TOC/配方跳转 5 条交互路径实测。

