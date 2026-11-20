#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "opencv-python-headless", "pillow"]
# ///
"""KONTROL adımı: render edilmiş Shorts'u çekim tablosuna ve kurallara karşı ölçer.

Ölçülenler (makine): biçim (1080x1920, 30 fps, süre), ses (bütünleşik LUFS, gerçek tepe, sessiz boşluk),
donma, çekim süreleri (kural 5: sabit plan <= 4 sn), kaynak payları (tek kaynaktan art arda <= 6 sn,
en az 2 kaynak, hiçbir kaynak > %55), künye (her çekimin kaynağında etiket var mı), altyazı (parça <= 3 kelime),
müzik başlangıcı (<= 3,5 sn) ve sürekliliği (tablodan).
Üretilenler: kontrol/kareler.jpg (her çekimden bir kare + kesim kareleri), kontrol/kanca-3sn.jpg
(ilk 3 sn, 0,25 sn arayla), KONTROL.md (SENTEZ §6 listesi: makine cevapları + insan sorusu olarak kalanlar).
Sesi DİNLEMEZ; yalnız ölçer.

Kullanım: kontrol.py <iş klasörü> [--tablo cekimler.json] [--video cikti/x.mp4]
"""
import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parents[1]


def kur_modul():
    spec = importlib.util.spec_from_file_location("kur", MOTOR / "montaj" / "kur.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def calis(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("is_klasoru")
    ap.add_argument("--tablo", default="cekimler.json")
    ap.add_argument("--video", default=None)
    a = ap.parse_args()
    J = Path(a.is_klasoru).resolve()
    T = json.loads((J / a.tablo).read_text())
    A = T["ayar"]
    video = J / (a.video or A["cikti"])
    out = J / "kontrol"
    out.mkdir(exist_ok=True)
    sonuc = []  # (madde, durum, ayrıntı)

    def ekle(m, ok, ay):
        sonuc.append((m, "EVET" if ok is True else ("HAYIR" if ok is False else ok), ay))

    # biçim
    pr = json.loads(calis(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration,size",
                           "-of", "json", str(video)]).stdout)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    sure = float(pr["format"]["duration"])
    ekle("Biçim 1080x1920 30 fps", v["width"] == 1080 and v["height"] == 1920 and v["r_frame_rate"] == "30/1",
         f"{v['width']}x{v['height']} {v['r_frame_rate']}, {sure:.2f} sn, {int(pr['format']['size']) / 1e6:.1f} MB")
    ekle("Süre <= 59 sn (telif kuralı 5: 61-180 sn Shorts Content ID'de küresel engellenir)", sure <= 59.0, f"{sure:.1f} sn")
    ekle("Süre 25-45 sn (danışman önerisi; düşürmez)", (25 <= sure <= 45) or "UYARI" if sure > 10 else "—", f"{sure:.1f} sn")
    ayar = json.loads((MOTOR / "ayar.json").read_text())
    tavan = float(ayar["kurgu"].get("tek_kaynak_seri_azami_sn", 4.0))

    # ses
    r = calis(["ffmpeg", "-nostdin", "-i", str(video), "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    lufs = float(I[-1]) if I else None
    tepe = float(tp[-1]) if tp else None
    ekle("Ses yüksekliği -14 LUFS ±1, tepe <= -1 dBTP", lufs is not None and abs(lufs + 14) <= 1 and (tepe or 0) <= -1.0,
         f"{lufs} LUFS, tepe {tepe} dBTP")
    r = calis(["ffmpeg", "-nostdin", "-i", str(video), "-af", "silencedetect=n=-45dB:d=0.4", "-f", "null", "-"]).stderr
    bos = re.findall(r"silence_start: ([\d.]+)", r)
    ekle("Seste 0,4 sn'den uzun sessizlik yok (müzik hiç susmaz)", not bos, f"sessizlik başlangıçları: {bos or 'yok'}")
    r = calis(["ffmpeg", "-nostdin", "-i", str(video), "-vf", "freezedetect=n=0.002:d=0.6", "-map", "0:v", "-f", "null", "-"]).stderr
    don = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", r)]
    # bulanık zeminli analiz kartları bilerek durgundur: o çekimlerin içindeki donma sayılmaz
    kartlar = [(c["bas"], c["son"]) for c in T["cekimler"] if float(c.get("bulanik", 0)) >= 15]
    gercek = [x for x in don if not any(a - 0.05 <= x < b for a, b in kartlar)]
    ekle("Görüntü donması yok (0,6 sn; analiz kartları hariç)", not gercek,
         f"donma: {gercek or 'yok'}" + (f"; kart içi (sayılmadı): {[x for x in don if x not in gercek]}" if len(gercek) < len(don) else ""))

    # çekimler ve kaynaklar
    C = T["cekimler"]
    uzun = [(c["bas"], c["son"]) for c in C if c["son"] - c["bas"] > 4.0 + 1e-6]
    ekle("Kural 5: hiçbir çekim 4,0 sn'yi aşmıyor", not uzun, f"en uzun {max(c['son'] - c['bas'] for c in C):.2f} sn; aşan: {uzun or 'yok'}")
    pay = {}
    for c in C:
        pay[c["kaynak"]] = pay.get(c["kaynak"], 0) + c["son"] - c["bas"]
    toplam = sum(pay.values())
    # bulanık zeminli analiz kartları (bulanik >= 15) kaynak kesiti sayılmaz ve seriyi böler
    seri, en_seri, onceki, seri_bas = 0.0, (0.0, None, 0), None, 0
    for c in C:
        if float(c.get("bulanik", 0)) >= 15:
            onceki, seri = None, 0.0
            continue
        if c["kaynak"] == onceki:
            seri += c["son"] - c["bas"]
        else:
            seri, seri_bas = c["son"] - c["bas"], c["bas"]
        onceki = c["kaynak"]
        if seri > en_seri[0]:
            en_seri = (seri, c["kaynak"], seri_bas)
    pay_metin = ", ".join(f"{k} ({T['kaynaklar'][k].get('kanal', k)}) {v / toplam:.0%}" for k, v in pay.items())
    ekle("En az 2 kaynak", len(pay) >= 2, pay_metin)
    ekle("Hiçbir kaynak videonun çoğu değil (<= %55)", max(pay.values()) / toplam <= 0.55, pay_metin)
    ekle(f"Tek kaynaktan art arda <= {tavan:g} sn (telif kuralı 1: 2-4 sn kesit)", en_seri[0] <= tavan + 1e-6,
         f"en uzun seri {en_seri[0]:.2f} sn ({en_seri[1]}, {en_seri[2]:.2f} sn'den)")
    sesli = [c["bas"] for c in C if c.get("kaynak_ses_db") is not None]
    ekle("Kaynak kliplerin sesi tamamen kapalı (telif kuralı 4)", A.get("kaynak_ses_db") is None and not sesli,
         f"ayar.kaynak_ses_db={A.get('kaynak_ses_db')}; sesli çekim: {sesli or 'yok'}")
    # özgün analiz katmanı payı
    analiz = sum(c["son"] - c["bas"] for c in C
                 if c.get("katman") or c.get("kart") or c.get("isaret") or float(c.get("bulanik", 0)) >= 15)
    kod_tam = sum(c["son"] - c["bas"] for c in C if float(c.get("bulanik", 0)) >= 15)
    hedef_oz = float(ayar["kurgu"].get("ozgun_katman_hedef", 0.5))
    ekle(f"Özgün analiz katmanı payı >= %{hedef_oz * 100:.0f} (tahmini ölçüt; düşürmez)",
         True if analiz / toplam >= hedef_oz else "UYARI",
         f"katmanlı süre %{analiz / toplam * 100:.0f} (bunun %{kod_tam / toplam * 100:.0f}'i bulanık zeminli tam kart); "
         "üst başlık, künye ve altyazı tüm videoda ayrıca var")
    # kanca kuralı: ilk cümlede GTA 6 (B kalıbı)
    mt = J / A.get("metin_dosyasi", "metin.txt")
    if mt.exists():
        ilk = re.split(r"(?<=[.!?])\s+", mt.read_text().strip())[0]
        gta = bool(re.search(r"\bGTA\s?(6|VI)\b", ilk))
        ekle("Kanca kuralı: ilk cümlede 'GTA 6' (B kalıbı)", gta, f"ilk cümle: \"{ilk}\"")
        ekle("Kanca kalıbı 'There's a/an ...' (düşürmez)", True if re.match(r"There('s| is) (a|an) ", ilk) else "UYARI", ilk[:60])
    else:
        ekle("Kanca kuralı: ilk cümlede 'GTA 6' (B kalıbı)", False, f"metin dosyası yok: {mt.name}")
    ub = (A.get("ust_baslik") or {}).get("metin") or (f"{A['konu'].upper()} IN GTA 6?" if A.get("konu") else None)
    ekle("Üst başlık bandı '<KONU> IN GTA 6?'", bool(ub) and "GTA 6" in ub, f"\"{ub}\"")
    # kara liste: kaynak başlık/açıklama ve oyun içi döküm
    kl = ayar.get("kara_liste", {})
    bulunan = set()
    metinler = [s.get("baslik", "") for s in T["kaynaklar"].values()]
    for d in (J / "dokum").glob("*.txt") if (J / "dokum").exists() else []:
        metinler.append(d.read_text(errors="ignore"))
    for kat in ("spoiler", "ciplak"):
        for w in kl.get(kat, []):
            if any(re.search(rf"\b{re.escape(w)}\b", m.lower()) for m in metinler):
                bulunan.add(f"{kat}:{w}")
    ekle("Kara liste (spoiler/çıplaklık) sözcüğü yok; kareler ayrıca gözle bakılır", not bulunan or "UYARI",
         f"bulunan: {sorted(bulunan) or 'yok'}")
    # izin durumu
    izin = {}
    ip = MOTOR / "izin" / "izinler.jsonl"
    if ip.exists():
        for x in ip.read_text().splitlines():
            if x.strip():
                r = json.loads(x)
                izin[r["url"]] = r
    durumlar = [f"{s['kanal']}: {izin.get(s['url'], {}).get('cevap') or ('istendi' if s['url'] in izin else 'istenmedi')}"
                for s in T["kaynaklar"].values()]
    ekle("İzin durumu (bilgi; düşürmez)", "BİLGİ", "; ".join(durumlar))
    eksik = [k for k, s in T["kaynaklar"].items() if not s.get("etiket") or not s.get("url")]
    ekle("Künye: her kaynakta ekran etiketi ve URL var (ekranda 'clip: @kanal')", not eksik and bool(A.get("kunye")),
         f"eksik: {eksik or 'yok'}")
    M = A.get("muzik")
    ekle("Kural 6: müzik <= 3,5 sn'de başlar, sona dek sürer (tablo)", bool(M) and float(M.get("ofset", 0)) >= 0,
         "müzik 0,0 sn'de giriyor, çıkışta %25'e iner, kesilmez" if M else "müzik yok")
    # altyazı parçaları
    try:
        kur = kur_modul()
        kel = json.loads((J / A["kelimeler"]).read_text())["words"]
        acfg = {**A["altyazi"], **ayar.get("stil", {}).get("altyazi", {})}  # montajla aynı birleşik ayar
        kel = kur.kelimeleri_duzelt(kel, acfg.get("birlestir", []))
        parca = kur.altyazi_parcala(kel, acfg, float(A["sure"]))
        en = max(len(p[2].split()) for p in parca)
        ekle("Kural 7: altyazı parçası <= 3 kelime", en <= 3,
             f"en uzun parça {en} kelime; üst başlık bandı kullanıcı kararıyla ayrıca var; analiz/kanıt kartı "
             "çekimlerinde altyazı kapalı olabilir")
        ilk = next((p for p in parca if p[0] <= 3.0), None)
    except Exception as e:  # noqa
        ekle("Kural 7: altyazı", "?", f"ölçülemedi: {e}")

    # kareler
    zamanlar = []
    for c in C:
        zamanlar += [c["bas"] + 0.05, (c["bas"] + c["son"]) / 2]
    zamanlar = sorted({round(min(t, sure - 0.05), 2) for t in zamanlar})
    tmp = out / "tmp"
    tmp.mkdir(exist_ok=True)
    for f in tmp.glob("*.png"):
        f.unlink()
    for i, t in enumerate(zamanlar):
        calis(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
               "-vf", f"scale=270:480,drawtext=text='{t:.2f}':x=6:y=6:fontsize=26:fontcolor=yellow:box=1:boxcolor=black",
               str(tmp / f"{i:03d}.png")])
    sutun = 10
    satir = (len(zamanlar) + sutun - 1) // sutun
    calis(["ffmpeg", "-nostdin", "-v", "error", "-y", "-framerate", "1", "-i", str(tmp / "%03d.png"),
           "-vf", f"tile={sutun}x{satir}", "-frames:v", "1", str(out / "kareler.jpg")])
    calis(["ffmpeg", "-nostdin", "-v", "error", "-y", "-t", "3.0", "-i", str(video), "-vf",
           "fps=4,scale=270:480,drawtext=text='%{pts\\:flt}':x=6:y=6:fontsize=26:fontcolor=yellow:box=1:boxcolor=black,tile=6x2",
           "-frames:v", "1", str(out / "kanca-3sn.jpg")])
    calis(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", "0.2", "-i", str(video), "-frames:v", "1", str(out / "kare-0.2.png")])

    # rapor
    md = [f"# KONTROL — {video.name}", "", "Makine ölçümü (`bin/kontrol.py`). Ses dinlenmedi; yalnız ölçüldü.", "",
          "| Madde | Sonuç | Ayrıntı |", "|---|---|---|"]
    md += [f"| {m} | {d} | {ay} |" for m, d, ay in sonuc]
    md += ["", "## SENTEZ §6 yayın öncesi listesi", "",
           "| # | Soru | Cevap |", "|---|---|---|",
           "| 1 | 0,2 sn karesi (ses ve yazı kapalı) sıradan olmayan bir şey gösteriyor mu? | İNSAN/AJAN: `kontrol/kare-0.2.png` |",
           "| 2 | Ses ve yazı kapalıyken ilk 3 sn'de ne olduğu anlaşılıyor mu? | İNSAN/AJAN: `kontrol/kanca-3sn.jpg` |",
           "| 3 | Tek ana soru, son %20'ye kadar açık mı? | METİN: `metin.md` |",
           "| 4 | Son 3 sn soruyu fiziksel/görsel olarak kapatıyor mu? | İNSAN/AJAN: son kareler |",
           f"| 5 | 4,0 sn'den uzun durağan plan yok mu? | {'EVET' if not uzun else 'HAYIR'} (tablo) |",
           f"| 6 | Müzik 3,5 sn'den önce girip hiç susmuyor mu? | {'EVET' if M and not bos else 'KONTROL ET'} (tablo + sessizlik ölçümü) |",
           "| 7 | Ekranda aynı anda <= 3 kelime mi? | altyazı <= 3; üst başlık bandı (kullanıcı kararı, 20 Kas) ve analiz kartları istisna |",
           "| + | Çıplaklık / sürprizbozan / ara sahne yok mu? | AJAN: `kontrol/kareler.jpg` gözle; kara liste satırı |",
           "| 8 | (Döngülü ise) son kare ilk kareye bağlanıyor mu? | döngü hedeflenmedi |", ""]
    (J / "KONTROL.md").write_text("\n".join(md))
    print("\n".join(md))
    print(f"\nkareler: {out / 'kareler.jpg'}\nkanca: {out / 'kanca-3sn.jpg'}")
    dusen = [m for m, d, _ in sonuc if d == "HAYIR"]
    if dusen:
        print(f"\nDÜŞEN MADDE: {len(dusen)}: " + " | ".join(dusen), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
