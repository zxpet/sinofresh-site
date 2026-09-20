# About 页上线前待办清单

**产出**：任务 7（About 页收尾）· 2026-09-17 · 当前版本 v2.10.18 / about.js 1.3.0
**范围**：About 页遗留项 + 与本轮相关的全站口径残留

---

## 一、阻塞上线（必须处理）

| # | 项 | 位置 | 处理方式 |
|---|---|---|---|
| 1 | **6 张占位工厂图替换为真实实拍** | `templates/page-about.html` → Inside Our Factory Gallery 第 7–12 张；文件 `/wp-content/uploads/2026/09/fac-placeholder.webp`（1100×733，6 张同一张） | 后台图库替换这 6 张，或直接覆盖同名文件。alt 已写 "Placeholder photo — replace with a real SINO FRESH factory image"，可用 `grep -c fac-placeholder` 校验是否替换干净 |
| 2 | **视频区播放按钮接真实 YouTube 视频** | `templates/page-about.html` → `.sf-video__play` 的 `data-video-id="REPLACE_ME"` | 填入真实视频 ID 即生效（`about.js initVideo()` 已就绪，无需改代码）；或整块替换。当前点击无功能——用户已确认任务 3 跳过 |

> 上线前自检：`grep -c "REPLACE_ME\|fac-placeholder" sinofresh-theme/templates/page-about.html` 应为 **0**。

---

## 二、全站口径残留（非 About 页，第二批处理）

### 2.1 认证清单缺 2 项（4 认证 → 6 认证）—— ✅ **已完成（2026-09-18）**

口径基准（About 页已统一）：完整 6 认证 = **FDA, cGMP, ISO 9001, FSSC 22000, HACCP, and BRC**
当前残留 = `FDA · cGMP · ISO 9001 · FSSC 22000`（徽章条）或 `FDA, cGMP, ISO 9001, FSSC 22000`（正文/规格行）

> **✅ 完成记录**：2026-09-18 全站口径统一已收口。下表为 15:50 的原始审计底稿，**与实际执行清单有出入**，执行以 `docs/cert-wording-rescan-2026-09-18.md`（2.1 复核）为准：
> - B 类「8 剂型页规格行」**无需改**——剂型页重构后规格面板已不再列认证，8 处自然消失
> - A10 services 徽章条已随 hero 重构消失，残留迁至该页合规清单（原 `:168–169`）
> - §2.2 洁净车间实际 **3 处**（`page-factory-tour.html` `:12 / :15 / :78`），非 1 处
> - 另有 4 处新残留（本表未列）：`functions.php` 默认徽章数据源、`functions.php` JSON-LD description、DB `wp_options.sf_certifications`（名为 `BRCGS`、顺序不符）、services 清单
> - §2.3「已达标（勿重复改）」行号已失效：front-page 认证文本实际在 `:20 / :1248 / :1324 / :1490`
> - **实际执行 17 处 / 12 文件 + 2 处数据源**；核验：源码四认证串 0、渲染 14 URL 0、DB 6 项 active（顺序 `… HACCP · BRC`）；备份 `_backup/cert-p2-20260918-172938/`（模板+functions.php）、`_backup/cert-p2-db-*/`（DB 选项）

**A 类 · 徽章条（11 处，`·` 分隔）**

| # | 文件 | 行 |
|---|---|---|
| 1 | templates/page-soft-chews.html | 20 |
| 2 | templates/page-tablets.html | 20 |
| 3 | templates/page-powders.html | 20 |
| 4 | templates/page-pastes.html | 20 |
| 5 | templates/page-liquids.html | 20 |
| 6 | templates/page-drops.html | 20 |
| 7 | templates/page-fish-oil.html | 20 |
| 8 | templates/page-dental-chews.html | 20 |
| 9 | templates/page-quality.html | 15 |
| 10 | templates/page-services.html | 15 |
| 11 | **templates/page-factory-tour.html** | **15** ⚠️ 见 2.2 |

**B 类 · 规格行 "Certifications"（8 处，8 个剂型页）**

| # | 文件 | 行 |
|---|---|---|
| 12–19 | page-{soft-chews,tablets,powders,pastes,liquids,drops,fish-oil,dental-chews}.html | 66 |

**C 类 · 正文/FAQ 句子（3 处）**

| # | 文件 | 行 | 当前文本 |
|---|---|---|---|
| 20 | templates/page-quality.html | 12 | FDA registered, cGMP compliant, ISO 9001 and FSSC 22000 certified. |
| 21 | templates/page-services.html | 12 | …8 dosage forms, flexible MOQ, FDA, cGMP, ISO 9001, FSSC 22000. |
| 22 | templates/page-soft-chews.html | 546 | FDA registration, cGMP, ISO 9001, FSSC 22000. |

