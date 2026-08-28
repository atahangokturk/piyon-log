"""
Piyon Log - birleşik giriş noktası.

Toplayıcıyı arka plan iş parçacığında, canlı web panelini de aynı süreç
içinde başlatır — ve paneli tarayıcıda değil, **kendi programımıza ait
gerçek bir pencerede** (pywebview + WebView2) gösterir. Böylece görev
çubuğunda Edge'in değil, Piyon Log'un kendi simgesi görünür. `.exe`
paketlemesi (PyInstaller) bu dosyayı hedef alır.

Tek örnek kilidi hem toplayıcıyı hem paneli kapsar: uygulama zaten
çalışıyorsa ikinci bir kopya açmaz, sadece mevcut pencereyi öne getirir.

Kullanım:
    python piyon_log.py
    -> Toplayıcı arka planda başlar, panel kendi penceresinde açılır.
    python piyon_log.py --background
    -> Pencere açmadan sessizce başlar (bilgisayar açılışı için).
"""

import os
import sys
import threading
import time
from http.server import ThreadingHTTPServer

import psutil
import win32con
import win32gui

import config
import db
import ui_server
from collector import Collector

LOCK_PATH = config.DB_PATH.parent / "app.lock"
WINDOW_TITLE = "Piyon Log"


def _acquire_lock() -> bool:
    """Uygulamanın aynı anda birden fazla kopyasının çalışmasını önler."""
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists():
        try:
            pid = int(LOCK_PATH.read_text().strip())
            if psutil.pid_exists(pid):
                return False
        except (ValueError, OSError):
            pass
    LOCK_PATH.write_text(str(os.getpid()))
    return True


def _release_lock():
    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


def _run_collector():
    Collector().start()


def _focus_existing_window() -> bool:
    """Zaten açık bir Piyon Log penceresi varsa öne getirir."""
    try:
        hwnd = win32gui.FindWindow(None, WINDOW_TITLE)
        if not hwnd:
            return False
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    url = f"http://{ui_server.HOST}:{ui_server.PORT}/"
    background = "--background" in sys.argv  # bilgisayar açılışında sessizce başlamak için

    if not _acquire_lock():
        print("[Piyon Log] Uygulama zaten çalışıyor, pencere öne getiriliyor.")
        if not _focus_existing_window():
            # Pencere bulunamadıysa (ör. arka plan modunda çalışıyordu) yedek olarak
            # tarayıcıda aç.
            ui_server.open_app_window(url)
        return

    try:
        threading.Thread(target=_run_collector, daemon=True).start()

        db.init_db()
        server = ThreadingHTTPServer((ui_server.HOST, ui_server.PORT), ui_server.PiyonLogHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"[Piyon Log] Uygulama çalışıyor: {url}")

        if background:
            print("[Piyon Log] Arka planda başlatıldı, pencere açılmadı.")
            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                pass
        else:
            # pywebview'i sadece pencere açılacaksa içe aktarıyoruz; arka plan
            # modunda gereksiz GUI arka ucu başlatma maliyetinden kaçınır.
            import webview

            webview.create_window(
                WINDOW_TITLE, url, width=1180, height=760, min_size=(760, 480)
            )
            webview.start()

        server.shutdown()
    finally:
        _release_lock()
        print("[Piyon Log] Uygulama durduruldu.")


if __name__ == "__main__":
    main()
