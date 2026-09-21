# Batch G — 详情页「主图 + 参数」两栏 + 剂型页 Packaging 第 4 行

**状态：已上线并闭环（2026-09-21）**。提交链：`c4f4437`（源改动 + 门工具 + 方案档）→ `d8c54a5`（门报告 + 渲染取证 + 本档）→ `8522f77`（`docs/b2d-g-closure/` 证据 + 本档头部）。线上工作树由 `4504aa9`（F1）快进到 `d8c54a5`（**主题内容＝`c4f4437`**，`d8c54a5` 只加 docs/tools），预检副本已拆净。

## 一、这批做了什么

1. **8 个剂型模板**：`.sf-facts-mini` 在 `Certifications` 行后增第 4 行 **Packaging**（`data-label="Packaging formats"`，无 h2）。值从各页配置器 `data-group="packaging"` 选项集抄录，去末项 `Custom`，统一以 **`, or custom formats`** 结尾（拍板 III：8 个剂型统一逗号版，soft-chews 的三重 `+` 保留）。
2. **详情页模板 `single-sf_formula.html`**：原独立全宽 `sf-gallery` group 改为 `section.sf-fdetail-media` 两栏——外层 constrained + `bg-light`（背景只挂外层），`__inner` 与左右两栏一律 `layout:default`（core 对 constrained 子项限宽居中，会打散 grid）；左栏 `#gallery`（h2 与 4 帧 slide 全保留），右栏 `aside` 装 `{{FORMULA_INTRO}}` + `[sf_formula_factsheet]` + `Request Sample` CTA。
3. **`functions.php`**（2.10.53 → **2.10.54**）：
   - `sinofresh_formula_specs_parts()`：`sf_formula_specs` **按 key 正则取字段**（shelf 先 `/\d+\s*months?\s+shelf\s+life/i` 移出，pack 再 `/\sper\s/i` 移出——裸 `per` 会假匹配 `dropper bottle`，实测 +2 假值），unit 取剩余首段；**2 段式 11 条无 pack ⇒ 整行不渲染**（拍板 I：缺就缺，不顶替）。
   - `sinofresh_formula_intro()`：`sf_formula_intro` meta 有值直接用，否则按模板拼 `{product} is a standard {form} formula … Minimum order quantity: {moq}. Lead time: {lead}.`（MOQ 自带 `from` ⇒ 冒号槽位）。**不复用 schema 生成函数** ⇒ JSON-LD 0 变化。
   - `[sf_formula_factsheet]` 短代码：`<dl>` 5 项 `Unit size / Pack options / Shelf life / Certifications / Packaging`，后两项经 `spec_cell()` 读剂型页新行（**零改动**，F1 的「先截块再按 data-label 取」天然兼容第 4 行）。空值行跳过。
   - `{{FORMULA_INTRO}}` 占位符映射（带 `<p>` 外壳）。
4. **`style.css`**（2.10.53 → **2.10.54**，两处同步）：`.sf-fdetail-media` 命名空间——`__inner` grid `minmax(0,3fr) minmax(0,2fr)` gap 48、`__inner > *{margin-block-start:0}`（抵消 core 的 flow margin，实测右栏被推下 24px）、左栏覆盖 `.sf-gallery__stage` 的 `max-width:680px;margin:30px auto 0`（否则又窄又居中）、`<dl>` dt/dd 形态、CTA 用 **`cta` #B54E0F**（拍板：与页尾 Request a Quote 统一）、`≤768px` 堆叠 gap 32。

## 二、门（`tools/b2d_g_confine.py`，六门 + 负对照 + 破坏矩阵）

**混合方向**：剂型 16 页走**插入批**（候选侧删新行还原基线）；详情 42 页走**结构重组**（四步：撤批注释 → 删右栏 → 左栏升回顶层并恢复 class/style → 按基线口径闭合）。

| 门 | 真数据候选结果 |
|---|---|
| 0 候选身份 | 75/75 来自预检副本（副本 `functions.php`/`style.css` sha256 与本地提交**逐位相同**） |
| 1 资源清单 | 仅 style.css `2.10.53 → 2.10.54` ×75，资源 SET 变化 0 |
| 2 掩码 DIFF | differ **58** / identical **17**，与期望集合精确命中 |
| 3 页级限定证明 | **58/58 逐字节还原**（剂型 16/16 + 详情 42/42）；八剂型行值与各自配置器交叉核对 **8/8 ok** |
| 4 源级重建 | **11 文件** undone==base（functions.php、style.css、8 剂型模板、single-sf_formula.html） |
| 5 JSON-LD | **75/75** deep-equal |
| 负对照（new=base） | **RC=1，144 条**（首条即显式守卫「NOTHING moved…is --new pointing at base?」） |

