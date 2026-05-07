import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import settings


def ensure_db_schema(db_path: str) -> None:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS vpn_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                expiry TEXT,
                device_limit INTEGER,
                vpn_ip TEXT,
                allowed_ips TEXT,
                bandwidth_kbps INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                user TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        # Lightweight migration for existing DBs.
        cols = [r[1] for r in conn.execute("PRAGMA table_info(vpn_users)").fetchall()]
        if "bandwidth_kbps" not in cols:
            conn.execute("ALTER TABLE vpn_users ADD COLUMN bandwidth_kbps INTEGER DEFAULT 0")
        conn.commit()
    finally:
        conn.close()


@contextmanager
def db_conn() -> Iterator[sqlite3.Connection]:
    ensure_db_schema(settings.db_path)
    conn = sqlite3.connect(settings.db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_user_by_username(username: str):
    with db_conn() as conn:
        cur = conn.execute("SELECT * FROM vpn_users WHERE username = ?", (username,))
        return cur.fetchone()


def list_users_html_rows() -> str:
    with db_conn() as conn:
        cur = conn.execute("SELECT username, expiry, device_limit FROM vpn_users")
        rows = cur.fetchall()

    # Keep JS expectations: return a <tr> header + <tr> data rows.
    # Escaping of username is done in the route layer.
    out = (
        "<tr>"
        "<th>User</th><th>Expiry</th><th>Limit</th><th>Actions</th>"
        "</tr>"
    )
    return out


def get_recent_logs_text(limit: int = 50) -> str:
    with db_conn() as conn:
        cur = conn.execute(
            "SELECT action, user, timestamp FROM logs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        lines = [
            f"{row['timestamp']} - {row['action']} - {row['user']}"
            for row in cur.fetchall()
        ]
    return "\n".join(lines) + (("\n") if lines else "")


def list_users() -> list[sqlite3.Row]:
    with db_conn() as conn:
        cur = conn.execute("SELECT * FROM vpn_users")
        return cur.fetchall()


def create_user(
    username: str,
    expiry: str,
    device_limit: int,
    vpn_ip: str | None,
    allowed_ips: str | None,
    bandwidth_kbps: int = 0,
) -> None:
    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO vpn_users (username, expiry, device_limit, vpn_ip, allowed_ips, bandwidth_kbps)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, expiry, device_limit, vpn_ip, allowed_ips, bandwidth_kbps),
        )


def delete_user(username: str) -> None:
    with db_conn() as conn:
        conn.execute("DELETE FROM vpn_users WHERE username = ?", (username,))


def update_user_profile(username: str, expiry: str, bandwidth_kbps: int) -> None:
    with db_conn() as conn:
        conn.execute(
            """
            UPDATE vpn_users
            SET expiry = ?, bandwidth_kbps = ?
            WHERE username = ?
            """,
            (expiry, bandwidth_kbps, username),
        )


def insert_log(action: str, user: str) -> None:
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO logs(action, user) VALUES (?, ?)",
            (action, user),
        )


def clear_logs() -> None:
    with db_conn() as conn:
        conn.execute("DELETE FROM logs")


def get_setting(key: str, default: str = "") -> str:
    with db_conn() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    if not row:
        return default
    return (row["value"] or "") if isinstance(row["value"], str) else str(row["value"])


def set_setting(key: str, value: str) -> None:
    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO app_settings(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (key, value),
        )

