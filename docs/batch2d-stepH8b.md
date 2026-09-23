# Batch H8b — 上线前剩余任务 · 批 2／3：Shape 与 Container Type 按剂型作答（2026-09-23）

> 代码提交 `1234492`（1/2）。门、E2E、帧与本档在第二个提交里。
> **未 pull 到 dev**，生产站零改动。
> 扫描报告（已随代码提交）：`docs/batch2d-stepH8b-scan.md`。

---

## 〇、本批范围与四条裁决

### 0.1 范围

**待办24「Shape / Container 按剂型差异化」** 一项，含两半：Shape 组与 Container Type 组。
版本：`style.css 2.10.74 → 2.10.75`。**本批不动 CSS、不动 JS**，这次 bump 是**标记性**的
——它的唯一作用是让「两条路由各自在服务哪一份字节」这件事可以被读出来（§5 的头两张帧就是靠它分左右）。

### 0.2 四条裁决（用户全选推荐项）

| # | 问题 | 裁决 |
|---|---|---|
| ① | Shape 的选项从哪来 | **A 与后台同源** —— 读 `sf_formula_field_pool($form_slug, 'shape')`，与 `inc/formula-admin.php` 里 `'pool' => 'shape'` 声明的是同一个函数 |
| ② | Container 的选项从哪来 | **A 按剂型 packaging 池** —— 不再读 Site Settings 的容器库 |
| ③ | 组的名称 | **改，按池** —— 粉末/滴剂/液体叫 `Appearance`，膏剂叫 `Texture`，鱼油叫 `Form` |
| ④ | Container 原来「等记录有值才渲染」的门 | **撤掉，全页常显** —— 与 Shape 同一条规则 |

第 ③ 条连带的：specs 表里那一行也跟着改（`$rows[($shape_row !== '' ? $shape_row : 'Shape')]`），
否则「Appearance 的拣选器上面写 Shape: Fine Powder」＝本批自己跟自己打架。

### 0.3 一条只报告、未改数据的事实

post 158 的 `sf_formula_container` 存的是**旧库的词** `Round`，它**不在任何 packaging 池里**。
本批**不碰数据**，所以这一行靠两处机制保住：

* `sinofresh_container_label('Round')` —— 在新库/新池里找不到，**回落到原始词**，meta 行照旧打印 `Round`；
* `'keep_unknown' => true` —— 保存处理器会清掉不在池里的 radio 值，没有这个旗标，**下一次保存会删掉一个没人动过的值**（与 H8a 保质期池同一个隐患）。

⇒ **待销售在后台重存一次 post 158，它就会落进新词表。** 这是数据决策，不是代码问题。

---

## 一、实现要点（为什么这么写）

### 1.1 病根不是「少了选项」，是**一个池子两个读者**

后台从 H1 起就写着 `'pool' => 'shape'`，所以一个粉末的编辑**只能**选
Fine Powder / Granules / Microencapsulated / Custom；而详情页在 42 页上**一律**画
`sf_shape_library()` 的八个软咀嚼形状。**两个方向同时是错的**：

* 粉末页在卖 `Bone` 和 `Paw`；
* 编辑实际选中的那个词（`Microencapsulated`）**在页面上根本不存在**。

所以本批的判据不能是「页面多/少了几个选项」，只能是**整张列表逐项相等**——
`applies` 里那 42 条 shape 编辑就是这件事。

### 1.2 库不退休：降级为**图片载体**

`sf_formula_library_options($pool, $library)` 取**池**的选项、取**库**的图片，
按**标签**匹配（`sf_formula_pool_option_image()`，大小写不敏感——两个列表都是手维护的，
`Round` 与 `round` 不是访客应该能看出来的差别）。

今天两个库里每一个 `attachment_id` 都是 `0`，所以这条路径**不改一个像素**；
它保住的是 Site Settings 页面承诺的「以后上传形状图」那条路。

### 1.3 Container 是同一件事，外加一件

