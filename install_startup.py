"""
Piyon Log - otomatik başlatma kurulumu.

Windows "Başlangıç" (Startup) klasörüne, bilgisayar açılınca uygulamayı
(toplayıcı + panel) konsolsuz (pythonw.exe) ve sessizce (panel penceresi
açılmadan) başlatan bir kısayol (.lnk) ekler. Paneli görmek isterseniz
masaüstündeki "Piyon Log" simgesine tıklamanız yeterli.

Kullanım:
    python install_startup.py             # kurar
    python install_startup.py --uninstall # kaldırır
    python install_startup.py --status    # kurulu olup olmadığını gösterir
"""

import argparse
import os
import sys
from pathlib import Path

import config

STARTUP_DIR = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
SHORTCUT_PATH = STARTUP_DIR / "PiyonLog.lnk"
APP_PY = config.BASE_DIR / "piyon_log.py"
ICON_PATH = config.BASE_DIR / "piyon-log.ico"


def get_pythonw_path() -> str:
    """Konsol penceresi açmayan pythonw.exe yolunu bulur; bulamazsa mevcut python.exe'ye düşer."""
    python_exe = Path(sys.executable)
    pythonw = python_exe.with_name("pythonw.exe")
    if pythonw.exists():
        return str(pythonw)
    return str(python_exe)


def install():
    import win32com.client

    if not APP_PY.exists():
        print(f"[Piyon Log] HATA: {APP_PY} bulunamadı.")
        return

    STARTUP_DIR.mkdir(parents=True, exist_ok=True)

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(SHORTCUT_PATH))
    shortcut.TargetPath = get_pythonw_path()
    shortcut.Arguments = f'"{APP_PY}" --background'
    shortcut.WorkingDirectory = str(config.BASE_DIR)
    shortcut.WindowStyle = 7  # simge durumunda (pythonw zaten konsolsuz)
    shortcut.Description = "Piyon Log - aktivite toplayıcı ve canlı panel"
    if ICON_PATH.exists():
        shortcut.IconLocation = f"{ICON_PATH},0"
    shortcut.save()

    print(f"[Piyon Log] Otomatik başlatma kuruldu: {SHORTCUT_PATH}")
    print("Bilgisayar bir sonraki açılışta uygulamayı sessizce (pencere açmadan) başlatacak.")


def uninstall():
    if SHORTCUT_PATH.exists():
        SHORTCUT_PATH.unlink()
        print(f"[Piyon Log] Otomatik başlatma kaldırıldı: {SHORTCUT_PATH}")
    else:
        print("[Piyon Log] Zaten kurulu değil.")


def status():
    if SHORTCUT_PATH.exists():
        print(f"[Piyon Log] Kurulu. Kısayol: {SHORTCUT_PATH}")
    else:
        print("[Piyon Log] Kurulu değil.")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Piyon Log otomatik başlatma kurulumu")
    parser.add_argument("--uninstall", action="store_true", help="Otomatik başlatmayı kaldır")
    parser.add_argument("--status", action="store_true", help="Kurulum durumunu göster")
    args = parser.parse_args()

    if args.uninstall:
        uninstall()
    elif args.status:
        status()
    else:
        install()


if __name__ == "__main__":
    main()
