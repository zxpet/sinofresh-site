# 批次 H5 Step 0 —— 只读扫描 ＋ 【停机报告】

> **状态：只读扫描完成，未改任何字节（主题侧 0 字节、DB 0 行、服务器 0 写入）。**
>
> **触发停机第 ③ 类「需改数据」＋ 第 ① 类「扫描与手册不符」**：
> - ③ —— H5 范围第 1 项要 `offers`（阶梯价格），但**阶梯价数据源 `sf_formula_price_tiers` 在 21 个配方上全为空**
>   （H3 已实测 `Quantity & Pricing` 0/42，本批复核一致）⇒ 无数据可渲染，补数据必须动 DB ⇒ 停机。
> - ① —— 手册 H5 范围第 3 项写「图片 ALT **自动生成**」，其**前提（存在缺 alt 的图）经实测不成立**：
>   75 页 **840 个 `<img>`，缺 alt = 0**。手册表述与实况不符 ⇒ 停机。
>
> **扫描方式**：主题静态盘点（`grep -E` 双侧锚点）＋ **75 页断面重解析**（`_backup/b2d-h4-candidates/`，
> 即 H4 预检态，`2.10.59`）＋ 服务器只读查询（`active_plugins`、插件目录）。
> **本批未建任何新探针** —— H5 的四项范围在**渲染产物 + 源码**两层即可完全判定，不需要 DB 探针。
>
> 关联：`docs/agent-playbook.md` §【H5】；基线＝**H4 的预检副本**（`sinofresh-theme-preflight` @ `2.10.59`）。

---

## 0. 结论速览

| H5 范围项 | 手册期望 | 实测现状 | 判定 |
|---|---|---|---|
| 1a. Product `additionalProperty`（口味/克重/包装） | 需强化 | **配方详情页 42/42 已有**；**剂型页 0/16 全缺**（数据锚点 H2b1 后已死） | ⚠️ **半成品**：一半已完成，一半是死锚点 |
| 1b. Product `offers`（阶梯价格） | 需新增 | **0/58**，且**数据源全空** | ⛔ **需改数据** ⇒ 停机 |
| 1c. `material` / `audience` / `isRelatedTo` | 需新增 | **全缺**（源码 0 处） | ⚠️ `isRelatedTo`/`audience` 可零数据推导，`material` 需数据 |
| 2. Organization `knowsAbout` | 需补 | **全缺**；其余字段（name/alternateName/url/email/telephone/address/areaServed 33 国/hasCredential 6 证/logo/sameAs）已齐 | ✅ **纯新增、零数据依赖**，可做 |
| 3. 图片 ALT **自动生成** | 需新增 | **缺 alt = 0 / 840**；空 alt 174 全为装饰件（语言国旗 150 + 博客头像 24） | ⛔ **前提不成立** ⇒ 真实议题是「质量规范化」而非「补齐」 |
| 4. 内容 80/20 原则审计 | 需审计 | 正文词数中位 **1,934 词/页**，CTA 密度 **3.6/千词（0.36%）** | ✅ **已满足**（内容高度资讯化）⇒ 审计本身无改造动作 |
| — | — | ⚠️ SEO 插件冲突面：**无 SEO 插件**（活跃插件仅 GF / TranslatePress×2 / consent-api / mail-logging / statistics）⇒ 主题 schema 具唯一权威性 | 无需 stand-down |

**净结论**：H5 的 4 项范围里，**2 项前提不成立**（ALT 补齐、80/20 改造）、**1 项半成品**（additionalProperty）、
**1 项可做**（knowsAbout），而**唯一真正的数据缺口是 `offers`**。⇒ **本批必须先裁决再动工。**

---

## 1. 范围项 1：Product Schema 强化

### 1.1 全站 JSON-LD 现状（75 页断面重解析，`json.loads` 逐块）

| `@type` | 覆盖 | 缺的页 |
|---|---|---|
| `Organization` | **75/75** | — |
| `BreadcrumbList` | 73/75 | `root.html`、`zh.html`（**首页无面包屑＝正确**，非缺陷） |
| `FAQPage` | 67/75 | 8 页（无 FAQ 手风琴的页） |
| `ItemList` | 60/75 | 15 页 |
| `Product` | **58/75** | 17 页（非产品页） |
| `HowTo` | 42/75 | = 21 配方 × 2 语言 |
| `Service` | 1/75 | `services.html` |
| `Article` | **断面 0/75**，但**源码有** | ⚠️ **采样假象** —— 75 页断面**不含博客单篇**（只有 `blog.html` 列表页）；`functions.php:5017-5100` 的 `is_singular('post')` Article 生成器（含 `datePublished`/`dateModified`/`author`/`publisher`）**是活的**。**不是缺口，不要报。** |

