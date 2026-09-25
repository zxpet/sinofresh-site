# 生产上线 Runbook（2026-09-25 起草，未执行）

> 状态：**方案待确认，未动生产**。确认后按阶段执行，每阶段末有验收点，任一失败即停。
> 回滚原则：旧生产（`/var/www/html` + DB `wordpress`）**整个保留不动**，回滚＝vhost 指回去，<1 分钟。

## 0. 勘察事实（2026-09-25 实测）

| 项 | dev（新站） | 生产（旧站） |
|---|---|---|
| docroot | `/var/www/dev.zxpet.com/public` | `/var/www/html` |
| DB | `sinofresh`（11.3 MB，prefix `wp_`） | `wordpress` |
| WP / PHP | 7.1.2 / 8.3.33 | 7.1.1 / 8.3.33 |
| 主题 | sinofresh-theme 2.10.82（软链→site-repo） | generatepress |
| 关键插件 | Fluent Forms 6.2.14 / TP 3.3.6 / WPS 14.16.14 / fluent-smtp | rank-math / fluent-smtp / puffergo / naibabiji |
| blog_public | 0（封锁中） | 1 |
| home/siteurl | https://dev.zxpet.com | https://www.zxpet.com |
| uploads | 67 MB | 12 MB |
| robots.txt | `Disallow: /` | — |
| mu-plugins | dev-lockdown / preflight / wps-consent-bridge | 无 |
| 磁盘余量 | 14 G（够） | |
| 证书 | `/etc/letsencrypt/live/zxpet.com/`（SAN＝zxpet.com + www.zxpet.com，直接可用） | |
| 443 vhost | `zxpet.com-le-ssl.conf`，DocumentRoot=/var/www/html | |

## 1. 策略：新目录 + 新 DB 晋升（方案 A）

不用原地升级 `/var/www/html`（旧站内容与 dev 完全不同源，原地拼装风险高、不可回滚）。
新站整体晋升为一个**新 docroot + 新 DB**，vhost 切 DocumentRoot 一刀切换。

**架构决策点（需确认）**：
- **D1 主域**：维持 `https://www.zxpet.com`（现状、SEO 延续、证书 SAN 已覆盖）。apex `zxpet.com` 301→www（现 vhost 已是这么做的）。
- **D2 旧生产内容**：`/var/www/html` + DB `wordpress` 原样保留作回滚（推荐），暂不清理不归档。
- **D3 dev 数据携出物**：dev DB 里的 WP Statistics 统计与 Fluent Forms 测试提交是否随迁？
  建议：迁移时 **TRUNCATE WP Statistics 表 + FF 测试提交**（生产不带测试数据），统计从零开始。
- **D4 CF 面板两件**（本机无 API token，需你手配，可同窗口做）：
  ① rate limit rule：`http.request.uri.path eq "/wp-json/sinofresh/v1/inquiry" and http.request.method eq "POST"`（建议加 `and not http.host eq "dev.zxpet.com"` 以免挡住 dev 的门测试），阈值 1 req / 60s / per IP，action=Block 60s——与服务器侧 60s 对齐，两层叠加；
  ② dev 域名 Bypass cache rule（dev-lockdown §8.1 遗留，顺手）。

## 2. 阶段与验收

### P0 备份（不动状态）
- `mysqldump` sinofresh + wordpress 两库 → `/root/golive-backup-<ts>/`
- `tar` `/var/www/html` 全量 → 同目录；`/etc/httpd/conf.d/` 全量副本 + sha256
- 验收：备份文件存在、大小合理、`sha256sum -c` 通过

### P1 构建新栈（生产不受影响）
1. `rsync -a /var/www/dev.zxpet.com/public/ /var/www/zxpet-v2/`，**剔除**：
   `wp-content/mu-plugins/zz-sf-dev-lockdown.php`、`zz-sf-preflight.php`、`zz-sf-preflight.log*`（→ §9 第 3 项）
