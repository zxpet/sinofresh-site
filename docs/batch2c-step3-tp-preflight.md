# 批次 2C 第三步 · TranslatePress 重收录 —— 执行前确认书

> 状态：**已确认，未执行**（本文档只是确认结论，除备份外未对站点做任何写入）。
> 对象：TranslatePress 3.3.6（`translatepress-multilingual`）+ 1.7.6（`translatepress-business`）
> 目标：把 2C Step2 引入的新英文串收进 TP 翻译表，使 `/zh/` 页面上的这些串可被翻译。

---

## 0. 先纠正一条旧结论

旧记忆写的是「访客渲染（含 `/zh/`）不注册新串（实测三表 Δ0）」。**这条是错的**，本次推翻：

- 字典表 id **1239–1290** 全部是本批次页面的串（21 条配方描述、`More <form> Formulas`、`Specification`、
  `Showing`、`of 21 formulas`、`Filter formulas by dosage form`、`Our Products`、`All Formulas` …）。
- 决定性证据：id **1282 = `Formulas – 第 2 页 – sinofresh`** —— 含中文「第 2 页」，只可能由 `/zh/` 前台渲染产生
  （英文页渲染不可能出现中文分页词），而该 URL 现在已被 301 挡掉、无法再复现。

⇒ **`/zh/…` 的真实前台渲染会注册串**；英文页渲染不会（源码注释见下）。

---

## 1. 重收录范围逐串核验

### 1.1 机制：串走哪张表，取决于它怎么被输出

| 输出方式 | 落表 | 判定依据 |
|---|---|---|
| **gettext 路由** —— 被 `__()/_e()/_n()` 包裹 | `wp_trp_gettext_original_strings` + `wp_trp_gettext_zh_cn` | TP 监听 gettext 调用 |
| **常规路由** —— 裸文本节点 / `esc_html('字面量')` | `wp_trp_original_strings` + `wp_trp_dictionary_en_us_zh_cn` | TP 解析页面 HTML |

渲染时 TP 还会给出身 gettext 的节点盖标记，实测 `/zh/formulas/` 上：

```html
<p class="sf-archive-count has-card-white-color" style="…" data-no-translation="" data-trp-gettext="">21 formulas</p>
```

`data-no-translation` 在 TP 的 `trp_skip_selectors` 列表里 ⇒ **该节点被 TP 主动跳过**，改由 gettext 表负责。

### 1.2 逐串判定（用户清单）

| 串 | 路由 | 状态 | 实证 id |
|---|---|---|---|
| `All Formulas`（导航） | 常规 | ✅ 已注册 | dict **1290**（最新一行） |
| `Formulas`（档案页 H1 + 面包屑） | 常规 | ✅ 已注册 | **1240**（`<title>` 变体 1243） |
| `21 formulas`（计数） | **gettext** | ✅ 已覆盖 | msgid `%d formulas` = gettext **1182**，译文行 **623**（status 0） |
| 9 个 chip 标签（`All` + 8 剂型） | 常规 | ✅ 已注册 | `All` **1241**；8 剂型标签 **55–62** |
| `Showing %1$s of %2$d formulas`（状态行） | 常规 | ✅ 已注册（**按文本节点拆成两条**） | `Showing` **1283**、`of 21 formulas` **1284** |
| `Browse All Formulas →`（8 剂型页） | 常规 | ❌ **未注册** | — |

补充已注册项：`Filter formulas by dosage form` **1285**、`Reference this formula →` **562**、
`Standard Formulas` **553**、`Explore dosage forms` **674**；gettext 侧 `%d article(s)` **1066** 也已在。

### 1.3 零写入对账法（本次采用）

抓 9 个相关页面的**英文版**（默认语言 ⇒ 不产生任何写入）：`/formulas/`、8×`/products/<form>/`、`/products/`，
抽出 **531 个文本节点**，与三张表逐条对账 ⇒ **只有 36 条未注册**，且全部可解释：

| 类别 | 条数 | 结论 |
|---|---|---|
| 纯数字（`01`–`07`、`21`、`500` …） | 17 | `enable_numerals_translation = no` ⇒ **故意不注册** |
| `21 formulas` | 1 | gettext 路由已覆盖（见 1.2） |
| 语言切换器 `English` / `简体中文` | 2 | TP 自带组件，非站点内容 |
| CF 邮箱混淆载荷 `[email protected]` | 1 | Cloudflare 产物 |
| 两个电话号 | 2 | 无需翻译 |
| **`Browse All Formulas →`** | **1** | **唯一真正缺失** |
| 其余 | 12 | 同一批（已在 `1.2` 归入已注册） |