> ⚠️ **教训（本批第 1 条）**：`Article` 在断面里 0 次出现**不等于**没有 Article schema ——
> **断面集合的构成必须先核对**。75 页断面刻意只取列表页不取博客单篇，直接读「0 页有 Article」会得出反向结论。
> 与 §Q.5「掩码门的盲区」同类：**工具没覆盖的地方，静默就是全绿。**

### 1.2 `additionalProperty` —— 逐页实测（58 个 Product 页）

| 页组 | 页数 | `additionalProperty` | `offers` | `image` |
|---|---|---|---|---|
| 剂型页 `/products/{slug}/`（EN） | 8 | **0/8** | 0/8 | 8/8 |
| 剂型页（ZH） | 8 | **0/8** | 0/8 | 8/8 |
| 配方详情页 `/formulas/{slug}/`（EN） | 21 | **21/21** | 0/21 | 21/21 |
| 配方详情页（ZH） | 21 | **21/21** | 0/21 | 21/21 |
| **合计** | **58** | **42/58** | **0/58** | **58/58** |

**配方详情页（已达标，样例 `formulas__joint-support-soft-chews.html`）** —— 3 行，读 post meta：

```
additionalProperty: [
  Ingredients            Glucosamine HCl, Chondroitin Sulfate, MSM, Green-lipped Mussel, Chicken Flavor
  Guaranteed Analysis    Glucosamine ≥500mg/chew, Chondroitin ≥200mg/chew, MSM ≥100mg/chew
  Standard Specs         2g/piece · 60/90/120 per bottle · 18 months shelf life
]
```

**剂型页（0/8，根因＝数据锚点死在 H2b1）** —— 生成器在 `functions.php:4796-4806`：

```php
// additionalProperty: spec rows — sf-spec-list first, legacy table fallback
if (preg_match_all('/<span class="sf-spec-term">([^<]+)<\/span><span class="sf-spec-value">([^<]+)<\/span>/', $html, $rows, PREG_SET_ORDER)) {
```

实测剂型页渲染产物：

| 锚点 | 出现 |
|---|---|
| `sf-spec-list` | **0** |
| `sf-spec-term` | **0** |
| 遗留 `flex-basis:35%` 表格 | **0** |
| **`sf-facts-mini`**（H2b1/F1 的替代品） | **4 行 × 16/16 页** |

⇒ **两条分支都永不匹配，`additionalProperty` 在 8 个剂型页（×2 语言＝16 页）上静默缺席。**
生成器的**注释仍宣称它读 `sf-spec-list`** —— 注释与实况脱节（`functions.php:4736-4740`）。

> ⚠️ **附带发现（本批第 2 条）**：该正则本身**形态也已过期** —— 配方详情页的真实标记是
> `<dt class="sf-spec-term">` / `<dd class="sf-spec-value">`（**`dt`/`dd`，不是 `span`**）。
> 本次 grep 若用旧正则（`<span class="sf-spec-term">`）会得 0 命中并误判「详情页也缺 additionalProperty」。
> **详情页之所以有 `additionalProperty`，是因为它走 post meta，压根不经过这条正则。**
> ⇒ 修剂型页时**不能顺手把 `span` 改成 `dt`** —— 那条正则只服务剂型页，而剂型页早已不用 spec-list。

**现成的正确数据（`sf-facts-mini` 4 行，16/16 页齐备）**：

| label | 样例值（soft-chews） |
|---|---|
| MOQ | `from 500–1,000 units` |
| Lead time | `Typically 7–15 working days after packaging is ready` |
| Certifications | `FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC` |
| Packaging | `Aluminum Stand-up Pouch, Aluminum Foil Pouch with Zipper, Plastic Bottle, Jar, Blister Pack, Box + Foil, or custom formats` |

> 手册 H5 要的「**包装**」这一项，正落在 `sf-facts-mini` 第 4 行 —— **数据已经存在，只是没人读**。
> 且 `functions.php:646-690` **已有一个作用域正确的读取器** `sinofresh_formula_spec_cell()`
> （它明确把 lookup 限定在 `.sf-facts-mini` 块内，避免命中全页同名 label）⇒ **零新代码即可复用**。

### 1.3 `offers`（阶梯价格）—— ⛔ 数据缺口

