# PushPull — Görev Listesi (Tasks)

> **Ajan Talimatı (`Eko Tek Madde`):** Her oturumda yalnızca sıradaki veya istenen **tek bir maddeyi** yap, yerel olarak doğrula ve `[x]` olarak işaretle.

## Faz 1: Proje İskeleti ve Ortam
- [x] **T-01:** `requirements.txt` (`PySide6`) ve sanal ortam (`.venv`) kurulumunu oluştur ve import testini doğrula.
- [x] **T-02:** Temel klasör yapısını oluştur (`src/app.py`, `src/models/`, `src/services/`, `src/ui/`).
- [x] **T-03:** `src/app.py` içinde boş ana `QMainWindow` penceresini aç ve kapandığını doğrula.

## Faz 2: Veri Modeli, Kalıcılık ve Git Motoru
- [x] **T-04:** `RepoItem` ve `RepoRunResult` veri modellerini (`dataclass`) tanımla (`name`, `path`, `order`, `status`, `logs`).
- [x] **T-05:** `repos.json` okuma/yazma servisini (`config_store.py`) yaz; sıralama ve ekleme/silmeyi kaydet.
- [x] **T-06:** `git_runner.py` temel `subprocess` sarmalayıcısını yaz (`CREATE_NO_WINDOW`, UTF-8 çıktı, exit code yakalama).
- [x] **T-07:** `git_ops.py` içine `fetch`, `analyze` (ahead/behind + dirty file count), `stash`, `pull`, `commit` (boşsa `YYYY-MM-DD HH:MM`), `push` fonksiyonlarını ekle.
- [x] **T-08:** `QThread` / `QRunnable` tabanlı asenkron işçi (`RepoWorker`) yaz; satır bazlı adım sinyalleri (`started`, `step_done`, `finished`, `error`) yayınlasın.

## Faz 3: Ana Arayüz, Tablo ve Accordion
- [x] **T-09:** Üst araç çubuğunu oluştur (`+ Repo Ekle`, `Tümünü Fetch Et`, `Seçilileri Çalıştır`).
- [x] **T-10:** Dikey kaydırmalı repo listesi konteynerini ve tek repo satır bileşenini (`RepoRowWidget`) oluştur.
- [x] **T-11:** Satır içi yukarı/aşağı (`▲` / `▼`) sıralama ve repo silme aksiyonlarını `repos.json` ile bağla.
- [x] **T-12:** Sütun başlıklarını (`Repo`, `Fetch`, `Analyze`, `Stash`, `Pull`, `Commit`, `Push`, `Durum`) ve satır checkbox hizalamasını tamamla.
- [x] **T-13:** Satır içi **Accordion** log çekmecesini ekle; durum rozetine/satıra tıklanınca sadece o reponun çıktısını aç/kapat.

## Faz 4: Commit Balonu ve Güvenli İşlem Zinciri
- [x] **T-14:** `Commit` checkbox'ı işaretlendiğinde açılan balon/satır içi commit mesaj kutusunu ekle (boşsa otomatik tarih-saat).
- [x] **T-15:** `Seçilileri Çalıştır` zincirini bağla: `Fetch -> Analyze -> Stash -> Pull -> Commit -> Push`; hata olursa kalan adımları durdur ve accordion'u otomatik aç.
- [x] **T-16:** Kirli çalışma ağacı (`dirty tree`) varken `Stash` seçilmeden `Pull` istenirse güvenlik uyarısı/engeli ekle.

## Faz 5: Doğrulama (Tek Dil: TR)
- [~] **T-17:** ~~`src/i18n/` altında `tr.json`, `en.json`, `ar.json` sözlüklerini ve anlık dil değiştirme yöneticisini oluştur.~~ *(Kullanıcı talebiyle kapsam dışı)*
- [~] **T-18:** ~~`AR` seçildiğinde `QApplication.setLayoutDirection(Qt.RightToLeft)` ve mantıksal hizalamayı doğrula.~~ *(Kullanıcı talebiyle kapsam dışı)*
- [x] **T-19:** Gerçek git repoları üzerinde uçtan uca manuel doğrulama yap (`Fetch`, `Analyze`, `Commit`, `Push`, Accordion, `repos.json` kalıcılığı).
