# 核验报告：plugins/ai 删除确认 + _backup* 目录审计

- 日期：2026-09-20 08:15–08:25（GMT+8）
- 性质：**只读取证，未执行任何删除**
- 站点：http://sinofresh.local（LocalWP / nginx 1.26.1 / PHP 8.2.29 / MySQL 8.4.0）
- 证据包：`_backup/img-cleanup-20260920-062700/verify-2.5/`

---

## 结论摘要

| 项 | 结论 |
|---|---|
| 核验 1：`plugins/ai/` 删除 | ✅ **通过**（6/6 项；含 1 处仪器修正） |
| 核验 2：`_backup_x/` | **空目录，0 文件 0 字节**，2026-09-18 13:46:07 创建；非 `_backup/` 的副本，判定为**误建残留** |
| 核验 2：`_backup/` | 90 个任务级快照 + `.DS_Store`，**22.86 MB / 344 文件**；全部是「改动前」副本，**无一与当前文件字节相同** |
| 是否需补删 | 建议 2 项（`wpai_version` option、`_backup_x/` 空目录）；**另有 1 项必须明确不删**（见 §1.6） |

---

## 核验 1：`plugins/ai/` 删除确认

### 1.1 Local 侧已删 ✅

```
~/Local Sites/sinofresh/app/public/wp-content/plugins/
├── gravityforms/            translatepress-business/
├── translatepress-multilingual/   wp-consent-api/
├── wp-mail-logging/         wp-statistics/
└── index.php
```

`plugins/ai/` → `No such file or directory`。`wp-content/upgrade/` 空。
各插件实际体积：gravityforms 17.55 MB / translatepress-business 10.00 MB /
translatepress-multilingual 29.90 MB / wp-statistics 19.97 MB / wp-mail-logging 1.35 MB /
wp-consent-api 0.11 MB。

### 1.2 源码侧无 `plugins/` ✅

- `find . -type d -name "plugins"`（项目根，全深度，排除 node_modules）→ **0 命中**
- `find . -maxdepth 4 -type d -name "ai"` → **0 命中**
- 主题源码中 `plugins/ai` 字符串引用 → **0 命中**
- `sinofresh-theme/` 顶层实际内容：

```
assets/  docs/  inc/  parts/  screenshots/  templates/  tools/
_backup/  _backup_x/  .DS_Store
functions.php  style.css  theme.json
```

即：**只有主题文件 + 本地工作资产**（`_backup`/`_backup_x`/`docs`/`screenshots`/`tools`），与用户截图一致。

### 1.3 active_plugins 6 项、无 ai ✅

```
a:6:{ i:0; gravityforms/gravityforms.php
      i:1; translatepress-business/index.php
      i:2; translatepress-multilingual/index.php
      i:3; wp-consent-api/wp-consent-api.php
      i:4; wp-mail-logging/wp-mail-logging.php
      i:5; wp-statistics/wp-statistics.php }
```

反序列化计数 = 6（**未用 grep 计数**）。`recently_activated` = `a:0:{}`。
运行期实际加载的前端资源：gravityforms ×15、translatepress-multilingual ×4、
wp-statistics ×1、wp-consent-api ×1 —— 无 `plugins/ai` 资源。

当前版本：gravityforms 3.1.0.3 / translatepress-business 1.7.6 /
translatepress-multilingual 3.3.6 / wp-consent-api 2.1.0 / wp-mail-logging 1.16.0 /
wp-statistics 14.16.14。

### 1.4 19 页全 200、无 PHP 报错 ✅

19 页（home/about/products/9 剂型页/quality/faq/services/cooperation/contact/blog/factory-tour/feedback）
**200 = 19/19**，非 200 = 0。

- 19 页 HTML 中 PHP 报错特征串（Fatal/Parse/Warning/Notice/Deprecated/critical error）→ **合计命中 0**
- `wp-content/debug.log`（mtime 06:56）→ 仅 2 条 **06:55–06:56 我自己的 CLI 工具**报错
  （`tools/t23_diag.php:44/56` 调用了未定义的 `wp_delete_option()`，工具侧 bug，与站点无关）；
  **07:19 起全部批次 0 新条目**
- `logs/nginx/error.log`（mtime 06:56）→ 同样无新增
- 运行时请求：132 个 URL，**非 2xx / failed = 0**；与 2.4.1 期请求集差异仅 7 行（全部为
  `blob:` / `chrome-extension:` 的浏览器内部 UUID 噪声）

### 1.5 掩码 sha256 vs 2.4.5 基线 ✅（首轮不一致，已定位为仪器问题）

**首轮对比失败**：以原 `t22_render_cmp.py` 掩码规则比对，19/19 页 sha256 **全部不一致**，
`about` 等 5 页 raw 字节数还各 **+23 B**。逐字节定位后确认是**两类新变量**，与原掩码集合未覆盖有关：

