# Batch H8b — 待办24「Shape / Container 按剂型差异化」· 只读扫描（未实施）

> **写给谁看**：本档是**扫描报告**，不是实施记录。按用户原话，批 2 的流程是 **先扫描现状 → 报告 → 停下 → 等确认再实施**。本档写完就停。
> 扫描日期 2026-09-23。读的都是 dev 站（live `2.10.73`）与工作区源码；**未改任何文件、未改任何数据、未 pull**。

---

## 一、一句话结论

**Shape 组的前端和后台读的根本不是同一个源**：后台编辑页的 Shape 字段**已经**按剂型给选项（`pool => 'shape'`，例如粉末页给 Fine Powder / Granules / Microencapsulated），而**前端详情页所有剂型都渲染同一套 8 个软咀嚼形状**（Bone / Round / Square / Heart / Star / Paw / Cylinder / Custom）。

⇒ 后果有两个方向，都很具体：

1. **页面上出现了该剂型不可能有的选项**：`/formulas/probiotic-powder/`（粉末）今天让客户选 **Bone（骨头）** 和 **Paw（爪印）**；`/formulas/liquid-joint-support/`（液体）也一样。
2. **销售在后台能选的答案，页面上根本没有**：粉末的 "Microencapsulated"、膏剂的 "Thick Paste"、鱼油的 "Softgel" —— 编辑选了它，前端仍然只画那 8 个骨头形状，客户无法选到。

⚠️ 这不是"缺一个功能"，是**同一份数据的两个消费者已经分叉**。

---

## 二、实测现状

### 2.1 数据面（dev 库）

- 配方记录 **21 条**，剂型 8 个：`soft-chews 4 / tablets 3 / dental-chews 3 / powders 3 / pastes 2 / drops 2 / liquids 2 / fish-oil 2`。
- `sf_formula_shape` 有值的记录：**只有 post 158 = `Custom`**（其余 20 条为 NULL）。
- `sf_formula_container` 有值的记录：**只有 post 158 = `Round`**。
- `wp_options` 里 **`sf_shapes` 与 `sf_containers` 两条都不存在** ⇒ 两个库都在**出厂默认**上跑（8 个形状 / 7 个容器），也就是「Shape(8)/Container(7) 图库待传图」这个待办还完全没动过。

### 2.2 渲染面（逐剂型实抓，一剂型一条）

| 剂型 | 抓的页 | 今天的 shape 选项（8 个，全剂型相同） | 组名 |
|---|---|---|---|
| soft-chews | joint-support-soft-chews | Bone, Round, Square, Heart, Star, Paw, Cylinder, Custom | Shape |
| tablets | joint-support-tablets | 同上 8 个 | Shape |
| dental-chews | plaque-control-dental-chews | 同上 8 个 | Shape |
| powders | probiotic-powder | 同上 8 个 | Shape |
| pastes | hairball-remedy-paste / nutrition-paste | 同上 8 个 | Shape |
| drops | ear-care-drops | 同上 8 个 | Shape |
| liquids | liquid-joint-support | 同上 8 个 | Shape |
| fish-oil | wild-alaskan-salmon-oil | 同上 8 个 | Shape |

- **shape 组出现在 42 页**（21 条 × 中英两版）；**container 组只出现在 2 页**（只有 post 158 有 `sf_formula_container`，而该组有一段「记录没值就不渲染」的门）。
- 选项**没有任何一个被预选中**（标记里没有 `checked`）——记录自己的值只喂**组名右边那行 meta**，不预选。

### 2.3 代码面：三个消费者

| 消费者 | 位置 | Shape 的选项来自 | Container 的选项来自 |
|---|---|---|---|
| **后台编辑页** | `inc/formula-admin.php:98` | `'pool' => 'shape'` ⇒ **按剂型**（`sf_formula_field_pool($form,'shape')`） | `:138` `'pool' => '_containers'` ⇒ **全局库**（`sf_container_options()`） |
| **前端详情页** | `functions.php:2305-2380` | `sf_shape_library()` ⇒ **全局库** | `sf_container_library()` ⇒ **全局库** |
| **询盘端点** | `functions.php:2463` `sinofresh_formula_config_rows()` | 不自己维护白名单，**读的是前端那份组** ⇒ 改前端即自动跟随 | 同左 |

⇒ **Shape 是唯一一个"后台按剂型、前端按全局"的组**。其余所有组（flavor / weight / pack / species / stage / pricing）前端读的都是**记录自己的值**，只有 shape 与 container 两个组用"库"。

---

## 三、现成的、已经有人写好并按剂型分好的数据

`inc/formula-pools.php` 里 `sf_formula_pools()` **早就有** `shape` 与 `packaging` 两维，且**逐剂型列好了**（H1 批从 8 个剂型页的配置器逐字抄下来，2026-09-21 冻结）：

