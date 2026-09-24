# 批 3b 收尾 + Flavor 双 Custom — 只读扫描报告

日期：2026-09-24　范围：只读（GET dev、读模板/主题源、读 dev 库的 meta 只读查询）。**未改一行代码、未写一个字节、未碰 post meta、未碰生产站。**

三件事的结论，先给最要紧的：

| # | 事项 | 结论 |
|---|---|---|
| 1a | C1 与 What We Handle 重复 | **属实**：C1 的 4 条与 `R&D & Formulation` 栏**前 4 条逐字相同**（同页、相隔一带）。3 个改法，建议 F3 |
| 1b | Quality 页改 3 列 | 机制就绪、可**纯 CSS**；但你给的数字里 **2 个与实测不符**（3 步→实为 **6 步**；600px→实测下限 **705px**） |
| 2 | Flavor 双 Custom | **根因确定，不是数据脏**：池里本来就带 `Custom`，渲染器又追加了一次。影响面**仅 post 158**；EN/ZH 两站同现 |

---

## 1. 任务 1a — C1 与 What We Handle 的重复

### 证据（模板源逐行比对）

| C1 `Custom Formulation Capability`（L203–209） | What We Handle → `R&D & Formulation`（L153–159） |
|---|---|
| `Custom formula development` | `Custom formula development` ← **同** |
| `Custom active ingredient levels` | `Custom active ingredient levels` ← **同** |
| `Palatability testing` | `Palatability testing` ← **同** |
| `Stability testing` | `Stability testing` ← **同** |
| — | `Packaging compatibility testing` |

两处都是 `ul.sf-checklist.sf-checklist--panel`。C1 已有的引导句（`From concept to a validated recipe — developed, sampled, and shelf-life tested in our own lab before a single unit is produced.`）已经把你要的那句宏观摘要写掉了 ⇒ 直接删列表会让这一带只剩 **h2＋一句话＋两个按钮**，偏薄。

### 三个改法

| 方案 | 做法 | 代价 |
|---|---|---|
| **F1** | 删掉 4 条列表，只留 h2＋宏观句＋2 个按钮 | 这一带变薄；与上一带「三栏清单」的视觉语言断开 |
| **F2** | 只留 **2 条**不重复的 + 链接 | 与 `Packaging compatibility testing` 仍有语义邻接 |
| **F3（建议）** | 保留列表形态，但把 4 条改成**「定制开发路径」**（另一视角，不是能力清单）：`Brief & reference match` / `Prototype sample round` / `Palatability & stability trials` / `Scale-up & packaging validation` | 动 4 行文案 |

F3 的好处：上一带讲「谁负责什么」（团队视角），C1 讲「你把想法交给我们之后会发生什么」（**流程视角**）⇒ 既不重复，也补上总览页原本没有的「定制怎么走」；且不动标题、不动按钮、不动底色。

---

## 2. 任务 1b — Quality 页 3 列卡片

### 2.1 现状实测（before，dev `2.10.76`，非推算）

| 视口 | 区块高 | 每行步数 | grid 列 | 图片盒 |
|---|---|---|---|---|
| 1440 / 1280 | **1800 px** | 1 | `620px 350px` | 350×263 |
| 1024 | **1800 px** | 1 | `554px 350px` | 350×263 |
| 375 | 2489 px | 1 | 299px | 299×224 |

你说的「1800–2000px」**精确命中**。另两条规格**现状已满足、无需改**：图比例实测 `1.333 = 4:3`；数字实测 **64px `rgb(90,183,53)`**（品牌绿）。

### 2.2 与你的描述不符的 3 处

| 你的描述 | 实测 |
|---|---|
| 「**3 步**各占一整行」 | **6 步**：01 Raw Material Inspection／02 Batching & Weighing／03 In-Process QC／04 Finished Product Testing／05 COA Issuance／06 Retention Sampling ⇒ 3 列必然 **2 行** |
| 「高度约 **600px（省 70%）**」 | 忠实实现（4:3 图＋数字在上＋全文案）实测 **861px（−52%）** |
| 「图片约 **50%**」 | 图固定 350px／文字 620px ⇒ 占 **34.5%** |

### 2.3 600px 需要放弃什么（**两个方案都是实测，不是算式**）

