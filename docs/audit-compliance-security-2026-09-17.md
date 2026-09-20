# SINO FRESH 官网 合规 + 安全审计报告

日期：2026-09-17 · 范围：sinofresh-theme 全部源码 + Local 运行站（sinofresh.local）渲染输出 + Gravity Forms 数据库配置
性质：只做「合规 + 安全」审计；「冗余 + 优化」类留到上线前另做。

---

## 扫描方法

- 源码：通读 functions.php（1046 行，主题内唯一活体 PHP）；grep 敏感词（password/api_key/secret/token/private 等）
- 运行站：curl 抓取 10 个代表页（/、/about/、/quality/、/contact/、/soft-chews/、/tablets/、/blog/、单篇文章、/privacy-policy/、/cookie-policy/）做 HTML/Schema/a11y/第三方脚本分析
- 数据库：wp_gf_form_meta 提取 4 个表单的字段/通知/确认配置；wp_options 查 reCAPTCHA 与插件清单
- 对比度：关键配色对 WCAG AA 数值计算

---

## 🔴 严重（必须上线前修）

### R1. Form 3/4/5 隐私政策勾选框未设必填
- 位置：DB `wp_gf_form_meta`，form_id=3（字段12）、4（字段14）、5（字段9），`isRequired` 为空；仅 Form 2（字段11）为必填
- 影响：GDPR 合规缺口——4 个表单中 3 个可不勾选同意即提交个人数据；被投诉举证不利
- 修法：GF 表单编辑器中逐个勾选 Required（推荐，别直接改 DB）

### R2. reCAPTCHA v3 未启用，honeypot 也未开
- 位置：`wp_options` 无任何 recaptcha 配置项；4 个表单 meta `honeypotEnabled` 均空
- 影响：机器人可无限提交，垃圾直达 sales@zxpet.com 邮箱 + GF entry 表；伴随自动回复邮件被滥用发信
- 修法：GF Settings → reCAPTCHA（v3）配置 site key/secret；若暂不接 Google，至少给 4 个表单开 honeypot

### R3. REST API 用户枚举暴露管理员账号
- 位置：`http://sinofresh.local/wp-json/wp/v2/users` 返回 200，暴露 `admin` 用户名与 /author/admin/ 链接
- 影响：撞库/爆破的第一手情报（用户名已知的爆破成功率远高于枚举失败）
- 修法：functions.php 加 `rest_endpoints` 过滤，未登录时移除 users 路由（示例代码待确认后实施）

### R4. 部署产物会带出开发文件（上线前清理）
- 位置：主题目录内 `_backup/`（30+ 快照，含 functions.php.deployed.bak、全量历史 style.css）、`tools/`（129 个 JS 测试脚本）、`screenshots/`（795 张）、`docs/`
- 影响：部署后这些文件成为公开可下载内容——.bak 不被 PHP 解析，会以纯文本暴露完整后端代码结构；截图泄露后台运营状态。本地已验证：源目录无 .git、/.git/HEAD 404、wp-config.php 输出 0 字节、debug.log 不存在——运行站本身干净，风险只在部署打包环节
- 修法：上线部署清单中加一条：rsync 排除 `_backup/ tools/ screenshots/ docs/ .DS_Store`，或上线前从主题目录移走

---

## 🟡 中等（建议修）

### Y1. 表单通知 From 地址直接用访客邮箱
- 位置：4 个表单的 Admin Notification 均 `from: {Email:x}`（Form2/3/5 用字段3，Form4 用字段4）
- 影响：From 与服务器域名不对齐 → DMARC/SPF 失败率高、通知信进垃圾箱；也是经典的邮件头注入最佳实践违规点（GF 2.9+ 对 From 有过滤，实际注入风险低，主要是送达率问题）
- 修法：From 固定为域名邮箱（如 website@zxpet.com），Reply-To 保留 `{Email:x}`（已有，正确）

### Y2. Cookie 弹窗「Manage Preferences」是假的
- 位置：assets/js/ui-components.js（sf-cookie 段）：`on(".sf-cookie-banner__manage", () => decide(false))` ——点击即静默拒绝，无偏好面板
- 影响：GDPR 要求同意可细分、可撤回。当前既不能按类别选择，同意后也无任何重新打开/撤回入口（存 localStorage，无重开按钮）
- 修法：最小改法——页脚加"Cookie Settings"链接重新显示 banner；"Manage Preferences"要么改名为"Reject"要么真做偏好面板。当前站内无任何第三方追踪脚本（见 G5），实际数据风险为零，主要是合规文本与交互不一致

