"""
Piyon Log - SQLite veritabanı katmanı.

Oturumların (session) yazılması ve raporlama için okunması burada yapılır.
"""

import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    start_ts   TEXT NOT NULL,      -- ISO 8601, ör. 2026-08-28T14:03:12
    end_ts     TEXT NOT NULL,
    duration_s INTEGER NOT NULL,   -- saniye
    app        TEXT,               -- ör. blender.exe, chrome.exe
    title      TEXT,               -- pencere başlığı (redakte edilmiş)
    project    TEXT,               -- eşleşen Piyon projesi (yoksa NULL)
    text       TEXT                -- o oturumda yazılan redakte metin (yoksa boş)
);

CREATE INDEX IF NOT EXISTS idx_sessions_start ON sessions(start_ts);

CREATE TABLE IF NOT EXISTS project_keywords (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL UNIQUE,   -- pencere başlığında aranan anahtar kelime (küçük harf)
    project TEXT NOT NULL           -- eşleşince atanacak proje adı
);
"""


def _seed_project_keywords_if_empty():
    """Tablo boşsa config.PROJECT_MAP'ten varsayılan eşleşmeleri yükler.

    Böylece ilk kurulumda hiçbir proje kaybolmaz; sonrasında kullanıcı
    panelden ekleyip silebilir.
    """
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM project_keywords").fetchone()[0]
        if count > 0:
            return
        conn.executemany(
            "INSERT OR IGNORE INTO project_keywords (keyword, project) VALUES (?, ?)",
            list(config.PROJECT_MAP.items()),
        )
        conn.commit()


@contextmanager
def get_connection():
    """DB dosyasının bulunduğu klasörün var olduğundan emin olup bağlantı açar."""
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Veritabanı ve tabloları (yoksa) oluşturur."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    _seed_project_keywords_if_empty()


def insert_session(session: dict):
    """Tek bir oturumu veritabanına yazar.

    session dict anahtarları: start_ts, end_ts, duration_s, app, title,
    project, text
    """
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions (start_ts, end_ts, duration_s, app, title, project, text)
            VALUES (:start_ts, :end_ts, :duration_s, :app, :title, :project, :text)
            """,
            session,
        )
        conn.commit()


def get_sessions_for_day(date_str: str):
    """'2026-08-28' formatındaki gün için tüm oturumları başlangıç zamanına göre döner."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT * FROM sessions
            WHERE start_ts LIKE ?
            ORDER BY start_ts ASC
            """,
            (f"{date_str}%",),
        )
        return [dict(row) for row in cur.fetchall()]


def get_project_totals(date_str: str):
    """O güne ait projelere göre toplam süreyi (saniye) döner: {proje: saniye}."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT COALESCE(project, 'Diğer') AS proje, SUM(duration_s) AS toplam
            FROM sessions
            WHERE start_ts LIKE ?
            GROUP BY proje
            ORDER BY toplam DESC
            """,
            (f"{date_str}%",),
        )
        return {row[0]: row[1] for row in cur.fetchall()}


def get_app_totals(date_str: str):
    """O güne ait uygulamalara göre toplam süreyi (saniye) döner: {uygulama: saniye}."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT COALESCE(app, 'Bilinmeyen') AS uygulama, SUM(duration_s) AS toplam
            FROM sessions
            WHERE start_ts LIKE ?
            GROUP BY uygulama
            ORDER BY toplam DESC
            """,
            (f"{date_str}%",),
        )
        return {row[0]: row[1] for row in cur.fetchall()}


def search_sessions(
    query: str | None = None,
    project: str | None = None,
    app: str | None = None,
    limit: int = 200,
):
    """Başlık/metinde ifade arar ve/veya proje ya da uygulamaya göre filtreler.

    Filtreler tüm günler içinde (tarihe bakılmaksızın) uygulanır.
    """
    conditions = []
    params: list = []

    if query:
        conditions.append("(text LIKE ? OR title LIKE ?)")
        like = f"%{query}%"
        params.extend([like, like])

    if project:
        if project == "Diğer":
            conditions.append("project IS NULL")
        else:
            conditions.append("project = ?")
            params.append(project)

    if app:
        conditions.append("app = ?")
        params.append(app)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            f"SELECT * FROM sessions {where} ORDER BY start_ts DESC LIMIT ?",
            params,
        )
        return [dict(row) for row in cur.fetchall()]