**破坏矩阵 9/9 被抓**（每个破坏恰好落在该负责的门上）：`drop-row`→门3 行缺失；`wrong-value`→门3 值≠配置器；`extra-diff`→门2 多 DIFF；`missing-aside`→门3 右栏缺失；`stray-byte`→门3 逐字节还原失败；`keep-h2`→门3 点轨 h2 断言；`version-only-one`→门1 74/75；`wrong-cta`→CTA 目的地；`zh-cta-dropped`→zh 按钮缺失。

### 门的自身 bug（Step 0「先合成候选跑通门」的收获，共 4 个）

前三门 bug 在**合成候选阶段**就 FAIL 出来，没浪费一次真数据抓取：

1. **`SIDE_RE` 只吃 2 个换行**：渲染器真实输出 `</section>\n\n\n<aside`（三个），少一个 ⇒ 每次撤销残留 1 字节，42 页全败。
2. **`CLOSERS_CAND` 少了结尾第三个换行**（`\n\n</section>\n\n` 应为 `\n\n</section>\n\n\n`）⇒ 尾部多 1 个 `\n`。两者都是「渲染接缝实测不推演」的教训重演——本次用 `do_blocks` oracle 把真实字节问出来后才修对。
3. **undo 漏撤批自己的模板注释**（`<!-- Batch G: … -->`，基线里没有）⇒ 改成显式四步，并把注释裁剪钉在开头字样上：改注释措辞 ⇒ 撤销不再命中 ⇒ 门报 no-op，而不是悄悄放行。
4. **CTA `href` 用了字面 `/contact/`**：TranslatePress 在本地化页把链接改写成 `/zh/contact/`（该页其它 CTA 全是这个形状），真数据阶段 21 条假 FAIL。改为「目的地」判据 `^(\/[a-z]{2})?\/contact\/$`，并给合成器补上 TP 改写建模（否则合成跑的门天然比真数据弱）＋ 新增 `wrong-cta` / `zh-cta-dropped` 两条负对照。

合成器本身也修了 2 处：formulas 分支「先插注释再定位」的索引偏移（曾产出 `<<section` 坏字节）；键名带 `.html` 后缀（F1 同款 bug 复发）。

## 三、渲染取证（`tools/b2d_g_evidence.py`，预检 **340 项 / 0 失败**，live 复跑 **342 项 / 0 失败**）

> 两次项数差 2，是因为 live 复跑把点轨断言从「两侧读数相等」升级成「直接断言 detail 0 / dosage 6」（多 2 项）。预检那一跑读的是候选副本，live 那一跑读的是线上（不带 `X-SF-Preflight` 头，并断言拿到的样式表**不是** preflight 目录）。

数字全部实测（`docs/batchG-evidence.json` 落盘，截图 `docs/batchG-shots/`），断言「拿到的是哪份样式表」也是一项检查（本批全走预检副本 `style.css?ver=2.10.54`）。

**详情页 @1440**（joint-support-soft-chews / pure-fish-oil-blend / zh 版）：2 栏 **691.188px / 460.797px**（比值 1.499≈3:2）、gap **48px**、左右顶边同为 **509**（右栏 `margin-block-start:0` 生效）、外层有背景且内层透明；`.sf-gallery__stage` **`max-width:none`、`margin-left:0`、宽 691＝栏宽**（旧 680px 居中帽已破）；4 帧 slide 与 `h2.sf-gallery__title` 都在；intro 逐字引用 hero 的 MOQ（`from 500–1,000 units`）与 Lead time；参数表 5 行按 canon 序、Packaging 以 `, or custom formats` 结尾；CTA `Request Sample` → `/contact/`（zh 页 `/zh/contact/`）、底色 `rgb(181,78,15)`；**0 JS 错、无横向滚动**。页面上同名按钮全量清点只有 1 个（x=859＝右栏左缘 120+691+48）。

**详情页 @375**：1 栏 299px、gap 32px、右栏落到左栏下方（554 → 1082）。**@768**：1 栏 692px、leftBottom 1303 → sideTop 1335（堆叠成立）。

