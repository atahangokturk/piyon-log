"""
Piyon Log - lokal web paneli.

Toplanan verileri, sunucu logu tarzında ama şık bir arayüzle canlı olarak
gösteren, dışa hiçbir istek göndermeyen bir yerel web sunucusu. Sadece Python
standart kütüphanesini kullanır (ek bağımlılık gerekmez).

Kullanım:
    python ui_server.py
    -> http://127.0.0.1:8420 tarayıcıda otomatik açılır.
"""

import json
import os
import shutil
import socket
import subprocess
import threading
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import collector
import config
import db
import digest

WEB_DIR = config.BASE_DIR / "web"
HOST = "127.0.0.1"
PORT = 8420

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/favicon.png": ("favicon.png", "image/png"),
    "/report.html": ("report.html", "text/html; charset=utf-8"),
}


class PiyonLogHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # sessiz sunucu: konsolu istek kayıtlarıyla kirletme

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in STATIC_FILES:
            filename, content_type = STATIC_FILES[parsed.path]
            self._serve_file(WEB_DIR / filename, content_type)
        elif parsed.path == "/api/today":
            self._serve_today(parsed)
        elif parsed.path == "/api/current":
            self._serve_current()
        elif parsed.path == "/api/info":
            self._serve_info()
        elif parsed.path == "/api/search":
            self._serve_search(parsed)
        elif parsed.path == "/api/projects":
            self._serve_projects()
        elif parsed.path == "/api/projects/summary":
            self._serve_project_summary()
        elif parsed.path == "/api/apps/summary":
            self._serve_app_summary()
        elif parsed.path == "/api/daily-totals":
            self._serve_daily_totals(parsed)
        elif parsed.path == "/api/daily-metrics":
            self._serve_daily_metrics(parsed)
        elif parsed.path == "/api/project-keywords":
            self._serve_project_keywords()
        elif parsed.path == "/api/report.md":
            self._serve_report_md(parsed)
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/session/update":
            self._update_session()
        elif parsed.path == "/api/project-keywords/add":
            self._add_project_keyword()
        elif parsed.path == "/api/project-keywords/delete":
            self._delete_project_keyword()
        elif parsed.path == "/api/open-data-folder":
            self._open_data_folder()
        else:
            self.send_error(404)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw or b"{}")

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path, content_type: str):
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_today(self, parsed):
        qs = parse_qs(parsed.query)
        date_str = qs.get("date", [date.today().isoformat()])[0]

        sessions = db.get_sessions_for_day(date_str)
        project_totals = db.get_project_totals(date_str)
        app_totals = db.get_app_totals(date_str)
        toplam_sure = sum(s["duration_s"] for s in sessions)
        focus = digest.compute_focus(sessions)

        payload = {
            "date": date_str,
            "sessions": sessions,
            "project_totals": project_totals,
            "app_totals": app_totals,
            "toplam_sure": toplam_sure,
            **focus,
        }
        self._send_json(payload)

    def _serve_current(self):
        state = collector.get_current_state()
        self._send_json({"active": state is not None, "current": state})

    def _serve_info(self):
        self._send_json(
            {
                "version": config.APP_VERSION,
                "data_dir": str(config.DB_PATH.parent),
                "encrypted": True,
            }
        )

    def _open_data_folder(self):
        try:
            os.startfile(str(config.DB_PATH.parent))
            self._send_json({"ok": True})
        except Exception:
            self._send_json({"ok": False}, status=500)

    def _serve_search(self, parsed):
        qs = parse_qs(parsed.query)
        query = qs.get("q", [""])[0].strip()
        project = qs.get("project", [""])[0].strip()
        app = qs.get("app", [""])[0].strip()

        if not query and not project and not app:
            self._send_json({"query": "", "sessions": []})
            return

        sessions = db.search_sessions(query=query or None, project=project or None, app=app or None)
        self._send_json({"query": query, "project": project, "app": app, "sessions": sessions})

    def _serve_projects(self):
        names = sorted({row["project"] for row in db.get_project_keywords()})
        self._send_json({"projects": names})

    def _serve_project_summary(self):
        self._send_json({"projects": db.get_project_summary()})

    def _serve_app_summary(self):
        self._send_json({"apps": db.get_app_summary()})

    def _serve_daily_totals(self, parsed):
        qs = parse_qs(parsed.query)
        days = int(qs.get("days", ["30"])[0])
        self._send_json({"days": db.get_daily_totals(days)})

    def _serve_daily_metrics(self, parsed):
        qs = parse_qs(parsed.query)
        days = int(qs.get("days", ["14"])[0])
        self._send_json({"days": db.get_daily_metrics(days)})

    def _serve_project_keywords(self):
        self._send_json({"keywords": db.get_project_keywords()})

    def _add_project_keyword(self):
        try:
            data = self._read_json_body()
            keyword = str(data["keyword"]).strip()
            project = str(data["project"]).strip()
            if not keyword or not project:
                raise ValueError
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            self.send_error(400)
            return

        db.add_project_keyword(keyword, project)
        updated = db.apply_keyword_retroactively(keyword, project)
        self._send_json({"ok": True, "updated": updated})

    def _delete_project_keyword(self):
        try:
            data = self._read_json_body()
            keyword_id = int(data["id"])
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            self.send_error(400)
            return

        db.delete_project_keyword(keyword_id)
        self._send_json({"ok": True})

    def _update_session(self):
        try:
            data = self._read_json_body()
            session_id = int(data["id"])
            project = (data.get("project") or "").strip() or None
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            self.send_error(400)
            return

        db.update_session_project(session_id, project)
        self._send_json({"ok": True})

    def _serve_report_md(self, parsed):
        qs = parse_qs(parsed.query)
        date_str = qs.get("date", [date.today().isoformat()])[0]

        markdown = digest.generate_report(date_str)
        body = markdown.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="piyon-log-{date_str}.md"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _port_in_use() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, PORT)) == 0


def _find_edge() -> str | None:
    """Adres çubuğu olmayan 'uygulama' penceresi açabilmek için Edge'i arar."""
    edge = shutil.which("msedge")
    if edge:
        return edge
    for candidate in (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def open_app_window(url: str):
    """Mümkünse pencereyi bir masaüstü uygulaması gibi (adres çubuksuz) açar."""
    edge = _find_edge()
    if edge:
        # stdin'i de DEVNULL'a bağlamak şart: .exe olarak paketlenmiş
        # (--windowed) sürümde konsol/stdin olmadığından, belirtilmezse
        # Popen çağrısı süreci kapanmayan bir tutamaca (handle) takılıp
        # asılı bırakabiliyor.
        subprocess.Popen(
            [edge, f"--app={url}", "--window-size=1180,760"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    else:
        webbrowser.open(url)


def main():
    url = f"http://{HOST}:{PORT}/"

    if _port_in_use():
        # Panel zaten arka planda çalışıyor; ikinci bir sunucu açmadan
        # sadece pencereyi göster.
        print(f"[Piyon Log] Panel zaten çalışıyor, pencere açılıyor: {url}")
        open_app_window(url)
        return

    db.init_db()
    server = ThreadingHTTPServer((HOST, PORT), PiyonLogHandler)
    print(f"[Piyon Log] Panel çalışıyor: {url}  (durdurmak için Ctrl+C)")

    threading.Timer(0.5, lambda: open_app_window(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("[Piyon Log] Panel durduruldu.")


if __name__ == "__main__":
    main()
