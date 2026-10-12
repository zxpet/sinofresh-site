#!/usr/bin/env bash
# H24b Q4 —— 上线「停用 wp-mail-logging」的受控验收流程
#
#   1) 上传条件式邮件隔离夹具 + 验收脚本
#   2) 安装夹具（php -l 先过）
#   3) 跑前后对照验收（停用前双写 → 停用 → 停用后只记一处）
#   4) **无条件删除夹具**（trap EXIT，正常/异常/中断都会执行）
#
# 用法：bash tools/h24b_q4_deploy.sh
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

SERVER="${SF_SERVER:-root@65.49.215.152}"
REMOTE_TOOLS=/root/h24-tools
FIX_NAME=zz-sf-zz-test-nomail.php
STAGE="$REMOTE_TOOLS/stage-$FIX_NAME"

scp -q "tools/fixtures/$FIX_NAME" "$SERVER:$STAGE" || { echo "上传夹具失败"; exit 1; }
scp -q tools/h24b_q4_mail_logging.py "$SERVER:$REMOTE_TOOLS/h24b_q4_mail_logging.py" || {
    echo "上传验收脚本失败"; exit 1; }

ssh "$SERVER" 'bash -s' <<SH
set -uo pipefail
FIX=/var/www/zxpet-v2/wp-content/mu-plugins/$FIX_NAME

remove_fix() {
    rm -f "\$FIX"
    if [ -f "\$FIX" ]; then
        echo "FIXTURE_REMOVED=NO   *** 夹具仍存在，请人工删除：\$FIX ***"
    else
        echo "FIXTURE_REMOVED=YES"
    fi
}
trap remove_fix EXIT

php -l $STAGE || exit 1
install -o apache -g apache -m 644 $STAGE "\$FIX"
echo "FIXTURE_INSTALLED=\$FIX md5=\$(md5sum "\$FIX" | cut -d' ' -f1)"

cd /var/www/zxpet-v2 || exit 1
SF_H24B_SITE=prod python3 $REMOTE_TOOLS/h24b_q4_mail_logging.py
RC=\$?
echo "Q4_RC=\$RC"
exit \$RC
SH
