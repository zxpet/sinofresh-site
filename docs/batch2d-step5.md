# 批次 2D · 第 5 批 — 剂型页「核心事实行 + Direct Answer」

一句话：每个剂型页在 hero 之后、配方卡墙（`#formulas`）之前，多了一条**不带标题**的事实带
（5 行表格 + 一段 50–80 词摘要），并把 How We Work 第 03 步的 `3–7 days` 统一成
`3–7 working days`。

- **产品 commit** `cc21dfc`（8 模板 + `style.css` 2.10.50 → **2.10.51** + `functions.php`）
- **工具/文档** `6eb19f3`（重写器 + 门）→ `f1b56ea`（三个门缺陷修复 + 取证工具 + 日志归因工具 + 取证件）
- **改前备份** `sinofresh-theme/_backup/b2d-step5-baselines/src/`（改前的 8 模板 + `style.css` + `functions.php`，
  经 `git show HEAD~1:` 导出，断言 `Version: 2.10.50`、8 模板 `B2D-S5` 计数 0）

---

## 1. 改了什么，为什么

### 拍板（本批开工前的六个待定项）

| # | 决策 | 理由 |
|---|---|---|
| D1 | **纯新增并存**，不碰第 4 段的 `.sf-spectable` | 事实表与 spectable 有 MOQ / Lead time / Pack options 三处重叠，去重风险大；本批只新增 |
| D2 | 事实行在**前**，摘要段在**后** | 先给数字再给散文，符合采购方的扫读顺序 |
| D3 | Packaging **从配置器抄** + `+ custom formats` | 单一真源；配置器 `data-group="packaging"` 是站点里该剂型可选项的权威列表 |
| D4 | 本批**不进 JSON-LD** | 摘要块形态未定，先不引入结构化数据变动 |
| D5 | 事实行用**表格 + `<caption>`** | `.sf-spectable` 已建立的先例：`<caption>` 提供可访问名而**不产生 `<h2>`** |
| D6 | 本批**一起修** How We Work 的 `3–7 days` → `3–7 working days` | 同一批要写 Sample lead time，留着两种写法会自相矛盾 |
| 补1 | Packaging 写 `选项1, 选项2, …, + custom formats` | 散文读法，不与配置器的逗号列表混淆 |
| 补2 | D6 顺手修正 How We Work **第 03 步** | 八页那句原文逐字节相同，一次改动覆盖八页 |
| 补3 | 新建 **`.sf-facts`** 类，不复用 `.sf-spectable` 类名 | 只复用视觉 token（细线行、无竖线、11px letterspaced caption、ink 值、堆叠逻辑），类名解耦 |

### 位置与形态

插入点：八页的 hero 闭合行**都是第 27 行**，第 28/29 行逐字节唯一（Python 验证
`L27/L28/L29 unique values: 1`）⇒ 单一锚点字面量即可安全插入，无需按页判断。

```html
<!-- B2D-S5: core facts -->
<!-- wp:group {"tagName":"section","className":"sf-facts", …} -->
<section class="wp-block-group sf-facts" …>
<!-- wp:html -->
<table class="sf-facts__table">
<caption class="sf-facts__caption">Core facts — Soft Chews</caption>
<tbody>
<tr><th scope="row">MOQ</th><td>from 500–1,000 units</td></tr>
<tr><th scope="row">Sample lead time</th><td>3–7 working days</td></tr>
<tr><th scope="row">Production lead time</th><td>7–15 working days after packaging is ready</td></tr>
<tr><th scope="row">Certifications</th><td>FDA, cGMP, ISO 9001, FSSC 22000, HACCP, BRC</td></tr>
<tr><th scope="row">Packaging</th><td>…, + custom formats</td></tr>
</tbody></table>
<!-- /wp:html -->
<!-- wp:paragraph {"className":"sf-facts__answer"} -->
<p class="sf-facts__answer">…Direct Answer…</p>
<!-- /wp:paragraph -->
</section>
<!-- /wp:group -->
<!-- /B2D-S5 -->
```

⛔ **不带 `<h2>`** 是硬约束：`toc-nav.js` 用 `root.querySelectorAll("h2")` 按顺序编号 `sf-sec-N`，
新块若带 H2 会让点轨 7 个点全部移位。可访问名交给 `<caption>`。

**Direct Answer** 是同一模板句 + 四个变量（`{product}` / `{benefits}` / `{moq}` / `{pack_forms}`），
八页 61–75 词：

