# Başvuru (Türkçe) — komutlar, kurallar, cekimler.json, stil

[README](../README.md) · [Türkçe README](../README.tr.md)

## Kalıcı kurallar (kontrol.py düşürür = paket çıkmaz)

| Kural | Ölçüm |
|---|---|
| Kanca B: ilk cümle "There's a/an ... in GTA 6, ..."; "GTA 6" ilk cümlede | `metin.txt` ilk cümlesi |
| Üst başlık bandı baştan sona "<KONU> IN GTA 6?" (`ayar.konu`) | ayar |
| Süre <= 59 sn | ffprobe |
| Kaynak klip sesi tamamen kapalı (`kaynak_ses_db: null`) | tablo |
| Tek kaynaktan art arda <= 4 sn; en az 2 kaynak; hiçbiri > %55 | tablo |
| Ekranda `clip: @kanal`; açıklamada kanal + link + "Not affiliated with Rockstar Games" | tablo + paket |
| Çekim <= 4 sn, müzik baştan sona, -14 LUFS, donma yok, altyazı <= 3 kelime | ölçüm |
| Uyarı (düşürmez): özgün analiz katmanı >= %50; kara liste sözcüğü; süre 25-45 sn | tablo/döküm |

Kara liste (`ayar.json > kara_liste`): başlıkta spoiler/çıplaklık sözcüğü geçen video taramaya girmez; şüpheli sözcük "elle bak" olur.
Kareleri ayrıca gözle kontrol et.

## Komutlar

```sh
./motor.sh tara                 # yeni keşifler  -> kuyruk/TARAMA-*.md
./motor.sh dogrula              # kural kontrolü -> kuyruk/ONAY.md
./motor.sh onayla <aday_id>     # İNSAN KAPISI
./motor.sh topla <iş> <aday_id> # indir + künye + döküm + kareler -> isler/<iş>/
./motor.sh sik <iş>             # TTS -> ses/anlatim.wav (3,5 kelime/sn)
./motor.sh zaman <iş>           # kelime zamanları (paketteki faster-whisper betiği)
./motor.sh transkript <dosya> <dizin> [dil]   # herhangi bir ses/videonun kelime zamanlı dökümü
./motor.sh kare <iş> 0.1,5,12   # kadraj denemesi (PNG)
./motor.sh bitir <iş>           # kur + kontrol + paket (kontrol düşerse paket çıkmaz)
./motor.sh izin <iş>            # klip sahiplerine izin metni; GÖNDERMEZ
./motor.sh durum                # onay kuyruğu + inceleme klasörleri
./motor.sh sunucu <iş> [dil]    # sunucu kipi tek komut
./motor.sh oto                  # zamanlayıcı koşusunun aynısı, elle
```
`tara`, `topla` ve `oto` ağ kullanır (yt-dlp); `./motor.sh` argümansız yalnız kullanımı basar.

## İnsan kapıları
1. Aday onayı (`motor.sh onayla`). 2. Son izleme + ses (müzik/ton/miks senin kulağınla). 3. İzin mesajlarını sen gönderirsin;
cevap `bin/izin.py cevap ...` ile `izin/izinler.jsonl`'a kaydedilir. 4. Başlık seçimi ve yükleme elle. 5. Zamanlayıcıyı açmak.

## Montaj stili (tek yer: `ayar.json > stil`)

- Font: **Montserrat** (değişken; Black / ExtraBold / Bold / SemiBold), `montaj/font/Montserrat.ttf`, lisans
  `montaj/font/Montserrat-OFL.txt` (SIL OFL 1.1, Google Fonts deposundan).
- Renkler: vurgu **#FFD400** (255,212,0), beyaz, gri (198,204,214) alt satırlar, siyah kontur.
- Altyazı: BÜYÜK HARF, Montserrat Black 92 px, 11 px siyah kontur + yumuşak gölge, 1–3 kelime (en çok 16 harf),
  konuşulan kelime sarı, girişte 0,1 sn "pop" (0,85 → 1,0), orta y = 1320 (alt üçte bir, Shorts başlık alanının üstünde).
  Özne altyazının altında kalıyorsa çekime `altyazi_y`.
- Üst bant: "<KONU> IN GTA 6?", Black 84 px (sığmazsa küçülür), "GTA 6?" sarı, yumuşak kenarlı yarı saydam koyu şerit,
  ilk 0,4 sn'de yukarıdan kayarak + belirerek girer (y 205).
- Künye: küçük yarı saydam kapsül, gri "clip:" + beyaz "@kanal", 28 px (x 44, y 392). Adım sayacı: sarı kapsül "STEP 1/4" (sağ, y 412).
- Kartlar: aynı font, köşe yarıçapı 26, koyu %86 zemin, sol sarı şerit, sarı ikon; ana satır BÜYÜK HARF ExtraBold,
  "gri" satırlar SemiBold alt satır. Alt konum 1030 (altyazının üstü); harita çekimlerinde 640 (iğneyi örtmesin).
İş başına değiştirmek için tabloya `ayar.stil` (aynı anahtarlar) yazılır.

## Sunucu kipi (harici sunuculu Shorts)

Harici bir araçta (ör. Shorts Studio) üretilen konuşan sunucu (dede / AI influencer) videosu oyun klipleriyle birleşir:

