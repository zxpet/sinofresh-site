# Batch H8a — 上线前剩余任务 · 批 1／3：右栏（主图吸附 ＋ 六项配置修补 ＋ 保质期固定池）（2026-09-23）

> 上游指令：「上线前全部剩余代码任务合并执行」，分 3 批，每批完成后 commit + push，无停机条件就自动进下一批。
> **本批＝批 1（H8a）**；批 2＝待办24「Shape/Container 按剂型差异化」；批 3＝待办21「Services 4 详情页」。
> 用户明示约束：**不 pull 到 dev（等单独授权）**、不引入 ACF／JS 库／CSS 框架、不碰 post meta（数据问题只报告）。
> **停机条件**：① 扫描与预期方向不符 ② 门抓到产品 bug ③ 需要用户裁决。本批触发过 ③ 一次（四项裁决，见 §〇·2）。

---

## 〇、本批范围与四条裁决

### 0.1 五项待办（27 含两半）＋ 版本

| 待办 | 内容 | 载体 |
|---|---|---|
| **23** | 详情页主图在 ≥769px 吸附（`top:100px`） | `style.css`（4 行） |
| **26** | 右栏参数区删掉 `Packaging` 行（后台字段保留） | `functions.php` |
| **27** | Flavor / Pack Size 改**单选**；每个可选项组末尾追加 **Custom** 选项 ＋ 服务端渲染的输入框；提交值打 `(custom)`；提示语 `Choose one or more` → `Choose one` | `functions.php` ＋ `config.js` ＋ `formula-admin.php` |
| **28** | 右栏折叠切点从第 4 组移到第 5 组（**只 ≤480**）；Shape/Container 由换行改**单行横滑**＋箭头 | `config.js` ＋ `style.css` |
| **29** | 保质期改读固定池 `sf_formula_shelf_life`（12/18/24/36 months）；前台两处只打印 `"18 months"`（不再重复自己的标签） | `inc/formula-pools.php` ＋ `functions.php` ＋ `formula-admin.php` |

版本 **`2.10.73 → 2.10.74`**；`config.js` **`1.3.0 → 1.4.0`**。其余令牌不动（formula-gallery.js `2.2.0`、formulas.js `1.2.0`）。

### 0.2 四条用户裁决（本批停下来征询的部分）

| 问 | 用户裁决 | 落点 |
|---|---|---|
| 折叠后哪几组常显？ | **pricing 常显 ＋ 其后 3 项** | 切点 `nth-child(n+5)`；`pricing` 永不进 fold 掩蔽 |
| 折叠宽度？ | **维持现状：只 ≤480 手机** | 481–768 仍是 H7d 全屏抽屉，不受影响 |
| 保质期值从哪来？ | **前台改读固定池 `sf_formula_shelf_life`** | 池 = 12/18/24/36 months |
| Custom 覆盖几个维度？ | **7 维一致：列出的 6 维 ＋ Shape** | `flavor, weight, pack, species, stage, shape, container` |

> **7 维 vs 渲染层 5 组**：`species`（Suitable For）与 `stage` 在今天的 21 条记录里 **0 次渲染**（见 §三·二 coverage `sf-fdetail-config__group` 110/110），所以页面上能打字的只有 **5 组**；另两维只在库层/后台可见 ⇒ 它们的 Custom 选项**由 `--source` 断言覆盖**，不靠渲染层断言。

### 0.3 两条只报告、未改数据的事实

1. **待办26 被删的那一行，值不来自 `sf_formula_packaging_extra`**。该字段 1/21，打印在正文 `Additional Packaging` 下；被删的行读的是**剂型页自己的 `.sf-facts-mini` 单元格**（`sinofresh_formula_facts_props()` 直接读它）。所以删这一行**不动任何 schema**，Product JSON-LD 也从未有过 `Packaging` 属性（门里 `json-ld deep equal` 75 页全等，正是这条的证据）。该单元格**仍在 `/products/*/` 打印**，E2E 有一条断言专门守它。
2. **post 158 的 `sf_formula_shelf_life` meta 原文是 `24months`**（没空格），而它的 `sf_formula_specs` 里写的是 `18 months shelf life`——**两者互相矛盾**。代码侧只做两件事：读取器归一化（`24months → 24 months`，所以页面上不会出现后台无法产出的值）＋ `keep_unknown` 保证保存时不清空。**值本身待销售确认**，不改。

---

## 一、实现要点（为什么这么写）

### 1.1 待办23 主图吸附：4 行就够，因为两个前提早就成立

