# 扫描：配方详情页右栏「缺产品标题」（只读，未改任何字节）

> **状态：只读扫描完成，主题侧 0 字节、DB 0 行、服务器 0 写入。**
> 触发来源：用户截图确认「右栏从『简介』开始，H1 缺失」，并要求先扫描再动手。
> 扫描对象：`/formulas/{slug}/`（21 配方 × 2 语言 = **42 页**），断面＝`_backup/b2d-h4-candidates/`
> （H4 预检态，`2.10.59`）。
> 关联：`docs/agent-playbook.md` §② Hero、**§③ 媒体 + 参数区**、`docs/batch2d-stepH2a.md`、
> `docs/batchH2a-gates/gate-main-candidate.txt`。

---

## 0. 五问五答（结论速览）

| # | 问题 | 实测答案 |
|---|---|---|
| 1 | 右栏当前有没有 H1 元素？ | **没有任何标题元素**。`<h1>`–`<h6>` 在右栏内命中 **0**；右栏首个子元素是 `<p class="sf-fdetail2__intro">` |
| 2 | Hero 区有没有 H1？ | **有，且只有一个**。`<h1 class="sf-formula-hero__title">{{TITLE}}</h1>`，在 Hero band 内，文本＝产品名 |
| 3 | Hero 有 H1／右栏无 —— 是 H2a 主动省略还是遗漏？ | **都不是**。H1 **从未进过右栏**：自 `04beba5`（Batch 2C Step1 建此模板）起就在 Hero；H2a 的门更**明文断言 hero 逐字节不变**。真因＝**手册 §③ 图示与实现从未对齐**（见 §3） |
| 4 | 页面上 h1 元素总共几个？ | **恰好 1 个**（全页 1、`<main>` 内 1）。**全站 75/75 页都恰好 1 个** ⇒ 规范达标 |
| 5 | 补的话方案是什么？ | **推荐 C：右栏不放，Hero 承担**（见 §5 的三方案对照）。若确认要改，**必须先裁决**，因为 A 会动四批已冻结的 Hero 区 |

**一句话**：这不是缺陷，是**手册图示落后于实现**。页面的 H1 语义**完全合规**（单一 H1、位于正文首个内容块、文案准确）。

---

## 1. 现状：DOM 事实（逐层可核）

### 1.1 模板 `templates/single-sf_formula.html`（139 行）

| 行 | 结构 |
|---|---|
| 1 | `wp:template-part header` |
| **6–16** | **Hero band**：`<section class="… sf-hero-inner sf-formula-hero">` —— 面包屑 / `<span class="sf-fcard__use">` / **`<h1 class="sf-formula-hero__title">{{TITLE}}</h1>`（行 11）** / `<p class="sf-formula-hero__meta">` / 两个 CTA |
| **27–50** | **§③ 两栏带**：`<section class="… sf-fdetail2">` |
| 31–37 | 左栏 `section#gallery.sf-gallery.sf-fdetail2__media` → `[sf_formula_gallery]` |
| **38–46** | **右栏 `aside.sf-fdetail2__side`** → `{{FORMULA_INTRO}}` + `[sf_formula_params]` + `<a class="sf-fdetail2__cta">` |
| 52+ | 长文 / Specification / actives / content / FAQ / sampling / more / CTA |

> 右栏模板内容**只有三样**：简介、参数 `<dl>`、Request Sample 按钮 —— **无标题**。

### 1.2 渲染实测（42 页逐页核）

| 项 | 实测 |
|---|---|
| 右栏内 `<h1>`–`<h6>` 命中 | **0** |
| 右栏首个子元素 | `<p class="sf-fdetail2__intro">` |
| 简介词数 | n=42，**中位 55**，区间 **53–57**（落在 §③ 规格「50–80 词」内 ✓） |
| 全页 `<h1>` 计数 | **1**；`<main>` 内 **1**；class ＝ `sf-formula-hero__title`；文本 ＝ 产品名 |
| 标题大纲（`<main>` 内 DOM 顺序） | `h1`（Hero 产品名）→ `h2`（左栏 gallery「A Closer Look at …」）→ `h2` Specification → `h3` Standard Specs → `h2` Formula & nutrition → … |

