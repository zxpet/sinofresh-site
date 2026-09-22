# 批次 H3 全档 —— 详细内容区 + Sampling Process（纯新增批）

> **状态：Step 1–5 全过门 + E2E 全过；Step 6（`git pull`）按用户 2026-09-22 规则整条跳过。**
> 产品提交 **`4ca3aea06c54144547198b835983b4f7521a0d47`**；基线 **`109be91`（＝H2b2 预检副本断面）**。
> 声明范围：`functions.php` ＋新内容区/新 Sampling 带/新 HowTo schema、`style.css` ＋样式、`templates/single-sf_formula.html` ＋两处插入。
> 预期 DIFF 集合：**42 页**（21 详情 ＋ 21 zh）各增 3 段，**其余 33 页仅 ver 令牌动**。
> Step 0 扫描档：`docs/batch2d-stepH3-scan.md`（含三项裁决）。

---

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 产品 diff | **554 增 / 2 删**，恰 3 个文件：`functions.php` +354−1、`style.css` +184−1、模板 +16 |
| 静态/主门 | **PASS —— 八条门全过，21 条 ok / 0 FAIL** |
| 基线断面 | 从预检副本重抓 **75 页**；与 `_backup/b2d-h2b2-candidates` **掩码比对 75/75 identical** |
| 基线可交叉复现 | 独立两轮抓取（相隔 3 分钟）**60/60 SAME**；MANIFEST **75/75 行对盘核过，0 不符** |
| 候选装载 | 预检副本 = 本地 `4ca3aea` 树 **347/347 逐字节相同**；75 页全 200 |
| 主门（限定证明） | **PASS 21 条 ok / 0 FAIL**：42 页逐字节重建 = 基线 ＋ 恰好三段，33 页仅令牌动 |
| 破坏矩阵 | **15/15**，全部 CAUGHT |
| 三条负对照 | 全部 FAIL 且**具名**（缺 served 清单 / 基线目录空 / 候选=基线） |
| 离线单测 | **54 passed / 0 failed**；负对照 **6/6，每条带具名判据** |
| 浏览器 E2E | **E1–E7 全过（31 ok / 0 FAIL）**，0 console error |
| 实拍 | 16 张 live 图（4 档 × 2 带 × 2 语言）＋ 9 张离线对照图，25 文件 / 2.9 MB |
| 版本号 | **`2.10.56 → 2.10.57`**（两处同步：`functions.php:31` ＋ `style.css:5`） |
| JSON-LD 普查 | 基线 0 HowTo / 67 FAQPage ⇒ 候选 **42 HowTo** / 67 FAQPage；已存块**逐字节未动** |
| 计划外 | **无**。7 源 0/21 属"先发渲染器"预期态，非计划外 |

---

## 1. 裁决落地（用户 2026-09-22 三项全按推荐 A）

| 裁决 | 内容 | 落地方式 |
|---|---|---|
| **A1** | 内容区**只做新增** | 只渲染 Recommended For / Use Cases / Who It's For / Packaging & Specifications（Container Options / Additional Packaging / Color Options / Storage / Carton Dimensions）。**Ingredients / GA / Formula 一律不重渲染** —— ⑤ `[sf_formula_detail_actives]` 两带已承担，`functions.php:1893-1900` 记载了上一批专门删掉重复的理由 |
| **A2** | 内容区**整段一色**，交替只用在相邻带之间 | ④ Specification / ⑤ Formula & nutrition / ⑥ Ingredients & composition / 新内容区 / FAQ / Sampling **全是 `card-white`**，`bg-light` 仍自 `.sf-fdetail-more` 起。**没有**逐块条纹 |
| **A3** | **Shelf Life 不单列** | H2a 参数表已展示（读 `sf_formula_specs` 解析出的那一段，服务值 `18 months shelf life`）。`sf_formula_shelf_life` 是**已注册但无渲染器**的死键 ⇒ 登记 H6（§8） |
| **补充** | Sampling 4 步 ＋ HowTo **单一渲染函数** | `sinofresh_sampling_steps()` 一份数组同时喂 ① 可见带 ② HowTo JSON-LD，**且就是 H4 弹窗要复用的那份** |

