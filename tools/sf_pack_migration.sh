#!/usr/bin/env bash
# =============================================================
# sf_pack_migration.sh — 迁移包（wp-content tar）的合规打包/复检脚本
#
# 根因（2026-09-21，批次 2D §5 收尾实证）：
#   初次上云的 wp-content-full.tar.gz 是在 Mac 上裸 tar 打的，无排除，
#   实测包内携带 debug.log ×1 + .DS_Store ×2（解包后成为 dev docroot 的
#   可达路径：debug.log 曾被扫描器以 200 抓到，见 docs/b2d-step5-logaudit.txt）。
#   另一条 macOS 目录直传路径（scp -r）又带入了 5645 个 AppleDouble ._*。
#
# 打包模式：COPYFILE_DISABLE=1 + 双层 --exclude（文件名 + 整路径），
#   打包后自证两个方向：
#   ① 垃圾不进来：包内 ._* / .DS_Store / debug.log 计数为 0；
#   ② 真文件不丢：包内条目数 == 磁盘真文件数 − 磁盘垃圾数，
#      防止 exclude 写宽了静默漏掉真文件。
#
# 复检模式（--verify <tar>）：对任意已有迁移包跑「垃圾计数」自证，
#   供部署前最后把关（deploy.sh 解包守门之外的人工/脚本复核）。
#
# 用法：
#   tools/sf_pack_migration.sh --src <本地 wp-content 目录> --out <输出目录>
#       [--name <tar 文件名，默认 wp-content-full.tar.gz>]
#       默认 --src 取 LocalWP 站点；--out 默认 _migration/
#   tools/sf_pack_migration.sh --verify <tar 文件>
#   退出码 0=过，1=有垃圾/计数不符，2=参数错。
#
# 注意：本脚本只打包/复检，不传输、不部署。传输仍按 _migration/README.md
# 的 scp 步骤；deploy.sh 在解包前还有一道包内容守门（双保险）。
# =============================================================
set -euo pipefail

SRC_DEFAULT="$HOME/Local Sites/sinofresh/app/public/wp-content"
OUT_DEFAULT="$(cd "$(dirname "$0")/.." && pwd)/_migration"
NAME="wp-content-full.tar.gz"
MODE="pack"
SRC=""
OUT=""
VERIFY_TAR=""

while [ $# -gt 0 ]; do
  case "$1" in
    --src)    SRC="$2"; shift 2 ;;
    --out)    OUT="$2"; shift 2 ;;
    --name)   NAME="$2"; shift 2 ;;
    --verify) MODE="verify"; VERIFY_TAR="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ---------------------------------------------------------------
# 复检模式：对已有 tar 跑垃圾计数（不比对磁盘，源树可能已不在）
# ---------------------------------------------------------------
if [ "$MODE" = "verify" ]; then
  [ -f "$VERIFY_TAR" ] || { echo "!! tar 不存在: $VERIFY_TAR" >&2; exit 2; }
  LIST=$(tar -tzf "$VERIFY_TAR")
  TAR_N=$(printf '%s\n' "$LIST" | wc -l | tr -d ' ')
  JUNK_IN=$(printf '%s\n' "$LIST" | grep -cE '(^|/)\._|\.DS_Store' || true)
  DBG_IN=$(printf '%s\n' "$LIST" | grep -cE '(^|/)debug\.log$' || true)
  echo "verify: $VERIFY_TAR"
  echo "  包内条目            : ${TAR_N}"
  echo "  包内 ._* / .DS_Store : ${JUNK_IN}（期望 0）"
  echo "  包内 debug.log      : ${DBG_IN}（期望 0）"
  FAIL=0
  [ "$JUNK_IN" -eq 0 ] || { echo "!! 包内携带 macOS 元数据 —— 禁止部署" >&2; FAIL=1; }
  [ "$DBG_IN" -eq 0 ]  || { echo "!! 包内携带 debug.log —— 禁止部署" >&2; FAIL=1; }
  [ "$FAIL" -eq 0 ] && { echo "PASS"; exit 0; } || exit 1
