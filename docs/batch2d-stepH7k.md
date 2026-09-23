# Batch H7k — 静图成链 ＋ 角标浮层 ＋ 认证带压缩 ＋ 清单两列 ＋ Key Facts 撑满版心（第一批 · 批 D）（2026-09-23）

> 版本 **2.10.72**。产品提交 `effee83`（功能）＋ `450ba65`（修复）。基线 = `_backup/b2d-h7j-candidates-fix`（2.10.71 态）。
> 门：`tools/b2d_h7_gate.py --batch h7k`；E2E：`tools/b2d_h7k_e2e.py`；帧：`docs/batchH7k-shots/`（15 张）。

## 〇、本批最重要的事：门与 E2E 都报绿之后，出了一个真缺陷、九条断言写错

批 D 的五项里有四项是「按单条规则重建标记」的 insert 改写，门一跑就绿了**一条都不差的 163/163**。但同一次运行也把两类别的东西暴露出来：

**一个真缺陷（待办22）。** 表格的第一次改法是 `max-width: none` —— 它确实完成了待办的**字面**要求（去掉 720px 上限），却顺手把**布局自己已经加给它的那道上限**也去掉了：那个 `<section>` 是 `is-layout-constrained` 组，核心已经把它的一级块子元素压在 `--wp--style--global--content-size`（1200px）上并居中，标题实测就是 1200px、落在 1364px 的内容盒正中。`none` 把表格**拿出**了那条规则，于是它铺满整个 1364px 内容盒，两端各**超出标题 82px** —— 与「与标题两端对齐」正相反。实测 1364 vs 标题 1200，修后 1200 落在 120→1320，与标题**逐像素相同**。

**九条断言写错。** 逐条从源码/几何证明是断言错而不是产品错，再重构（不是放宽）：

| # | 原断言 | 实测 | 结论 |
|---|---|---|---|
| 1 | 静图中心 hit-test **就是**那个 `<a>` | `elementFromPoint` 返回 `<img>`，`inLink: true`，最近锚点 href = 卡片自己的路由 | 图在链内、点它就走该链。原断言在**图未加载**时反而通过（点穿透到锚点）⇒ 判据依赖图片时序。改为「点落在链内 **且** 最近锚点是该卡片自己的路由」 |
| 2 | 认证带高度 ≤ 220px（量 `secBox`） | `secBox` = 414.7px，因为该 section 里还装着 `sf-certbar`（87.3）与旧按钮（48），**本批都没碰** | 量的元素不对。改成量 `.sf-certstrip` 自身：**155.4px** |
| 3 | 其余大区块「都在 48px」 | `Insights / Latest Articles` 计算值是 32px | 它在 `(min-width: 769px)` 由**先于本批存在**的 `.sf-section:has(.sf-slot--cover)` 规则取胜，与内联 48px 无关。改为「唯一不在 48px 的那个，正是那条规则已经覆盖的那个」（并要求该例外**存在**，防止判据空过） |
| 4/5 | 同 2/3 的 `/zh/` 孪生页 | 同 | 同 |
| 6 | 五项以 `Your company name` **开头** | 实际是 `✓ Your company name …` | 标记符在最前。改为逐项去标记后**全量比对五项且按序** |
| 7 | section 高 ≤ 最高列 + 160px（299.9 vs 284.8） | 299.9 = 48 + 标题 55.1 + 间隙 24 + 列 124.8 + 48 | +160 这个猜测漏掉了标题。改用机制判据：**块高 ≈ 最高列**（124.8）**且** ≪ 两列之和（249.6）——即「它们共处一行」这件事本身 |
| 8 | 375 下每列宽度 ≈ `innerWidth`（375） | 每列 299 = 内容列宽（375 − 2×38） | 参照物是**内容列**不是视口。改为与同页标题自身的宽度比（299） |
| 9/10 | 表格宽 = 标题宽 | 1364 vs 1200 | **真缺陷**，见上 |

**教训（写给下一批）**：① 量「改动过的那个东西」，不要量「改动过的东西恰好住在里面的那个容器」——section/父级常常还装着本批没碰的邻居，`secBox` 与 `secPad` 都是这类陷阱；② 任何跨改动前后的「其余都没变」断言，必须指名**先于本批就存在的例外**（本例是一条 `:has()` 规则），否则它测的是历史而不是本批；③ 判据里凡是**参照物**（innerWidth / 视口 / 固定像素猜测），先问一句「这个参照物和被测量的是同一个坐标系的吗」。

## 一、五项待办与实现

