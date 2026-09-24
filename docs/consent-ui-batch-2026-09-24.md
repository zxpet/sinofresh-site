# Cookie 批第二段（UI 两件）· pull 待确认 ＋ TP Business 移除 ＋ GF 迁移剩余方案

> 候选 **`9cd750d`**（已装预检副本，**未 pull**）· dev live `38204d5` · 令牌 `2.10.79`→候选 `2.10.80`
> 前一篇：`docs/consent-batch-2026-09-24.md`（技术两件，已随 `38204d5` 上线）

## 1. UI 两件（用户裁决已给，实施完毕，停在 pull 前）

| 裁决 | 落地 |
|---|---|
| 去掉 Manage Preferences | `parts/footer.html` 删按钮；`style.css` 删两条死规则；JS 删绑定。理由（上批已证）：它的 handler 就是 `decide(false)`，承诺管理、实为一键拒绝 |
| 加撤回入口 | 页脚 legal 行加 `Cookie Preferences` 链接：清记录 → 重开横幅。**配套修复**：横幅按钮监听从「仅首访绑定」移到「横幅存在即绑定」——否则重开的横幅对老访客是死按钮 |

- 脚本 `1.1.0 → 1.2.0`；主题令牌 `2.10.79 → 2.10.80`（CSS 有字节变化；6 个门工具的钉值同步）。
- 证据：单元门 **37/0**（新增撤回 5 断言：重开、清记录、按钮仍活、未决策时无害、无链接页不崩）；E2E **25/0**（预检副本，含 Consent API cookie 复写为 allow）；候选/live 归一化后**零残差**（把本批两处意图改动按元素点名归一化掉之后）。
- 量具自纠三处：stub 缺 `preventDefault`；块配平计数未剔除自闭合块（以 git 基线对照为准）；「归一化后逐字节一致」的断言写错了对象——本批的目的是改 markup，改为「意图差异之外零残差」。

**两个后果**（同上一批）：已记录的访客再被问一次；站点设 `wp_consent_statistics/_marketing` cookie。

## 2. 同意批第一段 pull 复验（`38204d5`）

`tools/b3g_consent_postpull.py`（新门，只问 pull 后该成立的事）：**12/0** —— live 服务 `1.1.0` 脚本含 `wp_set_consent`/两条守卫/`VERSION=2`；`/zh/about/` 仍 301。ZH 门 `b3e_zh_postpull.py` 复跑 **77/0**。

⛔ 量具陷阱（第三次同类）：postpull 初版从**本机** curl `127.0.0.1`，11 条假红。判据：断言内容/状态码走 `dev.zxpet.com`；断言**来源头/缓存**才需要登服务器绕 CF。

## 3. TP Business 破解插件：已移除（2026-09-24）

前置只读核查：免费版 `translatepress-multilingual 3.3.6` 对 addon 的引用仅 onboarding/插件列表展示；addon 的 **7 个子 add-on 全部 `false`**（SEO pack 未激活，`/sitemap_index.xml` 404 与之互证；无机器翻译配置）⇒ **零功能在用**。

执行：`wp plugin deactivate` → 复验（4 页 200、hreflang 2 条、ZH 301）→ `wp plugin delete` → **清 DB 假 key**（`trp_license_key` option 已删）→ 复验：
- 页面 200 ×4、切换器 markup 0（正常，floater 关）、hreflang 2 条、ZH 门 **77/0**；
- `gpltimes` 全站仅剩 `gravityforms/gravityforms.php`（GF 迁移完成后消零）；
- PHP-FPM 今日非 NOTICE 仅 5 条 `pm.max_children`（02:0x，普查爬取旧账）；`wp-login.php` 401（Basic Auth 壳正常）。

## 4. GF → Fluent Forms：数据已迁，剩余三块需裁决

已完成：FF 6.2.14（WP.org 校验和通过）＋ 5 表单迁移（修正 stock migrator 的两个缺陷：`phone` 字段整个丢失（Pro 元素）、`time` 误映射为 date+time 选择器）＋ 保真度门 **222/0**（逐字段对照 GF 源，含 planted-rotation 控制）。证据 `docs/form-migration-2026-09-24/`。

**剩余三块（不能由数据迁移覆盖，需你裁决实施顺序）：**

1. **14 个模板**的 GF Gutenberg 块 → `<!-- wp:shortcode -->[fluentform id="N"]<!-- /wp:shortcode -->`（映射 2→8, 3→9, 4→10, 5→11, 6→12）。纯机械，但改动面大。
2. **functions.php 三块 GF API 业务逻辑**：
   - 表单 5 **COA 证书门下载**（`gform_confirmation_5` + `gform_after_submission_5` + entry meta，约 280 行）——最大一块，需在 FF 钩子上重写并重测；
   - 表单 6 **Feedback 服务端提交**（GFAPI 调用）→ FF API；
   - 表单 2 的 **WhatsApp 提示**（`gform_submit_button_2` 过滤器）→ CSS/JS 注入替代。
3. **CSS**：`.gform_wrapper` 整块样式 → FF 的 `.ff-el-*` 结构，外观会变，需视觉验收。

顺序建议：1 → 3 → 验证渲染与提交 → 2（COA 门最后，单独测）→ 全绿后停用+删除 GF。GF 删除前模板不能先换（反之亦然），中间态避免不了；每步可独立回滚。
