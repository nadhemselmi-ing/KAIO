"""Ground-segment storage: users, refresh tokens and the telecommand log (SQLite, standard library).

Passwords are stored as scrypt hashes with a random salt, never in clear.
Refresh tokens are stored as SHA-256 hashes, so a stolen database cannot be used to log in.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from typing import Optional

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("KAIO_GROUND_DATA", os.path.join(ROOT, "data"))
ROLES = ("viewer", "operator")


def _path(name: str) -> str:
    os.makedirs(DATA, exist_ok=True)
    return os.path.join(DATA, name)


def secret(name: str, nbytes: int = 32) -> bytes:
    """Load a secret key from data/<name>, creating it (owner-only permissions) on first use."""
    env = os.environ.get("KAIO_" + name.upper().replace(".", "_"))
    if env:
        return env.encode()
    p = _path(name)
    if not os.path.exists(p):
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(secrets.token_bytes(nbytes))
    return open(p, "rb").read()


def db() -> sqlite3.Connection:
    con = sqlite3.connect(_path("kaio_ground.db"), check_same_thread=False, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, salt BLOB, pw BLOB, role TEXT, created REAL);
    CREATE TABLE IF NOT EXISTS refresh(h TEXT PRIMARY KEY, username TEXT, family TEXT, exp REAL, revoked INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS tclog(id INTEGER PRIMARY KEY AUTOINCREMENT, seq INTEGER, ts REAL, username TEXT, param TEXT, value REAL, mac TEXT, ok INTEGER, result TEXT);
    """)
    return con


# ---- passwords ---------------------------------------------------------------------------
def hash_pw(password: str, salt: Optional[bytes] = None):
    salt = salt or secrets.token_bytes(16)
    return salt, hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)


def add_user(con, username: str, password: str, role: str) -> None:
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    if len(password) < 10:
        raise ValueError("password must have at least 10 characters")
    salt, pw = hash_pw(password)
    con.execute("INSERT OR REPLACE INTO users VALUES(?,?,?,?,?)", (username, salt, pw, role, time.time()))


def check_user(con, username: str, password: str) -> Optional[str]:
    row = con.execute("SELECT salt, pw, role FROM users WHERE username=?", (username,)).fetchone()
    if row is None:
        hash_pw(password)  # same work as a real check, so timing does not reveal valid usernames
        return None
    salt, pw, role = row
    return role if hmac.compare_digest(hash_pw(password, salt)[1], pw) else None


def role_of(con, username: str) -> Optional[str]:
    row = con.execute("SELECT role FROM users WHERE username=?", (username,)).fetchone()
    return row[0] if row else None


# ---- refresh tokens (opaque, rotated on every use) ------------------------------------------
def _h(tok: str) -> str:
    return hashlib.sha256(tok.encode()).hexdigest()


def new_refresh(con, username: str, ttl_s: float, family: Optional[str] = None) -> str:
    tok = secrets.token_urlsafe(32)
    con.execute("INSERT INTO refresh VALUES(?,?,?,?,0)", (_h(tok), username, family or secrets.token_hex(8), time.time() + ttl_s))
    return tok


def rotate_refresh(con, tok: str, ttl_s: float):
    """Return (username, new_token) or (None, reason). Re-use of a revoked token revokes the whole family."""
    con.execute("BEGIN IMMEDIATE")
    try:
        row = con.execute("SELECT username, family, exp, revoked FROM refresh WHERE h=?", (_h(tok),)).fetchone()
        if row is None:
            con.execute("COMMIT"); return None, "unknown refresh token"
        username, family, exp, revoked = row
        if revoked:
            con.execute("UPDATE refresh SET revoked=1 WHERE family=?", (family,))
            con.execute("COMMIT"); return None, "refresh token re-used: session revoked"
        if exp < time.time():
            con.execute("COMMIT"); return None, "refresh token expired"
        con.execute("UPDATE refresh SET revoked=1 WHERE h=?", (_h(tok),))
        new = secrets.token_urlsafe(32)
        con.execute("INSERT INTO refresh VALUES(?,?,?,?,0)", (_h(new), username, family, time.time() + ttl_s))
        con.execute("COMMIT")
        return username, new
    except Exception:
        con.execute("ROLLBACK"); raise


def revoke_refresh(con, tok: str) -> None:
    row = con.execute("SELECT family FROM refresh WHERE h=?", (_h(tok),)).fetchone()
    if row:
        con.execute("UPDATE refresh SET revoked=1 WHERE family=?", (row[0],))