**待办14 — 所有配方卡片图片加链接。** 渲染器在 `$links` 为真时把静图包进
`<a class="sf-fcard__imagelink" href="{permalink}" aria-label="View the {name} formula">`，链在 `<figure class="sf-fcard__media">` 之内、body 之前。**href 与 aria-label 都从这一条记录自己派生**（标题 href 与标题文本），没有一处手写路由表。覆盖 8 剂型页卡墙、`/formulas/` 21 张卡、21 个详情页的 More Formulas：**160 张静图**。

**待办17 — 卡片标签改角标浮层。** 新增后台字段 `sf_formula_card_badge`（下拉：无 / Best Seller / Hot / New，读的就是渲染器用的同一张映射表），角标是**静图的兄弟**（`<figure>` 内、`<a>` 之外）——放进链里会让整块浮层变成链接的一部分。颜色 `--best-seller #8A6D1F` / `--hot #B3261E` / `--new #1F5C99`；无静图的记录走 `--inline` 静态摆放。**本批不碰 post meta**，所以全站渲染数 = 0，这是**声明出来的**零（`insertions` 与 `unmoved` 两处都写 0），不是漏测。

**待办18 — 首页认证区改横向。** 定调语 ＋ 6 个 chip（32px 图标 ＋ 名称，3 列 × 2 行）＋「View all certifications →」。图标是**把印章自己的 `<g>` 原样搬过来**，不是重画：属性大小写跟随**各自那一页**（模板写 `viewBox`，zh 孪生页经 `render_block()` 重新序列化成 `viewbox`），两个计数都是 6 → 6。

**待办19 — Factory Tour 两列。** 用 `wp:columns` 包住页面**自己那五段**（3 ＋ 2），零 CSS。

**待办22 — Key Facts 撑满版心。** 见 §〇。

## 二、改动清单

| 文件 | 改 |
|---|---|
| `functions.php` | `sinofresh_formula_card_badges()` / `_badge($post_id)` / `_badge_markup($badge, $inline)`；静图外包 link；`<figure>%s%s</figure>` 保持角标为兄弟 |
| `inc/formula-admin.php` | 新字段规格（`type: select`）＋ `case 'select'` 渲染器 ＋ `case 'radio': case 'select':` 并入保存分支 |
| `style.css` | `Version: 2.10.72`；`.sf-certgrid/.sf-certcard*` 删除，`.sf-certstrip__*` 就位；768 折到 2 列、420 只收窄**不堆叠**；`.sf-fcard__media{position:relative}`、`.sf-fcard__imagelink`、`.sf-fcard__badge` 及其三色/`--inline`；`.sf-keyfacts` 上限改为与标题同源 |
| `templates/front-page.html` | Compliance 带 → `.sf-certstrip`（lede ＋ `ul[role=list]` 六 chip ＋ more 链）；带内边距 48 → 32 |
| `templates/page-factory-tour.html` | `wp:columns{className:"sf-prepare"}` ＋ 两个 `wp:column` |

## 三、门（`tools/b2d_h7_gate.py --batch h7k`）

基线 `_backup/b2d-h7j-candidates-fix`（2.10.71）→ 候选 `_backup/b2d-h7k-candidates`（2.10.72），A/A 用 `-candidates-aa`。

