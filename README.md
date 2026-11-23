# PushPull

Birden fazla Git reposunu (`15-20+`) tek ekrandan, AI kod ajanlarına bağımlı kalmadan güvenli şekilde yönetmek ve senkronize etmek için **Python + PySide6** tabanlı masaüstü uygulaması.

## Temel Özellikler
- Dikey kaydırmalı, kullanıcı tarafından yukarı/aşağı sıralanabilir ve eklenebilir repo listesi
- Satır bazlı işlem seçimi: `Fetch` · `Analyze (Durum/Ahead-Behind)` · `Stash` · `Pull` · `Commit` · `Push`
- Satır içi Accordion (açılır log çekmecesi) ile her repo için bağımsız çıktı ve hata takibi
- `Commit` kutusu seçildiğinde açılan balon/metin alanı (boş bırakılırsa tarih-saat ile otomatik commit)
- Yerel sunucu (`localhost`) gerektirmeyen doğrudan masaüstü penceresi
- `TR / EN / AR` (RTL destekli) çoklu dil arayüzü

## Dokümanlar
- [AGENTS.md](AGENTS.md) — AI kod ajanları için bağlayıcı çalışma protokolü ve mimari kurallar
- [tasks.md](tasks.md) — Adım adım, token-ekonomik geliştirme görev listesi
