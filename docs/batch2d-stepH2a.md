# 批次 H2a —— 配方详情页前台模板重写（媒体带 + 参数区）

> 状态：**已上线闭环**（live `c1f6a35`，Step 6 收尾 2026-09-22）。
> 上线内容：配方详情页的**媒体带与参数区**整体重写 —— 新的 `.sf-fdetail2` 命名空间、
> 竖缩略图轨道（72px）、短视频 facade、新短码 `[sf_formula_params]`（空值整行不渲染）、
> 认证行改走 Site Settings pills（`sf_render_cert_badges()` 同源）。
> 本批**不是零差异批**：42 页（21 英文详情 + 21 中文详情）按声明必须变，其余 33 页只允许
> 版本令牌移动。门因此是**双向**的（该变的必须变、不该变的一个字节都不能动）。

## 关键提交链

`eb47f6c`（H2a 模板重写：functions.php 新增 5 个函数 + 删 factsheet、style.css 第 38 段、
gallery JS 2.0.0、模板媒体带重写）→ `c1f6a35673d637689514e851afeca5cb3e3d619d`（H2c 搭车：
precheck 横幅正则加 `|Save`，enqueue ver 1.0.0→1.0.1）。**上线 SHA 即 `c1f6a35…`。**

## 交付物与改动面

| 文件 | 改动 |
|---|---|
| `sinofresh-theme/functions.php` | +5 函数（`sinofresh_formula_video_id` / `_gallery_slots` / `_gallery` / `_params` / `_chip_list` / `_tier_table`）、删 `sinofresh_formula_factsheet`、`functions.php:31` ver 2.10.55、`:197` gallery 2.0.0、`:3518` intro 类名改 `sf-fdetail2__intro` |
| `sinofresh-theme/style.css` | 第 38 段 `.sf-fdetail2`（移动优先四档断点）、`Version: 2.10.55`；**零 `:has()`、零 `!important`** |
| `sinofresh-theme/assets/js/formula-gallery.js` | 2.0.0 重写（竖轨道、视频 facade、ArrowUp/Down、`--off` 帧标记） |
| `sinofresh-theme/templates/single-sf_formula.html` | 媒体带重写（18–50 行）、`[sf_formula_params]`、`.sf-fdetail2__cta`；Hero/Spec/actives/composition/FAQ/More 七块保留 |
| `sinofresh-theme/inc/formula-admin.php` + `assets/admin/sf-mb-precheck.js` | H2c：正则 `/^(Publish\|Update)$/` → `/^(Publish\|Update\|Save)$/`，ver 1.0.1 |

候选 6 文件哈希表：`docs/batchH2a-gates/cand-files.sha256`（style.css = `d867e8827a22…`）。

## 门与核验（候选 `c1f6a35`）

- **主门** `tools/b2d_h2a_confine.py` **PASS 18/18**（`docs/batchH2a-gates/gate-main-candidate.txt`）：
  ① 资产清单（base 侧 75/75 `2.10.54`、候选侧 75/75 `2.10.55`、42 页 gallery `2.0.0`、无 admin 资产泄漏）
  ② 折叠 `?ver=` 后**恰好 42 页差 / 33 页同**，未折叠时 75/75 全差（证明折叠只藏了声明过的令牌）
  ③ 带外区域（head/header/hero/Specification/FAQ/More/CTA/footer）在 42 页逐字节不变、带本身必差
  ④ 源级重建 + tokenizer（5 个新函数深度 0）
  ⑤ FAQPage JSON-LD 42 页逐字节不变
  ⑥ 同源接线 10 条 + 短码在 42 页各渲染出一份非空列表
- **负对照**（`--neg`）**12 项 FAIL**（as required）、**破坏矩阵 11/11 全 FAIL**
  （`gate-neg.txt` / `gate-sabotage.txt`）
- **认证对账 8/8**：Site Settings 与 8 个剂型页 facts-mini 一致、0 差异（6 枚认证）
- **响应式五档**（候选）480/768/1024/1101/1440 零横向溢出；`prefers-reduced-motion` 生效；
  hover 正负对照用 init-script stub 改写 `matchMedia`，证明切换是媒体查询门控而非"打开就有"

## 上线八步（2026-09-22 06:15–06:40 UTC+8）

1. **`pull --ff-only`**：服务器 `site-repo` `1d4bd965ab38c7c4ae1b9f65c18d6795f08e08a3` → **全 SHA 校验 = `c1f6a35673d637689514e851afeca5cb3e3d619d`**、工作树 clean、`6 files changed, 740 insertions(+), 75 deletions(-)`。
   主题目录是**软链**（`themes/sinofresh-theme → site-repo/sinofresh-theme`），pull 即刻换字节。
