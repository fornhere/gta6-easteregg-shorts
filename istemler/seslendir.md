# Ajan adımı: SESLENDİR (Epidemic Sound MCP ya da başka bir TTS; çıktı ham.mp3 olmalı)

MCP yoksa: kendi TTS'inle `isler/<ad>/ses/anlatim/ham.mp3` üret ve 3. adımdan devam et.

1. Epidemic Sound MCP'nin `GenerateVoiceover` aracı (araç adı istemciye göre önek alır: Claude Code'da
   `mcp__epidemic-sound__GenerateVoiceover`; Codex ve Antigravity'de sunucu adı + araç adı) voiceId=`ayar.json > seslendir.ses` içindeki varsayılan kimlik, languageCode=en, speed=0.55, text=metin.txt.
   Ölçüm: speed hızı pek değiştirmiyor; yavaşlığın kaynağı cümle arası duraklamalar.
2. `PollVoiceoverGenerationStatus` DONE → `DownloadVoiceover` → URL'yi `curl -o isler/<ad>/ses/anlatim/ham.mp3`.
3. `motor.sh sik <ad>` → duraklamaları 0,22 sn'ye indirir, gerekirse atempo (<= 1,15x) ile 3,5 kelime/sn.
4. `motor.sh zaman <ad>` → `zaman/anlatim.json` kelime zamanları. Altyazıda bozulan sözcükleri
   `ayar.altyazi.birlestir` ile düzelt (ör. ["2","a",".m.","2AM"], ["Port","Gellhorn","Port Gellhorn"]).
5. Müzik/SFX: `SearchRecordings` (vocals=false, enerjik/gerilim) + `SearchSoundEffects`; `DownloadRecording`
   / `DownloadSoundEffect` → `ses/muzik.mp3`, `ses/sfx/*.wav`. Oyun içi radyo müziği kullanma.
   Seçim etiketlere göre yapılır; ajan sesi dinleyemez — kullanıcı dinleyip onaylar.
