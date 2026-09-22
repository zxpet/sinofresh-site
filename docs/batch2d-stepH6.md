# 批次 H6 —— 收尾批：H2b2 留下的死代码，与那份没人读的载荷

**提交**：`9de31e5`（父提交 `6819d26`＝H6 Step 0 扫描档）｜**令牌** `2.10.60 → 2.10.61`（两处同步）
｜**Step 6（`git pull` 上线）按用户 2026-09-22 指令跳过** —— 本批只交候选。

**基线**：`084b246`（H5-0 修复）的预检副本；**本批不改数据、不动业务字段、不扩范围**。

---

## 0. 本批是什么形状（决定了门长什么样）

H2b2 删掉了 `configurator.js` / `configurator.css`，但把它的**对侧**留在了站点上：一份每页下发的 JSON、
一个写进 `sessionStorage` 却没人读的键、一个找不到目标的 `scrollIntoView` 分支、一条只服务配置器的 CSS 规则，
以及三个更早批次（H1 / 批 E / H2a）遗留的类家族。这些都不会报错，也不会有人来报 bug。

所以 H6 不是"H5 的下一批"，它是**形状完全不同的一批**：

| | H2b2 | H5 | **H6** |
|---|---|---|---|
| 改动性质 | 纯删除 | 纯新增 | **纯删除 ＋ 一处令牌** |
| 主证明 | `undo_declared(cand) == base` | 从候选里**只删**新块后逐字节 | **`cand == fold(base) − 声明载荷`** |
| 新增的第 4 条判据 | — | 掩码哈希 | **遮蔽读回**（掩码抹掉的东西单独再查一遍） |

H6 的形状比两者都锋利：**删掉的东西在候选上必须出现 0 次**，而**没声明的东西一个字节都不许动**。
于是判据是四条，缺一条都能被"看起来全绿"骗过去：

1. **字节证明** —— 折叠两个令牌、剥掉声明的载荷、掩掉 CF/GF 的每请求噪声后，逐页逐字节相等；
2. **覆盖断言** —— 声明的旧裸串在**候选**上计数必须为 0（负向前瞻，不是在基线上算）；
3. **不变式** —— 与声明无关的计数（logo alt 总数、每页计数集合）两侧相同；
4. **遮蔽读回** —— 被掩码抹掉的字节区间**再单独解出来**比一次，否则掩码就是个可以把改动藏起来的黑洞。

---

## 1. 用户六条裁决（2026-09-22 定论）

| 项 | 裁决 | 本批动作 |
|---|---|---|
| 起订量（第 4＋12 项） | **保持现状**（各剂型不同值是事实） | **只出对账表，不改任何值**（见 §7） |
| `material`（第 14 项） | **不做**，登记未来批 | 无 |
| `WebSite`（第 15 项） | **不做**，登记未来批 | 无 |
| `sales@zxpet.com`（第 10 项） | **已完成（H4e）** | 无 |
| 询盘弹窗复位（第 11 项） | **不复原**（H4 新建） | 无 |
| `sf_formula_shelf_life`（第 9 项） | **保留**（未来可能用） | 无 |

**原则**：只做清理（旧 CSS / PHP / JS），不扩范围、不改数据、不动业务字段。

---

## 2. 实际执行的七项（声明清单）

**本批的真实改动面（`git diff --numstat 6819d26 9de31e5` ——已排除 H5 / 文档 / 工具）：**

| 文件 | 增 / 删 | 净行 | 内容 |
|---|---|---|---|
| `assets/js/formulas.js` | +23 / −44 | **−21**（116→95） | 死写 ＋ 死分支 ＋ `reduceMotion` |
| `functions.php` | +52 / −175 | **−123**（5,921→5,798） | 孤儿渲染器 117 行 ＋ 载荷构建 ＋ 注释订正 |
| `style.css` | +18 / −286 | **−268**（9,540→9,272） | 48 条死选择器 / 36 个规则块 |
| **主题树合计** | **+93 / −505** | | **零新增 CSS、零新增 JS** |

### 2.1 死 CSS：48 条选择器（`style.css`）

| 家族 | 选择器 | 处置 |
|---|---|---|
| `.sf-facts__*`（H1 遗留） | 14 | 删 |
| `.sf-spectable__*`（批 E 遗留） | 23 | 删 |
| `.sf-fdetail-media__*`（H2a 遗留） | 13 | 删 |
| `.configurator__summary-value`（H2b2 遗留） | 1 | 删 |

**300,185 → 291,209 B（**−8,976 ＝ −8.77 KB**）**，9,540 → 9,272 行；工具实测：
**48 条死选择器 / 36 个规则块**，另 1 个 `@media` 空壳清除、1 条**部分规则保留**（见下）。

> 数值出处：字节/行数取 `git show <rev>:sinofresh-theme/style.css` 的 blob 长度；
> 选择器与规则块计数取 `tools/b2d_h6_css_prune.py` 在**基线版样式表**上的扫描输出
> （`dead selectors to cut: 48  (rule blocks removed: 36)`）。
> ⚠️ 早前笔记里的 `299,679 → 290,552（−9,127）` 是**错的**，已按上表更正。
> ⛔ **但产品提交 `9de31e5` 的信息里仍写着 `9,127 B`** —— 该提交已 push，不改写历史。
> ⇒ 本轮 closure 提交在信息里**显式记明这处更正**；**以本档 ＋ 本档引用的 blob 长度为准确值**。
> 教训：**提交信息里不要写需要"再算一次"才成立的下游数字** —— 数字要写就写**从对象里直接取到的**那一个
> （blob 长度），否则它会作为永久产物把错值固定下来。

