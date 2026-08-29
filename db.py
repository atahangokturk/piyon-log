"""
Piyon Log - SQLite veritabanı katmanı.

Oturumların (session) yazılması ve raporlama için okunması burada yapılır.
Veritabanı SQLCipher ile şifrelenir (bkz. crypto_key.py); anahtar bu Windows
hesabına DPAPI ile bağlı olarak saklanır.
"""

import shutil
import sqlite3  # sadece eski düz-metin veritabanını taşımak için kullanılır
from contextlib import contextmanager
from datetime import date, timedelta

from sqlcipher3 import dbapi2 as sqlcipher

import config
import crypto_key

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


def _seed_project_keywords():
    """config.PROJECT_MAP'ten varsayılan eşleşmeleri yükler.

    Yalnızca tablo İLK KEZ oluşturulduğunda çağrılır (bkz. init_db). Satır
    sayısına değil tablonun var olup olmadığına bakılır — yoksa kullanıcı
    panelden bilerek tüm kuralları sildiğinde (tablo var ama boş), bir
    sonraki açılışta varsayılanlar sessizce geri gelirdi. Bu gerçek bir
    hataydı ve düzeltildi.
    """
    with get_connection() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO project_keywords (keyword, project) VALUES (?, ?)",
            list(config.PROJECT_MAP.items()),
        )
        conn.commit()


def _is_plaintext_sqlite(path) -> bool:
    """Dosya, standart (şifresiz) sqlite3 ile açılabiliyor mu?"""
    try:
        conn = sqlite3.connect(str(path))
        conn.execute("SELECT count(*) FROM sqlite_master")
        conn.close()
        return True
    except sqlite3.DatabaseError:
        return False


def _migrate_plaintext_to_encrypted(key: str):
    """Eski, şifresiz bir data/log.db varsa SQLCipher ile şifreli hâline taşır.

    Orijinal dosya `log.db.bak` olarak korunur; taşıma sırasında herhangi bir
    sorun olursa hiçbir şey silinmez, sadece taşıma atlanır.
    """
    path = config.DB_PATH
    if not path.exists() or not _is_plaintext_sqlite(path):
        return

    backup_path = path.with_suffix(".db.bak")
    shutil.copy2(path, backup_path)

    tmp_path = path.with_suffix(".db.encrypting")
    if tmp_path.exists():
        tmp_path.unlink()

    conn = sqlcipher.connect(str(path))
    try:
        conn.execute("ATTACH DATABASE ? AS encrypted KEY ?", (str(tmp_path), key))
        conn.execute("SELECT sqlcipher_export('encrypted')")
        conn.execute("DETACH DATABASE encrypted")
    except sqlcipher.OperationalError:
        # Bazı sqlcipher3 sürümlerinde ATTACH ... KEY parametreli sorguyu
        # desteklemiyor; anahtar hex olduğundan doğrudan gömmek güvenlidir.
        conn.execute(f'ATTACH DATABASE ? AS encrypted KEY "{key}"', (str(tmp_path),))
        conn.execute("SELECT sqlcipher_export('encrypted')")
        conn.execute("DETACH DATABASE encrypted")
    finally:
        conn.close()

    path.unlink()
    tmp_path.rename(path)


@contextmanager
def get_connection():
    """DB dosyasının bulunduğu klasörün var olduğundan emin olup şifreli bağlantı açar."""
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    key = crypto_key.get_or_create_key()

    conn = sqlcipher.connect(str(config.DB_PATH))
    # PRAGMA parametreli sorguyu desteklemez; anahtar secrets.token_hex ile
    # üretildiği için yalnızca [0-9a-f] içerir, doğrudan gömülmesi güvenlidir.
    conn.execute(f'PRAGMA key = "{key}"')
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Veritabanı ve tabloları (yoksa) oluşturur.

    Eski, şifresiz bir veritabanı bulunursa (önceki sürümlerden kalma)
    burada bir kereliğine şifreli hâle taşınır. Varsayılan proje kuralları
    da yalnızca tablo ilk kez oluşturulduğunda bir kereliğine eklenir.
    """
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    key = crypto_key.get_or_create_key()
    _migrate_plaintext_to_encrypted(key)

    with get_connection() as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='project_keywords'"
        )
        is_first_run = cur.fetchone() is None
        conn.executescript(SCHEMA)
        conn.commit()

    if is_first_run:
        _seed_project_keywords()


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
        conn.row_factory = sqlcipher.Row
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
        conn.row_factory = sqlcipher.Row
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
        conn.row_factory = sqlcipher.Row
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


def apply_keyword_retroactively(keyword: str, project: str) -> int:
    """Yeni eklenen bir kuralı GEÇMİŞTEKİ kayıtlara da uygular.

    Yalnızca henüz hiçbir projeye atanmamış (project IS NULL) oturumları
    günceller — elle veya başka bir kuralla zaten sınıflandırılmış bir
    kaydın üzerine yazmaz. Güncellenen satır sayısını döner.
    """
    like = f"%{keyword.lower().strip()}%"
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE sessions
            SET project = ?
            WHERE project IS NULL AND LOWER(title) LIKE ?
            """,
            (project.strip(), like),
        )
        conn.commit()
        return cur.rowcount


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


def get_daily_metrics(days: int = 14):
    """Son N gün için toplam süre, odak süresi, derin çalışma süresi ve
    oturum sayısını döner (metrik kartlarındaki mini grafik/karşılaştırma
    için). Veri olmayan günler sıfırlarla doldurulur."""
    today = date.today()
    date_list = [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]

    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT
                substr(start_ts, 1, 10) AS gun,
                SUM(duration_s) AS toplam,
                SUM(CASE WHEN duration_s >= ? THEN duration_s ELSE 0 END) AS odakli,
                SUM(CASE WHEN duration_s >= ? THEN duration_s ELSE 0 END) AS derin,
                COUNT(*) AS oturum_sayisi
            FROM sessions
            WHERE substr(start_ts, 1, 10) >= ?
            GROUP BY gun
            """,
            (config.FOCUS_MIN_SESSION_S, config.DEEP_WORK_MIN_SESSION_S, date_list[0]),
        )
        rows = {
            row[0]: {
                "total_seconds": row[1],
                "focus_seconds": row[2],
                "deep_work_seconds": row[3],
                "session_count": row[4],
            }
            for row in cur.fetchall()
        }

    empty = {"total_seconds": 0, "focus_seconds": 0, "deep_work_seconds": 0, "session_count": 0}
    return [{"date": d, **rows.get(d, empty)} for d in date_list]


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
