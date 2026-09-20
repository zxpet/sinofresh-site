#!/bin/bash
# =============================================================================
# REVERT: dev.zxpet.com indexing / crawler lockdown
# Added 2026-09-20 14:18 UTC.  Undoes everything that batch changed.
#
# Usage:  bash REVERT.sh
#
# Removes:   Basic Auth on the dev vhost
#            /etc/httpd/.htpasswd-dev.zxpet.com
#            the mu-plugin robots gate
#            the SF_DEV_LOCKDOWN constant in wp-config.php
# Restores:  dev.zxpet.com.conf byte-for-byte from dev.zxpet.com.conf.orig
#            (that original already contained X-Robots-Tag + AllowOverride All,
#             so the dev host stays de-indexed by header after the revert)
# Leaves:    public/robots.txt  (pre-existing, Disallow: /)
#            public/.htaccess    (pre-existing AI-crawler 403 block)
#            Delete those two by hand if you want the dev host fully open.
#
# Production is NOT touched by this script: zxpet.com and www.zxpet.com are
# served by wordpress-zxpet.conf / zxpet.com.conf / zxpet.com-le-ssl.conf from
# DocumentRoot /var/www/html.
# =============================================================================
set -euo pipefail

D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
say() { printf '\n[%s] %s\n' "$1" "$2"; }

say 1/5 "restore dev.zxpet.com.conf from backup"
cp -a "$D/dev.zxpet.com.conf.orig" /etc/httpd/conf.d/dev.zxpet.com.conf

say 2/5 "remove the htpasswd file"
rm -f /etc/httpd/.htpasswd-dev.zxpet.com

say 3/5 "remove the mu-plugin"
rm -f /var/www/dev.zxpet.com/public/wp-content/mu-plugins/zz-sf-dev-lockdown.php

say 4/5 "remove the SF_DEV_LOCKDOWN constant from wp-config.php"
python3 - <<'PY'
import re
P = "/var/www/dev.zxpet.com/public/wp-config.php"
src = open(P, encoding="utf-8").read()
out = re.sub(r"\n*/\* DEV-ONLY indexing lockdown switch\..*?define\( 'SF_DEV_LOCKDOWN', true \);\n?",
             "\n", src, flags=re.S)
if out != src:
    open(P, "w", encoding="utf-8").write(out)
    print("    removed")
else:
    print("    already absent")
PY

say 5/5 "config test + reload"
httpd -t
systemctl reload httpd

echo
echo "Reverted. Verify with:"
echo "  curl -sI https://dev.zxpet.com/ | head -3"
echo "  curl -s  https://dev.zxpet.com/ | grep -o 'meta name=.robots[^>]*'"
echo
echo "Remember: purge the Cloudflare cache for dev.zxpet.com in the dashboard."
