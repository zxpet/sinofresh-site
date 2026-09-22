# Batch H5 —— SEO/GEO：Schema 补齐 ＋ ALT 规范化

**状态：Step 1–5 全部完成。门四件套全绿，E2E 20/0，截图 11/11。Step 6 `git pull` 按规则跳过（H5 起不上线）。**

- 产品 `1eafe62`（七条裁决 A–G 落地）＋ 修复 `2017dbe`（图集首帧＝alt 的第三个载体）
- 基线＝**H5-0 的预检副本**（`084b246` 树，`2.10.60`，仍在位未拆）
- 扫描与裁决：`docs/batch2d-stepH5-scan.md`（A–G 七条）
- 旁证报告：`docs/batch2d-stepH5-audit-8020.md`（裁决 E）
- 证据：`_backup/b2d-h5-gates/`（`main` / `aa` / `matrix` / `negctl` / `e2e` / `e2e-report` / `shots`）
- 实拍：`docs/batchH5-shots/`（11 张）

---

## 1. 改动面：9 文件，+508 / −77，**零 CSS**

| 文件 | 改动 |
|---|---|
| `sinofresh-theme/functions.php` | 473 行变动（8 个新函数 ＋ 3 个生成器改写＋注释） |
| `templates/page-{8 剂型}.html` | 每页 14 行（**7 处缩略图 alt** × 2） |

拆成两个提交是因为第二处是**门抓出来的漏改**，不是计划内的一部分：

- `1eafe62`：9 files, +496 / −76 —— 七条裁决落地
- `2017dbe`：1 file, +17 / −6 —— 图集首帧的 `alt` 改走同一个读取器

**新增函数（8 个）**：`sinofresh_formula_alt_visuals()`／`sinofresh_formula_product_alt()`／
`sinofresh_formula_facts_props()`／`sinofresh_formula_audience()`／`sinofresh_formula_related()`／
`sinofresh_dosage_related()`／`sinofresh_formula_offers()`／`sinofresh_knows_about()`

⛔ **不改 CSS ⇒ 版本令牌不动（仍是 `2.10.60`）**。"改 `style.css` 才 bump 两处"这条规则是**条件式**的，
本批没碰 `style.css`，所以**没有** bump。代价见 §5.3：两态 provenance 只能**按内容**证。

---

## 2. 七条裁决落地（A–G）

| # | 裁决 | 落地 |
|---|---|---|
| **A** | `additionalProperty` 复用 `sf-facts-mini` 读取器（不换真源） | 剂型页 **0/16 → 16/16**。新 `sinofresh_formula_facts_props()` 经 `sinofresh_formula_spec_cell()` 读 —— 就是 F1 hero 在用的那个读取器 ⇒ schema、hero meta、H3 参数行**同一个源**。两个死解析器（`.sf-spec-list` 正则、遗留表）**保留作 fallback**（裁决 A 而非 C）并加注释写明"它们已经匹配不到了" |
| **B** | `offers` 渲染器优先，有数据才输出 | `sinofresh_formula_offers()` 每有数字就渲染、无数字**返回 `null`**。`sf_formula_price_tiers` 在 **21 条配方上全空** ⇒ 今日 **0/58 页**输出。只认**整格纯小数**（`1.20`／`$1.20`／`USD 1.20`／`1.20 USD`）；**`1,200` 与区间跳过不解析** —— 把 `1,200` 读成 `1.2` 会发出**低三个数量级**的价格。门只能证 null 分支 ⇒ 用 **22 条离线断言**证另一支 |
| **C** | 只做 `isRelatedTo` + `audience`，`material` 登记 H6 | `isRelatedTo` **58/58**（读页面上**可见的** tile／card 链接，同序列、同排除）；`audience` **32 页**。扫描档"8 个剂型各有固定物种映射"的前提**不成立** —— `sf_formula_species` 在 **21 条记录上全空**，8 个页头里只有 4 个写了物种（soft chews／tablets／fish oil＝Dogs & Cats；dental chews＝Dogs）⇒ 其余 **4 个剂型不给 audience**，不给一个没人声明过的物种。`material` 需要记录里没有的字段 ⇒ **H6 第 14 项** |
| **D** | ALT **规范化**（不是被否决的 212 处重写） | 商品图加上目标格式要求的视觉短语，且短语**从实际发货的图读出**、不从剂型名猜（fish oil 是**胶囊**、liquids 是**瓶**）。8 个声明的旧串共 **398 个属性值**（314 `alt=` ＋ 42 `data-label=` ＋ 42 `aria-label=`）⇒ 候选上 **398 / 旧串 0** |
| **E** | 80/20 **只出报告** | `docs/batch2d-stepH5-audit-8020.md`。结论：**已满足且余量极大，不动**（见 §8） |
| **F** | Organization `knowsAbout` 10 条 | 8 个剂型标签（读各自页面标题）＋ 2 条服务线，**75/75**。**memoise** —— 页面标题查询本来每页都会跑 |
| **G** | `WebSite` schema 登记 H6 | **H6 第 15 项**，本批不建 |