它的选项原本是 Site Settings 的容器库 —— `Round / Square / Oval / Jar / Pouch / Tube / Custom`，
那是**瓶型，不是包装格式**（「Round」不是一个包装形式）。后台当时用 `'pool' => '_containers'`
读同一个库，所以**两端互相一致、却一起答错了题**。两边现在都读按剂型的 packaging 池，
`'_containers'` 池和它的解析函数 `sf_formula_container_options()` 已**删除**，不留悬空。

第二件事是那道门。旧写法：

```php
if ($container !== '' && function_exists('sf_container_library')) { ... }
```

它让这个组**等记录自己有值**——这就是「21 页里只有 1 页画了它」的原因。选项不再依赖记录，
于是它和 Shape 走同一条规则。

### 1.4 `keep_unknown` 从 select 分支补到 radio 分支

H8a 只教会了 `select` 分支（保质期是 select）。`Container Type` 是 **radio**，
所以这条旗标要在 radio 分支里也生效——否则编辑打开记录会看到**一个都没勾**的列表：

```php
if (!empty($spec['keep_unknown']) && '' !== (string) $raw && !in_array($raw, $opts, true)) {
    array_unshift($opts, $raw);
}
```

### 1.5 后台的字段标签仍然只叫 `Shape`（故意不动）

页面的组名跟着池走，但 **wp-admin 那个字段标签不跟**：阶段一的横幅与列表页用**同一个标签**打印全部
21 条记录，它是一个**跨记录名**，而页面上的组标题不是。判断依据不同，就不该一起改名。

---

## 二、改动清单（提交 `1234492`）

| 文件 | 改动 |
|---|---|
| `docs/batch2d-stepH8b-scan.md` | +148（扫描报告） |
| `sinofresh-theme/functions.php` | +160 / −91 区段：`$form_slug` 取剂型；Shape 组整体替换；Container 组整体替换并撤门；specs 行名同源；正文 Container 注释更新；版本 `2.10.75` |
| `sinofresh-theme/inc/formula-admin.php` | 40 行：`'pool' => 'packaging', 'keep_unknown' => true`；**删** `sf_formula_container_options()`；`` `_containers` `` 分支删除；radio 分支新增 `keep_unknown` |
| `sinofresh-theme/inc/formula-pools.php` | +89：新增 `sf_formula_pool_option_image()`、`sf_formula_library_options()` |
| `sinofresh-theme/style.css` | 2 行：`Version: 2.10.74 → 2.10.75`（标记性） |
| `tools/b2d_h8b_pool_check.php` | +108：独立池检查（只桩 `sanitize_title` / `wp_get_attachment_image_url`），五组断言 **PASS 0 clause(s) failed** |

合计 6 文件、+456 / −91（其中主题 4 文件、+200 / −91）。

---

## 三、门（`tools/b2d_h7_gate.py --batch h8b`）

**基线**＝`_backup/b2d-h8a-candidates`（＝H8a 的预检副本，`?ver=2.10.74`）；
**候选**＝`_backup/b2d-h8b-candidates`（`?ver=2.10.75`，75 页全 200）。
两个 JSON：`_backup/b2d-h8b-gate.json`、`_backup/b2d-h8b-gate-source.json`（**源码段独立跑**）。

### 3.1 全绿表

| 段 | 结果 |
|---|---|
| A/A（同一状态两次抓取） | 75 页 **0 差异** |
| 主证 `mask(transform(baseline)) == mask(candidate)` | 75 页 **0 差异**，`applied 128 (declared 128)`，方向 `insert` |
| coverage | **48 条**（13 absent ＋ 16 insertions ＋ 19 counts）全绿 |
| invariants | **24 行** 全绿（14 unmoved ＋ 2 per_page ＋ 2 scoped ＋ 2 corroborated ＋ 2 order ＋ h2_delta ＋ json-ld） |
| 掩码回读 | 23 页 **0 differ**；46 个被掩的币种值是二进制非文本 |
| 破坏矩阵 | **6/6 全部被捕获**，无一是空转变体 |
| 负对照 | **27 项**（NC1–NC16 ＋ 12 × NC-src ＋ 3 × NC-page）全部按预期失败 |
| 源码段（独立跑） | **22 条**全绿 |
| h2 delta | 0 页移动（声明：none） |
| JSON-LD 深比较 | 75 页解析，全等 |

