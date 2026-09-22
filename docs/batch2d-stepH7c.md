# 批次 H7c —— 阅读区顶部新增「参数明细表」12 行（新模块，不是改造）

**状态**：Step 1–5 全部完成。门四件套全绿（75/75 主证、覆盖 22 项、不变式 13 项、遮蔽读回 23 页 0 差），
源码检查 30/30，破坏矩阵 5/5 抓到，具名负对照 NC1–NC15 15/15，浏览器 E2E 39/0，截图 5/5 非平帧，
限定证明 14/14 ＋ NC1–NC5 5/5。**Step 6（`git pull` 上线）按规则跳过** —— 本批只交候选。

**提交**：`5b80d11`（主题 3 文件，`+286/−2`）→ 本收尾提交（门声明 ＋ 门机制泛化 ＋ 限定证明工具 ＋ 浏览器 pass ＋ 截图 ＋ 本档）。
｜**令牌** `2.10.63 → 2.10.64`（`functions.php` enqueue ＋ `style.css` 头 `Version:` 两处同步）。

**⛔ 本批基线 ＝ `5c92ac8`**（H7b 收尾，`2.10.63`）的预检副本 —— 本批**唯一**的字节基准。
**本批不改数据、不动业务字段、不扩范围**（DB 零写入；只跑过只读 SQL）。

**用户裁决（2026-09-22）**：H7c 的 A/B/C 提问**都不是** —— 这是**新增**一个模块，不是改造既有模块。

---

## 0. 本批是什么形状：`mode: delete`（与 H7a／H7b 相反）

H7a/H7b 的主证方向是「**替换**一个基线里已经存在的串」—— 所以期望页可以从基线**造**出来。
H7c 是**新增**逐记录不同的标记（同一张表，A 记录 8 行、B 记录 10 行），基线里没有任何串能拼出它。
两条出路，只有一条诚实：

| | 做法 | 为什么不用 |
|---|---|---|
| ❌ | 从基线自己的页面**重建**这张表（剂型面包屑、解析后的规格行、配料 pill 都在页面上） | 等于教门去**渲染**。会渲染的门就能和渲染错的作品达成一致 —— H6 扫描拒绝「重新推导一个本该被测量的值」正是同一个理由 |
| ✅ | 从**候选**里**删掉**声明区域，要求剩下的一字不差等于基线 | 什么都不重新推导；载荷是被**声明**的，不是被**造**出来的 |

本批主证打印的方向因此是 `mask(transform(candidate)) == mask(fold(baseline))`，而不是 H7b 的
`mask(transform(baseline)) == mask(candidate)`。**门现在读声明里的 `mode` 并交换方向。**

| | H7a | H7b | **H7c** |
|---|---|---|---|
| 改动性质 | 删列 ＋ 加开关 | 改身份（`button`→`a`） | **纯新增**一段逐记录内容 |
| 主证方向 | 替换 | 替换 | **删除**（`mode: delete`） |
| 新增判据 | — | 计数双向 ＋ 顺序 | **作用域计数 `scoped`** ＋ **占位断言 `order`** |

### 0.1 `mode: delete` 的代价，写在脸上（不是藏起来）

区域被**整段**删掉，所以载荷自身的字节**不参与**主证比较。这不是要糊上的洞，是分工：

- 载荷的**内容** → **覆盖断言**（在**原始候选**上计数）；
- 载荷的**每页形状** → `scoped`（每个详情页恰一次、别处零次）；
- 载荷的**位置** → `order`（四个锚点的先后）。

三者各自被破坏测试覆盖（矩阵）＋ 各自有具名负对照。**NC13 就是把这件事说出来**：
把表内一行标签改名，要求 `main_green=True AND coverage_red=True` —— 一条只展示失败的负对照，
会把影响半径留在未测量状态。

---

## 1. 实际执行的改动（声明清单）

### 1.1 模板：一个新块，42 个详情页

`templates/single-sf_formula.html` 在「Block 3: long copy」之前插入：

