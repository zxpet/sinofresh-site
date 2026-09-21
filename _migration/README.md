# SINO FRESH 本地 → 云端迁移包

生成时间：2026-09-20 ｜ 来源：LocalWP（sinofresh.local）

## 包内容
| 文件 | 大小 | 说明 |
|---|---|---|
| sinofresh-db.sql.gz | 930K | 完整数据库 dump（utf8mb4，含内联 SVG 的 post_content） |
| wp-content-full.tar.gz | 49M | 完整 wp-content：插件(GF/TranslatePress等)+主题+uploads+语言 |
| deploy.sh | - | 服务器端一键部署脚本（AlmaLinux 9 + LEMP） |
| nginx-dev.zxpet.com.conf | - | nginx server 块模板 |

环境参数：WP 7.1.1 / PHP 8.2 / 表前缀 wp_ / 数据库字符集 utf8mb4_unicode_520_ci

## 执行步骤
1. **上传**（在 Mac 上执行，把 IP 换成服务器实际地址）：
   ```bash
   scp -r _migration root@<服务器IP>:/root/
   ```
2. **部署**（在服务器上）：
   ```bash
   sudo bash /root/_migration/deploy.sh
   ```
   脚本自动完成：建库建用户 → 下载 WP 内核 → 解包 wp-content → 导库 → **三段式域名替换**（sinofresh.local → dev.zxpet.com）→ 权限 → 完整性校验
3. **nginx**：复制 conf 模板到 `/etc/nginx/conf.d/`，改证书路径，`nginx -t && systemctl reload nginx`
4. **Cloudflare**：加 `dev` A 记录（开橙云），SSL 模式 Full(strict) + Origin 证书
5. **回归核验**：首页/剂型页/配置器/GF 表单/TranslatePress `/zh/` 逐项点验

## 注意事项
- deploy.sh 里 `DOMAIN` 默认 `dev.zxpet.com`，用别的域名记得改
- **重打包必须走 `tools/sf_pack_migration.sh`**（根因修复 2026-09-21）：
  首次部署的 `wp-content-full.tar.gz` 是裸 tar 打的，实测携带
  `debug.log` ×1 + `.DS_Store` ×2（`.DS_Store`/`debug.log` 已随批次 2D 收尾清掉，
  旧包留档但**不得再用**，部署前可 `tools/sf_pack_migration.sh --verify <tar>` 复检）。
  该脚本 = `COPYFILE_DISABLE=1` + 双层 exclude + 打包后自证（垃圾为 0 且真文件不少），
  deploy.sh 解包前还有一道包内容守门，双保险。
  另：从 Mac 直传目录（scp -r）会把 AppleDouble `._*` 一并带上去（dev 站曾积到 5645 个）——
  直传目录一律走 rsync 加 `--exclude='._*' --exclude='.DS_Store'`，或打包后只传 tar。
- GF 表单测试注意 ≥2.9.15 拒收 `@example.com` 邮箱
- TranslatePress 首次在云端渲染后需让它重新抓取译文
- 剂型页规范路径 `/products/{slug}/`，核验爬取要 `-L` 跟随
