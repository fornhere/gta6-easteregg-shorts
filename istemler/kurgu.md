# Ajan adımı: KURGULA (cekimler.json yaz → kur → kareye bak → düzelt)

1. Kilit anlar: `isler/<ad>/kare/*_NN.jpg` (4 sn sayfa) + `dokum/*.txt` (oyun diyaloğu) + `kare/*_sahne.txt`.
   Ayrıntı için 2 fps sayfa: `ffmpeg -ss <s> -t 16 -i kaynak/A.mp4 -vf "fps=2,scale=320:-1,tile=8x4" ...`.
   Kaynak kanalın kendi yazıları (ör. PowerPyx'in "AFTER 2:00 AM" bindirmesi, filigran, bitiş ekranı) kadraj dışında kalsın.
2. Her anlatım cümlesine görüntüyü birebir eşle (>= %85 birebir). Çekim <= 4 sn, kesim 2–3 sn'de bir.
   Telif kuralları (kontrol.py ölçer): tek kaynaktan art arda <= 4 sn (kaynakları dönüşümlü diz);
   hiçbir kaynak > %55; en az 2 kaynak; `ayar.kaynak_ses_db: null` (kaynak sesi tamamen kapalı); <= 59 sn.
   Aynı kaynak anını iki çekimde kullanma (istisna: kapanışta ilk kareye dönen döngü).
   ÇIPLAKLIK / SÜRPRİZBOZAN: kareye bak. Çıplak NPC (ör. UFO'nun bıraktığı kadın), striptiz, ara sahne / hikâye sonu varsa
   o çekimi kullanma; gerekiyorsa `bulanik: 30, karart: 0.5` zemin + alıntı paneliyle anlat.
   Özgün analiz katmanı hedefi >= %50 süre: konum kartı (harita + `pin` + `panel` ikon=pin), `ok`, `isaret` (daire),
   adım sayacı (`ayar.sayac`), kanıt kartı (`kart`: oyun arayüzünden bölge, ör. kupa / araç adı), gönderme kartı
   (bulanık zemin + `panel` ikon=film). Kaynak durağansa `hiz: 0.02` ile kare dondurulup kod kamerayla yaklaşılır.
   Üst başlık bandı (y 222–445) kaynağın üstünü örter: önemli öğe orada kalmasın. Altyazı özneyi örtüyorsa çekime `altyazi_y`.
3. Kadraj: `x,y` kırpma merkezi (0–1, kaynakta), `z` yakınlık (1 = tam yükseklik 9:16). Özneyi merkezde tut; oyun
   altyazısı (alt %10), harita/HUD (köşeler), kaynak filigranı dışarıda kalsın. Kesimde kısa vuruş otomatik.
   Kanca çekiminde `isaret` (kırmızı daire, kaynak piksel koordinatı). Kanıt anı için `kart` (kaynak karenin bir
   bölgesini — ör. kupa bildirimi — büyütüp ortaya bindirir; o çekimde `altyazi: false`). Karanlık sahne: `parlaklik`, `gama`.
4. `motor.sh kare <ad> 0.1,5,12,...` ile PNG'lere bak; düzelt; `motor.sh bitir <ad>`; `kontrol/kareler.jpg` ve
   `kontrol/kanca-3sn.jpg`'yi görsel açabilen araçla incele (Claude Code: Read; Codex/Antigravity: görüntüyü aç) (kırpma özneyi kesiyor mu, altyazı okunuyor mu, künye görünüyor mu).
5. Kancalar: `kanca/A|B|C/cekimler.json` (aynı ayar, kendi anlatım/kelime dosyası) → her biri ayrı mp4.
