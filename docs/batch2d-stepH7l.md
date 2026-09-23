# Batch H7l — 价格阶梯移到简介下 ＋ 认证带六枚卡片（第一批收尾 · 4 项修补里的第 2、4 项）（2026-09-23）

> 版本 **2.10.73**。产品提交 `79ec18e`（本批唯一一次代码改动）。
> 门：`tools/b2d_h7_gate.py --batch h7l` → `_backup/b2d-h7l-gate.{json,log}` 与 `…-gate-source.{json,log}`。
> E2E：`tools/b2d_h7l_e2e.py` → `_backup/b2d-h7l-e2e-{pre,live}.json`。
> 上线后验收：`tools/b2d_h7l_live_accept.py --frames` → `_backup/b2d-h7l-live-accept.{json,log}`。
> 帧：`tools/b2d_h7l_shots.py` → `docs/batchH7l-shots/`（**12 张，含 2 张 before**）
> ＋ `docs/batchH7l-live-shots/`（**8 张 live 帧**）。

## 〇、本批最重要的事：四项报障里只有两项是真缺陷

用户报了 4 项、并要求**先扫描再执行**。扫描的结论是：**第 1、3 项已经在 live 上达标，且不是这次改出来的**，第 2、4 项是真缺陷。四份证据如下。

### 0.1 第 1 项（价格区间文字）—— **部署滞后窗口**，不是数据问题也不是代码问题

用户截图上三行都是 `○ Custom quantity　USD 3.88 / unit`（3.88／3.58／3.28）。三方取证把它钉死成一个**时序**问题：

| 证据 | 实测 |
|---|---|
| dev 库的 post 158 `sf_formula_price_tiers` | **正确的三档** `[{min:10,max:99,price:3.88}, {min:100,max:999,price:3.58}, {min:1000,max:null,price:3.28}]` —— 数据本来是好的 |
| live HTML（不带预检头，curl） | 三档渲染为 `US$3.88 / 10-99 / pieces`、`US$3.58 / 100-999`、`US$3.28 / ≥1,000`；`Custom quantity` **0 次** |
| `git log -S"Custom quantity"` | 该兜底串只在 `functions.php` 一处（现行码里 `Custom quantity` 仍是**合法的**兜底，只是没有记录走到它） |
| 代码史 | `967d252`（H7i，2.10.70）把读取器从只认 `qty` 键改成认 `min/max` |

⇒ 用户截图的那一刻，**dev 的 checkout 还停在 2.10.69**（旧读取器只认 `qty`），而 H7i 已经把 meta 写成 `min/max`，于是三行**全部落进兜底**并打出旧币种格式 `USD n / unit`；`2.10.72` 上线后读码与数据一致，现象消失。截图与「2.10.69 读 2.10.70 的数据」逐字吻合。

**本批结论：不动。** 不改数据（用户明示不碰 post meta），不改代码（改了就破坏兜底）。

### 0.2 第 3 项（底部按钮）—— **已经是 Send Inquiry**

live HTML 实测：`<a class="sf-fdetail2__cta" href="/contact/#quote" data-sf-inquiry-open>Send Inquiry</a>`。
`Request Sample` 在整页里**只出现在一段 HTML 注释内**（原始字节 1 次，**去掉注释后 0 次**）。
`data-sf-inquiry-open` 在详情页 4 次命中 = **3 处真载体**（样品行的 `sf-fdetail-config__sample-cta`、栏底的 `sf-fdetail2__cta`、悬浮的 `sf-float-btn--inquiry`）＋ 1 处在注释里（那处注释正是上一批留下的说明）。

**本批结论：不动。** H4e 那一批已经做完了。

### 0.3 第 2 项（待办25）与第 4 项（待办4）—— 真缺陷，见 §一

| | 实测（live 2.10.72） |
|---|---|
| 右栏 DOM 顺序 | `h1(index 198) → intro → Flavor(202) → weight → pack → Shape → Container → **pricing(350)** → 参数表 → CTA` |
| 屏幕位置 | intro `top 510.4` < Flavor `678.4` < **pricing `1653.1`** ⇒ 价格在折叠线以下 974px 处 |
| 认证带 | `.sf-certstrip__row` 3 列、`gap: 10px 20px`、图标 `32×32`、**无卡片**（背景透明、边框 0、圆角 0、内边距 0），带高 **155.4px** |