| 现象 | 根因 | 证据 |
|---|---|---|
| 19 页 sha256 全变 | wp-statistics 的 `nonce` 值 10 位十六进制令牌翻窗 | `nonce=bf1d8cca1c`（2.4.2–2.4.5 四批恒为同一值）→ `nonce=61bd157f96` |
| 5 页 raw +23 B（伪装成"内容变多"） | **读数口径陷阱**：`t22_render_cmp.py` 以文本模式读文件，通用换行把 `\r\n`→`\n`，每对丢 1 字节；这 5 页恰好各有 **23 个 CR** | `wc -c` 两侧均 **124,090 B，delta = 0**；`tr -cd '\r'` 两侧均 23 |
| 叠加 mask 后 14 页仍差 | GF 的 `config_nonce`（另一个 10 位十六进制 WP nonce，同一时间窗） | `config_nonce":"aa39811603"` → `"3656070d43"` |

**nonce 翻窗时刻已被数学证实**：WP `wp_create_nonce` 对未登录访客的 tick =
`ceil(time()/43200)`（12 h 窗，边界落在 UTC 00:00 / 12:00）。

| 批次 | 本地时间 | UTC | unix | tick |
|---|---|---|---|---|
| 2.4.5 基线 | 2026-09-20 07:56 | 09-19 23:56 | 1789862160 | **41432** |
| 本次核验 | 2026-09-20 08:15 | 09-20 00:15 | 1789863300 | **41433** |

边界 = **UTC 2026-09-20 00:00 = CST 08:00** —— 正好落在两次抓取之间。
2.4.2→2.4.5 之所以四批 sha256 恒同，是因为它们全部落在同一 tick（07:19–07:56）。

**修正后的判定**：把 `nonce=<10hex>` 与 `config_nonce":"<10hex>"` 纳入掩码集合后——

```
结论：19/19 页逐字节全同；异常：无
```

即 **2.4.5 之后站点输出零真实变化**。完整逐页 sha256 见
`verify-2.5/maskcmp-vs-2.4.5.json`。

### 1.6 是否需要补删任何位置

全位置扫描结果：

| 位置 | 命中 | 判定 |
|---|---|---|
| `wp_options.option_name LIKE 'ai\_%'` | 空 | ✅ 无 |
| `wp_options` 值含 `plugins/ai` / `ai/ai.php`（BINARY） | `_site_transient_update_plugins` | 🟡 见下 |
| `wp_usermeta` 含 `plugins/ai` | 空 | ✅ 无 |
| `wp_options.option_name LIKE 'wpai%'` | **`wpai_version` = `1.3.0`** | 🟡 **真残留，建议清** |
| `wp-content/mu-plugins/` | 空目录 | ✅ 无 |
| `wp-content/languages/plugins/` 中 ai 语言包 | 空 | ✅ 无 |
| `wp-content/upgrade/` | 空 | ✅ 无 |
| 文件系统目录名 `ai` | 空 | ✅ 无 |
| `wp-config.php` 常量 | 空 | ✅ 无 |
| `translatepress-multilingual/partials/ai-api-key-settings-page.php` | 命中 | ⛔ **不得删** |

**① `wpai_version`（建议清，低风险）**
`option_id=963, autoload=auto, value='1.3.0'`。已删插件的更新缓存显示其身份为
`slug=ai / plugin=ai/ai.php / version=**1.3.0** / url=https://wordpress.org/plugins/ai/` ——
**版本号逐字符吻合**，命名前缀 `wpai_` 亦对应 slug `ai`；且全站（6 个插件 + 主题源码）
**无任何代码引用 `wpai_version`**。判定：已删插件遗留 option，5 字节，可清。
（同族无其他残留：`wpai%` 仅此 1 条，`ai_%`/`ai-%` 全空。）

**② `_site_transient_update_plugins`（无需处理，自愈）**
4,340 B 缓存中仍列 `ai/ai.php`（`no_update` + `checked` 数组）。其
`_site_transient_timeout_update_plugins` **不存在** → 按 WP `get_site_transient` 逻辑已视为过期，
下次进后台即重算覆盖。属插件更新缓存的正常滞后，**不需要动**。

**③ `translatepress-multilingual/partials/ai-api-key-settings-page.php`（⛔ 明确不删）**
文件名含 "ai"，但属 **TranslatePress 自带的 AI 翻译配置页**，与已删的 `ai` 插件无关。
这是「按名搜 ai 就删」最容易误伤的坑。

**④ 范围外（沿用既有判定，仅备案）**
`_site_transient_wp_font_collection_url_…google-fonts-with-preview.json` = 3,104 KB，
WP 核心 Google Fonts 缓存，与本次无关。

