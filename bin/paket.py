#!/usr/bin/env python3
"""İNCELEME PAKETİ adımı: yayına hazır ama YÜKLENMEMİŞ paket -> motor/inceleme/<tarih>-<ad>/.

İçerik: video (tam kalite), <ad>-paylas.mp4 (720p, < 30 MB), kanca klipleri (varsa), KONTROL.md, kontrol kareleri,
YAYIN.md (3 başlık önerisi, açıklama taslağı, sabit yorum önerisi, etiketler). Açıklamadaki künye bloğu
kaynaklar sözlüğünden otomatik yazılır; "Not affiliated with Rockstar Games" notu ve kaynak linkleri zorunludur
(eksikse betik durur). Metinler isler/<ad>/paket.json'dan gelir (Ajan adımı yazar).
Otomatik yükleme YOK: yükleme kullanıcı onayıyla, elle yapılır.

Kullanım: paket.py <iş klasörü> [--tarih 2026-11-20]
"""
import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]
NOT = "Not affiliated with Rockstar Games. Gameplay clips belong to their creators and are used in short excerpts with credit."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("is_klasoru")
    ap.add_argument("--tarih", default=dt.date.today().isoformat())
    a = ap.parse_args()
    J = Path(a.is_klasoru).resolve()
    T = json.loads((J / "cekimler.json").read_text())
    P = json.loads((J / "paket.json").read_text())
    ad = J.name
    hedef = MOTOR / "inceleme" / f"{a.tarih}-{ad}"
    hedef.mkdir(parents=True, exist_ok=True)
    video = J / T["ayar"]["cikti"]
    shutil.copy2(video, hedef / f"{ad}.mp4")
    paylas = hedef / f"{ad}-paylas.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(video), "-vf", "scale=720:1280",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "26", "-maxrate", "5M", "-bufsize", "10M",
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(paylas)], check=True)
    mb = paylas.stat().st_size / 1e6
    if mb >= 30:
        sys.exit(f"paylaşım kopyası {mb:.1f} MB (>= 30)")
    kanca_dir = hedef / "kancalar"
    for k in sorted((J / "kanca").glob("*/cikti/*.mp4")) if (J / "kanca").exists() else []:
        kanca_dir.mkdir(exist_ok=True)
        shutil.copy2(k, kanca_dir / k.name)
    for f in ("KONTROL.md", "metin.md"):
        if (J / f).exists():
            shutil.copy2(J / f, hedef / f)
    kk = hedef / "kontrol"
    kk.mkdir(exist_ok=True)
    for f in (J / "kontrol").glob("*.jpg"):
        shutil.copy2(f, kk / f.name)
    if (J / "kontrol" / "kare-0.2.png").exists():
        shutil.copy2(J / "kontrol" / "kare-0.2.png", kk / "kare-0.2.png")

    kunye = ["Clips:"]
    for h, s in T["kaynaklar"].items():
        kunye.append(f"- {s['kanal']} ({s['etiket']}): {s['url']}")
    aciklama = P["aciklama"].rstrip() + "\n\n" + "\n".join(kunye) + "\n\n" + NOT + "\n\n" + " ".join(P.get("hashtag", []))
    for s in T["kaynaklar"].values():
        if s["url"] not in aciklama:
            sys.exit(f"açıklamada kaynak linki eksik: {s['url']}")
    izin = {}
    ip = MOTOR / "izin" / "izinler.jsonl"
    if ip.exists():
        for x in ip.read_text().splitlines():
            if x.strip():
                r = json.loads(x)
                izin[r["url"]] = r
    izin_satir = "; ".join(
        f"{s['kanal']}: " + (("istenmedi") if s["url"] not in izin else
                             f"istendi {izin[s['url']]['istek_tarihi']}, cevap: {izin[s['url']].get('cevap') or 'yok'}")
        for s in T["kaynaklar"].values())
    md = [f"# YAYIN — {ad} (YÜKLENMEDİ; kullanıcı onayı bekler)", "",
          f"- **İzin durumu:** {izin_satir}  (şablon: `motor/izin/SABLON.md`, metin: `bin/izin.py mesaj <iş>`; "
          "motor mesaj göndermez)",
          f"- Video: `{ad}.mp4` · paylaşım kopyası: `{paylas.name}` ({mb:.1f} MB)",
          f"- Kanca klipleri: `kancalar/` ({', '.join(p.name for p in sorted(kanca_dir.glob('*.mp4'))) if kanca_dir.exists() else 'yok'})",
          "", "## Başlık önerileri", ""]
    md += [f"{i}. {b}" for i, b in enumerate(P["basliklar"], 1)]
    md += ["", "## Açıklama taslağı", "", "```", aciklama, "```", "", "## Sabit yorum önerisi", "", "```", P["sabit_yorum"], "```"]
    if P.get("notlar"):
        md += ["", "## Notlar", ""] + [f"- {n}" for n in P["notlar"]]
    (hedef / "YAYIN.md").write_text("\n".join(md) + "\n")
    print(hedef)
    print("\n".join(md))


if __name__ == "__main__":
    main()