- Düzen: üst %58 oyun klibi (kesitler, künye, daire/ok, kartlar, adım sayacı; kartlar bu bölmeye sıkıştırılır),
  alt %42 sunucu (yalnız kırpma, yeşil ekran yok; `ayar.sunucu` x/y/z ile yüz kadrajda), sınırda sarı ayraç,
  altyazı iki bölmenin sınırında, üstte "<KONU> IN GTA 6?" bandı. Oran: `ayar.json > stil.sunucu.ust_oran`.
- Ses: sunucunun kendi sesi anlatımdır (TTS yok); kelime zamanları o sesten whisper ile çıkar; müzik + SFX
  aynı kurallarla altında (konuşmada kısılır), kaynak klip sesi kapalı.
- Kullanım:
  1. Sunucu videosunu `isler/<iş>/sunucu/sunucu.mp4` olarak koy (9:16, kendi sesiyle, **ekrana gömülü yazı/altyazı olmadan**).
  2. `metin.txt` = sunucunun söylediği metin (kanca kuralı buna bakar: ilk cümlede "GTA 6").
  3. `cekimler.json`: `ayar.kip: "sunucu"`, `ayar.sunucu: {"dosya": "sunucu/sunucu.mp4", "x": 0.5, "y": 0.40, "z": 1.25}`,
     `ayar.anlatim: "sunucu/sunucu.mp4"`, `ayar.sure` = sunucu videosu süresi; çekimler sunucunun cümlelerine göre.
  4. **Tek komut:** `./motor.sh sunucu <iş> [dil]` → whisper (varsayılan en) → `zaman/anlatim.json` → kur → kontrol
     (→ `paket.json` varsa paket).

## cekimler.json özet (montaj/kur.py)

`ayar`: `konu` (üst bant), `ust_baslik` {boyut, ust_y, bant}, `kunye` {y: 462}, `sayac` [{t, metin}], `flas` [{t}],
`altyazi` {orta_y 1180, birlestir [[sözcükler..., yeni]]}, `muzik` {dosya, ofset, db, konusmada_kis_db}, `kaynak_ses_db: null`.
`kaynaklar`: harf → {dosya, kanal, etiket, url, tarih}. `cekimler`: {bas, son, kaynak, kt, hiz (0.02 = donmuş kare),
kadraj [{u|t, x, y, z}], vurus, parlaklik, gama, bulanik, karart, altyazi (false), altyazi_y, isaret [{sx, sy, r, oran, bas}],
kart {x0, y0, x1, y1, genislik, orta_y, karart}, katman [{tur: panel|pin|ok, ...}]}. `sfx`: [{t, dosya, db, kirp_*}].

## Klasörler

| Yol | Ne |
|---|---|
| `install.sh` | araç kontrolü + Python bağımlılıkları (uv) + isteğe bağlı skill kurulumu |
| `motor.sh`, `ayar.json` | giriş noktası; sorgular, kara liste, ses kimlikleri, kurgu sınırları, stil |
| `bin/` | tara, dogrula, topla, sesi_sik, kontrol, paket, izin, transkript (faster-whisper) |
| `montaj/kur.py`, `montaj/font/` | render; Montserrat + OFL lisansı |
| `istemler/*.md` | LLM adımlarının talimatları |
| `AGENTS.md`, `CLAUDE.md` | ajan yönergesi (Codex/Antigravity `AGENTS.md`, Claude Code `CLAUDE.md` üzerinden) |
| `.agents/skills/gta6-easteregg-shorts/` | ortak skill (Codex, Antigravity); `.claude/skills/` buna bağlantı |
| `ajan-kur.sh` | skill'i global klasörlere kurar/kaldırır (isteğe bağlı) |
| `izin/SABLON.md` | izin metni şablonu (`izinler.jsonl` çalışırken oluşur) |
| `kuyruk/` | tarama çıktıları, ONAY.md (şablon) |
| `zamanlayici/` | systemd şablonları + `calistir.sh` (KAPALI) |
| `isler/`, `inceleme/`, `islenen.jsonl` | çalışırken oluşur |

## Zamanlayıcı (varsayılan KAPALI)
`zamanlayici/gta6-motor-tara.timer` günde 3 kez tara + dogrula çalıştırır. Üretim aşaması yalnız ajan seçiliyse çalışır.
Ajanı `GTA6_AJAN=claude|codex|antigravity` ile seç (hazır komutlar `zamanlayici/calistir.sh` içinde; ağ izni açık) ya da
kendi komutunu `GTA6_OTO_KOMUT` ile ver (istem son argüman olarak eklenir). Elle deneme: `GTA6_AJAN=codex ./motor.sh oto`.
Servis dosyasında `#Environment=GTA6_AJAN=codex` satırını aç. Açmak istersen kendi kararınla:
```sh
mkdir -p ~/.config/systemd/user
sed "s#@MOTOR_DIR@#$PWD#g" zamanlayici/gta6-motor-tara.service > ~/.config/systemd/user/gta6-motor-tara.service
cp zamanlayici/gta6-motor-tara.timer ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now gta6-motor-tara.timer
```
Durdurma: `systemctl --user disable --now gta6-motor-tara.timer`.

## Bilinen sınırlar
- Ses dinlenmedi, yalnız ölçülür; müzik/ton kararı insanındır.
- Kadraj, ok/daire koordinatları otomatik değil; kamera hareketli kaynakta `hiz: 0.02` ile kare dondur.
- Tarama yalnız YouTube; haber doğrulaması ajan adımındadır. Kümeler sözcük benzerliğiyle kurulur, yanlış bölünebilir.
- Kara liste taraması kaba; çıplaklık için tek güvence kareye bakmaktır.
- Telif kuralları genel iyi uygulama tahminidir; hukuki güvence değildir.
