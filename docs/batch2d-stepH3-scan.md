# 批次 H3 Step 0 扫描 —— 内容区 + FAQ + Sampling

> 扫描时间 2026-09-22 · 目标：云端 dev `65.49.215.152`（只读）· 产品基线 `3b9fc23`（H2b2 收尾）
> 方式：模板/短码/样式静态盘点 ＋ **活动库只读探针**（`tools/b2d_h3_dataprobe.php`，零写入）
> 证据落盘：`_backup/b2d-h3-dataprobe.json`

## 0. 结论：**停机报告**（触发条件①「扫描与手册不符」）

playbook【H3】的范围可以照做，但**其中两条与今日代码的既成事实冲突**，冲突点不是数字/行号派生误差，
而是**方向本身**——照字面执行会撤销上一批的刻意设计，并产生同一字段的重复渲染。故按 Step 0 规则停下。

**两项冲突与一条连带：**

| # | 冲突 | 依据 |
|---|---|---|
| **C1** | H3 内容区的前 3 块（Ingredients / Guaranteed Analysis / Formula）**与页面上已有的两带重复**；其中前两块是**上一批刻意去重**过的 | `functions.php:1893-1900`：*"Ingredients and Guaranteed Analysis are deliberately left out, because the "Formula & nutrition" band below already carries both from the same meta — **they were being rendered twice on every detail page**"* |
| **C2** | 「背景色交替 white / bg-light」会把一片**连续 4 带的白色"本配方数据面"**从中间切开 | `style.css:8103-8111`：三个数据带（Specification / Formula & nutrition / Ingredients & composition）**同色 card-white**，注释写明 *"the three read as one "this formula's data" surface"* |
| **C3** | H3 的 **Shelf Life** 块会与 H2a 已上线的 `Shelf life` 参数行重复（同一事实、两个来源） | H2a 行解析 `sf_formula_specs` 的 `… shelf life` 段；H3 块读 `sf_formula_shelf_life`（21/21 = `18 months`）。**两个键同时存在** |

**本批不受冲突影响、可照做的部分：**Sampling Process 4 步 ＋ HowTo Schema、`.sf-fdetail-content` 命名空间与样式、模板插入。
（详见 §5。）

---

## 1. 今日详情页的实际结构（21 英语页 × 21 中文页，实测字节）

取自 `_backup/b2d-h2b2-candidates/formulas__joint-support-soft-chews.html`（120,285 B）：

| # | 段 | 类/短码 | 背景 | 今日是否出字节 |
|---|---|---|---|---|
| 1 | Hero（面包屑＋H1＋meta＋2 CTA） | `.sf-formula-hero` | 品牌绿 | ✅ |
| 2 | 媒体 ＋ 参数两栏 | `.sf-fdetail2`（`bg-light`） | 浅灰 | ✅ |
| 3 | 长文（`post_content`） | `[sf_formula_body]` | — | ❌ 21 条 `post_content` 全空 ⇒ 整段不渲染 |
| 4 | Specification | `[sf_formula_detail]` | **白** | ✅ 仅 1 卡 `Standard Specs` |
| 5 | Formula & nutrition | `[sf_formula_detail_actives]` | **白** | ✅ Ingredients 药丸 ＋ Guaranteed Analysis 网格 |
| 6 | Ingredients & composition | `[sf_formula_detail_composition]` | **白** | ❌ 两键 0/21 ⇒ 整段不渲染 |
| 7 | FAQ（9 条） | `[sf_formula_faq]` | 白 | ✅ |
| 8 | More {剂型} Formulas | `[sf_formula_grid limit="4"]` | `bg-light` | ✅ |
| 9 | CTA「Ready to Launch Your Product?」 | — | 品牌绿 | ✅ |

⛔ **今日页面上既无「详细内容区」，也无「How Sampling Works」**，`style.css` 里 `sf-fdetail-content` / `sf-sampling` / `HowTo` **零命中** —— H3 确是纯新增。

---

## 2. H3 十二个数据源的真实供给（活动库实测，21 条记录）

`_backup/b2d-h3-dataprobe.json`。**21 条记录里 `sf_formula*` 键总共只有 8 个 × 21 = 168 行**，
另有 `wp_statistics_words_count` 21 行（与内容无关）。