| 剂型 | **shape** 池（今天后台就在用） | n | shape 的**组名**（池里也定好了） | **packaging** 池 |
|---|---|---|---|---|
| soft-chews | Bone, Round, Square, Heart, Star, Paw, Cylinder, Custom | 8 | Shape | Aluminum Stand-up Pouch, Aluminum Foil Pouch with Zipper, Plastic Bottle, Jar, Blister Pack, Box + Foil, Custom |
| tablets | Round, Oval, Square, Bone, Custom | 5 | Shape | Plastic Bottle, Jar, Blister Pack, Foil Pouch, Custom |
| dental-chews | Bone, Stick, Round, Spiral, Toothbrush, Custom | 6 | Shape | Foil Pouch, Stand-up Pouch, Box, Custom |
| pastes | Smooth Paste, Thick Paste, Squeezable Gel, Custom | 4 | **Texture** | Plastic Tube, Metal Tube, Aluminum Tube, Custom |
| powders | Fine Powder, Granules, Microencapsulated, Custom | 4 | **Appearance** | Jar, Foil Pouch, Stand-up Pouch, Custom |
| drops | Clear, Light Yellow, Amber, Custom | 4 | **Appearance** | Dropper Bottle, Glass Bottle, Plastic Bottle, Custom |
| liquids | Clear, Light Color, Suspension, Custom | 4 | **Appearance** | Plastic Bottle, Glass Bottle, Bottle with Cup, Custom |
| fish-oil | Softgel, Liquid Oil, Pump Bottle, Custom | 4 | **Form** | Plastic Bottle, Glass Bottle, Pump Bottle, Custom |

**三条要点**：

1. **软咀嚼今天"看起来是对的"纯属巧合**——全局库的 8 个正好等于软咀嚼池的 8 个（连顺序都一样）。
2. **组名也要跟着变**：池里已经规定粉末/滴剂/液体叫 **Appearance**、膏剂叫 **Texture**、鱼油叫 **Form**。今天这 5 个剂型的页面上都写着 **Shape**，与池的定义不符。
3. 每个池的最后一个值都是 **Custom** ⇒ 与批 H8a 刚做的"每组末尾一律追加 Custom（`custom` 标记 → 会开输入框）"**天然对得上**，不需要为它加特例。

---

## 四、Container 是另一回事：两个词表指向不同的东西

`packaging` 池（逐剂型）与全局 `sf_container_library()`（7 项：**Round, Square, Oval, Jar, Pouch, Tube, Custom**）**不是同一套词汇**：

- 全局库里的 **Round / Square / Oval 是"瓶型"**，语义上更像 shape，不像"容器类型"；
- `packaging` 池里的是**真的容器**：Dropper Bottle / Glass Bottle / Pump Bottle / Metal Tube / Aluminum Stand-up Pouch / Blister Pack…

而且 post 158 存的是 `sf_formula_container = "Round"` —— **一条数据把"Round（圆瓶）"填进了"Container Type"**，正好落在这个歧义上。

⇒ Container 这一半**不能只照抄 Shape 的做法**，需要你在下面两条里裁决一条。

---

## 五、需要你裁决的四件事

### 问题 1：Shape 的选项源（推荐 A）

- **A（推荐）**：前端改读 `sf_formula_field_pool($form,'shape')`，与后台**同源**。图库仍留着做**图片载体**：池里某个标签与图库标签同名（如软咀嚼的 Bone/Round/Square/Star/Paw/Cylinder、片剂的 Bone/Round/Square）就自动用那张图，不同名（粉末的 Fine Powder 等）就走今天已有的"虚线空槽 + 名称"占位。**今天 8 张图一张都没传，所以视觉上零变化**，但你以后传图的路没有断。
- **B**：前端继续用全局 8 个库，只按剂型**过滤**掉不该出现的。问题：**过滤不出**"Fine Powder / Microencapsulated / Clear / Softgel / Thick Paste"——粉末页会只剩 Round/Bone/Custom 之类，等于把池里 4 个正确答案丢掉 3 个。**不推荐**。
- **C**：Shape 与 Container 都改成"记录自己声明"（像 flavor/pack 那样）。问题：Shape 是**目录级**的选择（H7g 已按你的裁决定成"不等记录、全页常显"），改成记录声明会把 21 页里 20 页的 shape 组**整组删掉**（都没值）——与 H7g 的裁决直接冲突。**不推荐**。

### 问题 2：Container 走哪条