**已达标（勿重复改）**：`parts/footer.html:9`、`front-page.html:20 / 1248 / 1324 / 1490`（原记 `1192 / 1268 / 1434` 行号已失效，那三行实为客户名、MAP 区块与博客标题）、`page-about.html:181`、`page-faq.html:70` 均为完整 6 认证。上述四处已于 2026-09-18 复核确认未误改。

### 2.2 洁净车间口径不一致 —— ✅ **已完成（2026-09-18，实际 3 处）**

`templates/page-factory-tour.html:15` 徽章条写作 **`10,000-Class Cleanroom`**；公司口径是 **10 万级洁净车间 = ISO 8 cleanroom**（About 页任务 1 已统一为 "ISO 8 cleanrooms"）。疑为 10,000 / 100,000 数字笔误，需确认后随 A 类一并修正。

> **✅ 完成记录**：确认系 10,000 / 100,000 数字笔误，口径统一为小写 **`ISO 8 cleanroom`**（与 front-page / about / config-pdf 现有写法一致）。实际改 **3 处**（非 1 处）：`page-factory-tour.html` `:12` 导语、`:15` 徽章条、`:78` 清单行。全站 `grep "10,000-Class\|10,000-class"` = 0（源码层与渲染层双验）。

### 2.3 旧文档状态

- `docs/cert-4list-residue-20places.md`（14:25 归档的 20 处）**已被本节取代**：该清单混入了 `_backup/` 归档文件命中，且 A 类徽章条部分已在 07:08–13:06 的其他批次中被修掉。以上 22 处为 15:50 精确审计结果（已排除 `_backup/`）。

### 2.4 低优先（可保持现状）

`templates/front-page.html:14` hero 轮播 eyebrow：`OEM / ODM · FDA registered · cGMP` —— 属于短标签而非完整认证清单，是否补全 6 项由市场口径决定。

---

## 三、素材与部署

1. **直链图片未注册媒体库**：About 页 12 张工厂图（6 真实 `fac-*.webp` + 6 占位 `fac-placeholder.webp`）与 5 张团队头像 `team-*.webp`，全部以 URL 直链引用，**未在媒体库登记**（与全站 61 张 AI 图同一约定）。上线部署时需把 `uploads/2026/09/` 下这些文件一并迁移，否则图片 404。
2. 图片体积：`fac-*.webp` 52–82KB、`fac-placeholder.webp` 121KB，均在可接受范围，无需压缩即可上线。
3. 占位图来源：复制自未引用的备用素材 `hero-facility.webp`（1100×733）。若后续不再需要，`hero-*.webp` 可与之一并清理。

---

## 四、已确认不做（记录以防反复讨论）

| 项 | 结论 |
|---|---|
| Gallery 分页 | 核心 Gallery 区块**无分页属性**，需插件；已确认不做 |
| 6 张占位图重复 | 用户已确认接受，上线前替换 |
| About 视频区（任务 3） | 用户已确认跳过，保持现状（0 iframe、海报 + 无功能按钮） |
| About 页 4 认证残留（任务 1 存档的那批） | 已由本轮 2.1 精确清单取代 |

---

## 五、任务 7 验收快照（可复查）

| 项 | 结果 |
|---|---|
| about.js 加载范围 | 仅 `/about/`（首页/products/quality/services/contact/blog 实测 0 次） |
| about.js 体积 | 10.6KB 原始 / **3.84KB gzip**（在 3–4KB 目标区间内；纯原生 JS，零依赖） |
| about.js 功能 | `initJourney()` 入场淡入 + `initVideo()` 点击加载 + `initFactoryLightbox()` 灯箱；hover 放大为纯 CSS |
| 双端核验 | 24/24 项 PASS（1440 + 375，含灯箱、hover、节奏、溢出、0 JS 错误） |
| Schema | `hasCredential` 6 条 = FDA Registered / cGMP Compliant / ISO 9001 Certified / FSSC 22000 Certified / HACCP Certified / BRC Certified；无 ISO 22000 |
| 文案残留 | `ISO 22000` 0 · `five dosage` 0 · `four continents` 0（本轮另修掉首页地图 SVG 标题与统计条 "4 Continents" 两处同义残留） |
| 一致性 | 源码 = Local：page-about.html / style.css / functions.php / front-page.html 全部 IDENTICAL；`/ -->` 0 |
| 截图 | `screenshots/t7_1440_fullpage.png`、`screenshots/t7_375_fullpage.png` |

## 2026-09-17 追加：博客特色图（数据问题）

