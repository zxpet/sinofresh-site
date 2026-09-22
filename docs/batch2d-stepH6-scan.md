# 批次 H6 Step 0 —— 只读扫描 ＋【停机报告】

断面：`_backup/b2d-h5-candidates`（75 页渲染捕获，H5 候选态）＋ 主题源码树
（`_backup*` / `screenshots` / `docs` / `tools` 一律排除，否则历史副本与文档里的串会让死代码读成活的）。
本批**未改任何字节**。工具：`tools/b2d_h6_deadscan.py`（token 计数）／`tools/b2d_h6_inventory.py`
（短码与资产）／`tools/b2d_h6_moq_recon.py`（MOQ 对账）。**四个控制 token 全部读活** ⇒ 扫描器可信。

---

## 0. 结论速览

| 类别 | 项 | 结论 |
|---|---|---|
| **甲 可自动执行** | 1, 2, 3, 5, 6, 7, 8 | 死 CSS 50 条选择器／1 个孤儿短码渲染器／0 个孤儿 JS／1 处死写／60 页 73 KB 死载荷／1 个死分支／1 条死选择器 —— **方向明确，无需裁决** |
| **乙 需裁决** | 4＋12, 9, 10, 11, 13, 15 | ⛔ **含一处访客可见的事实冲突**（soft chews 的 MOQ 两个说法）；另有 3 项**手册前提不成立**，须重新定范围 |
| **丙 需改数据** | 14 | `material` 无真源 ⇒ 补字段须回填 21 条记录 ⇒ ⛔ **触发停机条件 ③** |
| **建议关闭** | 3, 13 | 3＝零孤儿，无可做动作；13＝本类泄漏全站**只有一个实例**，H5-0 已处理 |

**⛔ 停机。** 三条理由：① 手册与实况不符（第 10 项说"三处"实为 **7 处**；第 15 项的 `SearchAction` 前提〔站点有搜索〕**不成立**；第 4 项说"三处对账"漏了首页/404/产品索引卡）② 扫描抓到**访客可见的内容冲突**（第 4 项）③ 第 14 项**需改数据**。

---

## 1. 甲类：可自动执行

### 1.1 第 1 项 —— 三类遗留 CSS：**50 条选择器，三层都为零引用** ✅ 可删

| 家族 | style.css 内选择器 | 活源码引用 | 75 页渲染命中 |
|---|---|---|---|
| `.sf-facts__*`（H1 遗留） | **14** | **0** | **0** |
| `.sf-spectable__*`（批 E 遗留） | **23** | **0** | **0** |
| `.sf-fdetail-media__*`（H2a 遗留） | **13** | **0** | **0** |

**取证三层**：① 全源码 token（含 `assets/js|css`，排除 `docs/` 与 `*.md`）② 75 页渲染 HTML ③ 历史副本单列
（`sf-spectable__` 在 `_backup/*` 里还有 209 处 —— **正是它让朴素递归 grep 读成"活的"**）。

⚠️ **边界**：三层里第 ② 层只覆盖这 75 页断面；断面上有 `aside.sf-basket-drawer` 这类**每页都有**的类，
但它们不在这三个家族里。第 ③ 层证明"只在历史副本里活"。

⚠️ 删的时候**只删选择器文本，不整块删规则** —— 若某条规则是 `.sf-facts__row,<活选择器>{}` 形式的选择器列表，
整块删会连带删掉活的那一半。（实现期逐条核。）

### 1.2 第 3 项 —— 无引用 JS：**零孤儿** ✅ 关闭

15 个 `.js` 在盘上，16 处 enqueue（15 脚本 ＋ 1 样式表），**孤儿 0 / 缺文件 0**。
⇒ 本项**无可执行动作**，建议直接关闭。

### 1.3 第 2 项 —— 已删短码的残留：**1 个孤儿渲染器**

16 个短码注册，**15 个有调用点，1 个没有**：

```
孤儿：sf_formula_actives     注册 functions.php:1494，渲染器 functions.php:1408
      全站调用点：0（8 个剂型模板里的调用点已随 H2b1 消失）
活：  sf_formula_detail_actives   templates/single-sf_formula.html:83  ✅
```

⛔⛔ **但它不能整块删** —— 详情页那个变体**依赖它的两个解析助手**：

```
functions.php:2180  "Parsing is [sf_formula_actives]' own two helpers, unchanged —
                     the same split that band uses on the same fields, so the two
                     pages cannot disagree about where an ingredient ends."
sinofresh_formula_detail_actives()  第 2204 行调用 sinofresh_formula_split_top_level()
                         并复用 .sf-actives__pill / __label / __ing 三个类
```