2. mu-plugins 只留 **`zz-sf-wps-consent-bridge.php`**（从仓库 `server/mu-plugins/` 取源码 → §9 第 11 项，⚠️ 不走软链必须显式拷）
3. 主题解软链：`rsync` 后 sinofresh-theme 已是实拷贝（确认 `git log` 对应 9bbd97e）
4. DB：`CREATE DATABASE zxpet_prod` → 导入 sinofresh dump →（按 D3）清统计/测试提交
5. `wp search-replace 'https://dev.zxpet.com' 'https://www.zxpet.com' --all-tables`（含裸 `dev.zxpet.com` 复扫一遍）
6. 新 `wp-config.php`：指向 zxpet_prod、**无 `SF_DEV_LOCKDOWN`**（→ §9 第 4 项）、新随机 salts
7. `wp option update blog_public 1`（→ §9 第 7 项 ⚠️ 最易漏）
8. `robots.txt` 换正式版（`Disallow: /wp-admin/` 型，→ §9 第 6 项）
9. Basic auth / X-Robots-Tag 只存在于 dev vhost——新 vhost 重写时天然不带（→ §9 第 1/2/5 项）；`.htpasswd` 是 dev 实体**保留不动**（dev 还要用，§9 第 2 项顺延到 dev 退役时）
10. 验收：`wp core verify-checksums`（php-ai-client 差异为预已知）、`wp plugin list` 与 dev 一致、首页 200

### P2 切换前预验（不经公网）
- 临时 vhost `:8080` 指向 `/var/www/zxpet-v2`，`curl -H 'Host: www.zxpet.com' http://127.0.0.1:8080/` 全链路：
  首页 200 / 主题样式 `ver=2.10.82` / 无 `noindex` / 无 `WWW-Authenticate` / robots.txt 正式版 / hreflang / inquiry 端点 429 行为
- 验收后**删除临时 vhost**

### P3 切换（秒级）
- `zxpet.com.conf` 与 `zxpet.com-le-ssl.conf`：DocumentRoot → `/var/www/zxpet-v2`（两处）
- `apachectl -t && systemctl reload httpd`
- 停机窗口＝reload 一瞬，无维护页需要

### P4 上线后自检（§9 末尾两条 + 扩展）
```bash
curl -sI https://zxpet.com/ | grep -iE "www-authenticate|x-robots-tag"   # 应无输出
curl -s  https://zxpet.com/ | grep -o "<meta name=.robots.[^>]*>"        # 应无 noindex
curl -s  https://zxpet.com/robots.txt                                    # 不应 Disallow: /
```
- 扩展：首页/表单页 200、inquiry 60s 节流 429、consent 门（未同意 0 hit）、sitemap、SEO 头、CF 缓存命中率
- dev 站保持封锁不动（继续当开发环境，DB 已导出快照）

### P5 回滚（随时可执行）
- vhost DocumentRoot 指回 `/var/www/html` + `systemctl reload httpd`
- DB 无需动（wordpress 库全程未写）

## 3. §9 十一项映射核对表

| §9 项 | 本 runbook 处置 |
|---|---|
| 1 Basic Auth / 2 .htpasswd / 5 X-Robots-Tag | 新 vhost 不含；.htpasswd 保留给 dev（退役时再删） |
| 3 meta robots 门控 | rsync 剔除 dev-lockdown mu-plugin |
| 4 SF_DEV_LOCKDOWN | 新 wp-config 不写 |
| 6 robots.txt | P1.8 换正式版 |
| 7 blog_public | P1.7 → 1 |
| 9 CF cache rule | D4② dev bypass 保留（dev 还在）；生产无 bypass 规则 |
| 10 CF Access / IP 白名单 | 未启用，N/A |
| 11 mu-plugins 单独部署 | P1.2 只带 consent-bridge |

## 4. 明确不做

- 不删 `/etc/httpd/.htpasswd-dev.zxpet.com`（dev 仍在用）
- 不清理 `/var/www/html` 与 `wordpress` 库（回滚资产）
- 不动 dev 站封锁（dev 继续开发）
- CF 面板操作（D4）由你手配，我只提供表达式与验证清单
