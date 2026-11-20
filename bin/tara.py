#!/usr/bin/env python3
"""TARA adımı: yeni GTA 6 easter egg keşiflerini YouTube aramasıyla bulur, konuya göre kümeler, puanlar.

Çalışan kaynaklar (20 Kas ölçümü, easteregg/tarama/ADAYLAR.md): yt-dlp ytsearch (ytsearchdate YOK),
WebSearch/WebFetch (yalnız Ajan adımında). Reddit RSS/JSON 403 verdiği için burada denenmez.

Yapılan:
  1) ayar.json'daki sorgularla `yt-dlp ytsearchN:` düz listesi (id, başlık, kanal, süre, izlenme)
  2) islenen.jsonl'daki video kimlikleri ve konu anahtarları elenir
  3) kalanların en çok --detay tanesi için tam meta veri (yükleme tarihi, açıklama, kanal kimliği)
  4) --gun günden eski ya da --azami-sure'den uzun videolar atılır
  5) başlıklar konu anahtarına indirgenip kümelenir (her küme = bir aday; bağımsız kanal sayısı = kaynak sayısı)
  6) kaba makine puanı: kaynak sayısı, izlenme/gün, tazelik, görsel tuhaflık sözcükleri
Çıktı: kuyruk/tarama-<zaman>.jsonl ve kuyruk/TARAMA-<zaman>.md (en iyi --n aday).
Makine puanı kabadır; ADAYLAR.md ölçütleriyle (G/M/K/B/T) son puanı Ajan adımı verir (istemler/tara.md).

Kullanım: tara.py [--n 8] [--gun 4] [--detay 60]
"""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]
DOLGU = set("""gta 6 vi gta6 gtavi grand theft auto the a an in of and to you is are this that it its i my we
easter egg eggs secret secrets hidden found find finds finding discovered discover new crazy insane must see
rockstar players player fans fan just actually really already location locations guide how where what why
shorts short video 100 trophy achievement leonida vice city jason lucia every most top best ever biggest
""".split())
TUHAF = set("""ufo alien aliens ghost ghosts haunted bigfoot sasquatch monster kraken whale shark zombie
cult body portal skeleton demon crab""".split())  # yalnız somut nesneler: "mystery/creepy" kümelemeyi gevşetiyordu (20 Kas testi)


def calis(cmd, zaman=180):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=zaman)


def anahtar(baslik):
    s = re.sub(r"[^a-z0-9 ]", " ", baslik.lower())
    return [w for w in s.split() if w not in DOLGU and len(w) > 2]