两种情形**不能整块删**，逐条核过：

- **携带选择器列表的规则**：`.sf-facts__row, .sf-num { font-variant-numeric: tabular-nums; }`
  只有一半是死的 ⇒ **删选择器文本、留规则本体**（现为 `.wp-block-table table, .sf-num { … }`）。
- **只出现在注释里的类名**：先做**长度保持地剥注释**再判定，否则注释会让死类名读成活引用。

工具 `tools/b2d_h6_css_prune.py`：按逗号拆成单选择器后判 whole / partial / untouched，**不用 sed**
（规则可携带列表，规则里也可能有注释）。

### 2.2 孤儿短码渲染器（`functions.php`）

`sf_formula_actives` 注册于 `functions.php:1494`、渲染器在 `:1408`，**全站调用点 0**（8 个剂型模板里的调用点随 H2b1 消失）。

⛔ **但它不能整块删** —— 活着的 `sf_formula_detail_actives()` 依赖它的**两个解析助手**
（`sinofresh_formula_split_top_level()` / `sinofresh_formula_analysis_pairs()`）与 `.sf-actives__*` 三组样式：

```
⇒ 删：注册行 ＋ 渲染函数体 ＋ 文档块（基线文件里占 L1378–L1494，共 117 行；
      用带断言的脚本删，断言边界后写盘）
⇒ 留：两个解析助手（定义各 1 次、被调用 2/1 次）＋ .sf-actives__* 全部样式
```

这条边界做成了**具名负对照 N4/N5**：「把 `split_top_level` 一起删掉」与「把 `.sf-actives__*` 样式一起删掉」
**都必须 FAIL** —— 否则"我删的是孤儿"这句话没有任何东西在检查。

### 2.3 死写 ＋ 死分支（`formulas.js`，1.1.0 → 1.2.0）

```js
sessionStorage.setItem('sinofresh_formula_' + slug, name)   // 写侧在、读侧 0（读者随 H2b2 消失）
document.getElementById('configurator')                      // 渲染页 id="configurator" 0/75 ⇒ 分支永不进
var reduceMotion = …                                          // 唯一读者是上面那个滚动
```

删这三处后 `formulas.js` 95 行。**K1 契约不变**：按钮仍 `class="sf-formula__cta" + data-formula`，
点击仍把配方名写进剪贴板。`data-form` 属性**留在标记上**（本批声明范围是死代码，不是属性）。

### 2.4 死载荷：60 页 × 1,197 B（`functions.php`）

`<script type="application/json" class="sf-formulas-data">` 由 `sf_formula_grid` 输出，
**唯一读者是已删除的 `configurator.js:readFormula()`**。

| | 值 |
|---|---|
| 出现的页 | **60/75**（21 详情 × 2 语言 ＋ 8 剂型 × 2 ＋ `/formulas/` ＋ `/zh/formulas/` 等） |
| JSON 体积 | **71,832 B**（扫描档记 72,720 B，**实测更正**），平均 **1,197 B/页** |
| 候选态残留 | **0 页**（60 → 0，`grep -rl` 实测） |

随之删掉的还有 `$payload` 的整块构建、`if ($json === '')` 的一半守卫，
以及 `$ingredients` / `$analysis` 两个**只为载荷而抓取**的 meta 读取 —— 现在只抓 `sf_formula_specs`。

### 2.5 4 处失真注释 ＋ 2 处助手文档块

`gallery` 的 "emits K2"、`detail` 的 "`.sf-formulas-data` payload"、`detail_actives` 的 "K2 mirror"
与 "Parsing is [sf_formula_actives]' own two helpers" —— 全部改成与代码一致的事实。
两个助手的 docblock 各加一句："Written for the `[sf_formula_actives]` band, which batch H6 retired。"

---

## 3. 门（`tools/b2d_h6_confine.py`）

### 3.1 四条判据

```
== main proof: candidate == fold(baseline) minus the declared payload ==
  pages                : 75  (0 mismatched/missing)
  folded style token   : 75 pages
  folded js token      : 60 pages
  payload removed      : 60 element(s) on 60 page(s), 71832 JSON bytes
  payload parsed ok    : 60/60
  ld+json blocks       : 376 -> 376
  masks (count/pages)  : cf_email_attr=155/75, cf_email_link=226/75, gf_config_nonce=23/23,
                         gf_currency_value=23/23, gf_phone_id=8/2, gf_state_blob=23/23,
                         gf_unique_id_value=23/23, inline_nonce=54/45,
                         preflight_theme_dir=1225/75, url_nonce=75/75
  PASS  confined change: 75/75 pages equal after the declared edit
== coverage ==              PASS  (3 declared old strings, 0 occurrences each)
== invariants ==            PASS  (0 pages with a changing count; logo alt 150/150)
== masked-blob read-back == PASS  (23 pages, 0 differ; 46 masked currency values are NOT text)
```