⇒ **裁决方向**：删**注册行＋渲染函数体**，**保留两个解析助手与 `.sf-actives__*` 样式**。
说"删掉 actives 那一段"会连带删掉活代码，是本项最容易踩的坑。

### 1.4 第 5/6/7/8 项 —— 一处死写、一处死载荷、一个死分支、一条死选择器

全部溯源到**同一个事实**：`configurator.js` / `configurator.css` 已随 H2b2 删除，而它的**对侧**还在。

| 项 | 物证 | 量 |
|---|---|---|
| **5** | `assets/js/formulas.js:95` `sessionStorage.setItem('sinofresh_formula_' + slug, name)` | 写侧 1 处；**读侧 0**（全 `assets/` 内 `sinofresh_formula_` 只出现 2 次：注释 ＋ 这行写） |
| **6** | `functions.php:1299` 输出 `<script type="application/json" class="sf-formulas-data">` | **60/75 页**；JSON **72,720 B** ／整个 `<script>` 元素 **76,680 B**（差 3,960＝60×66 的标签开销）。声明过的唯一读者是 `configurator.js:readFormula()` |
| **7** | `assets/js/formulas.js:110` `document.getElementById('configurator')` | 1 处；渲染页 `id="configurator"` **0/75** ⇒ 分支永不进（且被 `if (target)` 护着，不报错） |
| **8** | `style.css:1220` `.configurator__summary-value` | 1 条；活引用 0；渲染页 `configurator__` **0/75** |

⇒ 6 的收益最大（**60 页 × 1.2 KB 的无效 JSON 不再下发**）。四者的判据一致：**新候选上这些串一律为 0，
且 `undo_declared` 后与基线逐字节相同**（H5 的四条判据形状可直接复用）。

---

## 2. 乙类：需裁决

### 2.1 ⛔ 第 4＋12 项 —— **同一个剂型，站点对访客说了两个 MOQ**（本轮最重要的发现）

`sinofresh_formula_spec_cell()` **读的是剂型模板文件本身**（`functions.php:680` 打开
`templates/page-{form}.html`，从 `<section class="sf-facts-mini">` 里取 `data-label` 的值），
所以**详情页这一侧是"一个来源"、构造上不可能漂移**。真正的问题在**不读它的那些地方**：

| 声明处 | soft-chews 的值 | 是否读真源 |
|---|---|---|
| 剂型页 `sf-facts-mini` 行 | **from 500–1,000 units** | 真源 |
| 剂型页 FAQ 答案 | **from 500–1,000 units** | ✗ 模板里的独立字面量 |
| 42 个详情页 hero meta | **MOQ from 500–1,000 units**（8 页 × 软咀嚼） | ✅ 读真源 |
| `page-products.html` 卡片 | ⛔ **MOQ from 500 units** | ✗ 独立字面量 |
| `front-page.html` 卡片 | ⛔ **MOQ from 500 units** | ✗ 独立字面量 |
| `404.html` 卡片 | ⛔ **MOQ from 500 units** | ✗ 独立字面量 |

**八个剂型逐项对账**：只有 **soft-chews 一处**冲突；其余 7 个（drops/liquids/pastes/powders＝500；
dental-chews/fish-oil/tablets＝1,000）**六处全部一致**。没有其他漂移。

⚠️ 两个说法**不是严格互斥**（"from 500"不含范围），但它们是同一事实的两种陈述，且只有**一种**是准的。
"三处对账"这个提法**漏了首页、404 与产品索引卡** —— 冲突恰好就在这三个漏掉的地方。

⇒ **需裁决**：soft-chews 的起订量到底是 **500** 还是 **500–1,000**？定下来之后，改动落在**模板字面量**上
（`page-products.html` / `front-page.html` / `404.html`），不是 DB。

### 2.2 第 9 项 —— `sf_formula_shelf_life` 死键

`inc/formula-admin.php:42`（描述）＋`:106`（字段定义，`req=2`，group `packaging`）注册；
**前端 0 处读取**。H3 的裁决原文已写在 `functions.php:2307-2312`：

> `sf_formula_shelf_life` is 21/21 "18 months" and **has never been read on the front end**, while the
> parameter row above derives the same fact from `sf_formula_specs`. Two sources for one fact drift;
> the rule here is one source of record per fact... **The key stays registered and the dead end is logged for H6.**

⇒ **需裁决**：①（推荐）**保留** —— 它是后台对"保质期"的唯一记录，且 21/21 有值；删字段会让这 21 个值变成孤儿数据。
② 若要收敛，正确动作是**让 H2a 的 Shelf life 行改读它**，而不是删它。
⚠️ 与 H2a 的 `Shelf life` 行是**一对**，必须同时裁决。

### 2.3 第 10 项 —— 硬编码 `sales@zxpet.com`：**不是三处，是 7 处 / 4 文件**