用 `tools/b3b_qs_measure.py --simulate --sim-overlay` 在真页注入 CSS 量的：

| 方案 | 1440 | 1024 | 相对 1800 |
|---|---|---|---|
| **A 忠实**（4:3 图＋数字在文字上方＋完整描述） | **861px** | 828px | **−52%** |
| **B 数字叠在图上**（其余不变） | **705px** | 672px | **−61%** |
| **600px** | — | — | **达不到**：单卡须 ≤286，而 4:3 图已占 239 ⇒ 文字只剩 47px（标题 30＋一段 51 装不下） |

⇒ 600px（−67%）要**再放弃一条**：把每段描述砍成**单行**（约 −105px），或把图改 3:2。两条都与你写的「4:3」「保留原文」直接冲突。**B 已经吃掉「数字在文字上方」这一条**（数字仍 64px、仍可保持品牌绿，只是落在图上、需要白描边保可读性）。

### 2.4 可复用的 3 列样式：**没有可直接套用的**

| 类 | 实情 |
|---|---|
| `sf-panel--3` | **在用**（5 个服务页的 Key Facts），但是 `gap:0 + hairline`，源码注释明说「reads as one table rather than as N cards」——**语义相反** |
| `sf-eq` | **同页**（Quality、Factory Tour）的 3 列图库，视觉最接近，但挂在 `wp:gallery` 上 |
| `sf-triple` | **零引用**（死样式） |

⇒ 建议**纯 CSS 改 `.sf-qs`**，模板一行不动。DOM 已经是 `div.sf-qs > article.sf-qs__step > (div.sf-qs__text + figure.sf-qs__media)`，`display:grid; grid-template-columns:repeat(3,minmax(0,1fr))` ＋ 每卡 `flex-direction:column-reverse` 即可把图提到文字上方（**DOM 顺序不变**，读屏顺序仍是「数字→标题→描述→图」）。要点三处：① 现有 `.sf-qs__step:nth-child(even)` 的**翻转规则必须显式关掉**（它给偶数卡换了轨道，同权重不覆盖不掉）；② `.sf-qs__step + .sf-qs__step` 的 22px 上边距＋hairline 要归零；③ 现有断点 `@media (max-width:900px)` 已把区块折成单列（L5101–5141），**手机 1 列堆叠是现状、不用新写**。

### 2.5 连带：**没有任何门断言需要改**

`/quality/` 在 75 页抓页清单里（`tools/b2d_s3_paths.txt` L5），但 `b2d_h7_gate.py` 的 4 处 quality 引用都不是本区块断言，`sf-qs` 在该门 **0 命中**；h5_0_geom／h6_geom／h5_e2e／s3_fetch／h8c_live_* **全 0 命中**。老 q 系列（`q3_verify.js`／`quality_scan.js`／`q3b_diag.js`／`q4_shots.js`／`q2_patch_quality.py`）确实引用 `sf-qs`，但都是**当年建页的一次性脚本**，且仍在找早已不存在的 `.sf-qs__content` 包裹层 ⇒ 非当前门链，不改。

**版本**：工作区已是 `2.10.77`（批 3b 已提交未 pull）；`dev` 仍服务 `2.10.76`。三件合并一次 pull ⇒ **沿用 `2.10.77`** 即可（若你想让 Quality 单独可回滚，再 bump 到 `2.10.78`）。

**DIFF**：`/quality/` 一页（＋所有页的 `style.css?ver` 令牌）。

---

## 3. 任务 2 — Flavor 出现两个 Custom（根因）

### 3.1 你问的四项，逐条回答

**① post 158 的 `sf_formula_flavors` 实际值**（dev 库只读查询）：

```
["Chicken","Beef","Lamb","Salmon","Peanut Butter","Cheese","Mint","Custom"]
```

⇒ **数组里本身就带 `"Custom"`**（第 8 个元素，编辑者在后台勾的）。

**② 池里 Flavor 的 Custom 配置**：**没有 slug 这回事** —— 池的选项值**就是标签**。`inc/formula-pools.php` 的 `sf_formula_pools()` 里，8 个剂型的 `flavors` 数组**都以字符串 `'Custom'` 结尾**（长度 soft-chews 13／tablets 6／dental-chews 7／pastes 6／powders 6／drops 6／liquids 6／fish-oil 6）。全池 **45 个数组全部以 `Custom` 结尾**，只有 8 个 `label` 映射表不是（它们是 `键=>标签`，不渲染成选项）。