### 内容带今天实际渲染出什么（重要，不是缺陷）

12 个 H3 源里 **11 个在全部 21 条记录上为空**（只有 `sf_formula_specs` 有值）。
所以 42 个详情页上的内容带**today 完全相同**：**一个组**（`Packaging & Specifications`），
组内**只有一个子块**（`Storage`）。

这是**先发渲染器、后填数据**，与 H2a 已获批准的同一口径（`functions.php:1975-1977`）。
它带来一个门设计上的硬约束：**实时抓取永远只走空分支，页面门分不出"渲染器работает"和"渲染器返回 `''`"**
⇒ 渲染器必须在离线单测里对着**从 `functions.php` 逐字抽取的函数体**跑（§4）。

---

## 2. 产品改了什么（`git diff 109be91 4ca3aea`）

| 文件 | 增 | 删 | 内容 |
|---|---|---|---|
| `sinofresh-theme/functions.php` | 354 | 1 | 内容区族（`sinofresh_formula_content` / `_block` / `_spec` / `_storage_line` / Carton 子块）、Sampling 族（`sinofresh_sampling_steps` / `sinofresh_formula_sampling`）、HowTo 输出、两个短码注册、版本令牌 |
| `sinofresh-theme/style.css` | 184 | 1 | `.sf-fdetail-content*` / `.sf-sampling*` 两族 ＋ 两处媒体查询；`Version:` 头 |
| `sinofresh-theme/templates/single-sf_formula.html` | 16 | 0 | 两处插入（`[sf_formula_content]`、`[sf_formula_sampling]`），**4 条注释**，不新增 `wp:` 分界 |

**模板插入落点（用户裁定的三段 run 中的 A、B 两段）：**

- **run A**：坐在 `[sf_formula_detail_composition]`（L76）与 FAQ 引导注释（L86）之间。
  锚点是 **`<!-- Batch C: the formula FAQ.`** 这条**会到达输出**的普通注释，不是 `<!-- wp:html -->` 分界（后者不进产物）。
- **run B**：坐在 `</section>` / `<!-- /wp:group -->`（L100-101）与 `<!-- Block 4: related formulas -->`（L111）之间。
- **run C**：HowTo 的 `ld+json` 块，插在 FAQPage 块**之后**（跳过 `</script>\n` 的那个换行，落点是 run C 自己的前导 `\n`）。

三段 run 的包装串分别是 `'\n%CONTENT%\n\n'`、`'\n%SAMPLING%\n\n\n'`、run C 自带前导 `\n`。

### HowTo 的落位（两处约束）

`is_singular('sf_formula')` 分支内、**FAQPage 实体计数门（`count($entities) >= 2`）之外**。
这样它①继承 RankMath/Yoast 的退让逻辑 ②继承固定的块顺序；
且**至少两个步骤**才输出，否则整块不出现。

---

## 3. 主门（`tools/b2d_h3_confine.py`，限定证明）

