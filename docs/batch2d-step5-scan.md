# Batch 2D Step 5 — 扫描：剂型页「核心事实行 + Direct Answer 摘要块」

> 状态：**只扫描，未动手**。等确认后开工。所有数字为 dev 站实测（`-u sfdev:…`，`/products/<slug>/`），
> 几何原档 `docs/b2d-step5-shots/geometry.json`，截图 `docs/b2d-step5-shots/01-soft-chews-hero-{1440,375}.png`。

---

## 0. 三个必须先说的发现

1. **8 个剂型页已经有"核心事实表"了** —— `.sf-spectable` 的 *Typical specifications* 五列表
   （Unit size / **Pack options** / Shelf life / **MOQ** / **Lead time**），只是位置很深（第 4 段，Hero+卡墙+配置器之后）。
   本轮要的 5 个字段里，**MOQ / Production lead time / Packaging 三项与它重叠** ⇒ 有重复与"双真源"风险（见 §8）。
2. **Hero 与卡墙之间只有 24px**（WP 顶层区块 gap），插一条新 section 是纯加法、不需要动任何现有元素。
3. **点轨靠 H2 顺序编号**（`id = "sf-sec-" + i`）⇒ 新块**只要不带 H2，点轨与既有锚点全不动**；
   一带 H2，7 个点全部移位、`#sf-sec-N` 全部重编。`.sf-spectable` 当初就是为这个理由不带标题（用 `<caption>` 提供可访问名）——有先例可循。

---

## 1. 8 个剂型页 Hero 当前结构（结构完全同构）

模板行号 1–27，八页逐字节同构（`awk` 实测 hero 闭合行**都是第 27 行**）：

| 行 | 元素 | 说明 |
|---|---|---|
| 1 | `wp:template-part header` | 吸顶导航 |
| 3 | `<!-- Block 2: Hero -->` | |
| 4 | `<section class="wp-block-group sf-hero-inner" style="padding-top/bottom: var(--wp--preset--spacing--80)">` | `spacing-80` = **48px**（theme.json） |
| 5 | `<!-- sf-schema-desc: … -->` | **JSON-LD description 的唯一来源**（注释形态，见 §11） |
| 7 | `<nav class="sf-breadcrumb sf-breadcrumb--d3" aria-label="Breadcrumb">` | Home / Products / {剂型} |
| 10 | `<h1 class="has-text-align-center …" style="font-size:clamp(36px,4vw,52px)">` | 居中，白字 |
| 13 | `<p class="has-text-align-center has-card-white-color …" style="font-size:18px">` | 事实副标题（八页**同一句**） |
| 16 | `wp:buttons` flex 居中，`margin-top: spacing-40`(32px) | 两个 CTA |
| 27 | `<!-- /wp:group -->` | Hero 结束 |

副标题（八页完全相同）：
`8 dosage forms · FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC · Flexible MOQ · Export to 30+ countries`

CTA：`Browse Standard Formulas`（`href="#formulas"`，品牌橙 243×48，`border:0`）+ `Build Custom Formula`（`href="#configurator"`，描边 203×48，`border:2px`）。

**Hero 几何实测（soft-chews，两页交叉一致）**

| | 1440 | 375 |
|---|---|---|
| hero 盒 | y 120→448，**高 328** | y 91→590，**高 499** |
| 面包屑 | y 168–186 | y 131–148 |
| H1 | y 210–268（h=57） | y 172–291（h=119，四行） |
| 按钮 | 高 48 | 高 48 |
| 文档高 | 7184 | 11732 |

> 副标题段落仍在模板里渲染，但**已经不喂 JSON-LD** 了：`description` 先匹配 `<!-- sf-schema-desc -->` 注释，
> 注释命中后 `elseif` 的 18px 段落分支永不执行（functions.php:3310）。所以这段 18px 文案目前是"只给人看"的冗余。

## 2. Hero 与配方卡墙之间有没有空隙可插入

有，而且是**现成的**：

```
hero  section  y 120..448      （内边距 48/48 计入盒内）
#formulas 区块  y 472..1209     ← 中间只有 24px，就是 WP 的 block gap
   └ h2 "Standard Formulas" 落在 y 520（= 472 + 48 内边距）
```