## 一、两项实现

**待办25 — 价格阶梯移到简介下方。** `functions.php` 里 `$groups[] = array('key'=>'pricing'…)` 改为
`array_unshift($groups, …)`。**同一个组、只是换了位置**，所以弹窗的重印、折叠摘要、无 JS 降级三条消费路径
**全部自动跟随**，没有一处需要同时改。pricing 组只在真正有阶梯的那一条记录上生成（全站 21 个配方里**只有 post 158 有** `sf_formula_price_tiers`），所以 `applied` 只有 **2**（英文页 ＋ zh 孪生页）。

**待办4 — 认证带六枚 chip 改六张小卡片。** 纯 CSS：`.sf-certstrip__row` 间距 `10px 20px` → `16px`；
`.sf-certstrip__badge` 加 Mist 底 ＋ Line 发丝边 ＋ `8px` 圆角 ＋ `16px` 内边距 ＋ `gap 12px`；
`.sf-certstrip__icon` `32×32` → `40×40`；断点由 `≤768` 步改为 `≤1024`（**平板 2 列**），`≤420` **保留 2 列**（用户裁决：手机端不要 1 列），只把 icon 收到 `32px`、内边距 `12px`、间距 `12px`。

### 一·一、一个二阶效应（本批主动识别、并写进断言）

移动端的折叠是 **位置性** 的：`config.js` 在列表后插按钮，CSS 隐藏 `.sf-fdetail-config__group:nth-child(n + 4)`。
把价格组移到首位之后，**折叠摘要从「Flavor / Piece Weight / Pack Size」变成「Quantity & Pricing / Flavor / Piece Weight」**
—— 价格进了摘要。这正是 brief 想要的方向（手机上一眼先看到价），但它**不是**「移动」的字面推论，所以单列一条断言守住它（live 上该断言红：`pricing: 'none'`）。

## 二、改动清单

| 文件 | 改 |
|---|---|
| `functions.php` | `$groups[] =` → `array_unshift($groups, …)`（第 2321 行附近，含说明为何不是「第二个渲染器」的注释）；`wp_enqueue_style(…, '2.10.73')` |
| `style.css` | `Version: 2.10.73`；`.sf-certstrip__row` gap 16px；`.sf-certstrip__badge` 卡片化；`.sf-certstrip__icon` 40px；断点 `768` → `1024`；`420` 段改为 2 列 ＋ 收窄 |
| `tools/b2d_h7_gate.py` | 新增 `BATCHES['h7l']`（含 `_h7l_move` 的 `place`/`drop`/`copy` 三个破坏旋钮） |
| `tools/b2d_h7l_e2e.py` | 新增（60 项） |
| `tools/b2d_h7l_shots.py` | 新增（12 帧，两段会话：live before ＋ preflight after） |

**本批零模板改动、零新文件到主题、零 CSS 之外的运行时改动。** 全站 42 个详情页的 HTML 只在 pricing 组存在的那 2 页上不同。

## 三、门（`tools/b2d_h7_gate.py --batch h7l`）

基线 = `_backup/b2d-h7l-baselines`（**live，无预检头**，即 dev 自己服务的 2.10.72）；
候选 = `_backup/b2d-h7l-candidates` 与 `-candidates-aa`（**带 `X-SF-Preflight: 1`**，2.10.73）。

**基线的忠实性先被独立证明过**：`_backup/b2d-h7l-baselines`（无头）与 `_backup/b2d-h7k-candidates`（带预检头、2.10.72）**掩码后 75/75 零差异** —— 同一份主题经两条路由取回是同一份字节，所以「基线是旧版」这件事本身是可证的，不是假设。