**结论：本次重收录真正要收的新串只有 `Browse All Formulas →` 一条。**

它缺失的原因也定位到了：**`/zh/products/*` 从未被渲染过**。旁证 —— 同一个页面上位置相邻的旧按钮
`Browse All Products &rarr;` 已在表内（id **643**），新加的兄弟节点不在 ⇒ 典型的「页面渲染过、但这次新增之后没再在 `/zh/` 下渲染过」。

> 另：TP 保留**实体形态** —— 旧按钮存的是 `Browse All Products &rarr;` 而不是解码后的 `→`。
> 而 2C Step2-5 新增的按钮在 8 个模板里写的是**字面 `→`**（该模板族的主流写法）⇒ 定向插串时必须用字面 `→`。

---

## 2. `original_strings_sync` 的安全性

### 2.1 会不会覆盖已有翻译？——不会，机制上是纯追加

源码 `includes/class-translation-render.php`：

- **L44**：`is_admin() && !ajax_on_frontend` 或翻译编辑器 ⇒ 直接 return
- **L617 注释**：*"We have necessary checks so that we don't get to this point when is_admin(), or when language is default."*
  ⇒ **默认语言下根本走不到写库分支**
- **L1936–1963**：`$new_strings` **只在 `!isset($dictionary[$string]->translated)` 时**才收集
  ⇒ 任何**已存在字典行**的串都不进 `$new_strings`
- **L2112**：`insert_strings($new_strings, 'zh_CN', …)` 是最终写库点
- `insert_strings()` 内部：只 `INSERT`（`translated = NULL`、`status = NOT_TRANSLATED(0)`、`block_type = 0`）＋ 调 `original_strings_sync()`
- `original_strings_sync()`（`queries/class-query.php:663`）：先 `SELECT` 已存在原串、`array_diff` 去掉，**只 INSERT 缺失的**；
  且有一条硬门 **`if ($this->settings['default-language'] != $language_code)`** ⇒ **必须以 `zh_CN` 调用**才会写
- `update_strings()` 只在 `$update_strings` 非空时跑，而后者只服务「相似串」特性 —— 本站
  `serve_similar_translation = no` ⇒ 该分支为空

**⇒ 全程无 UPDATE / DELETE，只有 INSERT。已有行不可能被改写。**

### 2.2 会不会影响 `/blog/`、`/products/*`、`/contact/` 等已有翻译？——不会

- 本站字典表现在是 **1290 行、status 全 0、translated 全空** ⇒ **中文站目前是零翻译、全英文回落**，本来就**没有已有翻译可影响**
- 唯一有真实译文的 476 行在 **gettext 表**（`status = 4`，插件自带语言包）
  → `original_strings_sync()` / `insert_strings()` **完全不碰 gettext 表** ⇒ 不受影响

### 2.3 ⛔ 两条必须知道的修正/风险

1. **`original_strings_sync()` 单独调用是不够的。**
   它只写 `wp_trp_original_strings`（原串表）；而 **TP 翻译界面读的是字典表**
   （`class-editor-api-regular-strings.php` → `get_string_rows()`）。
   ⇒ 要「出现在 TP 翻译界面」，必须调 `TRP_Query::insert_strings($strings, 'zh_CN')`（它内部会先调 `original_strings_sync()`）。
   原计划里记的 option B（`original_strings_sync('zh_CN')`）应据此升级为 `insert_strings()`。

2. **两张表都没有 `original` 的 UNIQUE 键**（只有 `KEY index_original(original(100))`）
   ⇒ **重复执行会造重复行**。而且这不是假设 —— **实测库里已存在 7 组重复**：

   | 原串 | 重复 id |
   |---|---|
   | `Oral care` | 634 / 1069 |
   | `Plaque control` | 1065 / 1093 |
   | `Urinary Care` | 633 / 925 |
   | `Skin & coat` | 569 / 631 |
   | `Shelf life` | 637 / 793 |
   | `Client Stories` | 313 / 397 |
   | `Copy Link` | 825 / 831 |

   ⇒ 执行后必须对目标串断言「**恰好 1 行**」，而不是「≥1 行」。

### 2.4 执行时间