⇒ 在 hero 的 `<!-- /wp:group -->`（第 27 行）与 `<!-- wp:group … anchor:"formulas"`（第 29 行）之间插一个顶层 section 即可，
**零 CSS 手术、零既有元素改动**。1440 下新块从 y=472 开始，仍在首屏（视口 900）内。

## 3. 核心事实行的最佳插入位置

**推荐：Hero 之后、`#formulas` 之前，作为新的顶层 section（不是塞进 Hero 内部）。**

理由（都基于实测）：

* 塞进 Hero 内会让 hero 盒变高：375 下 hero 已经 499px 高、底边在 y=590，再塞进一条 5 字段表会把它推到 y≈850+，**反而把事实行挤出首屏**；
* Hero 是 `.sf-hero-inner`，被 6 处 CSS 引用、是 `27s` 那条"给裸顶层 group 补 38px 内边距"规则的**唯一例外**，还有"hero 必须是第一个元素"（style.css:1856）的历史约束 —— 不动它最省事；
* 新 section 用页面主色纸白/雾白，与站点"细线代替阴影"的语言一致；`.sf-spectable` 已证明"无标题数据带"这条先例可行。

## 4. Direct Answer 摘要块的位置：合并还是分开

**推荐：与核心事实行合成一个 section，且事实行在前、摘要段在后。**

* 合并的理由：同一件事（"这页在卖什么、什么条件"）不该占两个 section，也不该让点轨/锚点承担两次风险；
* 顺序的理由是首屏覆盖率的实测差：375 下新块从 y≈614 开始，视口 812（iPhone 常见）时
  **事实表在前** ⇒ 表头（44px）与前 1–2 行（MOQ）能进首屏；
  **摘要段在前** ⇒ 50–80 词在 375 下约 5–6 行 ≈ 150px，事实表会被推到 y≈790 之后，**首屏看不到任何字段**。1440 下两种顺序都在首屏内，分不出差别，所以按窄屏定顺序。
* 形态上分区：事实行是结构化数据（表/定义列表），摘要段是一句话，二者用 title/caption 或一条细线分隔即可，不需要两个标题。

## 5. 现有可复用 CSS（都是现成的，不需要新造组件）

| 类 | 位置 | 形态 / 可复用点 |
|---|---|---|
| `.sf-hero-inner` | style.css:1879 | `background:#2E6B54`；内页 hero 色 |
| `.sf-spectable` / `__table` / `__caption` | 1894 / 1898 / 1916 | **首选复用**：5 列表 + `table-layout:fixed` 列宽 + 绿底大写表头（墨字 5.8:1，白字只有 2.7:1 所以没用白字）+ **≤767px 自动堆叠成"标签:值"行**（`td::before{content:attr(data-label)}`）+ `<caption>` 提供可访问名（**不带 H2**） |
| `.sf-keyfacts` | 6553 | /services/ 的 2 列（Item/Detail）商业条款表，`max-width:720px` 居中；字段名恰好就是 MOQ / Sampling / Lead Time / Payment / Trade Terms |
| `.sf-spec-list` / `__row` / `__term` / `__value` | 2064 起 | `<dl>` 形态（38% / 1fr 两列，`<dt>` 13px 次色 + `<dd>` 14px 粗体主色）。⚠️ 用 `<dt>/<dd>` 形态是**安全**的（见 §11） |
| `.sf-cell` | 559 起 | 面板里的"细线单元格"（顶边 3px 品牌绿），适合做 inline 标签行 |
| `.sf-strip` / `.sf-claim` | 495 起 | 首页的 claim 条 |
| `.sf-faq` / `.sf-tile` / `.sf-actives` | — | 同页其它段落的既有语言，新块可参照节奏 |

另外现成的排版常量：`--wp--preset--spacing--{20,30,40,50,60,80,100}` = 16/24/32/40/48/48/64px；
颜色 `brand-green #5AB735`、`primary #1B4D3E`、`bg-light #F3F6F4`、`border-light #DCE2DF`、`text-secondary #5F6B65`、`cta #B54E0F`。

## 6. 8 页当前 H1 文案

| slug | H1 |
|---|---|
| soft-chews | Private Label Soft Chews for Dogs & Cats |
| tablets | Private Label Pet Tablets for Dogs & Cats |
| powders | Private Label Pet Supplement Powders |
| pastes | Private Label Pet Supplement Pastes |
| drops | Private Label Pet Supplement Drops |
| liquids | Private Label Liquid Pet Supplements |
| fish-oil | Private Label Fish Oil for Dogs & Cats |
| dental-chews | Private Label Dental Chews & Sticks for Dogs |