**全站 H1 计数分布（75 页）**：`1 个 h1 : 75 页`；非 1 个的页 **0**。

### 1.3 H1 的文案来源

`{{TITLE}}` 由 `sinofresh_template_placeholders()` 替换（`functions.php:4273`，值＝`esc_html(get_the_title())`）。
⇒ **H1 文案来自 DB，不是模板字面量**；同一个值还供给面包屑当前项、gallery 的 H2、FAQ、JSON-LD。

---

## 2. 版本溯源：H1 从未进过右栏

| 提交 | 右栏内容 | H1 位置 |
|---|---|---|
| `04beba5`（Batch 2C Step1：建此模板） | — | **Hero**（`<h1 class="sf-formula-hero__title">`） |
| `cdcf4d3`（2D Step3：图集带移入详情页） | — | Hero |
| `c4f4437`（Batch G：媒体带变两栏） | `{{FORMULA_INTRO}}` + `[sf_formula_factsheet]` + CTA | Hero |
| **`eb47f6c`（H2a：重写媒体带 + 参数区）** | `{{FORMULA_INTRO}}` + **`[sf_formula_params]`** + CTA | **Hero（未动）** |
| `ebe8f50` / `4ca3aea` / HEAD | 同 H2a | Hero |

**H2a 对模板的改动只有两类**（逐行 diff 已核）：

1. 类名命名空间：`sf-fdetail-media__*` → `sf-fdetail2__*`（`__left` → `__media`）
2. 短码替换：`[sf_formula_factsheet]` → `[sf_formula_params]`

**H1 那一行前后完全一致**，且 H2a 的主门产物里明文写着：

```
docs/batchH2a-gates/gate-main-candidate.txt:15
  ok   [3] head/hero/Specification/FAQ/More/CTA/footer byte-identical on all 42 pages
```

⇒ **H2a 的批次边界就是「媒体带 + 参数区」，Hero 是它门里被保护的不变量**。
所以问题不在 H2a 的取舍，而在§3。

---

## 3. 真因：手册 §③ 的图示是设计稿，且与它自己的字段表矛盾

### 3.1 图示画了 5 个右栏元素，实测只实现 2 个

| §③ 图示元素 | 实测（42 页） |
|---|---|
| **H1（产品名）** | **0** —— 从未在右栏 |
| 简介（50–80 词） | **42/42** ✅（中位 55 词） |
| Flavor（chips） | **0** —— `style.css` 有 `.sf-fdetail2__chip`，但 `sf-fdetail2__chip` 渲染 **0/42 页** |
| Piece Weight / Pack Size | **42/42 与 20/42** ✅（走 `[sf_formula_params]`） |
| Suitable For / Life Stage | **0** —— 数据空（H3 已登记 renderer-first） |
| Quantity & Pricing（阶梯价表） | **0** —— `sf_formula_price_tiers` 全空（H5 扫描同日确认） |

⇒ 图中 **5 类元素里 3 类从未实现**。这**不是实现漏做**：H3 的裁决原文就是
「**renderer first, data later**」——渲染器已就位，等数据。但 **H1 不属这一类**：它不是"等数据"，而是**本就不该在这里**。

### 3.2 关键证据：图示下方的「权威字段表」里没有 H1

手册 §③ 在图**之后**给了精确的「数据源（精确）」表，逐字段列 meta key 与空值行为：

```
Flavor / Piece Weight / Pack Size / Suitable For / Life Stage
Quantity & Pricing / Certifications / Lead time
```

—— **8 个字段，没有一条是「标题」或「H1」**。
同处还有「参数区交互」小节，同样**只列这 6 个可选字段**。

⇒ §③ 内部**自相矛盾**：ASCII 图（旧单栏稿的遗留）带 H1，而**字段级规格（权威、更细）不带**。
⇒ 正确处置＝**改手册**（删掉图上那行 H1 并注明由 §② 承担），**不是改产品**。

