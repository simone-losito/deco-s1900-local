"""Crypto helpers for TP-Link Deco S1900 local web protocol."""
from __future__ import annotations

import base64
import json
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_der_public_key


class DecoCryptoError(RuntimeError):
    """Crypto error."""


def _parse_kv(value: str) -> dict[str, str]:
    return dict(parse_qsl(value, keep_blank_values=True))


def _json(payload: Any) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


@dataclass
class DecoS1900Crypto:
    """AES/RSA implementation matching TP-Link tpEncrypt.js."""

    aes_value: str
    seq: int | str
    hash_value: str | None
    rsa_value: str

    def __post_init__(self) -> None:
        aes = _parse_kv(self.aes_value)
        rsa_data = _parse_kv(self.rsa_value)
        self.key = aes["k"].encode("utf-8")
        self.iv = aes["i"].encode("utf-8")
        self.seq_int = int(self.seq)
        self.aes_key_string = f"k={aes['k']}&i={aes['i']}"
        self.nn = rsa_data["nn"]
        self.ee = rsa_data["ee"]
        self._public_key = self._load_public_key(self.nn, self.ee)

    @staticmethod
    def _load_public_key(modulus_hex: str, exponent_hex: str) -> rsa.RSAPublicKey:
        numbers = rsa.RSAPublicNumbers(int(exponent_hex, 16), int(modulus_hex, 16))
        return numbers.public_key()

    def rsa_encrypt_hex(self, text: str) -> str:
        encrypted = self._public_key.encrypt(text.encode("utf-8"), asym_padding.PKCS1v15())
        expected_len = len(self.nn)
        value = encrypted.hex()
        return value.rjust(expected_len, "0")

    def get_signature(self, seq_plus_len: int) -> str:
        raw = f"{self.aes_key_string}&s={seq_plus_len}"
        chunks: list[str] = []
        pos = 0
        while pos < len(raw):
            chunks.append(self.rsa_encrypt_hex(raw[pos : pos + 53]))
            pos += 53
        return "".join(chunks)

    def aes_encrypt_text(self, text: str) -> str:
        padder = padding.PKCS7(128).padder()
        padded = padder.update(text.encode("utf-8")) + padder.finalize()
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(self.iv))
        enc = cipher.encryptor()
        raw = enc.update(padded) + enc.finalize()
        return base64.b64encode(raw).decode("ascii")

    def aes_decrypt_text(self, value: str) -> str:
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(self.iv))
        dec = cipher.decryptor()
        raw = dec.update(base64.b64decode(value)) + dec.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        plain = unpadder.update(raw) + unpadder.finalize()
        return plain.decode("utf-8")

    def encrypt_payload(self, payload: Any | None = None) -> dict[str, str]:
        text = _json(payload or {})
        data = self.aes_encrypt_text(text)
        sign = self.get_signature(self.seq_int + len(data))
        return {"sign": sign, "data": data}

    def decrypt_response(self, value: str) -> Any:
        text = self.aes_decrypt_text(value)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