手册记的是"`functions.php:4925` 收件人 ＋ `config-pdf.php` ×2"。实测：

| # | 位置 | 性质 |
|---|---|---|
| 1 | `functions.php:4451` `sf_site_settings_defaults()` | ✅ **就是真源**（选项默认值） |
| 2 | `functions.php:4504` `sanitize_callback` 兜底 | ✅ 合法默认 |
| 3 | `functions.php:5383` `get_option('sf_contact_email', 'sales@…')` | ✅ 读选项，只是带默认 |
| 4 | `functions.php:2951` 选项为空时的兜底收件人 | ⚠️ 合法兜底（可讨论） |
| 5 | **`functions.php:5756`** `$sales = 'sales@zxpet.com'` → 用于 `:5793` 邮件正文行 ＋ `:5794` 的 `Cc:` | ⛔ **真硬编码** |
| 6 | **`inc/config-pdf.php:102`** `Cc: sales@zxpet.com` | ⛔ 真硬编码 |
| 7 | **`inc/config-pdf.php:195`** `Cc: sales@zxpet.com` | ⛔ 真硬编码 |
| 8 | **`inc/config-pdf.php:440`** PDF 正文 `Request samples` 行 | ⛔ 真硬编码（**手册未列**） |
| 9 | **`inc/config-pdf.php:527`** PDF 正文 `Request a sample` 行 | ⛔ 真硬编码（**手册未列**） |
| 10 | **`inc/cert-download.php:169`** REST 404 文案 `Please email sales@zxpet.com.` | ⛔ 真硬编码（**手册未列**） |
| 11 | **`templates/page-contact.html:48`** `<a href="mailto:sales@zxpet.com">` | ⛔ 真硬编码（**手册未列**） |
| — | `inc/config-pdf.php:14`／`assets/js/basket.js:10` | 注释，不算 |

⛔ **手册的 `functions.php:4925` 锚点已失效**（现为 **5756**）—— 认锚点别认行号（§J）。
⛔ 今天这些值**恰好都等于选项值**（H4e 把选项也改成了 `sales@`），所以**现在看不出问题**；
漂移风险是"选项一改，这 7 处不跟"。
⇒ **需裁决范围**：建议只收敛 ⛔ 那 7 处（读 `sf_contact_email`，空则回落到 `sf_site_settings_defaults()` 的同名默认值），
**不动** 1–3 的默认值本体（那是真源）。模板里的 `mailto:` 要不要一起收敛，请一并定。

### 2.4 第 11 项 —— 询盘弹窗提交后无复位路径

`assets/js/inquiry.js`：

```
:229   form.hidden = true;            ← 成功时翻转
:230   success.hidden = false;
:234   timer = setTimeout(close, 3000);
:123   close() 只做 modal.classList.remove('is-open') / modal.hidden = true / 解锁 body
       —— 从不把 form.hidden / success.hidden 翻回来
:114   var first = form && !form.hidden ? nameInput : closeBtn;
       —— 它甚至**专门处理了"表单已隐藏"这一支**（此时聚焦关闭按钮）
```

⇒ **行为是自洽的、看起来是有意的"一次性"弹窗**，不是漏写。但代价是：提交过的访客再点胶囊，
看到的是 3 秒后自动关闭的确认页，**没有第二次提交的入口**。
⇒ **需裁决**：① 复原（`open()` 里复位两处 `hidden`）② 明确做成一次性（并让文案说清"如需再询价请联系…"）。
推荐 ①，因为同一访客常要问第二个配方。

### 2.5 第 13 项 —— `theme.json` 元素规则的隐式泄漏：**全站只有一个实例，H5-0 已处理**

按"三处枚举"复查 75 页渲染产物：带 `__title|__heading|__eyebrow|__subtitle` 的类共 **12 个**，
其中落在**非标题标签**上的只有 **4 个**：

| 类 | 标签 | 出现 | 判定 |
|---|---|---|---|
| `sf-formula-hero__title` | `div` | 42 | ✅ **H5-0 已修**：`.sf-formula-hero__title{font-weight:700}` 已声明，打印选择器组已含该类 |
| `sf-slide__title` | `p` | 6 | ✅ 无害：`<p>` 不受 `styles.elements.h1–h4`（编译成标签选择器）影响，且该类**已自行声明** `font-size/font-weight/line-height/letter-spacing/color` |
| `sf-slide__subtitle` | `p` | 8 | ✅ 自行声明 `font-size/line-height/color` |
| `sf-slide__eyebrow` | `p` | 2 | ⚠️ **只声明 `color`**（style.css:1071）⇒ 字号/行高来自 body 默认（16px/1.6）。**不是 H5-0 那种"改变标签名"的泄漏**，是既有的样式选择 |

