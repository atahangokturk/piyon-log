# Piyon Log

Tek bir Windows makinesinde **tamamen lokal (offline)** çalışan kişisel aktivite
günlüğü aracı. Gün içinde bilgisayarda ne yaptığınızı sessizce kaydeder, akşam
okunabilir bir markdown rapor sunar. Bir "ikinci beyin" / quantified-self
aracıdır — ActivityWatch, ManicTime, RescueTime mantığında ama tamamen
kişisel ve kapalı devre.

**Temel ilke:** Hiçbir veri internete gönderilmez. Tüm kayıt ve işleme bu
makinede kalır. Rapor üretimi de varsayılan olarak lokaldir (şablon tabanlı);
isteğe bağlı olarak yerel bir Ollama modeli de kullanılabilir (yine
`localhost` üzerinden, dışarı çıkmaz).

## Kurulum

```powershell
python -m pip install -r requirements.txt
```

Python 3.11+ gereklidir.

## Kullanım

### 1. Uygulamayı başlatma

```powershell
python piyon_log.py
```

Bu, **tek ve önerilen** giriş noktasıdır: toplayıcıyı arka planda başlatır
VE canlı paneli aynı anda açar — tek uygulama, tek pencere. Zaten
çalışıyorsa ikinci bir kopya açmaz, sadece panel penceresini gösterir.

Konsol penceresi olmadan (sessiz, pencere de açmadan — otomatik başlatma
için) çalıştırmak istersen:

```powershell
pythonw.exe piyon_log.py --background
```

Toplayıcıyı veya paneli **ayrı ayrı** çalıştırmak isteyenler için
`main.py` (sadece toplayıcı) ve `ui_server.py` (sadece panel) hâlâ
bağımsız olarak kullanılabilir.

### 2. Günlük rapor alma

Akşam, o güne kadar toplanan verilerden bir rapor üretmek için:

```powershell
python digest.py             # bugünün raporu
python digest.py 2026-08-28  # belirli bir günün raporu
```

Rapor hem terminale yazdırılır hem de `reports/GÜN.md` olarak kaydedilir.

### 3. Canlı panel (web arayüzü)

Sunucu logu tarzında ama temiz, minimal ve **kart tabanlı** bir panel;
`python piyon_log.py` ile birlikte otomatik açılır (bağımsız çalıştırmak
isterseniz `python ui_server.py`).

Panel üstte günün özet kartlarını (toplam süre, oturum sayısı, en çok
zaman ayrılan proje/uygulama) gösterir. Altta ise her oturum ayrı bir
kart olarak akar: saat, uygulama rozeti, proje etiketi, süre — ve varsa
**o oturumda yazdığınız metin de kartın içinde görünür** (parola
yöneticileri ve dışlanan pencereler hariç, bkz. "Nasıl çalışır?"). Kartlar
her ~2.5 saniyede bir güncellenir. Ek bir bağımlılık gerektirmez (yalnızca
Python standart kütüphanesi), veri dışarı çıkmaz.

"AKIŞ" başlığının yanındaki **‹ ›** okları ile geçmiş günlere gidip
gelebilirsiniz; geleceğe gidilemez. "Bugün"ü izlerken gece yarısı geçilirse
panel kendini otomatik olarak yeni güne günceller (panel açık unutulsa
bile).

Proje dağılımı bir **çubuk grafik** ile de gösterilir, üstte bir de
**odak skoru** kartı vardır (`config.FOCUS_MIN_SESSION_S`'den — varsayılan
3 dakika — uzun süren kesintisiz oturumların toplam süreye oranı). "AKIŞ"
satırındaki **".md indir"** butonu o günün raporunu markdown dosyası
olarak indirir; **"PDF"** butonu ise yazdırmaya hazır, temiz bir belge
açar — tarayıcının "Yazıcı" menüsünden "PDF olarak kaydet" seçeneğiyle PDF
alabilirsiniz (ek bir kütüphane kurulmaz, Windows'un kendi PDF yazıcısı
kullanılır).

Üst çubuktaki arama kutusuyla **tüm geçmiş günlerde** başlık/metin
içinde tam metin arama yapabilirsiniz. Her kartın proje etiketine
tıklayarak (veya etiket yoksa "+ proje" yazısına) o oturumun projesini
elle değiştirebilirsiniz — otomatik eşleşme yanlış olduğunda düzeltmek
içindir.

