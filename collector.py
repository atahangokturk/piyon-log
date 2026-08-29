"""
Piyon Log - toplayıcı (collector).

Aktif pencereyi periyodik olarak yoklar ve global klavye olaylarını dinler.
Aktif pencere değiştiğinde veya kullanıcı uzun süre boşta kaldığında mevcut
"oturumu" kapatıp (flush) veritabanına yazar.
"""

import threading
import time
from datetime import datetime

import psutil
import win32gui
import win32process
from pynput import keyboard, mouse

import config
import db
import redact


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_active_window():
    """Aktif pencerenin (uygulama_adi.exe, pencere_basligi) bilgisini döner."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) or ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            app = psutil.Process(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            app = "bilinmeyen.exe"
        return (app, title)
    except Exception:
        return ("bilinmeyen.exe", "")


def is_excluded(active) -> bool:
    """Uygulama veya pencere başlığı dışlama listesine giriyorsa True döner.

    Bu, redaksiyondan ÖNCE gelen birincil korumadır: eşleşirse klavye metni
    hiç toplanmaz.
    """
    app, title = active
    excluded_apps = [a.lower() for a in config.EXCLUDED_APPS]
    if app and app.lower() in excluded_apps:
        return True
    if app and app.lower() in config.SELF_APP_NAMES:
        return True
    if title:
        lowered = title.lower()
        for keyword in config.EXCLUDED_TITLE_KEYWORDS:
            if keyword.lower() in lowered:
                return True
    return False


# Çalışan toplayıcı örneğine, aynı süreç içindeki web sunucusunun "şu an"
# kartı için erişebilmesi amacıyla tutulur (bkz. get_current_state()).
CURRENT_INSTANCE = None


class Collector:
    """Aktif pencere + klavye izlemeyi yürüten ve oturumları veritabanına yazan sınıf."""

    def __init__(self):
        self._lock = threading.Lock()
        self.active = None
        self.buffer = ""
        self.session_start = None
        self.last_activity = time.time()
        self.last_title_change_ts = time.time()
        self.idle_flushed = False
        self.running = False
        self._keyboard_listener = None
        self._mouse_listener = None

    # --- yaşam döngüsü ---

    def start(self):
        global CURRENT_INSTANCE
        db.init_db()
        self.active = get_active_window()
        self.session_start = now_iso()
        self.last_activity = time.time()
        self.last_title_change_ts = time.time()
        self.running = True
        CURRENT_INSTANCE = self

        self._keyboard_listener = keyboard.Listener(on_press=self._on_press)
        self._keyboard_listener.start()

        # Fare hareketi/tıklaması hiçbir koordinat veya içerik kaydetmez;
        # sadece "kullanıcı burada" sinyali olarak boşta kalma sayacını
        # sıfırlar (ör. mouse ile sayfa okurken yanlışlıkla idle sayılmasın).
        self._mouse_listener = mouse.Listener(
            on_move=self._on_mouse_activity, on_click=self._on_mouse_activity
        )
        self._mouse_listener.start()

        print(f"[Piyon Log] Toplayıcı başladı. Aktif pencere: {self.active}")
        try:
            self._poll_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        global CURRENT_INSTANCE
        if not self.running:
            return
        self.running = False
        if self._keyboard_listener is not None:
            self._keyboard_listener.stop()
        if self._mouse_listener is not None:
            self._mouse_listener.stop()
        with self._lock:
            self._flush_locked(self.active)
        if CURRENT_INSTANCE is self:
            CURRENT_INSTANCE = None
        print("[Piyon Log] Toplayıcı durduruldu.")

    def get_current_state(self):
        """Şu anki (henüz kapanmamış) oturumun anlık görüntüsünü döner."""
        with self._lock:
            if not self.running or self.active is None:
                return None
            app, title = self.active
            visible_title = "" if is_excluded(self.active) else title
            safe_title = redact.redact(visible_title) if visible_title else ""
            return {
                "app": app,
                "title": safe_title,
                "project": db.match_project(title) if title else None,
                "start_ts": self.session_start,
            }

    # --- iç mantık ---

    def _poll_loop(self):
        while self.running:
            time.sleep(config.POLL_INTERVAL_S)
            with self._lock:
                current = get_active_window()
                changed = self._handle_window_change(current)
                if changed:
                    continue

                idle_for = time.time() - self.last_activity
                if idle_for >= config.IDLE_TIMEOUT_S and not self.idle_flushed:
                    # Oturumu, gerçek son etkileşim anında bitmiş say (idle
                    # süresini oturum süresine eklemeden).
                    self._flush_locked(self.active, end_ts=self._iso(self.last_activity))
                    self.idle_flushed = True

    def _on_press(self, key):
        with self._lock:
            self.last_activity = time.time()
            self.idle_flushed = False
            current = get_active_window()
            self._handle_window_change(current)

            if not is_excluded(self.active):
                self.buffer = self._apply_key(self.buffer, key)

    def _on_mouse_activity(self, *_args):
        # Kilidi her fare olayında almamak için kaba bir hız sınırlama:
        # zaten yakın zamanda etkinlik görülmüşse tekrar kilitlemeye gerek yok.
        if time.time() - self.last_activity < 1:
            return
        with self._lock:
            self.last_activity = time.time()
            self.idle_flushed = False

    def _handle_window_change(self, current) -> bool:
        """Aktif pencere değişikliğini değerlendirir.

        Uygulama değiştiyse oturumu kapatıp yeni oturum başlatır (True döner).
        Sadece başlık değiştiyse ve bu değişiklik MIN_TITLE_CHANGE_S içinde
        gerçekleştiyse (ör. sekme sayısı/okunmamış sayaç gibi oynak
        başlıklar), oturumu bölmeden başlığı günceller (False döner).
        Hiçbir değişiklik yoksa False döner.

        Her zaman self._lock tutulurken çağrılmalıdır.
        """
        if current == self.active:
            return False

        if current[0] != self.active[0]:
            self._flush_locked(current)
            return True

        # Aynı uygulama, sadece başlık değişti.
        now = time.time()
        if now - self.last_title_change_ts < config.MIN_TITLE_CHANGE_S:
            self.active = current
            self.last_title_change_ts = now
            return False

        self._flush_locked(current)
        return True

    @staticmethod
    def _apply_key(buffer: str, key) -> str:
        try:
            if key == keyboard.Key.backspace:
                return buffer[:-1]
            if key == keyboard.Key.enter:
                return buffer + "\n"
            if key == keyboard.Key.space:
                return buffer + " "
            if key == keyboard.Key.tab:
                return buffer + " "
            if hasattr(key, "char") and key.char is not None:
                return buffer + key.char
            # Ctrl, Alt, Shift, ok tuşları vb. diğer özel tuşlar buffer'a eklenmez.
            return buffer
        except Exception:
            return buffer

    @staticmethod
    def _iso(epoch_s: float) -> str:
        return datetime.fromtimestamp(epoch_s).isoformat(timespec="seconds")

    def _flush_locked(self, new_active, end_ts: str = None):
        """Mevcut oturumu kapatıp veritabanına yazar, yeni pencere için sıfırlar.

        Bu metod her zaman self._lock tutulurken çağrılmalıdır.
        """
        end_ts = end_ts or now_iso()
        start_dt = datetime.fromisoformat(self.session_start)
        end_dt = datetime.fromisoformat(end_ts)
        duration_s = int((end_dt - start_dt).total_seconds())

        is_self = self.active is not None and self.active[0].lower() in config.SELF_APP_NAMES

        if duration_s >= 1 and self.active is not None and not is_self:
            app, title = self.active
            safe_title = redact.redact(title)
            safe_text = redact.redact(self.buffer) if self.buffer else ""
            project = db.match_project(title)

            db.insert_session(
                {
                    "start_ts": self.session_start,
                    "end_ts": end_ts,
                    "duration_s": duration_s,
                    "app": app,
                    "title": safe_title,
                    "project": project,
                    "text": safe_text,
                }
            )

        self.active = new_active
        self.buffer = ""
        self.session_start = now_iso()
        self.last_title_change_ts = time.time()
        self.idle_flushed = False


def get_current_state():
    """Aynı süreçte çalışan bir toplayıcı varsa canlı durumunu döner, yoksa None."""
    if CURRENT_INSTANCE is None:
        return None
    return CURRENT_INSTANCE.get_current_state()