```html
<!-- H7c: the spec sheet. Emitted whole by its shortcode; the placement and the
     row sources are in the renderer's docblock (functions.php). This comment
     ships into the page like every other one in this file — keep it short. -->
<!-- wp:html -->
[sf_formula_specs_table]
<!-- /wp:html -->
```

⛔ **注释就是页面字节**（H7b 5.1 的同一课，本批又踩了一次）：前两版注释写成长段散文，
已回撤成两行。基线上 H5-0／B2D-S3／batch G 的注释都是**逐字**在页面里的（各计数 1），
所以载荷正则必须把这段注释一起声明。

### 1.2 渲染器：`sinofresh_formula_specs_table()`（`functions.php`，＋174 行）

12 行（**不是 13 行**），值全部来自页面已经信任的来源：

| 行 | 来源 |
|---|---|
| Dosage Form | taxonomy `sf_formula_form`（用 term 自己的 name） |
| Applicable Pet | `sf_formula_species`（多值，chips） |
| Life Stage | `sf_formula_lifestage`（文本） |
| Shape | `sf_formula_shape`（文本） |
| Unit Weight | `sf_formula_specs`（解析：unit 段） |
| Pack Size | `sf_formula_specs`（解析：`… per …`） |
| Shelf Life | `sf_formula_specs`（解析：`… shelf life`） |
| Main Ingredients | `sf_formula_ingredients`（前三个） |
| MOQ | 剂型页 `.sf-facts-mini` 行（经 `spec_cell`） |
| Certifications | Site Settings `sf_certifications`（与 factsheet 行、batch C 的 FAQ 答案**同一个读取器**，三者不可能互相矛盾） |
| Place of Origin | 硬编码 `Linyi, Shandong, China`，**H7e 移到 Site Settings** |
| OEM / ODM | 硬编码 `Available`，**H7e 移到 Site Settings** |

**Lead Time 被丢弃，不是合并**（用户的第 13 行留给渲染器裁决）：它在媒体列的参数表里**已经有一行**，
而唯一能与它共格的是 MOQ —— 那会把「from 500–1,000 units」和「Typically 7–15 working days after
packaging is ready」拼成一句关于数量的句子。丢掉它，页面一个事实也没少。

三条设计决定，都写进了 docblock：

1. **空 = 不渲染**（沿用 `[sf_formula_params]` 的契约）：`sf_formula_species` 与 `sf_formula_lifestage`
   两个 meta **今天在 21 条记录上一条都不存在**（实测：这两个 key 在 `wp_postmeta` 里查不到），
   所以这两行今天**全站不出现**。前两行是留给销售填的，不是留给部署的。
2. **Shape 读一个没人注册的 key**：该字段早于 meta 注册表，只存在于 1 条记录上；WordPress 读未注册
   key 不报错，而在这里注册它，等于对外宣告一个表单其余部分都还没提供的发布字段。
3. **切分是对「实际渲染出来的行」做的**（`ceil(n/2)`），不是对字段清单做的：9 行的记录得到 5 ＋ 4。
   对字段清单切，会让某一列少了三个字段后留下一段空 —— 正好是两列的反面。

### 1.3 CSS：`38a-ii` 一段（`style.css`，＋107 行）

`.sf-fdetail-specs`（48px 0／card-white）→ `__inner`（两列 grid、64px column-gap）→ `__group`／`__row`
（150px/40% 标签 ＋ 值，发丝下边）→ 首末行收边 → `__term`（13px/600/secondary）→ `__value`（15px）
→ `__chip`（描边胶囊，999px）。

**四个块的顺序是承重结构**：基础规则 → `1240` → `900` → `768`。
⛔ **媒体查询不增加优先级** —— 写在它要覆盖的规则**上面**的步进在每个宽度上都是死的
（H7b 5.3 的同一课）。文件语法里没有任何东西能抓到这件事，所以源码检查里有一条**顺序断言**，
并且一条具名负对照（NC9）专门把这个手机步进**搬到基础规则上面**，要求源码检查失败。