- **A（推荐）**：与 Shape 对称——Container 改读**同剂型的 `packaging` 池**，组名仍叫 Container Type。数据上意味着 post 158 的 `"Round"` 不再属于任何池 ⇒ meta 行按已有的兜底打印原文 `Round`（`sinofresh_container_label()` 本来就这么兜底），页面上不预选任何项，**不报错、不丢行**，销售后台重新存一次就会落进新词表。副作用：7 张"容器图库"从此闲置（反正是空的）。
- **B**：Container 保持全局库，只按剂型做一张**新的**映射表（哪个剂型允许 Round/Square/Oval/Jar/Pouch/Tube）。工作量更大，且"粉末的容器是 Round？"这个问题本身没答案。
- **C**：Container 先不动，本批只做 Shape（并把 container 的 7 项留给以后的"容器图库"批）。

### 问题 3：组名要不要一起按剂型改

池里已经定好：粉末/滴剂/液体 = **Appearance**、膏剂 = **Texture**、鱼油 = **Form**、软咀嚼/片剂/洁齿 = **Shape**。
- **改（推荐）**：与池一致，一步到位；"粉末的 Appearance：Fine Powder / Granules / Microencapsulated" 读起来是对的。
- **不改**：全部仍叫 Shape，但"Shape: Fine Powder"读起来别扭。

### 问题 4：Container 组的"记录没值就不渲染"这条门，要不要顺势撤掉

今天 Container 只在 post 158 出现（2 页）。若改读 `packaging` 池，选项不再依赖记录 ⇒ 是否改成**像 Shape 一样全页常显**（会从 2 页变成 42 页）？还是**保持这条门**（仍在 1 条记录上出现）？

---

## 六、改动面（确认后才动，这里只登记）

| 文件 | 位置 | 预期 |
|---|---|---|
| `sinofresh-theme/functions.php` | `sinofresh_formula_config_groups()` 的 shape 段（2305-2346） | 选项源换成逐剂型池；组名换成池给的 label；图库降级为"同名才供图" |
| 同上 | container 段（2348-2380） | 取决于问题 2/4 |
| `sinofresh-theme/style.css` | `style.css` 头部 `Version:` | `2.10.74 → 2.10.75` |
| `sinofresh-theme/functions.php` | enqueue 的 style 版本 | 同上，两处同步 |
| `tools/b2d_h7_gate.py` | 新增 `BATCHES['h8b']` | 主证/applies 要按**逐剂型**的选项数逐条算（8 个剂型各自不同，不能用"全站一个数"） |
| 新 `tools/b2d_h8b_e2e.py` | — | 断言必须**按剂型分档**（同一批断言跨 8 个剂型会重犯"抄断言丢作用域"） |

**版本号**：本批只动 PHP（若问题 3 选"改"，则不涉及 CSS/JS）⇒ **只 bump style 版本**；`config.js` 不需要动（rails/箭头/Custom 输入框都是通用的，与选项来自哪个池无关）。**这一点要在实施时再核一遍**：若 group 的选项数从 8 掉到 4，手机上 shape 行可能不再溢出 ⇒ **横滑箭头会自动消失**（`config.js` 的 `sync()` 本来就这么判），这是正确行为，但 E2E 今天有一条"shape 行比它自己的盒子宽"的断言，**它会因此变红**——那是断言需要按剂型重写，不是产品缺陷。

---

## 七、顺带发现（**不在本批范围**，只登记）

1. **"Piece Weight" 组名也不按剂型变**：`functions.php:2244` 写死 `'label' => 'Piece Weight'`，而池里为膏剂定的组名是 **Tube Weight**、粉末/液体是 **Serving Size**、滴剂是 **Bottle Size**、鱼油是 **Omega-3 per Unit**。页面上 8 个剂型今天全写 "Piece Weight"。是否并入本批，请示下（我倾向**不并入**：本批是 24 号待办，改这个要另开一条待办并单独过门）。
2. **两处注释与代码不符**（文档缺陷，非产品缺陷，实施时顺手修）：
   - `inc/formula-admin.php:617-619` 说 Shape 的 slug 是永久的、因为"PDF 端点按它们校验"——实测 `inc/config-pdf.php` **完全不读** shape/container（端点的白名单由 `sinofresh_formula_config_rows()` 从页面自己的组推出，不引用 slug 名）。结论不变，但理由写得过时了。
   - `functions.php:2348-2352` 说 Container 的记录值给了"the meta line **and the initial radio**"——实测**没有任何项被预选**（标记里无 `checked`）。只有 meta 行是真的。

---

## 八、扫描期遵守的约束

- ✅ 只读：**未改任何文件、未改任何 post meta、未改任何 option**；**未 pull**；生产站零接触。
- ✅ dev 抓取带 Basic 凭据，逐条 `sleep ≥1.2s`（避免 CF 403 把空体当证据）。
- 本档即报告；**等你对第五节四个问题给出裁决后再实施**。