### 2.1 刻意没做的：站内 logo 的 `alt` 在模板里改不到

WordPress 在 `custom-logo` 附件**没有 Alt Text** 时会**回落到站点标题**，于是每页印出 `alt="sinofresh"`。
这个串**不在主题里**，没有任何模板编辑能触及它 —— 它是**媒体库的一行**。已在该处设定（见 §9）。

---

## 3. 门的形状：本批不能用 H2b1–H5-0 的字节门

`knowsAbout` 75/75 页 DIFF、剂型页 `additionalProperty` 16 页 DIFF、logo `alt` 75 页 DIFF —— **全部合法**。
沿用旧门会 75 页全红。所以 `tools/b2d_h5_gate.py` 是**四条判据**，缺一条就是全绿假象：

1. **JSON-LD 语义门** —— 每块 `json.loads` 后 deep-equal：**允许新增键、禁改值/删键**，
   且**新增键路径集合 = 声明的集合**（未声明的新增也 FAIL）。
   ⛔ 必须走**解析**不能走字面：EN 紧凑 / ZH pretty 的序列化差异是本族第三次复现。
2. **渲染 HTML 白名单字节门** —— 挖掉 `ld+json`、把声明的新串**反演回旧串**，然后要求**逐字节相等**。
3. **覆盖断言（第三判据）** —— 批次跑完，声明的**旧裸串出现次数必须 = 0**。
   ⛔ 缺它则上述两门**都能在"漏改 126 处"的构建上全绿**：漏改处与基线**逐字节相同**，
   反演后照样相等 ⇒ 反演式门**对"该改的没改"结构性失明**。
   且**声明粒度必须 = 承载粒度**：同一串落在 `alt`／`data-label`／`aria-label` **三个属性**上，
   就必须声明**裸串**；声明成 `alt="串"` 形状 ⇒ 另外两个属性天然在判据之外。
   用**负向前瞻** `old(?!\s*—\s)` —— **新串以旧串为前缀**，朴素 `old in text` 在正确候选上也不为 0。
4. **不变式** —— 同一事实再声明一次，不依赖声明表（声明表过期也会响）：
   **同一页内，同一张图只有一个 `alt`**（按 `(page, file)` 聚合，不是按 `file`）。
   ⛔ "全站一个文件只能有一个 `alt`"是**假断言** —— 同一张图在案例页/索引页被复用时
   **本来就该**写该页语境的 alt，写成"全站唯一"会让 8 个文件全红。

外加 **A/A 自检**、**破坏矩阵**、**具名负对照**。判据改完**两侧验响**：未修态要 FAIL、补正态要 PASS。

---

## 4. 门结果：全绿

| 门 | 结果 |
|---|---|
| **主门** | **PASS — 79 断言 / 0 FAIL**（基线 10,278,894 B → 候选 10,348,574 B） |
| **A/A 自检** | **PASS — 3/0** |
| **破坏矩阵** | **17 变异 / 17 CAUGHT / 0 MISSED** |
| **具名负对照** | **7/7 behaved as required** |
| **浏览器 E2E** | **PASS — 20 passed / 0 failed**（75 页，4m12s，0 console error） |
| **截图** | **PASS — 11/11** |

主门关键数字：

```
alt_totals   baseline_old 398 → candidate_new 398 → candidate_old 0
logo         old 150 / new 150 / left 0
still_pages  64      still_conflicts []      still_not_declared []
isRelatedTo_pages 58   product_pages 58   dosage_pages 16   formula_pages 42
audience     32 pages  (Dogs 8 / Dogs+Cats 24)
```

逐剂型 alt 普查（8 个声明串，合计 398）：

