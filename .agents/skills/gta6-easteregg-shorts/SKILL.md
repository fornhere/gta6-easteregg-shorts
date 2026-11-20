---
name: gta6-easteregg-shorts
description: GTA 6 easter egg Shorts motorunu çalıştırır - yeni keşfedilen easter egg'leri bulur, en az iki kaynakla doğrular, keşif kliplerinden kısa kesitlerle hızlı tempolu İngilizce anlatımlı dikey Shorts kurar ve inceleme paketine koyar (yüklemez). "GTA 6 easter egg Shorts üret", "motoru çalıştır", "yeni easter egg bul", "easter egg taraması yap", "GTA 6 Shorts kuyruğu", "UFO/easter egg videosunu yeniden üret", "sunuculu GTA 6 Shorts" dendiğinde kullan. Also use for "make GTA 6 easter egg Shorts", "run the Shorts engine", "find new GTA 6 easter eggs", "scan for easter eggs".
---

# GTA 6 easter egg Shorts motoru

<!-- MOTOR_KOKU -->Motor kökü: bu deponun kökü (`motor.sh`, `AGENTS.md`, `README.md` aynı dizinde). Komutları orada çalıştır.
Bu skill yalnız yön verir; komutların ve kuralların doğrusu motorun içindedir. Başlamadan `README.md`'yi oku.

## Akış

| Adım | Komut / talimat |
|---|---|
| TARA | `./motor.sh tara` → `kuyruk/TARAMA-*.md`; ajan puanı: `istemler/tara.md` |
| DOĞRULA | `./motor.sh dogrula` → `kuyruk/ONAY.md` (>= 2 bağımsız kaynak; kara liste işaretli olan hazır olamaz) |
| ONAY (insan) | `./motor.sh onayla <aday_id>` — test koşusunda ajan onayı ancak `--not "test için ajan onayı"` ile |
| TOPLA | `./motor.sh topla <iş> <aday_id>` (indirme, künye, whisper dökümü, kare sayfaları) |
| YAZ | `istemler/yaz.md` → `isler/<iş>/metin.md` + `metin.txt` |
| SESLENDİR | `istemler/seslendir.md` → `./motor.sh sik <iş>` → `./motor.sh zaman <iş>` |
| KURGULA | `istemler/kurgu.md` → `cekimler.json`; deneme `./motor.sh kare <iş> 0.1,5,12` |
| KONTROL + PAKET | `./motor.sh bitir <iş>` → `inceleme/<tarih>-<iş>/` (kontrol düşerse paket çıkmaz) |

## Sunucu kipi

Harici bir araçta (ör. Shorts Studio) üretilen konuşan sunucu videosunu `isler/<iş>/sunucu/sunucu.mp4` olarak koy (9:16, kendi sesi, ekrana gömülü
yazısız); `cekimler.json`'da `ayar.kip: "sunucu"` + `ayar.sunucu` + `ayar.anlatim: "sunucu/sunucu.mp4"`; tek komut
`./motor.sh sunucu <iş> [dil]`. Düzen: üst %58 oyun klibi, alt %42 sunucu, altyazı sınırda, üst bant korunur. TTS gerekmez.

## Kalıcı kurallar (kontrol.py düşürür)

- **Kanca B:** ilk cümle "There's a/an <tuhaf şey> in GTA 6, …"; "GTA 6" ilk cümlede zorunlu.
- **Üst başlık bandı:** baştan sona "<KONU> IN GTA 6?" (`ayar.konu`); künye bandın altında, altyazı ortada.
- **Telif:** Shorts <= 59 sn; kaynak klip sesi tamamen kapalı (`kaynak_ses_db: null`);
  tek kaynaktan art arda <= 4 sn; en az 2 kaynak, hiçbiri > %55; ekranda `clip: @kanal` + açıklamada link;
  spoiler / ara sahne / çıplaklık yok; oyun içi radyo müziği yok. Özgün analiz katmanı (konum kartı, ok, daire,
  adım sayacı, kanıt/gönderme kartı) hedefi >= %50 (uyarı).
- **İzin:** şablon `izin/SABLON.md`, metin `bin/izin.py mesaj <iş>`, arşiv `izin/izinler.jsonl`. Motor mesaj GÖNDERMEZ.
**Yükleme yok** — yükleme yalnız kullanıcı onayıyla, elle. Zamanlayıcıyı kullanıcı onaysız etkinleştirme.
- Yalnız doğrulanmış bilgi; `metin.md`'de iddia → dayanak tablosu.
- **Görünüm tek yerden:** `ayar.json > stil` (Montserrat, vurgu #FFD400, Shorts altyazısı, üst bant, künye kapsülü, kartlar).
  Görünümü kur.py'de sabit kodla değiştirme; stil bölümünü düzenle.

## İnsan kapıları

Aday onayı · kanca/son izleme (ajan sesi dinleyemez, yalnız ölçer) · izin mesajlarını gönderme · başlık seçimi ve yükleme · zamanlayıcıyı açma.

## Sık hatalar

- Kaynak klipte çıplak NPC (ör. UFO'nun bıraktığı kadın): kareye bak; o çekimi bulanık zemin + alıntı kartıyla değiştir.
- Üst bant kaynağın üst kısmını örter: UFO / gökyüzü gibi önemli öğe kaynakta çok yukarıdaysa kadrajı aşağı al ya da başka kaynak seç.
- Kaynak kanalın kendi bindirmesi (PowerPyx "AFTER 2:00 AM", filigran, bitiş ekranı) ve oyun altyazısı kadraja girmesin.
- Whisper "2 a.m." / özel adları böler: `ayar.altyazi.birlestir` (ör. ["2","a",".m.","2AM"]).
- Epidemic `speed` hızı pek değiştirmez; hız `sesi_sik.py` ile gelir.
- 4 sn kesit tavanı için kaynakları dönüşümlü diz; aynı kaynak sahnesini iki çekimde tekrar kullanma.
- `tara.py` kümeleri sözcük benzerliğiyle kurar: aynı konu iki kümeye bölünebilir, farklı konular birleşebilir — ajan birleştirir/ayırır.

## Ajan farkları (Claude Code · Codex · Antigravity)

Akış ve kurallar her ajanda aynıdır; yalnız araç adları değişir.

| İş | Claude Code | Codex | Antigravity |
|---|---|---|---|
| Web araması (TARA/DOĞRULA) | WebSearch | yerleşik web araması | yerleşik web araması |
| Kareye bakma (PNG/JPG) | Read | görüntüyü aç | görüntüyü aç |
| TTS (isteğe bağlı) | `claude mcp add` | `codex mcp add` | `agy mcp add` |
| Başsız koşu (`motor.sh oto`) | `GTA6_AJAN=claude` | `GTA6_AJAN=codex` | `GTA6_AJAN=antigravity` |

Görsele bakamayan bir ajan kare kontrolünü atlamaz: "kareye bakılmadı" diye yazar ve insana bırakır.