```
========================================================================
  ok   [0] both captures hold 75 pages; the renderer declares 4 steps
  ok   [1] exactly the declared 42 detail pages differ; 33 identical
  ok   [1] the token moved on all 75 pages, and folding it leaves exactly the 42 detail pages differing
  ok   [1] all 42 detail pages carry the content band, the sampling band and the HowTo schema exactly once each
  ok   [1] none of the 33 other pages carries any of them
  ok   [2] all 42 pages rebuild byte-for-byte as the baseline plus exactly the three declared runs, and the other 33 are unchanged apart from the token
  ok   [3] both served bands are byte-identical to the local render of the shipped functions on all 42 pages
  ok   [3] each declared run appears exactly once per detail page
  ok   [4] all 347 files match the served pre-flight copy byte-for-byte
  ok   [4] the four K1-K7 contract files are present
  ok   [4] the theme change set versus 3b9fc23 is exactly functions.php, style.css and the detail template
  ok   [5] every baselined JSON-LD block is byte-identical on all 75 pages
  ok   [5] exactly one HowTo per detail page, none anywhere else
  ok   [5] the HowTo parses and equals the steps the band renders from
  ok   [5] exactly one h1 per page on all 75 pages
  ok   [6] on all 42 pages the order is actives < content < FAQ < sampling < grid
  ok   [6] the content band renders one h2 per group, no h3, in the declared order (only the packaging group has data today, within it only Storage)
  ok   [6] params, FAQ accordion, hero CTA and the related grid all survive
  ok   [7] style.css 2.10.56 -> 2.10.57 on all 75 pages
  ok   [7] no other asset version token moved on any page
------------------------------------------------------------------------
VERDICT: PASS — all eight gates hold
```

### 3.1 门被修好的 5 处（每一处初版都是**误判**，不是产品缺陷）

| # | 症状 | 根因 | 修法 |
|---|---|---|---|
| 1 | 门对 **21 个 zh 页全瞎** | `HOWTO_MARK = '"@type":"HowTo"'` 只匹配 EN 的**紧凑**序列化。TranslatePress 会把块**重新序列化**成 pretty-printed，实测 **21 紧凑 / 21 精美**，两侧一致 ⇒ 字面匹配天然漏一半 | 换成**解析式** `ld_types()` / `find_ld_block()` / `count_ld_blocks()`，按 `@type` 判定 |
| 2 | [1] 折叠断言不成立（75 vs 42，无解） | 断言写成 `folded == len(diff)` | 改为 `folded == 75`（令牌在**每一页**都动；折叠它之后**恰好**剩 42 页有差） |
| 3 | [2] 把令牌判成 75 页全差 | 左边 `masked(t)` 已折叠、右边 `masked(craw)` 未折叠 ⇒ 非对称比较 | 两侧都过 `clean()` |
| 4 | [2] zh 的 run C 匹配不上 | 本地插入的是**紧凑**串，页面上的 zh 块是**精美**串 | 加 `normalize_ld()`：两侧都 parse 再 dump 成紧凑（**不可解析的块保持原样**，所以真差异依旧显形） |
| 5 | [2] run A/B 锚晚了一个注释 | `FAQ_OPEN`/`MORE_OPEN` 是 section 标签，而模板里的注释在它们**上面** | 新增 `FAQ_COMMENT` / `MORE_COMMENT` 两个注释锚 |

附带修掉两处工具自身缺陷：`negcontrol()` 返回了 `run()` 的 `(fails, notes)` 元组（解包成 `TypeError: sequence item 0: expected str instance, list found`）；[6] 的"四条平铺 h2"是对数据的错误假设（今天只渲染一组）。

### 3.2 放宽后仍咬得住 —— 破坏矩阵 15/15

```
=== sabotage matrix — every variant must be caught ===
  content-band-removed               CAUGHT   [1] [2] [3] [6]
  sampling-band-removed              CAUGHT   [1] [2] [3] [6]
  howto-removed                      CAUGHT   [1] [2] [3] [5]
  howto-step-dropped                 CAUGHT   [2] [3] [5]
  content-band-on-a-dosage-page      CAUGHT   [1] [2]
  style-token-not-bumped             CAUGHT   [2] [5] [7]
  undeclared-token-moved             CAUGHT   [2] [7]
  faqpage-changed                    CAUGHT   [2] [5]
  detail-page-unchanged              CAUGHT   [1] [2] [3] [5] [6] [7]
  storage-line-changed               CAUGHT   [2] [3]
  packaging-heading-demoted          CAUGHT   [2] [3] [6]
  band-moved-after-the-grid          CAUGHT   [2] [6]
  second-h1-introduced               CAUGHT   [2] [5]
  zh-howto-payload-changed           CAUGHT   [2] [3] [5]
  zh-content-band-removed            CAUGHT   [1] [2] [3] [6]
------------------------------------------------------------------------
  15/15 variants caught
```

