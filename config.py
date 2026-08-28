"""
Piyon Log - merkezi ayar dosyası.

Tüm kişiselleştirme (dışlama listeleri, proje eşleştirme, zamanlama, rapor
modeli ayarları) burada toplanır. Diğer modüller ayar için buraya bakar.
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "log.db"
REPORTS_DIR = BASE_DIR / "reports"

# --- Metin toplanmayacak uygulamalar (birincil koruma) ---
# Buradaki uygulamalar aktifken klavye metni HİÇ toplanmaz; sadece süre ve
# (redakte edilmiş) başlık kaydedilir.
EXCLUDED_APPS = [
    "bitwarden.exe",
    "1password.exe",
    "keepass.exe",
    "keepassxc.exe",
]

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
