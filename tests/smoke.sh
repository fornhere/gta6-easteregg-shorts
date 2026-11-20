#!/usr/bin/env bash
# Offline smoke test: syntax, skill files for every agent, skill installer, scheduler agent presets.
# Needs no network, GPU, agent CLI or API key. Run: tests/smoke.sh
set -euo pipefail
M="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
gec() { printf 'ok   %s\n' "$1"; }
dus() { printf 'FAIL %s\n' "$1"; exit 1; }

for f in "$M"/*.sh "$M"/zamanlayici/*.sh "$M"/tests/*.sh; do bash -n "$f" || dus "bash -n $f"; done; gec "shell syntax"
python3 - "$M" <<'PY' || dus "python syntax"
import sys, pathlib, ast
for p in list(pathlib.Path(sys.argv[1]).glob("bin/*.py")) + [pathlib.Path(sys.argv[1]) / "montaj/kur.py"]:
    ast.parse(p.read_text(encoding="utf-8"), str(p))
PY
gec "python syntax"
python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$M/ayar.json" || dus "ayar.json"; gec "ayar.json"

S="$M/.agents/skills/gta6-easteregg-shorts/SKILL.md"
head -1 "$S" | grep -qx -- '---' && grep -q '^name: gta6-easteregg-shorts$' "$S" && grep -q '^description: ' "$S" || dus "skill frontmatter"
grep -q '^<!-- MOTOR_KOKU -->' "$S" || dus "skill root marker"
[ "$(readlink "$M/.claude/skills/gta6-easteregg-shorts")" = ../../.agents/skills/gta6-easteregg-shorts ] || dus "claude skill link"
[ -f "$M/.claude/skills/gta6-easteregg-shorts/SKILL.md" ] || dus "claude skill link target"
grep -qx '@AGENTS.md' "$M/CLAUDE.md" || dus "CLAUDE.md -> AGENTS.md"
grep -q 'Yükleme yok' "$M/AGENTS.md" || dus "AGENTS.md upload rule"
gec "skill visible to Claude Code (.claude/skills), Codex and Antigravity (.agents/skills, AGENTS.md)"

"$M/motor.sh" | grep -q 'motor.sh tara' || dus "motor.sh usage"; gec "motor.sh usage"

H="$T/home"; mkdir -p "$H"
HOME="$H" CODEX_HOME= CLAUDE_CONFIG_DIR= "$M/ajan-kur.sh" all >/dev/null
for d in .claude/skills .codex/skills .gemini/config/skills; do
  f="$H/$d/gta6-easteregg-shorts/SKILL.md"; [ -f "$f" ] || dus "install $d"
  grep -q "Motor kökü: \`$M\`" "$f" || dus "absolute root in $d"
done
mkdir -p "$H/.codex/skills/x"; echo mine > "$H/.codex/skills/x/SKILL.md"
HOME="$H" "$M/ajan-kur.sh" all --remove >/dev/null
[ -z "$(find "$H" -path '*gta6-easteregg-shorts*' -name SKILL.md)" ] || dus "remove"
[ -f "$H/.codex/skills/x/SKILL.md" ] || dus "foreign skill kept"
mkdir -p "$H/.codex/skills/gta6-easteregg-shorts"; echo mine > "$H/.codex/skills/gta6-easteregg-shorts/SKILL.md"
HOME="$H" "$M/ajan-kur.sh" codex >/dev/null 2>&1; grep -qx mine "$H/.codex/skills/gta6-easteregg-shorts/SKILL.md" || dus "no overwrite of foreign skill"
gec "ajan-kur.sh install / remove / no overwrite"

# scheduler presets: fake agents + fake scan, check the prompt arrives as the single last argument
R="$T/repo"; cp -a "$M" "$R"; rm -f "$R"/kuyruk/oto-*.log
printf '#!/bin/sh\necho stub\n' > "$R/bin/tara.py"; cp "$R/bin/tara.py" "$R/bin/dogrula.py"
mkdir -p "$T/bin"
for a in claude codex agy; do
  printf '#!/bin/sh\nfor x; do son="$x"; done\nprintf "%%s|%%s\\n" "%s" "$(printf "%%s" "$son" | head -1)"\n' "$a" > "$T/bin/$a"; chmod +x "$T/bin/$a"
done
for a in claude:claude codex:codex antigravity:agy; do
  rm -f "$R"/kuyruk/oto-*.log
  PATH="$T/bin:$PATH" GTA6_AJAN="${a%%:*}" "$R/motor.sh" oto
  grep -q "^${a##*:}|İŞÇİ KOŞUSU" "$R"/kuyruk/oto-*.log || dus "preset ${a%%:*}"
done
rm -f "$R"/kuyruk/oto-*.log; PATH="$T/bin:$PATH" GTA6_AJAN= "$R/motor.sh" oto; grep -q 'atlandı' "$R"/kuyruk/oto-*.log || dus "no agent -> skip"
if PATH="$T/bin:$PATH" GTA6_AJAN=bogus "$R/motor.sh" oto; then dus "unknown agent should fail"; fi
gec "scheduler presets: claude, codex, antigravity"
echo "all smoke checks passed"