| 项 | 实测 |
|---|---|
| Product 页带 `offers` | **0/58** |
| 数据源 | `sf_formula_price_tiers`（post meta，行表 `qty`/`price`），渲染器 `sinofresh_formula_tier_table()` 在 `functions.php:2094` |
| 数据实况 | `Quantity & Pricing` 行在 42 个详情页 **0 出现**（H3 已登记「renderer first, data later」，本批复核一致） |
| 剂型页价格源 | **不存在**（`sf-facts-mini` 的 4 行里没有价格，页面上任何位置都没有价格） |

**详情页源码已写死「不输出 offers」的理由**（`functions.php:4846-4849`）：

> `No offers / price: a standard formula is an OEM reference, not a priced SKU, and inventing a price would be worse than omitting the property.`

⇒ 现在有**两条互斥的路线**：手册要 offers ↔ 源码注释说 OEM 不报价。

### 1.4 `material` / `audience` / `isRelatedTo` —— 全缺（源码 0 处命中）

| 字段 | 数据可得性 |
|---|---|
| `isRelatedTo` | ✅ **零数据可推** —— 同 `sf_formula_form` 分类下的兄弟配方，**现成查询**（H2a 的 Related 区已在用同一关系） |
| `audience` | ✅ **零数据可推** —— 8 剂型的适用对象是固定映射（犬/猫/通用），可写成常量表 |
| `material` | ⛔ **需数据** —— 需「剂型主料」字段；现有 `sf_formula_ingredients` 是**配方**原料，语义不同（剂型页的 material 应是明胶/甘油/淀粉基等载体），不可直接挪用 |

---

## 2. 范围项 2：Organization `knowsAbout`

**现状（`functions.php:4926-4996`，75/75 页生效）** —— 已含 10 个字段：

`@id`（被 `services.html` 的 Service 的 `provider` 引用）／`name`／`alternateName`／`url`／`email`／`telephone`／
`address`（PostalAddress 4 段）／`areaServed`（33 国）／`hasCredential`（6 证，`sf_cert_schema_credentials()`）／`logo`／`sameAs`

**`knowsAbout` 实测：源码 0 处命中。** 补齐是**纯新增、零数据依赖**——
8 个剂型名 + `Pet Supplement OEM/ODM Manufacturing` + `Private Label Pet Supplements` 等固定词条即可。

> ⚠️ 但 `knowsAbout` 会**全站 75 页 DIFF**（Organization 是 site-wide 块）。这不是问题，是**门的设计前提**（见 §6）。

---

## 3. 范围项 3：图片 ALT —— ⛔ 手册前提不成立

### 3.1 实测普查（75 页断面）

| 指标 | 数值 |
|---|---|
| `<img>` 总数 | **840** |
| **缺 `alt` 属性** | **0** |
| `alt=""`（空，装饰性） | 174 |
| 有实质 alt | 666 |
| distinct alt 文本 | 85 |

**174 个空 alt 的来源（逐 `src` 归因，全部合理）**：

| 来源 | 计数 | 判定 |
|---|---|---|
| `en_US.svg`（语言切换器国旗） | 75 | ✅ 正确（装饰件） |
| `zh_CN.svg`（同上） | 75 | ✅ 正确 |
| `avatar-*.webp`（博客作者头像，紧邻作者名文字） | 24 | ✅ 正确（避免与相邻文字重复） |

⇒ **「自动生成 ALT」没有对象**：**0 个图缺 alt**，174 个空 alt **全部是刻意的装饰件**。

### 3.2 真实议题＝质量，不是覆盖

| 问题 | 实测 | 判定 |
|---|---|---|
| logo alt 是小写且无品类词 | `alt="sinofresh"` × **150**（header+footer × 75 页） | ⚠️ 应规范化 |
| 剂型页商品图缺卖点/视觉特征 | `SINO FRESH Soft Chews private label pet supplement product` × 62 —— 骨架符合 H5 目标格式，但**无「60 Count Bottle」类视觉特征** | ⚠️ 可选升级 |
| 工厂图质量已高 | `Soft Chews production line at the SINO FRESH GMP facility` | ✅ 达标，不动 |
| 博客图质量已高 | `How to choose a pet supplement manufacturer - fact…` | ✅ 达标，不动 |

