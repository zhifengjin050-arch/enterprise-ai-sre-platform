"""SSH / 通用凭据加解密"""

from app.security.secrets import (
    SECRET_PREFIX,
    decrypt_secret,
    encrypt_secret,
    is_encrypted_secret,
)


def test_encrypt_roundtrip():
    cipher = encrypt_secret("CloudShop@Prod!")
    assert cipher is not None
    assert cipher != "CloudShop@Prod!"
    assert is_encrypted_secret(cipher)
    assert cipher.startswith(SECRET_PREFIX)
    assert decrypt_secret(cipher) == "CloudShop@Prod!"


def test_legacy_plaintext_passthrough():
    assert decrypt_secret("legacy-password") == "legacy-password"
    assert decrypt_secret(None) is None
    assert decrypt_secret("") == ""


def test_encrypt_is_idempotent():
    once = encrypt_secret("once")
    twice = encrypt_secret(once)
    assert once == twice
    assert decrypt_secret(twice) == "once"


def test_empty_not_prefixed():
    assert encrypt_secret("") == ""
    assert encrypt_secret(None) is None