`900` 不是 `768`：两列的 150px 标签＋值在 768 就已经放不下（值列不足 300px，配料 chip 每个都换两行）。

---

## 2. 门的形状与结果（基线 `5c92ac8`，候选 `5b80d11`）

```
python3 tools/b2d_h7_gate.py --batch h7c \
        --base _backup/b2d-h7c-baselines --cand _backup/b2d-h7c-candidates \
        --aa _backup/b2d-h7c-candidates-aa --matrix --negctl
```

| 件 | 结果 |
|---|---|
| A/A（同一态两次抓取） | **75 页比较 / 0 页不同** |
| 主证 `mode: delete` | **75 页 / 0 页不同 / 应用 42（声明 42）** |
| 覆盖断言 | **22 项**：`?ver=2.10.63`→0、`?ver=2.10.64`→75、`class="sf-fdetail-specs"`→42、`__group"`→84、6 个标签各 42，＋ 14 项两侧计数 |
| 不变式 | **13 项**：5 项未动计数、每页 `h1`=1、`scoped` 2 项、`order` 3 项、`h2` 位移 0、JSON-LD 75 页 deep-equal |
| 遮蔽读回 | 23 页 GF 状态块 / 0 差；46 个被抹掉的金额值 |
| 破坏矩阵 | **5/5 抓到**（每个变体都改变页数，无空转） |
| 具名负对照 | **NC1–NC15 15/15** |

### 2.1 覆盖断言里各项的实测值（两侧）

| 项 | base → cand | 期望 |
|---|---|---|
| MOQ 每页多一行 | 18 → 60 | 18 → 60 |
| Certifications 每页多一行 | 58 → 100 | 58 → 100 |
| 产地行每页多一行 | 154 → 196 | 154 → 196 |
| Applicable Pet 空行不印 | 0 → 0 | 0 → 0 |
| Life Stage 空行不印 | 0 → 0 | 0 → 0 |
| **Lead Time 一行都不加** | 2 → 2 | 2 → 2 |
| Pack Size 只在有该段的记录上印 | 40 → 60 | 40 → 60 |
| Shape 只在有它的记录上印 | 0 → 2 | 0 → 2 |
| 媒体参数表未动 | 42 → 42 | 42 → 42 |
| actives 带未动 | 42 → 42 | 42 → 42 |
| content 带未动 | 42 → 42 | 42 → 42 |
| 参数行未动 | 234 → 234 | 234 → 234 |

### 2.2 42 页上的行分布（实测，不是估算）

| 行数 | 页数 |
|---|---|
| 8 行 | 22 |
| 9 行 | 18 |
| 10 行 | 2 |

标签出现次数：Dosage Form／Unit Weight／Shelf Life／Main Ingredients／MOQ／Certifications／
Place of Origin／OEM-ODM 各 **42**；Pack Size **20**；Shape **2**（1 条记录 × EN+ZH）；
Applicable Pet／Life Stage／Lead Time 各 **0**。

---

## 3. 源码检查（30/30，`--source`）

模板 5 项（短码被调用、在长文之前、在 Specification 带之前、在 Ingredients 带之前、在媒体带之后）、
渲染器 14 项（注册、post type 守卫、9 个取值来源、三个"不做"的断言、切分依据、整段发射）、
令牌 4 项（enqueue 已 bump、旧 enqueue 0、`Version:` 2.10.64、旧头 0）、
CSS 6 项（白底、桌面两列、行列网格、**四个块顺序**、手机一列、胶囊词汇）。

---

## 4. 浏览器 E2E（39/0，`tools/b2d_h7c_e2e.py`）

复用 H7b 的会话层（`attach`：`close` → `set credentials` → `open` → `set headers{Basic＋自定义}`；
`goto`：`open` → `reload` → 视口 → **断言拿到的是哪一份资源**；每次点击后 `on_page()` 守卫）。

四件字节门看不见的事，全部是**布局**：