（各页 `<!-- sf-schema-desc -->` 也各不相同，形态统一为 `Custom {剂型} for {功效列举}. OEM/ODM with flexible MOQ, fast sampling, and full regulatory support.`）

## 7. 核心事实的数据来源：**全是硬编码，没有 post meta**

* `register_post_meta()` 全站只有一处，注册的是 CPT `sf_formula` 的 4 个字段（functions.php:451）。**8 个剂型页是 `page`，零 meta**。
* 因此五个字段目前散落在模板里，**每页一份、八份独立**：

| 字段 | 现住址 | 八页是否同值 |
|---|---|---|
| MOQ | `.sf-spectable` 第 4 列 + FAQ 第 1 问 | **不同**（500 / 500–1,000 / 1,000） |
| Production lead time | `.sf-spectable` 第 5 列 | 同值 `7–15 working days after packaging is ready` |
| Sample lead time | "How We Work" 第 03 步 `Detailed quotation plus samples delivered in 3–7 days`（/services/ 写的是 `3–7 working days · $200`） | 同值，但**两处措辞不一致**（days vs working days） |
| Certifications | Hero 副标题 `FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC` | 同值；与 Organization schema 的 6 条 `EducationalOccupationalCredential` 一致 |
| Packaging | 各页配置器的 `data-group="packaging"` 选项集（7/5/4/4/4/4/4/4 项）+ `.sf-spectable` 的 Pack options 列（6 页是 `—`） | **不同，且 spectable 那一列基本是空的** |

八页逐页值（供写文案时直接取用）：

| slug | MOQ | Unit size | Pack options（spectable） | Shelf life | Packaging（配置器选项集） |
|---|---|---|---|---|---|
| soft-chews | from 500–1,000 units | 2 g/piece | 60/90/120 per bottle | 18 months | Aluminum Stand-up Pouch, Aluminum Foil Pouch with Zipper, Plastic Bottle, Jar, Blister Pack, Box + Foil, Custom |
| tablets | from 1,000 units | 1 g/tablet | 60/120/180 per bottle | 24 months | Plastic Bottle, Jar, Blister Pack, Foil Pouch, Custom |
| powders | from 500 units | 4/8/16 oz jar | — | 18–24 months | Jar, Foil Pouch, Stand-up Pouch, Custom |
| pastes | from 500 units | 50/60/100/120 g tube | — | 24 months | Plastic Tube, Metal Tube, Aluminum Tube, Custom |
| drops | from 500 units | 30/50 ml dropper bottle | — | 24 months | Dropper Bottle, Glass Bottle, Plastic Bottle, Custom |
| liquids | from 500 units | 8/16/32 oz pump bottle | — | 24 months | Plastic Bottle, Glass Bottle, Bottle with Cup, Custom |
| fish-oil | from 1,000 units | 8/16/32 oz pump bottle | — | 24 months | Plastic Bottle, Glass Bottle, Pump Bottle, Custom |
| dental-chews | from 1,000 units | 15–20 g/piece | 7/14/28 or 14/28/56 per bag | 18 months | Foil Pouch, Stand-up Pouch, Box, Custom |

## 8. 现有事实类组件盘点（重复风险的实际范围）

```
.sf-spectable   8 个剂型页各 1 张（每页 4 处引用）    ← Typical specifications，5 字段
.sf-keyfacts    /services/ 1 张                       ← MOQ / Sampling / Lead Time / Payment / Trade Terms
.sf-statbar     首页 64 处 + /factory-tour/ 34 处     ← 数字条，另一个形状
.sf-strip       首页 2 处
```

⇒ 剂型页上，**MOQ 会在站点里出现第 3 次**（FAQ 第 1 问、`.sf-spectable`、新的核心事实行）。
这是本批**最需要拍板的一件事**（D1）。

## 9. 方案

### 一、核心事实行