| 串 | 基线 | 候选 | 旧串残留 |
|---|---|---|---|
| SINO FRESH Soft Chews | 78 | 78 | 0 |
| SINO FRESH Dental Chews | 56 | 56 | 0 |
| SINO FRESH Powders | 56 | 56 | 0 |
| SINO FRESH Tablets | 56 | 56 | 0 |
| SINO FRESH Drops | 38 | 38 | 0 |
| SINO FRESH Fish Oil | 38 | 38 | 0 |
| SINO FRESH Liquids | 38 | 38 | 0 |
| SINO FRESH Pastes | 38 | 38 | 0 |

**`audience` 分布**（32 页 = 12 formula_EN ＋ 12 formula_ZH ＋ 4 product_EN ＋ 4 product_ZH）：
`[Dogs, Cats]` **24 页**、`[Dogs]` **8 页**（3 个 dental 配方 ×2 语 ＋ dental-chews 剂型页 ×2）。
其余 4 个剂型与另 9 个配方**没有 `audience`**（页头没写物种）。

**破坏矩阵 17 条**含本批的核心形状：`knowsAbout dropped/shortened`、`additionalProperty dropped/value changed`、
`audience dropped/audienceType changed`、`isRelatedTo shortened/reordered`、`an undeclared key added`、
`logo alt reverted on 3 pages`、`one form clause reverted`、`an unrelated alt changed`、
`the gallery aria-label / data-label / frame and stage left un-normalised`、`an ld+json block removed`、
`the printed heading edited`。攻击面覆盖三个页面类别（dosage / formula / plain）。

**具名负对照 7/7**（`candidate as-is` 必须 PASS ＋ 6 条必须 FAIL）：截断抓取、logo `alt` 未改、
未声明的新增键、非 alt 属性残留、**图集首帧与舞台未规范化**、**抓取无预检标记**。

**独立交叉核验（grep，与门结论一致，不共用代码）**：剂型页 `additionalProperty` **16/16**、
`"offers"` **0 页**、`isRelatedTo` **58 页**、`audience` **32 页**、`knowsAbout` **75 页**。

---

## 5. 本轮四个新发现（已并入 RULES §Q.8）

### 5.1 ⛔⛔ 同一个值有**四个**载体，而第四个**在捕获的 HTML 里不存在**

产品图的同一个串落在四个地方：

1. `[sf_formula_grid]` 卡片（`sinofresh_formula_product_alt()` 打印）—— 258 处渲染
2. 8 个剂型模板各 **7 处**缩略图（静态 HTML，调不到函数，只能抄同一串）—— 56 处字面量
3. **详情页图集首帧**（`sinofresh_formula_gallery_slots()`，`functions.php:1602`）—— 本轮漏掉的第三个
4. **图集缩略图条**的 `button.sf-gallery__thumb` —— **运行时由 `formula-gallery.js` 构建**

第 3 个由修复 `2017dbe` 补上。它在**每个配方页写三遍**：舞台 `aria-label`（`role="tabpanel"`，
读屏软件报的就是它）、首帧 `data-label`、首帧 `img alt`。所以修复前每个配方页上**同一个 `.webp` 有两种说法**：
卡片带视觉短语、图集首帧只有裸描述。

第 4 个是**本轮 E2E 才发现的**：它的 `alt=""` 是**有意为之的装饰性空 alt**（按钮自身
`aria-label` 才是可访问名）。这意味着：

⛔ **任何基于"捕获 HTML"的门永远看不见第四个载体** —— 它不在任何一份抓取里。
判据必须写成**不变式**（页内一图一 alt）＋**显式断言缩略图必须保持装饰性**，
否则"运行时多出来的空 alt"会被误读成产品缺陷（本轮 E2E 首判正是这么红的）。

### 5.2 E2E 的三个"工具假红"（都不是产品缺陷）

| 症状 | 根因 | 修法 |
|---|---|---|
| `FATAL not the pre-flight copy`（连续 3 次） | 探针选择器 `link[href*="sinofresh-theme"]` **先命中 favicon**；且 `logoAlt`（DOM 的**值**）拿去和 `LOGO_NEW`（`alt="…"` 的**属性串**）比 —— 一个永远无法成立的匹配 | 选择器限定 `link[rel="stylesheet"]`；新增 `LOGO_ALT = LOGO_NEW[len('alt="'):-1]`，**两种拼法各起一个名字**而不是折成一个 |
| `--report` 模式下 E10 恒绿 | 报告模式去问**当前**浏览器会话的 console（早就换了页面） | `Sweep.recorded_errors` 缓存；报告模式先灌回 `data['console_errors']` |
| `TypeError: 'set' object is not subscriptable` | 载体集是 `set`，却写了 `v[0]` | 改 `next(iter(v))` |