- 那个带的栅格已经是 `align-items: start`（否则子项会被拉满高，`sticky` 无从生效）；
- `style.css` 顶部的横向溢出守卫是 **`overflow-x: clip`**（不是 `hidden`），且原注释就写着它要给 `position:sticky` 让路。
  ⇒ **`clip` 不创建滚动容器**，所以祖先链上没有任何一层会吃掉 sticky。E2E 有一条断言专门读这条守卫（`...because nothing between it and the root clips`）。

### 1.2 待办27 单选 ＋ Custom：四件必须做对的事

1. **Custom 输入框必须是选项列表的兄弟，不能是 `<label>` 的子节点**——`<label>` 里的 `<input type=text>` 会在每次点击时把 radio 又切一次。
2. **输入框由服务端渲染并带 `hidden`**，所以**无 JS 时该组仍然能提交一个 `Custom` 答案**（降级不是"退化到不能选"）。
3. **端点也跟着改，但改得有界**：只有在**该组自己提供了 Custom 选项**时才接受自由文本；文本 `sanitize` ＋ 截断 60；落库时打 `"{答案} (custom)"`，让销售一眼分清"客户打的字"和"目录里的选项"。H7d 的旧规则（请求说**选哪几个**、服务端说**它们叫什么**）对其它所有值继续成立。
4. **Custom 输入类型跟着该组自己的字节走**——`'checkbox' if 'type="checkbox"' in body else 'radio'`。因为 `species`（Suitable For）**保持多选**，它的 Custom 是 checkbox。**这一条是负对照逼出来的**（§三·四）。

### 1.3 待办28 折叠切点与横滑

- H7l 已按用户裁决把**价格阶梯移到简介下**，它现在是右栏第一组 ⇒ 旧切点（第 4 组起折叠）会把价格折掉。切点移到 **`nth-child(n+5)`**，`pricing` 常显。
- Shape/Container 从"折成两行"改成"**一行 + 横滑**"，由 `config.js` 造箭头（**"没有滑块的滚动条不是可供性"**）。
- 箭头 `display:inline-flex` 写过值却是 `flex`——**绝对定位会 blockify**，所以断言读 rect 尺寸，不读字面 display（§四·二）。

### 1.4 待办29 去冗余

两条前台行（右栏 `sf-fdetail2…Shelf life` 与正文 `sf-fdetail-specs…Shelf Life`）改读池值。**去冗余就在读取器的回退路径上**：回退解析 `sf_formula_specs` 时把尾部的 `"shelf life"` 丢掉，因为两行自己已经带了标签。⇒ 页面从 `18 months shelf life` 变成 `18 months`。
**JSON-LD 的 `Standard Specs` 与相关卡片仍保留原串**（预期不变，门里 `json-ld deep equal` 75 页证明）。

---

## 二、改动清单（提交 `c43708e`）

```
 sinofresh-theme/assets/js/config.js   | 119 +++++++++++++++++--
 sinofresh-theme/functions.php         | 215 ++++++++++++++++++++++++++++------
 sinofresh-theme/inc/formula-admin.php |  41 ++++++-
 sinofresh-theme/inc/formula-pools.php |  61 ++++++++++
 sinofresh-theme/style.css             | 151 +++++++++++++++++++++---
 5 files changed, 520 insertions(+), 67 deletions(-)
```

**证据段（本文件所在提交）**：`tools/b2d_h7_gate.py`（新增 `BATCHES['h8a']`）、`tools/b2d_h8a_e2e.py`、`tools/b2d_h8a_shots.py`、`docs/batchH8a-shots/`（14 PNG）、本档、记忆。

---

## 三、门（`tools/b2d_h7_gate.py --batch h8a`）

基线＝上一批预检副本（**H7l，2.10.73**）；候选＝本批预检副本（**H8a，2.10.74**）；A/A 用同版本第二份抓取。

| 段 | 结果 |
|---|---|
| **A/A**（同状态两份抓取，掩码下） | **75/75，0 差异** ✅ |
| **主证** `mask(transform(baseline)) == mask(candidate)` | **75 页 0 差异**；`applied = 314 (declared 314)`，`applied_base = 0`，mode = `insert` ✅ |
| **coverage** | **25/25** ✅ |
| **invariants** | **22/22** ✅ |
| **掩码回读**（掩码擦掉的字节） | 23 页 **0 differ**，46 个二进制段 ok ✅ |
| **破坏矩阵** | **11/11 全捕获** ✅ |
| **具名负对照** | **25/25 全响** ✅（NC1–8 ＋ NC-src 10 条 ＋ NC-page 3 条 ＋ NC13 ＋ NC14/15/16） |
| **源码段 `--source`（独立跑）** | **35/35** ✅ |