* **位置**：Hero 之后、`#formulas` 之前（第 28 行插入），作为新的顶层 `wp:group` section。**不塞进 Hero 内部**（§3）。
* **字段**：MOQ / Sample lead time / Production lead time / Certifications / Packaging（5 项，按用户给定）。
* **形态**：**推荐沿用 `.sf-spectable` 的表格形态**（新建 `.sf-facts` 一组类，复用其视觉语言与 ≤767px 堆叠逻辑），
  理由：①"真数据用真表格"是 /services/ 的既定做法（注释里写明是给 SEO/GEO 的）；②窄屏堆叠已有实现可抄；
  ③`<caption>` 能提供可访问名而**不用 H2**。
  备选：`<dl>` 网格（更紧凑，桌面可两列排布，5 项 → 3+2）。**不推荐 inline 标签流**：5 个字段值较长（Packaging 最多 7 项），标签流在 375 下会碎成难读的短行。
* **数据来源**：**八页各自硬编码在模板里**（与现状一致，单一真源就在该页自己的模板中）。
  不引入 post meta：注册 meta 会新增一套后台编辑面与同步风险，而 8 页的值本来就不同、改动频率低。
  *Packaging 取值建议改从该页配置器的 `data-group="packaging"` 选项集抄写*，因为 spectable 那一列 6 页是 `—`（见 D3）。

### 二、Direct Answer 摘要块

* **位置**：与事实行**同一个 section**，排在**事实行之后**（§4 的首屏实测）。
* **内容**：50–80 词，含 产品名 / 剂型 / 核心卖点 / MOQ / 交期。
* **模板 + 变量**：8 页**同一条模板句**，变量 4 个：`{剂型}`、`{功效列举}`（取自各页自家 `sf-schema-desc`）、`{MOQ}`、`{包装形态}`。
  这样 8 页读起来一致（GEO 要的是可抽取的模式），又保留每页差异。
  ⚠️ 全英文、不混排（沿用第 4 批 D2 的口径）。

### 三、与现有模块的交互

| 模块 | 是否受影响 | 依据 |
|---|---|---|
| **K1/K2 配方卡**（`[sf_formula_grid]`） | 否 | 新块在 `#formulas` **之前**，是独立顶层 group；卡墙的 `id="formulas"` 与锚点不动 |
| **配置器** | 否 | 不动其 markup；Packaging 只**读**它的 `data-group="packaging"` 文案 |
| **点轨 `toc-nav`** | **不变**（前提：新块不带 H2） | 点轨只收 `h2`（`root.querySelectorAll("h2")`），本页 7 个目标；编号 `sf-sec-0..6` 由 H2 顺序决定，加 H2 会全部移位 |
| **入队资源** | **不变**，只要纯 markup + CSS | 本页现役：CSS `sinofresh-style`(2.10.x) + `configurator.css`(2.9)；JS sticky-header 1.0.0 / ui-components 1.0.0 / mobile-nav 1.1.0 / basket 1.3.0 / quote-cta 1.0.0 / **toc-nav 2.0.0（剂型页在入队白名单里）** / configurator 2.3 / formulas 1.1.0。新块**不需要新 JS**（无交互）。唯一的入队变化是 `style.css` 版本号（全站 75 页的 `?ver=` 会变） |
| **JSON-LD** | **不变**（前提：不用 `<span class="sf-spec-term">`） | 见 §11 |

### 四、回归点（按本项目的四个门 + 两个补充）

| 门 | 本批预期 |
|---|---|
| **限定证明**（纯新增） | 本批是**纯新增**（只在 8 个模板各插一段 + style.css 追加一段），所以走最便宜的形态：**把新增块删掉后逐字节等于基线**（8 页）；其余 67 页只差 `?ver=`。⚠️ 若采纳 D1 的"精简旧表"选项，就变成**改+删批次**，必须换**重建式门**（第 4 批那套：期望值只由基线推出） |
| **掩码回归** | 预期**只有 8 个剂型页变化** ✓。但**必须先归一化 `?ver=` 令牌**，否则版本号一升 **75 页全 DIFF**（无 ver 掩码，实测）。配一个**资源清单门**，证明只有 `style.css` 从 2.10.x 迁到 2.10.x+1，没有别的资源动 |
| **JSON-LD deep-equal** | 成立。剂型页 Product schema 是**从模板文件正则解析**的，不读渲染 HTML：`name`←`<h1>`、`description`←`<!-- sf-schema-desc -->`（`elseif` 18px 段落是死分支）、`image`←按 slug 在 uploads 里 glob、`additionalProperty`←模板里的 `<span class="sf-spec-term">`（**模板 0 处 ⇒ 现在根本没这个键**）。新块用 `<table>/<td>` 或 `<dl>/<dt>/<dd>`，这些正则**一条都不命中** ⇒ 逐键相同 |
| **浏览器 E2E** | 1440 + 375：新块确实在首屏；无横向溢出（`documentElement.scrollWidth ≤ innerWidth`）；**点轨仍 7 个点**且 `#sf-sec-N` 与基线同序；DA 字数落在 50–80；窄屏堆叠后每行仍带字段名 |
| **仓库级 md5** | `git -c core.quotePath=false ls-files -z \| xargs -0 md5sum` 两侧拉回、**排序只在本地**，13 个中文名逐条证明参与比对（当前基线 1211 文件） |

