#!/usr/bin/env bash
# =============================================================
# SINO FRESH WordPress 迁移部署脚本（云端 AlmaLinux 9 + LEMP）
# 用法：把 _migration/ 整个目录 scp 到服务器后执行：
#   sudo bash deploy.sh
# 执行前只需改 DOMAIN；其余自动完成。
# =============================================================
set -euo pipefail

# ---------- 可配置项 ----------
DOMAIN="dev.zxpet.com"            # ← 改成你实际要用的域名
WP_VERSION="7.1.1"
PHP_VERSION="8.2"                 # 服务器上 php-fpm 主版本
# ------------------------------

SITE_DIR="/var/www/${DOMAIN}"
DB_NAME="sinofresh"
DB_USER="sinofresh"
DB_PASS="$(openssl rand -hex 12)"
WP_USER_OS="$(id -un 2>/dev/null || echo nginx)"   # 一般 nginx/php-fpm 跑在 nginx 用户
PKG_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> [1/8] 检查依赖"
for bin in nginx mysql php; do command -v "$bin" >/dev/null || { echo "缺少 $bin，请先装好 LEMP"; exit 1; }; done
if ! command -v wp >/dev/null; then
  curl -sSLo /usr/local/bin/wp https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar
  chmod +x /usr/local/bin/wp
fi

echo "==> [2/8] 建库建用户"
mysql -uroot <<SQL
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_520_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

echo "==> [3/8] 下载 WordPress ${WP_VERSION} 内核"
mkdir -p "${SITE_DIR}/public"
cd "${SITE_DIR}/public"
wp core download --version="${WP_VERSION}" --locale=en_US --allow-root --force

echo "==> [4/8] 解包 wp-content（插件/主题/uploads/语言）"
# 守门：包里若携带 macOS 元数据/陈旧 debug.log，先拒绝解包。
# 实证：2026-09-20 首次部署的包内携带 debug.log ×1 + .DS_Store ×2，
# debug.log 曾被公网扫描器以 200 抓到（docs/b2d-step5-logaudit.txt）。
# 重打包请用 tools/sf_pack_migration.sh（打包+自证一体）。
if tar -tzf "${PKG_DIR}/wp-content-full.tar.gz" \
     | grep -qE '(^|/)\._|\.DS_Store|(^|/)wp-content/debug\.log$'; then
  echo "!! 迁移包含 macOS 元数据或陈旧 debug.log，禁止解包" >&2
  echo "   重新打包：tools/sf_pack_migration.sh --src <本地 wp-content> --out _migration/" >&2
  exit 1
fi

tar -xzf "${PKG_DIR}/wp-content-full.tar.gz" -C "${SITE_DIR}/public"

# 防御清扫（双保险）：万一守门被绕过（手工 tar/别的包），解包后照样扫掉。
# macOS bash 3.2 会把 $VAR（ 后的多字节字节吃进变量名，变量一律用 ${VAR}。
N_JUNK=$(find "${SITE_DIR}/public" -type f \( -name '._*' -o -name '.DS_Store' \) | wc -l | tr -d ' ')
if [ "${N_JUNK}" -gt 0 ]; then
  find "${SITE_DIR}/public" -type f \( -name '._*' -o -name '.DS_Store' \) -delete
  echo "    （防御清扫：已删除 ${N_JUNK} 个 macOS 元数据文件）"
fi
rm -f "${SITE_DIR}/public/wp-content/debug.log"

echo "==> [5/8] 生成 wp-config.php"
wp config create --dbname="${DB_NAME}" --dbuser="${DB_USER}" --dbpass="${DB_PASS}" \
  --dbhost="localhost:/var/lib/mysql/mysql.sock" --dbprefix="wp_" --allow-root --force
wp config set WP_REDIS_DISABLE true --raw --allow-root 2>/dev/null || true
wp config set FS_METHOD direct --allow-root

echo "==> [6/8] 导入数据库并替换域名"
mysql -uroot "${DB_NAME}" < <(gunzip -c "${PKG_DIR}/sinofresh-db.sql.gz")
wp search-replace 'https://sinofresh.local' "https://${DOMAIN}" --all-tables --precise --allow-root
wp search-replace 'http://sinofresh.local'  "https://${DOMAIN}" --all-tables --precise --allow-root
wp search-replace 'sinofresh.local'         "${DOMAIN}"       --all-tables --precise --allow-root
# 修正 home/siteurl（防止 search-replace 漏网）
wp option update home "https://${DOMAIN}" --allow-root
wp option update siteurl "https://${DOMAIN}" --allow-root

echo "==> [7/8] 权限与缓存"
chown -R "${WP_USER_OS}":"${WP_USER_OS}" "${SITE_DIR}"
find "${SITE_DIR}" -type d -exec chmod 755 {} \;
find "${SITE_DIR}" -type f -exec chmod 644 {} \;
wp cache flush --allow-root 2>/dev/null || true

echo "==> [8/8] 校验"
wp core verify-checksums --allow-root
wp db check --allow-root
echo ""
echo "=============================================="
echo " 部署完成：${DOMAIN}"
echo " 数据库用户/密码（记下来，用于 wp-config）:"
echo "   DB_USER=${DB_USER}"
echo "   DB_PASS=${DB_PASS}"
echo " nginx server 块模板: ${PKG_DIR}/nginx-${DOMAIN}.conf"
echo "   cp 到 /etc/nginx/conf.d/ 后改证书路径并 systemctl reload nginx"
echo "=============================================="