**若严格按 H5 目标格式（产品名+剂型+卖点+视觉特征）全量重写**，会改动 **约 62 + 150 ≈ 212 处**，
且**绝大多数是模板里的静态字面量**（`templates/page-*.html` 的 `<img alt>`），**不是「自动生成」能覆盖的范围** ——
真要"自动"，只能做成 `the_content`/`render_block` 过滤器改写，那会**给整站加一层运行时字符串替换**，与现有
「模板即单一真源」的架构冲突。

> ⚠️ **本批第 3 条教训**：手册里写「自动生成」时，**默认它描述的是期望，不是现状**。
> 先量「缺多少」，再决定"生成"是不是正确的动词 —— 本例正确动词是**「规范化」**。

---

## 4. 范围项 4：内容 80/20 原则审计

### 4.1 实测

| 指标 | 数值 |
|---|---|
| 正文词数中位 | **1,934 词/页** |
| <300 词的页 | **0/75** |
| 全站 CTA 语（get a quote / request a sample / contact us / send an inquiry / download …） | 524 次 / 145,677 词 |
| **CTA 密度** | **3.6 / 千词 ＝ 0.36%** |
| CTA 密度最高的页 | `privacy-policy` 6.9、`contact` 5.8、配方详情页 4.2 |
| CTA 密度最低的页 | `feedback` / `quality` / `services` 2.4，首页 `root` 2.3 |

### 4.2 判定

**80/20 已满足，且余量很大** —— CTA 密度 0.36% 意味着正文压倒性是资讯性的。
⇒ **本项唯一该交付的是「审计报告」，没有改造动作。** 若强行"提高到 20% 促销"，方向是**反的**。

> ⚠️ 注：本节的「词数」是**粗算**（`<main>` 内去标签后的空白切分），会偏高（含少量属性残留）。
> 同一页更严的算法（只数 `h/p/li/td/th/dt/dd` 标签内容）得 777 词。
> **两个口径的中位数排序一致**，但**报给用户的数字必须带口径**（本批第 4 条教训）。

---

## 5. 范围外的两项发现（需裁决「纳入 H5 / 登记 H6 / 不做」）

| # | 发现 | 性质 | 建议 |
|---|---|---|---|
| 1 | **无 `WebSite` schema**（Sitelinks SearchBox 的宿主） | 纯新增、零数据 | 可选纳入 H5（1 行新块，只首页输出） |
| 2 | **`Product` 在首页缺失**（`root.html` 无 Product，**正确**）；`BreadcrumbList` 首页缺失（**正确**） | — | **不是缺陷，不要动** |
| 3 | **`sf-facts-mini` 的 4 行与 H3 内容区参数行有 3 项语义重叠**（Certifications / Lead time / Packaging 在两处都渲染） | ⚠️ **双真源风险** | 登记 H6 对账（与 H6 第 4 项「MOQ 三处对账」合并） |

> ⚠️ **本批第 5 条教训**：H5 要以 **`sf-facts-mini` 为剂量页 schema 的唯一真源**，
> 而 `sinofresh_formula_spec_cell()` 已经这么做了 —— **`functions.php:1994` 明确写「NOT the dosage page's
> .sf-facts-mini certifications cell」**，说明 H3 的原作者已经踩过一次「两个来源同名」的坑并加了注释。
> 修 additionalProperty 时**必须复用这个读取器**，否则会引入第三处真源。

---

## 6. ⛔ 门的设计前提（本批与 H2b1–H4 的根本差异）

H2b1–H4 的门是**字节门**（掩码比对 / 限定证明）。**H5 不能沿用**：

| 变更 | 字节门结果 | 实际 |
|---|---|---|
| Organization 加 `knowsAbout` | **75/75 页 DIFF** | 全部**合法** |
| 剂型页加 `additionalProperty` | **16 页 DIFF** | 全部**合法** |
| logo alt 规范化 | **75 页 DIFF**（×2 处） | 全部**合法** |
| 新增 `WebSite` 块 | **若干页 DIFF** | 全部**合法** |

⇒ **H5 的门必须是 JSON-LD 语义门**：`json.loads` 后做 **deep-equal，允许「新增键」通过、禁止「改值/删键」**，
外加**渲染 HTML 的白名单字节门**（只允许声明的 alt 位移）。
手册 H5 回归栏写的就是「JSON-LD **deep-equal**（除新增字段）」——**与本判定一致**，
但**必须显式写进门工具**，否则「除新增字段」这句话没有可执行定义。

> ⚠️ **本批第 6 条教训**：**先量「合法 DIFF 集」再写门**。若沿用字节门，第一批绿就是假绿；
> 若把门放宽成「JSON-LD 不 parse 错就过」，则删掉 `brand` 也能过 —— 两者都是**假绿**。

