"""
Piyon Log - birleşik giriş noktası.

Toplayıcıyı arka plan iş parçacığında, canlı web panelini aynı süreç
içinde ana iş parçacığında başlatır — tek pencere, tek uygulama. `.exe`
paketlemesi (PyInstaller) bu dosyayı hedef alır.

Tek örnek kilidi hem toplayıcıyı hem paneli kapsar: uygulama zaten
çalışıyorsa ikinci bir kopya açmaz, sadece panel penceresini gösterir.

Kullanım:
    python piyon_log.py
    -> Toplayıcı arka planda başlar, panel http://127.0.0.1:8420 adresinde
       bir uygulama penceresinde açılır.
"""

import os
import sys
import threading
from http.server import ThreadingHTTPServer

import psutil

import config
import db
import ui_server
from collector import Collector

LOCK_PATH = config.DB_PATH.parent / "app.lock"


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


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    url = f"http://{ui_server.HOST}:{ui_server.PORT}/"
    background = "--background" in sys.argv  # bilgisayar açılışında sessizce başlamak için

    if not _acquire_lock():
        print("[Piyon Log] Uygulama zaten çalışıyor, pencere açılıyor.")
        ui_server.open_app_window(url)
        return

    try:
        threading.Thread(target=_run_collector, daemon=True).start()

        db.init_db()
        server = ThreadingHTTPServer((ui_server.HOST, ui_server.PORT), ui_server.PiyonLogHandler)
        print(f"[Piyon Log] Uygulama çalışıyor: {url}  (durdurmak için Ctrl+C)")

        if background:
            print("[Piyon Log] Arka planda başlatıldı, pencere açılmadı.")
        else:
            threading.Timer(0.5, lambda: ui_server.open_app_window(url)).start()

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    finally:
        _release_lock()
        print("[Piyon Log] Uygulama durduruldu.")


if __name__ == "__main__":
    main()
