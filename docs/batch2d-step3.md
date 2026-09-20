# 批次 2D 第 3 批 —— 执行记录（第 0–3 步）

> 目标：把第 2 批装在 8 个剂型页的产品图集带**搬到** 21 条配方详情页，详情页新增两个模块
> （`[sf_formula_detail_actives]` / `[sf_formula_detail_composition]`）。
> 本文只记**已发生的事实与证据**。方案见 `batch2d-step3-plan.md`，扫描见 `batch2d-step3-scan.md`。

---

## 0. 状态一句话

| 步骤 | 状态 |
|---|---|
| 第 0 步 清预检脚手架 | ✅ |
| 第 1 步 撤剂型页图集 + 入队迁移 + 版本号 | ✅ |
| 第 2 步 详情页新增模块 | ✅ |
| **第 3 步 push + 云端 pull + 四门核验** | ✅ **本文档** |
| 第 4 步 浏览器 E2E | ✅ 已跑完 46/46；**随后按决策停用**（不再精修，改四项快验 → §6） |
| 第 5 步 备份 + 提交 | ⏸ 未执行，待确认 |

提交：`67afac0`（第 2 批遗留工具 + 取证图）、`dcfc4d3`（本批实现，已 push：`cb63af6..dcfc4d3`）

---

## 1. 云端动作（第 3 步第一项）

- `git pull --ff-only` → `dcfc4d3`
- chown **只** `site-repo/sinofresh-theme`（仓库根仍 `root:root` ⇒ 避免 `dubious ownership`）
- 版本号 **2.10.47** 两处落盘：`functions.php:26`（`wp_enqueue_style` ver）+ `style.css:5`（`Version:`）

**实测坑（已写进工具 docstring + 加断言）**：云端 **缩写 SHA 无法解析** ——
`git cat-file -t dcfc4d3` 失败、40 位全 SHA 正常；`git log --oneline` 打印的又是缩写，
极易粘回。`tools/b2d_s1_preflight.py install` 现在对短 SHA 直接 `raise SystemExit`。

---

## 2. 四门核验（`docs/b2d-step3-gates.txt`，全 PASS）

比对对象：`_backup/b2d-s3-baselines/base`（75 页，`ver=2.10.46`）↔ `new`（75 页，`ver=2.10.47`）。
75 页体积互不相同（96 KB–242 KB），这本身就是"两侧不是同一个 401 页"的证据。

| 门 | 结果 |
|---|---|
| [1] ver inventory | `style.css 2.10.46→2.10.47` 75 页；`formula-gallery.js 1.0.0` **ADDED 42 页**（详情）/ **REMOVED 16 页**（剂型）；**无其它资源令牌变动** |
| [2] 限定证明 | 75/75 —— **16 纯删除**、**42 移位+新增**、**17 逐字节未动** |
| [3] script 标签 | 新基线恰好在 42 个详情页带该脚本 |
| [4] 结构 + 非循环 | 42/42 单元的图集/活性表匹配各自模式；①② 数据 == 同页卡片自身数据（非循环校验）；③ 组合段为空 |

**归一化处理**：先复用 `sf_masked_cmp.masked()`（**import 复用同一掩码集，不另抄**），
再 `VER_RE.sub('?ver=MASK')`。若先做 ver 掩码会引入 `?ver=<V>`，其中 `>` 使
`SCRIPT_RE` 的 `[^>]*` 提前截断 ⇒ gallery script"消失"⇒ 单窗口假设破裂。

**锚点定窗**取代 LCP：LCP 边界曾落在注释中间（`<!-- B` 共同，base 接 `lock 2:`、new 接 `2D-S3:`），
marker 被切半致全部查找 miss。现用剂型页 `<!-- B2D-S2: gallery -->` → `<section id="formulas"`、
详情页 `<!-- B2D-S3: gallery -->` → `<!-- Block 4: related formulas -->`。

---

## 3. 身份链（`tools/b2d_s3_identity.py`）

```
tracked files under sinofresh-theme/: 691
[live]  /var/www/dev.zxpet.com/site-repo/sinofresh-theme
  compared 691 files, mismatches: 0
PASS  identity chain
```

- 文件列表必须用 `git -c core.quotePath=false ls-files`：默认会把非 ASCII 路径转义成
  `"..."` + 八进制，对端被误判"文件缺失"。
- CSS 三项不变量：`:has(` **163 + 7 = 170**；新增段 `!important` = 0、`url(` = 0。

---

## 4. 浏览器 E2E（第 4 步内容，`tools/b2d_s3_browser.py`，**46/46 PASS**）

首轮 → 最终：`44 项 1 失败` → `46 项 0 失败`（`docs/b2d-step3-shots/e2e-run*.txt`）。
最后一轮 `e2e-run5-final.txt` 在**预检拆除之后**跑，结论落在站点最终状态上。
途中暴露并修掉**两个自我缺陷**，都不是产品缺陷：

