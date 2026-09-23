# Batch H7g — Shape 图片选择器 ＋ 页脚手机号处理（2026-09-23）

**状态：实施＋本地结构验证完成；未 pull（用户约束「不 pull、不拆预检、不删守卫」）。**
**Step 6 跳过**＝dev live 仍 `2.10.67`（GO 批态）；本批上线待用户下一次 pull 授权。

## 四项用户裁决（AskUserQuestion，2026-09-23 04:4x）

1. **Shape 范围＝全部详情页常显**——shape 库是全局概念，不依赖 post meta（DB 事实：21 产品中仅 1 个有 `sf_formula_shape`、1 个有 `sf_formula_container`；照 Container 的门控则选择器只出现在 1 页）。纯前端预览，**不写任何 post meta**。
2. **紧凑化＝js 类门控**——值预览行（`__meta`）是无 JS 时唯一的当前值展示（渲染函数注释明写的契约）；config.js 已给根元素加 `sf-fdetail-config--js`，CSS 用它隐藏 meta：**有 JS 紧凑、无 JS 保留**。
3. **删页脚手机号＝只删页脚那一处**座机 tel 链接；schema `telephone`／邮件签名／PDF 页脚／联系页 4 处硬编码不动。
4. **WhatsApp＝只统一机制，号码不动**——悬浮钮 href 从 `{{sf-social:whatsapp}}`（`sf_social_links` option，手填完整 URL）改为 `{{sf-whatsapp-link}}`（`sf_contact_whatsapp` 自动拼 wa.me），与页脚文字链同源，双源漂移消失。

## 改动清单

### A. Shape Library 后台（`inc/formula-admin.php`）
- `sf_default_shapes()`：8 项 bone/round/square/heart/star/paw/cylinder/custom，`attachment_id` 全 0（与 Container Library 同构）。
- `sf_shape_library()`：读 option `sf_shapes`，缺省回退 8 项默认。
- `register_setting('sf_site_settings', 'sf_shapes', …)`：同 `sf_containers` 的 sanitize（有 slug 才存活、空行丢弃）。
- 新子页 `sf_render_shapes_page()`（仿 containers 页，`id="sf-shapes"`）＋ `add_submenu_page` ＋ admin_enqueue hook 数组加 `site-settings_page_sf-shapes`。
- `assets/admin/sf-site-settings.js`（**1.0.0→1.0.1**）：选图/加行/删行 handler **泛化**——attachment 输入按 `[attachment_id]` 后缀匹配（不再写死 `sf_containers[` 前缀），按钮匹配 `.sf-containers__pick, .sf-shapes__pick`／`#sf-containers-add, #sf-shapes-add`，tbody 用 `row.closest('tbody')`。

### B. Shape 组＋空槽渲染＋预览层（`functions.php`）
- `sinofresh_formula_config_groups()`：**shape 组插在 container 之前**，`type single / style image / hint "Choose one"`；选项来自 `sf_shape_library()`；记录的 `sf_formula_shape` 文本与库 label **大小写不敏感匹配**时作为 meta 行（值预览），**不预选** radio（沿用「无勾选即无请求」契约）。
- 空库槽渲染：虚线框内**名称居中**（`sf-fdetail-config__empty-label`），该选项**不再输出** `__text`（名字只写一次）；有图槽保持 img＋下方 label。
- `sinofresh_formula_gallery()`：stage 内追加 `<div class="sf-gallery__preview" data-sf-gallery-preview hidden>`——**只加节点不碰 slide**，slide id／`formula-gallery.js` 零改动。
- 版本令牌：`style.css` **2.10.67→2.10.68**（两处同步：头部 `Version:` ＋ functions.php:31 enqueue）。

### C. config.js（**1.0.0→1.1.0**）
- `selection()` 的 label 读取回退链：`__text` → `__empty-label` → input value（空槽选项的摘要/询盘弹窗仍拿得到正确名字）。
- 预览层三模式：shape/container radio 选中→若该选项**有图**则填充预览层并显示；**空槽＝不切换**（主图区保持产品图库——占位框不冒充产品图）；stage 内**任何点击**（缩略图/Photos/Video 切换）→隐藏预览层回默认。formula-gallery.js 零改动。

### D. CSS（`style.css`）
- 缩略图 **46→60px**，移动端 768 断点内 48px；`--empty` 变 flex 居中容器＋透明背景；`.sf-fdetail-config__empty-label` 11px 次级色。
- `.sf-fdetail-config--js .sf-fdetail-config__meta { display:none }`（紧凑化的 js 门控）。
- `.sf-gallery__preview`：absolute inset 0（stage 本就 `position:relative`）、z-index 2、白底居中、`[hidden]` 时 display none。

### E. 页脚（`parts/footer.html`）
- `sf-footcontact` 行删除 `<a href="{{sf-phone-tel}}">{{sf-phone}}</a>`（剩 email＋WhatsApp＋地址）。
- 悬浮 WhatsApp 钮 href `{{sf-social:whatsapp}}`→`{{sf-whatsapp-link}}`。
- ⚠️ **登记**：`{{sf-phone}}`/`{{sf-phone-tel}}` 令牌现在**全站零使用**（替换器保留未删）——属新造零引用，登记不夹带。页脚第 12 行的社交图标行 WhatsApp **仍读** `sf_social_links`（社交档案链接语义，与联系号分属两源，按裁决 4 只统一悬浮钮）。