**掩码是逐条实测出来的，不是抄来的**：裸字节比对首跑 **75/75 全 DIFF**（长度却全同）——
Cloudflare 的邮件混淆每请求重编。用 `sf_masked_cmp.py` 先确认 A/A 通过，再为本批自带一套掩码。
其中两条**刻意排除**了通用兜底 blob 掩码（`[A-Za-z0-9+/=]{16,}` 与 `[A-Za-z0-9+/]{40,}`）：
本批是删除证明，**能抹掉 40 字符 base64 的掩码也能把真实内容改动一起抹掉**。

### 3.2 GF 状态块：不能靠 base64 子串找

`/contact/` 等 23 页有 Gravity Forms 的 612 字符 `state_timestamp` 状态块。它**不能**用 base64 子串定位 ——
该块编码的是**带转义引号**的 `\"state_timestamp\"`，字节不对齐 ⇒ 子串搜索实测命中 **0/11**。
也不能用兜底 blob 掩码：同形 run 在 `/contact/` 上有 11 条，其中 **8 条解码后是内联 SVG path（真实内容）**。

⇒ 判据改成**解码后判定**（`GF_BLOB_MIN=200` 且解出 `state_timestamp` 才掩），
并加第 4 条判据把它单独读回（见 3.4）。

### 3.3 破环矩阵：11/11，且**报"空转"**

| 例 | 破坏 | 捕获 |
|---|---|---|
| M1/M2 | 还原一页 / 全部页的 style 令牌 | 字节证明 FAIL ＋ 覆盖 FAIL |
| M3 | 还原 js 令牌 | 同上 |
| M4/M5 | 还原一页 / 全部页的载荷 | 同上 |
| M6 | `</body>` 前插一句注释 | 字节 FAIL（覆盖 PASS） |
| M7 | 删掉一个 ItemList 块 | 字节 FAIL ＋ 不变式 FAIL |
| M8 | 给原本没有的页面注入载荷 | 字节 FAIL ＋ 覆盖 FAIL（"意外多出"也抓） |
| M9 | 候选 ＝ 基线（什么都没改） | 字节 FAIL |
| M10 | 改一个可见字符 | 字节 FAIL |
| M11 | 改**掩码 blob 内部**的内容 | 字节 PASS、**读回 FAIL** ← 证明第 4 条判据不是摆设 |

**builder 一律返回改动量，为 0 判 INVALID** —— 首版 M6 用的是 `_typo` 靶串，该串在页面上根本不存在，
破坏是空转却"被捕获"了：这是假捕获，比漏捕获更危险。

### 3.4 具名负对照 7/7 ＋ 源码不变式 32 项

```
N1 base vs base 必须 FAIL 字节证明          N2 覆盖门 PASS 而字节门 FAIL（证明两门不同向）
N3 还原全部载荷 ⇒ 覆盖与字节双 FAIL          N4 删掉 split_top_level ⇒ 源码门 FAIL
N5 删掉 .sf-actives__* 样式 ⇒ 源码门 FAIL    N6 style.css 令牌未 bump ⇒ 源码门 FAIL
N7 掩码 blob 内部被改：字节门 PASS、读回 FAIL（＝ M11 的独立复现）
```

源码侧 32 项：助手定义恰 1 次、死串归零（3 个）、死 CSS token 归零（4 个）、
活规则存活（`.sf-num` / `.sf-facts-mini*` / `.sf-actives__*` 共 10 项 / `.sf-spectable {`）、
两个新令牌就位、`formulas.js` 代码区四串归零（`sessionStorage` / `getElementById` / `scrollIntoView` / `getAttribute('data-form')`）。

### 3.5 合成候选（门可信度的最后一环）

把声明的改动**施加到基线**上合成一份候选，跑完整套 → 全绿。
⇒ 门不是"只能对真候选全绿"，它对**按声明构造的正确候选**也全绿，且对 11 种错误构造都 FAIL。

---

## 4. 几何两态实测（`tools/b2d_h6_geom.py`）

外链样式表是**渲染捕获的盲区**：页面只带 URL ＋ 令牌，删 8.8 KB 对抓取产物不可见。
所以"删掉的 CSS 确实是空操作"必须**在浏览器里量**，不能从字节推。

做法：对所有 `[class]` 元素取**四元盒子 ＋ 52 个 computed 属性**做签名，两态各扫一遍再**逐页比**；
`compare()` 先断言两侧服务的 sheet **不同**、且各等于 `git show <提交>:sinofresh-theme/style.css` 的 sha256
—— 否则"两侧服务了同一份 sheet"会打出完美一致却什么都没证明。

| | 基线态 | 候选态 |
|---|---|---|
| 安装的提交 | **`2017dbe`**（H5 候选） | `9de31e5` |
| 服务端 `style.css` sha256 | `9cc2a7a2…` | `a3207cc9…` |
| 页面视图 | 75 页桌面 1440×900 ＋ 6 页手机 390×844（**抽样，明说它不完整**） | 同 |
| probe 错误 | 0 | 0 |

### 4.1 ⛔ 基线一开始装错了 —— 与字节门不是同一个基线