| 断言 | 实测 |
|---|---|
| 两列**真的并排** | 两 group `top` 1396 / 1396，`left` 120 / 752；`grid-template-columns: 568px 568px`；`column-gap: 64px` |
| 手机**真的堆叠** | 420 宽：group0 bottom 2363 ＝ group1 top 2363，`left` 20 / 20；`grid-template-columns: 380px` |
| 位置**在屏幕上**递增 | 媒体参数表@749 → 表@1348 → Specification 带@1881 → actives 带@2100 |
| 空行**对读者确实不在** | 10 行；Applicable Pet／Life Stage／Lead Time 三个标签都不在渲染出的行里 |

其余：`h1` 全页恰 1、表内 0 个 `h1`／0 个 `h2`、chip 3 个且 `border-radius: 999px`、
420 宽下 `overflow = 0`、1440 下 `overflow = 0`、ZH 页表在且**与 EN 标签逐字相同**（短码不是副本）。

截图 5 帧（`docs/batchH7c-shots/`），**非平帧断言**（解压 IDAT 后 distinct 字节 > 8）：5/5 通过，
256 个不同字节值，0 平帧。折叠线以下的元素一律用**视口帧 ＋ 显式滚动偏移**取。

---

## 5. 限定证明（14/14 ＋ NC1–NC5，`tools/b2d_h7c_confine.py`）—— 本批补上的一处洞

**字节门看不见 `style.css`**，而且不是偶然：样式表从不进入页面字节。对一条**既有**规则的改动
（本批从未声明的），会让 75 页全部字节相同，而读者看到的东西变了。所以样式表要按自己的语言立据：

- `style.css` **只失去**版本头一行；
- `style.css` **只获得** 新版本头 ＋ **一段连续块**，块内打开的每个选择器都必须属于声明命名空间；
- `functions.php` **只失去** enqueue 一行；获得的就是新渲染器；
- 模板**只增不减**。

**「连续」是承重的那一半**：「每一行都提到命名空间」这条弱判据，会被散落在文件各处的编辑满足 ——
而这个工具要抓的失败，恰恰是**别处**的一处编辑，它按定义不带那个令牌。

工具自己先错了两处，都是被**具名负对照**抓出来的（值得留档）：

1. **`@media (max-width: 1240px) {` 被当成外来选择器** —— at-rule 是**容器**不是选择器，
   不能带类名；能带且必须带的是它**里面**的规则。于是 at-rule 走白名单（只许 `@media`/`@supports`），
   其余「提到 `{` 的行」都算选择器。
2. **单行写法 `.a { color: red; }` 完全看不见** —— 按 `endswith('{')` 找规则开头的判据，
   对单行规则一行都看不到（NC5 抓到的）。改成「注释之外、提到 `{` 的行」，注释用状态跟踪而不是前缀跳过。

---

## 6. 本批四处发现

### 6.1 ⛔ A/A 拿错态，看起来就像 75 页回归（本批最大的过程教训）

第一次跑门时 `--aa` 指到了一个**基线时代**的抓取目录（`b2d-h7c-baselines-aa`）。结果不是报错，
而是 **75 页全红**、每页差异都是 `?ver=2.10.64` vs `?ver=2.10.63` —— 一条**读起来完全像真回归**的
失败。当时被 `tail -40` 截掉，只能从 JSON 里才找到病根。

已修：`aa()` 现在在比较前**断言两次抓取是同一个态**（比对两份目录携带的 `?ver=` 令牌画像），
不同就 `FATAL` 中止并打印两侧令牌 —— 「不可静默通过」的依据是**说不清就中止整轮**。
同一次还把第二个洞补上：**页集不同必须 FAIL**，而不是悄悄按交集比（比 74/75 页看起来和比 75 页一模一样）。
两条都配了控制：**NC14**（拿另一个态的抓取喂给严格 A/A，必须中止）、**NC15**（抽掉一页，必须 FAIL）。

⚠️ 同场修正：`aa()` 同时被 **NC6**（"A/A against a different state fails"）当**灵敏度探针**用 ——
那里两个态**本来就该不同**。所以判据拆成「原语 `_page_diffs()` ＋ 策略 `aa(strict=)`」，
NC6 走 `strict=False` 才既能拿到结果、又不与守卫冲突。