fi

# ---------------------------------------------------------------
# 打包模式
# ---------------------------------------------------------------
SRC="${SRC:-$SRC_DEFAULT}"
OUT="${OUT:-$OUT_DEFAULT}"

[ -d "$SRC" ] || { echo "!! src 不存在: $SRC" >&2; exit 2; }
mkdir -p "$OUT"
TAR_OUT="$OUT/$NAME"
TMP_TAR="$OUT/.tmp-$NAME"
rm -f "$TMP_TAR"
SRCBASE=$(basename "$SRC")

echo "==> 1) 磁盘侧计数：真文件 vs 垃圾"
ALL_FILES=$(find "$SRC" -type f | wc -l | tr -d ' ')
JUNK=$(find "$SRC" -type f \( -name '._*' -o -name '.DS_Store' \) | wc -l | tr -d ' ')
DBG=0
[ -f "$SRC/debug.log" ] && DBG=1
echo "    磁盘文件总数        : $ALL_FILES"
echo "    其中 ._* / .DS_Store : $JUNK"
echo "    其中 debug.log      : $DBG"
# bsdtar 默认把目录也写成包内条目（src/、src/sub/…），期望数要把目录算上；
# 空目录同样会被收进包。若源树含符号链接，两边计数口径会失配而 FAIL（fail-safe）。
ALL_DIRS=$(find "$SRC" -type d | wc -l | tr -d ' ')
EXPECT=$((ALL_FILES + ALL_DIRS - JUNK - DBG))

echo "==> 2) 打包（COPYFILE_DISABLE=1 + 双层 exclude）"
# bsdtar 的 exclude 匹配：裸 '._*' 匹配任意层级的文件名尾部，
# '*/._*' 显式覆盖带目录前缀的形态；两层叠加，不赌单一实现的行为。
COPYFILE_DISABLE=1 tar -czf "$TMP_TAR" \
  --exclude='._*'          --exclude='*/._*' \
  --exclude='.DS_Store'    --exclude='*/.DS_Store' \
  --exclude="$SRCBASE/debug.log" \
  -C "$(dirname "$SRC")" "$SRCBASE"
mv -f "$TMP_TAR" "$TAR_OUT"

echo "==> 3) 打包后自证"
LIST=$(tar -tzf "$TAR_OUT")
TAR_N=$(printf '%s\n' "$LIST" | wc -l | tr -d ' ')
JUNK_IN=$(printf '%s\n' "$LIST" | grep -cE '(^|/)\._|\.DS_Store' || true)
DBG_IN=$(printf '%s\n' "$LIST" | grep -cE "^$SRCBASE/debug\.log$" || true)
echo "    包内条目            : ${TAR_N}（期望 ${EXPECT}）"
echo "    包内 ._* / .DS_Store : ${JUNK_IN}（期望 0）"
echo "    包内 debug.log      : ${DBG_IN}（期望 0）"

FAIL=0
[ "$JUNK_IN" -eq 0 ] || { echo "!! 包内仍有 macOS 元数据" >&2; FAIL=1; }
[ "$DBG_IN" -eq 0 ] || { echo "!! 包内仍有 debug.log" >&2; FAIL=1; }
[ "$TAR_N" -eq "$EXPECT" ] || { echo "!! 条目数不符（多排或漏排）：包内 $TAR_N != 磁盘 $EXPECT" >&2; FAIL=1; }

if [ "$FAIL" -eq 0 ]; then
  SIZE=$(du -h "$TAR_OUT" | cut -f1 | tr -d ' ')
  echo ""
  echo "PASS：${TAR_OUT}（${SIZE}，${TAR_N} 个条目，垃圾 0，真文件不少）"
  exit 0
fi
exit 1
