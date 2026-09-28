# 上线 P3 切换报告（2026-09-28）

> 执行范围：runbook v3 的 **P3（vhost 切换）＋ 你指定的 4 项顺带工作**。
> **已切换完成，www.zxpet.com 现由 `/var/www/zxpet-v2`（新栈）服务。**
> P2 报告见 `golive-p2-report-2026-09-28.md`，SMTP 真因见 `golive-smtp-rootcause-2026-09-28.md`。

---

## 一、切换时间

| 事件 | 时间 |
|---|---|
| 4 处 DocumentRoot 替换完成 + reload | **2026-09-28 16:33:40（北京时间）/ 08:33:40 UTC** |
| SSL 修复后 reload（恢复公网） | 16:36 前后（中断窗口约 **2–3 分钟**） |

## 二、执行步骤与结果

| # | 步骤 | 结果 |
|---|---|---|
| 1 | 删临时 vhost `zz-temp-v2-preverify.conf` | ✅ 副本存 `/root/golive-p3-archive-20260928/`；8080 端口已关 |
| 2 | 启用 noarchive 头 | ✅ `zz-noindex-zxpet.conf.disabled` → `.conf`；`X-Robots-Tag: noindex, nofollow, noarchive` 生效。**注意：全局作用域**（本机仅此项目，可接受） |
| 3 | drop `wp_gf_*` 遗留表 | ✅ 实际 **8 张**（非 6 张，多出 `wp_gf_form_view`/`wp_gf_form_revisions`）；先 `wp db export` 备份（`/root/gf-tables-prod-backup-20260928.sql` + `.gz` + sha256），后 drop。总表数 52→44 |
| 4 | `blogname` → **SINO FRESH** | ✅ 首页 `<title>SINO FRESH</title>` 已生效 |
| 5 | 切换 4 处 `DocumentRoot`（+4 处 `<Directory>`，共 8 处）→ reload | ✅（见下方事故） |

### 事故：www 的 :443 vhost 缺 SSL 指令 → 重定向环（已修复）

**现象**：切换 reload 后，`https://www.zxpet.com/` 无限 301（`X-Redirect-By: WordPress`），**公网中断约 2–3 分钟**。

**根因**：`wordpress-zxpet.conf` 的 `:443` vhost **从未配置过任何 SSL 指令**（无 `SSLEngine on`、无证书文件）。Apache 找不到可用的 www SSL vhost，把 SNI=www 的 443 请求按 :80 配置处理 ⇒ PHP 收到 `SERVER_PORT=80` / `HTTPS=(unset)` ⇒ WP `is_ssl()`=false 而 `home` 是 https ⇒ 规范化 301 打环。

**为什么以前没爆**：旧站是 `.htaccess` 静态维护跳转，不关心 HTTPS；新站是标准 WP，才会被这个坑打中。**属于切换前就存在的结构性配置缺陷，被旧站掩盖**。

**修复**：给 `:443` vhost 补上
```
Include /etc/letsencrypt/options-ssl-apache.conf
SSLEngine on
SSLCertificateFile /etc/letsencrypt/live/zxpet.com/fullchain.pem
SSLCertificateKeyFile /etc/letsencrypt/live/zxpet.com/privkey.pem
```
证书 SAN 覆盖 `zxpet.com` + `www.zxpet.com`。修复后本机+公网均 200 无跳转。
修复前后文件存档：`/root/golive-p3-archive-20260928/wordpress-zxpet.conf.before`（替换+DocumentRoot 后）与 `.prelsfix`（修复前最后状态）。

### 顺带清理

- 库里唯一本地路径残留 `wp_statistics_tracker_js_errors` option（含 `/Users/meng` 调试日志）已删；全库再无 `sinofresh.local` / `dev.zxpet.com` / 本地路径残留。
- P3 测试痕迹（FF 提交 1 条 + 邮件日志 3 条）已归档 `/root/p3-test-traces-archive-20260928-084833.txt.gz` 后删除，表清零。

## 三、切换后自检（逐项）