**③ 渲染函数怎么输出 Flavor 选项**：`sinofresh_formula_config_groups()`（`functions.php` L2224–2240）读 meta → 逐条做成选项 → **然后无条件 `$options[] = sf_formula_custom_option();`**。那个合成 Custom 由 L2155 的 `sf_formula_custom_option()` 造：`value='Custom'`、`label='Custom'`、**`custom => true`**。

**④ 为什么两个**：meta 里的 `Custom` 和追加的 `Custom` 是**两个不同的对象、印出同一个词**。线上实测 9 个选项：

```
 1 Chicken  2 Beef  3 Lamb  4 Salmon  5 Peanut Butter  6 Cheese  7 Mint
 8 Custom   ← 来自 meta，无 custom 标记
 9 Custom   ← 追加，带 data-sf-config-custom="1"
```

**源码自己写了正确做法** —— `sf_formula_library_options()`（`inc/formula-pools.php` L255–258）的注释：

> *"Custom" is **MARKED rather than appended**: every pool already ends in it … **Appending a second one would print the word twice.***

池驱动的组（Shape／Container Type）走的就是这条：**标记**池里那个 Custom（`$option['custom'] = true`），**不追加**。记录驱动的 Flavor 组没走这条规矩 —— 这就是全部根因。

### 3.2 截图里「一个已选中」是怎么来的 —— 实测

浏览器实测（1440×900，真实鼠标，整数坐标，命中校验）：

| 芯片 | 点击结果 | 摘要行 |
|---|---|---|
| **#8**（meta 的 Custom） | 勾上了 ✅，**输入框不出现** | `Flavor: Custom` |
| **#9**（追加的 Custom） | 勾上了 ✅，**输入框展开** | `Flavor: Custom` |

- **服务端零预勾选**：整页 `checked` 出现 **0 次**（渲染器与 config.js 都不预勾）。所以「✓ 已选中」是**交互后**的状态，不是页面到达时的样子。
- 真正的缺陷不是「多印一个词」，而是 **#8 是空壳选项**：访客点了它，**输入框永不出现**，只能以「自定义」四个字成交（销售收到 `Flavor: Custom`，却不知道客人想要什么口味）；而且它和 #9 同组同名同值，**点它会抢走 #9 的勾**。
- EN 与 ZH 两站同一页都复现（9 选项、2 个 Custom）。

### 3.3 影响面（DB 实证）

`sf_formula_flavors`／`sf_formula_species`／`sf_formula_packaging_extra` 中含 `Custom` 的记录：

```
post 158  sf_formula_flavors        [...,"Custom"]      ← 唯一造成双芯片的
post 158  sf_formula_packaging_extra [...,"Custom"]      ← 不渲染成配置组（只印内容 chips），无重复
```

⇒ **全站 21 个 formula 页里只有 post 158 一页有此现象。**

### 3.4 修复方案（**代码侧**，不改 meta）

同一个「先标记、没有再追加」的判断，同时套到 5 个记录驱动的组上（Flavor／Piece Weight／Pack Size／Suitable For／Life Stage）——它们**现在是同一个写法，只是今天只有 Flavor 的数据踩到**：

```php
/* 记录里的值可能来自「本来就以 Custom 结尾」的池，所以要先认出来再标记，
   而不是无脑追加 —— 这正是 sf_formula_library_options() 已经写明的规矩。 */
function sinofresh_formula_value_options($values) {
	$out = array(); $has_custom = false;
	foreach ((array) $values as $v) {
		$v = trim((string) $v);
		if ($v === '') { continue; }
		if (0 === strcasecmp($v, 'Custom')) { $out[] = sf_formula_custom_option(); $has_custom = true; continue; }
		$out[] = array('value' => $v, 'label' => $v, 'image' => '', 'note' => '');
	}
	if (!$has_custom) { $out[] = sf_formula_custom_option(); }
	return $out;
}
```

5 处调用点换成它即可；`'meta' => implode(', ', $flavors)` **保持不变**（那行是记录自己的规格文本，`…, Custom` 是编辑者真选过的值，应当保留）。

