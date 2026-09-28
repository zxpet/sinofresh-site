# SMTP 真因定位报告（2026-09-28）

> 起因：dev 站 15:57 提交表单，**回执 + 通知两封都收到** ⇒ 推翻此前「腾讯账号级限流」结论。
> 本报告为**只读诊断**，**未做任何修改**；修复方案已端到端验证可行，等确认后执行。

---

## 一、结论（一句话）

**prod 库里 FluentSMTP 存的客户端专用密码已失效；dev 库存的是新密码。两边 `wp-config` 的 salts 完全相同、导入也是逐字节忠实的——不是导入 bug，是 dev 在导入之后换过密码，prod 没同步。**

---

## 二、假设证伪过程

| 假设 | 验证方法 | 结果 |
|---|---|---|
| ~~A. 腾讯账号级限流~~ | 同一时刻、同一服务器、同一 smtp 主机，分别用两边密码直连 465 做 AUTH LOGIN | dev `235 Authentication successful`／prod `535 system busy` ⇒ **账号没被限流，是密码本身被拒** |
| ~~B. DB 导入/迁移出错~~ | 从 P1 导入源 dump（06:33）里提取密码密文，与 prod 当前值比 | 密文 md5 `0ec1c000…` **完全相同** ⇒ 导入忠实，**非导入 bug** |
| **C. prod 的密码已失效（真因）** | 解密两边密文取明文 md5 对比 | dev `72275dd9…` ≠ prod `fa667daf…` ⇒ **两把不同的密码** |

---

## 三、证据

### 3.1 配置逐字段对比（`fluentmail-settings`）

```
[DIFF] .connections.0534d693…provider_settings.password:
         dev  = xO12ar1Ex1rUv/+4jR8qTnVk…  (len 168)
         prod = M7luCJd0JYAN52HELvpWSnJv…  (len 168)
[DIFF] .test:                       ← 无关的连接测试暂存令牌
         dev  = pnFNDDP8FC9bcUVJPivgC2lC…
         prod = j57h6fx0x+zhWTbXwnS8U0pp…
（以上为全部差异，其余字段逐个相等）
```

### 3.2 加密密钥（`wp-config.php`）—— **完全相同**

| 常量 | dev md5 | prod md5 | |
|---|---|---|---|
| `LOGGED_IN_KEY` | `d06dd715466752ec6b95eabae5515b6a` | 同左 | ✅ 一致 |
| `LOGGED_IN_SALT` | `30e923afa64d858ae838a60201ba40be` | 同左 | ✅ 一致 |

⇒ 盐决策（这 2 枚沿用 dev）执行正确；两侧密文都能用各自 salts 正常解出 16 位明文。

### 3.3 明文对比（解密后）

| | 明文长度 | 明文 md5 |
|---|---|---|
| dev | 16 | `72275dd938c9279f765a503121312815` |
| prod | 16 | `fa667daf9f1930b85ea72ba26b9e5a1b` |

### 3.4 SMTP 直连认证（同一时刻、同一服务器）

| 用哪边的密码 | SMTP 应答 | 判定 |
|---|---|---|
| dev 的 | `235 Authentication successful` | ✅ 有效 |
| prod 的 | `535 Error: authentication failed, system busy` | ❌ 失效 |

⇒ 所谓 "system busy" 是腾讯对**失效客户端密码**的通用文案，**不是限流**。这是我此前误判的根源。

### 3.5 dump 取证（判定「导入 bug」还是「事后变更」）

| dump | 时间 | 里面的 password 密文 md5 | 对照 |
|---|---|---|---|
| `golive-backup-20260928-0520/db-sinofresh.sql.gz` | 05:20 | **无该 option** | FluentSMTP 当时尚未配置 |
| `golive-build-20260928-0633/db-sinofresh-fresh.sql.gz` | 06:33 | `0ec1c000e1263d7ef1090e0883597400` | **= prod 当前值** |

⇒ 导入把 06:33 那一刻 dev 的值**原样搬了过来**。差异是**导入之后**在 dev 侧产生的。

### 3.6 prod 重测（临时 vhost，16:04:18）

```
HTTP 500
{"code":"sf_inquiry_mail","message":"We could not send that just now. Please try again.","data":{"status":500}}

wp_fsmpt_email_logs（prod）：
id 8 | failed | [Inquiry] Website — P2 retest | 16:04:18
       response = a:3:{s:4:"code";i:422;s:7:"message";s:35:"SMTP Error: Could not authenticate.";s:6:"errors";N;}
```

### 3.7 交叉验证：**修复方案已证明可行**

用 **prod 的 `wp-config`（salts）** 解 **dev 的密文**，再实连 SMTP：

```
cipher_source=EXTERNAL(交叉) md5=b3ac3c10c1508e8f911ee312f9251b88
decrypt: OK len=16 md5=72275dd938c9279f765a503121312815
SMTP: 235 Authentication successful
AUTH_RESULT: *** SUCCESS ***
```