**剂型页 @1440（8/8）**：4 个带 `data-label` 的值，第 4 个＝`Packaging formats` 且以 `, or custom formats` 结尾，前三个 label 不变；事实带**换行成 2 行**（tops `473,473,473,505`，带高 **55px**）＝拍板 II(a) 预先接受、本次实测定稿的形态；点轨 **6 点 / 6 个 h2** 自洽。**@375**：4 项各占一行（tops 615/677/738/800，带高 289px），点轨 6/6。

## 四、重要发现：详情页没有点轨（纠正方案前提）

方案里「详情页点轨 4 点」是**错误前提**。实测（预检与线上 2.10.53 各测一遍）：详情页 `toc-nav.js` **根本未入队**，`.sf-toc__dot` 为 **0**，全页无任何 `*toc*` 元素；线上同样为 0。所以本批的不变量不是「保持 4 点」，而是「**详情页点轨数与线上一致（0＝0）、剂型页 6 点不变**」——已用 live vs 候选两侧对照证实（detail `0/0`，dosage `6/6`，均 RAIL UNCHANGED）。断言一个不存在的东西，只会把对的改成错的；这条已写进取证工具的注释。

## 五、Step 7 上线与八步闭环（2026-09-21 07:2x–07:4x UTC）

拍板后执行。八步逐条落证，证据全在 `docs/b2d-g-closure/`（8 个文件 + `shots/` 4 张截图）：`closure-75.json`、`teardown-75.json`、`e2e.json`、`e2e.txt`、`logaudit.txt`、`identity-chain.txt`、`g-preflight.log`、`teardown.txt`。

> `shots/` 与 §三 的 `docs/batchG-shots/` 是同名两次抓取：前者对着**线上**（不带预检头），后者对着**预检副本**（带 `X-SF-Preflight` 头）。四张里三张（768 / zh-1440 / fish-oil-1440）逐字节相同；唯一不同的 `joint-support-soft-chews-1440.png`，页面版式一样，**差在缩略图懒加载的瞬时状态**——预检那跑只等到了第 1 张缩略图，live 那跑 4 张全到位（两图都带 cookie 横幅）。两份都留着：它们各自是那一次取证的原始产物，替换成一份就等于把「对着哪份字节测的」这件事抹掉。

| 步 | 结果 |
|---|---|
| 1 上线 | `git pull --ff-only`：`4504aa9`（F1）→ `d8c54a5`。`git diff --name-only c4f4437 d8c54a5` 里**主题文件 0 个** ⇒ 上线的主题字节就是门上跑过的 `c4f4437`；线上 `functions.php`/`style.css` sha256 与本地**逐位相同**（`87a0499b…`／`2578488e…`） |
| 2 服务侧 | 详情页与剂型页都引用 `themes/sinofresh-theme/style.css?ver=2.10.54`（**不是** preflight 目录）；两栏 8 个类各 1 次、`id="gallery"` 1、`h2.sf-gallery__title` 1、4 帧 slide 在；`<dl>` **5 行**（Unit size / Pack options / Shelf life / Certifications / Packaging）；CTA → `/contact/`「Request Sample」；剂型页事实带 **4 项**、第 4 项 `data-label="Packaging formats"` 以 `, or custom formats` 结尾；**A/A 掩码自检 PASS**（111918/111918 B） |
| 3 掩码回归 | 抓 live 75 页，先**逐页断言样式表目录为 `sinofresh-theme` 且版本为 2.10.54**（否则 CF 快照能冒充上线）→ 候选 vs live **75/75 identical** |
| 4 浏览器 E2E（live） | **342 项 / 0 失败**：1440 两栏 **691.19 / 460.80 px**（≈3:2）、gap **48**、左右顶边同为 **509**、`.sf-gallery__stage` `max-width:none` 宽 691＝栏宽、CTA `rgb(181,78,15)`；**点轨直接断言 detail 0 / dosage 6**；375（299px 单栏、gap 32）与 768（692px 单栏，leftBottom 1303 → sideTop 1335）堆叠成立；**0 JS 错** |
| 5 拆预检 | 主题目录 / mu-plugin / 日志三者全消，`find *preflight*` **零残留**（仅余常驻 `zz-sf-dev-lockdown.php`）；拆前先把预检副本自己的访问日志（158 行、07:04:24→07:18:47）留档为 `g-preflight.log`。复验：**拆除前 live vs 拆除后 live 75/75 identical** ⇒ 拆除本身零字节影响；带 `X-SF-Preflight` 头访问现在也回落到线上主题 |
| 6 日志归因 | **窗口内 0 条**；40 行按内容归因；1 条 `--allow` 记账（2D-E 负对照的故意 fatal）。窗口内 **1113 条请求全部认证为 `sfdev`，非我方 0 条**（`curl/8.7.1` 230 + 浏览器 882 + 站点自身 wp-cron 环回 1） |
| 7 身份链 | workspace ↔ `site-repo/sinofresh-theme`：**691 文件 0 不一致**；第三条腿：仓库目录 ↔ Apache 实际服务的 symlink 目录：**691 文件 0 差异** |
| 8 仓库 md5 | **1339 文件 0 差异**（1340 跟踪 − 1 排除；两侧同排除 `docs/batch2d-stepG.md`。原始输出见本节末尾） |

