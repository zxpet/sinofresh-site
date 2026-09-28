# 上线前置只读扫描报告：两个"数据系统"查明（2026-09-28）

> 状态：**只读扫描，未改任何文件/数据/生产**。等确认后才进入上线阶段。

## 一、结论：不是 Multisite，是两套独立的 WordPress

| 排查项 | 结果 |
|---|---|
| `MULTISITE` 定义 | 两个 wp-config.php 都**没有** |
| `wp_blogs` / `wp_site` 表 | 全服务器所有库中**一张都不存在** |
| 后台"我的站点" | 单站点（无站点网络菜单） |

**真实结构＝同一台 VPS 上装了两套 WordPress、两个数据库：**

| | 旧生产（现 zxpet.com） | 新站（现 dev.zxpet.com） |
|---|---|---|
| docroot | `/var/www/html` | `/var/www/dev.zxpet.com/public` |
| 数据库 | `wordpress`（prefix `wp_`） | `sinofresh`（prefix `wp_`） |
| DB 用户 | `wpuser` | `sinofresh` |
| WP 版本 | 7.1.1 | 7.1.2 |
| 主题 | generatepress | sinofresh-theme 2.10.88（软链） |
| 活跃插件 | rank-math、fluent-smtp、puffergo、naibabiji-b2b-product-showcase | fluentform、translatepress、wp-consent-api、wp-mail-logging、wp-statistics |
| 内容 | 7 页（Home/About/Contact/Factory Tour/Blog/Thank You/示例页面）＋ 6 篇文章 | 26 页 ＋ 7 篇文章（完整业务站） |
| uploads | 12 MB | 201 MB |
| 当前状态 | **全站 302 → maintenance.html（维护页）** | Basic 认证封锁中，blog_public=0 |

## 二、两个"系统"各是什么

- **旧站＝模板演示壳**：6 篇文章全是 **LED 照明行业**的占位文（AeroPro Zigbee、DLC 5.1、IP65、冷库灯、高天棚灯间距）——与宠物食品毫无关系，是建站模板自带的演示内容（`naibabiji-b2b-product-showcase` 插件＋`puffergo` 主题＋中文"示例页面"＋"世界，您好"）。
- **旧站现在对访客完全不可见**：`.htaccess` 里 `RewriteRule ^.*$ /maintenance.html [R=302,L]`，全站跳维护页（自 09-19 前后）。
- **新站＝真正的 SINO FRESH 官网**，内容完整、门禁齐全、随时期待上线。

## 三、合并方案与风险：**不需要合并**

- 两库完全不同源、旧站零业务内容（无可迁移的文章/页面/SEO 价值）⇒ **不存在数据库合并**，只有"整体替换"。
- 唯一值得从旧站确认带走的是 **SMTP 发信配置**——但扫描发现旧站 `fluent_smtp_settings` 也是**空的**（插件激活了没配），dev 甚至没装 fluent-smtp。⇒ **两边的表单邮件目前都走 PHP mail()**，上线前需要配一次 SMTP（或验证 mail() 可达 sales@zxpet.com），否则询盘通知可能进垃圾箱/丢失。这是新发现的上线缺口。
- 风险因此大幅降低：旧站没有真内容，"切错方向"的代价＝回到维护页而已；回滚＝vhost 指回 `/var/www/html`（<1 分钟）。

## 四、要上线的那个：sinofresh（dev）

按已定稿 runbook（`docs/golive-runbook-2026-09-25.md`）方案 A：
新 docroot `/var/www/zxpet-v2/` ＋ 新 DB `zxpet_prod` ← 导入 `sinofresh` dump ＋ search-replace 域名 → vhost 切 DocumentRoot；旧站与 `wordpress` 库原样保留作回滚。

### 你的 noindex 指令对 runbook 的两处修改（已确认后执行）

| runbook 原文 | 改为（按你本次指令） |
|---|---|
| P1.7 `wp option update blog_public 1` | **保持 0**（sinofresh 库本来就是 0，克隆过来即 noindex；不执行 update 1） |
| P1.8 robots.txt 换正式版 | 换成**你的 AI 拦截版**：`User-agent: *` ＋ GPTBot/ClaudeBot/PerplexityBot/Google-Extended 全部 `Disallow: /` |
| P2/P4 预验与自检 | 断言**反转**：应看到 noindex meta ＋ robots Disallow，访客正常 200（非维护页、无 Basic 认证） |

注意一个机制细节：`blog_public=0` 只输出 `User-agent: * Disallow: /`，且**物理 robots.txt 存在时 WP 虚拟 robots 不生效**——所以你的"方法一＋方法二"实际合并为一份物理 robots.txt（含 `User-agent: *` 段），`blog_public=0` 作为第二道保险（输出 noindex meta）。放开收录时：改 robots.txt ＋ `blog_public 1` ＋ GSC 提交 sitemap，三步。

## 五、待确认清单（进入 P0 前需要你点头）

1. **确认无需合并、直接整体替换**（旧站是演示壳，无内容可迁）。
2. **D1 主域**：`https://www.zxpet.com` 为规范域，apex 301→www（runbook 原建议，未变）。
3. **D3 测试数据**：生产库 TRUNCATE WP Statistics ＋ FF 测试提交（统计从零开始）。
4. **D4 CF 面板两件**（需你手配）：inquiry 端点 rate limit ＋ dev bypass cache。
5. **SMTP 缺口**：上线前配 fluent-smtp（新站需安装配置）或验证 mail() 可达——否则询盘通知不可靠。
6. 上线后按你的指令：blog_public 保持 0 ＋ AI 拦截 robots.txt ＋ GSC 验证"已被 robots.txt 屏蔽"。

**扫描完毕，停在这里。确认后按 runbook 分阶段执行（P0 备份 → P1 构建 → P2 预验 → P3 切换 → P4 自检），每阶段末停下验收。**