### 3.3 §② 与 §③ 也互相矛盾

| 位置 | 原文 |
|---|---|
| **§② Hero**（手册 107 行） | `H1：产品名（如 Joint Support Soft Chews）` |
| **§③ 图示**（手册 126 行） | 右栏顶部 `H1（产品名）（字号 28px 粗体）` |

两处都写「H1」⇒ 若照字面执行会得到 **2 个 H1**（违反 Q4 的规范）。
可见 §③ 的那行 H1 是**从"还没有 Hero"的单栏设计稿里带过来的**，从未清理。

---

## 4. 三方案对照（含被隐藏的代价）

### A：Hero 的 H1 移到右栏（唯一 H1）

| 维度 | 影响 |
|---|---|
| SEO | ✅ 仍唯一 H1；但 **DOM 位置推迟** —— Hero 在 §③ 带**之前**，左栏 gallery 是 §③ 的**第一个**子块 ⇒ H1 会从「正文第 1 个内容块」掉到「左栏图集之后」 |
| **视觉** | ⛔ **首屏层级塌掉**。Hero 桌面高 **328px**（§② 明文）是按含 H1 计的；掏掉 H1 后绿带只剩面包屑 + use 标签 + meta + 2 个按钮，**且产品名要等到下面两栏才出现** |
| **样式** | ⛔ H1 现有 `clamp(36px, 4vw, 52px)` ＋ **白色**，是为**绿底**设计的；落到右栏的浅灰底（`bg-light`）要重设整套字号/颜色/行高 |
| **改动面** | 模板 2 处 ＋ `style.css` **Hero 段与第 38 段两处** ⇒ 触碰 **H2a / H2b1 / H3 / H4 四批已冻结的 Hero 区**，需重跑 75 页门 |
| JSON-LD | ✅ 详情页 Product 的 `name` 走 `get_the_title()`、`intro` 走 `get_the_title()`（`functions.php:789`）⇒ 与 H1 位置**解耦**，不会连带变 |
| 定级 | **不推荐** —— 换来「右栏多一行字」，代价是首屏视觉与四批冻结区 |

> ⚠️ 一处**需要澄清的误判风险**：`functions.php:4765` 确实有一条正则抓 `<h1>`（`'/<h1[^>]*>(.*?)<\/h1>/s'`），
> 但它抓的是**剂型页**模板 `page-{slug}.html`（用来给 8 个剂型页的 Product 取 `name`），
> **不读** `single-sf_formula.html`。⇒ 详情页动 H1 **不会**连带改 JSON-LD。这条要写清，免得误以为不能动。

### B：右栏用 h2 视觉呈现（Hero 保留 H1）

| 维度 | 影响 |
|---|---|
| SEO | ⚠️ H1 仍 1 个 ✅，但页面会出现**与 H1 逐字相同**的一个 h2 ⇒ **同一标题在页面上出现两次**。Google 不惩罚，**但没有收益**；屏幕阅读器会读两遍，标题大纲里「产品名」出现两次 |
| 语义 | ⚠️ 用一个 h2 去"充当"H1，既没解决 §③ 图的诉求（图上是 H1），又制造了重复标题 |
| 改动面 | 模板 1 处 ＋ 右栏标题样式 ⇒ **仍需动 Hero 之外的门**，且引入新样式 |
| 定级 | **不推荐** —— 零收益 + 新增重复标题 |

### C：右栏不放，Hero 承担 ✅（推荐）

| 维度 | 影响 |
|---|---|
| SEO | ✅ **完全合规**：单一 H1、位于正文首个内容块、文案准确（全站 75/75 页一致） |
| 视觉 | ✅ Hero 保留产品名大标题 ⇒ 首屏层级不变。有 Hero 的产品页把 h1 交给 Hero 是**主流做法**（Amazon / Apple 同构） |
| 改动面 | **0 字节**产品改动 |
| 收尾动作 | 改**手册**：§③ 图示删掉「H1（产品名）」那一行，并注明「H1 由 §② Hero 承担」⇒ 修的是**文档与实现的偏差**，不是产品 |
| 定级 | **推荐** |

