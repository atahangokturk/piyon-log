"""
Piyon Log - redaksiyon (metin sansürleme) katmanı.

Metin diske yazılmadan ÖNCE buradan geçirilir. Bu, ikincil bir korumadır;
birincil koruma config.EXCLUDED_APPS / EXCLUDED_TITLE_KEYWORDS ile hassas
uygulamalarda metnin hiç toplanmamasıdır (bkz. collector.py).
"""

import re

import config

# 6 ve üzeri haneli sayı dizileri (telefon, hesap no, vb.)
_NUMBER_RE = re.compile(r"\d{6,}")

# E-posta adresleri
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# TR IBAN benzeri desen: TR + 24 hane (aralarda boşluk olabilir)
_IBAN_RE = re.compile(r"\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b", re.IGNORECASE)

# 16 haneli kart numarası deseni (4'lü gruplar, boşluk/tire opsiyonel)
_CARD_RE = re.compile(r"\b(?:\d[ -]?){16}\b")

_CUSTOM_PATTERNS = [re.compile(p) for p in config.CUSTOM_REDACT_PATTERNS]


def redact(text: str) -> str:
    """Verilen metindeki hassas görünen desenleri maskeler."""
    if not text:
        return text

    result = text
    result = _IBAN_RE.sub("[IBAN]", result)
    result = _CARD_RE.sub("[KART]", result)
    result = _EMAIL_RE.sub("[MAIL]", result)
    result = _NUMBER_RE.sub("[SAYI]", result)

    for pattern in _CUSTOM_PATTERNS:
        result = pattern.sub("[GİZLİ]", result)

    return result


if __name__ == "__main__":
    # Basit doğrulama testleri
    ornekler = [
        ("Telefonum 05321234567", "Telefonum [SAYI]"),
        ("mail: ata@example.com", "mail: [MAIL]"),
        ("TR330006100519786457841326", "[IBAN]"),
        ("kart no 4111111111111111", "kart no [KART]"),
        ("normal bir metin burada", "normal bir metin burada"),
    ]
    for girdi, beklenen in ornekler:
        sonuc = redact(girdi)
        durum = "OK" if sonuc == beklenen else "HATA"
        print(f"[{durum}] '{girdi}' -> '{sonuc}' (beklenen: '{beklenen}')")