### 5.3 两态 provenance 只能按内容证

本批不改 CSS ⇒ 版本令牌不动 ⇒ **不能用版本号冒充 provenance**。
改为**按内容**：基线 `alt="sinofresh"`×150 且 `knowsAbout`×0；候选 `alt="SINO FRESH logo"`×150 且
`knowsAbout` 满。**"换了 SHA 但没有版本号"不等于"没换"。**

### 5.4 同文件并行 Edit ＝ 静默丢改动（本轮当场踩到）

一条消息里对同一文件发两个 Edit，**两个回执都写 Successfully edited**，**后写的整文件覆盖掉先写的**
（两次都基于同一份快照）。丢的那处**不报错、不留痕**，事后只表现为"这次编辑像没生效"。
⇒ 已升格进 playbook【铁律9】：改完立刻 `grep -c` **回读每一处**（为"几处改动都还在"而读，不只为"有没有改"）。

---

## 6. 浏览器 E2E：20 passed / 0 failed

75 页、1440×900、`2017dbe45b75`、**0 probe error、0 console error**（4m12s）：

- `knowsAbout` 每页 10 条、`additionalProperty` 与页面对账、`audience`／`isRelatedTo` 与**可见内容**对账
- **42 个参数带页面**：缩略图条存在且**全为装饰性**（`alt=""`）；`prodTabAria` 非空白
- `logoAlt` 解析到 `SINO FRESH logo`、来源是 `-preflight/` 目录的样式表
- 每页 `ld+json` 块数、`h1` 数不变

⚠️ `_backup/b2d-h5-gates/e2e-report.txt` 是 **16:29 的旧产物**（17/2，含未修的图集首帧），
`e2e.json`/`e2e.txt` 是 **16:36** 的定稿。**引用看后两个。**

---

## 7. 截图取证：11 张，判据是"尺寸 ＋ 非纯色"

`tools/b2d_h5_shots.py`（复用 E2E 的探针与 provenance 断言）：

| 帧 | 尺寸 | 字节 | 内容 |
|---|---|---|---|
| 01-desktop-top | 1440×900 | 359,672 | 首屏：hero ＋ 图集 |
| 02-desktop-gallery-stage | 607×607 | 167,613 | 舞台（`aria-label` 是读屏听到的名字） |
| 03-desktop-gallery-frame | 607×607 | 167,613 | 首帧（`alt` ＋ `data-label` 在这） |
| 04-desktop-gallery-thumbs | 72×332 | 36,809 | **载体 4**：运行时构建，其 img 必须保持装饰 |
| 05-desktop-cardwall | 1440×900 | 220,473 | 卡片墙（`isRelatedTo` 的镜像，y=3307） |
| 06-desktop-more | 1440×900 | 211,940 | "more formulas" 网格（链接第二源，y=3175） |
| 07-desktop-full | 1440×4614 | 1,074,031 | 整页 |
| 08-dosage-facts | 1440×900 | 237,732 | 四行 `additionalProperty` 的镜像（y=332） |
| 09-zh-gallery-stage | 607×607 | 168,946 | `/zh/` 同一舞台（EN/ZH 序列化不同） |
| 10-zh-dosage-facts | 1440×900 | 238,076 | `/zh/` 的 facts 带 |
| 11-phone-dosage-top | 390×844 | 73,323 | 手机端剂型页首屏 |

### ⛔ 判据的形状：字节下限是**代理指标**，会假红

上一版用"≥8000 B"被 2 帧打红：`05` 是 **282×430 的卡片，1,231 B 完全正常**
（一张 282px 宽的卡片本来就没多少像素）。**对元素裁剪，字节量不是判据。**

改判据后立刻暴露出**真问题**：`05`/`06` 解压后只有 **4 个不同的字节值 ＝ 真纯色空图**。
于是做了 A/B/C 定向实验：

```
A) 无滚动   scrollY = 0    → 282x430  distinct=4   1231 B      ← 空
B) 滚动后   scrollY = 3212 → 282x430  distinct=4   1231 B      ← 滚动无效
C) 滚动后整视口            → 1440x900 distinct=256 219067 B    ← 正确
```

**两条实测事实**：

1. `screenshot <selector>`（元素裁剪）**只在元素位于初始视口（`scrollY=0`）内时正确**；
   一旦页面滚过（人工或 `scrollIntoView` 都一样）⇒ 返回**尺寸正确但纯色的空白**。
2. **`scrollIntoView` 作为"修复"反而更糟**：把 `.sf-facts-mini` 从 22,935 B 打到 **474 B**。