> {product} are manufactured to FDA, cGMP, ISO 9001, FSSC 22000, HACCP and BRC standards, with a
> flexible MOQ {moq} and samples ready in {sample}. Formulated for {benefits}, they ship in
> {pack_forms} or custom formats. Bulk production takes {prod}.

数据全部取真值：MOQ 抄 `.sf-spectable` 第 4 列、Packaging 抄配置器 `data-group="packaging"`
（去掉结尾的 `Custom` 再加 `+ custom formats`）、`{benefits}` 取各页自家 `sf-schema-desc`。
fish-oil 是唯一 schema-desc 讲形态不讲功效的页，其 `{benefits}` 改取自家 functions 列表。

### D6

`Detailed quotation plus samples delivered in 3–7 days.` → `… in 3–7 working days.`（八页各 1 处）。

### CSS

`style.css` 末尾追加 3749 B（100 行）：`.sf-facts` / `.sf-facts__table` / `.sf-facts__caption` /
`tbody th`（220px 标签列、12px/700/uppercase/次色）/ `tbody td` /
`.sf-facts .sf-facts__answer`（860px 上限、24px 上边距、20px 上内边距、细线分隔）/
`@media (max-width: 767px)` 堆叠。

⛔ 摘要段的选择器必须是**双类** `.sf-facts .sf-facts__answer`：WP core 的
`:where(.is-layout-constrained) > * { margin-block-start: 24px }` 权重 0,1,0，
单类选择器压不住，上边距会是 24px 而不是设计值。

⛔ **不改 `.sf-spectable`，也不改它的任何一条声明。**

---

## 2. 六门 + 负对照（`tools/b2d_s5_confine.py`）

| 门 | 结果 |
|---|---|
| [1] 资源清单 | `style.css 2.10.50 → 2.10.51` on **75 页**；asset **SET 变动 0**（`NOTHING moved` 即 FAIL） |
| [2] 掩码比较 | **differ 16 / identical 59**；期望 16 = 8 剂型页 + 8 个 `/zh/` 孪生页（**是集合不是计数**） |
| [2b] 页级限定证明 | **16/16** 页：删 band 的 span + 还原那句话 → 与基线**逐字节相同** |
| [3] 源级重建 | `style.css` 258083 → 261832 → undone **258083**；`functions.php` 168850（本批无实质改动）；8 模板 base → new → undone **全部等于 base**，每份 `applied:YES undone==base:YES` |
| [6] JSON-LD | **75/75** 页 decoded 结构 deep-equal |

**负对照**（`--new` 指向 base 自身）**FAIL 62 条 / RC=1**（`docs/b2d-step5-negctl.txt`），
失败点包括 `NOTHING moved — the two directories have identical version tokens`、
16 条 `should have differed and did not`、16 条 `band span is not present`、
以及 16 条模板声明 `occurred 0 time(s)`。
⚠️ 注意门 [6] 在负对照里**仍报 75/75 identical** —— 它天生看不见「自己跟自己比」，
这正是不变量式的门 [1] 存在的理由。

---

## 3. 渲染取证 29/29（`tools/b2d_s5_evidence.py`，预检副本上跑，上线后复跑同样 29/29）

1440×900：

```
hero   top 120  bottom 448
band   top 472  bottom 948      ← 与 hero 只隔 24px
#formulas top 972               ← 与 band 底只隔 24px
row tops above 900: [539, 578, 618, 658, 698]   ← 5 行全在首屏
answer 763..908                 ← 摘要在首屏内开始
band left edge 120 = 页面度量左缘
```

- band 内 `<h2>` 数 **0**；页面 h2 列表与基线**逐项同序**（基线侧从字节读，两侧独立；
  ⛔ 必须 `html.unescape`，否则 `&amp;` vs `&` 假 DIFF）
- 375px：band 375 宽、无横向滚动、`th`/`td` 都 `display:block`、5 行标签都还在、摘要 75 词、
  点轨 7 个点不变

**负对照**：注入 `.sf-facts{padding-top:1400px !important}` 后比**第一行行顶边**（不是 band 盒子顶边
—— padding 不移动盒子顶边，第一版比盒子顶边测到 0px 位移、什么都没证明），实测 **+1360px**，
首屏内的行数塌到 0。

---

## 4. 上线与闭环