### 3.2 `applies = 128` 的逐条算术（必须自洽，否则就是声明写错）

```
22  组名  'Shape' → 池自己的词         （11 页 × 2 语言：膏2＋粉3＋滴2＋液2＋油2）
22  同一批页的 box aria-label          （同上，正好同 11×2）
42  shape 组整张选项表换成池的          （42 页）
 2  post 158 的 container 选项换成池的  （1 页 × 2 语言）
40  其余 40 页插入整个 container 组     （42 − 2）
---
128
```

**为什么是「22」而不是 42：** 池把这个问题在软咀嚼／片剂／洁牙咀嚼上也叫作 `Shape`，
所以那 20 页的组名**不是编辑**。`_h8b_rub()` 于是**返回 0**（基线已经说了同一句话）。
把它们算成编辑，会让一个组名写错的页面**藏进总数里**——
而总数正是主证唯一检的那个数。

### 3.3 coverage 的决定性条目（节选）

| 声明 | 基线 → 候选 |
|---|---|
| `name="sf-config-shape"` | **336 → 218** |
| `data-sf-config-group="container"` | **2 → 42** |
| `name="sf-config-container"` | **14 → 198** |
| `sf-fdetail-config__label">Shape<` | 42 → 20 |
| `sf-fdetail-config__label">Appearance<` | 0 → 14 |
| `type="radio"` | 536 → 602（差 66 ＝ (218+198) − (336+14)） |
| `data-sf-config-custom-input="` | 108 → 148（＋40 ＝ 40 个新组各带一个盒子） |
| `value="bone"` 等 12 个旧库 slug | 各 → **0**（两套退役词表**逐词**清空） |
| `name="sf-config-container" value="Custom"` | 0 → 42 |

**336 → 218 的两半都要读**：218 是各剂型池的和（8×8＋5×6＋6×6＋4×4＋4×6＋4×4×3），
而 336 是「8 个形状 × 42 页」——**只有这一对数在一起，才说明「一个词表」变成了「八个词表」**。

### 3.4 invariants 里最关键的几条

* **`scoped`**：`container` 组在**每一个详情页一次**、在**其他任何页零次**。
  `unmoved` 说不出这句话——42 这个总数也可以是「一页扛了 42 个」。
* **`corroborated`**：shape / container 的选项数**从基线那一页自己的剂型读出**
  （`_h8b_opts_expected` 读 specs 表的 `Dosage Form` 行，与文件名无关）。
  一个悄悄少一个选项的页面**只会让那一页动 1**，任何站点总数都看不出来。
* **`order`**：container 组必须**排在 shape 组之后**、且在**收尾的 summary 之前**。
  「同样的两组换了顺序」在 `insert` 方向下主证是看不见的。
* **`unmoved` 里的 `sf-fdetail-specs__term` 写 42 而不是 358**：
  这一族的 `want` 是**页数**不是出现次数（本批修掉的两条就错在这里，见 §3.7）。

### 3.5 破坏矩阵 6/6

| 变体 | 结局 | 依据 |
|---|---|---|
| 不折叠版本令牌 | 捕获 | 75 页差异 |
| 组名留作 `Shape` | 捕获 | 22 页差异（且 applied 84/128） |
| shape 组留作旧八个名字 | 捕获 | 42 页差异 |
| container 组原样不动 | 捕获 | 42 页差异 |
| 运行数少报 1 | 捕获 | applied 128/127 |
| 完全不施加 | 捕获 | 42 页差异 |