⇒ **建议关闭本项**，只留一句登记：`.sf-slide__eyebrow` 若日后要显式化，补 `font-size` 即可。
⚠️ `styles.elements.heading` 的 `fontWeight:600` 与 `styles.elements.h2/h3/h4` 也都在 `theme.json` 里，
**未来任何一次"标题标签改成 div"都必须同时检查这六组**（本批已确认现在没有第二个实例）。

### 2.6 第 15 项 —— `WebSite` schema：**⛔ 站点根本没有搜索，`SearchAction` 会是假声明**

- 全站源码 `WebSite` 出现 **0 次** —— 属实。
- 但 `get_search_form` / `get_search_link` / `?s=` / `searchform` **全部 0 命中** ⇒ **本站没有搜索功能**。

⇒ 手册给本项的落点建议（`WebSite + SearchAction`）**前提不成立**。`SearchAction` 指向一个不存在的搜索页
是**虚假结构化数据**，Google 明确要求该 URL 真实可用。
⇒ **需裁决**：①（推荐）**不做**，或 ② 只发**裸 `WebSite`**（`name`/`url`/`publisher`，无 `SearchAction`，收益很低）；
③ 若要做 `SearchAction`，须**先建站内搜索**（那是另一个批次）。

---

## 3. 丙类：需改数据

### 第 14 项 —— Product 的 `material` 无真源 ⇒ ⛔ 停机条件 ③

- 源码里 `material` 只作为**英文散文**出现（"raw material inspection" 等），**没有任何 schema 键或 meta 字段**。
- `sf-facts-mini` 每个剂型模板**恰好 4 行**：`MOQ` / `Lead time` / `Certifications` / `Packaging formats` —— **没有材质行**。
- `sf_formula_*` meta 里也没有材质字段。

⇒ 要发 `material` 就必须**先造真源**（`sf-facts-mini` 加第 5 行？还是每个剂型一条 meta？）**再回填 8 个剂型 × 内容**。
这是**新增数据**，不是派生 ⇒ **触发停机条件 ③，本批不做**，请裁决：补真源 / 明确不做并记档。

---

## 4. 门的设计前提（H6 与 H5 不同）

H6 是**删除 + 一处内容订正**，与 H2b2（纯删除）和 H5（纯新增）都不同：

1. **两类改动的判据必须分开声明**：① **删掉的串在候选上出现 0 次**（H5 的覆盖断言直接复用）
   ② **`undo_declared(candidate) == baseline` 逐字节**（H2b2 的形状）——
   注意 H6 **会动 `style.css`**（第 1 项）⇒ **必须两处同步 bump 版本令牌**（`functions.php` enqueue ＋ `style.css` 头 `Version:`），
   于是 75 页会**只**在 ver 令牌上有差 ⇒ 掩码/归一化必须先吃掉令牌（§B/§C）。
2. **`sf-formulas-data` 的删除会实质改变 60 页的字节**，不是令牌差 —— 声明必须精确到"哪 60 页、删多少字节"。
3. **第 4 项若改了模板字面量，`sf-formula_spec_cell()` 读的还是同一份文件** ⇒ 改 `sf-facts-mini` 行会**连带**改 42 个详情页的 hero
   （那是正确的连带，必须在声明里写明"预期连带"而不是当成回归）。
4. **孤儿短码的删除不能动它的助手**（§1.3）⇒ 门要有一条**具名负对照**：
   "把 `sinofresh_formula_split_top_level()` 一起删掉"必须 FAIL。

---

## 5. 证据索引

| 文件 | 内容 |
|---|---|
| `_backup/b2d-h6-scan/deadscan.txt` / `.json` | token 计数（含四个控制 token） |
| `_backup/b2d-h6-scan/inventory.txt` | 短码双侧 ＋ 资产双侧 |
| `_backup/b2d-h6-scan/moq.txt` | MOQ 六处声明逐页对账 |

工具：`tools/b2d_h6_deadscan.py`（3 个）／`b2d_h6_inventory.py`／`b2d_h6_moq_recon.py`

---

## 6. 停机声明

**本批未进 Step 1、未改任何字节、未建新门的判据。** 请裁决：

- **乙类**：4＋12（soft chews 起订量取哪个数）／9（Shelf life 字段保留还是改读它）／
  10（收敛哪几处）／11（弹窗复原还是一次性）／15（`WebSite` 做还是不做）
- **丙类**：14（`material` 补真源还是一次性记档不做）
- **建议直接关闭**：3（零孤儿）／13（只有一个实例且已修）
- **甲类 1/2/5/6/7/8 我可以在裁决后自动执行**（含 50 条死选择器、1 个孤儿渲染器、73 KB 死载荷、1 处死写、1 个死分支、1 条死选择器）
