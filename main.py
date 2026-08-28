"""
Piyon Log - giriş noktası.

Toplayıcıyı başlatır. Konsolsuz çalıştırmak için `pythonw.exe main.py` kullanın
(bkz. install_startup.py, install_desktop_icons.py).
"""

import os
import sys

import psutil

import config
from collector import Collector

LOCK_PATH = config.DB_PATH.parent / "collector.lock"


def _acquire_lock() -> bool:
    """Toplayıcının aynı anda birden fazla kopyasının çalışmasını önler.

    Masaüstü simgesine yanlışlıkla iki kez tıklanması gibi durumlarda,
    veritabanına çakışan/yinelenen oturumlar yazılmasını engeller.
    """
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


def main():
    # Windows konsolunda Türkçe karakterlerin doğru görünmesi için.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not _acquire_lock():
        print("[Piyon Log] Toplayıcı zaten çalışıyor, ikinci bir kopya başlatılmadı.")
        return

    try:
        collector = Collector()
        collector.start()
    finally:
        _release_lock()


if __name__ == "__main__":
    main()