### 缺陷 A：scroll-snap 断言写错（唯一的 FAIL 来源）
断言写成"计算值里是否含子串 `snap`"，但属性是 `scroll-snap-type`，
**"snap" 在属性名里、不在值里** —— 实测值 `x mandatory` 完全正确，却被判失败。
改为与第 2 批同一形态的**整值比对**（`b2d_s2_browser.py:463` 已用此写法）。

### 缺陷 B：cookie 横幅的"存在"≠"在屏幕上"，导致误导性警告
`dismiss_cookie_banner()` 只看 `querySelector('.sf-cookie-banner')` 是否存在。
实测（`docs/b2d-step3-shots/_banner-*.txt`，三步取证）：

| 实验 | 结果 |
|---|---|
| 视口扫描（新会话，1440/375/1280） | 横幅可见、accept 按钮真实（104×44 / 343×44），`elementFromPoint` 命中按钮 |
| 时间线（10s 采样，1280×900） | `display:block` h=76 **稳定 17 秒**，手动滚动不消失、重载仍在 ⇒ **排除定时自动隐藏** |
| 逐步复演 real_click | down/up **之后**才 `display:none` ⇒ 点击本身有效 |
| **同会话后续导航** | 横幅仍在 DOM 但 `display:none`、按钮 0×0 ⇒ **接受状态在同一会话内被记住** |

⇒ 首次导航点击成功；之后每次导航都会打出"later click checks may fail for this reason alone"，
而那时**没有任何东西能被挡住**（F/G 的点击检查实际全部通过）。
修法不是改点击，而是改判定依据：**看横幅自己有没有布局盒**，不看它在不在 DOM。

### F 段同时被纠正为空测
首版在"页面加载时的滚动位置"测量覆盖率，而横幅是 `position:fixed` 贴视口底、
375px 下高 266px，图带在首屏之下（文档 y 938..1030）⇒ 测出"不重叠"与横幅无关。
改为**先把图带滚入视口再测**（那才是真实点击发生的位置），并记录关闭前状态作为证据：

```
banner/strip BEFORE dismissal: {"over": true,  "bannerBox":[375,266,401,667], "stripBox":[299,92,311,403]}
banner/strip AFTER:            {"over": false, "why":"banner has no box (already resolved)"}
```

关闭前 `over:true` 是**记录而非断言**：站点自身横幅是否在该视口渲染，不属本批改动范围，
断言它会让回归门因交付物之外的缘故失败。

### E2E 覆盖
E 无 JS 静态契约（4 帧 / 2–4 帧 `hidden` / 不带缩略图带 / 首图 eager）· A 1440 详情带 ·
B 缩略图真实点击（命中校验）· C 键盘 ←/→/Home/End · D 手势方向（右=回、左=进、竖划不动）·
F 375px（无横向溢出 / 带内滚动 / scroll-snap / 横幅不压带）· G zh 详情页。

**点轨**：详情页 `toc-nav.js` 未入队 ⇒ 无点轨，脚本**显式断言其不存在**（而非静默跳过）；
且点轨本身桌面专用（`style.css:7322` `@media(max-width:1100px){display:none}`）。

> ⏹ **本 harness 到此为止**。它揭出的 5 个 bug 全部属于测试基础设施（`networkidle` 永不返回、
> `agent-browser` 守护进程挂死、URL 双重前缀、scroll-snap 断言看错值、cookie 时序），
> **没有一个是产品问题**；继续精修它的边际收益低于成本，改为 §6 的四项快验。工具保留备查。

---

## 5. 拆除预检装置（第 3 步第六项，`docs/b2d-step3-shots/teardown.txt`）

拆除前的成对取证（证明脚手架当时确实在生效）：

| 请求 | 样式指向 |
|---|---|
| 凭据，不带头 | `themes/sinofresh-theme/style.css?ver=2.10.47` |
| 凭据 + `X-SF-Preflight: 1` | `themes/sinofresh-theme-preflight/style.css?ver=2.10.47` |

`python3 tools/b2d_s1_preflight.py remove` 之后：

- 副本目录 **gone**、mu-plugin **gone**、预检日志 **gone**；`mu-plugins/` 只剩常驻 `zz-sf-dev-lockdown.php`
- 带 `X-SF-Preflight: 1` **回到实服务主题** ⇒ 开关真的没了
- 匿名 **401**（dev 封锁仍生效）；带凭据 **200**
- 详情页仍有 `B2D-S3: gallery` ×1 与 `<section id="gallery" class="… sf-gallery …">`
- 剂型页 `B2D-S2: gallery` ×0 ⇒ 撤除在线上生效
- 身份链重跑：**691 文件 0 不一致**
- 日志零新增：`dev.zxpet.com-ssl-error.log` **1494 B / mtime 2026-09-20 19:31:11**，
  与第 0 步基线**逐字节一致**（覆盖 push → pull → 装副本 → 四门 → E2E → 拆除全程）
- 基线目录未被动过：base/new 各 76 文件