### Y3. 品牌绿/橙对比度不达 WCAG AA
- 位置：theme.json 色板 + style.css；实测 #5ab735 on 白 = 2.54:1，#e8923a on 白 = 2.44:1（正文要求 4.5，大字/非文本要求 3.0）
- 影响：绿/橙作正文文字、按钮白字、CTA 焦点描边（style.css:256 用的是橙色）的场景全部不达标
- 修法：文字与焦点描边引入深色变体（绿 #4a9427 一类可达 3:1+，正文需更深）；#5ab735 保留给装饰/下划线/大面积底色（白字加粗放大在按钮上仍建议换深绿）。具体替换范围可在修复阶段逐处过

### Y4. GF 输入框聚焦态只剩边框变色
- 位置：style.css:152-156 `.gform_wrapper input:focus { border-color: cta !important; outline: none; }`（search 框同款 237 行）
- 影响：全局 `:focus-visible` 有 2px 描边（style.css:253-258），但 GF 规则特异性更高把表单内 outline 干掉了；1px 边框变色是弱可见指标（WCAG 2.2 Focus Appearance 建议 ≥2px）
- 修法：聚焦态 outline 保留或边框加粗到 2px

### Y5. 数据留存无期限（GDPR 留存策略缺失）
- 位置：WP Mail Logging 插件（所有外发邮件含表单个人数据落库）+ GF entries 默认永久保留
- 修法：上线清单加数据留存政策：GF entries 保留 N 个月后清理、邮件日志停用或限期；隐私政策页面写明留存期

### Y6. generator meta 泄露 WP 版本号
- 位置：所有页面 `<meta name="generator" content="WordPress 7.1">`
- 修法：functions.php 移除 generator（一行过滤）

### Y7. 实验性插件 AI 1.3.0 激活中
- 位置：wp-content/plugins/ai/（WordPress 官方实验插件，非自研）
- 影响：无使用场景的额外攻击面（abilities/REST 端点）
- 修法：确认无用后停用

### Y8. xmlrpc.php 可达（405）
- 位置：http://sinofresh.local/xmlrpc.php
- 修法：nginx 层直接 444/403，或 WP 内禁用

---

## 🟢 轻微（可修可不修）

### G1. functions.php:650-651 `echo $i` 未显式转义
循环计数器 int 变量，实际安全；风格上补 `(int)` 更严谨。

### G2. 首页 12 张 avatar 空 alt
testimonial 头像旁有可见姓名文本，空 alt 符合 WCAG（装饰图处理），可不改。

### G3. Product Schema 无 offers
8 个剂型页的 Product JSON-LD 缺 offers 字段，Google 会给 warning（非错误）。OEM 代工无标价属正常业务，可接受 warning，或在 Search Console 忽略。

### G4. FAQPage 富结果大概率不展示
标记语法有效（必填字段齐全），但 2023 年起 Google 仅对政府/健康站点展示 FAQ 富结果。保留无害，别指望 SERP 展示。

### G5. GF 隐私同意用的是 checkbox 而非专用 Consent 字段
GF Consent 字段类型可自动记录政策文本+时间戳，举证更强。现 checkbox 功能上够用。

### G6. 表前缀 wp_ 为默认值
Local 环境现状，存量迁移成本高，知情即可；上线全新安装时可用随机前缀。

---

## ✅ 扫描通过项（无需行动）

| 项 | 结果 |
|---|---|
| PHP 转义 | functions.php 全部输出经 esc_html/esc_attr/esc_url；JSON-LD 全走 wp_json_encode |
| SQL | 全站 0 处 $wpdb / SQL 拼接 |
| 文件包含 | file_get_contents 仅读主题内模板文件，slug 来自 WP post_name，无用户输入直达 |
| 设置页 | current_user_can + Settings API nonce + 全字段 sanitize_callback |
| 敏感词扫描 | password/api_key/secret/token 零命中（全部为色值 token/遮罩等误报） |
| JSON-LD 语法 | 10 页全部解析成功，零语法错误；Article/Breadcrumb/Organization/FAQPage/Product 必填字段全齐 |
| HTML 合规 | 无重复 ID、无 <p><figure> 嵌套、img alt 全覆盖（no-alt=0） |
| a11y 结构 | 表单 label 全关联（唯一未标注为隐藏字段）、aria-required/fieldset/legend 齐、灯箱/轮播/浮动按钮 aria 完善 |
| 键盘焦点 | 全局 :focus-visible 2px 描边存在（GF 输入框为 Y4 所述弱化场景） |
| Cookie 弹窗 | 所有页面生效；隐私政策/Cookie 政策/Terms 链接全部 200 |
| 第三方追踪 | 全站零第三方脚本；YouTube 走 nocookie + 点击后加载 |
| .git/配置泄露 | 无 .git 目录；wp-config.php 输出 0 字节；debug.log 不存在；uploads 目录列表 403 |

---

## 建议修复顺序

1. R1 + R2（表单后台配置，半小时内可完成，风险最高收益最快）
2. R3 + Y6（functions.php 各加一小段，同一次提交）
3. R4（写进上线部署清单）
4. Y1-Y5（表单通知、Cookie JS、对比度、聚焦态、留存策略）
5. G 项按需
