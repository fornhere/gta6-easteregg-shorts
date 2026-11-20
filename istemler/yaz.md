# Ajan adımı: YAZ (hızlı Shorts kalıbı, İngilizce, 25–45 sn)

Kurallar: `README.md` "Kalıcı kurallar" tablosu.
- Süre 25–45 sn; 3,3–3,7 kelime/sn => ~90–150 kelime. Cümle 6–14 kelime, araya 2–5 kelimelik vuruşlar.
- KANCA (0–3,5 sn) — KALICI KURAL: B kalıbı.
  İlk cümle "There's a/an <tuhaf şey> in GTA 6, …" biçiminde; "GTA 6" ilk cümlede ZORUNLU (kontrol.py düşürür).
  Örnek: "There's a UFO in GTA 6, and it only shows up after 2 AM." / "There's a car in GTA 6 with a license plate that says HAD YOU."
  İlk karede o tuhaf şey görünür. Soru cümlesiyle açma.
- Konu adı (`ayar.konu`, ör. "UFO", "PAUL WALKER'S CAR") üst başlık bandına "<KONU> IN GTA 6?" olarak otomatik gider.
- Süre <= 59 sn (telif kuralı; kontrol düşürür), hedef 25–45 sn.
- Kaynaklar çelişirse (ör. "Pay 'n' Spray'de sizin olur" vs "olmuyor") o iddiayı metne koyma.
- Sıra: KANCA → NEREDE/NASIL → 2–3 adım tırmanma → TERS KÖŞE / AÇIKLAMA ("ne anlama geliyor": gönderme, gerçek karşılık)
  → SON (baştaki soruyu kapatan somut vuruş). Kahraman: "you" (izleyici).
- Yalnız doğrulanmış bilgi. `metin.md`'ye "iddia → dayanak" tablosu yaz (kaynak + zaman damgası). Dayanaksız
  genelleme ("only", "nobody knows", "Rockstar never…") yazma ya da yumuşat.
- Çıktı: `isler/<ad>/metin.md` + düz metin `metin.txt` (TTS'e giden). Ayrıca 3 kanca varyantı (A/B/C) yaz.