- 表极小（最大 512 KB，`wp_trp_gettext_original_strings`）⇒ 单条 `insert_strings` 是 3 条 SQL，**远小于 1 秒**
- 走「渲染收集」路线则是 9 次页面 GET，**约 5–15 秒**
- **无 WP-CLI 命令、无批处理、无超时风险、无机器翻译计费**（DeepL add-on 未启用）

### 2.5 回滚方案（**备份已做**）

```bash
# 已执行（10 张 trp 表，带 DROP TABLE IF EXISTS，可整份导回）
/root/tp-backup-20260920-115727.sql   # 425104 B，10×CREATE TABLE / 7×INSERT，以 "Dump completed" 收尾
```
- **整份回滚**：`mariadb -u root -p… sinofresh < /root/tp-backup-20260920-115727.sql`
- **轻量回滚**：本操作只追加、id 单调 ⇒ `DELETE FROM wp_trp_* WHERE id > <执行前 MAX(id)>`
- 执行前基线（已记录）：originals **1290**／dict **1290**（MAX id **1290**）／gettext_orig **1178**／gettext_zh_cn **623**（147×status0 + 476×status4）

---

## 3. 执行方式

### 3.1 有没有 WP-CLI 命令？——没有

全插件搜 `WP_CLI::add_command` 结果为空。可用的只有两条：

| 路线 | 做法 | 优点 | 风险 |
|---|---|---|---|
| **1（推荐）** | 前台 GET `/zh/…`，让 TP 自己收 | 走插件自己的管线，**串的字面量必然与 TP 提取到的一致**；顺带把可能漏判的串一并收掉 | CF 缓存 |
| **2** | `wp eval-file` 调 `insert_strings(['Browse All Formulas →'], 'zh_CN')` | 精准、可断言 | 串的字面量需人工对齐（实体 vs 字面 `→`） |

⛔ **路线 1 必须破 CF 缓存**：CF 给 HTML 盖 `cache-control: max-age=86400` 且**按 URL 缓存**，
命中缓存时 origin 不执行 ⇒ **什么都不会注册**。做法：带唯一 query 串，例如
`curl -s -o /dev/null "https://dev.zxpet.com/zh/products/soft-chews/?trpsync=$(date +%s)"`。

建议：**先路线 1；若对账后仍有缺失，再用路线 2 定向补齐。**

### 3.2 执行前是否备份 TP 表？——是，**已完成**

见 2.5。备份落在 `/root/tp-backup-20260920-115727.sql`（站外目录、不进 Git）。

### 3.3 执行后如何验证

1. **入队断言（SQL）**：目标串在 `wp_trp_dictionary_en_us_zh_cn` **恰好 1 行**、`status = 0`、`translated IS NULL`、
   `original_id` 非空且能在 `wp_trp_original_strings` 里对上
2. **界面可译**：TP 翻译界面搜索 `Browse All Formulas` 能命中；浏览器打开 `/zh/products/soft-chews/` 该按钮可点取翻译
3. **gettext 侧未被动**：`wp_trp_gettext_zh_cn` 的 status 分布仍为 **147 / 476**
4. **其他页翻译不受影响**：`/zh/blog/`、`/zh/products/*`、`/zh/contact/` 与执行前**逐字节一致**（掩码回归；
   空译文回落原文 ⇒ 结构本不应变化）
5. **重复行未新增**：`GROUP BY original HAVING COUNT(*)>1` 仍是 7 组（不因本次执行增加）
6. **回滚演练（可选）**：用备份导入一次，确认 `/zh/` 页面字节回到执行前

---

## 4. 顺带发现（Step2 残留，非本步引入）

`/zh/formulas/` 的**可见面包屑当前是 `归档： Formulas`**：

```html
<span class="sf-breadcrumb__crumb sf-breadcrumb__current" aria-current="page">归档： Formulas</span>
```

- 原因：R6 剥离正则 `'/^(?:…|归档)\s*[^:：]*:\s*/'` 末尾的冒号是 **ASCII `:`**，
  而 WP zh 输出的是**全角 `：`** ⇒ `[^:：]*` 吃不到、`:` 又匹配不上 ⇒ 前缀没被剥掉。
- H1 干净（`Formulas`）是因为 H1 走 `wp:query-title`，不经过这个正则。
- 该串**也不在 TP 表里**（全库仅 6 条含中文的原串，不含它）—— 与它同页、同为文本节点的 `Showing`/`of 21 formulas` 都注册了，
  这一点尚未解释清楚，**建议在浏览器里复看一下该面包屑**再定。