- A/A：**PASS**（75 页 0 差异 —— 掩码集未变）。
- 主证 `mask(transform(baseline)) == mask(candidate)`：**PASS**，75 页比对、**0 页差异**、**163/163 applied**（`applied_base = 0`，`mode: insert`）。
- coverage **33 行全 ok**；invariants **20 行全 ok**；掩码回读 **PASS**。
- 矩阵 **10 个突变体全部 caught，无一 no-op**：

  | 突变体 | 结果 | 差异页 | applied |
  |---|---|---|---|
  | tokens 未折叠 | caught | 75 | 163/163 |
  | 静图不加链 | caught | 60 | 3/163 |
  | 链包 figure 而不包静图 | caught | 60 | 163/163 |
  | 标签改成描述照片 | caught | 60 | 163/163 |
  | 认证带保留六张卡 | caught | 2 | 161/163 |
  | 印章不缩水照搬 | caught | 2 | 163/163 |
  | 清单仍单列 | caught | 1 | 162/163 |
  | 清单切成 4＋1 | caught | 1 | 163/163 |
  | 轮次少声明 1 | caught | 0 | 163/**162** |
  | 完全不施加 | caught | 63 | 0/0 |

- 负对照：**41 条全 ok**（NC1–NC8 ＋ NC-src 24 ＋ NC-page 5 ＋ NC13–NC16），其中 NC13 现在两半都真的触发：`page=root.html main_red=True coverage_red=True`。
- source 段（必须**独立跑一次**）：**43/43 PASS，exit 0** → `_backup/b2d-h7k-gate-source.{log,json}`。
- 主段：**7/7 子句 PASS，0 FAIL，exit 0**，耗时 42m → `_backup/b2d-h7k-gate.{log,json}`。

### 三·一、本批为门补的两条子句

1. **`corroborated`** —— 卡墙和**它自己的 ItemList** 是同一个数字的两个载体，而主证**分不出**它们：变换是沿卡墙走的，所以「墙上 20 张、上面的 JSON-LD 说 21」会被**同样地镜像**过去、照样绿。新子句从**基线**读那个 ItemList 的数，要求候选页上的链接数与它相等；模式以反向引用收尾，于是同时要求**每条链指向它自己标题链所指的那条记录**。实测 75 页全等，总数 160。
2. **`h2_delta` 支持 dict 形式** —— 旧的标量形式把自己挂在 `decl['applies']` 上（H7j 是 1500 次编辑、H7k 是 163 次），于是它**只**能说「每次编辑都动了一个标题」。H7k 是**在 75 页里的 2 页上各撤掉一个**标题，标量形式表达不了。dict 形式点名一个页集合与每页步长，两半各有一个**具名负对照**去触发它。

### 三·二、三条负对照是**断言**错，不是产品错（逐条从源码证明后重构）

- `NC-src 定位上下文`：突变针写成字面量 `.sf-fcard__media {\n\tposition: relative;`，而该声明是块内**七条里的最后一条**、前面还夹着注释，所以字面量**根本不在 style.css 里** → 控制报「needle is not in style.css」，是一个**开不了火**的控制，不是一条不能失败的判据。它守的那条判据匹配该块真实的 539 字节，**产品是对的**。改成伸手进块里改写。
- `NC-page 角标不请自来`：往卡片里注入角标后**没有一条变红**——它保护的判据是 `insertions` 计数，而 `insertions` 归 `coverage` 管，这个控制只能跑 `invariants`。这条事实现在**第二个载体**是一个 `unmoved` 的**页计数**（不是冗余：一个总计数分不清「一页三个」和「三页各一个」）。
- `NC13`：突变体给 `View all certifications` 尾巴加了个 `X`，判据自己的子串**原样保留**，于是主证看见了编辑（`sighted`）而 coverage 仍旧绿。改成**换词**，声明计数 2 → 1。

### 三·三、门自身的两个坑（本批实测，已修）

1. **`_clone` 在本机根本复制不了主题。** 沙箱文件 broker 会在真 `copytree` 走之前先把目标**目录骨架**建好，于是真的那个撞上自己的目录、抛 `shutil.Error`，列表里**只有目录没有文件** —— 正是主题的九个一级目录（`_backup` `_backup_x` `assets` `docs` `inc` `parts` `screenshots` `templates` `tools`）外加深浅不一的若干 `_backup/*`，三次运行分别是 58/60/71 个，**不确定性本身**就是它是竞态而不是规则的证据。它把运行掐死在第一个 `nc_source` 突变体上（NC1–NC8 之后），**于是 NC9 起的每一条源码控制从来没真正跑过**。改法 `dirs_exist_ok=True`（broker 复制的那份就是我们想要的那份），并**加一条文件数后置检查**：克隆若在返回时还不完整，下游每条源码判据读到的都是半个主题，本该响的那些控制会安静地通过。已用 sha256 清单验证 745 文件 0 缺 0 多 0 异，`copytree` 与 `cp -a` 各三次。
2. **`--source` 是 `if/else` 分支不是叠加**：与 `--base/--cand` 同传只会跑源码段却照样打印 PASS。每批必须**两次独立运行**、两个 JSON。

## 四、E2E（`tools/b2d_h7k_e2e.py`，**115/115**，exit 0）

`--only cards,badge,band,prepare,keyfacts` 可分段；每次开页都先断言**是哪一份资源在应答**（`served()`），再断言别的。

`--live` 红基线（去掉预检头 → 打到 dev 的 2.10.69）：**18/114，exit 1**，且**第一条**就是
`preflight 2.10.72 served (/products/drops/) | {pre: False, theme: …/sinofresh-theme/style.css?ver=2.10.69, v72: False}` —— 先证明它拿到的是**live 那份**，再说别的。这证明 E2E 不是空过。

## 五、几何实测（把「约 180px、省 70%」变成数字）

同一把尺子在两版上各量一次（都量**该 section 的**高度：旧的带没有单一包裹元素，且两版 section 里都装着本批没碰的 `sf-certbar` 与按钮，在**差值**里相互抵消）：

| 量 | 2.10.69（live） | 2.10.72（预检） |
|---|---|---|
| 带本体（eyebrow→卡片底 / lede→strip 底） | **607.3px** | **155.4px** |
| 所在 section | 898.6px | 414.7px |
| section 内边距 | 48 / 48 | 32 / 32 |

⇒ **省 451.9px、短 74%**，待办写的「约 180px、省 70%」两项都达到且超过。
Key Facts 修后实测：表格 `max-width: 1200px`、盒 `120→1320`，标题 `120→1320`。

## 六、工具链踩坑（本批实测，写给下一批）

- ⛔ **`screenshot --full` 会拍下「还没被揭示」的区块**：首页折线以下的 section 由 `interactions.js` 挂 `.sf-pending`、由 `.sf-motion …{opacity:0}` 隐藏，滚动揭示后**永久移除**。不预滚动就抓，那一块是**纯色**——本次三张认证带帧返回 `colours=1`，而**同样裁剪尺寸**的 zh 孪生页返回 509（它当时已揭示），差的不是 CSS 是拍摄时机。解法：抓之前自上而下滚一遍再滚回顶，并**断言**留下的 `.sf-pending` 为 0。
- ⛔ **`position: fixed` 的 cookie 横幅/浮条在整页截图里会落在页面中部**，压住正在证明的那一行。组件类帧抓之前把它 `display:none` 并在日志里说明（它是本批没碰的全站既有覆盖层，属噪声不属证据）。
- ⛔ **前台 heredoc 会 OOM**：`python - <<'PY'` 里遍历 75 页连挂三次（exit 137），同一件事写成**脚本文件**或丢后台就好。本批又踩了一次（六次 sha256 清单）。另：`cmd > log 2>&1` 在全缓冲下**退出前一直是 0 字节**，`wc -c` 为 0 **不是**卡住的证据。
- ⛔ **BSD grep 的交替**：`grep -n "a\|b"` 静默返回空（exit 0）。本批又误判一次，必须 `grep -E` 或用 Grep 工具。
- ⛔ **预检安装要先在服务器仓库 fetch**：`b2d_s1_preflight.py` 只有 `install/remove/status`，没有 fetch；fetch 前还必须先 `git push`，否则服务器上根本没有那个对象。

## 七、版本与基线说明

本次 `style.css` 修复**没有 bump 版本**，仍是 2.10.72。理由：2.10.72 **从未对任何面向用户的入口发布**（预检目录每次 install 都是新建），批 D 以**一个版本号**收尾；H7j 先例相同（两个候选目录相隔一次提交、掩码下逐字节相同，整批仍以 2.10.71 发布）。因此**候选抓取不需要重做**（HTML 字节不变），需要重跑的是**读 style.css 的源码段**与**negctl**，两者都已重跑。

## 八、仍需用户处理

- **post 158 三处演示值**（`sf_formula_video_url` / `sf_formula_sample_price` / `sf_formula_price_tiers`）仍待销售填真数据；回滚档 `_backup/b2d-h7i-post158/before.json`。
- **批 E 已取消**：所有产品内容（含占位数据）由用户自己在后台填写，本批**不碰 post meta**。角标因此全站渲染数为 0。
- **Shape Library(8) / Container Library(7)** 待用户传图。
- **生产上线 10 项移除**留第二批（最易漏 `blog_public` 0→1）。
- 登记在案：`color` 标记对比度保持现状（品牌绿 #5AB735）。

## 九、帧（`docs/batchH7k-shots/`，15 张，全部 non-flat 已验）

| 帧 | 说明 |
|---|---|
| 01 / 03 / 04 | 卡墙：`/formulas/`（21）、`/products/drops/`、`/zh/products/drops/` 孪生页 |
| 02 | 单卡：静图在链内 |
| 05 / 06 / 07 | 三色角标（**注入**，因为无记录携带值）、单卡特写、768 |
| 08 / 09 / 10 / 11 | 认证带 1440 / 768 / 375 / zh 孪生页 |
| 12 / 13 | Factory Tour 清单 1440（一行两列）/ 375（堆叠） |
| 14 / 15 | Key Facts 与标题两端对齐 1440 / 375 |