**JSON**：`_backup/b2d-h8a-gate.json`（主证/AA/coverage/invariants/readback/matrix/negctl）、`_backup/b2d-h8a-gate-source.json`（源码段）。
⚠️ `--source` 是 `main()` 里的 **if/else 分支**，与 `--base/--cand` 同传只跑源码段却照样打印 PASS ⇒ **必须独立跑一次**，所以每批是**两个 JSON**。

### 3.1 `applies = 314` 的逐条算术（必须自洽，否则就是声明写错）

```
74  红框改单选（flavor/pack 两组的 checkbox → radio）
+ 2  提示语 Choose one or more → Choose one
+108 追加 Custom 选项（每组一个）
+ 42 删掉右栏 Packaging 行
+ 84 两条 shelf-life 行改读池值（42 + 42）
+ 4  池本身（inc/formula-pools.php 的新增）
= 314
```

### 3.2 coverage 决定性条目（节选）

```
absent  >Choose one or more<                                  want=0    got=0
absent  months shelf life</dd>                               want=0    got=0
absent  <dt class="sf-fdetail2__term">Packaging</dt>         want=0    got=0
absent  data-sf-config-custom-for="pricing"                  want=0    got=0   ← 价格不给 Custom
present ?ver=2.10.74                                          want=75   got=75
present config.js?ver=1.4.0                                   want=42   got=42
present data-sf-config-custom="1"                             want=108  got=108
counted type="checkbox"       [base,cand] = [74, 0]                      ← 旧多选清零
counted type="radio"          [base,cand] = [398, 536]
counted value="custom"        [base,cand] = [44, 44]                     ← 不增不减
counted value="Custom"        [base,cand] = [0, 64]
counted sf-fdetail-config__group  [110, 110]                             ← 组数不变（只换控件）
counted sf-fdetail-config__opt    [582, 646]
counted sf-fdetail2__value">18 months</dd>   [0, 14]                     ← 去冗余生效
counted sf-fdetail2__value">24 months</dd>   [0, 28]
```

> **`applied` 为什么在这个模式里是 314**：`insert` 方向下 `applied` 数的是 **transform 产出的编辑数**，不是"页面数"。所以每一条都能对着代码逐项加起来（见 3.1），而不是一句"看起来对"。

### 3.3 invariants 里最关键的几条

```
a Custom box for every group that can be typed in            bad_pages = 0
the Custom pick ends the row it belongs to, its box after it bad_pages = 0
the column still ends on its inquiry button, after the list  bad_pages = 0
h2 delta                                                     moved_pages = 0
json-ld deep equal                                           bad = []
the parameter column / ...and every group it holds           42 / 42
...and the ladder is still on no page it was not on          2 / 2
```
另有 `corroborated`（**箱子数由基线独立数一遍**，不是从声明抄）与两条 `order`（新 `Custom` 在组内最后、其箱在线之后）。

### 3.4 破坏矩阵 11/11（全部被捕获）

```
the tokens are not folded              → differing pages = 75, applied = 314/314
the pick is left off every group       → 42
...and the box is left off with it     → 42
the group the visitor types into is skipped instead → caught
pack size keeps its checkboxes         → caught
the hint goes on promising more than one → caught
the Packaging row is left in the list  → caught
the shelf life goes on repeating its own name → caught
the record keeps the spec value instead of its pool value → 2
the run count is declared one short    → 报 314/313
nothing is applied at all              → caught
```

> `the record keeps the spec value…` 只红 **2 页**——因为全站只有**一条记录**（post 158）同时有池值和非冗余的 specs 串。**"只红 2 页"是设计，不是松懈**：矩阵要证明的是"这条 mutant 能被看见"，不是"红得够多"。

### 3.5 负对照逼出的一个**真缺口**（本批最有价值的一节）

矩阵与 NC 全绿之后，`NC-src the source pass fails when the parameter row reads the spec string again` **不响**。
根因：**源码段当时只断言了"包装函数存在"，没断言 `functions.php` 真的调用了新读取器**——也就是说，把 `functions.php` 改回去读 `$parts['shelf']`，源码段照样过。
**修法是补断言，不是放宽**：新增两条 `php` 正断言（参数行调 `sf_formula_shelf_life_line()`、规格表调同一条读取器）＋ 一条 `php_live` 反断言（两处都**不再**读 `$rows['Shelf life'] = esc_html(isset($parts['shelf'])…)`）。

`nc_page` 第三条也 FAIL 过一次：那个 mutant 改的是**记录的打印值**，而 `invariants` 里**没有任何子句阅读打印值** ⇒ 它当然响不了。
**没有硬凑**：删掉该条，并在两处写清"记录的打印值由**主证 ＋ 覆盖对**拥有，其 control 是矩阵 mutant `pool=False`（2 页红）"，另换一条真能响的（`boxFor` 改名）。