---

## 6. 四项快验（替代继续精修自动化 E2E）

**决策**：停止精修 `tools/b2d_s3_browser.py`。该harness 的 5 个 bug 全是**测试基础设施问题、不是产品问题**
（`networkidle` 永不返回／`agent-browser` 守护进程挂死／URL 双重前缀／scroll-snap 断言看错值／cookie 时序），
记为技术债；改为在 **`/formulas/ear-care-drops/`** 上做一个独立短脚本 `tools/b2d_s3_quickcheck.py` + 一条 curl。
**12/12 PASS**（`docs/b2d-step3-shots/quickcheck.txt`）。

| # | 项 | 证据 | 结果 |
|---|---|---|---|
| 1 | 缩略图切换 | 帧 1 = `drops.webp` → 真实鼠标点第 2 张 → 帧 2 = `fac-placeholder.webp` | ✅ |
| 2 | 375px 无横向溢出 | `innerWidth 375`、`scrollWidth 375`、`clientWidth 375`、`bodyScrollWidth 375` | ✅ |
| 3 | 无 JS 有主图 | curl：图集段服务端渲染；第 1 帧**不** hidden 且含 `<img src="…/drops.webp">`；2–4 帧 hidden；缩略图带**不在**服务端 HTML（由 JS 生成，符合契约） | ✅ |
| 4 | 键盘操作 | 聚焦 `sf-gallery-tab-drops-1` 后 ←/→ 与 Home：1→2→3→2→1 | ✅ |

### ⚠️ 快验脚本自己出的 3 个 bug（同样是测试问题，非产品问题）
1. ⛔ **缩略图 id 前缀不是页面 slug**。`formula-gallery.js` 用
   `"sf-gallery-tab-" + inner[data-gallery] + "-" + n` 生成 id，而 `data-gallery` 存的是
   **剂型（taxonomy）slug** —— 本页是 `drops`，页面却是 `/formulas/ear-care-drops/`。
   按页面 slug 去选 ⇒ 全部 miss，会被误读成"缩略图带没生成"；`soft-chews` 那页恰好两者同名才没暴露。
   ⇒ 前缀必须**从标记里读**，不能假设。
2. ⛔ **375px 测量曾落在空 DOM 上**：测量前不重新加载，沿用上一段留下的页面状态，
   一次运行里读到既无缩略图带、也无 cookie 横幅的空页面，却报出"无横向溢出"。
   ⇒ 改为在 375 重新 `open` 并**在同一次 eval 里断言** `readyState`、`innerWidth` 与 thumb 数，
   空 DOM 无法冒充通过。
3. ⛔ **键盘期望值写错了起始状态**：点击段结束时可见帧已是第 2 帧，因此 ArrowRight 得到 3 是**正确行为**，
   却被判失败。⇒ 断言前先 `Home` 归一到第 1 帧。

### 复验（快验之后重测）
- 预检：`no preflight theme` / `no preflight mu-plugin` / `no preflight log`；`mu-plugins/` 只剩 `zz-sf-dev-lockdown.php`
- 匿名 **401**；带凭据 **200**；带 `X-SF-Preflight: 1` 得到 **实服务主题**（`sinofresh-theme/style.css?ver=2.10.47`）
- 图集脚本也来自实服务主题：`sinofresh-theme/assets/js/formula-gallery.js?ver=1.0.0`
- 身份链 **691 文件 0 不一致**；日志仍 `1494 B / mtime 2026-09-20 19:31:11`（零新增）

---

## 7. 未完成 / 待确认

- **第 5 步（提交）**未执行。工作区当前未提交清单：
  - 已改：`tools/b2d_s1_preflight.py`（全 SHA 守卫 + NOTE）、`tools/b2d_s2_browser.py`（横幅判定修正）
  - 未跟踪：`tools/b2d_s3_confine.py`、`tools/b2d_s3_identity.py`、`tools/b2d_s3_browser.py`、
    三个 `tools/b2d_s3_banner_forensics_*.py`、`docs/b2d-step3-gates.txt`、`docs/b2d-step3-shots/*`（含 4 张图 + 8 个证据文本）
  - 已在 `dcfc4d3` 入库：`b2d_s3_apply.py` / `b2d_s3_fetch.py` / `b2d_s3_paths.txt` / 两个 `b2d_s3_probe_*.php` / `b2d_s3_revert.py`
- **第 4 步口径**（已按确认执行）：375px 只验横向溢出；点轨 ≥1101px 验，详情页无点轨故跳过并显式断言不存在。
- 遗留观察项：
  - ⚠️ 详情页图集 h2 沿用 `Inside Our {L} Production`（无参短代码复用的必然结果，**待预览再定文案**）
  - ⚠️ ≤1239px 内页 hero 贴边（`style.css` 27s 段 `1024px`→`1239px`，独立待办）
  - ⛔ 上线阻塞：实拍图替换 **34 张**（非 18）→ 见扫描档 §9
