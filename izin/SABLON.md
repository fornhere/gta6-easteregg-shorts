# Klip sahibinden izin isteme (şablon) — GÖNDERME İŞİ KULLANICININDIR

Motor mesaj göndermez. `bin/izin.py mesaj <iş>` her kaynak için doldurulmuş metni basar; kullanıcı DM/e-posta
ile kendisi gönderir, sonra `bin/izin.py ekle ...` ile kaydeder. Kanal: YouTube "Hakkında" iş e-postası, X DM,
Reddit sohbet. Kısa, kibar, kanıtlanabilir: yanıt ekran görüntüsü olarak saklanır.

## DM (kısa)

Hi {kanal}! Great find on the GTA 6 {konu} easter egg. I make GTA 6 easter egg Shorts (monetized channel).
Could I use 2-4 second clips from your video ({url}) with an on-screen credit "clip: {etiket}" and a link in the
description? A simple "yes" here works as permission. Totally fine if not. Thanks!

## E-posta

Subject: Permission request: 2-4 sec clips from your GTA 6 {konu} video

Hi {kanal},

I loved your video on the GTA 6 {konu} easter egg ({url}). I run a YouTube Shorts channel that explains GTA 6
easter eggs with my own narration, captions and on-screen analysis. The channel is monetized.

May I use a few short excerpts (2-4 seconds each, muted) from your video? You would be credited on screen
("clip: {etiket}") and linked in the description and pinned comment. A reply with "yes" is enough as written
permission, and I will remove the clips any time you ask.

Thank you,
{imza}

## Kayıt

`izin/izinler.jsonl` satırı: {"kanal", "etiket", "url", "is", "istek_tarihi", "kanal_turu" (dm/e-posta), "cevap"
(null | "evet" | "hayir"), "cevap_tarihi", "kanit" (ekran görüntüsü yolu)}.
