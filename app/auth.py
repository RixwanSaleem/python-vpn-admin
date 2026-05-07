import hashlib
import os
import re
import secrets as secrets_stdlib
from dataclasses import dataclass
from datetime import datetime

from .config import settings


USERNAME_RE = re.compile(r"^[^\s]{1,128}$")


@dataclass(frozen=True)
class CreateUserInput:
    username: str
    password: str
    expiry_raw: str
    device_limit: int
    vpn_ip: str | None
    allowed_ips_raw: str | None


def validate_username(username: str) -> str:
    username = (username or "").strip()
    if not username or not USERNAME_RE.match(username):
        raise ValueError("Invalid username")
    return username


def validate_device_limit(limit_raw: str) -> int:
    s = (limit_raw or "").strip()
    try:
        v = int(s)
    except ValueError as e:
        raise ValueError("Invalid device limit") from e
    if v < 0:
        raise ValueError("Invalid device limit")
    return v


def validate_expiry(expiry_raw: str) -> str:
    expiry_raw = (expiry_raw or "").strip()
    if not expiry_raw:
        raise ValueError("Invalid expiry")

    # Accept both formats; preserve the original string.
    formats = ("%d-%m-%Y", "%Y-%m-%d")
    for fmt in formats:
        try:
            datetime.strptime(expiry_raw, fmt)
            return expiry_raw
        except ValueError:
            pass
    raise ValueError("Invalid expiry format (use DD-MM-YYYY or YYYY-MM-DD)")


def validate_bandwidth_kbps(value: str) -> int:
    s = (value or "").strip()
    if not s:
        return 0
    try:
        v = int(s)
    except ValueError as e:
        raise ValueError("Invalid bandwidth") from e
    if v < 0:
        raise ValueError("Invalid bandwidth")
    return v


def parse_ip_or_none(value: str | None) -> str | None:
    v = (value or "").strip()
    if not v:
        return None
    # Keep validation light here; firewall will validate further.
    parts = v.split("/")
    if len(parts) not in (1, 2):
        raise ValueError("Invalid IP")
    return v


def validate_admin_username(username: str) -> str:
    u = (username or "").strip()
    if not u or len(u) > 128:
        raise ValueError("Invalid admin username")
    if any(ch in u for ch in "\r\n\t"):
        raise ValueError("Invalid admin username")
    return u


def _hash_panel_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, 600_000, dklen=32
    ).hex()


def effective_panel_admin_username() -> str:
    from .db import get_setting

    u = get_setting("panel_admin_user", "").strip()
    return u or settings.admin_user


def verify_panel_login(username: str, password: str) -> bool:
    from .db import get_setting

    u = (username or "").strip()
    if u != effective_panel_admin_username():
        return False
    stored_hash = get_setting("panel_admin_hash", "").strip()
    stored_salt = get_setting("panel_admin_salt", "").strip()
    if stored_hash and stored_salt:
        try:
            salt = bytes.fromhex(stored_salt)
            cand = _hash_panel_password(password or "", salt)
            return secrets_stdlib.compare_digest(cand, stored_hash)
        except ValueError:
            return False
    return password == settings.admin_pass


def set_panel_admin_credentials(username: str, new_password: str) -> None:
    from .db import set_setting

    user = validate_admin_username(username)
    if not new_password or len(new_password) < 6:
        raise ValueError("Password must be at least 6 characters")
    salt = os.urandom(16)
    h = _hash_panel_password(new_password, salt)
    set_setting("panel_admin_user", user)
    set_setting("panel_admin_salt", salt.hex())
    set_setting("panel_admin_hash", h)