- 修法（一行）：把末尾 `:` 改成字符类 `[:：]`，顺带清掉正则里重复的 `Classification|Classification`。
  **属 Step2 残留，需单独拍板，不建议塞进本次 TP 步骤。**

---

## 5. 待拍板

- 路线 1 还是路线 2？（建议：先 1，再按对账结果补 2）
- 是否同意把 option B 从 `original_strings_sync('zh_CN')` 升级为 **`insert_strings($strings,'zh_CN')`**（否则串进不了界面）
- §4 的面包屑残留是否另开一个小批次处理

---

# 执行记录（2026-09-20 20:0x，路线 1 执行完毕）

> 用户已拍板：① 先路线 1、按对账结果补路线 2；② 同意 option B 升级为 `insert_strings($strings,'zh_CN')`；③ 面包屑残留另开小批次。
> **实际结论：路线 1 一次到位，路线 2 未启用。**

## 6. 执行

9 个 URL，全部带唯一 query 绕 CF 缓存（`?sfcap=sync<epoch>`），User-Agent 用桌面浏览器串：

| URL | CF 判定 | 目标按钮在响应体 |
|---|---|---|
| `/zh/formulas/` | `cf-cache-status: DYNAMIC` | 0（档案页本就没有该按钮） |
| `/zh/products/{soft-chews,tablets,powders,pastes,drops,liquids,fish-oil,dental-chews}/` | 同上，8/8 `DYNAMIC` | **8/8 各 1 处** |

`DYNAMIC` = CF 判定不可缓存、**每次都回源**（比 cache HIT 更直接的可信信号；带 query 是双保险）。

## 7. 对账结果

### 7.1 目标串

| 项 | 实测 |
|---|---|
| `wp_trp_dictionary_en_us_zh_cn` 中 `Browse All Formulas →` | **恰好 1 行**（id **1312**） |
| `original` | `Browse All Formulas →`（**字面 `→`**，与模板写法一致，非 `&rarr;`） |
| `status` | **0**（未翻译） |
| `original_id` | **1312**（非空，指向原串表同一行） |
| `block_type` | 0 |
| 原串表 `wp_trp_original_strings` | 同一串 **1 行**（id 1312） |
| 重复组数 | dict **7 / 7**、orig **7 / 7** —— **与执行前完全一致，未增加** |

### 7.2 全表增量与「零覆盖」取证

| 项 | 执行前 | 执行后 |
|---|---|---|
| `wp_trp_original_strings` | 1290 | **1333**（+43） |
| `wp_trp_dictionary_en_us_zh_cn` | 1290 | **1333**（+43） |
| id 范围 | 1..1290（连续） | **1..1333（连续，COUNT=DISTINCT=1333）** |
| `wp_trp_gettext_original_strings` | 1178 | **1178**（不动） |
| `wp_trp_gettext_zh_cn` | 623 = 147×status0 + 476×status4 | **623 = 147/476**（不动） |

取证方法：把备份 `tp-backup-20260920-115727.sql` 导入临时库 `sfs3_bak`，与现表做**行级指纹 diff**（`md5(original)|status|translated|original_id`）：

- **备份有、现在没有 = 0** → 没有任何已有行被删除
- **同 id 但内容不同 = 0** → 没有任何已有行被 UPDATE
- **现在有、备份没有 = 43** → 纯追加

导入过程本身也**验证了备份可用**（回滚方案不是纸面承诺）。临时库已 `DROP`。

### 7.3 43 行新串的来源（如实说明）

| id 段 | 行数 | 来源 | 说明 |
|---|---|---|---|
| 1291–1311 | 21 | **`/zh/blog/`** | `Blog &amp; Resources`、`9 月 10, 2026`、5 篇 Case Study 标题+摘要、`Stay Updated`、`Blog – sinofresh` 等。**由本轮早先的「路径可用性探测」那批 curl 触发**（它与基线读数命令并行执行，所以基线里 `COUNT(*)=1290` 与 `MAX(id)=1311` 看似矛盾——插入正好发生在两次查询之间）。不是异常。 |
| **1312** | **1** | **8 个剂型页** | **目标串 `Browse All Formulas →`** |
| 1313–1333 | 22 | `/zh/products/*` + `/zh/formulas/` | 底部询盘/联系区块（`How soon will I get a reply?`、`Send Us an Inquiry`、`Phone / WhatsApp`、`Address`、`Building B3, No. 22 Zhongshan Road…`、`Monday–Friday, 9:00–18:00 (GMT+8)` 等）以及 `Contact Us – sinofresh` |