| # | 检查项 | 结果 |
|---|---|---|
| 1 | `www.zxpet.com` 200，显示新站 | ✅ 200；`<title>SINO FRESH</title>`；主题 2.10.88（`ver=2.10.88`）；Playwright 实截图确认（`docs/golive-p3-live-home-2026-09-28.png`） |
| 2 | robots.txt = Disallow 版 | ✅ `User-agent: *` / `Disallow: /` + AI 爬虫显式拦截段 |
| 3 | 首页无 noindex 遗漏 | ✅ 三道保险齐：`<meta name='robots' content='noindex,nofollow'>` + `X-Robots-Tag: noindex, nofollow, noarchive` + `blog_public=0` |
| 4 | SMTP 测试邮件能收到 | ✅ 真实邮箱可核收（见 §四） |
| 5 | 图片正常显示 | ✅ 首页抽样 12 张全 200；产品页图片 0 异常；CSS/JS 抽样全 200 |
| 6 | 询盘表单提交，两封邮件都到 | ✅ Fluent Forms「Get a Quote」真实提交 → **2 封全部 `sent`**（见 §四） |

**补充核验**：

- 33/33 已发布 page/post 全 200；`sf_formula` 21/21 全 200；8 个剂型短链 301 归一化后全部 200。
- hreflang 当前仅 `en`/`en-US` —— 与 ZH/DE/ES 未发布的现状一致（重新启用属后续独立工作）。
- `zxpet.com`（apex）→ 301 → `https://www.zxpet.com/` → 200，归一正确。
- CF→源站为 **HTTPS 回源**（日志实证），无 Flexible 回源的重定向环风险。

## 四、SMTP / 询盘邮件实测（16:47–16:48）

真实提交 Fluent Forms form 8「Get a Quote」（提交记录 insert_id=1，已归档后清理）：

| # | 收件人 | 主题 | 状态 |
|---|---|---|---|
| 1 | `sales@zxpet.com` | `New Inquiry: Soft Chews from SINO FRESH QA (Germany)` | **sent / OK** |
| 2 | `p3-ff@example.com`（提交者） | `We've received your inquiry — SINO FRESH` | **sent / OK** |

外加 REST 配方询盘端点 1 封（`[Inquiry] Website — P3 self-test` → sales，sent）。
**通知与回执双链路均实发成功。** 请到 `sales@zxpet.com` 收件箱核对上面两封真实可达的邮件。

## 五、新旧站状态

| | 状态 |
|---|---|
| **新站** `/var/www/zxpet-v2`（507M） | **在线服务 www.zxpet.com**；DB `zxpet_prod`；主题 2.10.88；mu-plugins 仅 consent-bridge；`blog_public=0`；robots=AI 拦截版 |
| **旧站** `/var/www/html`（185M） | **原封未动**（文件与库都在，只是不再被服务）；随时可回 |
| 回滚 | 改回 4 处 DocumentRoot → reload（<1 分钟）；配置备份全在 `/root/golive-p3-archive-20260928/` |

## 六、遗留事项

| # | 事项 | 说明 |
|---|---|---|
| 1 | **核对真实收件** | 请到 `sales@zxpet.com` 确认收到 §四 两封测试邮件（服务器侧已 `sent`，若收件箱没有请查垃圾箱/企邮后台投递记录） |
| 2 | 泄露的旧密码轮换 | P2 遗留项，失效密码风险已消；要不要在企邮后台轮换客户端专用密码由你定（换后需同步 FluentSMTP + postfix 两处） |
| 3 | `p2_preverify.py` 门已过时 | 门针对已删除的临时 vhost（:8080）；后续如需回归门，需改指正式站 |
| 4 | P6（打开收录）未执行 | 当前仍 noindex。等你确认站点内容/SEO 就绪后，按 runbook P6 操作（`blog_public 0→1` + 换 robots.txt + 摘 noindex 头） |
| 5 | dev 站与生产的关系 | dev（`dev.zxpet.com`）仍在 Basic Auth 后正常运转，作为后续开发环境；两者已完全独立 |