- A/A：**PASS**（75 页、**0 差异**）。
- 主证 `mask(transform(baseline)) == mask(candidate)`：**PASS**，75 页比对、**0 页差异**、**applied 2/2**（`applied_base = 0`，`mode: insert`）。
- coverage **16 行全 ok**；invariants **26 行全 ok**；掩码回读 **PASS**（23 页 blob、46 项二进制回读、0 处不等）。
- 矩阵 **8 个突变体全部 caught，无一 no-op**：

  | 突变体 | 结果 | 差异页 | applied |
  |---|---|---|---|
  | tokens 未折叠 | caught | 75 | 2/2 |
  | 阶梯**留在原地**（不移动） | caught | 2 | 0/0 |
  | 阶梯移到 Flavor **之后**（而不是之前） | caught | 2 | 2/2 |
  | 同上但确认「second ≠ 本批」 | caught | 2 | 2/2 |
  | 阶梯**复制**到头部、原处**也保留** | caught | 2 | 2/2 |
  | 阶梯**删除**而不是移动 | caught | 2 | 2/2 |
  | 轮次少声明一次 | caught | 0 | 2/**1** |
  | 完全不施加 | caught | 2 | 0/0 |

- 负对照：**21 条全 ok**（NC1–NC8 ＋ NC-src 6 ＋ NC-page 3 ＋ NC13–NC16），其中 NC13 两半都真的触发：`page=formulas__joint-support-soft-chews.html main_red=True coverage_red=True`。
- source 段（**独立跑一次**，`--source` 是 `if/else` 分支不是叠加）：**24/24 PASS，exit 0**。

### 三·一、本批为门新增的东西

1. **`_h7l_move` 的三个破坏旋钮**（`place='head'|'second'|'tail'`、`drop`、`copy`）—— 「移动」这一类编辑的**反向**形态不止一种：留在原地、移到别处、复制一份、直接删掉。前三种在旧的 `insert` 声明里都是 `applied=0/0` 或字节相同，**只有把四种都做成突变体**才能证明主证区分得出「移动」和「复制」「删除」。
2. **`copy` 旋钮的第一版是错的（假阴性）**：我把「复制」实现成「先删后插同一串」，而那**恰好就是本批本身**（head 分支），于是突变体输出与本批逐字节相同、门打印 `PASSED / the gate let this through`。改成「在头部多写一份、**原处保留**」才是真的复制。**教训：突变体必须与「本批的正确产出」在某些字节上不同，否则它测的是本批自己。**

### 三·二、三条声明是**断言**错，不是产品错（逐条从源码/几何证明后重构）

| # | 原声明 | 实测 | 结论 |
|---|---|---|---|
| 1 | `the flavor group` 应在 **42** 页 | base = **2** | flavor 是 meta 驱动的（与 shape/container 同族，销售填了才有）；**产品对**。改 `want=None`（只比 base==cand） |
| 2 | `the container group` 应在 **42** 页 | base = **2** | 同上 |
| 3 | `the column still ends on its inquiry button`（用英文 `H7L_CTA` 找） | zh 页 `find = -1` | zh 页的 href 是 `/zh/contact/#quote`。改用**与语种无关**的标记 `data-sf-inquiry-open>Send Inquiry</a>` |
| 4 | NC-src 的针 `.sf-certstrip__row {\n\t\tgap: 12px;\n\t}` 紧贴断点行 | 断点与规则之间夹着 3 行注释 ⇒ **针不在 style.css 里** | 控制「开不了火」不是判据不能失败。改为**锚在规则本身**（不含断点行） |
| 5 | NC-page「一个换行不再是换行」`sf-tier__dot` → `sf-tier__dots` | 计数**不变** ⇒ 控制未触发 | `sf-tier__dots` 仍**含子串** `sf-tier__dot`。换掉：新增「带里多出第七张卡」与「一条记录少一个参数组」两条页控制 |
| 6 | 源码 420 断点那条 `[\s\S]{0,260}` | 注释 ~380 字符 ⇒ x0 FAIL | 放宽到 `0,520`（**只**用于「锚在规则」这类断言，且该断言另有一条 `css_live` 缺席断言配对） |

**这些声明错与产品无关，全部都改回「断言更严 / 更贴机制」而不是改松。**

### 三·三、旧批的 `--source` 为什么常红（本批实测确认）

`--source` 是**时点记录**：它读的是「此刻工作区的源码」，因此**必然**随版本号前进而失效。本批用 h7c／h7g／h7h 三条实测确认它们今天都是红的（版本字面量变了），**这不是回归**。所以门纪律只能是「**本批只跑自己的 `--source`**」，不能跨批回归。

## 四、E2E（`tools/b2d_h7l_e2e.py`）

两跑，两个 JSON，两条不同的问题：

| 跑 | 命令 | 结果 | 这一跑在回答什么 |
|---|---|---|---|
| 预检 | `tools/b2d_h7l_e2e.py` | **60/60，exit 0** | 2.10.73 是否把两项都做到了 |
| live | `tools/b2d_h7l_e2e.py --live` | **46/60，14 红，exit 1** | 脚本**能不能红**；以及第 1、3 项是否本来就达标 |

**每次开页都先断言是哪一份资源在应答**（`served()`：`ver` ＋ 是否 `-preflight` ＋ `h1==1`），再断言别的。预检跑里每条 `served()` 都是 `themes/sinofresh-theme-preflight/style.css?ver=2.10.73`；live 跑里都是 `themes/sinofresh-theme/style.css?ver=2.10.72`。

**live 的 14 条红，全部落在两项新工作上，且都能指出它读到的旧形态**：

| 落在 | 条数 | 例 |
|---|---|---|
| 待办4 | 8 | `cardBg: rgba(0,0,0,0)`、`cardBorderW: 0px`、`cardRadius: 0px`、`cardPad: 0px`、`iconW: 32px`、`gap: 10px 20px` |
| 待办25 | 5 | `pricing 主序 350 > flavor 202`；屏幕 `pricing 1653.1 > flavor 678.4`；折叠摘要里 `pricing: 'none'`；zh 孪生页同 |
| 待办1 | 1 | `the three breaks are painted at 375 too` → `w:0, h:0`（**是待办25 的后果**：live 上价格组是第 6 组、被折叠隐藏，所以它在 375 下**根本没有盒子**；移上去之后它进了摘要，这条才变绿） |

**待办1 与待办2 的 24 条在 live 上全绿** —— 这就是 §〇.1／§〇.2 的报告证据：它们**在 live 上已经是达标的**，红的只有这次要动的两项。

### 四·一、一条**指错了元素**的断言（同类错第三次，已重构）

门与 E2E 首次全跑后，唯一一条红是
`待办25 ...and its 32px bold price | {'size': '17px', 'weight': '700'}`。

按纪律先判「断言错还是产品错」，从源码证明：

- `.sf-tier__price` 在 style.css 里是 **`font-size: 17px; font-weight: 700`**（`≤480` 步 `16px`），
  并且 `git log -S"sf-tier__price"` 显示它**自 `967d252`（H7i）引入以来只有 17px 过一个值** —— **从来没有 32px**。
- 那一栏里唯一 32px／700 的元素是 **`.sf-fdetail2__title`**，也就是右栏自己的 h1（`style.css:8580`），
  它就坐在价格组**上方**、本批一个字节都没动。

⇒ brief 的原话是「**保留**样式（三档横排、32px 加粗）」，「三档横排」说的是阶梯，「32px 加粗」是阶梯上方那个栏标题；
我把它读成了阶梯自己的价格，因为 **`.sf-tier__price` 是名字里带 "price" 的第一个元素**。
**产品是对的，断言错了。**

重构（不是放宽）成两条，各自点名自己那个元素，并把两个数字都留在日志里：

```
待办25 the column's 32px bold title survives the move   -> {size: '32px', weight: '700', text: 'Joint Support Soft Chews'}
待办25 ...and the ladder's own price keeps the voice H7i gave it -> {size: '17px', weight: '700'}
待办25 the ladder's phone step is still the inherited 16px -> {size: '16px', weight: '700'}
待办25 the column title keeps its 26px phone step        -> {size: '26px'}
```

这四条在 **live 跑里也全绿**（同一组数字）—— 于是「移动没有顺手动样式」这件事是由**两份独立测量给出同一个值**来证的，而不是靠一个硬编码数字。

> ⛔ 这是「断言指错了对象／范围」这一族错在本项目**第三次**出现。登记为复发项：
> **凡判据里出现某个尺寸，先问「这个元素是不是那个尺寸的载体」，不要从名字猜。**
> 族谱：① H7k `secBox`（量的是「改动过的东西恰好住着的容器」）；② H7k「其余大区块都 48px」（把例外当全体）；③ 本条。

## 五、几何实测

| 量 | live 2.10.72（before） | preflight 2.10.73（after） | 差 |
|---|---|---|---|
| 认证带 `.sf-certstrip` @1440 | **155.4px** | **245.4px** | +90.0 |
| @768 | 193.6px | **331.6px** | +138.0 |
| @375 | 221.3px | **324.9px** | +103.6 |
| 右栏价格组 `top`（同页 intro 恒定 510.4） | **1653.1** | **678.4** | 上移 **974.7** |

被标记的那一列（价格组）在移动前后**都是 472×1752**（帧 `-00` vs `-01` 同尺寸）—— 位置变、高度不变。

**带高为什么不是 brief 的「约 200px」**：卡片高 = `16 + 40 + 16 = 72`（图标 40 是行高的下限，文字只有 1 行），两行 = `72×2 + 16 = 160`，再加 lede `23.8` ＋ 两个 ~`20` 的间隙 ＋ more `17` ≈ **245**。
要压到 ~200 必须**破掉 brief 自己给的某一条**（内边距 16 → ~8，或图标 40 → ~28）。**本批按 brief 的字面值执行**，把这个 45px 的超出如实报出来，改法留给用户裁决。

**列数与宽度的实测**（用**不同 left/top 的个数**数行列，而不是读 `grid-template-columns` —— 一个全折进单列的 grid 与一个填满三列的 grid，声明是一样的）：

| 宽度 | 列 | 行 | 卡片宽 | 图标 | 内边距 | 间距 |
|---|---|---|---|---|---|---|
| 1440 | 3 | 2 | 389.3 | 40×40 | 16px | 16px |
| 768 | 2 | 3 | 338.0 | 40×40 | 16px | 16px |
| 375 | **2**（用户裁决，不堆叠） | 3 | 299.0 | **32×32** | **12px** | **12px** |

图标在卡片上的**中线偏差 0.0px**（`icon_cy 2897.2 == card_cy 2897.2`）。

## 六、帧（`docs/batchH7l-shots/`，12 张，全部 non-flat 已验）

| 帧 | 说明 |
|---|---|
| **00** | **before**：live 2.10.72 的右栏 —— 价格阶梯在**最底下**（Container 之后） |
| **00b** | **before**：live 2.10.72 的认证带 —— 透明底的 3×2 扁条 |
| 01 | after：同一右栏 —— 阶梯紧跟简介 |
| 02 | after：阶梯特写（三档 ＋ 价格在**第一行** ＋ 样品行） |
| 03 | after：栏底按钮 `Send Inquiry` |
| 04 | after：375 下的折叠摘要（**阶梯在摘要里**） |
| 05 / 06 / 07 | after：认证卡片 1440（3 列）/ 768（2 列）/ 375（2 列） |
| 08 | after：单卡特写（Mist 底 ＋ 发丝边 ＋ 8px 圆角 ＋ 40px 图标） |
| 09 | after：zh 孪生页认证卡片 —— **与 05 逐字节相同**（`md5 b263b021…`）：这条带是**语种无关**的，lede 与六个名字在 zh 页上也是英文，所以它不是一份独立佐证，而是「没被翻译」这件事的证据 |
| 10 | after：zh 孪生页右栏（阶梯同样在简介下） |

上线后同一套画面在 live 路由上又拍了一遍（`docs/batchH7l-live-shots/`，8 张，与上表有对应关系的 8 张**逐字节相同**），见 §九.3。

## 七、工具链踩坑（本批实测）

- ⛔ **拍帧脚本必须用带 Pillow 的解释器**：`/Users/meng/.workbuddy/binaries/python/versions/3.13.12/bin/python3` **没有 PIL**，会 `ModuleNotFoundError`（在 `import` 那一行就死，看起来像脚本没写完）。用 `~/.workbuddy/binaries/python/envs/default/bin/python`（Pillow 12.2.0）。跑 E2E 用前者、拍帧用后者，本批就是这么分工的。
- ⛔ **`agent-browser` 的 `set headers` 按 origin 生效**，所以 before/after 两段必须是**两段会话**（`close --all` → `open` → `set headers` → `reload`），且凭据必须**与自定义头同一次**设在 `set headers` 里（`set credentials` 与它互斥）。
- ⛔ **折线以下的区块在整页截图里是纯色**（`interactions.js` 的 `.sf-pending` / `opacity: 0`）。抓之前必须自上而下滚一遍再滚回顶，并**断言**留下的 `.sf-pending` 为 0；`position: fixed` 的 cookie 横幅也要先 `display:none`（它是本批没碰的全站既有覆盖层，属噪声）。

## 八、仍需用户处理／待裁决

1. **是否把 2.10.73 pull 到 dev** —— **已由用户裁决「现在 pull」并执行完毕，见 §九**。
2. **认证带高度 245.4px vs brief 的「约 200px」** —— **已由用户裁决「保持现在的 245.4px」**，不再改。
3. **预检副本 `79ec18e1…`（2.10.73）在 pull 之后就是 live 的冗余副本**：`diff -rq live主题 preflight主题` **零输出**（逐字节相同），且有对应关系的 **8 张 live 帧也与预检帧逐字节相同**（见 §九.3）。更旧的四份更加过时。**删/留仍未获授权**，登记。
4. **post 158 三处演示值**（`sf_formula_video_url` / `sf_formula_sample_price` / `sf_formula_price_tiers`）仍待销售填真数据，回滚档 `_backup/b2d-h7i-post158/before.json`；本批**不碰 post meta**。
5. **HTML 的 1 天浏览器缓存**（Apache `ExpiresDefault "access plus 1 day"` ⇒ `Cache-Control: max-age=86400`）用户选择**先不动服务器**；所以在浏览器里验收时需 `Cmd+Shift+R`（样式表 URL 带 `?ver=2.10.73` 已是新资源，不受影响）。
6. 长期未变：生产上线（`docs/dev-lockdown.md` 的 10 项移除，最易漏 `blog_public` 0→1）与 Shape(8)/Container(7) 图库待传图。

## 九、上线 dev（2026-09-23，用户授权）＋ 上线后验收

### 9.1 执行与结果

| 步 | 命令 | 结果 |
|---|---|---|
| 1 | `git push origin main` | `79ec18e..4dc3da4`；`origin/main` = `4dc3da4` |
| 2 | `ssh root@65.49.215.152` → `cd /var/www/dev.zxpet.com/site-repo` | `git fetch --prune origin` → `79ec18e..4dc3da4`；`git pull --ff-only` 快进 `63a7f1d → 4dc3da4`，无冲突 |
| 3 | `git rev-parse HEAD origin/main` | 两者同为 `4dc3da40f6bc68888b5895879060f7604fd7b56e` |
| 4 | live 主题（symlink → `site-repo/sinofresh-theme`） | `style.css` `Version: 2.10.73`；`functions.php` enqueue `'2.10.73'`；`array_unshift($groups, …)` 在 **2327** 行；`.sf-certstrip__badge` 卡片规则在 **2474** 行 |
| 5 | 权限 | `style.css` / `functions.php` 均 `644 root:root` ⇒ apache 可读，**无需改属主** |

**未做任何 dev 封锁变更**；`zz-sf-dev-lockdown.php` 与 Basic Auth 原样保留。**生产站零改动。**

### 9.2 上线后验收（`tools/b2d_h7l_live_accept.py --frames`，**不带 `X-SF-Preflight`**）

**64/64 PASS，exit 0**；帧 8 张、0 平帧 → `docs/batchH7l-live-shots/`（`_backup/b2d-h7l-live-accept.{json,log}`）。

⚠️ 这个脚本的 `served()` 门是**反的**：它必须证明答话的是
`themes/sinofresh-theme/style.css?ver=2.10.73`，并且**不是** `-preflight` 副本。
上线**前**把同一个 URL 抓下来，答的是 `themes/sinofresh-theme/style.css?ver=2.10.72`
＋ 阶梯在列底（`pricing 350 > flavor 202`）—— 所以这条门正是区分「pull 生效」与
「还在读旧字节」的那一条，其余断言都挂在它后面，且这条**失败即中止**（不记成一条红）：
一份关于错字节的报告比没有报告更糟。

| 用户要求验证 | 实测 |
|---|---|
| `themes/sinofresh-theme/style.css?ver=2.10.73` | 详情页／首页／`/zh/`／`/zh/formulas/…` 四处门全 OK（`pre: False`） |
| 待办25 价格在简介下 | DOM `intro 198 < pricing 202 < flavor 235`；屏幕 `510.4 < 678.4 < 862.2`；zh 孪生页 `200/204/237` |
| 待办25 手机折叠摘要含价格 | `/formulas/…` @375 `folded: True`、`pricing: block`、`flavor/weight: block`、`pack/shape/container: none` |
| 待办25 样式未被顺手改动 | 栏标题 `32px/700`、阶梯价 `17px/700`（↔ live 上线前**同一组数字**）；三列卡 `148.266px ×3` |
| 待办1 三档文字 | `10-99` / `100-999` / `≥1,000`；价格 `US$3.88/3.58/3.28`；`Custom quantity` **0 次**；回显行 `10-99 — US$3.88 / unit · …` |
| 待办2 Send Inquiry ＋ 弹窗 | `a.sf-fdetail2__cta`／`Send Inquiry`／`href=/contact/#quote`／`data-sf-inquiry-open`；**真点击**后弹窗 `hidden: False`、`isOpen: True`，**0.8s 后读第二遍**仍是 `isOpen: True`（同 tick 那一次读的是 `requestAnimationFrame` 之前的态，两次都记在 JSON 里）；弹窗重印三档 |
| 待办4 认证卡片 | 1440 三列两行 / 768 两列三行 / 375 **两列**三行；卡片 `Mist rgb(243,246,244)` ＋ `1px rgb(220,226,223)` ＋ `8px`；图标 `40×40`（375 步到 `32×32`）；内边距 `16px`（375 `12px`）；间距 `16px`（375 `12px`）；图标中线偏差 **0.0px / 0.05px** |
| 待办4 带高 | **245.4px**（1440）／331.6（768）／324.9（375）—— 与上线前的预检实测**逐位相同** |
| 广度 | **75 条路径全部有响应**、主题锚全部 `themes/sinofresh-theme/…?ver=2.10.73`、旧认证标记（`sf-certgrid`／`article.sf-certcard`）**0 处残留** |

**缓存无需清**：CF `cf-cache-status: DYNAMIC`（HTML 不入 CF 缓存）；样式表 URL 带 `?ver=2.10.73` 已是新资源。

### 9.3 两条路由现在渲染同一份像素

- 服务器上 `diff -rq …/themes/sinofresh-theme …/themes/sinofresh-theme-preflight` → **零输出**（逐字节相同）。
- 本地 **8/8 live 帧与预检帧 md5 相同**（`b6a6d7c2…`、`6090402f…`、`9684b9ef…`、`b263b021…`、`2075ebf7…`、`d80a11c8…`、`b263b021…`、`3a9945ad…`）。

⇒ **「pull 生效」与「预检副本已冗余」这两件事，各由一份独立证据给出**；`79ec18e1…` 现在可以删（未获授权）。

### 9.4 验收脚本里三条断言是我写错的（已重构，未放宽）

首次运行 **65 项 / 3 红**，三条全在 375 上：`待办4 the card surface … 16px`、`the icon is 40x40 …`、`the chips sit on a 16px gutter`。
实测 `cardPad 12px`／`iconW 32px`／`rowGap 12px` —— **产品的手机步是对的**。

根因：我把 E2E 的 `strip_checks` 抄进验收脚本时，**丢掉了它的按宽度作用域** ——
E2E 只对 1440 与 768 调用这套桌面令牌，375 另有一套；抄过来变成对三个宽度都调用，
于是拿桌面令牌去量一个**明写在 brief 里会变**的断点。改成把期望的 `icon/pad/gap`
**作为参数按宽度传入**（`(375, 2, 3, "32px", "12px", "12px")`）：
既是修错，也是更严的写法 —— 它要求那个步长是**具体那一个**，而不只是「不等于桌面值」。

> ⛔ **这是「断言指错了对象／范围」这一族的第四次复发。** 这回的形态是
> **「抄一套断言时丢掉它的作用域」**。登记：**凡带断点的组件，判据必须与断点一一对应，
> 不能有一套「通用值」跨宽度复用。**

