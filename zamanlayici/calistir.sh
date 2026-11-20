#!/usr/bin/env bash
# Zamanlanmış koşu (TASLAK, varsayılan KAPALI). İki aşama:
#  1) tara + dogrula (kredi harcamaz, yükleme yapmaz)
#  2) İSTEĞE BAĞLI üretim: ajan, istemler/oto.md içeriği SON argüman olarak eklenerek çalışır.
#     GTA6_AJAN=claude|codex|antigravity hazır komutu seçer; GTA6_OTO_KOMUT verilirse o kullanılır.
#     İkisi de yoksa bu aşama atlanır.
# Asla yüklemez; onay vermez (onay yalnız insan: motor.sh onayla <id>).
set -uo pipefail
M="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$M/kuyruk"
LOG="$M/kuyruk/oto-$(date +%Y%m%d-%H%M).log"
exec >>"$LOG" 2>&1
echo "== $(date -Is) tara"
"$M/bin/tara.py" --n 8 --gun 4 --detay 60 || echo "tara hata $?"
"$M/bin/dogrula.py" || echo "dogrula hata $?"
[ "${1:-}" = "--yalniz-tara" ] && exit 0
# Hazır ajan komutları (istem sona eklenir). Ağ gerekir: topla yt-dlp ile indirir.
case "${GTA6_AJAN:-}" in
  claude)      HAZIR='claude --allowedTools Bash,Read,Write,Edit,Glob,Grep,WebSearch,WebFetch -p' ;;
  codex)       HAZIR='codex exec --skip-git-repo-check -s workspace-write -c sandbox_workspace_write.network_access=true' ;;
  antigravity) HAZIR='agy --mode auto --dangerously-skip-permissions --print-timeout 0 --print' ;;
  "")          HAZIR='' ;;
  *)           echo "GTA6_AJAN bilinmiyor: $GTA6_AJAN (claude|codex|antigravity)"; exit 2 ;;
esac
GTA6_OTO_KOMUT="${GTA6_OTO_KOMUT:-$HAZIR}"
if [ -z "$GTA6_OTO_KOMUT" ]; then echo "GTA6_AJAN / GTA6_OTO_KOMUT yok: üretim aşaması atlandı"; exit 0; fi
echo "ajan komutu: $GTA6_OTO_KOMUT"
echo "== $(date -Is) üretim"
cd "$M"
# shellcheck disable=SC2086
flock -n "$M/kuyruk/.uretim-kilit" $GTA6_OTO_KOMUT "$(cat "$M/istemler/oto.md")" < /dev/null || echo "komut hata $?"
echo "== $(date -Is) bitti"