### 3.6 负对照 27 项

12 条 `NC-src` 覆盖**每一条源码断言族**：版本头、enqueue、Shape 读回库、Container 读回库、
Container 那道门回来、specs 行名写死、图片载体、大小写匹配、`Custom` 标记、
后台池、radio 的 `keep_unknown`、退役的解析函数回来。
3 条 `NC-page` 分别打 `scoped`／`order`／`corroborated`——**三条都住在 `invariants` 里**，
不是随便挑的页面编辑。`NC13` 走 `sighted`（`insert` 方向逐字节比对 payload，
所以主证**应当看见**，覆盖率**应当确认**），实测 `main_red=True coverage_red=True`。

### 3.7 顺手修掉 H8a 一条「不可能响」的断言

H8a 的声明里：

```python
('no 2.10.73 header survives', 'css_live', r'(?m)^Version: 2\.10\.73$', False),
```

`css_live` 是**注释剥离后的孪生文本**，而 style.css 的主题头**本身就住在一个 `/* */` 块里** ——
那一行被抹成空格，所以这条断言**永远为 0、永远通过**。本批把 H8b 的同名断言写在 `css`（原始字节）上，
并**回头把 H8a 那条也改了**，然后在 H8a 的主题状态上重跑验证：

```
$ git archive 1234492^ sinofresh-theme | tar -x -C /tmp/h8a-theme
$ … --batch h8a --source --theme /tmp/h8a-theme/sinofresh-theme   → PASS 22/22
$ … --batch h8a --negctl --theme /tmp/h8a-theme/sinofresh-theme   → 27/27 全 ok
$ 聚焦验证：把 Version 改回 2.10.73 → 两条同时响
  [{'label': 'style.css declares 2.10.74', 'want': True, 'got': 0, 'ok': False},
   {'label': 'no 2.10.73 header survives', 'want': False, 'got': 1, 'ok': False}]
```

`got: 1` 就是它过去**不可能**打出的那个数。**改法是加强断言，不是放宽它。**

---

## 四、E2E（`tools/b2d_h8b_e2e.py`）

**判据按剂型分档**：八个剂型八套期望值，**不跨剂型复用**。
`POOLS` 表是从 `inc/formula-pools.php` **第三次手工转写**的，
刻意**不 import 门里那份**——脚本从门里取期望值，就会同意门的任何错误；
这两份独立读法由门的 `source` 段负责要求它们都与产品一致。

### 4.1 预检 **95/95 PASS**（2.10.75）

八个剂型逐一断言，每个九条：页面自报的剂型、组标题（`__label` 与选项表 `aria-label` **两个载体**）、
选项**逐项有序相等**、全是 radio 且无预选、Container 组渲染且选项有序相等、container 在 shape **之后**、
两组各自以 Custom 收尾且盒子归属本组、盒子的 `aria-label` 点名本组、桌面宽度下每一组都**被画出来**。

跨页那两条是**任何单页都做不出**的声明：

```
the eight forms draw eight different shape pools
  → {'Soft Chews': 8, 'Tablets': 5, 'Dental Chews': 6, 'Pastes': 4,
     'Powders': 4, 'Drops': 4, 'Liquids': 4, 'Fish Oil': 4}
...and the four names only soft chews own appear on no other form
  → {'Heart': ['Soft Chews'], 'Star': ['Soft Chews'],
     'Paw': ['Soft Chews'], 'Cylinder': ['Soft Chews']}
```

外加：post 158 的 meta 行仍打印 `Round`（记录自己的词）而选项是软咀嚼的 packaging 池、
它的价格阶梯仍是自己一组；zh 孪生页两张池与英文页一致；`/about/` 长出 0 个 container 组。

**手机段（375×812）** —— 折叠的切点在**第 5 组**（H7l），而本批往 40 页上**各加了一组**，
所以「有没有把某一页推过那条线」是桌面段问不出来的问题：

