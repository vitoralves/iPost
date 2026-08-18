from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

from ipost.errors import ConfigError
from ipost.settings import Settings, get_settings
from ipost.storage import supabase_client

SESSION_COOKIE = "ipost_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 30
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def _settings(settings: Settings | None) -> Settings:
    return settings or get_settings()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    hashed = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    )
    return f"scrypt${salt.hex()}${hashed.hex()}"


_DUMMY_HASH = hash_password("invalid")


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, hashed_hex = stored.split("$", 2)
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    hashed = hashlib.scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt_hex),
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    )
    return hmac.compare_digest(hashed.hex(), hashed_hex)


def sign_session(username: str, secret: str) -> str:
    payload = urlsafe_b64encode(
        json.dumps({"u": username, "t": int(time.time())}, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    signature = hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def read_session(token: str, secret: str) -> str | None:
    if not token or "." not in token or not secret:
        return None
    payload, signature = token.rsplit(".", 1)
    expected = hmac.new(secret.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        data = json.loads(urlsafe_b64decode(payload.encode("ascii")))
        username = str(data["u"])
        issued = int(data["t"])
    except (KeyError, TypeError, ValueError):
        return None
    if time.time() - issued > SESSION_TTL_SECONDS:
        return None
    return username


def get_user(username: str, settings: Settings | None = None) -> dict | None:
    settings = _settings(settings)
    client = supabase_client(settings)
    try:
        rows = (
            client.table("users")
            .select("username,password_hash")
            .eq("username", username)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        raise ConfigError(str(exc)) from exc
    return rows[0] if rows else None


def upsert_user(username: str, password: str, settings: Settings | None = None) -> str:
    settings = _settings(settings)
    ident = username.strip()
    if not ident or not password:
        raise ConfigError("Username and password are required")
    client = supabase_client(settings)
    try:
        client.table("users").upsert(
            {"username": ident, "password_hash": hash_password(password)}
        ).execute()
    except Exception as exc:
        raise ConfigError(str(exc)) from exc
    return ident


def authenticate(username: str, password: str, settings: Settings | None = None) -> str | None:
    user = get_user(username.strip(), settings)
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user["username"]


def cookie_params(settings: Settings) -> dict:
    secure = settings.session_secure
    return {
        "key": SESSION_COOKIE,
        "httponly": True,
        "secure": secure,
        "samesite": "none" if secure else "lax",
        "max_age": SESSION_TTL_SECONDS,
        "path": "/",
    }