def update_session_project(session_id: int, project: str | None):
    """Bir oturumun proje etiketini elle günceller (panelden düzenleme için)."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE sessions SET project = ? WHERE id = ?",
            (project or None, session_id),
        )
        conn.commit()


def get_project_keywords():
    """Tüm proje eşleştirme kurallarını döner: [{id, keyword, project}, ...]."""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT id, keyword, project FROM project_keywords ORDER BY project, keyword")
        return [dict(row) for row in cur.fetchall()]


def match_project(title: str):
    """Pencere başlığına göre eşleşen projeyi döner (veritabanındaki kurallara göre)."""
    if not title:
        return None
    lowered = title.lower()
    for row in get_project_keywords():
        if row["keyword"].lower() in lowered:
            return row["project"]
    return None


def add_project_keyword(keyword: str, project: str):
    """Yeni bir proje eşleştirme kuralı ekler. Aynı anahtar kelime zaten varsa günceller."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO project_keywords (keyword, project) VALUES (?, ?)
            ON CONFLICT(keyword) DO UPDATE SET project = excluded.project
            """,
            (keyword.lower().strip(), project.strip()),
        )
        conn.commit()


def delete_project_keyword(keyword_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM project_keywords WHERE id = ?", (keyword_id,))
        conn.commit()


def get_app_summary():
    """Tüm zamanlar için uygulama bazında özet döner: toplam süre, oturum
    sayısı, ilk ve son görülen gün."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT COALESCE(app, 'Bilinmeyen') AS uygulama,
                   SUM(duration_s) AS toplam,
                   COUNT(*) AS oturum_sayisi,
                   MIN(start_ts) AS ilk,
                   MAX(start_ts) AS son
            FROM sessions
            GROUP BY uygulama
            ORDER BY toplam DESC
            """
        )
        return [
            {
                "app": row[0],
                "total_seconds": row[1],
                "session_count": row[2],
                "first_date": (row[3] or "")[:10],
                "last_date": (row[4] or "")[:10],
            }
            for row in cur.fetchall()
        ]


def get_daily_totals(days: int = 30):
    """Son N gün için günlük toplam süreyi döner: [{date, total_seconds}, ...]
    (eskiden yeniye). Veri olmayan günler de 0 saniye olarak dahil edilir —
    ısı haritasının her zaman tam N günlük bir grid olması içindir."""
    today = date.today()
    date_list = [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]

    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT substr(start_ts, 1, 10) AS gun, SUM(duration_s) AS toplam
            FROM sessions
            WHERE substr(start_ts, 1, 10) >= ?
            GROUP BY gun
            """,
            (date_list[0],),
        )
        totals = {row[0]: row[1] for row in cur.fetchall()}

    return [{"date": d, "total_seconds": totals.get(d, 0)} for d in date_list]


def get_project_summary():
    """Tüm zamanlar için proje bazında özet döner: toplam süre, oturum
    sayısı, ilk ve son görülen gün."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT COALESCE(project, 'Diğer') AS proje,
                   SUM(duration_s) AS toplam,
                   COUNT(*) AS oturum_sayisi,
                   MIN(start_ts) AS ilk,
                   MAX(start_ts) AS son
            FROM sessions
            GROUP BY proje
            ORDER BY toplam DESC
            """
        )
        return [
            {
                "project": row[0],
                "total_seconds": row[1],
                "session_count": row[2],
                "first_date": (row[3] or "")[:10],
                "last_date": (row[4] or "")[:10],
            }
            for row in cur.fetchall()
        ]