后两条是本批**专门新加**的**中文侧**变异 —— 第 3.1 节 #1 的漏检如果没修，它们会全绿通过。

### 3.3 三条负对照（均具名）

```
  served-manifest-missing      FAIL (as required)  served manifest points at a nonexistent path
  baseline-empty               FAIL (as required)  baseline directory is empty
  candidate-equals-baseline    FAIL (as required)  candidate is a copy of the baseline
  3/3 controls failed as required
```

---

## 4. 离线单测（`tools/b2d_h3_render_unit.py`）

页面门天然的盲区是"渲染器在空数据上的行为"。所以本批把渲染器**从 `functions.php` 里逐字抽出来**跑：

- 抽取靠**内容寻址的 START/END 标记**，**不是行号** ⇒ 文件漂移不会让证据悄悄失真。
- **54 passed / 0 failed**（分节：空值守卫 / 分组的 h2-h3 层级 / 子块守卫 / 转义 / 两带契约同一性 / Sampling 带 / 短码注册）。

### 6/6 负对照，**每条都带具名判据**（不是裸 rc≠0）

| 变异 | 具名判据 | 它防的是什么 |
|---|---|---|
| `empty-prose-field-still-rendered` | no heading for an empty field | 空值字段也被渲染出标题 |
| `spec-guard-removed` | Storage is the only sub-block | 空 chips 列表留下孤儿 label |
| `storage-line-emptied` | Storage label + the exact line are on the page | 整带塌缩，连带两条守卫失效 |
| `numeral-not-rendered` | the numerals are 1,2,3,4 and are real text | 步骤序号消失 |
| `single-use-case-sent-to-the-list-branch` | one line -> paragraph, no bullet | 单条用例渲染成单点列表 |
| `content-shortcode-unregistered` | sf_formula_content is registered | 内容带根本不渲染 |

### 两条对照**修好断言之后才失败** —— 都是检查的缺陷，不是产品的

| 缺陷 | 说明 | 修法 |
|---|---|---|
| `sinofresh_formula_content_block()` 里的空值守卫**不可达** | 四个调用方各自先测了自己的字段 ⇒ 任何变异都不可能让它失败（死断言） | 删掉死守卫，责任落到 `sinofresh_formula_content_spec()` 与调用方 |
| Storage 断言**拿页面比自己函数的返回值** | `sinofresh_formula_storage_line()` 返回什么都会通过 | 钉到**字面量** |

---

## 5. 浏览器 E2E（`tools/b2d_h3_e2e.py`）

```
E1  两带：存在、顺序、文档大纲                                   12 ok
E2  页面与其 HowTo schema 不能漂移                               2 ok
E3  一整片连续白色阅读面                                         4 ok
E4  步骤标记与步骤字形                                            4 ok
E5  响应式：行数、内缩、无横向滚动                                2 ok
E6  本批不得扰动的既有不变量                                      2 ok
E7  FAQ 手风琴仍能用真实鼠标打开                                  4 ok
console errors: none
------------------------------------------------------------
VERDICT: PASS — 31 ok, 0 FAIL
```

要点摘录：

- **E3** 用 `effBg()` 沿祖先链找**第一个不透明色**，要求 5 个带**全是 `rgb(255,255,255)`** 且**上下两个邻居都是 `rgb(243,246,244)`** ⇒ 直接证明"一整片白"＋"交替只在带之间"两条裁决同时成立。
- **E4** 实测 44×44 圆形、`primary rgb(27,77,62)` 底、`card-white` 序号、h3 17px 标题、正文 `text-secondary`。
  ℹ️ `brand-green`（`#5AB735`）在 44px 标记上只有 **2.7:1**，不过 AA ⇒ 选 `primary`。