| 项 | 说明 |
|---|---|
| 问题 | 12 篇文章全部共用同一张特色图（`blog-softchews.webp`，1200×900，附件 ID 53）→ 文章详情页与 Related Articles 三卡同图，博客列表页 12 张卡同图 |
| 待办 | 上线前为每篇文章上传/生成不同的特色图（建议 1200×675 以上、16:9；列表卡按 4:3 裁切显示） |
| 备注 | 模板侧无问题（single.html 重设计已完成 2026-09-17）；纯数据侧替换特色图即可 |

## 2026-09-18 追加：配置器 PDF 功能上线依赖

| 项 | 说明 |
|---|---|
| ⚠️ wp-content/vendor/ 必须随站打包 | Dompdf 3.1（composer 安装在 `wp-content/vendor/`，含 composer.json/composer.lock/composer.phar）。**不在主题目录内**，迁移/上线时若漏掉，REST 端点 `/wp-json/sinofresh/v1/config-pdf` 将返回 503（代码已做缺库兜底） |
| ⚠️ 邮箱副本真实投递 | 本地 Local 用 127.0.0.1 catcher，邮件不真实出站。上线后需配置 SMTP（腾讯企业邮箱 smtp.qq.com:465，账号 jack@zxpet.com 或专用发信账号），实测「Email me a copy」到客户邮箱 + Cc sales@zxpet.com 到达。已验证：本地日志 23 条无 error，Cc 头正确 |
| PDF 字体 | PDF 用 Dompdf 自带 DejaVu Sans（Unicode 全，≥/→/m² 正确）。如需与网站一致的 Inter，需下载 Inter TTF 并用 Dompdf loadFont 注册（可选优化） |
| 配方占位数据 | Standard Formulas 配方库为占位数据，PDF「FORMULA (Standard)」区块内容跟随配方库——真实配方数据替换后 PDF 自动跟随 |

## Inquiry Basket 上线依赖（2026-09-18，阶段 3）
- GF Form 2 notifications 本地为空：上线配置通知时，Admin 通知正文用 {all_fields} 即自动携带字段 12（多剂型汇总）；自动回复需含篮子清单同样用 {all_fields}（本地无通知可改，无代码改动）
- 上线前在真实 SMTP 下验证：basket 提交 → 字段 12 入库 → 通知邮件包含汇总

## Certificate gated download 上线依赖（2026-09-18，Quality 页）

| # | 项 | 说明 |
|---|---|---|
| 1 | **证书文件放 public_html 外层** | 4 张全清证书图必须在**文档根之外**：生产环境上传到 `public_html/../private-certs/`（即与 `public_html` 同级）。本地对应 `~/Local Sites/sinofresh/app/private-certs/`。路径常量 `SF_CERTS_DIR`（`inc/cert-download.php` 顶部，`dirname(ABSPATH) . '/private-certs/'`）是**唯一需要按生产布局核对的一处**。目录内文件：`cert-fda.webp` / `cert-cgmp.webp` / `cert-iso9001.webp` / `cert-iso22000.webp` |
| 2 | 为什么不能用 .htaccess | 技术栈是 nginx（Local 1.26.1 + 生产 AlmaLinux 9 LEMP），**`.htaccess` 完全不被读取**。实测：`uploads-private/` 方案下全清证书直链返回 200，保护为零。移至文档根外是唯一不依赖服务器配置、且重启/迁移不丢的方案 |
| 3 | 页面展示用 teaser | 公有路径仅保留 400×550 低清 teaser（`uploads/2026/09/cert-*-thumb.webp`，正文字段不可读）。全清件只经 `GET /wp-json/sinofresh/v1/cert-download` 一次性 token 下发 |
| 4 | 真实 PDF 源文件待替换 | 当前 4 张证书是 webp 扫描图（页面文案已于 2026-09-18 由 "Download Certificate (PDF)" 改为 **"Request Certificate"**，与留资弹窗一致）。拿到真 PDF 后放入 `private-certs/`，并把 `sinofresh_cert_files()` 里对应条目的 `file`/`mime`/`download` 改掉即可，端点逻辑无需改动 |
| 5 | HACCP / BRC 无文件 | 两行目前是 "Certificate coming soon"，登记表里 `file` 留空 → token 有效但返回 404 + 提示联系邮箱，仅用于记录留资意向 |

### Certificate gated download — GF Form 5 激活状态（2026-09-18，B3）