### 6.2 空行也是页面字节（H7b 5.1 的同一课）

`H7C_PAYLOAD` 少了开头的 `\s*`：删掉了注释和 `<section>`，却把插入块**自带的那几个换行**留下了，
于是 42 页每页多 3 个换行，主证在**纯空白**上失败（`expected 126104 B / candidate 126107 B`）。
**判据是对的，错的是声明。** 修完 NC2、NC13 两条假失败同时转绿。

### 6.3 ⛔ 多值单元格在提取文本里**粘成一坨** —— 但这是**既有**性质，不是本批引入的

浏览器 pass 打出 `Main Ingredients = 'Glucosamine HClChondroitin SulfateMSM'`（三个 chip 的
`textContent` 无分隔）。按本项目的 SEO/GEO 标准，这值得查。

**实测（同页对比，决定性证据）**：**未被本批触碰**的媒体参数表粘得更彻底 ——
`'FlavorChickenBeefLambSalmonPeanut ButterCheeseMint'`、`'CertificationsFDAcGMPISO 9001FSSC 22000HACCPBRC'`。
即：这是**全站既有**的标记性质，H7c 的 chip 与它一致，**不是本批回归**。

**裁决：不在本批修**（不在声明里、会扩范围），**登记**为未来批候选：
「多值单元格的可提取性」—— 涉及 `.sf-fdetail2__params`、`.sf-actives__pill` 列表、本批新表三处，
需要一次统一的定调（把内联 chip 换成 `<ul>/<li>` 与既有配料列表同词汇，或给容器加可见分隔）。
证据留在本档，将来不必重新测量。

### 6.4 门机制的泛化（本批新增，供 H7d–H7f 复用）

`mode`（主证方向）、`scoped`（声明子集上的每页计数）、`order`（两锚点先后）、
`nc_source`／`nc_page`／`nc_blind`（三类新负对照）全部进了 `BATCHES[...]` 声明机制；
`b2d_h7c_confine.py` 已参数化（`--ns`／`--expect-php`／`--tpl-line`），H7d–H7f 只要给
`--base/--cand/--ns` 就能直接用。

---

## 7. 证据清单

| 路径 | 内容 |
|---|---|
| `docs/batchH7c-shots/` | 5 帧：桌面整页／桌面表／桌面「媒体带＋表」同帧／手机表／手机 ZH 表 |
| `_backup/b2d-h7c-baselines/` | 基线抓取（75 页，`?ver=2.10.63`） |
| `_backup/b2d-h7c-candidates/` · `-aa/` | 候选抓取两次（75 页，`?ver=2.10.64`，A/A 用） |
| `_backup/b2d-h7c-gate.json` | 门结果全文 |
| `_backup/b2d-h7c-full.json` | 浏览器 pass 39 条断言全文 |
| `tools/b2d_h7c_e2e.py` · `tools/b2d_h7c_confine.py` | 本批新增的两个工具 |
| `tools/b2d_h7_gate.py` | `mode`／`scoped`／`order`／三类新负对照 ＋ A/A 守卫 |

---

## 8. 服务器状态与下一批

- **预检副本现＝ `5b80d11`（`2.10.64`）＝ H7c 候选态**；复核锚点：`link` 指 `sinofresh-theme-preflight/`
  ＋ `style.css?ver=2.10.64` ＋ 详情页 `.sf-fdetail-specs` ×1（2 group）＋ 全页 `h1` 恰 1
  ＋ `functions.php` sha256 `9f5b7125…` ＋ `style.css` sha256 `61d4612f…`。
- **基线副本 `5c92ac8` 现在＝ H7c 的基线**，下一批（H7d）用完前**禁拆**。
- **下一批（H7d）的基线 ＝ 本批收尾提交**（主题态与 `5b80d11` 相同）。
- 本批**未上线**（Step 6 跳过）；dev live 仍是 pre-H2b1 态，属预期。