**"AKIŞ" / "PROJELER" / "UYGULAMALAR" sekmeleri:** Projeler ve Uygulamalar
sekmeleri, her projeye/uygulamaya şimdiye kadar ayrılan toplam süreyi,
oturum sayısını ve ilk/son görülme tarihini gösterir. Birine tıklayınca
**tüm zamanlardaki** kayıtları listeler.

**Proje yönetimi:** "Projeler" sekmesinde, üstte bir "anahtar kelime →
proje adı" ekleme formu ve mevcut kuralların listesi (her birinin yanında
silme (✕) düğmesi) bulunur. Artık projeler kod düzenlemeden, doğrudan
panelden eklenip çıkarılabilir; kurallar veritabanında tutulur
(`project_keywords` tablosu).

Sayfanın üstünde, son 30 günün toplam sürelerini gösteren küçük bir
**ısı haritası** (koyu → daha yoğun gün) da vardır.

**Nasıl açılır?** İki yol var:

- **Tarayıcıda adres olarak:** sunucu `http://127.0.0.1:8420` adresinde
  çalışır, herhangi bir tarayıcıda bu adresi ziyaret edebilirsiniz.
- **Program gibi (önerilen):** aşağıdaki "Masaüstü kısayolları" adımını
  kurarsanız, panel Edge'in "uygulama modunda" (adres çubuğu, sekmeler
  yok — sıradan bir program penceresi gibi) açılır; IP/adres yazmanıza
  gerek kalmaz. Panel zaten açıksa, tekrar başlatmak ikinci bir sunucu
  açmaz, sadece pencereyi öne getirir.

### 4. Masaüstü kısayolları (bir program gibi kullanmak için)

```powershell
python install_desktop_icons.py             # kurar
python install_desktop_icons.py --status    # kurulu mu kontrol eder
python install_desktop_icons.py --uninstall # kaldırır
```

Masaüstüne, `piyon-log.png`'den üretilen özel bir simgeyle (bkz.
`piyon-log.ico`) iki kısayol ekler:

- **"Piyon Log"** — toplayıcıyı VE canlı paneli birlikte başlatır (çift
  tıklamak yeterli). Zaten çalışıyorsa ikinci bir kopya açmaz, sadece
  pencereyi gösterir.
- **"Piyon Log Rapor Al"** — o güne kadar toplanan verilerden anında bir
  rapor üretir, ekranda gösterir ve `reports/GÜN.md` olarak kaydeder.

Artık terminal açmadan, sıradan bir Windows programı gibi simgelere çift
tıklayarak kullanabilirsiniz.

### 5. Bilgisayar açılınca otomatik başlatma

```powershell
python install_startup.py             # kurar (Başlangıç klasörüne kısayol ekler)
python install_startup.py --status    # kurulu mu kontrol eder
python install_startup.py --uninstall # kaldırır
```

Kurulum, Windows "Başlangıç" (`shell:startup`) klasörüne `pythonw.exe`
ile `piyon_log.py --background`'ı konsolsuz VE penceresiz başlatan bir
kısayol ekler. Böylece oturum açılışında toplayıcı + panel sessizce
çalışmaya başlar (panel penceresi açılmaz); görmek isterseniz masaüstündeki
"Piyon Log" simgesine tıklamanız yeterli — uygulama zaten çalıştığı için
anında pencereyi açar.

## `.exe` olarak derleme (Python kurmadan dağıtmak için)