### 3.6 声明把新标签写死成 radio（同类错，已修）

`suitable_for` / `species` 组在 `functions.php` 里是 `'type' => 'multi', 'style' => 'chips'` ⇒ **它的 Custom 是 checkbox**，不是 radio。声明原本写死 radio。改成**从该组自身字节推 `kind`**，并补两条 species 的 source 断言（渲染层 0/21，摸不到）。

---

## 四、E2E（`tools/b2d_h8a_e2e.py`）

**预检（2.10.74）47/47 全绿**；**`--live`（2.10.73）19/46**，27 条红**全部落在本批五项**上——这正是"改动确实还没上线"的证据。

### 4.1 三条决定性证据（用户级）

```
待办27 the typed answer is what the submission carries, marked as custom
       {"pricing":"100-999","weight":"5 g chew (custom)"}          ← 打字的带标记，选的没有
待办23 ...and it really stays at 100px while the page scrolls
       {"scrollY": 639, "target": 639, "mediaTop": 100}            ← 滚了 639px，主图仍在 100
待办28 the fold rule is the script's, phone-only, and it hides the tail
       {"media": "(max-width: 480px)", "sel": "...nth-child(n+5)", "body": "display: none;"}
```

配套覆盖：1440 / 375 / 768 三档 ＋ 表单页（`/products/soft-chews/`，该页不 enqueue config.js，所以 `served()` 传 `with_config=False`）＋ **中文孪生页**（`/zh/formulas/joint-support-soft-chews/`）。

### 4.2 本批 E2E 写错的四处判据（全部重构，未放宽）

1. **`pickText` 读 `__text`，但 shape/container 用的是 `__empty-label`** ⇒ 改 `pickWords` 两处都读；
2. **`boxAfterRow`（前兄弟是 `__options`）在 rail 包住行之后为 false** ⇒ 改 `boxIsLast` ＋ `rowBeforeBox`（用 `compareDocumentPosition & 4` 判断文档序，不依赖兄弟关系）；
3. **箭头期望 `inline-flex`，绝对定位实际 `flex`** ⇒ 改读 rect 尺寸；
4. **`FOLD_RULE` 探针因 CSS Nesting 返回空** ⇒ CSSOM 里**每条** style rule 的 `r.cssRules` 都是 truthy 空对象，递归必须 keyed on `r.media !== undefined`（否则每一层都进不去/都进去，都拿不到 `@media` 的 `conditionText`）。

另外两处**测试自身的顺序错**：
- **折回只需一次点击**（编辑时误留两对 `click`，偶数次把列表又展开）；
- **pricing 的 `folded` class 在桌面也在**（`config.js` 无条件加，规则只作用 ≤480）⇒ 桌面判据改为"全组可见 ＋ fold 按钮 `display:none`"；
- **手机横滑检查必须移到展开之后**（折叠时 shape 组 `display:none`，量到 0 宽）。

最后一处**会话错**：首轮整轮打到 live `2.10.73`（`run()` 漏调 `session(live)`）。顺带查清 **`agent-browser open <url>` 会清掉自定义头**（症状 `net::ERR_INVALID_AUTH_CREDENTIALS` ＋ 后续回落 live）⇒ 每段必须在 `open` **之后**再 `set headers`。

---

## 五、帧（`docs/batchH8a-shots/`，14 张，**0 flat**）

| # | 帧 | 状态 |
|---|---|---|
| 01 / 02 | `column-1440` | before / after |
| 13 / 12 | `params-1440` | before / after |
| 03 / 04 | `shape-1440` | before / after |
| 10 / 11 | `sticky-1440` | before / after |
| 05 / 06 | `fold-375` | before / after |
| 07 / 08 | `shape-375` | before / after |
| 09 | `custom-typed-1440` | only-after |
| 14 | `formcell-1440` | only-after |

**sticky 的对帧必须用视口捕获**：全页捕获会把 sticky 元素画在"未吸住"的位置。日志留下决定性证据 ——
**before `media top = -441.2 px`；after `media top = 100.0 px`**。
`_save()` 逐张查颜色数（**distinct > 8 才算非平帧**，`尺寸对 ≠ 内容对`）。

---

## 六、待办 & 约束遵守情况

- ✅ 不引入 ACF / JS 库 / CSS 框架；
- ✅ 不碰 post meta（两条数据事实只报告，见 §0.3）；
- ✅ 先扫描 → 停下征询 → 实施（四条裁决见 §0.2）；
- ✅ 本批 commit + push；
- ✅ **未 pull 到 dev**（等用户单独授权）；**生产站零改动**。

**下一批（自动进入）**：批 2＝待办24「Shape/Container 按剂型差异化」——按用户原话，先扫描现状、报告后停下、等确认再实施。
