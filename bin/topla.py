#!/usr/bin/env python3
"""TOPLA adımı: onaylanan aday için 2-3 kaynak videoyu indirir, künyeyi yazar, kilit anları bulmaya hazırlar.

  isler/<ad>/kaynak/ham/<id>.mp4 + .info.json   (yt-dlp, <=1080p; indirilen veri güvenilmez: yalnız okunur)
  isler/<ad>/kaynak/A.mp4, B.mp4 ...             (ham dosyalara bağ; montaj bu harflerle çalışır)
  isler/<ad>/kaynaklar.json                       (harf -> kanal, @etiket, url, yükleme tarihi, süre)
  isler/<ad>/dokum/<id>.txt|json                   (yerel faster-whisper dökümü: oyun içi diyalog, yorum sesi var mı?)
  isler/<ad>/kare/<id>_NN.jpg                      (4 sn arayla 6x6 kare sayfaları; kilit anı gözle bulmak için)
  isler/<ad>/kare/<id>_sahne.txt                   (ffmpeg sahne değişimi > 0,3 zamanları)
Kilit an seçimi Ajan adımıdır (istemler/kurgu.md): kare sayfalarına bakılır, gerekirse 2 fps ayrıntı sayfası
çıkarılır. İsteğe bağlı ikinci göz: harici bir model/araçla kare incelemesi (motor çağırmaz).

Kullanım: topla.py <ad> <url1> <url2> [<url3>]   ya da   topla.py <ad> --aday <aday_id>  (kuyruk/onaylanan.jsonl)
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]


def calis(cmd, **k):
    print("$", " ".join(cmd)[:160], file=sys.stderr)
    return subprocess.run(cmd, **k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ad")
    ap.add_argument("urller", nargs="*")
    ap.add_argument("--aday")
    ap.add_argument("--azami", type=int, default=3)
    ap.add_argument("--whisper-yok", action="store_true")
    a = ap.parse_args()
    urller = list(a.urller)
    if a.aday:
        for x in (MOTOR / "kuyruk" / "onaylanan.jsonl").read_text().splitlines():
            d = json.loads(x)
            if d["id"] == a.aday:
                urller += [v["url"] for v in d.get("videolar", [])]
    # aynı kanaldan ikinci videoyu alma (bağımsız kaynak kuralı)
    J = MOTOR / "isler" / a.ad
    ham = J / "kaynak" / "ham"
    ham.mkdir(parents=True, exist_ok=True)
    (J / "dokum").mkdir(exist_ok=True)
    (J / "kare").mkdir(exist_ok=True)
    kaynaklar, kanallar = {}, set()
    harfler = iter("ABCDEFGH")
    for url in urller:
        if len(kaynaklar) >= a.azami:
            break
        r = subprocess.run(["yt-dlp", "-j", "--skip-download", "--no-warnings", url], capture_output=True, text=True)
        if r.returncode:
            print(f"meta veri alınamadı: {url}", file=sys.stderr)
            continue
        m = json.loads(r.stdout.splitlines()[0])
        if m.get("channel") in kanallar:
            continue
        vid = m["id"]
        hedef = ham / f"{vid}.mp4"
        if not hedef.exists():
            calis(["yt-dlp", "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]", "--merge-output-format", "mp4",
                   "--write-info-json", "-o", str(ham / "%(id)s.%(ext)s"), url], check=False)
        if not hedef.exists():
            print(f"indirilemedi: {url}", file=sys.stderr)
            continue
        h = next(harfler)
        bag = J / "kaynak" / f"{h}.mp4"
        if bag.is_symlink() or bag.exists():
            bag.unlink()
        bag.symlink_to(hedef)
        kanallar.add(m.get("channel"))
        kaynaklar[h] = {"dosya": f"kaynak/{h}.mp4", "kanal": m.get("channel"),
                        "etiket": "@" + (m.get("uploader_id") or m.get("channel", "")).lstrip("@"),
                        "url": m.get("webpage_url"), "tarih": m.get("upload_date"), "sure": m.get("duration"),
                        "baslik": m.get("title")}
        calis(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(hedef), "-vf",
               "fps=1/4,scale=384:-1,drawtext=text='%{pts\\:hms}':x=5:y=5:fontsize=22:fontcolor=yellow:box=1:boxcolor=black,tile=6x6",
               str(J / "kare" / f"{vid}_%02d.jpg")])
        r = subprocess.run(["ffmpeg", "-nostdin", "-i", str(hedef), "-vf", "select='gt(scene,0.3)',showinfo", "-an",
                            "-f", "null", "-"], capture_output=True, text=True)
        sahne = [s.split("pts_time:")[1].split()[0] for s in r.stderr.splitlines() if "pts_time:" in s]
        (J / "kare" / f"{vid}_sahne.txt").write_text("\n".join(sahne) + "\n")
        if not a.whisper_yok:
            calis([str(MOTOR / "motor.sh"), "transkript", str(hedef), str(J / "dokum"), "en"], check=False)
    if len(kaynaklar) < 2:
        print("UYARI: 2'den az bağımsız kaynak indirildi; kural gereği bu iş kurgulanmaz.", file=sys.stderr)
    (J / "kaynaklar.json").write_text(json.dumps(kaynaklar, ensure_ascii=False, indent=1))
    print(json.dumps(kaynaklar, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
