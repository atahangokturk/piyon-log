"""
Piyon Log - veritabanı şifreleme anahtarı yönetimi.

Anahtar rastgele üretilir ve Windows DPAPI (CryptProtectData) ile bu Windows
kullanıcı hesabına bağlı olarak şifrelenmiş şekilde diske yazılır. Anahtar
dosyası çalınsa bile, aynı Windows hesabında oturum açılmadan çözülemez.
Bu, "diskteki dosyayı biri kopyalarsa okuyamasın" tehdidine karşı makul bir
korumadır; tam bir güvenlik garantisi değildir (bkz. README).
"""

import secrets

import win32crypt

import config

KEY_PATH = config.DB_PATH.parent / "key.bin"

# DPAPI'ye ek bağlam olarak veriyoruz; anahtarın başka bir DPAPI korumalı
# veriyle karıştırılmasını zorlaştırır.
_ENTROPY = b"piyon-log-db-key-v1"


def get_or_create_key() -> str:
    """Şifreleme anahtarını döner; yoksa yeni bir tane üretip DPAPI ile korur."""
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)

    if KEY_PATH.exists():
        protected = KEY_PATH.read_bytes()
        _desc, raw = win32crypt.CryptUnprotectData(protected, _ENTROPY, None, None, 0)
        return raw.decode("utf-8")

    key = secrets.token_hex(32)
    protected = win32crypt.CryptProtectData(
        key.encode("utf-8"), "Piyon Log DB Key", _ENTROPY, None, None, 0
    )
    KEY_PATH.write_bytes(protected)
    return key