⇒ 最终策略：**首屏内的元素用裁剪，首屏外一律拍视口帧**并把滚动偏移写进 note。
判据 ＝ **尺寸（PNG IHDR vs DOM 盒子，1px 属取整并打印为 note）＋ 非纯色（`MIN_DISTINCT=8`）**。
本轮 2 项 1px 差已**当 note 打印、没有咽掉**。

---

## 8. 裁决 E：80/20 审计（只出报告）

`docs/batch2d-stepH5-audit-8020.md`。**本批未改任何页面内容**（改的是 schema 与 `alt` 字符串），
所以这份审计同时是"H5 有没有偷偷改内容"的旁证。

| 指标 | 严口径 | 宽口径 |
|---|---|---|
| 正文词数中位 | **668 词/页** | 727 词/页 |
| <300 词的页 | 5/75 | 3/75 |
| **CTA 密度** | **4.4 / 千词 ＝ 0.44%** | — |

判据线（先说判据再读数）＝ **200 / 千词**量级 ⇒ 实测**低 45 倍**。
**结论：80/20 已满足且余量极大，本项关闭、无可执行动作。** 把密度"提到 20%"是反方向处方。

口径警告：本站是块主题、**没有 `<main>`**（顶层只有 `.wp-site-blocks`），正文区＝`<body>` 去
script/style 再减页头页脚（每页 `2×<header>`＋`2×<footer>`，形状为常量，工具会断言）。
**整页去标签（含 ~100 KB 行内块 CSS）口径偏高约 2.5 倍 ⇒ 不可比、弃用**（扫描档报的 `/about/` 1,930 词
就是这个口径，本报告不复用）。两口径排序偏移 >12 位的页有 4 个 ⇒ **两个口径必须并列报**。

---

## 9. 本批**唯一**的 DB 写

`alt="sinofresh"` 的真源是**媒体库 96 号附件**（`post_title = sino fresh logo`，`image/png`）：

```
wp_postmeta:  post_id=96  meta_key='_wp_attachment_image_alt'  →  'SINO FRESH logo'
```

**只读核验**（2026-09-22，`sinofresh` 库）：全库只有 96 号附件带 `SINO FRESH%` 的 alt；
`meta_value = 'sinofresh'` 的附件 **0 行**（旧串已无残留）。**回滚＝把这一行改回 `sinofresh`。**

⛔ 教训沿用 H4e：**改 DB 的批没有"候选态"** ⇒ 顺序必须是「抓基线（旧 DB）→ 改 DB → 装候选 → 抓候选」。

---

## 10. 未做 / 边界（登记 H6）

| # | 事项 | 原因 |
|---|---|---|
| 14 | Product 的 **`material`** 未声明 | 裁决 C：记录里没有材质字段（`sf_formula_*` 无此真源）。要么补一个真源，要么明确不做并记档 |
| 15 | **`WebSite` schema 全站缺** | 裁决 G：缺 `WebSite` ＋ `SearchAction` ⇒ 站内搜索不被识别。需决定是否上线 |
| 12 | `sf-facts-mini` 4 行与 H3 内容区参数行 **3 项语义重叠** | 裁决 A 让"同一事实两个来源"从 2 处变 3 处 ⇒ **并入 H6 第 4 项「MOQ 三处对账」** |
| — | `functions.php:1666` 的同族第 4 个字面量 | `"%s private label pet supplement product photo"`，是**另一句话**、不在 8 个声明串里，且**今日不可达**（`sf_formula_gallery_ids` 在 21 条记录上全空）。**刻意不动**，只记录它在哪 |
| — | `offers` 的**数据** | 代码已就位，缺的是 `sf_formula_price_tiers` 的填数（wp-admin 一步） |

`data-label` 在本主题**无任何读取者（死属性）**，但仍**必须一起规范化** —— 否则"同一文件两个说法"仍在页上。

---

## 11. 下一步

1. **commit + push**（`docs/` 与 `tools/b2d_h5_*.py` 五个工具 ＋ `docs/batchH5-shots/`）
2. **自动进 H6**（用户裁决："然后自动接 H1 位置修复（如果用户已发指令），或先接 H6"；H1 位置修复指令本轮未收到 ⇒ **先接 H6**）
3. H6 起手即 **15 项待办**（playbook【H6】段），收尾时**逐项裁决、不得遗漏**
4. ⛔ **预检副本 `084b246`（`2.10.60`）＝ H5 的基线，H6 用完前不拆**
