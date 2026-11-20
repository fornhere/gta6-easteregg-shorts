#!/usr/bin/env python3
"""DOĞRULA adımı (insan onayı kapısı).

Son taramadaki her aday için kural: en az 2 BAĞIMSIZ kaynak (farklı kanal ya da kanal + haber/wiki sayfası).
  - >= 2 kaynak  -> "hazir": kuyruk/ONAY.md'ye girer, insan onayını bekler
  - tek kaynak / şüpheli -> "bekler": kuyrukta kalır, sonraki taramada ikinci kaynak çıkarsa yükselir
Bu betik yalnız makinece sayılabileni yapar. Görüntülü kanıtın aynı oyun anını gösterdiği, eski oyun/kurgu/yapay
zekâ sahtesi olmadığı ve haber kaynakları Ajan adımında (istemler/dogrula.md: web araması + kare bakışı)
kontrol edilip `--ek-kaynak` ile eklenir. Onayı yalnız insan verir: `motor.sh onayla <aday_id>`.

Kullanım: dogrula.py [--tarama kuyruk/tarama-X.jsonl] [--ek-kaynak aday_id=url ...]
          dogrula.py --onayla aday_id   (yalnız insan çalıştırır; kuyruk/onaylanan.jsonl'a ekler)
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]
K = MOTOR / "kuyruk"


def son_tarama():
    t = sorted(K.glob("tarama-*.jsonl"))
    if not t:
        sys.exit("tarama yok: önce motor.sh tara")
    return t[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tarama")
    ap.add_argument("--ek-kaynak", nargs="*", default=[], help="aday_id=url (haber/wiki/başka kanal)")
    ap.add_argument("--onayla")
    ap.add_argument("--not", dest="onay_notu", default="kullanıcı onayı")
    a = ap.parse_args()
    durum_yolu = K / "dogrulama.json"
    durum = json.loads(durum_yolu.read_text()) if durum_yolu.exists() else {}

    if a.onayla:
        if a.onayla not in durum or durum[a.onayla]["durum"] != "hazir":
            sys.exit(f"{a.onayla} 'hazir' değil; tek kaynaklı aday onaylanamaz")
        kayit = dict(durum[a.onayla], onay_zamani=dt.datetime.now().isoformat(timespec="minutes"), onay_notu=a.onay_notu)
        with open(K / "onaylanan.jsonl", "a") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
        durum[a.onayla]["durum"] = "onaylandi"
        durum_yolu.write_text(json.dumps(durum, ensure_ascii=False, indent=1))
        print(f"onaylandı: {a.onayla} -> kuyruk/onaylanan.jsonl (sonraki: motor.sh topla {a.onayla})")
        return

    tarama = Path(a.tarama) if a.tarama else son_tarama()
    for s in (json.loads(x) for x in tarama.read_text().splitlines() if x.strip()):
        d = durum.setdefault(s["id"], {"id": s["id"], "ek_kaynak": [], "durum": "bekler"})
        if d["durum"] == "onaylandi":
            continue
        d.update({"ornek_baslik": s["ornek_baslik"], "videolar": s["videolar"], "makine_puani": s["makine_puani"],
                  "kara_liste_isareti": s.get("kara_liste_isareti", [])})
    for e in a.ek_kaynak:
        i, url = e.split("=", 1)
        if i in durum and url not in durum[i]["ek_kaynak"]:
            durum[i]["ek_kaynak"].append(url)
    for d in durum.values():
        if d["durum"] == "onaylandi":
            continue
        kanallar = {v["kanal"] for v in d.get("videolar", [])}
        d["bagimsiz_kaynak"] = len(kanallar) + len(d["ek_kaynak"])
        if d.get("kara_liste_isareti"):
            d["durum"] = "kara liste - elle bak"   # spoiler/çıplaklık/şüphe sözcüğü: otomatik hazır olamaz
        else:
            d["durum"] = "hazir" if d["bagimsiz_kaynak"] >= 2 else "bekler"
    durum_yolu.write_text(json.dumps(durum, ensure_ascii=False, indent=1))
    hazir = sorted((d for d in durum.values() if d["durum"] == "hazir"), key=lambda d: -d.get("makine_puani", 0))
    bekler = [d for d in durum.values() if d["durum"] == "bekler"]
    md = ["# ONAY KUYRUĞU (insan kapısı)", "", f"Güncelleme: {dt.datetime.now():%Y-%m-%d %H:%M}. "
          "Onay vermeden önce: iki kaynağın aynı oyun anını gösterdiğine, eski oyun / mod / yapay zekâ sahtesi olmadığına "
          "ve hikâye sürprizbozanı içermediğine bak.", "", "## Hazır (>= 2 bağımsız kaynak)", ""]
    for d in hazir:
        md.append(f"- `{d['id']}` — {d['ornek_baslik'][:80]} · {d['bagimsiz_kaynak']} kaynak · puan {d.get('makine_puani')}")
        for v in d.get("videolar", [])[:4]:
            md.append(f"  - {v['kanal']} ({v.get('tarih')}): {v['url']}")
        for u in d["ek_kaynak"]:
            md.append(f"  - ek: {u}")
        md.append(f"  - onay: `motor/motor.sh onayla {d['id']}`")
    kara = [d for d in durum.values() if d["durum"].startswith("kara")]
    md += ["", f"## Kara liste işaretli (spoiler/çıplaklık/şüphe; onaylanamaz, elle bak) — {len(kara)}", ""]
    md += [f"- `{d['id']}` — {d.get('ornek_baslik', '')[:70]} · {', '.join(d.get('kara_liste_isareti', []))}" for d in kara]
    md += ["", f"## Bekleyen (tek kaynak) — {len(bekler)} aday", ""]
    md += [f"- `{d['id']}` — {d.get('ornek_baslik', '')[:80]}" for d in bekler[:20]]
    (K / "ONAY.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