---

## 核验 2：`_backup*` 目录审计

### 2.1 清单

`sinofresh-theme/` 下 `_backup*` 共 **2 个**（另有 1 个同名目录在项目根，见 §2.5）：

```bash
find . -maxdepth 2 -name "_backup*" -not -path "./_backup/*"
./_backup                        # 项目根（对照）
./sinofresh-theme/_backup
./sinofresh-theme/_backup_x
```

### 2.2 `sinofresh-theme/_backup_x/`

| 项 | 值 |
|---|---|
| 体积 | **0 B** |
| 文件数 | **0** |
| 子目录数 | 0 |
| 创建（birth） | **2026-09-18 13:46:07** |
| 最后修改 | 2026-09-18 13:46:07 |
| 内容摘要 | **空目录**（`find` 递归 0 条） |

### 2.3 `sinofresh-theme/_backup/`

| 项 | 值 |
|---|---|
| 体积 | **22.86 MB**（23,975,112 B） |
| 文件数 | 344（+ 1 个顶层 `.DS_Store`） |
| 子目录数 | 96 |
| 顶层条目 | **91** = 90 个任务快照目录 + `.DS_Store` |
| 创建（birth） | 2026-09-16 14:32:02 |
| 最后修改 | 2026-09-20 05:45:39 |

命名规范：`<任务名>-<YYYYMMDD-HHMMSS>` 或 `<任务名>-<HHMMSS>`。按日期分布：

| 日期 | 条目 | 文件 | 体积 |
|---|---|---|---|
| 2026-09-16 | 12 | 54 | 2.70 MB |
| 2026-09-17 | 34 | 132 | 10.67 MB |
| 2026-09-18 | 22 | 94 | 5.06 MB |
| 2026-09-19 | 22 | 63 | 4.20 MB |
| 2026-09-20 | 1 | 1 | 0.23 MB |
| **合计** | **91** | **344** | **22.86 MB** |

内容摘要（典型形态，全部为「改动前」的文件副本）：

| 快照 | 文件 | 体积 | 内容 |
|---|---|---|---|
| `round9-imagelink-20260916-143202` | 11 | 513 KB | 模板 HTML（front-page/page-*）批量副本 |
| `db-template-overrides-0848` | 12 | 2.3 MB | DB 模板覆盖前导出的 `db-66…db-77.html` |
| `cert-gate-20260918-153931` | 4 | 311 KB | 含 `cert-originals/*.webp` 4 张原始证书图 |
| `cert-p2-db-20260918-173152` | 1 | 1 KB | `sf_certifications.sql` |
| `hotlink-20260919-070318` | 7 | 11 KB | **非主题文件**：`nginx/includes/*.conf.hbs` |
| `gf-form4-20260919-195043` | 2 | 13 KB | GF 表单 JSON（before/after） |
| `version-bump-20260919-214016` | 1 | 103 KB | `functions.php` |
| `version-align-20260920-051220` | 1 | 231 KB | `style.css`（最新一个） |

### 2.4 `_backup_x/` 与 `_backup/` 的关系 —— **非副本，独立**

- `_backup_x/` **完全为空**，不存在「`_backup` 的复制/子集」这种关系。
- 关键时间巧合：`_backup_x` 的 birth = **2026-09-18 13:46:07**，
  与项目根 `_backup/contact-split-20260918-134607/` 的 birth **精确同秒**，
  也正是 `sinofresh-theme/` 目录 mtime（该目录最后一次增删条目）的时刻。
- 全项目源码/脚本/文档检索 `_backup_x`：仅 5 处，**全部是文档对它的描述**（审计报告 2 处 +
  `MEMORY.md`/`RULES-sinofresh.md`/`MANIFEST-2.4.2.md` 各 1 处），**无任何脚本创建它**；
  shell 历史（zsh/bash）中 0 命中。

判定：**2026-09-18 13:46 执行 contact-split 备份那一步时误建的空目录**
（同秒产生真实快照在 `_backup/`，此处多出一个空兄弟目录）。零内容、零引用、零风险。

### 2.5 与当前项目状态的关系 —— **旧快照，无一等于当前**

- 90 个快照全部是**改动前**副本（「备份→改→核对」流程的中间产物）。
- 逐一比对 MD5：`_backup` 中 **不存在**与当前 `style.css` 或 `functions.php` 字节相同的文件。
- 最容易误判的两个「尺寸相同」项，内容实为改动前版本：