- **E5** 8 档视口：**769px 还是 4 列，768px 起 1 列**；内缩 `0 / 38 / 20px`；**任何档位都无横向滚动**。
- **E7** 真实鼠标 `move → down → up`，**前/后各做一次 `elementFromPoint` 命中校验**，作用域**限定 `.sf-fdetail-faq`**，目标选一个**闭合**的答案，并断言**页脚 3 个手风琴没有动**。

### 踩到的两个坑（工具层）

| 坑 | 症状 | 修法 |
|---|---|---|
| `set viewport '1440x1000'` **被静默忽略** | `innerWidth` 八档恒为 1280 —— E5 其实把**同一个布局量了八次** | CLI 要**两个参数** `set viewport <w> <h>`；并且加 **FATAL 断言**：`viewportW` 必须等于请求值 |
| E7 数出 **12 个 `<details>` / 4 个展开** | 9 个 FAQ 答案 ＋ 3 个页脚手风琴，而且 **FAQ 块默认展开第一条** ⇒ "点第一条"其实是把它**关上** | 限定 `.sf-fdetail-faq`、要求 `faqItems == 9 / faqOpen == 1`、**点一条闭合的**、并断言页脚不动 |

启动纪律（四步，顺序不能错）：
`close --all → set credentials → open origin → set headers{Authorization, X-SF-Preflight} → errors --clear → open url → reload → set viewport w h → eval`
`goto()` 每次都断言 ① `viewportW` 等于请求 ② 样式表是 `sinofresh-theme-preflight` ＋ `ver=2.10.57`。

---

## 6. 基线与候选的取证路径

| 环节 | 做法 | 结果 |
|---|---|---|
| 基线断面 | 预检副本（仍＝H2b2 候选 `3b9fc23` 树）重抓 75 页 | 与 `_backup/b2d-h2b2-candidates` **掩码 75/75 identical** |
| 基线来源可信度 | 独立两轮抓取（相隔 3 分钟）交叉复现 | **60/60 SAME** ⇒ 排除 Cloudflare 缓存干扰 |
| 清单对盘 | MANIFEST 75 行 逐行核磁盘 | **75/75，0 不符** |
| 候选装载 | `install <全 40 位 SHA>` 进预检副本 | 75 页全 200 |
| 副本 = 提交 | 347 文件逐个 sha256 vs `4ca3aea` 树 | **347/347 逐字节相同** |
| 服务资源确证 | 单页探针 | `2.10.57`=1、`2.10.56`=0、`-preflight`=16、HowTo=1 |

**695 vs 347 的疑团已闭环**：主题树实为 **695** 个文件，其中 **348** 个在**嵌套的 `sinofresh-theme/_backup/`** 里。
服务/提交的比对集是 **347**（与 H2b2 的 "347/347" 对得上，且 `git ls-tree -z` 同数为 695）。

### JSON-LD 普查（按解析，不按字面）

| | 基线 | 候选 |
|---|---|---|
| FAQPage | **67** | **67** |
| HowTo | **0** | **42** |
| 不可解析块 | 0 | 0 |
| 已存块是否变化 | — | **逐字节未动** |

---

## 7. 实拍（`docs/batchH3-shots/`，25 文件 / 2.9 MB）

`live-{content,sampling}-{en,zh}-{1440,1101,768,480}.png`（34–87 KB，**非空白**）共 16 张，
由 `tools/b2d_h3_shots.py` 产出：视口抬到"带高 +220"（上限 3000）、`scrollintoview`、整屏截图，
并断言①视口真的生效 ②样式表是本批的 ③任何 PNG **< 8000 B 即 FAIL**。
（`< 8000 B` 这条来自 H2b1 的教训：`screenshot <selector>` 曾写出 1.7 KB 纯白图，看着像证据。）
另有离线对照 9 张（`filled-*` / `empty-*` / `sampling-1440-1to1.png`）。

---

## 8. 本批新造的死角 —— 登记 H6，本批不动