几何首跑用的是 `084b246`（H5-0 修复）。它**不是** H6 的基线：
H6 的字节门基线是 **H5 候选**（已核实：`_backup/b2d-h6-baselines` 与 `_backup/b2d-h5-candidates`
掩码比对 **75/75 identical**），即 `2017dbe`，两者之间夹着 H5 的**产品提交**。

后果是几何比较**把 H5 的改动也算成了差异**（实测：详情页多出 7 个 `SPAN.sf-fdetail2__chip`
＋ `TABLE.sf-fdetail2__tiers`，正是 H5 的 `offers`／价格阶梯渲染器）。
⇒ 改用**正确的基线 `2017dbe`** 重扫。**教训**："基线＝上一批预检副本"这条铁律，
在**两个门读取的基线不一致**时会静默失效 —— 字节门的基线与几何门的基线必须是**同一个提交**，
这一点要**显式写进每批的检查表**，不能靠"我记得装的是基线"。

### 4.2 ⛔ 并发编辑：扫描进行中有人改了内容（本批实发）

候选态扫描（18:17–18:22）**进行中**，wp-admin 在 **18:21:29** 改了 post 158
（`joint-support-soft-chews` —— 正是唯一有价格阶梯数据的那一页）。
症状极具误导性：**同一个提交**下，EN 1440 少 24 个元素、EN 390 多 24 个元素 ——
看起来完全像"响应式布局被改坏了"，实际是**编辑器在打字**。

证据链：
```
SQL   SELECT ID,post_name,post_modified FROM wp_posts WHERE ID=158
      → joint-support-soft-chews  2026-09-22 18:21:29
范围  近 2 小时仅此一条内容改动（另有一条 auto-draft，只表示有人打开了"新建"页）
数据  wp_postmeta: sf_formula_price_tiers 现 1 行（post 158, [{"qty":"200","price":"2.5"}]）
后果  H6 的两侧捕获均早于 18:21:29 ⇒ 都没有 offers；而"现在"渲染同一提交会出现 offers
```

⇒ **新增「静默守卫」（`content_fingerprint()`）**：扫描**前后各取一次**内容指纹
（REST API 的 `id,modified`，分页取全），不同即 **FAIL**。

⚠️ **落档时对这条守卫的描述作了更正**（原文写"不依赖任何凭据"，是错的）：

- `content_fingerprint()` 走 `curl -u <dev Basic Auth>` —— **它要凭据**，只是**不读 DB**。
- "不可被静默关闭"的**真正依据**是它**读不到就中止整轮**：
  `if rc != 0 or not out.startswith('['): raise SystemExit(...)`。
- ⇒ 把理由写成"凭据无关"很危险：那等于给门留了"401 时静默继续"的口子。
  本项目已经踩过一次同型坑（**不带凭据 ⇒ curl 拿到 401 页 ⇒ 两侧哈希同一个错误页 ⇒ 静默全绿**，见 `RULES §Q`）。
  **写对理由比写对结论更重要** —— 理由写错，下一个照理由复用的人就会复现这个坑。

**18:21:29 那次编辑改了什么（本轮补测）**：除价格阶梯外，还给 post 158 加了两段**测试占位文本**
（`Recommended For` → `testsadasdfasf`、`Use Cases` → `sdasdasdasad`），**EN 与 zh 两侧都出现**。
它**不在** H6 声明内，按裁决**不动数据**；已登记进 §8。
⇒ 后果是**截图（18:44）比字节门的捕获（约 17 时）内容更新**：帧上能看到这两段占位文本。
**站点自 18:21:29 起未再变动**（本轮 18:45 连测两次指纹均为 `f6e7e15d1f`，与 18:33/18:38 记录一致，
且 `post 158 modified` 仍为 `2026-09-22T18:21:29`），所以这不是"截图期间还在被人编辑"。

### 4.3 ⛔ 先测噪声，再测差异（A/A 是权威）

首跑 191 处差异。**不解释差异，先做 A/A**（同一份安装扫两遍）：凡 A/A 就不同的，**按定义是噪声**。
实测三类噪声，每一类都是**先被 A/A 抓出来、再针对性处理**，而不是靠猜：

| 噪声 | A/A 实测 | 处理 |
|---|---|---|
| **动画相位** | `/about/` 两个 `div` 的 `opacity`/`transform` 两次不同、**盒子全等** | 采样前**冻结**（`transition/animation:none!important` ＋ `scrollTo(0,0)` ＋ 强制回流），两侧同一覆盖 |
| **每请求 id** | `country-item-sx-6ab2509a215d6` → `…6ab253bb94fad`，且**同一哈希还在另两个 id 上** | 规则化：**id 内 ≥8 位十六进制连串 = 生成令牌** → `<H>`，并**列出被改写的全部 id** |
| **滑块进度条** | `.sf-slider-progress__bar` 宽度 290/292、293/298、96/105 —— 连续三次都不同 | 只掩**它的盒子与 `transform`**，其余属性照比（CSS 冻结拦不住：是 JS 每帧写内联样式） |

⇒ 处理完后 A/A **10 个页面视图 0 差异**，才去跑真两态。
**没有 A/A 的"0 差异"不可信；A/A 不通过的"有差异"也不可信。**

