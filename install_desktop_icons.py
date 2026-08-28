"""
Piyon Log - masaüstü kısayolları kurulumu.

Piyon Log'u sıradan bir Windows programı gibi çift tıklayarak
kullanabilmeniz için masaüstüne iki kısayol ekler:

- "Piyon Log.lnk"           -> toplayıcıyı VE canlı paneli aynı anda,
  tek bir uygulama olarak başlatır (bkz. piyon_log.py). Zaten çalışıyorsa
  ikinci bir kopya açmaz, sadece panel penceresini gösterir.
- "Piyon Log Rapor Al.lnk"  -> o güne kadarki verilerden anında bir markdown
  rapor üretir (digest.py), ekranda gösterir ve reports/ klasörüne kaydeder.

Not: Uygulamanın bilgisayar açılışında OTOMATİK başlaması için ayrıca
`install_startup.py` çalıştırılmalı; bu script sadece manuel/masaüstü
kısayollarını kurar.

Kullanım:
    python install_desktop_icons.py             # kurar
    python install_desktop_icons.py --uninstall # kaldırır
    python install_desktop_icons.py --status    # kurulu olup olmadığını gösterir
"""

import argparse
import os
import sys
from pathlib import Path

import config

DESKTOP_DIR = Path(os.environ["USERPROFILE"]) / "Desktop"
ICON_PATH = config.BASE_DIR / "piyon-log.ico"

# Eski (main.py + ui_server.py ayrı ayrı açan) sürümden kalan kısayollar;
# tek uygulamaya geçişte otomatik temizlenir.
LEGACY_SHORTCUTS = [
    DESKTOP_DIR / "Piyon Log Başlat.lnk",
    DESKTOP_DIR / "Piyon Log Paneli.lnk",
]


def get_pythonw_path() -> str:
    python_exe = Path(sys.executable)
    pythonw = python_exe.with_name("pythonw.exe")
    if pythonw.exists():
        return str(pythonw)
    return str(python_exe)


def get_python_path() -> str:
    return str(Path(sys.executable))


def build_shortcuts():
    pythonw = get_pythonw_path()
    python_exe = get_python_path()
    digest_py = config.BASE_DIR / "digest.py"

    return {
        "app": {
            "path": DESKTOP_DIR / "Piyon Log.lnk",
            "target_exe": pythonw,
            "arguments": f'"{config.BASE_DIR / "piyon_log.py"}"',
            "description": "Piyon Log - aktivite toplayıcı ve canlı panel",
        },
        "report": {
            "path": DESKTOP_DIR / "Piyon Log Rapor Al.lnk",
            # cmd /k ile açılır ki rapor okunduktan sonra pencere kapanmasın.
            "target_exe": "cmd.exe",
            "arguments": f'/k ""{python_exe}" "{digest_py}""',
            "description": "Piyon Log - günün raporunu oluştur",
        },
    }


def install():
    import win32com.client

    shortcuts = build_shortcuts()

    if not (config.BASE_DIR / "piyon_log.py").exists():
        print(f"[Piyon Log] HATA: {config.BASE_DIR / 'piyon_log.py'} bulunamadı.")
        return

    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
    shell = win32com.client.Dispatch("WScript.Shell")

    for entry in shortcuts.values():
        shortcut = shell.CreateShortCut(str(entry["path"]))
        shortcut.TargetPath = entry["target_exe"]
        shortcut.Arguments = entry["arguments"]
        shortcut.WorkingDirectory = str(config.BASE_DIR)
        shortcut.Description = entry["description"]
        if ICON_PATH.exists():
            shortcut.IconLocation = f"{ICON_PATH},0"
        shortcut.save()
        print(f"[Piyon Log] Kısayol oluşturuldu: {entry['path']}")

    for legacy in LEGACY_SHORTCUTS:
        if legacy.exists():
            legacy.unlink()
            print(f"[Piyon Log] Eski kısayol temizlendi: {legacy.name}")

    print("Masaüstündeki 'Piyon Log' simgesine çift tıklayarak uygulamayı "
          "başlatabilirsiniz.")


def uninstall():
    for entry in build_shortcuts().values():
        path = entry["path"]
        if path.exists():
            path.unlink()
            print(f"[Piyon Log] Kaldırıldı: {path}")
        else:
            print(f"[Piyon Log] Zaten kurulu değil: {path.name}")


def status():
    for entry in build_shortcuts().values():
        path = entry["path"]
        durum = "kurulu" if path.exists() else "kurulu değil"
        print(f"[Piyon Log] {path.name}: {durum}")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Piyon Log masaüstü kısayolları kurulumu")
    parser.add_argument("--uninstall", action="store_true", help="Kısayolları kaldır")
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