| # | 死角 | 实测 | 为何不动 |
|---|---|---|---|
| 1 | **`sf_formula_shelf_life` 是已注册但无渲染器的死键** | `inc/formula-admin.php:42/106` 注册（group `packaging`, req 2）；`functions.php` 里只在 **2278/2288 两条注释**出现；**没有任何前台读取**。H2a 的 `Shelf life` 行读的是 `sf_formula_specs`（L1968 / L2035 解析 "… shelf life" 段），服务值 `18 months shelf life` | 用户裁决 A3：**不单列**。删键属数据改动（停机类）⇒ 登记 H6 一并处理 |

> ⚠️ 这一项是"同一个事实存两个来源"的典型：删掉渲染器之外的任何一半都会让页面漂，
> 所以它只能作为**一对**（键＋H2a 行）在 H6 里一起裁决。

---

## 9. 证据索引

| 文件 | 内容 |
|---|---|
| `docs/batch2d-stepH3-scan.md` | Step 0 扫描全档（三项裁决的前提） |
| `docs/batchH3-gates/main-gate.txt` | 主门运行记录（21 条 ok） |
| `docs/batchH3-gates/matrix.txt` / `matrix.json` | 破坏矩阵 15/15 |
| `docs/batchH3-gates/negctl.txt` / `negctl.json` | 三条负对照 3/3（具名） |
| `docs/batchH3-gates/unit.txt` / `unit-negctl.txt` | 离线单测 54 passed ＋ 6/6 具名对照 |
| `docs/batchH3-gates/e2e-run.txt` / `e2e.json` | E1–E7 全量（31 ok） |
| `docs/batchH3-gates/served-copy-sha256.txt` | 预检副本 347 文件 sha256 清单 |
| `docs/batchH3-gates/local-tree-sha256.json` | 本地 `4ca3aea` 树 sha256 |
| `docs/batchH3-gates/{baseline,candidate}-manifest.tsv` | 两侧 75 页断面清单 |
| `docs/batchH3-gates/baseline-vs-h2b2-candidates.json` | 基线 vs 上一批候选（75/75） |
| `docs/batchH3-gates/baseline-cross-tool-replication.json` | 独立两轮交叉复现（60/60 SAME） |
| `docs/batchH3-shots/` | 16 张 live ＋ 9 张离线对照 |
| `tools/b2d_h3_confine.py` · `_render_unit.py` · `_e2e.py` · `_shots.py` · `_preview.py` | 本批工具链 |
| `_backup/b2d-h3-baselines-alt/` | 换名前的 60 个重命名副本（口径修正留档） |

---

## 10. 交 H4 的不变量

1. **上线不存在**：`git pull` 整体跳过；live 长期停 `2.10.55` ＋ 配置器是**预期状态**。
2. **基线 = 上一批的预检副本**，**本批的候选断面是 `_backup/b2d-h3-candidates/`** —— 它就是 H4 的基线。
   预检副本（现＝`4ca3aea` 树，347/347）**在 H4 用完之前禁拆**。换候选前先 `git fetch`，`install` 前置检查必须 `if`/`exit`。
3. **`sinofresh_sampling_steps()` 是 H4 弹窗必须复用的那一份**：4 步文案 ＋ HowTo 都从它出。
   改动它会同时改 ①可见带 ②JSON-LD ③H4 弹窗 —— **三处同步**。
4. 详情页带序（H3 之后）：media → spec → actives → **content** → FAQ → **sampling** → more(grid)。
5. `:has(` 全站仍 **164**（本批未动）；`configurator.css` / `configurator.js` 已不存在，任何"迁回"都是回退。
6. **HowTo 在 `is_singular('sf_formula')` 分支内、实体计数门之外** ⇒ 加新的结构化数据时**不要**碰那个 `count($entities) >= 2` 门。
7. H6 待办清单由 **8 项增至 9 项**（本批 1 项见 §8）。
