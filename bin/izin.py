#!/usr/bin/env python3
"""İzin şablonu ve arşivi. Mesaj GÖNDERMEZ.

  izin.py mesaj <iş klasörü> [--konu UFO] [--imza ...]   # her kaynak için doldurulmuş DM + e-posta metni
  izin.py ekle --kanal X --etiket @x --url U --is ufo-kacirilma --kanal-turu dm      # istek gönderildi kaydı
  izin.py cevap --url U --cevap evet|hayir [--kanit yol]                              # cevap kaydı
  izin.py durum <iş klasörü>                                                           # kaynak başına durum
"""
import argparse
import datetime as dt
import json
import re
import string
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]
DOSYA = MOTOR / "izin" / "izinler.jsonl"


def oku():
    if not DOSYA.exists():
        return []
    return [json.loads(x) for x in DOSYA.read_text().splitlines() if x.strip()]


def yaz(kayitlar):
    DOSYA.write_text("".join(json.dumps(k, ensure_ascii=False) + "\n" for k in kayitlar))


def main():
    ap = argparse.ArgumentParser()
    alt = ap.add_subparsers(dest="komut", required=True)
    m = alt.add_parser("mesaj"); m.add_argument("is_klasoru"); m.add_argument("--konu"); m.add_argument("--imza", default="[your name / channel]")
    e = alt.add_parser("ekle")
    for k in ("kanal", "etiket", "url", "is"):
        e.add_argument(f"--{k}", required=True)
    e.add_argument("--kanal-turu", default="dm")
    c = alt.add_parser("cevap"); c.add_argument("--url", required=True); c.add_argument("--cevap", choices=["evet", "hayir"], required=True); c.add_argument("--kanit")
    d = alt.add_parser("durum"); d.add_argument("is_klasoru")
    a = ap.parse_args()
    if a.komut in ("mesaj", "durum"):
        J = Path(a.is_klasoru).resolve()
        T = json.loads((J / "cekimler.json").read_text())
        kayit = {k["url"]: k for k in oku()}
        if a.komut == "durum":
            for s in T["kaynaklar"].values():
                k = kayit.get(s["url"])
                print(f"{s['kanal']} ({s['url']}): " + ("istenmedi" if not k else f"istendi {k['istek_tarihi']}, cevap: {k.get('cevap') or 'yok'}"))
            return
        sablon = (MOTOR / "izin" / "SABLON.md").read_text()
        dm = sablon.split("## DM (kısa)")[1].split("## E-posta")[0].strip()
        ep = sablon.split("## E-posta")[1].split("## Kayıt")[0].strip()
        konu = a.konu or T["ayar"].get("konu", "")
        if len(konu) > 4 and konu.isupper():
            konu = string.capwords(konu.lower())  # "PAUL WALKER'S CAR" -> "Paul Walker's Car"
        for s in T["kaynaklar"].values():
            alanlar = dict(kanal=s["kanal"], etiket=s["etiket"], url=s["url"], konu=konu, imza=a.imza)
            print(f"===== {s['kanal']} =====\n--- DM ---\n{dm.format(**alanlar)}\n--- E-posta ---\n{ep.format(**alanlar)}\n")
    elif a.komut == "ekle":
        k = oku()
        k.append({"kanal": a.kanal, "etiket": a.etiket, "url": a.url, "is": getattr(a, "is"),
                  "istek_tarihi": dt.date.today().isoformat(), "kanal_turu": a.kanal_turu, "cevap": None,
                  "cevap_tarihi": None, "kanit": None})
        yaz(k)
    elif a.komut == "cevap":
        k = oku()
        for r in k:
            if r["url"] == a.url:
                r.update(cevap=a.cevap, cevap_tarihi=dt.date.today().isoformat(), kanit=a.kanit)
        yaz(k)


if __name__ == "__main__":
    main()