* `calcium-phosphorus-tablets`：4 组，折叠态下**四组全可见**（切点在 5）⇒ **本批没有造出任何被藏起来的组**；
* post 158：折叠后仍是 H7l 保留的四组，**展开后 container 组上屏**。

### 4.2 live 60/95 红（2.10.73）

`--live` 去掉预检头、直接驱动 dev 自己那份 2.10.73。**每一项都必须红**，这一轮才是「脚本会失败」的证据。

**35 条绿的全部意义**（不是噪声）：

| 绿的 | 为什么本来就该绿 |
|---|---|
| 8 × `the 2.10.73 theme answered` ＋ 8 × `the page states the dosage form` | 守卫：证明拿到的是被服务的 2.10.73 页、且页面自报的剂型正确（★） |
| `Soft Chews / Tablets / Dental Chews the group is titled the way its pool is` | **这三个剂型的池把问题就叫 `Shape`** —— 它们本来就达标，不是漏检 |
| 8 × `every group it has is drawn at desktop width` | 本批没动可见性 |
| post 158 `...and its ladder is still a group of its own, untouched` | 本批没动阶梯 |
| `/about/ a page with no configurator gained no container group` | 本批没往无关页加东西 |
| `...and unfolding it puts the container group on screen` | 展开按钮本来就工作 |
| 2 × 手机段 `the 2.10.73 theme answered` ＋ 2 条 `the record ...` 的守卫 | 同上（★） |

（★）`served()` **先证明答话的是哪一份资源再断言内容**，所以「页面本身没加载」与「部署不对」不会混在一起。

**60 条红的形态正是本批的形状**：五个组名不同的剂型（膏/粉/滴/液/油）连**组标题**一起红；
八个剂型**全部**在「选项逐项相等」「Container 组渲染」「两组的 Custom 收尾」上红；
两条跨页声明红；`the eight forms draw eight different shape pools` 红 —— 因为 live 上**八页画的是同一张表**（★核心）。

### 4.3 本批 E2E 自己写错的两处判据（都已修，未放宽）

1. **「已导航」≠「已加载」**。手机段比其他段多一次 `reload`，于是两页读到
   `theme: '' / title: '' / h1: 0`，而 `location.pathname` 是对的 ——
   这**与「部署坏了」长得一模一样**，5 条假 FAIL 全出于此。
   修法不是加 `sleep`，是加**就绪门** `wait_ready()`：轮询
   `readyState === 'complete'` ＋ 有 `title` ＋ 至少一个 `link[rel=stylesheet]`，
   并把结果并进 `served()` 的判据与诊断里。加 `title`/样式表两个条件，
   是为了让这道门**不能在一个 401 页上意外通过**。
2. **诊断字典是急切求值的**。有一处判据写成
   `sh is not None and co is not None and …`（条件短路），
   但同一句的 `detail` 参数里直接写 `{k: co.get(k) …}` ——
   **live 上 `co` 是 `None`，于是整个脚本在第一个失败的剂型上崩掉**，
   而不是打出一行 FAIL。修法是 `(co or {})`。
   **这个缺陷只有 live 轮能找出来**：预检上八页都有 container 组，`co` 从来不是 `None`。

---

## 五、帧（`docs/batchH8b-shots/`）

15 张，**before 7 / after 8**。它们按**会话**排序（主题由请求头切换，每换一次边＝重建一次浏览器上下文），
名字自带配对，读的时候左右并排看。

