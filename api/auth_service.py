
import hashlib
import hmac
import os
import secrets
import sqlite3

from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from pwdlib import PasswordHash


# ==========================================================
# CONFIGURATION
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_PATH = PROJECT_ROOT / "data" / "exam_monitoring.db"

ADMIN_USERNAME = os.getenv("MONITORAI_ADMIN_USERNAME", "").strip()
ADMIN_PASSWORD_HASH = os.getenv("MONITORAI_ADMIN_PASSWORD_HASH", "")

SESSION_TTL_HOURS = int(
    os.getenv("MONITORAI_SESSION_TTL_HOURS", "8")
)

SESSION_COOKIE_SECURE = (
    os.getenv("MONITORAI_SESSION_COOKIE_SECURE", "true")
    .strip()
    .lower() == "true"
)

SESSION_COOKIE_NAME = "monitorai_session"

password_hasher = PasswordHash.recommended()


if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
    raise RuntimeError(
        "Bootstrap administrator credentials are not configured. "
        "Check MONITORAI_ADMIN_USERNAME and "
        "MONITORAI_ADMIN_PASSWORD_HASH in .env."
    )

if SESSION_TTL_HOURS < 1:
    raise RuntimeError(
        "MONITORAI_SESSION_TTL_HOURS must be at least 1."
    )


# ==========================================================
# DATABASE
# ==========================================================

def _connect():
    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=10,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def initialize_auth_database():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS authors (
                author_id TEXT PRIMARY KEY,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'AUTHOR'
                    CHECK (role IN ('ADMIN', 'AUTHOR')),
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK (is_active IN (0, 1)),
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                session_id TEXT PRIMARY KEY,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                author_id TEXT REFERENCES authors(author_id)
            )
            """
        )

        # Migrate existing sessions created by the single-author
        # version of MonitorAI.
        session_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(auth_sessions)"
            ).fetchall()
        }

        if "author_id" not in session_columns:
            connection.execute(
                "ALTER TABLE auth_sessions ADD COLUMN author_id TEXT"
            )

        now = datetime.now(timezone.utc).isoformat()

        # Bootstrap or refresh the configured administrator.
        # Existing administrator sessions remain associated with
        # this account; the configured password hash is preserved.
        admin = connection.execute(
            "SELECT author_id FROM authors WHERE username = ?",
            (ADMIN_USERNAME,),
        ).fetchone()

        if admin is None:
            admin_id = secrets.token_hex(16)
            connection.execute(
                """
                INSERT INTO authors (
                    author_id, username, password_hash,
                    role, is_active, created_at
                )
                VALUES (?, ?, ?, 'ADMIN', 1, ?)
                """,
                (admin_id, ADMIN_USERNAME, ADMIN_PASSWORD_HASH, now),
            )
        else:
            admin_id = admin["author_id"]
            connection.execute(
                """
                UPDATE authors
                SET password_hash = ?, role = 'ADMIN', is_active = 1
                WHERE author_id = ?
                """,
                (ADMIN_PASSWORD_HASH, admin_id),
            )

        # Associate sessions from the previous single-user version
        # with the bootstrap administrator.
        connection.execute(
            """
            UPDATE auth_sessions
            SET author_id = ?
            WHERE author_id IS NULL
            """,
            (admin_id,),
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at
            ON auth_sessions(expires_at)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_sessions_author_id
            ON auth_sessions(author_id)
            """
        )


# ==========================================================
# AUTHOR ACCOUNTS
# ==========================================================

def authenticate_author(username: str, password: str):
    username = username.strip()

    with _connect() as connection:
        author = connection.execute(
            """
            SELECT author_id, username, password_hash, role, is_active
            FROM authors
            WHERE username = ? COLLATE NOCASE
            LIMIT 1
            """,
            (username,),
        ).fetchone()

    if author is None or not author["is_active"]:
        return None

    try:
        password_valid = password_hasher.verify(
            password,
            author["password_hash"],
        )
    except (ValueError, TypeError):
        password_valid = False

    if not password_valid:
        return None

    return {
        "author_id": author["author_id"],
        "username": author["username"],
        "role": author["role"],
    }


def verify_author_credentials(username: str, password: str) -> bool:
    # Compatibility helper for any older code still using this name.
    return authenticate_author(username, password) is not None


def create_author(
    username: str,
    password: str,
    role: str = "AUTHOR",
):
    username = username.strip()
    role = role.upper()

    if len(username) < 3 or len(username) > 80:
        raise ValueError("Username must be between 3 and 80 characters.")

    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters.")

    if role not in {"ADMIN", "AUTHOR"}:
        raise ValueError("Role must be ADMIN or AUTHOR.")

    password_hash = password_hasher.hash(password)
    author_id = secrets.token_hex(16)
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO authors (
                    author_id, username, password_hash,
                    role, is_active, created_at
                )
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (
                    author_id,
                    username,
                    password_hash,
                    role,
                    created_at,
                ),
            )
    except sqlite3.IntegrityError as error:
        raise ValueError("That username is already in use.") from error

    return {
        "author_id": author_id,
        "username": username,
        "role": role,
    }


def get_author_by_id(author_id: str):
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT author_id, username, role, is_active, created_at
            FROM authors
            WHERE author_id = ?
            LIMIT 1
            """,
            (author_id,),
        ).fetchone()

    return dict(row) if row else None


# ==========================================================
# SESSION HELPERS
# ==========================================================

def create_session(author_id: str) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=SESSION_TTL_HOURS)
    token = secrets.token_urlsafe(32)

    with _connect() as connection:
        author = connection.execute(
            """
            SELECT author_id
            FROM authors
            WHERE author_id = ? AND is_active = 1
            """,
            (author_id,),
        ).fetchone()

        if author is None:
            raise ValueError("Author account is not active.")

        connection.execute(
            "DELETE FROM auth_sessions WHERE expires_at <= ?",
            (now.isoformat(),),
        )

        connection.execute(
            """
            INSERT INTO auth_sessions (
                session_id, token_hash, created_at,
                expires_at, author_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                secrets.token_hex(16),
                _hash_token(token),
                now.isoformat(),
                expires_at.isoformat(),
                author_id,
            ),
        )

    return token, expires_at


def get_session_author(token: str | None):
    if not token or len(token) > 256:
        return None

    now = datetime.now(timezone.utc).isoformat()

    with _connect() as connection:
        row = connection.execute(
            """
            SELECT
                a.author_id, a.username, a.role, a.is_active,
                s.expires_at
            FROM auth_sessions s
            JOIN authors a ON a.author_id = s.author_id
            WHERE s.token_hash = ?
              AND s.expires_at > ?
              AND a.is_active = 1
            LIMIT 1
            """,
            (_hash_token(token), now),
        ).fetchone()

    return dict(row) if row else None


def validate_session(token: str | None) -> bool:
    return get_session_author(token) is not None


def revoke_session(token: str | None) -> None:
    if not token or len(token) > 256:
        return

    with _connect() as connection:
        connection.execute(
            "DELETE FROM auth_sessions WHERE token_hash = ?",
            (_hash_token(token),),
        )


def list_authors():
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT author_id, username, role, is_active, created_at
            FROM authors
            ORDER BY created_at DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]


# Initialize and migrate the database at import time.
initialize_auth_database()
