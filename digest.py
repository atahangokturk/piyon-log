"""
Piyon Log - akşam raporu üretici.

Kullanım:
    python digest.py            # bugünün raporu
    python digest.py 2026-08-28 # belirli bir günün raporu

config.USE_OLLAMA True ise özet lokal bir Ollama modeline gönderilip akıcı
bir günlük metnine dönüştürülür. Model kurulu değilse veya erişilemiyorsa
otomatik olarak şablon tabanlı rapora düşer (çökme olmaz).
"""

import sys
from datetime import date, datetime

import requests

import config
import db

AY_ADLARI = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]


def format_sure(saniye: int) -> str:
    """Saniyeyi 'X saat Y dakika' biçiminde okunabilir Türkçe metne çevirir."""
    saniye = int(saniye or 0)
    saat, kalan = divmod(saniye, 3600)
    dakika = kalan // 60
    if saat and dakika:
        return f"{saat} saat {dakika} dakika"
    if saat:
        return f"{saat} saat"
    if dakika:
        return f"{dakika} dakika"
    return "1 dakikadan az"


def format_saat(iso_ts: str) -> str:
    try:
        return datetime.fromisoformat(iso_ts).strftime("%H:%M")
    except Exception:
        return iso_ts


def format_baslik_tarih(date_str: str) -> str:
    try:
        d = date.fromisoformat(date_str)
        return f"{d.day} {AY_ADLARI[d.month - 1]} {d.year}"
    except Exception:
        return date_str


def compute_focus(sessions: list) -> dict:
    """Oturum listesinden odak skorunu türetir.

    config.FOCUS_MIN_SESSION_S'den uzun süren oturumlar "odaklı çalışma"
    sayılır. Skor, odaklı sürenin toplam süreye oranıdır (0-100).
    """
    toplam = sum(s["duration_s"] for s in sessions)
    odakli = sum(s["duration_s"] for s in sessions if s["duration_s"] >= config.FOCUS_MIN_SESSION_S)
    oran = round((odakli / toplam) * 100) if toplam else 0

    derin_calisma = [s for s in sessions if s["duration_s"] >= config.DEEP_WORK_MIN_SESSION_S]
    derin_calisma_saniye = sum(s["duration_s"] for s in derin_calisma)

    return {
        "focus_ratio": oran,
        "focus_seconds": odakli,
        "scattered_seconds": toplam - odakli,
        "deep_work_seconds": derin_calisma_saniye,
        "deep_work_count": len(derin_calisma),
    }


def build_summary(date_str: str) -> dict:
    """O güne ait tüm veriyi tek bir yapılandırılmış özet sözlüğünde toplar."""
    sessions = db.get_sessions_for_day(date_str)
    project_totals = db.get_project_totals(date_str)
    app_totals = db.get_app_totals(date_str)
    toplam_sure = sum(s["duration_s"] for s in sessions)
    focus = compute_focus(sessions)

    return {
        "date_str": date_str,
        "sessions": sessions,
        "project_totals": project_totals,
        "app_totals": app_totals,
        "toplam_sure": toplam_sure,
        **focus,
    }


def render_template_report(summary: dict) -> str:
    """Modele ihtiyaç duymayan, doğrudan verilerden markdown rapor üretir."""
    date_str = summary["date_str"]
    sessions = summary["sessions"]
    project_totals = summary["project_totals"]
    app_totals = summary["app_totals"]
    toplam_sure = summary["toplam_sure"]

    baslik_tarih = format_baslik_tarih(date_str)
    satirlar = [f"# Piyon Log — Günlük Rapor — {baslik_tarih}", ""]

    if not sessions:
        satirlar.append("Bu gün için herhangi bir kayıt bulunamadı.")
        return "\n".join(satirlar) + "\n"

    # --- Günün Özeti ---
    satirlar.append("## Günün Özeti")
    satirlar.append("")
    satirlar.append(f"- Toplam kayıtlı süre: **{format_sure(toplam_sure)}**")
    satirlar.append(f"- Oturum sayısı: **{len(sessions)}**")
    if project_totals:
        en_cok_proje = max(project_totals, key=project_totals.get)
        satirlar.append(
            f"- En çok zaman ayrılan proje: **{en_cok_proje}** "
            f"({format_sure(project_totals[en_cok_proje])})"
        )
    if app_totals:
        en_cok_app = max(app_totals, key=app_totals.get)
        satirlar.append(
            f"- En çok kullanılan uygulama: **{en_cok_app}** "
            f"({format_sure(app_totals[en_cok_app])})"
        )
    satirlar.append(
        f"- Odak skoru: **%{summary['focus_ratio']}** "
        f"({format_sure(summary['focus_seconds'])} kesintisiz, "
        f"{config.FOCUS_MIN_SESSION_S // 60}+ dakikalık bloklarda)"
    )
    satirlar.append("")

    # --- Zaman Çizelgesi ---
    satirlar.append("## Zaman Çizelgesi")
    satirlar.append("")
    for s in sessions:
        baslangic = format_saat(s["start_ts"])
        bitis = format_saat(s["end_ts"])
        proje_etiketi = f" · _{s['project']}_" if s.get("project") else ""
        baslik = s.get("title") or ""
        satirlar.append(
            f"- `{baslangic}–{bitis}` **{s.get('app') or 'Bilinmeyen'}**{proje_etiketi}"
            f"{' — ' + baslik if baslik else ''}"
        )
    satirlar.append("")

    # --- Projeler ---
    if project_totals:
        satirlar.append("## Projeler")
        satirlar.append("")
        for proje, sure in project_totals.items():
            satirlar.append(f"- **{proje}**: {format_sure(sure)}")
        satirlar.append("")

    # --- Uygulamalar ---
    if app_totals:
        satirlar.append("## Uygulamalar")
        satirlar.append("")
        for app, sure in app_totals.items():
            satirlar.append(f"- {app}: {format_sure(sure)}")
        satirlar.append("")

    # --- Notlar / Yazdıkların ---
    notlar = [s for s in sessions if s.get("text") and len(s["text"].strip()) >= 20]
    if notlar:
        satirlar.append("## Notlar / Yazdıkların")
        satirlar.append("")
        for s in notlar:
            baslangic = format_saat(s["start_ts"])
            metin = s["text"].strip().replace("\n", " ")
            satirlar.append(f"- `{baslangic}` ({s.get('app') or 'Bilinmeyen'}): {metin}")
        satirlar.append("")

    return "\n".join(satirlar) + "\n"