**数据侧备注（不代做）**：若你更愿意从数据上根治，就删掉 post 158 `sf_formula_flavors` 里的 `"Custom"` 一项（1 个值）——但**同一页还有第二条**依赖：`sf_formula_shape` = `Custom`（也是编辑者选的），那条**不**造成重复（池驱动组是标记式的），所以只有 flavors 这一项需要动。按你的约束我不碰 meta。

**改动后 DIFF**：只剩 `/formulas/joint-support-soft-chews/`（该页 flavor 组 9→8 芯片）；其他 20 页**不产出一个字节变化**（它们的列表里没有 Custom，helper 走的是同一分支）。

---

## 4. 合并实施计划（等确认后才动）

| # | 改动 | 文件 | 形态 |
|---|---|---|---|
| 1a | C1 的 4 条文案（F3） | `templates/page-services.html` | 改 4 行 |
| 1b | `.sf-qs` 改 3 列（方案 A 或 B） | `style.css` | 纯 CSS，约 30 行，含显式关掉偶数卡翻转 |
| 2 | Flavor 去重 helper ＋ 5 处调用 | `functions.php` | 约 20 行 |
| 连带 | 版本（沿用 2.10.77）＋ 报告 | `style.css`/`functions.php`/`docs/` | — |

**核验台阶**（按你写的执行顺序）：本地语法与断言自检 → `install <SHA>` 到**预检层** → 截图 **1024／1280／1440**（Quality 3 列、/services/ 两带、**页脚 5 栏挤压**，以及 158 的 flavor 组）→ 报告 → **停下等确认 pull**。dev 的 live 层与生产站在本阶段**零改动**。

---

## 5. 待你裁决

| # | 问题 | 我的建议 |
|---|---|---|
| **P1** | C1 用 F1／F2／**F3**？ | **F3**（改 4 行文案，转成「定制开发路径」视角） |
| **P2** | Quality 3 列：**A 忠实（861px）** 还是 **B 数字叠图上（705px）**？ | **A**：B 会把 64px 大数字落在照片上，与「大号绿色数字」的可读性冲突；省下的 156px 换不来这个代价 |
| **P3** | 600px 死线要保吗？（要保 ⇒ 必须砍成单行描述） | 不保。**861 或 705 二选一** |
| **P4** | Flavor 修复：**代码侧（helper）** 还是**数据侧（删 meta 里那 1 个值）**，还是两者都做？ | **代码侧**：数据侧只治 158 一页，代码侧同时封掉另外 4 个组将来会踩的同一个坑 |
| **P5** | 版本：沿用 **2.10.77**（合并一次 pull）还是 Quality 单独 bump **2.10.78**？ | 沿用 2.10.77 |
| **P6** | 1b 的 `.sf-qs` 改完，是否**一并复核**同页 `.sf-eq` 图库与 `sf-pal` 流条（它们在同一带群里，视觉上应当仍然连续）？ | 一并截图复核，不做改动 |

---

## 6. 证据与工具

- **本次新建**：`tools/b3b_flavor_probe.py` — Flavor 组探针（只读；读选项/标记/预勾选/输入框，真实鼠标点两个 Custom 并报各自结果）。用法：`--path` 换页、`--viewport WxH`。
- **本次扩展**：`tools/b3b_qs_measure.py` 加 `--sim-overlay`（量「数字叠图上」变体）。
- **原始数据**：`/tmp/flavor-probe.json`、`/tmp/qs-recheck.json`（before＋A 变体）、`/tmp/qs-overlay.json`（B 变体）。
- 三处自查并更正的方法问题（记下来避免重犯）：① 探针首次用「`scrollIntoView` 后同 tick 读坐标」⇒ 滚动未稳时坐标/命中校验都落在动画中间，一度误报「芯片被悬浮层盖住」（第 8 芯片在 1280×577 的矮窗口下**确实**会被展开的悬浮层压住 3/9 个采样点，但那是视口高度问题，不是本 bug）；② 图样式组的标签落在 `__empty-label` 而非 `__text`，用 `__text` 统计会把 Shape 的 Custom 数错算成 0；③ 本报告所有计数一律 `grep -E` 口径（BSD grep 的 `\|` 交替静默返回空）。
