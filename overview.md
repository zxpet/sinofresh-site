# 上线 P2 收尾 — SMTP 修复 + 三步验收（2026-09-28 16:25）

**结论：方案 A 已按确认执行并全部验收通过。prod 发信恢复，postfix 旧凭据一并换新。P2 全绿，P3 待你点头。**

## 做了什么

| 步 | 动作 | 结果 |
|---|---|---|
| 1 | 备份 prod `fluentmail-settings` → 用 dev 值覆盖 | 回读逐字节一致；密文 md5 `b3ac3c10…`（=dev） |
| 2 | `/etc/postfix/sasl_passwd` 失效密码 → 有效密码 + `postmap` + reload | 实测 `status=sent (250 Ok)`，队列 0 |
| 3 | 三步验收 | 探针 `235` ✅ / 询盘重测日志 `sent` ✅ / 门 `--with-mail` **37/37** ✅ |
| 4 | 清 P2 痕迹 | 邮件日志 10 行归档后删除（现 0 行）；探针 + 明文临时文件已销毁 |

## 关键决策 / 变更

- **只动两个东西**：prod 的 `fluentmail-settings` option + postfix 凭据。**未碰 docroot、未碰 DB 结构、未碰旧站 `/var/www/html`。**
- **备份/回滚**：
  - `fluentmail-settings` → `/root/prod-fms-backup-20260928-081513.json`（回滚＝`wp option update fluentmail-settings --format=json < 该文件`）
  - postfix → `/etc/postfix/sasl_passwd.bak.20260928-081625`
- 根因复核过程中纠正了一处旧记忆：postfix 里其实是**32 位失效密码**（md5 `a820bfaa…`），非早前记的 16 位值。

## 下一步（P3，待确认）

- 切换 3 文件 4 处 `DocumentRoot` → `/var/www/zxpet-v2`，`systemctl reload httpd`（秒级；回滚 <1 分钟）。
- P3 执行前：删临时 vhost `zz-temp-v2-preverify.conf`。
- 可选项：启用 `noarchive` 头、drop `wp_gf_*` 6 张遗留表、`blogname` 改 SINO FRESH。

## 产物

- `docs/golive-p2-report-2026-09-28.md`（§3.8 修复执行与验收、§5 待确认表、§6 P3 预案）
- `docs/golive-smtp-rootcause-2026-09-28.md`（真因 + 执行结果）