### 4.4 比较器自身的负对照（8 条，两个方向）

过滤与掩码是**最能把门变成橡皮章**的东西，所以每一条都双向验证：

```
NC1 候选仍带一个载荷元素        → 必须 FAIL（覆盖断言没被过滤吃掉）
NC2 候选侧少一个元素            → 必须 FAIL
NC3 一个盒子位移 3px            → 必须 FAIL
NC4 一个 computed 属性变了      → 必须 FAIL
NC5 被掩 id 换一个哈希          → 必须 PASS（这正是掩码的职责）
NC6 不含十六进制连串的 id 被改名 → 必须 FAIL（掩码是规则，不是"凡 id 都放过"）
NC7 原样不动                    → 必须 PASS
NC8 滑块条的 backgroundColor 变了 → 必须 FAIL（它只被豁免盒子与 transform，不是整块豁免）
```

### 4.5 结果

```
  baseline sheets: ['9cc2a7a2a49b']
  candidate sheets: ['a3207cc9129b']
  baseline: git+sha256 style.css 9cc2a7a2a49b (served ['9cc2a7a2a49b'])
  candidate: git+sha256 style.css a3207cc9129b (served ['a3207cc9129b'])
  elements compared: 32861 across 81 page-views
  declared deletion applied: 65 element(s) on 65 page(s), stripped from the baseline only (candidate residuals would FAIL)
  per-request ids masked: 984 occurrence(s), 984 distinct: ['country-item-ac-6ab2588a37831', 'country-item-ac-6ab2589079ea2', 'country-item-ac-6ab259b48127e', 'country-item-ac-6ab259bab4a07', 'country-item-ad-6ab2588a37831', 'country-item-ad-6ab2589079ea2']
  volatile elements (box + transform dropped, rest compared): 6 occurrence(s) of ['sf-slider-progress__bar']
  differing elements: 0
  baseline content fingerprint f6e7e15d1f.. -> f6e7e15d1f.. (50 posts)
  candidate content fingerprint f6e7e15d1f.. -> f6e7e15d1f.. (50 posts)
  PASS  geometry/computed-style: 0 differing element(s) over 81 page-views
```

| 项 | 值 |
|---|---|
| 页面视图 | **81**（75 桌面 1440×900 ＋ 6 手机 390×844；**抽样**，明说它不完整） |
| 比较的元素 | 32,861 |
| 声明删除（**只从基线侧剥**） | 65 元素 / 65 页；候选侧残留 **0**（残留即 FAIL） |
| 掩码：每请求 id | 984 处（按**规则**改写，且**逐个列出**） |
| 掩码：滑块条 | 6 处（**只**免盒子与 `transform`，其余 50 个属性照比） |
| probe 错误 | 0 / 0 |
| **差异** | **0** |
| 内容指纹（两侧各取前后两次） | `f6e7e15d1f..` → `f6e7e15d1f..`（50 posts）**不变** |
| 两侧 sheet | **不同**，且各等于 `git show <该侧提交>:sinofresh-theme/style.css` 的 sha256 |
| **判定** | **PASS** |

**A/A（同一份安装扫两遍，10 页面视图）**：5,703 元素，**0 差异**，指纹不变 ⇒ PASS。
（A/A 是权威：先证明"不变的东西量出来就是不变"，两态的 0 差异才有意义。）

⚠️ **一处措辞更正（落档后再核）**：上面表格里"扫描前后各取一次指纹"的**依据**写成了"不依赖凭据"。
`content_fingerprint()` 实际走 `curl -u <dev Basic Auth>`——**它要凭据**，只是**不读 DB**。
"不可被静默关闭"的真正依据是 `if rc != 0 or not out.startswith('['): raise SystemExit`
（**读不到就中止整轮**），不是凭据无关。见 §4.2 末段更正。

---

## 5. 浏览器功能实测（`tools/b2d_h6_e2e.py`）

对**一次 JS 删除**做浏览器回归的理由：`formulas.js` 按 URL 入队，内容**从不出现在任何捕获里**，
字节门只能证明令牌搬家。而这类删除是**静默失败型** —— 语法错，或在已不存在的 `#configurator` 上抛错，
标记看起来完美、浏览器里是死的，而 75 页字节证明全程绿。

```
PASS  E2E: 34 ok / 0 FAIL
```

要点（每页先断言"拿到的是预检副本 ＋ ver=2.10.61"，否则拒绝继续）：

| 断言 | 结果 |
|---|---|
| 剂型页卡数 **＝ 基线捕获实测值**（4，不是凭记忆的 21） | 4/4 |
| 存档页卡数 ＝ 基线捕获（21），`.sf-fgrid` 恰 1 | ✅ |
| ItemList 仍可 parse 且**逐项覆盖全部卡片** | ✅ 4 / 21 |
| 每页 5 个 ld+json 块**全部 parse 成功** | ✅ |
| 页面上 `class="sf-formulas-data"` | **0** |
| `#configurator`（剂型页 / 详情页 / zh 页） | **0 / 0 / 0** |
| 一次**真实鼠标点击**（scrollIntoView → 命中校验 → move/down/up） | 落在按钮上 |
| 点击后弹 toast，且是**成功分支**那条文案 | ✅ |
| 点击后 `sessionStorage` 里 `sinofresh_formula_*` | **0**（写侧确实没了） |
| 点击后**页面不滚动**（死分支确实没了） | Δ=0 |
| 详情页全页 `h1` 恰 1 且＝右栏标题、hero CTA 名 ＝ 页标题 | ✅ |
| 助手依赖的 actives 带仍渲染（5 pills ＋ 2 labels，zh 同） | ✅ |
| 无页面错误、无 probe 失败 | ✅ |

