#!/usr/bin/env bash
# Skill'i ajanların global skill klasörüne kurar (isteğe bağlı).
# Depoyu Claude Code / Codex / Antigravity ile açınca skill zaten bulunur (.agents/skills, .claude/skills);
# bu betik yalnız "her dizinden çağırabileyim" diyenler için. Kopya kurar, motor kökünü mutlak yol yapar.
# Kullanım / usage: ./ajan-kur.sh [claude|codex|antigravity|hepsi|all] [--kaldir|--remove]
set -euo pipefail
M="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AD=gta6-easteregg-shorts
KAYNAK="$M/.agents/skills/$AD/SKILL.md"
hedef() {
  case "$1" in
    claude)      echo "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/$AD" ;;
    codex)       echo "${CODEX_HOME:-$HOME/.codex}/skills/$AD" ;;
    antigravity) echo "$HOME/.gemini/config/skills/$AD" ;;
    *) echo "bilinmeyen ajan: $1 (claude|codex|antigravity|hepsi|all)" >&2; exit 2 ;;
  esac
}
secim="${1:-hepsi}"; kaldir="${2:-}"
[ "$secim" = all ] && secim=hepsi; [ "$kaldir" = --remove ] && kaldir=--kaldir
[ "$secim" = hepsi ] && ajanlar="claude codex antigravity" || ajanlar="$secim"
for a in $ajanlar; do
  d="$(hedef "$a")"
  if [ "$kaldir" = --kaldir ]; then
    [ -f "$d/SKILL.md" ] && grep -q 'kurulum: ajan-kur.sh' "$d/SKILL.md" && rm -r "$d" && echo "kaldırıldı: $d" || echo "atlandı (bizim kurulum değil ya da yok): $d"
    continue
  fi
  if [ -e "$d" ] && ! grep -q 'kurulum: ajan-kur.sh' "$d/SKILL.md" 2>/dev/null; then
    echo "atlandı: $d zaten var ve bu betikle kurulmamış; elle bak" >&2; continue
  fi
  mkdir -p "$d"
  python3 - "$KAYNAK" "$d/SKILL.md" "$M" <<'PY'
import sys, pathlib
src, dst, kok = sys.argv[1:]
t = pathlib.Path(src).read_text(encoding="utf-8")
satir = next(l for l in t.splitlines() if l.startswith("<!-- MOTOR_KOKU -->"))
t = t.replace(satir, f"<!-- MOTOR_KOKU --><!-- kurulum: ajan-kur.sh -->Motor kökü: `{kok}` (`motor.sh`, `AGENTS.md`, `README.md`). Komutları orada çalıştır.")
pathlib.Path(dst).write_text(t, encoding="utf-8")
PY
  echo "kuruldu: $a -> $d"
done