| H3 块 | meta key | 键已注册 | 有值/21 | **今日页面已渲染几次** | 判定 |
|---|---|---|---|---|---|
| Ingredients | `sf_formula_ingredients` | ✅ | **21/21** | **1 次**（⑤ 药丸） | ⛔ **C1 重复** |
| Guaranteed Analysis | `sf_formula_analysis` | ✅ | **21/21** | **1 次**（⑤ 网格） | ⛔ **C1 重复** |
| Formula | `sf_formula_specs` | ✅ | **21/21** | **4 次**（④ 卡片 ＋ H2a 三行解析） | ⛔ **C1 重复** |
| Recommended For | `sf_formula_recommended_for` | ✅（H1） | **0/21** | 0 | 空值不渲染 |
| Use Cases | `sf_formula_use_cases` | ✅（H1） | **0/21** | 0 | 空值不渲染 |
| Who It's For | `sf_formula_who_for` | ✅（H1） | **0/21** | 0 | 空值不渲染 |
| Container Options | `sf_formula_container` | ✅（H1） | **0/21** | 0 | 空值不渲染（库内有 7 项可选） |
| Additional Packaging | `sf_formula_packaging_extra` | ✅（H1） | **0/21** | 0 | 空值不渲染 |
| Color Options | `sf_formula_colors` | ✅（H1） | **0/21** | 0 | 空值不渲染 |
| Shelf Life | `sf_formula_shelf_life` | ✅ | **21/21**（`18 months`） | 0（那是 specs 解析出来的另一行） | ⛔ **C3 重复** |
| Storage | 硬编码 | — | n/a | 0 | 可照做（全站同一句） |
| Carton Dimensions | `sf_formula_cartons` | ✅（H1） | **0/21** | 0 | 空值不渲染 |

**读法：** 12 块里 **3 块与现状重复**、**1 块与 H2a 行重复**、**7 块今天渲染 0 字节**（键已注册、数据未填）、
**1 块（Storage）可立即出字节**。

### 2.1 为什么「7 块 0 字节」本身**不是**问题

键全部已在 `inc/formula-admin.php`（批 H1）注册，含后台分组、类型、必填级与选项池；
缺的只是**值还没人填**。这正是 H2a 已确立并获用户批准的交付模式——

> *"That is the whole point of shipping the renderer before the data — the sales team fills a field,
> the row appears, nothing is deployed."*（`functions.php:1975-1977`）

H2a 的四个参数行（Flavor / Suitable For / Life Stage / Quantity & Pricing）今天同样是 **0/21**，
`docs/h2a-data-checklist.md` 记着 **84 个待填单元格**，运营尚未开始录入。故 H3 照此模式交付**口径一致**。

### 2.2 但 C1 不是「空」，是「重复」——这才是要裁决的

页面上同一字段的**现有出现次数**（今日实测）：

| 字段 | 出现处 | 次数 |
|---|---|---|
| `sf_formula_ingredients` | ⑤ Formula & nutrition → Ingredients 药丸 | 1 |
| `sf_formula_analysis` | ⑤ Formula & nutrition → Guaranteed Analysis 网格 | 1 |
| `sf_formula_specs` | ④ `Standard Specs` 卡 ＋ ③ 参数区 `Piece Weight`/`Pack Size`/`Shelf life` 三行（均由该串解析） | **4** |

再叠加 H3 的 3 块 ⇒ `ingredients` 2 次、`analysis` 2 次、`specs` **5 次**。
其中 `ingredients`/`analysis` 的「2 次」**正是上一批专门删掉的那个状态**。

---

## 3. 与 playbook【H3】的逐条对照

| playbook 条目 | 扫描结果 |
|---|---|
| 1. 详细内容区 6 块 | ⚠️ 前 3 块重复（C1）；后 3 块键已注册、数据待填 |
| 1b. Packaging & Specifications（6 子块） | ✅ 结构可照做；Container 库已有 7 项（Round/Square/Oval/Jar/Pouch/Tube/Custom）；其余 5 子块数据待填 |
| 2. Sampling Process 4 步 ＋ HowTo Schema | ✅ **无冲突**：全静态文案，无数据依赖；`functions.php` 已有 9 个 `wp_head` JSON-LD 发射器可循 |
| 3. 模板插入 | ✅ 可照做。落点按 ①–⑧ 序：内容区在 **③ 媒体+参数** 与 **⑤ FAQ** 之间；Sampling 在 **⑤ FAQ** 与 **⑦ More** 之间 |
| 4. meta 空值整块不渲染 | ✅ 与 H2a 既定模式一致 |
| 样式 `.sf-fdetail-content` / 每块 48px / 表格 border-collapse | ✅ 可照做 |
| 样式 背景交替 white / bg-light | ⛔ 与 C2 冲突 |
| 回归：DIFF 集合 = 21 ＋ 21 zh = **42 页** | ✅ 与 75 页断面吻合（75 = 17 静态 ＋ 8 剂型 ＋ 8 zh 剂型 ＋ 21 详情 ＋ 21 zh 详情） |
| 回归：JSON-LD FAQPage 不变、HowTo 新增 | ✅ 可照做；FAQ 页 21/21 有 `sf_formula_faq_data` |
| 回归：点轨（详情页无点轨） | ✅ 与 RULES 一致，本批不涉及 |

**一处需记录、但无需裁决的重叠：** FAQ 里已有一条 *"Can I sample this formula before ordering?"*，
与新的 Sampling Process 段主题相邻。属自然呼应，非重复。

**一处跨批耦合（供 H4 复用）：** H4 范围第 5 项「4 步打样流程内嵌（弹窗里）」
需要同一份 4 步内容 ⇒ Sampling 四步应做成**单一渲染函数**，H3 出独立段、H4 出弹窗内嵌，避免两处硬编码文案漂移。

---

## 4. 需要裁决的三项

### 裁决 1（阻塞）：H3 内容区的 6 块如何处置与现状重复的 3 块

