#!/usr/bin/env bash
# One-command setup: checks tools, warms the Python dependencies (via uv), optionally installs the agent skill.
# Usage: ./install.sh [--agent claude|codex|antigravity|all] [--whisper]
#   --agent    also copy the skill to that agent's global skill folder (repo-local skill works without this)
#   --whisper  also download faster-whisper now (otherwise it downloads on first transcription)
# Never uses sudo and never installs system packages; it tells you what is missing.
set -uo pipefail
M="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$M"
ajan=""; whisper=0
while [ $# -gt 0 ]; do
  case "$1" in
    --agent|--ajan) ajan="${2:-}"; shift 2 ;;
    --whisper) whisper=1; shift ;;
    -h|--help) sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
[ "$ajan" = all ] && ajan=hepsi

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
eksik(){ printf '  \033[31m✗\033[0m %s — %s\n' "$1" "$2"; eksik_var=1; }
eksik_var=0
os="$(uname -s)"
ipucu() {  # <arch> <debian> <mac>
  case "$os" in
    Darwin) echo "brew install $3" ;;
    *) if command -v pacman >/dev/null 2>&1; then echo "sudo pacman -S $1";
       elif command -v apt-get >/dev/null 2>&1; then echo "sudo apt install $2";
       elif command -v dnf >/dev/null 2>&1; then echo "sudo dnf install $2";
       else echo "install $1 with your package manager"; fi ;;
  esac
}

echo "GTA 6 easter egg Shorts engine — setup"
echo "1) Tools"
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
  ok "python3 $(python3 -c 'import platform; print(platform.python_version())')"
else eksik "python3 >= 3.10" "$(ipucu python python3 python)"; fi
for t in ffmpeg ffprobe; do
  command -v "$t" >/dev/null 2>&1 && ok "$t" || eksik "$t" "$(ipucu ffmpeg ffmpeg ffmpeg)"; done
command -v yt-dlp >/dev/null 2>&1 && ok "yt-dlp $(yt-dlp --version 2>/dev/null)" || eksik "yt-dlp" "$(ipucu yt-dlp yt-dlp yt-dlp)  (or: uv tool install yt-dlp)"
command -v uv >/dev/null 2>&1 && ok "uv $(uv --version 2>/dev/null | cut -d' ' -f2)" || eksik "uv" "see https://docs.astral.sh/uv/getting-started/installation/"
if command -v flock >/dev/null 2>&1; then ok "flock (only for the optional scheduler)"; else echo "  - flock not found (only needed by the optional scheduler)"; fi
if command -v nvidia-smi >/dev/null 2>&1; then ok "NVIDIA GPU (transcription runs on GPU)"; else echo "  - no NVIDIA GPU: transcription runs on CPU (slower, works)"; fi

if [ "$eksik_var" = 1 ]; then
  echo; echo "Install the missing tools above, then run ./install.sh again."; exit 1
fi

echo "2) Python dependencies (uv caches them; first run downloads ~100 MB)"
chmod +x motor.sh ajan-kur.sh bin/*.py montaj/kur.py zamanlayici/calistir.sh 2>/dev/null
if uv run --script montaj/kur.py --help >/dev/null 2>&1; then ok "render (numpy, opencv, pillow)"; else eksik "render deps" "run: uv run --script montaj/kur.py --help"; fi
if uv run --script bin/sesi_sik.py --help >/dev/null 2>&1; then ok "audio tools"; else eksik "audio deps" "run: uv run --script bin/sesi_sik.py --help"; fi
if [ "$whisper" = 1 ]; then
  if uv run --with faster-whisper --with numpy python -c 'import faster_whisper' >/dev/null 2>&1; then ok "faster-whisper"; else eksik "faster-whisper" "check your network / uv"; fi
else echo "  - faster-whisper: downloads on first transcription (or run ./install.sh --whisper)"; fi

echo "3) Agents"
for a in claude codex agy; do command -v "$a" >/dev/null 2>&1 && ok "$a found"; done
echo "  Opening this folder in Claude Code, Codex or Antigravity is enough: the skill is in .agents/skills/."
if [ -n "$ajan" ]; then ./ajan-kur.sh "$ajan" || eksik_var=1; fi

echo
if [ "$eksik_var" = 1 ]; then echo "Setup finished with problems (see ✗ above)."; exit 1; fi
cat <<'EOF'
Ready. Next:
  ./motor.sh tara        # find new easter eggs (network)
  ./motor.sh dogrula     # 2-source rule -> kuyruk/ONAY.md
  or open this folder in your agent and say: "run the GTA 6 easter egg Shorts engine"
Nothing is ever uploaded; you review inceleme/ and upload by hand.
EOF