### 5.1 ⛔ 剪贴板读回在这个环境里**不可得**（实测，不是推断）

首跑 `[E9]/[E18]` FAIL：剪贴板读回来是空串，而页面弹的是**成功**文案。两种解释的后果相反
（① 复制成功、我的读回瞎 ② 复制失败、toast 在说谎），所以**不能靠推理**，写了两个探针实测
（`tools/_h6_clip_probe.py` / `_h6_clip_probe2.py`）：

```
navigator.clipboard.writeText(...)  从 eval 调用  → REJECTED:NotAllowedError（无用户激活）
navigator.clipboard.writeText(...)  真实鼠标点击后 → RESOLVED（⇒ 弹成功 toast）
page 内 readText()                                → REJECTED:NotAllowedError
agent-browser clipboard read                      → NotAllowedError: Read permission denied
agent-browser clipboard paste（焦点 textarea）     → 字段仍为空
press Meta+v / Control+v                          → 字段仍为空
```

⇒ **`clipboard-write` 自动授予、`clipboard-read` 不授予**，四条读回通道全被权限拒绝。
代码本身是正确的（`writeText(text).then(onDone, onFail)`，拒绝会走**另一条**文案），
所以 `[E9]` 的判据改成"**点击把处理器推到了成功分支**"，并把"剪贴板在本环境不可读"**明写进输出**而不是悄悄放过。

**并且没有把这件事当信仰**：加了负对照 `[E11b]` —— 把 `writeText` 打桩成 reject 后再点，
**必须出现另一条 toast**（实测 `'Copy unavailable — reference "Joint Support So…'`）。
⇒ 成功文案是**有判别力的信号**，不是常量。

---

## 6. 截图（`tools/b2d_h6_shots.py` → `docs/batchH6-shots/`）

H6 删的东西**没有一个能拍下来**：删掉的选择器没有像素，删掉的 `<script>` 不投影子。
所以本批的帧只主张两件事：**站点看起来还是它自己**（几何比较的可视化对照），
以及**那个按钮还能用**（真实点击后的 toast）。

**没有"改前"帧**：基线副本已卸装，为拍两张图再装一次，买不到几何比较没说过的东西
（两态主张是 81 个页面视图的逐元素比较，不是两张 PNG）—— 手挑一对图是**把弱证据装扮成强证据**。

元素裁剪的一条实测纪律（批 H5 实测、本批复现）：`screenshot <selector>` 只在元素位于**初始 scrollY=0 视口内**时裁得正确；
先滚动会让它返回**尺寸正确但内容空白**的一块。⇒ 折叠线以下一律用**视口帧**，并把滚动偏移写在说明里。

14 帧，`VERDICT: PASS — 14 frames, each a real render the size it claims (min 2606 B, max 1155418 B)`：

| # | 帧 | 盒子 | 说明 |
|---|---|---|---|
| 01 | `01-dose-top.png` | 1440×900 | 剂型页顶部（8,976 B 离开样式表之后） |
| 02 | `02-dose-cta.png` | 1440×900 | **卡墙里的 K1 按钮**，视口帧 y=960（见下方"两处脚本 bug"） |
| 03 | `03-dose-cardwall.png` | 1440×900 | 卡墙 y=587，**4 张卡 ＝ 基线捕获数** |
| 04 | `04-dose-toast-after-click.png` | 1440×900 | **真实点击后**：toast `'Formula name copied. Paste it in your inquiry.'`，命中 `sf-formula__cta\|BUTTON` |
| 05 | `05-detail-top.png` | 1440×900 | 详情页顶部；**全页 h1 ＝ 1** |
| 06 | `06-detail-hero-cta-crop.png` | 209×38 | hero CTA **真裁剪**（在首屏内）＝ 210×38，差 1px 计入舍入说明 |
| 07 | `07-detail-actives.png` | 1440×900 | actives 带 y=1487；5 pills ＋ 2 labels，**样式完好**（助手类活了） |
| 08 | `08-detail-more.png` | 1440×900 | more 网格 y=4014（第二处链接来源） |
| 09 | `09-detail-full.png` | 1440×**5454** | 整页一张 |
| 10 | `10-archive-grid.png` | 1440×900 | 存档网格 y=448，**21 张卡** |
| 11 | `11-zh-detail-actives.png` | 1440×900 | `/zh/` 同一条带 y=1487，5 pills |
| 12–14 | `12/13/14-phone-*.png` | 390×844 | 手机：剂型页顶 / 卡墙 y=997 / 详情页顶 |

每帧都断言 IHDR 尺寸与自己声称的盒子一致（±1px 计入舍入说明）且**不是平帧**（解压后 distinct 字节 > 8）。