| # | 项 | 说明 |
|---|---|---|
| 1 | **无需 GF 后台配置** | Form 5 的 confirmation 与客户邮件**全部由代码产出**：`gform_confirmation_5`（functions.php）替换默认确认消息并带 JSON payload；`gform_after_submission_5` 负责发信。GF 后台的 Settings → Confirmations / Notifications **保持为空即可**，不要在后台再加 confirmation，否则会与 filter 叠加 |
| 2 | 销售线索副本 | 客户邮件的 `Cc: sales@zxpet.com`。客户地址不可用时（GF 校验基本不会放过，属兜底）改为**只发 sales**，并附下载链接，避免丢单 |
| 3 | hidden 字段 | `certificate`，字段 ID **10**，前端 `#input_5_10`。`nextFieldId` 已递增到 11，后台再加字段不会撞号 |
| 4 | 邮件附件 | 以友好名附件（`SINO-FRESH-FDA-Registration.webp` 等）从 private-certs 复制到临时目录后附加，发完即删；源文件不受影响 |
| 5 | 出站邮件依赖 | 本地 Local 走 **Mailpit**（日志：WP Mail Management / `wp_wpml_mails`）；生产必须配 SMTP 才能真实投递。**即使邮件失败，下载链接仍在 confirmation 里即时返回**，功能不依赖 SMTP |
| 6 | 上线前清理测试条目 | 本地 Form 5 现有 22 条条目（其中 15 条为 B3 测试，id 19–36，含 `sf_cert_*` 元数据），生产环境不要带入 |
| 7 | 测试提示 | GF ≥2.9.15 内置拒收 `@example.com` / `@domain.com`（`GF_Field_Email::is_email_rejected`）→ 任何测试邮箱都要用像真实域名的地址，否则提交在校验阶段就被拦、钩子不会执行 |
| 8 | 响应耗时 | 邮件为**同步发送**（本地实测整次提交 ~46ms，走 Mailpit）。生产 SMTP 下预计 0.5–2s，落在表单提交响应里；下载按钮在 confirmation 中即时给出，用户下载不被邮件阻塞。若要响应零等待需改队列（`wp_schedule_single_event`，依赖 WP-Cron 触发）——尚未采用 |

## 2026-09-18 追加：Quality 页证书区 2 列网格（✅ 已完成）

| 项 | 说明 |
|---|---|
| 需求 | 证书区原为纵向 6 行列表（1440px 下区块高 1496px，行列表 1247px），过长；改为横向 2 列卡片网格 |
| 实现 | **只改 `style.css`**（新 section 31d 追加文件尾 + 一条 ≤768 断点），模板 / JS 零改动（`quality.js` 灯箱按 `.sf-certrow__media a` DOM 行主序建画廊，类名与顺序须保留） |
| 桌面 ≥769 | `.sf-certdetail` → 2 列 grid（gap 20/24）；`.sf-certrow` 卡片化（`border 1px + radius 6 + card-white + padding 16px 18px`）；缩略图仍 120×167；不做卡级 hover lift |
| 移动 ≤768 | 1 列堆叠 + 卡框，padding 12px + 内 gap 12px；保留 88×123 缩略图在左 |
| 实测 | 1440：区块 **1496 → 892px**（≤950 达标），行列表 1247 → 643px（−48%），卡宽 588 等高 201；900：detail 959 → 615；375：1462 → 1547（**+85px，已确认接受**） |
| 已知增量 | 移动端 +85px 来源：卡框水平内缩把正文列由 195px 压到 ~170px，6 卡合计多换行。**决策：接受，保持现状**。若要回填，把 ≤768 的 media 轨道由 88px 降到 68px 即可（一行改动） |
| 备份 | `_backup/cert-2col-20260918-175020/`（style.css） |
| 测试 | 新 `tools/_cert_2col_test.js` 47 断言 + 回归 triggers 40 / copy_cta 24 / coa_trust 26，合计 137 断言全绿 |

### ⚠️ 上线前待办：样式缓存破坏

| # | 项 | 说明 |
|---|---|---|
| 1 | **`style.css` 版本号需 +1** | 入队版本在 `functions.php:26`：`wp_enqueue_style('sinofresh-style', get_stylesheet_uri(), array(), '2.10.37')` → **当前 2.10.37**，上线前需加到 `2.10.38`（或更高）。否则老访客浏览器命中缓存，拿不到本轮 2 列网格 + 弹窗等样式改动。备注：`style.css` 文件头 `Version:` 字段是 `2.10.29`，仅供 WP 后台识别，**不参与缓存破坏**，可一并同步但非必需 |



## 2026-09-19 追加：sf-single-meta 块校验报错（⏳ 待处理，非阻断）

| 项 | 说明 |
|---|---|
| 现象 | 后台打开文章编辑器时 console 报 `Block validation: Block validation failed for core/group`：`templates/single.html` 中 `sf-single-meta` group（flex 布局 + blockGap 10px）save 生成的 style 为 `margin-top:...`，与模板里 `margin-top:...;gap:10px` 不一致 |
| 影响 | **仅 console 噪音**：前台渲染正常、编辑器可用、保存不受影响。属 WP 7.1 对 flex blockGap 序列化的行为变化 |
| 建议 | 上线前用块编辑器重新选中该 group 并保存一次模板（让 WP 重写序列化），或手动把 `style` 拆进 attributes；改动后回归单篇文章页视觉 |