def build_ollama_prompt(summary: dict) -> str:
    """Ollama modeline gönderilecek, zaten redakte edilmiş özet üzerine kurulu prompt."""
    date_str = summary["date_str"]
    project_totals = summary["project_totals"]
    app_totals = summary["app_totals"]
    toplam_sure = summary["toplam_sure"]

    proje_satirlari = "\n".join(
        f"- {p}: {format_sure(s)}" for p, s in project_totals.items()
    ) or "- (proje eşleşmesi yok)"
    app_satirlari = "\n".join(
        f"- {a}: {format_sure(s)}" for a, s in app_totals.items()
    ) or "- (veri yok)"

    zaman_cizelgesi = "\n".join(
        f"- {format_saat(s['start_ts'])}–{format_saat(s['end_ts'])} "
        f"{s.get('app') or 'Bilinmeyen'} "
        f"({s.get('project') or 'proje yok'}): {s.get('title') or ''}"
        for s in summary["sessions"]
    ) or "- (kayıt yok)"

    sistem_talimati = (
        "Aşağıda bir kullanıcının bilgisayar aktivite özeti var. Bunu samimi, "
        "kısa ve düzenli bir Türkçe günlük raporuna dönüştür. Hangi projeye ne "
        "kadar zaman ayrıldığını vurgula, dikkat dağınıklığı varsa nazikçe "
        "belirt. Uydurma bilgi ekleme, sadece verilenleri yorumla."
    )

    return (
        f"{sistem_talimati}\n\n"
        f"Tarih: {date_str}\n"
        f"Toplam süre: {format_sure(toplam_sure)}\n\n"
        f"Proje bazında süreler:\n{proje_satirlari}\n\n"
        f"Uygulama bazında süreler:\n{app_satirlari}\n\n"
        f"Zaman çizelgesi:\n{zaman_cizelgesi}\n"
    )


def render_ollama_report(summary: dict) -> str:
    """Ollama'ya istek atar, başarısız olursa istisna fırlatır (çağıran yakalamalı)."""
    prompt = build_ollama_prompt(summary)
    response = requests.post(
        config.OLLAMA_URL,
        json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=60,
    )
    response.raise_for_status()
    metin = response.json().get("response", "").strip()
    if not metin:
        raise ValueError("Ollama boş yanıt döndürdü.")

    baslik_tarih = format_baslik_tarih(summary["date_str"])
    return f"# Piyon Log — Günlük Rapor — {baslik_tarih}\n\n{metin}\n"


def generate_report(date_str: str) -> str:
    summary = build_summary(date_str)

    if config.USE_OLLAMA:
        try:
            return render_ollama_report(summary)
        except Exception as hata:
            print(f"[Piyon Log] Ollama'ya ulaşılamadı ({hata}), şablon moduna geçiliyor.")

    return render_template_report(summary)


def save_report(date_str: str, markdown: str):
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    rapor_yolu = config.REPORTS_DIR / f"{date_str}.md"
    rapor_yolu.write_text(markdown, encoding="utf-8")
    return rapor_yolu


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    date_str = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()

    markdown = generate_report(date_str)
    rapor_yolu = save_report(date_str, markdown)

    print(markdown)
    print(f"[Piyon Log] Rapor kaydedildi: {rapor_yolu}")


if __name__ == "__main__":
    main()