### 6.1 ⛔ 两处脚本 bug —— 都是"断言抓出来的"，不是我看出来的

1. **帧 02 原写的是 `.sf-formula__cta` 的裁剪**，首跑返回 **192 B / 4 个 distinct 字节值 / 209×38** ——
   尺寸完全正确、内容全白。这正是上面那条裁剪纪律所预言、且 **`png_probe()` 的"非平帧"断言抓到**的。
   ⇒ 改成**视口帧**并把 y 写进说明；同时确认详情页 hero CTA（06）在首屏内、裁剪可用，**保留一帧真裁剪**。
   **"断言只是形式"的反例**：如果只查"文件存在 ＋ 尺寸对"，这一帧会全绿地通过，而证据是块白板。

2. **帧 07/11 原用 `.sf-actives`，脚本 `raise SystemExit('... refusing to scroll to nothing')` 直接停机。**
   查证：`.sf-actives` 这个类名**全站不存在** —— 四份捕获（含**基线**）**命中均为 0**；
   真实容器是 `section.sf-fdetail-actives`，里面的 `sf-actives__label/__ing/__pill` 才是
   **本批刻意保留的那批助手类**。
   ⇒ **不是 H6 的回归**（基线本来就长这样），是**我按记忆里的类名写选择器**。
   修法：选择器改 `.sf-fdetail-actives`，并在脚本里写明"全站无 `.sf-actives`，别再写它"。
   **教训**：选择器不能凭记忆写；而"脚本拒绝对着不存在的元素拍照"这个设计，比"量到 null 就当 0"安全得多。

3. **帧内容与捕获的时间差（须连同帧一起读）**：帧拍于 **18:44**，而字节门的两侧捕获拍于**约 17 时**、
   早于 18:21:29 那次编辑 ⇒ 帧上多出的两段**测试占位文本**（§4.2 末段、§8）是**内容差异，不是渲染差异**。
   站点自 18:21:29 起未再变动（18:45 连测两次指纹一致），所以帧仍是**静止站点上的**捕获。


---

## 7. MOQ 对账（第 4＋12 项：**只出表，不改值**）

`sinofresh_formula_spec_cell()` 读的是**剂型模板文件本身**（`templates/page-{form}.html` 的 `sf-facts-mini`），
所以详情页这一侧**构造上不可能漂移**；风险在**不读它**的地方。八个剂型 × 六处声明逐项实测：

| 剂型 | `sf-facts-mini`（真源） | FAQ 答案 | 42 详情页 hero meta | `/products/` 卡 | `front-page.html` 卡 | `404.html` 卡 |
|---|---|---|---|---|---|---|
| soft-chews | from 500–1,000 units | 500–1,000 | 500–1,000 | ⛔ **from 500 units** | ⛔ **from 500 units** | ⛔ **from 500 units** |
| 其余 7 个 | — | 一致 | 一致 | 一致 | 一致 | 一致 |

⛔ **唯一冲突：soft-chews 的三处独立字面量**（`page-products.html` / `front-page.html` / `404.html`）。
"+三处对账"这个提法**漏的恰好就是这三处**。两个说法不是严格互斥（"from 500"不含范围），但只有一种准。
**按裁决保持现状**，改动本应落在模板字面量、**不是 DB**。表：`_backup/b2d-h6-geom/moq-recon.json`。

---

## 8. 未做的，与实测残留（**不在声明内 ⇒ 一律不动**）

| 项 | 实测 | 处置 |
|---|---|---|
| `.sf-spectable` **根类** 30 处 | 仍是死的（本批删的是 `__` 后代选择器） | 登记，不动 |
| `.sf-facts` **根类** 44 处 | 75 页渲染 **0 命中** | 登记，不动 |
| `data-form` / `{{FORM_SLUG}}` | 因死写删除而**实质归零**，但属性仍在标记上 | 登记，下一批标记整理 |
| `material` / `WebSite` / 弹窗复位 / `shelf_life` | 用户裁决：不做或保持 | 未来批 |
| `SearchAction` 前提 | ⛔ **站点根本没有搜索**（`get_search_form`/`?s=` 全 0 命中）⇒ 指向不存在的搜索页是**虚假结构化数据** | 已据此裁决不做 |
| ⛔ **post 158 的测试占位文本** | `Recommended For` → `testsadasdfasf`、`Use Cases` → `sdasdasdasad`，**EN ＋ zh 两侧都渲染**；由 18:21:29 那次 wp-admin 编辑写入（不在本批声明内） | **登记，不动数据**（按裁决）。⚠️ 见下 |

⚠️ 上一条**仅供裁决参考，不是本批结论**：dev 是**独立 WP**（docroot `/var/www/dev.zxpet.com/public`、
独立 DB `sinofresh`、`blog_public=0`、全站 Basic Auth），生产是另一套（`/var/www/html`，现为 maintenance 占位）
⇒ 这段占位文本**只在受封锁的 dev 上**，不是线上事故。它已出现在截图 07/11 里，
**上线前应清掉**（连同 `sf_formula_price_tiers` 的测试值），否则会随内容一起上线。

---

## 9. 预检副本与上线