2. **服务侧验证**：`style.css` 头 `Version: 2.10.55` 与 `functions.php:31` 同源；`formula-gallery.js?ver=2.0.0`；
   详情页含 `sf-fdetail2` **8 处**、旧命名空间 `sf-fdetail-media` **0 处**；**8 个剂型页配置器原封不动**
   （`configurator.css?ver=2.9` / `configurator.js?ver=2.3` / `basket.js?ver=1.3.0`，H2b 未动）。
   live `style.css` 抓取 sha = `d867e8827a22…` = 工作树字节。
3. **live 75 页掩码比对（硬指标）**：以同一套 42 页声明对 live 字节重跑主门 → **PASS 18/18**；
   逐页清单 `docs/batchH2a-gates/live-page-compare.txt` = **DIFF 42（恰为 21 en + 21 zh 详情页）/ SAME 33**，
   其余页差异仅 `style.css` 版本令牌（折叠后 identical）。
4. **live 浏览器 E2E**（`tools/b2d_h2a_responsive.py --mode live`）：五档零横向溢出；
   两栏档（1101/1440）轨道 **72×332**、缩略图 72×72；参数行 **6/6**、认证 pill **6/6**；
   移动设备视口 393px 零溢出；reduced-motion 生效；**0 页面错误**（`agent-browser errors`）。
   ⚠️ 同时断言**来源**：live 档要求资产 URL **不含** `-preflight` 且 `ver=2.10.55`（防止把预检副本当 live 报告）。
5. **拆预检副本**：`themes/sinofresh-theme-preflight`、`mu-plugins/zz-sf-preflight.php`、预检日志**三件全删**，
   只剩常驻 `zz-sf-dev-lockdown.php`。复验 `X-SF-Preflight: 1` **已失效**：带/不带头两次抓取
   **掩码后 sha 相同**、页面 `preflight` 字符串 **0** 处。
6. **错误日志逐条归因**：显式窗口 `2026-09-21T21:15:00Z → 22:35:00Z`；**归因清除 134 条、记账 53 条
   （16 个时间戳）、无法归因 0 条 → PASSED**（`logaudit-h2a.txt` + `logaudit-h2a-allow.txt`）。
   窗口内 9 行全部ours/可归因，明细见下节。
7. **身份链 + 仓库 md5**：见文末。
8. **文档与记忆**：本文档 + `.workbuddy/memory/2026-09-22.md` + `MEMORY.md`（含 H2b 待办）。

## 日志归因明细（记账的 16 个时间戳）

窗口内 9 行（旧口径"窗口内必须 0 条"已被证伪 —— 本批窗口内含我们自己的认证握手流量）：

| 时间（UTC） | 条数 | 归因 |
|---|---|---|
| 21:38:52 / 21:38:53 | 2 | **ours**：agent-browser 在 `Authorization` 头生效前先打了一次 `GET /`（访问行：user `sfdev`、401、UA `HeadlessChrome/153`） |
| 21:41:01 / 21:41:27 | 3 | **ours**：我们的 cookie 横幅探针 `?sfcap=cookieprobe[2]`（缓存串是我们自己编的），同秒 401 |
| 22:05:51 / 22:11:01 / 22:11:10 | 3 | **ours**：ssh 侧 `curl -u base64(凭据)` 把 base64 当成了用户名（访问行 user 字段就是那串 base64、401、`curl/7.76.1`） |
| 22:12:34 | 1 | **third party**：`DuckAssistBot` 被封锁挡住（访问行 user `-`、403），在窗口内但从来不是我们 |

窗口外 44 行（全部属于**批 H1**、已在 H1 文档记账，非本批引入）：
03:38:30 ABSPATH 探针（1）、09:10:58–09:11:03 preflight 副本 redeclare 突发（42，同秒 500 行 user `sfdev` + `curl/8.7.1`）、
14:45:23 MaxRequestWorkers（1，H1 并发抓 75 页）。

## 三条自我修正（记功）

1. **「190 行」应为 189**：拆开＝**189 条内容 meta + 1 条 H1 自己漏删的 `_edit_lock`**（post 178，`1789996083:1001`，
   用户 1001 已删）。归因证据＝访问日志 `post=178` 301 条，末条 13:07:33 GET + 13:08:03 POST，UA `HeadlessChrome/153` + `sfdev`
   ⇒ H1 早期版 E2E 的目标帖，后改 158。真不变量＝**内容 189 行不变**（sha `fc6426d4…`）。