## 验证（本地，未上 dev）

- `php -l` functions.php／formula-admin.php ✓；`node --check` config.js／sf-site-settings.js ✓。
- 令牌两处同步 ✓（`Version: 2.10.68` ＋ enqueue）。
- **渲染冒烟桩**（`tools/b2d_h7g_render_harness.php`，WP 函数桩＋真渲染）：**9/9**——shape 组在 container 前／8 选项／15 个空槽带名（8 shape＋7 container）／记录 shape "Bone" 进 meta／shape 组无重复 `__text`／container 组原样／预览层在 stage 内且 hidden／slides 照常渲染。
  ⚠️ 桩的静默退出坑：`inc/config-pdf.php` 的 `if (!defined('ABSPATH')) exit;` 会让无 ABSPATH 的 CLI 脚本**零输出退 0**——桩先 define 即可。
- **未验证（留待上线批）**：浏览器交互（点选切主图/点缩略图回退/悬停仅边框/移动端 48px）、75 页门、E2E。原因：本批约束不 pull，dev live 未装本批代码。

## 联动核查（做了）

- **config-pdf 端点**：`$data['config']` 是通用 label/value 对（sanitize＋mb_substr 限长），无按键白名单 ⇒ 新增 `shape` 组的选中值随询盘提交**不会被拒**。`sinofresh_*` 函数零悬空未复验（本批只增不改删）。

## 仍需用户处理

1. **两张图库都待传图**：Shape Library（8 项）与 Container Library（7 项）现全空（attachment_id=0）——上传前前台显示虚线占位框，主图切换对空槽**不生效**（设计如此）。
2. **post 158 测试值 5 处仍由用户后台自清**（GO 批遗留）。
3. 预检副本 `0b015e1` 已过时（相对 live 多 guard、相对本批少全部改动）——删/重装待裁决。

---

## 上线（2026-09-23 09:5x，批 A＝用户 pull 授权）

- **pull**：`/var/www/dev.zxpet.com/site-repo` `git fetch --prune` → `git pull --ff-only origin main`；`77a81b9 → 5db481d`，四条入站提交 `e8f0172`(H7g) / `65f8d56` / `8a613bd` / `5db481d`(H7h＋档)。主题目录是 symlink ⇒ 即时生效。
- ⚠️ **live 版本＝`2.10.69`，不是订单里写的 `2.10.68`**：H7h 已在其上（`65f8d56`＋`8a613bd`），pull 一次把两批一起带上。属派生数字偏差，方向一致，未停机。
- **H7g 门重跑（全绿）**：主证 75/0、A/A 75/0、矩阵 **7/7**（含「一组都不插」131/173、「令牌不折」75 页、「run count 少一」172/172）、负对照 **16/16**、源码 **15/15**（对 `git archive e8f0172` 检出）、掩码回读 23 页＋46 二进制 0 差异。
- **H7g E2E（`tools/b2d_h7g_e2e.py`，对 live，22/22）**：
  - 四剂型各一页（soft-chews／liquids／tablets／dental）先断言「被服务的是 live 主题」＝`link` 含 `/sinofresh-theme/`**且不含** `-preflight`＋`ver=2.10.69`＋config 1.2.0＋gallery 2.2.0＋h1=1；
  - **Shape 常显**：四页各 8 个选项、`type=radio`、value 互不相同、label＝`Shape`；
  - **Container 随记录**（双向断言）：soft-chews 有 `sf_formula_container`=Round ⇒ 组在、7 项、meta 读回 `Round`、且 Shape 在 Container **之前**（idx 3 < 4）；liquids／tablets／dental 无该 meta ⇒ 组**缺席**（idx −1）。
    ⛔ 首跑 3 处 FAIL 是**断言写错**（把 Container 当成常显），不是产品缺陷 —— 证据＝源码注释「Container waits for the record's own meta before it renders」＋DB 只有 post 158 有该 meta。修法是**重构断言**（拆成双向两半），不是改松。
  - **交互（空图库态）**：点第 1 项只勾它、点第 2 项只勾它（单选）；空槽**不夺主图**（src 不变）且预览层始终 `hidden`；点舞台也保持隐藏。
  - **H7g 后半**：详情页全页 `tel:` 链接 **0**；悬浮 WhatsApp href＝`https://wa.me/8613385397805` 与页脚 WhatsApp **同串**（三处页脚链接全同）；悬浮询盘钮 `/contact/#quote` ＋ `data-sf-inquiry-open` 仍在。
  - 375 视口下 Shape 组仍在 DOM（8 项）；**0 页面错误**。
- **服务侧站点级验收**：`/`、`/formulas/`、`/products/soft-chews/`、`/quality/`、`/contact/`、`/blog/` 全 200 且 `style.css?ver=2.10.69`、每页 h1=1；`/no-such-page-zzz` = 404；**匿名 401**；`x-robots-tag: noindex, nofollow, noarchive` 封锁仍在。
- **未修**：Shape/Container 两库仍空（占位框态即本批 E2E 的状态）；post 158 五处测试值未动。