- 副本现装 **`9de31e5`（`2.10.61`）** ⇒ **H6 的候选态**。
- ⛔ 按用户指令 **Step 6（`git pull` 上线）跳过**；dev live 主题停在 pre-H2b1 是**预期状态**。
- H6 是"H2b→H6"五批的**最后一批**。上线前仍须执行 `docs/dev-lockdown.md` 的**上线前 10 项移除**
  （最易漏：`blog_public` 0→1）。
- ⛔ **另须清理一处内容**（非封锁项，故不在那 10 项里）：post 158 的测试占位文本
  （`testsadasdfasf` / `sdasdasdasad`）与 `sf_formula_price_tiers` 的测试值 —— **会随内容一起上线**（§8）。

---

## 10. 证据索引

| 文件 | 内容 |
|---|---|
| `_backup/b2d-h6-baselines/`（76 文件） | 基线 75 页捕获（`2.10.60` × 75、`formulas.js 1.1.0` × 60、载荷 60 页 71,832 B） |
| `_backup/b2d-h6-candidates/`（76 文件） | 候选 75 页捕获（载荷 0 页） |
| `_backup/b2d-h6-gate.json` ／ `docs/b2d-h6-gates.txt` | 真候选全套门 |
| `_backup/b2d-h6-gates-synth.json` ／ `docs/b2d-h6-gates-synth.txt` | 合成候选全套门 |
| `_backup/b2d-h6-geom/{base,cand}.json` ＋ `{base,cand}.log` | 几何两态（**冻结版**，含内容指纹） |
| `_backup/b2d-h6-geom/{base,cand}-unfrozen.json` | 冻结**前**的旧捕获（留档；**不可与冻结版混比**） |
| `_backup/b2d-h6-geom/ab1.json` ／ `ab2.json` ＋ `aa.txt` | **A/A 自检**（同一份安装扫两遍，10 页面视图） |
| `_backup/b2d-h6-geom/compare.txt` | 两态比较输出（含声明／掩码／指纹的完整说明行） |
| `_backup/b2d-h6-e2e.json` | 浏览器 34 项 |
| `_backup/b2d-h6-geom/moq-recon.json` | MOQ 八剂型 × 六处 |
| `_backup/b2d-h6-scan/` | Step 0 三个扫描器的原始输出 |
| 工具 | `b2d_h6_deadscan.py` / `_inventory.py` / `_moq_recon.py` / `_css_prune.py` / `_confine.py` / `_geom.py` / `_e2e.py` / `_shots.py` ＋ 两个 `_clip_probe*.py`（剪贴板四通道实测）＋ `_h6_geom_diff.py` / `_h6_geom_keydiff.py`（差异归因的一次性工具） |

---

## 11. 本批新增的四条方法论（已回写手册与技能）

1. **删外部资源（CSS/JS）时，"字节门全绿"和"渲染没坏"是两件事** —— 外链文件的内容从不出现在捕获里，
   必须**浏览器两态实测**，且 `compare()` 要断言**两侧服务的不是同一份 sheet**。
2. **一个断言只要"总是成立"，它就没有证明任何东西** —— 本批两次踩到：M6 的靶串不存在（空转捕获）、
   E9 的剪贴板读回全空（恒为空）。修法都是加**具名负对照**：破坏必须改变被观察量。
3. ⛔ **先测噪声，再测差异；且"基线是谁"必须用证据确认。**
   - 差异不能直接解释 —— 先做 **A/A**（同一份安装扫两遍），A/A 会变的即为噪声
     （本批三类：动画相位／每请求 id／JS 每帧写的滑块条）。**处理完噪声的 A/A 必须归零，才去跑真两态。**
   - **基线的提交身份要用证据核实**（本批几何门一度装成 `084b246`，把 H5 的改动算进了 H6 的差异）。
   - **两态渲染比较的前提是"站点静止"** —— 本批实发并发编辑（post 158，18:21:29），
     其症状与"响应式被改坏"完全一样。⇒ 扫描前后各取一次内容指纹，不同即 FAIL，
     且守卫**不可被静默关闭** —— ⚠️ 依据是**"读不到就中止整轮"**，**不是**"凭据无关"
     （该守卫走 `curl -u`，它要凭据；写错理由会留下"401 就静默继续"的口子）。
4. **证据的"存在"与"内容"是两条断言；选择器不能凭记忆写。**
   - 截图只查"文件存在 ＋ 尺寸对"，一帧**全白**也能全绿通过（实测帧 02：192 B、209×38、正确尺寸）。
     真正抓到它的是 **"非平帧"断言**（解压后 distinct 字节 > 8）。**"尺寸对"永远不是"内容对"的证据。**
   - 一处选择器凭记忆写成 `.sf-actives`，**全站（含基线）命中为 0**，真实容器是 `.sf-fdetail-actives`。
     教训：靠"拒绝拍摄不存在的元素"（`raise SystemExit`）把它拦下来，**比把 `null` 当 0 静默放过安全**。
   - 帧的时间戳必须与门的时间戳**一起读**：本批帧（18:44）晚于字节门捕获（约 17 时），
     帧上多出的占位文本是**内容差异**，读的人必须知道，否则会把"内容变了"误读成"渲染变了"。