| 文件 | 备份 | 当前 | 差异 |
|---|---|---|---|
| `style.css` | `_backup/version-align-20260920-051220/style.css`（81ed9bf3…） | 本尊（89541c5c…） | `Version: 2.10.29` → **2.10.38** |
| `functions.php` | `_backup/version-bump-20260919-214016/functions.php`（7fb56b66…） | 本尊（46382246…） | 4 处 enqueue 版本号：style 2.10.37→2.10.38 / hero-slider 1.1.0→1.1.1 / configurator 2.8→2.9 / product-slider 1.0.0→1.0.1 |

> 注：**两文件尺寸完全相同**（237,005 B / 105,847 B）而内容不同——版本号是等长字符串替换。
> 因此**不能用 `wc -c` 判断备份是否过时，必须比 MD5**。

- 部署安全：`diff -rq` 显示 `_backup`、`_backup_x` 均为 `Only in` 源码侧，
  **Local 主题目录（部署位）里根本没有它们** —— 现状下不会误上线。
- 但项目**没有** `.gitignore` / `.distignore` / 部署脚本排除清单，
  保护完全依赖「手工只 cp 需要的文件」。审计报告已列为「部署卫生」项
  （整个主题目录若整体上传将多出 ~73 MB 且**会公开历史源码**）。
- 副作用：它污染 `grep -r` 结果（同名旧文件、`/ -->` 类断言会命中历史版本），
  这也是冗余审计报告里被单独指出的原因。

### 2.6 建议

| 对象 | 建议 | 理由 |
|---|---|---|
| `_backup_x/` | **可删（0 字节空目录）** | 误建残留；删前唯一影响是让 `diff -rq` 的 `Only in` 从 48 行降 1 行 |
| `_backup/` | **不建议删除；建议改为「归档出主题目录」** | ① 它是本项目唯一的改前回滚网，`_backup/<任务>-<ts>/` 是既有约定，后续 CWV／删守卫／素材替换还要用；② 22.86 MB 成本极低；③ 真问题不是"占空间"而是"躺在部署树里"——移出到项目根（与 `_db_backup/`、根 `_backup/` 同级）即可同时消除上线风险 + grep 污染 + 审计假阳性，且保留回滚能力 |
| 若坚持原地保留 | 至少**建立显式排除清单**（`.distignore` 或部署脚本 `--exclude`），把 `_backup/ _backup_x/ screenshots/ tools/ docs/ .DS_Store` 写死 | 现在没有任何机制兜底，靠人记 |

**两个选项都请先确认再动——本轮不执行任何删除。**

---

## 附录 A：对照参照（项目根 `_backup/`，非本次审计对象）

| 项 | 值 |
|---|---|
| 顶层条目 | 57 |
| 文件数 / 体积 | 456 / **171.67 MB** |
| 内容 | 早期任务快照（`round6-` / `round8-` / `round9-` / `about-*` / `contact-split-*` / `cert-modal-*` …）+ **本次冗余清理的备份根 `img-cleanup-20260920-062700/`** |

即项目存在**两个备份根**，命名规范相同但归属不同任务批次：

- `sinofresh-theme/_backup/` → 09-16 14:32 起，主题源码改动快照（91 项）
- `<项目根>/_backup/` → 更早，且后期演变为审计/清理备份根（57 项）

`_db_backup/local-20260918-104650.sql`（3.16 MB，09-18 10:46）为全库 dump。

## 附录 B：本轮核验方法

| 手法 | 用途 |
|---|---|
| 反序列化计数（PHP `unserialize`） | `active_plugins` 计数——**不用 grep 数序列化数据** |
| DB 侧 `LOCATE(..., COLLATE utf8mb4_bin)` | 精确定位 `plugins/ai` / `ai/ai.php`，规避 LIKE 排序规则折叠 |
| `nonce=<10hex>` + `config_nonce":"<10hex>"` 扩展掩码 | 归一 WP 12 h 时间窗令牌 |
| `wc -c` + `tr -cd '\r'` 双口径 | 识别文本模式读文件的 CRLF 折损假差异 |
| MD5 而非体积 | 判定备份是否等于当前（等长版本号替换的坑） |
| birth time（`st_birthtime`）关联 | 追溯空目录的产生时刻 |
| Playwright 运行时请求采集 | 证明无 404 / 无 ai 资源请求 |
| 19 页掩码 sha256 逐页比 | 零变化回归（**截图只作目视，不作字节级仪器**） |

## 附录 C：证据文件

```
_backup/img-cleanup-20260920-062700/verify-2.5/
├── maskcmp-vs-2.4.5.json          19 页逐页 基线/当前 sha256 + 掩码命中域
├── runtime_urls.txt               运行期 132 个请求 URL
├── runtime_bad.txt                非 2xx/failed（0 字节 = 空 = 通过）
├── diff-rq-source-vs-local.txt    diff -rq 全输出（Files differ = 0）
└── shots/                         8 张（home / soft-chews / quality，桌面 1440 + 移动 375）
```
