#!/usr/bin/env bash
# GTA 6 easter egg Shorts motoru — tek giriş noktası. Ayrıntı: README.md
set -euo pipefail
M="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
B="$M/bin"
# Transkript betiği (kelime zamanları): GTA6_TRANSKRIPT ortam değişkeni ya da ayar.json > transkript.betik.
# Arayüz: python <betik> <ses|video> --out <dizin> --dil <kod>  ->  <dizin>/<ad>.json (kelime zamanlı), .srt, .txt
WHISPER="${GTA6_TRANSKRIPT:-$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("transkript",{}).get("betik",""))' "$M/ayar.json" 2>/dev/null || true)}"
[ -z "$WHISPER" ] || case "$WHISPER" in /*) ;; *) WHISPER="$M/$WHISPER" ;; esac
komut="${1:-yardim}"; shift || true

[ -n "$WHISPER" ] || WHISPER="$B/transkript.py"   # paketle gelen varsayılan (faster-whisper)

transkript() {  # <ses/video> <çıkış dizini> <dil>
  [ -f "$WHISPER" ] || { echo "Transkript betiği yok: $WHISPER (GTA6_TRANSKRIPT ya da ayar.json > transkript.betik)" >&2; exit 1; }
  local ek=()
  if command -v nvidia-smi >/dev/null 2>&1 && [ "$(uname -s)" = Linux ]; then
    ek=(--with 'nvidia-cublas-cu12>=12.8' --with 'nvidia-cudnn-cu12>=9')   # GPU varsa CUDA kütüphaneleri
  fi
  uv run --with faster-whisper --with numpy ${ek[@]+"${ek[@]}"} python "$WHISPER" "$1" --out "$2" --dil "$3"
}

zaman() {  # <iş> : anlatım.wav -> zaman/anlatim.json (kelime zamanları, yerel whisper)
  local J="$M/isler/$1"
  mkdir -p "$J/zaman"
  transkript "$J/ses/anlatim.wav" "$J/zaman" en
}

case "$komut" in
  tara)      "$B/tara.py" "$@" ;;                                  # yeni keşifler -> kuyruk/TARAMA-*.md
  dogrula)   "$B/dogrula.py" "$@" ;;                               # 2 bağımsız kaynak kuralı -> kuyruk/ONAY.md
  onayla)    "$B/dogrula.py" --onayla "$1" ;;                      # İNSAN KAPISI 1
  topla)     "$B/topla.py" "$1" --aday "${2:-$1}" ;;               # <iş adı> [aday_id]: indir, künye, döküm, kareler
  sik)       "$B/sesi_sik.py" "$M/isler/$1/ses/anlatim/ham.mp3" "$M/isler/$1/ses/anlatim.wav" \
               --metin "$M/isler/$1/metin.txt" --hedef-wps "${2:-3.5}" ;;   # TTS -> hızlı tempo
  zaman)     zaman "$1" ;;
  transkript) transkript "$1" "$2" "${3:-en}" ;;                    # <ses|video> <çıkış dizini> [dil]
  kare)      cd "$M/isler/$1" && "$M/montaj/kur.py" cekimler.json --kare "$2" ;;   # kadraj denemesi PNG
  kur)       cd "$M/isler/$1" && "$M/montaj/kur.py" cekimler.json
             for k in "$M/isler/$1"/kanca/*/; do [ -f "$k/cekimler.json" ] && (cd "$k" && "$M/montaj/kur.py" cekimler.json); done; true ;;
  kontrol)   set +e; "$B/kontrol.py" "$M/isler/$1"; st=$?
             for k in "$M/isler/$1"/kanca/*/; do [ -f "$k/cekimler.json" ] && "$B/kontrol.py" "$k" >/dev/null; done
             exit $st ;;   # ana videoda düşen madde varsa 1 döner; bitir paketi üretmez
  izin)      "$B/izin.py" mesaj "$M/isler/$1" ;;                    # izin isteme metinleri (GÖNDERMEZ)
  paket)     "$B/paket.py" "$M/isler/$1" ;;                        # -> inceleme/<tarih>-<iş>/ (YÜKLEMEZ)
  bitir)     "$0" kur "$1" && "$0" kontrol "$1" && "$0" paket "$1" ;;   # kur + kontrol + paket tek seferde
  sunucu)    # Sunucu kipi tek komut: isler/<iş>/sunucu/sunucu.mp4 (Shorts Studio çıktısı) -> kelime zamanları -> kur + kontrol (+ paket)
             J="$M/isler/$1"; dil="${2:-en}"
             [ -f "$J/sunucu/sunucu.mp4" ] || { echo "yok: $J/sunucu/sunucu.mp4"; exit 1; }
             mkdir -p "$J/zaman"
             transkript "$J/sunucu/sunucu.mp4" "$J/zaman" "$dil" >/dev/null
             for e in json srt txt; do   # whisper bağın hedef adını kullanabilir: en yeni çıktıyı al
               f=$(ls -t "$J/zaman"/*."$e" 2>/dev/null | grep -v "/anlatim\.$e$" | head -1)
               [ -n "$f" ] && mv -f "$f" "$J/zaman/anlatim.$e"; done
             "$0" kur "$1"
             if [ -f "$J/paket.json" ]; then "$0" kontrol "$1" && "$0" paket "$1"; else "$0" kontrol "$1"; fi ;;
  oto)       exec "$M/zamanlayici/calistir.sh" "$@" ;;             # tara+dogrula; GTA6_AJAN/GTA6_OTO_KOMUT varsa ajanla üretim (taslak)
  durum)     echo "== onay kuyruğu"; sed -n '1,40p' "$M/kuyruk/ONAY.md" 2>/dev/null || echo "(yok)"
             echo "== inceleme"; ls -1 "$M/inceleme" 2>/dev/null ;;
  *) sed -n '/## Komutlar/,/## İnsan kapıları/p' "$M/docs/REFERANS.md" 2>/dev/null || echo "kullanım: motor.sh tara|dogrula|onayla|topla|sik|zaman|kare|kur|kontrol|izin|paket|bitir|sunucu|oto|durum" ;;
esac