| 对 | live 2.10.73 | preflight 2.10.75 |
|---|---|---|
| `{before,after}-powder-shape` | `Shape:` Bone / Round / Square / Heart / Star / Paw / Cylinder | `Appearance:` Fine Powder / Granules / Microencapsulated |
| `{before,after}-drops-shape` | 同上八个软咀嚼形状 | `Appearance:` Clear / Light Yellow / Amber |
| `{before,after}-pastes-shape` | 同上 | `Texture:` Smooth Paste / Thick Paste / Squeezable Gel |
| `{before,after}-fishoil-shape` | 同上 | `Form:` Softgel / Liquid Oil / Pump Bottle |
| `{before,after}-powder-group` | 整列参数里**没有** Container Type | 末组 `Container Type`（Jar / Foil Pouch / Stand-up Pouch / Custom） |
| `{before,after}-record-container` | `Round / Square / Oval / Jar / Pouch / Tube / Custom` | 软咀嚼的 packaging 池，左侧 meta 行**仍是** `Round` |
| `{before,after}-chews-group` | 五组 | 六组（多出 container） |
| `after-chews-config-375` | —— | 手机断点整列 |

每张都在**非平帧**（≥9 种颜色）检查通过后才报告；一张只有一种颜色的裁图是**抓失败**，不是发现。

### 5.1 一个比断言更硬的事实：before 那四张是**同一张图**

`before-powder-shape` / `before-drops-shape` / `before-pastes-shape` / `before-fishoil-shape`
分别取自**四个不同剂型**的页面，实测：

```
4 张 before-*-shape 的独立 md5 数量 = 1   ← 逐字节相同
4 张 after-*-shape  的独立 md5 数量 = 4   ← 四张各不相同
```

**这是本批的病灶与药效同时被截图钉住**：live 上四个剂型画的是**同一张图**
（同一句 `Shape:`、同八个软咀嚼名字，连渲染字节都一样），
preflight 上它们成了四句不同的话。任何计数断言都只是这句话的转述。

`after-powder-shape` 实测渲染为 `Appearance:` **Fine Powder / Granules / Microencapsulated / Custom**；
`before-powder-shape`（同一页、同一选择器、同一宽度）为 `Shape:` **Bone / Round / Square / Heart / Star / Paw / Cylinder / Custom**。
`after-powder-group` 里 `Piece Weight → Appearance → Container Type(Jar / Foil Pouch / Stand-up Pouch)` 三组连排，
而 `before-powder-group` 整列**没有 Container Type 这一组**。

---

## 六、待办 & 约束遵守情况

| 约束 | 遵守 |
|---|---|
| 不引入 ACF / JS 库 / CSS 框架 | ✅ 只改 PHP 与一处版本号，零新增依赖 |
| 不碰数据（post meta） | ✅ 未写任何 option / meta；post 158 的 `Round` 是**报告**给用户 |
| dev 站带凭据访问 | ✅ Basic Auth 常驻；预检走 `X-SF-Preflight: 1` |
| 先扫描 → 报告 → 停下等确认 → 实施 | ✅ `docs/batch2d-stepH8b-scan.md` 提交在前，四条裁决到手后才动代码 |
| 每批完成 commit ＋ push | ✅ `1234492`（本档与门/E2E/帧在第二个提交） |
| 不 pull 到 dev | ✅ 未 pull，dev 仍 `2.10.73` |
| 生产上线 | ❌ 不在本指令范围，等用户单独授权 |

### 交给用户的

1. **post 158 的 `sf_formula_container = "Round"`** —— 后台重存一次即落进新词表（§0.3）。
2. **Shape(8) / Container(7) 图库仍未传图** —— 本批已把「图片按标签匹配」的路留好，传图即生效。
3. 预测检副本 `79ec18e1…` 与本次的 `1234492…` 的**删／留**仍待裁决。
4. **批 3：待办21「Services 4 详情页」**（先扫描、报告、停下等确认）。

---

*本档由 `tools/b2d_h7_gate.py --batch h8b`（`_backup/b2d-h8b-gate.json`、`-gate-source.json`）、
`tools/b2d_h8b_e2e.py`（`/tmp/h8b-e2e-pre.json`、`/tmp/h8b-e2e-live.json`）、
`tools/b2d_h8b_shots.py`（`docs/batchH8b-shots/`）与 `tools/b2d_h8b_pool_check.php` 的证据写成。*