| 选项 | 做法 | 代价 |
|---|---|---|
| **A（推荐）** | 内容区**只做 4 块新增文案**（Recommended For / Use Cases / Who It's For ＋ Packaging & Specifications 6 子块）＋ Storage；Ingredients / GA / Formula **不重复渲染**，页面继续由 ④ Specification 卡 ＋ ⑤ Formula & nutrition 承担 | 与 playbook ④ 的「6 块」字面不符，需在批次档登记；无回归风险 |
| **B** | 内容区做全 6 块，并**把 ④ 的 `Standard Specs` 卡与 ⑤ 的 Ingredients/GA 移除**，由新内容区统一承载（三带并一带） | 触及批 E/G 已上线资产；`sf-fdetail-actives` 的样式与 `[sf_formula_detail]` 卡片需一并处理；改动面大于「H3 = 纯新增」 |
| **C** | 照字面全做 6 块，**接受重复** | 与 `functions.php:1893-1900` 的刻意去重直接矛盾；同一页 `specs` 出现 5 次 |

### 裁决 2（阻塞）：背景交替是否适用于这一片连续白带

| 选项 | 做法 |
|---|---|
| **A（推荐）** | 内容区**整段一个背景**（承 ④⑤⑥ 的 card-white 连续面），内部用分隔线/间距分块；交替色只用于**与相邻带之间** |
| **B** | 照 playbook 逐块交替 white / bg-light |

### 裁决 3（可合并进裁决 1）：Shelf Life 的单一真源

| 选项 | 做法 |
|---|---|
| **A（推荐）** | H3 不再单列 Shelf Life 块（H2a 参数行已展示该事实），存量不动 |
| **B** | H3 出 Shelf Life 块，并把 H2a 的 `Shelf life` 行**改为读 `sf_formula_shelf_life`**（消除 specs 解析这一路），是数据管线改动 |
| **C** | 两处都留（重复） |

---

## 5. 无论裁决如何都可以先做的部分

1. **Sampling Process 段**：4 步静态文案 ＋ 圆圈数字（44px 绿底白字）＋ ≥769px 横排 / ≤768px 纵排 ＋ 末句 *"Typically 3-7 working days"*。
   做成**可复用渲染函数**（H4 弹窗复用），命名空间 `.sf-sampling`。
2. **HowTo JSON-LD**：`name="How Sampling Works"`、4 个 `HowToStep`、`totalTime="P3D"`；循 `functions.php` 现有 `wp_head` 发射器写法。
3. **`.sf-fdetail-content` 样式骨架**：48px 块间距、表格 `border-collapse` ＋ 1px 细线、空值不出块。
4. **模板插入位**：内容区（③ 与 ⑤ 之间）、Sampling（⑤ 与 ⑦ 之间）——两处都不动既有块。
5. **回归门**：DIFF 集合 = 42 页（21 ＋ 21 zh）；纯新增 ⇒ 优先用**限定证明**（删掉新增块后逐字节比基线，最便宜且最强）。

---

## 6. 证据索引

| 项 | 位置 |
|---|---|
| 活动库只读探针（源） | `tools/b2d_h3_dataprobe.php` |
| 探针输出（落盘） | `_backup/b2d-h3-dataprobe.json`（`_backup/` 被 gitignore ⇒ 仅本地；可由上面的探针**逐字节重建**） |
| 今日详情页字节 | `_backup/b2d-h2b2-candidates/formulas__*.html`（21 ＋ 21 zh） |
| 刻意去重的原始决策 | `sinofresh-theme/functions.php:1893-1900` |
| 三带同色的原始决策 | `sinofresh-theme/style.css:8103-8111` |
| 后台字段权威定义 | `sinofresh-theme/inc/formula-admin.php:26-115` |
| H2a 数据现状清单 | `docs/h2a-data-checklist.md` §5.2 |
| 75 页门禁断面 | `_backup/b2d-h2b2-candidates/`（MANIFEST.tsv ＋ 75 html） |

---

## 7. 停机声明

按 playbook 第十部分 **Step 0**：*「不符：停下报告」*，以及授权规则「只 3 类停机」之①
「**扫描与手册不符**」——本次停下，**未进 Step 1，未改任何字节**（服务器侧仅 `wp eval-file` 只读探针，
零 option/meta/post 写入）。等裁决 1/2/3 后自动继续。

### 7.1 「零写入」不是自称，是可核对的对账

本次探针跑完后，与**探针前**已有的快照对账（`_backup/b2d-h2a-baselines/db-before.json`，今日 05:54）：

| 维度 | 结果 |
|---|---|
| 逐键 × 空/非空 的格子数 | **16 格，0 处不符** |
| `formula_ids` | **完全相同**（158–178 共 21 条） |
| `sf_formula` meta 行总数 | **189 = 189** |

⇒ 两件事同时成立：**① 探针没有写任何东西**（跑完与跑前逐格相同）；**② 数据自 H2a 以来未动**
（运营尚未开始录入，与 `docs/h2a-data-checklist.md` 的「84 个待填单元格」一致）。