ActivityWatch gibi araçların yaptığının aynısı: [PyInstaller](https://pyinstaller.org)
ile Python'u ve tüm bağımlılıkları tek bir `.exe` içine gömebilirsiniz —
kullanan kişinin Python kurmasına gerek kalmaz.

```powershell
python -m pip install pyinstaller
pyinstaller --onefile --windowed --name PiyonLog --icon piyon-log.ico --add-data "web;web" piyon_log.py
```

Sonuç `dist/PiyonLog.exe` — tek dosya, çift tıklayınca toplayıcıyı ve
paneli birlikte başlatır. Kendi veri/rapor klasörünü `.exe`'nin
bulunduğu dizinin yanında oluşturur (bkz. `config.py`'deki
`sys.frozen` kontrolü). `PiyonLog.spec` dosyası aynı build tarifini
saklar; sadece `pyinstaller PiyonLog.spec` çalıştırarak da
tekrarlayabilirsiniz.

Gerçek bir kurulum dosyası (`PiyonLogSetup.exe` — Program Files'a
kopyalayan, Başlangıç/Masaüstü kısayollarını kendisi oluşturan,
kaldırma seçeneği sunan) için üzerine [Inno Setup](https://jrsoftware.org/isinfo.php)
(ücretsiz) eklenmesi önerilir; bu depoda henüz bir Inno Setup betiği yok.

Kod imzalama için $200-400/yıl ödemeniz şart değil: açık kaynak
projelere ücretsiz sertifika veren [SignPath.io](https://signpath.io)
gibi seçenekler var. İmzalamadan dağıtırsanız Windows SmartScreen bir
uyarı gösterir, kullanıcı "yine de çalıştır" der — küçük açık kaynak
araçların çoğu böyle başlar.

## GitHub'da açık kaynak olarak yayınlama

Depo zaten hazır: `git init` yapıldı, ilk commit atıldı, `.gitignore`
kişisel verinizi (`data/`, `reports/`) asla commit'e dahil etmeyecek
şekilde ayarlandı, `LICENSE` (MIT) eklendi. Kalan adımlar:

1. [github.com/new](https://github.com/new) adresinden **boş** bir
   repo oluşturun (README/license eklemeden — zaten var).
2. Terminalde:
   ```powershell
   git remote add origin https://github.com/KULLANICI_ADINIZ/piyon-log.git
   git branch -M main
   git push -u origin main
   ```
3. Derlenmiş `.exe`'yi commit etmeyin (deponun şişmesine yol açar);
   bunun yerine GitHub'ın "Releases" özelliğinden ayrı bir sürüm olarak
   yükleyin, ya da Gumroad/Lemon Squeezy üzerinden "istediğini öde" ($0
   dahil) şeklinde dağıtın.

`git commit` her yaptığınızda `data/` ve `reports/` otomatik hariç
tutulur — yine de göndermeden önce `git status` ile neyin ekleneceğini
kontrol etmek iyi bir alışkanlıktır.

## `data/log.db` hakkında

Bu, tüm oturum kayıtlarınızın tutulduğu tek SQLite dosyasıdır. **Program
hiçbir zaman, hiçbir koşulda kendiliğinden bu dosyadaki kayıtları silmez**
— ne toplayıcıda (`collector.py`), ne panelde (`ui_server.py`), ne de
raporlamada (`digest.py`) böyle bir kod yoktur. Toplayıcı çalıştığı sürece
veriler sadece birikir. Dosyayı silmenin tek yolu, siz kendiniz elle
silmenizdir (ya da geliştirme sırasında test verisi temizlemek için
elle çalıştırılan komutlarla — geliştirme tamamlandı, bundan sonra
dokunulmuyor).

## Windows Defender istisnası

Piyon Log, aktivite takibi için global bir klavye dinleyicisi kullanır.
Bu, teknik olarak bir "keylogger" davranışıdır ve Windows Defender veya
başka bir antivirüs bunu şüpheli olarak işaretleyebilir. **Bu beklenen bir
durumdur** — araç yalnızca kendi makinenizde, kendiniz için çalışır ve
hiçbir veri dışarı gönderilmez.

Uyarı almamak için proje klasörünü Defender istisnalarına ekleyebilirsiniz:

1. Windows Ayarlar → Gizlilik ve Güvenlik → Windows Güvenliği → Virüs ve
   tehdit koruması → Ayarları yönet → Dışlamalar → Dışlama ekle.
2. "Klasör" seçin ve `piyon-log` proje klasörünün tam yolunu gösterin.

## Nasıl çalışır?

- **Oturum (session):** Aynı pencerede kesintisiz geçirilen süre. Aktif
  pencere (uygulama) değiştiğinde veya ~90 saniye hareketsizlik olduğunda
  oturum kapanır ve veritabanına yazılır.
- **Aşırı parçalanmayı önleme:** Bazı uygulamalar pencere başlığına oynak
  bilgi ekler (tarayıcıda sekme sayısı, okunmamış e-posta sayacı gibi).
  Aynı uygulamada başlık `config.MIN_TITLE_CHANGE_S` (varsayılan 5) saniyeden
  daha sık değişirse oturum bölünmez, devam eder. Ayrıca hareketsizlik
  yüzünden bir oturum kapatıldıktan sonra, siz gerçekten bir şey yapana
  kadar aynı pencerede tekrar tekrar boş oturum açılmaz.
- **Fare varlık algılama:** Fare hareketi/tıklaması hiçbir konum veya
  içerik kaydetmez; sadece "kullanıcı burada" sinyali olarak boşta kalma
  sayacını sıfırlar. Böylece sadece mouse ile okuduğunuz bir sayfa,
  klavyeye dokunmadığınız için yanlışlıkla "boşta" sayılmaz.
- **Dışlama listesi (birincil koruma):** `config.py` içindeki
  `EXCLUDED_APPS` ve `EXCLUDED_TITLE_KEYWORDS` listelerine giren
  uygulama/pencerelerde (parola yöneticileri, bankacılık vb.) klavye metni
  **hiç toplanmaz**, sadece süre ve uygulama adı kaydedilir.
- **Redaksiyon (ikincil koruma):** Toplanan metin diske yazılmadan önce
  `redact.py` üzerinden geçer; e-posta, IBAN, kart numarası ve 6+ haneli
  sayı dizileri maskelenir.
- **Proje eşleştirme:** Pencere başlığı `config.PROJECT_MAP` içindeki
  anahtar kelimelerle eşleşirse oturum ilgili Piyon Co. projesine
  (Nomad Box, Köpek Atık Toplama Aparatı, SpaBook, ...) atanır.

## Ayarları özelleştirme (`config.py`)

- `EXCLUDED_APPS` / `EXCLUDED_TITLE_KEYWORDS`: kendi hassas
  uygulamalarınızı/pencerelerinizi mutlaka buraya ekleyin.
- `PROJECT_MAP`: yalnızca ilk kurulumda veritabanına kopyalanan
  varsayılan proje kuralları. Kalıcı yönetim için panelin "Projeler"
  sekmesini kullanın.
- `POLL_INTERVAL_S` / `IDLE_TIMEOUT_S`: yoklama sıklığı ve boşta kalma
  eşiği.
- `USE_OLLAMA`: `True` yapılırsa `digest.py` raporu zenginleştirmek için
  yerel bir Ollama modeline gönderir.

## Zengin rapor için Ollama (opsiyonel)

Diskte yer açıldığında, akşam raporunu daha akıcı ve yorumlu bir dille
almak için:

1. [Ollama](https://ollama.com) kurun.
2. Bir model indirin: `ollama pull qwen2.5:7b`
3. `config.py` içinde `USE_OLLAMA = True` yapın.
4. `python digest.py` çalıştırın.

Ollama kurulu değilse veya `localhost:11434`'e erişilemiyorsa `digest.py`
otomatik olarak şablon tabanlı rapora düşer; hiçbir şey çökmez.

## Güvenlik ve gizlilik notları

- Tüm veri lokaldir, hiçbir ağ isteği yapılmaz (Ollama hariç, o da yalnızca
  `localhost`'a).
- `data/log.db` hassas veri içerebilir. İleride SQLCipher gibi bir
  çözümle şifrelenmesi düşünülebilir (şu an için opsiyonel, uygulanmadı).
- Dışlama listesi birincil korumadır; redaksiyon kusursuz değildir. Hassas
  metin girdiğiniz uygulamaları `config.py`'ye eklemek, redaksiyona
  güvenmekten daha güvenlidir.

## Proje yapısı

```
piyon-log/
├── piyon_log.py             # BİRLEŞİK giriş noktası (toplayıcı + panel, .exe hedefi)
├── main.py                  # sadece toplayıcı (bağımsız kullanım için)
├── collector.py             # aktif pencere + klavye/fare izleme, oturum mantığı
├── redact.py                # metin sansürleme / temizleme katmanı
├── db.py                    # SQLite şema, yazma/okuma, proje kuralları
├── digest.py                # akşam raporu üretici (şablon + opsiyonel Ollama)
├── ui_server.py             # sadece panel (bağımsız kullanım için) + HTTP API
├── web/                     # panelin HTML/CSS/JS dosyaları (kart tabanlı arayüz)
├── config.py                # tüm ayarlar (frozen/.exe yol çözümü dahil)
├── install_startup.py       # bilgisayar açılışında otomatik başlatma kurulumu
├── install_desktop_icons.py # masaüstü kısayolları (program gibi kullanım)
├── piyon-log.png / .ico     # uygulama simgesi
├── PiyonLog.spec            # PyInstaller build tarifi
├── LICENSE                  # MIT
├── .gitignore                # data/ ve reports/ asla commit edilmez
├── requirements.txt
├── data/
│   └── log.db               # SQLite veritabanı (çalışınca oluşur, git'e girmez)
└── reports/
    └── GÜN.md                # günlük raporlar (git'e girmez)
```