---

## 7. 裁决请求（逐条，全部按推荐项排首位）

| # | 议题 | 推荐 | 选项 |
|---|---|---|---|
| **A** | 剂型页 `additionalProperty`（现 0/16，死锚点） | **A（推荐）** | **A** 复用 `sinofresh_formula_spec_cell()` 读 `sf-facts-mini` 4 行 → 零数据、修死锚点、不引第三真源 ／ **B** 删掉死代码分支、剂型页不发 additionalProperty（承认 OEM 剂型页无参数行） ／ **C** 两件都做（先读后删冗余分支） |
| **B** | `offers`（阶梯价格）—— ⛔ 数据缺口 | **A（推荐）** | **A** 先做渲染器（`sf_formula_price_tiers` 有数据才输出 offers，零数据改动，与 H3「renderer first」同构） ／ **B** 本批补真实阶梯价（**需运营提供数据** ⇒ 请给出阶梯价，我落 DB） ／ **C** 跳过 offers，并把「OEM 不公开报价」写进 Product 生成器注释（与 `functions.php:4846-4849` 现有立场一致） |
| **C** | `material` / `audience` / `isRelatedTo` | **A（推荐）** | **A** 只做零数据的两个（`audience` 从 8 剂型常量表推、`isRelatedTo` 用同 `sf_formula_form` 兄弟配方）；`material` 登记 H6 等字段 ／ **B** 三个都做，`material` 由我按剂型给建议常量表（**需你确认**） ／ **C** 本批全不做，全部登记 H6 |
| **D** | 图片 ALT | **A（推荐）** | **A** 只做规范化：logo `alt="sinofresh"` ×150 → `alt="SINO FRESH logo"`；剂型页商品图补视觉特征（62 处）／ **B** 按 H5 目标格式**全量重写 ~212 处**（改动面大，且相当部分需新增运行时过滤器，与"模板即真源"冲突） ／ **C** 不做（实测 0 缺 alt、174 空 alt 全为合理装饰件） |
| **E** | 80/20 审计 | **A（推荐）** | **A** 只出审计报告（实测已满足，无改造）／ **B** 附带出「可加资讯内容」的选题清单供运营 ／ **C** 跳过 |
| **F** | Organization `knowsAbout` 词表 | **A（推荐）** | **A** 用 8 剂型名 + OEM/ODM + Private Label 共 10 条固定词条 ／ **B** 你给词表 ／ **C** 不做 |
| **G** | 范围外：`WebSite` schema（SearchBox） | **B（推荐）** | **A** 纳入 H5（首页 1 个新块）／ **B** 登记 H6（H5 已经是"修既有 schema"的批次，不宜再扩范围）／ **C** 不登记（不需要） |

---

## 8. 扫描证据索引

| 证据 | 位置 |
|---|---|
| 75 页断面（H4 预检态 `2.10.59`） | `_backup/b2d-h4-candidates/` |
| H5 基线预检副本（服务器） | `/var/www/dev.zxpet.com/public/wp-content/themes/sinofresh-theme-preflight` @ `2.10.59` |
| Product schema（剂型页）生成器 | `functions.php:4729-4830`（死锚点 `4796-4806`） |
| Product schema（配方详情页）生成器 | `functions.php:4832-4930`（`offers` 立场注释 `4846-4849`） |
| Organization 生成器 | `functions.php:4917-4996` |
| Article 生成器（**活的，勿误判为缺口**） | `functions.php:5017-5100` |
| `sf-facts-mini` 读取器（**复用它的作用域逻辑**） | `functions.php:646-690` |
| 阶梯价渲染器 | `functions.php:2038-2042`（接入）／`2094-2113`（`sinofresh_formula_tier_table`） |
| `related` 兄弟配方查询（`isRelatedTo` 可复用） | H2a Related 区（`sf_formula_form` 分类） |

---

## 9. 停机声明

**⛔ 本批停在 Step 0，未进 Step 1，未改任何字节。**

停机依据：
1. **第 ③ 类「需改数据」** —— `offers` 的阶梯价在 DB 里是空的（裁决 B）；
2. **第 ① 类「扫描与手册不符」** —— 手册 H5 第 3 项「ALT 自动生成」的前提（存在缺 alt）实测不成立，
   且第 1 项 `additionalProperty` 是**半成品**（配方页已完成、剂型页是死锚点），第 4 项 80/20 已达标。

⇒ **等 §7 的 A–G 七条裁决，收到后进 Step 1。**
