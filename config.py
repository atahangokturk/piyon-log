"""
Piyon Log - merkezi ayar dosyası.

Tüm kişiselleştirme (dışlama listeleri, proje eşleştirme, zamanlama, rapor
modeli ayarları) burada toplanır. Diğer modüller ayar için buraya bakar.
"""

import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # PyInstaller ile paketlenmiş .exe içinde çalışıyor.
    # APP_DIR: .exe'nin yanı - veri/rapor gibi yazılabilir şeyler buraya.
    # BASE_DIR: pakete gömülü salt-okunur varlıklar (web/ klasörü vb.).
    APP_DIR = Path(sys.executable).parent
    BASE_DIR = Path(sys._MEIPASS)
else:
    APP_DIR = Path(__file__).parent
    BASE_DIR = APP_DIR

DB_PATH = APP_DIR / "data" / "log.db"
REPORTS_DIR = APP_DIR / "reports"

# --- Metin toplanmayacak uygulamalar (birincil koruma) ---
# Buradaki uygulamalar aktifken klavye metni HİÇ toplanmaz; sadece süre ve
# (redakte edilmiş) başlık kaydedilir.
EXCLUDED_APPS = [
    "bitwarden.exe",
    "1password.exe",
    "keepass.exe",
    "keepassxc.exe",
]

# Piyon Log'un KENDİ penceresi: bu uygulama hiç oturum olarak kaydedilmez
# (ne süre ne metin). Kendi izleyicinize bakma süreniz gerçek aktivite
# sayılmaz; kaydedilirse "Piyon Log" diye tuhaf, kendine referans veren
# bir proje/uygulama olarak listelere karışır.
SELF_APP_NAMES = ["piyonlog.exe"]

# --- Başlığında bu kelimeler geçen pencerelerde metin toplama ---
EXCLUDED_TITLE_KEYWORDS = [
    "banka",
    "bank",
    "ödeme",
    "odeme",
    "payment",
    "login",
    "giriş",
    "giris",
    "şifre",
    "sifre",
    "password",
]

# --- Yoklama ve idle ayarları ---
POLL_INTERVAL_S = 3      # aktif pencere kaç saniyede bir kontrol edilsin
IDLE_TIMEOUT_S = 90      # bu süre hareketsizlik sonrası oturum kapatılır (flush)

# Aynı uygulamada pencere başlığı bu süreden daha sık değişirse (ör. tarayıcı
# başlığındaki sekme sayısı, okunmamış e-posta sayacı gibi oynak kısımlar,
# ya da sayfa aynı kalsa da başlığın ufak titremesi yüzünden), oturum
# bölünmez; mevcut oturuma devam edilir. Log'un aşırı parçalanmasını
# (aynı sayfada saniyede bir yeni kayıt açılmasını) önler.
MIN_TITLE_CHANGE_S = 5

# Odak skoru: bu süreden (saniye) uzun süren oturumlar "odaklı çalışma"
# sayılır; daha kısaları "dağınık/geçiş" olarak değerlendirilir.
FOCUS_MIN_SESSION_S = 180

# Derin çalışma: bu süreden uzun, gerçekten kesintisiz bloklar. Odak
# skorundan daha katı bir eşiktir.
DEEP_WORK_MIN_SESSION_S = 900

# --- Piyon proje eşleştirme (yalnızca ilk kurulum tohumu) ---
# Veritabanı ilk kez oluşturulurken bu eşleşmeler `project_keywords`
# tablosuna kopyalanır. Sonrasında projeler artık buradan değil, panelin
# "Projeler" sekmesinden yönetilir (db.add_project_keyword /
# db.delete_project_keyword); bu sözlük yalnızca ilk varsayılanlar içindir.
PROJECT_MAP = {
    "nomad": "Nomad Box",
    "köpek": "Köpek Atık Toplama Aparatı",
    "kopek": "Köpek Atık Toplama Aparatı",
    "dog": "Köpek Atık Toplama Aparatı",
    "spabook": "SpaBook",
    "piyon": "Piyon Co.",
}


# --- Rapor modeli ---
USE_OLLAMA = False  # disk açılınca True yap
OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_URL = "http://localhost:11434/api/generate"

# --- Ek özel redaksiyon desenleri (regex string listesi) ---
CUSTOM_REDACT_PATTERNS: list[str] = []