流程沿用"**先过门再上线**"：`git fetch`（只取对象）→ 全 SHA 装预检副本 → 候选经 `X-SF-Preflight: 1` 抓 75 页跑全套门 → 过了才 `pull --ff-only` → 上线后 `sf_masked_cmp` 候选 vs live 逐页 identical → 拆净预检 + 复验 + 查错误日志。

## 10. 待拍板

| # | 决策 | 选项 | 建议 |
|---|---|---|---|
| **D1** | 与既有 `.sf-spectable`（MOQ/Pack options/Lead time）**重复**怎么办 | (a) **纯新增并存**，旧表不动；(b) 把旧表**上移到 Hero 后**并扩成事实行（移动，不新增）；(c) 新块新增 + **精简**旧表到只剩 Unit size/Shelf life | **(a)**。本批是纯新增才能用最便宜的"删块即逐字节相同"限定证明；重复问题记成独立小批次再处理（约 3 行 markup）。选 (b)/(c) 会让本批升级为改+删批次 |
| **D2** | 事实行 vs 摘要段谁在前 | (a) 事实行在前；(b) 摘要段在前 | **(a)**（§4 的 375 首屏实测） |
| **D3** | Packaging 取值 | (a) 抄各页配置器 `data-group="packaging"` 选项集；(b) 写一句通用形态（Bottles, jars, tubes, pouches, blister packs — custom formats available）；(c) 本批不出 Packaging 字段 | **(a)**，页面自有单一真源、八页天然有差异；但需要你确认选项集就是对外口径（含 `Custom` 要不要写出来） |
| **D4** | 事实进不进 JSON-LD | (a) 不进（保持 deep-equal）；(b) 进 `additionalProperty`（改 PHP，**JSON-LD 会变**，回归点要改成"仅这 8 页、仅新增该键"的限定证明） | **(a)** 本批先不进；`additionalProperty` 目前是空的、GEO 收益真实，可作下一个独立小批次（改动小、但要单独的门） |
| **D5** | 形态与可访问名 | (a) 表格 + `<caption>`；(b) `<dl>` 网格 + `aria-label`；(c) inline 标签流 | **(a)**（§9 一） |
| **D6** | Sample lead time 口径 | (a) `3–7 working days`（跟 /services/）；(b) `3–7 days`（跟本页 How We Work 第 03 步） | **(a) 并顺手修正** How We Work 那句 —— 同一事实两处措辞不一致，GEO 最怕这个；但这会让本批不再是"纯新增 8 页"，需要单独确认 |

## 11. 约束核对

* 不删 DOM 内容 —— 方案 (a) 路线下**一个字节都不删**；只有 D1 选 (b)/(c) 或 D6 才会触碰既有内容（需单独确认）
* 不引入 JS 库 / CSS 框架 —— 纯 markup + CSS，无新 JS
* 自闭合区块用 ` /-->` —— 沿用模板既有写法（`<!-- wp:group {…} /-->` 是自闭合；`<!-- wp:group {…} -->…<!-- /wp:group -->` 是成对，两者按原样式）
* dev 站访问一律带凭据 `-u 'sfdev:…'`（或 `$SF_DEV_AUTH`）
* 新代码若用 `.sf-spec-term` 语义 —— **用 `<dt>/<dd>`，禁借用 `<span>` 形态**（K6 解析器 functions.php:3307 会把它当 spec 行抓走）
* 完成停下汇报