**C 的可选加强（C+，视需要再定）**：如果诉求是「右栏视觉上没有锚点」而不是「SEO 需要 H1」，
正确做法是给参数区一个**不与产品名重复**的锚点，例如
`<h2 class="screen-reader-text">Key specifications</h2>`（仅屏幕阅读器可见，给 `<dl>` 提供可访问名）
或一个可见的小节标签（如 `Specifications at a glance`）。
**注意**：这是**新增内容**，不是修 H1 —— 要单独裁决，不要与 A/B 混为一谈。

---

## 5. 附带发现（与本次提问相邻，一并登记）

| # | 发现 | 性质 | 建议 |
|---|---|---|---|
| 1 | ⚠️ **右栏用的是 `<aside>`**（`templates/single-sf_formula.html:38` → `wp:group {"tagName":"aside"}`）。按 HTML 规范 `aside` ＝**与周围内容"边缘相关"**的内容；而这里放的是**产品自身的简介与参数**（主体内容），不是旁注 | 语义标注问题（非 H1 问题） | 可改为普通 `div`（去掉 `tagName`）—— 属**低风险 1 处改动**，但需单独裁决，别搭 H1 的便车 |
| 2 | 手册 §② 与 §③ **都写了 H1**，字面执行会得 2 个 H1 | 文档内部矛盾 | 已并入本报告 §3.3；修文档时一并清理 |
| 3 | §③ 图示里的 Flavor chips / Suitable For / Life Stage / Quantity & Pricing 四行**均 0/42** | 已知（H3「renderer first」、H5 阶梯价空） | 无需动作，但**图示应标注"待数据"**，免得下次又被读成"漏做" |

---

## 6. 证据索引

| 证据 | 位置 |
|---|---|
| 详情页模板（Hero 行 6–16，H1 在行 11；§③ 带行 27–50；右栏行 38–46） | `sinofresh-theme/templates/single-sf_formula.html` |
| `{{TITLE}}` 占位符来源 | `functions.php:4273`（`sinofresh_template_placeholders`） |
| 简介生成器（读 `get_the_title()`，与 H1 位置解耦） | `functions.php:777-816` |
| 剂型页 Product 抓 `<h1>` 的正则（**只读剂型页模板，勿误判**） | `functions.php:4765` |
| H2a 对模板的逐行 diff（只改类名与短码） | `git show eb47f6c -- sinofresh-theme/templates/single-sf_formula.html` |
| H2a 门明文断言 hero 逐字节不变 | `docs/batchH2a-gates/gate-main-candidate.txt:15` |
| H2a 批次边界声明（「Hero/Spec/actives/composition/FAQ/More 七块保留」） | `docs/batch2d-stepH2a.md` |
| §③ 图示 + 其后的权威字段表 | `docs/agent-playbook.md` 120–174 行、224–236 行 |
| 42 页断面 | `_backup/b2d-h4-candidates/formulas__*.html`、`zh__formulas__*.html` |

---

## 7. 停机声明

**⛔ 停在扫描，未改任何字节**（未动模板、未动 `style.css`、未动 `functions.php`、未动手册）。
本次为**只读**：全部结论来自源码 grep、42 页断面重解析、`git show` 版本比对、以及门产物文本。

**需要裁决的一项**：

> **§③ 的「H1」按 C 处理（改手册、产品 0 改动）—— 确认吗？**
>
> - 确认 **C** ⇒ 我改手册 §③（删掉图上 H1 那行 + 注明由 §② 承担），产品零改动。
> - 选 **A** ⇒ 我出 Step 1 方案（含 Hero 高度重算、右栏 H1 样式、四批冻结区的门重建），**先给方案不动手**。
> - 选 **B** ⇒ 同上，先给方案（含重复标题的取舍说明）。
> - 另需单独一句话：**附带的 `<aside>` 要不要改**（§5 #1）—— 建议改，但与本项分开裁决。