2. **Piece Weight 的真相比预想麻烦**：它**不是**读后台 `Weight per piece` 字段，而是**从 Standard Specs 解析**。
   于是粉/膏/滴/液体/鱼油这 11 条今天把**整瓶容量**印成了 "Piece Weight"
   （`4oz/8oz/16oz jar`、`50g/60g/100g/120g tube`、`30ml/50ml dropper bottle`、`8oz/16oz/32oz pump bottle`）。
   已在 `docs/h2a-data-checklist.md` §3 给出逐条建议写法。
3. **「11 条 6 行 / 10 条 5 行」是反的**：实测 **10 条 6 行**（软咀嚼 4+片剂 3+洁齿 3）、
   **11 条 5 行**（粉 3+膏 2+滴 2+液体 2+鱼油 2）。

## 工具缺口与教训（写给下一批）

- ⛔ **门不许用子串判 marker**：`sf-fdetail2__intro2` 会命中 `sf-fdetail2__intro`，
  导致破坏矩阵 `intro-class-lost` / `cta-lost` 漏网。改用 **class token 集合**（按空白切分后精确匹配）
  且断言限定在目标区域内。
- ⛔ **`grep` 命中要看位置**：类名 token 可能在 PHP **字符串里拼出来**（`functions.php:3518` 硬编码
  `<p class="sf-fdetail-media__intro">`）。"某旧规则已无使用者"必须逐条看命中所在行是不是活引用。
- ⛔ **设备模拟 ≠ 媒体环境**：`agent-browser set device` 只换 UA 与布局视口，`maxTouchPoints` 仍 0、
  `(hover: hover)` 仍 true ⇒ 触屏/悬停断言必须用 **init-script stub** 做**正负对照**。
- ⛔ **截图假象 ≠ 布局错误**：cookie 横幅遮挡、元素高于视口时溢出部分画成空白，都会误判"没渲染"。
  **几何测量（`getBoundingClientRect`）才是判据**，测量用原视口高、截图另开高视口，两者分离。
- ⛔ **`curl -u` 只吃明文** `user:pass`：喂 base64 会被当成**用户名**并弹交互式密码提示 ⇒ ssh 静默挂死。
  （本次日志归因的三条 AH01618 就是这个坑的现场证据。）
- ⛔ **`json.dumps()` 会把本地非 ASCII 路径转义**（`\u5916…`）⇒ `scp` 找不到文件；本地路径用 `shlex.quote`。
- ⚠️ **日志工具 `b2d_s5_logaudit.py` 的已知边界**：`classify()` 在**窗口判定**处直接返回 FAIL，
  窗口内的行**不做内容归因**（设计如此，靠 `--allow` 逐条记账）；因此窗口里出现外部 AI 爬虫噪声时，
  也必须给一条 `--allow`（本批 22:12:34 的 DuckAssistBot 即此例）。下一批若嫌啰嗦，可在 `--allow` 前
  先跑内容归因并只把"判为 ours"的行升级为 FAIL —— 但这会改变闸门语义，需单独评审。

## 遗留与待办

- 📋 **批 H2b（未开工）**：① **8 个剂型页配置器删除**（含 CTA 改向、chips 移位）——
  ⛔ 注意 `inc/config-pdf.php` 被 `basket.js` 共享，**删配置器不能删端点**；
  ② 本批实测 8 个剂型页三件资产（configurator.css 2.9 / configurator.js 2.3 / basket.js 1.3.0）**均未动**，是 H2b 的基线。
- ✅ **H2c 已完成**（搭 H2a 车）：precheck 横幅在区块编辑器 `Save` 下触发（正则 1.0.1），
  E2E 实测横幅文案已列出 11 项缺项（H1 同处测得 0 条）。
- 📋 **2D 第 6 批候选**：MOQ 重复对账（FAQ vs 详情页 meta）。
- 📋 **残留**：实拍图 34 张、详细介绍 21 条全空、≤1239px hero 贴边、首页 `<title>` 仍是 `sinofresh`。
- 📋 **运营待补**：`docs/h2a-data-checklist.md` 的 21 帖 × 4 键（flavors / species / lifestage / price_tiers）
  = **84 格**全空；另粉/膏/滴/液体/鱼油五剂型 11 条需补真正的 Piece Weight。

## 身份链与仓库 md5

- 身份链（`tools/b2d_s3_identity.py`，workspace ↔ site-repo live 主题）：
  **__IDENTITY__**
- 仓库 md5（`tools/sf_repo_md5.py --exclude 本文档`，JSON `_backup/b2d-h-baselines/repo-md5-h2a.json`）：
  **__REPO_MD5__**
- 闭包时服务器 HEAD：**__CLOSURE_HEAD__**（本地 `/tmp` 无残留、`/root` 无残留；
  预检副本三件已删；`screenshots/` 与 `_backup/` 按 `.gitignore` 不进仓库）
