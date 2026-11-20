# Ajan adımı: TARA puanlama

Girdi: `kuyruk/TARAMA-<son>.md` ve `.jsonl` (makine kümeleri, kaba puan).
1. Her kümenin örnek başlığına ve açıklamasına bak; aynı easter egg'i anlatan kümeleri birleştir, alakasızları (liste
   videosu, söylenti, fragman analizi, mod) at.
2. ADAYLAR ölçütleriyle 1–5 puan ver: G görsel tuhaflık (ilk karede gösterilebilir mi), M merak ("ne anlama geliyor"),
   K küresel anlaşılırlık (dil/kültür bağımsız), B görüntü bulunabilirliği (>= 2 kaynakta temiz kesit), T tazelik.
   Sürprizbozan (hikâye sonu, karakter ölümü) varsa işaretle; öne çıkarma.
3. Web aramasıyla (Claude Code: WebSearch; Codex ve Antigravity: yerleşik web araması) `ayar.json > tara.haber_siteleri` üzerinde konu adını ara; bulunan haber/wiki sayfasını
   `bin/dogrula.py --ek-kaynak <aday_id>=<url>` ile ekle (bu ikinci bağımsız kaynak sayılır).
4. Reddit RSS/JSON 403 verir (20 Kas); deneme. X gönderilerine erişim yok; X linkleri yalnız haberde geçiyorsa aktarılır.
5. Sonuç: `kuyruk/ADAYLAR-<tarih>.md` (tablo + en iyi 3 gerekçeli). Uydurma yok: bilinmeyen alan "bilinmiyor".