⇒ 只要把 dev 的配置搬进 prod，**立即恢复发信**，无需重新输入密码、无需改 salts。

---

## 四、时间线重建（与全部证据自洽）

| 时刻(UTC+8) | 事件 | 证据 |
|---|---|---|
| ≤05:20 | dev 未配置 FluentSMTP | P0 dump 无该 option |
| 05:20–06:33 | 在 dev 配置 FluentSMTP，密码 = **P_old** | 06:33 dump 密文 = P_old |
| 06:33 | dev → prod 导入，prod = **P_old** | 密文逐字节相同 |
| 13:33 | dev 发信成功 | dev 日志 id 1/2 `sent` |
| 14:38:57 | prod 发信成功 | prod 日志 id 1 `sent` |
| ~14:39 | **P_old 失效**（腾讯侧该客户端密码被重新生成/删除） | prod 14:39:24 起连续 422 |
| ~14:39–14:55 | dev 换用 **P_new** | dev 14:55 起发信成功 |
| 15:57 | dev 两封均送达（用户实测） | dev 日志 id 5/6 `sent` |
| 16:04 | prod 重测仍失败（仍持 P_old） | prod 日志 id 8 `failed` |

> 无法从 `wp_options` 直接读到「改动时刻」（该表无时间戳），故 14:39 这个时点是由「prod 14:38:57 成功 → 14:39:24 失败」这一对日志**夹逼**出来的。

---

## 五、修复方案（**待确认，尚未执行**）

### 方案 A（推荐）：把 dev 的 `fluentmail-settings` 覆盖进 prod

```bash
# 0) 先备份 prod 现值（可回滚）
cd /var/www/zxpet-v2
wp option get fluentmail-settings --format=json --allow-root \
  > /root/prod-fms-backup-20260928-1600.json

# 1) dev → prod 覆盖（一条命令）
cd /var/www/dev.zxpet.com/public
wp option get fluentmail-settings --format=json --allow-root \
  | ( cd /var/www/zxpet-v2 && wp option update fluentmail-settings --format=json --allow-root )

# 2) 验证：探针应回 235
php /tmp/smtp-auth-probe.php PROD /var/www/zxpet-v2

# 3) 真发验证：向临时 vhost 提交一次测试询盘 → 日志应为 sent
# 4) 回归门：python3 tools/p2_preverify.py --with-mail  应 37/37
```

**回滚**：`wp option update fluentmail-settings --format=json --allow-root < /root/prod-fms-backup-20260928-1600.json`

- 优点：一条命令、已交叉验证、可秒级回滚、不动 salts。
- 风险：极低（两侧 salts 相同，密文直接可用）。

### 方案 B：只替换 `password` 单个字段
等价于 A，改动面更小，但需要 PHP 读改写（多一步、无额外收益）。

### 方案 C：在 prod 后台重新输入密码
临时 vhost 只绑 loopback，浏览器登录 admin 会因主机名不一致触发跨域跳转，不便；P3 切到正式域名后可行。

**建议 A。**

---

## 六、附带发现（**独立问题**，不阻塞本次修复）

**postfix relay 仍持第三把失效密码**：

```
最近 3 小时 SASL authentication failed 次数：108
最新一条：Sep 28 07:09:38 UTC → sales@zxpet.com  status=deferred
         said: 535 Error: authentication failed, system busy
/etc/postfix/sasl_passwd 密码明文 md5 = f65dd323c8e37539cbaf156e3a48941d
对照：dev 可用密码 = 72275dd9…   prod 旧密码 = fa667daf…   （第三把，两者都不是）
队列现状：0 封（此前清空有效）
```

- 它**不会**影响网站发信（WP 邮件全走 FluentSMTP），但持续对腾讯做失败认证，属卫生问题。
- 处置二选一：① 改为当前可用密码；② 若确认网站/系统不依赖 postfix 外发，直接停用 relay。
- 另外：postfix 走 **587**，FluentSMTP 走 **465/SSL**，两者路径本就不同。

---

## 七、需要更正的既有记录

| 位置 | 原结论 | 更正为 |
|---|---|---|
| 本报告 §3（`golive-p2-report-2026-09-28.md`） | 「配置正确，但账号被腾讯限流」 | 「prod 的客户端密码已失效；dev 持新密码」 |
| 同上「两个密码不一致」表 | 归因 postfix 旧凭据触发风控 | postfix 是**独立**问题；FluentSMTP 失败是**密码本身失效** |
| runbook §5 / MEMORY.md 的 SMTP 卡点条目 | 「限流，需腾讯侧解封」 | 「同步 dev 的 fluentmail-settings 即可」 |

---

## 八、验证用的临时探针（服务器 `/tmp`，修复后删除）

- `/tmp/fms-probe.php` — 解密密文 + 打印 salts/密文 md5
- `/tmp/smtp-auth-probe.php` — 用本机配置实连 SMTP，只打印应答码
- `/tmp/smtp-auth-probe2.php` — 支持外来密文的交叉验证版

均**只输出 md5 与 SMTP 应答码**，不打印任何明文密码。
