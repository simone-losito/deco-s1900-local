"""Async API client for TP-Link Deco S1900 local web UI.

v2.0.0: stable local API for S1900 firmware.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import aiohttp
from yarl import URL

from .const import DEFAULT_PORT, DEFAULT_TIMEOUT, ENDPOINTS
from .crypto import DecoCryptoError, DecoS1900Crypto

_LOGGER = logging.getLogger(__name__)


class DecoS1900Error(RuntimeError):
    """Base error."""


class DecoAuthError(DecoS1900Error):
    """Auth/session error."""


class DecoConnectionError(DecoS1900Error):
    """Connection error."""


_TPLINK_SALT = "RDpbLfCPsJZ7fiv"
_TPLINK_ALPHABET = (
    "yLwVl0zKqws7LgKPRQ84Mdt708T1qQ3Ha7xv3H7NyU84p21BriUWBU43odz3iP4"
    "rBL3cD02KZciXTysVXiV8ngg6vL48rPJyAUw0HurW20xqxv9aYb4M9wK1Ae0"
    "wlro510qXeU07kV57fQMc8L6aLgMLwygtc0F10a0Dg70TOoouyFhdysuRMO51"
    "yY5ZlOZZLEal1h0t9YQW0Ko7oBwmCAHoic4HYbUyVeU3sfQ1xtXcPcf1aT303wAQhv66qzW"
)


def _clean_line(value: str) -> str:
    """Remove CR/LF/control chars that cannot appear in URLs/headers."""
    return "".join(ch for ch in str(value).strip() if ord(ch) >= 32 and ch not in "\r\n")


def _su_encrypt(value: str, salt: str = _TPLINK_SALT, alphabet: str = _TPLINK_ALPHABET) -> str:
    """Port of TP-Link $.su.encrypt(value, salt, alphabet).

    Firmware login uses:
        id = $.su.encrypt(tmp[3], MD5(password), tmp[4])
    """
    value = _clean_line(value)
    salt = _clean_line(salt)
    alphabet = _clean_line(alphabet)
    out: list[str] = []
    value_len = len(value)
    salt_len = len(salt)
    alphabet_len = len(alphabet)
    for idx in range(max(value_len, salt_len)):
        left = 187
        right = 187
        if value_len <= idx:
            right = ord(salt[idx])
        elif salt_len <= idx:
            left = ord(value[idx])
        else:
            left = ord(value[idx])
            right = ord(salt[idx])
        out.append(alphabet[(left ^ right) % alphabet_len])
    return "".join(out)


def _encode_id(value: str) -> str:
    """Encode unsafe URL/control characters only."""
    out = []
    for ch in str(value):
        if ord(ch) < 32 or ch in "%&#":
            out.append(quote(ch, safe=""))
        else:
            out.append(ch)
    return "".join(out)


def _make_16_digit_key(offset: int = 0) -> str:
    """Generate the same kind of 16-char numeric key used by TP-Link JS."""
    value = f"{int(time.time() * 1000) + offset}{random.randint(100000000, 999999999)}"
    return value[:16]


def _split_lines(text: str) -> list[str]:
    """Split firmware CRLF text without losing meaningful middle lines."""
    lines = text.split("\r\n") if "\r\n" in text else re.split(r"\r?\n", text)
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def _split_bootstrap_response(text: str) -> tuple[str, str, str]:
    """Parse code=16 'get' response: status, exponent, modulus, sequence."""
    lines = [_clean_line(line) for line in _split_lines(text) if _clean_line(line)]
    if len(lines) < 4 or lines[0] != "00000":
        raise DecoAuthError(f"Unexpected bootstrap response: {text[:180]!r}")
    exponent = lines[1]
    modulus = lines[2]
    seq = lines[3]
    return exponent, modulus, seq


@dataclass
class DecoS1900Api:
    """Client that follows the S1900 browser endpoints."""

    session: aiohttp.ClientSession
    host: str
    password: str
    port: int = DEFAULT_PORT
    timeout: int = DEFAULT_TIMEOUT

    def __post_init__(self) -> None:
        self._crypto: DecoS1900Crypto | None = None
        self._lock = asyncio.Lock()
        self._id: str | None = None
        self._logged_in = False

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def _headers(self) -> dict[str, str]:
        """Headers matching the Deco browser XHR as closely as possible."""
        return {
            "Accept": "*/*",
            "Accept-Language": "it-IT,it;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Content-Type": "text/plain;charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "DNT": "1",
        }

    def _url(self, endpoint: str) -> str:
        if not self._id:
            raise DecoAuthError("Session id is not available")
        sep = "&" if "?" in endpoint else "?"
        return f"{self.base_url}{endpoint}{sep}id={_encode_id(self._id)}"

    async def _post_raw(self, path: str, body: str | bytes | None, *, allow_auth_error: bool = False) -> tuple[int, str]:
        """Raw POST used by firmware handshake.

        Empty body is sent as a true zero-length body, like Chrome's cURL:
            POST /?code=7&asyn=1
            Content-Length: 0
        """
        url = f"{self.base_url}{path}"
        headers = self._headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"

        if body in (None, ""):
            post_data: bytes | None = None
            headers["Content-Length"] = "0"
        elif isinstance(body, bytes):
            post_data = body
        else:
            post_data = body.encode("utf-8")

        try:
            async with self.session.post(
                URL(url, encoded=True),
                data=post_data,
                headers=headers,
                skip_auto_headers={"Accept-Encoding"},
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                text = await resp.text()
                _LOGGER.debug("Deco raw POST %s -> HTTP %s body=%r", path, resp.status, text[:220])
                if resp.status in (401, 403) and not allow_auth_error:
                    raise DecoAuthError(f"HTTP {resp.status}; url={url}; body={text[:180]!r}")
                if resp.status not in (401, 403):
                    resp.raise_for_status()
                return resp.status, text
        except DecoAuthError:
            raise
        except (aiohttp.ClientError, TimeoutError, asyncio.TimeoutError) as err:
            raise DecoConnectionError(f"Unable to call {url}") from err

    async def _get_tmp_key_dictionary(self) -> list[str]:
        """Mirror main.getTmpKey(): code=7/asyn=1 returns 401 with key lines."""
        status, text = await self._post_raw("/?code=7&asyn=1", None, allow_auth_error=True)
        raw_lines = _split_lines(text)
        _LOGGER.debug("Deco getTmpKey HTTP %s lines=%r", status, raw_lines[:6])
        if status == 401 and len(raw_lines) >= 5 and raw_lines[0] == "00007":
            return raw_lines
        raise DecoAuthError(f"Unexpected getTmpKey response HTTP {status}; body={text[:220]!r}")

    async def _enable_gdpr(self) -> None:
        status, text = await self._post_raw("/?code=16&asyn=0", "enable")
        if status != 200 or not text.startswith("00000"):
            raise DecoAuthError(f"enableGDPR failed HTTP {status}: {text[:160]!r}")

    async def _bootstrap_crypto(self) -> None:
        """Read RSA/seq from /?code=16&asyn=0 and create AES/RSA encryptor."""
        status, text = await self._post_raw("/?code=16&asyn=0", "get")
        if status != 200:
            raise DecoAuthError(f"Bootstrap rejected with HTTP {status}: {text[:160]!r}")
        ee, nn, seq = _split_bootstrap_response(text)
        aes = f"k={_make_16_digit_key(0)}&i={_make_16_digit_key(17)}"
        rsa_value = f"nn={nn}&ee={ee}"
        self._crypto = DecoS1900Crypto(aes, seq, "undefined", rsa_value)
        _LOGGER.debug("Deco bootstrap OK seq=%s", seq)

    async def _set_gdpr_key(self) -> None:
        assert self._crypto is not None
        assert self._id is not None
        body = "set " + self._crypto.rsa_encrypt_hex(self._crypto.aes_key_string)
        status, text = await self._post_raw(f"/?code=16&asyn=0&id={_encode_id(self._id)}", body, allow_auth_error=True)
        if status != 200 or not text.startswith("00000"):
            raise DecoAuthError(f"setGDPRKey failed HTTP {status}; body={text[:180]!r}")

    async def async_login(self) -> None:
        """Login like modules/login/localLogin/controllers.js.

        Browser flow:
        1) getTmpKey()     -> POST /?code=7&asyn=1 with empty body, expected HTTP 401
        2) enableGDPR()    -> POST /?code=16&asyn=0 body 'enable'
        3) getGDPRKey()    -> POST /?code=16&asyn=0 body 'get'; returns ee, nn, seq
        4) id              -> $.su.encrypt(tmp[3], MD5(password), tmp[4])
        5) doLogin()       -> POST /?code=7&asyn=0&id=<id> body rsaEncrypt(password)
        6) setGDPRKey()    -> POST /?code=16&asyn=0&id=<id> body 'set ' + rsaEncrypt(aesKey)
        """
        if self._logged_in:
            return

        tmp = await self._get_tmp_key_dictionary()
        await self._enable_gdpr()
        await self._bootstrap_crypto()
        assert self._crypto is not None

        password_md5 = hashlib.md5(self.password.encode("utf-8")).hexdigest()  # noqa: S324
        self._id = _su_encrypt(tmp[3], password_md5, tmp[4])

        body = self._crypto.rsa_encrypt_hex(self.password)
        login_path = f"/?code=7&asyn=0&id={_encode_id(self._id)}"
        status, text = await self._post_raw(login_path, body, allow_auth_error=True)
        if status != 200 or not text.startswith("00000"):
            raise DecoAuthError(
                "Browser-style login failed. "
                f"id={self._id!r}; HTTP {status}; body={text[:180]!r}; tmp={tmp[:6]!r}"
            )

        await self._set_gdpr_key()
        self._logged_in = True
        _LOGGER.debug("Deco browser-style login accepted id=%s", self._id)

    async def _post(self, endpoint: str, payload: Any | None = None) -> Any:
        await self.async_login()
        assert self._crypto is not None
        async with self._lock:
            form = self._crypto.encrypt_payload(payload or {})
        url = self._url(endpoint)
        try:
            async with self.session.post(
                URL(url, encoded=True),
                data=("sign=" + form["sign"] + "&data=" + form["data"]) if isinstance(form, dict) else form,
                headers=self._headers(),
                skip_auto_headers={"Accept-Encoding"},
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                text = await resp.text()
                if resp.status in (401, 403):
                    self._logged_in = False
                    raise DecoAuthError(
                        f"HTTP {resp.status}; endpoint={endpoint}; url={url}; body={text[:180]!r}"
                    )
                resp.raise_for_status()
            return self._crypto.decrypt_response(text)
        except DecoAuthError:
            raise
        except DecoCryptoError as err:
            raise DecoS1900Error(f"Unable to decrypt endpoint {endpoint}") from err
        except (aiohttp.ClientError, TimeoutError, asyncio.TimeoutError) as err:
            raise DecoConnectionError(f"Unable to call endpoint {endpoint}") from err

    async def probe(self) -> Any:
        return await self.get_device_list()

    async def get_device_list(self) -> Any:
        return await self._post(ENDPOINTS["device_list"])

    async def get_clients(self) -> Any:
        return await self._post(ENDPOINTS["client_list"])

    async def get_wan(self) -> Any:
        return await self._post(ENDPOINTS["wan_ipv4"])

    async def get_lan(self) -> Any:
        return await self._post(ENDPOINTS["lan_ip"])

    async def get_wireless(self) -> Any:
        return await self._post(ENDPOINTS["wlan"])

    async def get_all(self) -> dict[str, Any]:
        """Fetch all stable Deco endpoints."""
        results: dict[str, Any] = {}
        for key, func in {
            "device_list": self.get_device_list,
            "clients": self.get_clients,
            "wan": self.get_wan,
            "lan": self.get_lan,
            "wireless": self.get_wireless,
        }.items():
            try:
                results[key] = await func()
            except Exception as err:
                _LOGGER.debug("Deco endpoint %s failed: %s", key, err)
                results[key] = {"error": str(err)}
        return results