### 过程里的两处自我纠正（都是用法错，不是数据错）

1. **日志审计第一次跑 FAIL**：我把 `--access-log` 覆盖成只剩 SSL 那一份，端口 80 的 `/cgi-bin/luci` 探测因此找不到对照行——工具 docblock 原文就写着这条要靠端口 80 的访问日志。去掉覆盖后 PASS（2 条 FAIL → 0 条）。
2. **窗口内那条 `WordPress/7.1.1` 请求**：`POST /wp-cron.php?doing_wp_cron=…`，访问日志记的用户是 `sfdev`、状态 200。它是**批前就有的既有行为**（前后 24 小时内每小时左右一条，最早一条在 20 Sep 23:25，早于本批任何改动），机制未坐实，但判别符说它是我们这一侧，一并计入归因。

### 回滚

预检脚手架已 `remove` 且已证零残留。主题回退＝在 `site-repo` 内 `git checkout 4504aa9 -- sinofresh-theme`（或把工作树 reset 回 `4504aa9`）；dev 站无页面缓存层，`functions.php` 的 enqueue 版本号一改，样式 URL 立刻换键，不需要手工清缓存。

### 顺序上的一个取舍

md5 是**最后一步**，在本档写下这些数字之前跑（`d63ea50`）。报告不能是它所报告集合的成员 ⇒ 两侧同时排除本档；复跑命令 `python3 tools/sf_repo_md5.py --exclude docs/batch2d-stepG.md`，应得同样的 1340/1/1339/0。曾想再拆出一个 `cloud-md5.txt` 单独落盘原始输出，被工具自己拦下——**未跟踪的排除路径会被拒绝**（否则排除是空动作），这个守门是对的，于是原始输出直接放进报告。

<details>
<summary>仓库 md5 原始输出（<code>python3 tools/sf_repo_md5.py --exclude docs/batch2d-stepG.md</code>，commit <code>d63ea50</code>）</summary>

```
tracked files            : 1340
excluded (both sides)    : 1  (docs/batch2d-stepG.md)
compared                 : 1339
hashed locally           : 1339  (unreadable: 0)
hashed on the dev box    : 1339
non-ASCII paths          : 13
   sinofresh-theme/docs/官网开发文档-全文.md                    matched
   sinofresh-theme/docs/视觉重设计方案-v2.md                   matched
   sinofresh-theme/screenshots/batch1-step2-hero/s2-liquids-1440-Hero特写.png matched
   sinofresh-theme/screenshots/batch1-step2-hero/s2-liquids-1440-首屏-标注.png matched
   sinofresh-theme/screenshots/batch1-step2-hero/s2-liquids-1440-首屏.png matched
   sinofresh-theme/screenshots/batch1-step2-hero/s2-liquids-375-首屏-标注.png matched
   sinofresh-theme/screenshots/batch1-step2-hero/s2-liquids-375-首屏.png matched
   sinofresh-theme/screenshots/batch1-step2-hero/s2-soft-chews-1440-Hero特写.png matched
   sinofresh-theme/screenshots/batch1-step2-hero/s2-soft-chews-1440-首屏-标注.png matched
   sinofresh-theme/screenshots/batch1-step2-hero/s2-soft-chews-1440-首屏.png matched
   sinofresh-theme/screenshots/batch1-step2-hero/s2-soft-chews-375-首屏-标注.png matched
   sinofresh-theme/screenshots/batch1-step2-hero/s2-soft-chews-375-首屏.png matched
   网站网址图标素材512-512.ai                                   matched
mismatches               : 0

PASS  1339 files, 0 mismatches
```

</details>