`git pull --ff-only`（12 files changed）→ 服务侧 `style.css?ver=2.10.51`、页面含 band →
抓 live 75 页 → `sf_masked_cmp new live` **75/75 identical / DIFF 0 / 每页 18 个
`preflight_theme_dir` 掩码**（`docs/b2d-step5-shots/closure.txt`）→ 上线后
`--live --expect-ver 2.10.51` 复跑取证 **29/29 PASS**（`evidence-live.txt`）。

**线上从不服务未过门的字节**：候选经 `X-SF-Preflight: 1` 整站抓 75 页跑全套门，过了才 `pull --ff-only`。

---

## 5. 拆除、日志（按归因）、仓库级一致性

### 预检脚手架拆除

`tools/b2d_s1_preflight.py remove` → `no preflight theme` / `no preflight mu-plugin` /
`no preflight log`，`mu-plugins/` 只剩常驻 `zz-sf-dev-lockdown.php`；
主题符号链接仍指向 `site-repo/sinofresh-theme`；拆除后线上 200 / `2.10.51` / 含 band，
带预检头也正确回落到 live 主题。

预检日志 85 行已归档 `docs/b2d-step5-shots/s5-preflight.log.txt`：
**85/85 都是 `theme=sinofresh-theme-preflight`**（零泄漏到 live 主题），覆盖 75 个不同 URI。

### 错误日志 —— 口径从「体积不变」改为「**每一条都能归因**」

新工具 `tools/b2d_s5_logaudit.py`（`docs/b2d-step5-logaudit.txt`）。体积/mtime 不是不变量：
这台机器在公网上，随机扫描随时写入。可靠的问题是「这一行是谁的」。

**判别符是访问日志的认证用户名字段**（dev 全站 Basic Auth，`combined` 格式第 3 字段）：
我们的工具只会写 `sfdev`，全日志 10481 行里用户名只有三种 ——
`-` 5686 / **`sfdev` 4792** / `admin` **2**。那 2 次 `admin` 与 error log 里 2 条
`AH01618: user admin not found` **一一对应**，一次不差。

窗口由归档的预检日志推出：**23:50:13 → 23:54:42**（±5 分钟为 23:45:13 → 23:59:42）。
窗口内访问日志 1436 行：**ours（sfdev）1060 行**、外部 376 行**全部 401**
（未过 Basic Auth ⇒ 从未到达 PHP ⇒ 结构上不可能写 error log）。

四份日志共 **27 条记录，逐条归因，窗口内 0 条**：

| 日志 | 记录数 | 归因 |
|---|---|---|
| `dev.zxpet.com-ssl-error.log` | 10 | 4× Apache 重启 `AH01909`（源站证书名不匹配，与批次无关）；3× `/.htpasswd(.bak)` 探针（本机 127.0.0.1 自查 403 + 两个外部 IP 403）；2× `user admin not found`；2× `/cgi-bin/.%2e/…` 漏洞扫描 |
| `dev.zxpet.com-error.log` | 0 | 80 端口 vhost 无 TLS 流量 |
| `/var/log/httpd/error_log`（全局） | 15 | **全部是 Apache 启动/graceful restart 通知**（00:00 / 05:39 / 05:46 / 14:18），最后一条 14:18:42，早于批次 |
| `/var/log/php-fpm/www-error.log` | 2 条记录 / 5 行 | ① `parts/footer.html` 读不到（05:49:31，主题刚部署时；**该文件现在存在 16752 B**）；② `ABSPATH` fatal（09:36:32）——**同一秒** `35.205.254.119` 直请 `/wp-settings.php` → **500**，是该请求的后果 |
| `wp-content/debug.log` | — | mtime `2026-09-19 22:56`，`WP_DEBUG=false`，批次期间零写入 |

**负对照**：把窗口平移到 09:36（盖住扫描器那条）→ **RC=1**，2 条 `inside the batch window`
（`docs/b2d-step5-logaudit-negctl.txt`）⇒ 门确实会响。

顺带坐实：lockdown 是在 **14:18** 生效的。之前未认证请求有 3014 个 200（站点是开着的），
之后未认证请求非 401 的只剩本机自查与 Apache 在鉴权前就拒掉的畸形请求（400）。

### 身份链与仓库级 md5

- `tools/b2d_s3_identity.py`：工作区 ↔ 实服务主题 **691 文件 0 不一致**
  （`docs/b2d-step5-shots/identity.txt`）。本批未在主题目录新增文件，故与 4c 同为 691。