这 43 行全部是**之前从未被 `/zh/` 渲染过的页面上的串**，属正常收获（纯追加、零风险）。

### 7.4 ⛔ 一处如实修正：`translated` 是**空串**，不是 SQL NULL

用户验收项写的是「`translated IS NULL`」。实测：**全表 1333 行 `translated IS NULL` 全为假**，包括**备份里的原始 1290 行** —— 即这是 TP 的固有写入形态，不是本次偏差。

源码印证：`class-query.php::insert_strings()` 的语句是
`INSERT INTO <dict>( original, translated, status, block_type, original_id ) VALUES …`，渲染期收集的串传进来时 `translated` 就是 `''`。
⇒ 判定「未翻译」用 **`translated = '' AND status = 0`**（两表在这一点上语义一致）。目标串与既有 1290 行**完全同形**，无异常。

## 8. 验证

| 组 | 方法 | 结果 |
|---|---|---|
| **界面能命中** | 调 **TP 自己的 API** `TRP_Query::get_string_rows( array(), array('Browse All Formulas →'), 'zh_CN' )`（`class-query.php:483`，即界面那条 SQL） | 返回 **1 行**：`id=1312 original='Browse All Formulas →' translated='' status=0 block_type=0 original_id=1312` ⇒ **会出现在翻译界面、可被翻译** |
| **页面掩码回归** | `tools/b2c_s3_tp_capture.py` 抓 19 页（`/zh/`、`/zh/blog/`、`/zh/products/`、8 个剂型页、`/zh/formulas/`+2 详情页、`/zh/contact/`、`/zh/about/`、`/zh/quality/`、`/formulas/`、`/blog/`）——执行前 vs 执行后 | **19/19 SAME**（页面输出逐字节不变：串已注册但译文为空 ⇒ 回落英文原文，结构不动） |
| **A/A 自检** | 两次**不同 tag 的真回源**抓取同一组 19 页 | **19/19 SAME**（`cache_buster` 各 3 次命中，证明绕 CF 生效、掩码有效） |
| **幂等性** | 执行后再渲染 19 次（post 快照）后复读表 | 仍 **1333 / 1333** —— 已注册的串**不会重复插入**，重复跑安全 |
| **重复行** | `GROUP BY original HAVING c>1` | 仍 **7 组 / 7 多余行**，未因本次执行增加 |
| **error.log** | `/var/log/php-fpm/error.log` | 18 → **20 行**，新增 2 行均为 `NOTICE: [pool www] child … exited/started`（php-fpm 进程回收），**零 PHP 错误** |
| **前端** | `curl` | `/formulas/` **200 / 131108 B**、`/zh/formulas/` **200 / 139432 B**（与执行前一致） |

## 9. 工具与产物

- `tools/b2c_s3_tp_capture.py`（带 `?sfcap=` 绕 CF 的批量快照；query 只进 URL 不进文件名，保证前后两次快照按名对齐）
- `tools/b2c_s3_tp_lookup_probe.php`（只读：调 TP 自身 `get_string_rows()` 验证界面命中 + 打印主题串邻行 + TP 相关 settings）
- `tools/b2c_s3_tp_scope_probe.php`（只读：三表通查 + 全页文本节点对账）
- `tools/sf_masked_cmp.py` **新增掩码** `sfcap=…` → `sfcap=MASK`（对不含该参数的旧基线零影响，hash 不变）

## 10. 回滚

备份：**`/root/tp-backup-20260920-115727.sql`**（425104 B，10 张 `wp_trp_*` 表，含 `DROP TABLE IF EXISTS`，已实测可导入）。
轻量回滚（本操作纯追加、id 单调）：

```sql
DELETE FROM wp_trp_dictionary_en_us_zh_cn WHERE id >= 1291;   -- 本轮新增 43 行
DELETE FROM wp_trp_original_strings        WHERE id >= 1291;
```

红线：执行后 `templates/` 与 `functions.php` **未改动**，仓库无新 commit 涉及主题 ⇒ 回滚 TP 表后站点回到执行前状态。
