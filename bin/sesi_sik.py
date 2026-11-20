#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
"""TTS anlatımını hızlı Shorts temposuna sıkıştırır: uzun sessizlikleri kısaltır, gerekirse atempo uygular.

TTS 'speed' parametresi hızı pek değiştirmiyor (ölçüm 20 Kas: Darren 0,15 -> 43,2 sn,
0,55 -> 41,4 sn); asıl yavaşlık cümle arası duraklamalar (~9-16 sn / 118 kelime). Bu betik:
  1) -40 dBFS altındaki >= --min-sessiz sn boşlukları --azami sn'ye indirir (duraklama <= 0,5 sn),
  2) metin verilirse kelime/sn hedefine (--hedef-wps) atempo ile yaklaştırır (en çok 1,15x),
  3) 48 kHz mono wav yazar ve özet basar.

Kullanım: sesi_sik.py girdi.mp3 cikti.wav [--metin metin.txt] [--hedef-wps 3.5] [--azami 0.22]
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np

SR = 48000


def oku(p):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(p), "-f", "f32le", "-ac", "1",
                          "-ar", str(SR), "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("girdi")
    ap.add_argument("cikti")
    ap.add_argument("--metin", help="kelime sayısı için düz metin dosyası")
    ap.add_argument("--hedef-wps", type=float, default=3.5)
    ap.add_argument("--azami", type=float, default=0.22, help="kısaltılmış duraklamanın süresi (sn)")
    ap.add_argument("--min-sessiz", type=float, default=0.25)
    ap.add_argument("--esik-db", type=float, default=-40)
    ap.add_argument("--azami-tempo", type=float, default=1.15)
    a = ap.parse_args()

    x = oku(a.girdi)
    hop = int(0.01 * SR)
    n = len(x) // hop
    rms = np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    sessiz = 20 * np.log10(rms) < a.esik_db
    parcalar, i, kisalan = [], 0, 0.0
    bas = 0
    while i < n:
        if sessiz[i]:
            j = i
            while j < n and sessiz[j]:
                j += 1
            uzun = (j - i) * 0.01
            # baştaki ve sondaki sessizliği tümden at (yalnız 0,05 sn bırak)
            hedef = 0.05 if (i == 0 or j == n) else a.azami
            if uzun >= a.min_sessiz or i == 0 or j == n:
                hedef = min(hedef, uzun)
                yarim = int(hedef / 2 * SR)
                s0, s1 = i * hop, j * hop
                parcalar.append(x[bas: s0 + yarim])
                bas = s1 - yarim
                kisalan += uzun - hedef
            i = j
        else:
            i += 1
    parcalar.append(x[bas:])
    y = np.concatenate([p for p in parcalar if len(p)])
    sure = len(y) / SR
    tempo = 1.0
    kelime = None
    if a.metin:
        kelime = len(re.findall(r"[A-Za-z0-9']+", Path(a.metin).read_text()))
        wps = kelime / sure
        if wps < a.hedef_wps:
            tempo = min(a.hedef_wps / wps, a.azami_tempo)
    af = f"atempo={tempo:.4f}" if tempo > 1.001 else "anull"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-af", af, "-c:a", "pcm_s24le", a.cikti], input=y.astype(np.float32).tobytes(), check=True)
    son = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                a.cikti], capture_output=True, text=True).stdout)
    ozet = {"girdi_sn": round(len(x) / SR, 2), "kisaltilan_sn": round(kisalan, 2), "tempo": round(tempo, 3),
            "cikti_sn": round(son, 2), "kelime": kelime, "wps": round(kelime / son, 2) if kelime else None}
    print(json.dumps(ozet, ensure_ascii=False))


if __name__ == "__main__":
    main()