- `tools/sf_repo_md5.py`：见 `docs/b2d-step5-shots/cloud-md5.txt`。
  ⛔ `--exclude` 传入未跟踪的路径会**直接拒绝运行**（否则排除是个空操作、静默什么都没缩小）。
  因此本批的记录与本报告都在被比较集合**之外**：报告不能是它所报告集合的成员，
  记录里又写着报告的结论 —— 两个文件都不存在稳定值。排除后**逐字节可复现**：
  同一条命令再跑一次，输出与入库报告 `cmp` 相同。

---

## 6. 本批在工具里抓到的三个真 bug + 一条口径修正

门第一次全量跑就 FAIL 40 条，**没有一条是站点的错**：

1. **声明对方向写反**。写成了 `(新, 旧)`，而契约是 `(restore_this, currently_present)` ⇒
   工具报告「明明在文件里的字面量出现 0 次」。改成 `(旧, 新)`。
2. **用空字面量表达「删除」**。`count('')` 返回 len+1（56837 次），`replace('', X, 1)` 是**前插**而非删除，
   于是「删掉这段 CSS」静默什么都没做。现在空字面量直接 FAIL，`None` 表示纯插入。
3. **span 校验匹配带闭合引号的类名**。渲染后是 `class="sf-facts__answer wp-block-paragraph"`
   （core 会给自己追加类），`'class="sf-facts__answer"'` 匹配不到，把一个完全正确的页面判死。
   改成不带引号匹配，并加断言 span 内 `<h2>` 数为 0。

渲染取证首跑另有 4 条 FAIL，其中 2 条是**真实几何发现**（不是 bug）：1440×900 下 band 底 948 > 900，
5 行字段全在首屏、摘要起始也在首屏，只有散文最后两行溢出 ⇒ 断言从「band 底 ≤ 900」改成
「摘要起始 < 900」，band 底/摘要上下沿作为**实测数字**打印而非断言。

**口径修正（记功）**：「错误日志零新增」不能拿体积/mtime 当不变量。4c 那次实测 1494 → 1939 B，
新增两行来自外部 IP 的 `/cgi-bin/.%2e/…` 探测。可靠的不变量是「**每一条都能归因**」。

---

## 7. 产物清单

| 路径 | 说明 |
|---|---|
| `sinofresh-theme/templates/page-{soft-chews,tablets,powders,pastes,drops,liquids,fish-oil,dental-chews}.html` | 8 页各 +38 行（2 个 hunk），How We Work 各改 1 行 |
| `sinofresh-theme/style.css` | `Version: 2.10.51` + 末段 3749 B |
| `sinofresh-theme/functions.php` | enqueue 版本 `2.10.50` → `2.10.51`（唯一改动） |
| `tools/b2d_s5_apply.py` | 幂等重写器（`--check`/`--apply`，`CSS_ADDITION` 与 `block()` 由门 import，避免两份拷贝） |
| `tools/b2d_s5_confine.py` | 六门（资源清单 / 掩码 / 页级限定证明 / 源级重建 / JSON-LD） |
| `tools/b2d_s5_evidence.py` | 渲染取证 29 项（含「拿到的是哪一份」与负对照） |
| `tools/b2d_s5_logaudit.py` | 错误日志**按归因**审计（本批新增） |
| `docs/b2d-step5-gates.txt` / `-negctl.txt` | 六门 PASS / 负对照 FAIL 62 |
| `docs/b2d-step5-logaudit.txt` / `-negctl.txt` | 日志归因 PASS / 负对照 RC=1 |
| `docs/b2d-step5-shots/` | 6 张截图（preflight / live × 1440 / 1440-hero / 375）、`evidence*.{txt,json}`、`closure.txt`、`identity.txt`、`s5-preflight.log.txt`、`cloud-md5.txt` |
| `_backup/b2d-step5-baselines/{src,base,new,live}` | 改前源码 + 三份 75 页取样 |

---

## 8. 遗留（不在本批）

- ③ 详细介绍 `post_content` 全空（21 条配方）
- ≤1239px hero 贴边
- 实拍图 34 张
- **MOQ 在站点里已出现第 3 次**（FAQ / `.sf-spectable` / 本批 `.sf-facts`）⇒
  独立小批次：新块与 `.sf-spectable` 的重复/漂移对账
- 配置器 Packaging 选项集与 `.sf-facts` Packaging 行同源，未来任一侧改动需要同步