def islenenler():
    ids, konular = set(), []
    p = MOTOR / "islenen.jsonl"
    if p.exists():
        for satir in p.read_text().splitlines():
            if satir.strip():
                d = json.loads(satir)
                ids.update(d.get("video_idler", []))
                konular.append(set(d.get("anahtar", [])))
    return ids, konular


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--gun", type=int, default=4)
    ap.add_argument("--detay", type=int, default=60)
    ap.add_argument("--azami-sure", type=int, default=900)
    a = ap.parse_args()
    ayar = json.loads((MOTOR / "ayar.json").read_text())
    ids_eski, konular_eski = islenenler()
    bugun = dt.date.today()

    gorulen = {}
    for q in ayar["tara"]["sorgular"]:
        r = calis(["yt-dlp", "--flat-playlist", "--no-warnings", "--print",
                   "%(id)s\t%(title)s\t%(channel)s\t%(duration)s\t%(view_count)s",
                   f"ytsearch{ayar['tara'].get('sorgu_basi', 40)}:{q}"])
        for satir in r.stdout.splitlines():
            p = satir.split("\t")
            if len(p) < 5 or p[0] in ids_eski or p[0] in gorulen:
                continue
            gorulen[p[0]] = {"id": p[0], "baslik": p[1], "kanal": p[2],
                             "sure": float(p[3]) if p[3] not in ("NA", "None", "") else None,
                             "izlenme": int(p[4]) if p[4].isdigit() else 0}
        print(f"sorgu '{q}': toplam {len(gorulen)} benzersiz", file=sys.stderr)

    eleme = [e.lower() for e in ayar["tara"].get("eleme_sozcukleri", [])]
    # telif kuralı 8 : spoiler / çıplaklık kara listesi başlıkta geçen videoyu hiç alma
    eleme += [e.lower() for k in ("spoiler", "ciplak") for e in ayar.get("kara_liste", {}).get(k, [])]
    supheli = [e.lower() for e in ayar.get("kara_liste", {}).get("supheli", [])]
    adaylar = [v for v in gorulen.values() if (v["sure"] or 0) <= a.azami_sure
               and not any(re.search(rf"\b{re.escape(e)}\b", v["baslik"].lower()) for e in eleme)]
    adaylar.sort(key=lambda v: -v["izlenme"])
    detayli = []
    for v in adaylar[: a.detay]:
        r = calis(["yt-dlp", "-j", "--skip-download", "--no-warnings", f"https://www.youtube.com/watch?v={v['id']}"], 90)
        if r.returncode or not r.stdout.strip():
            continue
        d = json.loads(r.stdout.splitlines()[0])
        tarih = d.get("upload_date")
        if not tarih:
            continue
        gun = (bugun - dt.date(int(tarih[:4]), int(tarih[4:6]), int(tarih[6:]))).days
        if gun > a.gun:
            continue
        # kara liste işareti: spoiler sözcükleri yalnız başlıkta (açıklamalarda "credits" vb. genel geçer),
        # çıplaklık + şüphe sözcükleri başlık + açıklamada
        kl = ayar.get("kara_liste", {})
        baslik = v["baslik"].lower()
        metin = (v["baslik"] + " " + (d.get("description") or "")[:1500]).lower()
        v["supheli"] = sorted({e for e in kl.get("spoiler", []) if re.search(rf"\b{re.escape(e)}\b", baslik)} |
                              {e for e in kl.get("ciplak", []) + kl.get("supheli", [])
                               if re.search(rf"\b{re.escape(e)}\b", metin)})
        v.update({"tarih": tarih, "gun": max(gun, 0), "etiket": "@" + (d.get("uploader_id") or "").lstrip("@"),
                  "kanal_url": d.get("channel_url"), "aciklama": (d.get("description") or "")[:600],
                  "url": d.get("webpage_url")})
        detayli.append(v)

    # kümele: anahtar sözcük kümesi Jaccard >= 0,34 ya da ortak tuhaf sözcük
    kumeler = []
    for v in detayli:
        k = set(anahtar(v["baslik"]))
        if not k:
            continue
        for c in kumeler:
            j = len(k & c["anahtar"]) / max(len(k | c["anahtar"]), 1)
            if j >= 0.34 or (k & c["anahtar"] & TUHAF):
                c["videolar"].append(v)
                c["anahtar"] |= k
                break
        else:
            kumeler.append({"anahtar": k, "videolar": [v]})
    sonuc = []
    for c in kumeler:
        if any(len(c["anahtar"] & e) / max(len(c["anahtar"] | e), 1) >= 0.5 for e in konular_eski if e):
            continue
        kanallar = {v["kanal"] for v in c["videolar"]}
        ipd = sum(v["izlenme"] / max(v["gun"], 0.5) for v in c["videolar"])
        tuhaf = len(c["anahtar"] & TUHAF)
        puan = 3 * min(len(kanallar), 4) + min(ipd / 20000, 6) + 2 * tuhaf + (3 - min(min(v["gun"] for v in c["videolar"]), 3))
        en_iyi = max(c["videolar"], key=lambda v: v["izlenme"])
        sonuc.append({"id": "-".join(sorted(c["anahtar"] & TUHAF) or anahtar(en_iyi["baslik"])[:3]) or en_iyi["id"],
                      "ornek_baslik": en_iyi["baslik"], "anahtar": sorted(c["anahtar"]),
                      "kanal_sayisi": len(kanallar), "izlenme_gun": round(ipd), "makine_puani": round(puan, 1),
                      "dogrulama": "aday (>=2 kanal)" if len(kanallar) >= 2 else "tek kaynak - bekler",
                      "kara_liste_isareti": sorted({w for v in c["videolar"] for w in v.get("supheli", [])}),
                      "videolar": [{k: v.get(k) for k in ("id", "url", "baslik", "kanal", "etiket", "tarih", "izlenme", "sure", "supheli")}
                                   for v in sorted(c["videolar"], key=lambda v: -v["izlenme"])]})
    sonuc.sort(key=lambda s: -s["makine_puani"])
    zaman = dt.datetime.now().strftime("%Y%m%d-%H%M")
    kuyruk = MOTOR / "kuyruk"
    kuyruk.mkdir(exist_ok=True)
    (kuyruk / f"tarama-{zaman}.jsonl").write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in sonuc))
    md = [f"# Tarama {zaman}", "", f"{len(gorulen)} benzersiz video, {len(detayli)} tanesi son {a.gun} günde; "
          f"{len(sonuc)} konu kümesi (işlenenler elendi). Makine puanı kaba; son puan ajan/insan.", "",
          "| # | Aday | Kanal | İzl/gün | Puan | Doğrulama | Örnek |", "|---|---|---|---|---|---|---|"]
    for i, s in enumerate(sonuc[: a.n], 1):
        v = s["videolar"][0]
        md.append(f"| {i} | `{s['id']}` | {s['kanal_sayisi']} | {s['izlenme_gun']} | {s['makine_puani']} | "
                  f"{s['dogrulama']} | [{v['baslik'][:60]}]({v['url']}) |")
    (kuyruk / f"TARAMA-{zaman}.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    print(f"\n-> {kuyruk / f'tarama-{zaman}.jsonl'}")


if __name__ == "__main__":
    main()
