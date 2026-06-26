# db.py
from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any, Optional, get_args

from config import SETTINGS
from utils import now_utc_iso, parse_iso
from models import (
    EventType,
    Lang,
    LeadStatus,
    RiskProfile,
    Step,
    LANG_UZ,
    SUPPORTED_LANGS,
    STEP_CHOOSE_LANG,
    RISK_PROFILES,
    LEAD_STATUSES,
    LEAD_NEW,
    LEAD_CALLED,
    LEAD_NO_ANSWER,
)


def _conn() -> sqlite3.Connection:
    db_path = Path(SETTINGS.DB_PATH)
    if db_path.parent and str(db_path.parent) not in ("", "."):
        db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_column(cur: sqlite3.Cursor, table: str, column: str, ddl: str) -> None:
    existing = {row["name"] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
    with _conn() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            name TEXT,

            lang TEXT NOT NULL DEFAULT 'uz',
            step TEXT NOT NULL DEFAULT 'choose_lang',

            risk_profile TEXT,
            amount REAL,
            phone TEXT,
            source TEXT,
            reminder_sent_at TEXT,
            no_answer_reminder_at TEXT,

            lead_status TEXT NOT NULL DEFAULT 'new',

            created_at TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
        """)

        _ensure_column(cur, "users", "username", "TEXT")
        _ensure_column(cur, "users", "full_name", "TEXT")
        _ensure_column(cur, "users", "name", "TEXT")
        _ensure_column(cur, "users", "lang", "TEXT NOT NULL DEFAULT 'uz'")
        _ensure_column(cur, "users", "step", "TEXT NOT NULL DEFAULT 'choose_lang'")
        _ensure_column(cur, "users", "risk_profile", "TEXT")
        _ensure_column(cur, "users", "amount", "REAL")
        _ensure_column(cur, "users", "phone", "TEXT")
        _ensure_column(cur, "users", "source", "TEXT")
        _ensure_column(cur, "users", "reminder_sent_at", "TEXT")
        _ensure_column(cur, "users", "no_answer_reminder_at", "TEXT")
        _ensure_column(cur, "users", "lead_status", "TEXT NOT NULL DEFAULT 'new'")
        _ensure_column(cur, "users", "created_at", "TEXT")
        _ensure_column(cur, "users", "last_seen", "TEXT")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT,
            created_at TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            file_id TEXT,
            text TEXT,
            created_at TEXT NOT NULL
        )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_lead_status ON users(lead_status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_risk ON users(risk_profile)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_source ON users(source)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_no_answer_reminder ON users(no_answer_reminder_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_events_type_time ON events(event_type, created_at)")
        cur.execute("UPDATE users SET lang=? WHERE lang IS NULL OR lang=''", (LANG_UZ,))
        cur.execute("UPDATE users SET step=? WHERE step IS NULL OR step=''", (STEP_CHOOSE_LANG,))
        cur.execute("UPDATE users SET lead_status=? WHERE lead_status IS NULL OR lead_status=''", (LEAD_NEW,))
        cur.execute("UPDATE users SET created_at=? WHERE created_at IS NULL OR created_at=''", (now_utc_iso(),))
        cur.execute("UPDATE users SET last_seen=created_at WHERE last_seen IS NULL OR last_seen=''")
        conn.commit()


def _row_to_dict(row: sqlite3.Row | None) -> Optional[dict[str, Any]]:
    return dict(row) if row else None


def _clean_text(value: str | None, max_len: int = 500) -> str:
    return " ".join((value or "").strip().split())[:max_len]


def _valid_step(step: Step) -> bool:
    return step in get_args(Step)


def _normalize_limit_offset(limit: int, offset: int = 0) -> tuple[int, int]:
    limit = max(1, min(int(limit or 1), 500))
    offset = max(0, int(offset or 0))
    return limit, offset


def add_event(tg_id: int, event_type: EventType, payload: str | None = None) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO events (tg_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
            (tg_id, event_type, _clean_text(payload, 1000) if payload else None, now_utc_iso()),
        )
        conn.commit()


def get_google_sheet_uid() -> str:
    return SETTINGS.GOOGLE_SHEETS_SPREADSHEET_ID


def upsert_user(tg_id: int, username: str | None, full_name: str | None) -> None:
    username = _clean_text(username, 128) or None
    full_name = _clean_text(full_name, 255) or None
    now = now_utc_iso()

    with _conn() as conn:
        cur = conn.cursor()
        exists = cur.execute("SELECT tg_id FROM users WHERE tg_id=?", (tg_id,)).fetchone()

        if exists:
            cur.execute(
                "UPDATE users SET username=?, full_name=?, last_seen=? WHERE tg_id=?",
                (username, full_name, now, tg_id),
            )
        else:
            cur.execute("""
                INSERT INTO users (
                    tg_id, username, full_name,
                    lang, step,
                    lead_status,
                    created_at, last_seen
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tg_id, username, full_name,
                LANG_UZ, STEP_CHOOSE_LANG,
                LEAD_NEW,
                now, now
            ))
        conn.commit()


def touch_last_seen(tg_id: int) -> None:
    with _conn() as conn:
        conn.execute("UPDATE users SET last_seen=? WHERE tg_id=?", (now_utc_iso(), tg_id))
        conn.commit()


def get_user(tg_id: int) -> Optional[dict[str, Any]]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        return _row_to_dict(row)


def set_lang(tg_id: int, lang: Lang, next_step: Step) -> None:
    if lang not in SUPPORTED_LANGS:
        lang = LANG_UZ
    if not _valid_step(next_step):
        next_step = STEP_CHOOSE_LANG

    with _conn() as conn:
        conn.execute(
            "UPDATE users SET lang=?, step=?, last_seen=? WHERE tg_id=?",
            (lang, next_step, now_utc_iso(), tg_id),
        )
        conn.commit()
    add_event(tg_id, "lang_set", lang)


def set_step(tg_id: int, step: Step) -> None:
    if not _valid_step(step):
        step = STEP_CHOOSE_LANG

    with _conn() as conn:
        conn.execute(
            "UPDATE users SET step=?, last_seen=? WHERE tg_id=?",
            (step, now_utc_iso(), tg_id),
        )
        conn.commit()


def set_name(tg_id: int, name: str, next_step: Step) -> None:
    name = _clean_text(name, 255)
    if not _valid_step(next_step):
        next_step = STEP_CHOOSE_LANG

    with _conn() as conn:
        conn.execute(
            "UPDATE users SET name=?, step=?, last_seen=? WHERE tg_id=?",
            (name, next_step, now_utc_iso(), tg_id),
        )
        conn.commit()
    add_event(tg_id, "name_set", name)


def set_amount(tg_id: int, amount: float, next_step: Step | None = None) -> None:
    amount = max(float(amount or 0), 0)
    if next_step and not _valid_step(next_step):
        next_step = STEP_CHOOSE_LANG

    with _conn() as conn:
        if next_step:
            conn.execute(
                "UPDATE users SET amount=?, step=?, last_seen=? WHERE tg_id=?",
                (amount, next_step, now_utc_iso(), tg_id),
            )
        else:
            conn.execute(
                "UPDATE users SET amount=?, last_seen=? WHERE tg_id=?",
                (amount, now_utc_iso(), tg_id),
            )
        conn.commit()
    add_event(tg_id, "amount_set", str(amount))


def set_risk_profile(tg_id: int, risk: RiskProfile, next_step: Step | None = None) -> None:
    if risk not in RISK_PROFILES:
        return
    if next_step and not _valid_step(next_step):
        next_step = STEP_CHOOSE_LANG

    with _conn() as conn:
        if next_step:
            conn.execute(
                "UPDATE users SET risk_profile=?, step=?, last_seen=? WHERE tg_id=?",
                (risk, next_step, now_utc_iso(), tg_id),
            )
        else:
            conn.execute(
                "UPDATE users SET risk_profile=?, last_seen=? WHERE tg_id=?",
                (risk, now_utc_iso(), tg_id),
            )
        conn.commit()
    add_event(tg_id, "risk_selected", risk)


def set_phone(tg_id: int, phone: str, next_step: Step | None = None) -> None:
    phone = _clean_text(phone, 64)
    if next_step and not _valid_step(next_step):
        next_step = STEP_CHOOSE_LANG

    with _conn() as conn:
        if next_step:
            conn.execute(
                "UPDATE users SET phone=?, step=?, last_seen=? WHERE tg_id=?",
                (phone, next_step, now_utc_iso(), tg_id),
            )
        else:
            conn.execute(
                "UPDATE users SET phone=?, last_seen=? WHERE tg_id=?",
                (phone, now_utc_iso(), tg_id),
            )
        conn.commit()
    add_event(tg_id, "phone_set", phone)


def set_source(tg_id: int, source: str, next_step: Step) -> None:
    source = _clean_text(source, 64)
    if not _valid_step(next_step):
        next_step = STEP_CHOOSE_LANG

    with _conn() as conn:
        conn.execute(
            "UPDATE users SET source=?, step=?, last_seen=? WHERE tg_id=?",
            (source, next_step, now_utc_iso(), tg_id),
        )
        conn.commit()
    add_event(tg_id, "source_set", source)


def set_lead_status(tg_id: int, status: LeadStatus) -> None:
    if status not in LEAD_STATUSES:
        return

    reminder_at = now_utc_iso() if status == LEAD_NO_ANSWER else None
    with _conn() as conn:
        if status == LEAD_NO_ANSWER:
            conn.execute(
                "UPDATE users SET lead_status=?, no_answer_reminder_at=?, last_seen=? WHERE tg_id=?",
                (status, reminder_at, now_utc_iso(), tg_id),
            )
        elif status == LEAD_CALLED:
            conn.execute(
                "UPDATE users SET lead_status=?, no_answer_reminder_at=NULL, last_seen=? WHERE tg_id=?",
                (status, now_utc_iso(), tg_id),
            )
        else:
            conn.execute(
                "UPDATE users SET lead_status=?, last_seen=? WHERE tg_id=?",
                (status, now_utc_iso(), tg_id),
            )
        conn.commit()


def mark_reminder_sent(tg_id: int) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET reminder_sent_at=?, last_seen=? WHERE tg_id=?",
            (now_utc_iso(), now_utc_iso(), tg_id),
        )
        conn.commit()
    add_event(tg_id, "reminder_sent", "incomplete_registration")


def list_users(limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
    limit, offset = _normalize_limit_offset(limit, offset)
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def list_users_by_risk(risk: RiskProfile, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
    if risk not in RISK_PROFILES:
        return []
    limit, offset = _normalize_limit_offset(limit, offset)

    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE risk_profile=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (risk, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def list_users_by_status(status: LeadStatus, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
    if status not in LEAD_STATUSES:
        return []
    limit, offset = _normalize_limit_offset(limit, offset)

    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE lead_status=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (status, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def save_broadcast(admin_id: int, kind: str, file_id: str | None, text: str | None) -> None:
    kind = _clean_text(kind, 32) or "text"
    file_id = _clean_text(file_id, 512) or None
    text = _clean_text(text, 4000) or None

    with _conn() as conn:
        conn.execute(
            "INSERT INTO broadcasts (admin_id, kind, file_id, text, created_at) VALUES (?, ?, ?, ?, ?)",
            (admin_id, kind, file_id, text, now_utc_iso()),
        )
        conn.commit()
    add_event(admin_id, "broadcast_sent", kind)


def count_users() -> int:
    with _conn() as conn:
        return int(conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"])


def count_by_status(status: LeadStatus) -> int:
    with _conn() as conn:
        return int(conn.execute("SELECT COUNT(*) AS c FROM users WHERE lead_status=?", (status,)).fetchone()["c"])


def count_by_risk(risk: RiskProfile) -> int:
    with _conn() as conn:
        return int(conn.execute("SELECT COUNT(*) AS c FROM users WHERE risk_profile=?", (risk,)).fetchone()["c"])


def list_incomplete_users_for_reminder(hours: int = 24, limit: int = 100) -> list[dict[str, Any]]:
    from datetime import timedelta

    limit, _ = _normalize_limit_offset(limit, 0)

    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM users
            WHERE lead_status=?
              AND (phone IS NULL OR phone='' OR source IS NULL OR source='')
              AND (reminder_sent_at IS NULL OR reminder_sent_at='')
            ORDER BY last_seen ASC
            LIMIT ?
            """,
            (LEAD_NEW, limit * 5),
        ).fetchall()

    cutoff = parse_iso(now_utc_iso())
    if not cutoff:
        return []

    cutoff = cutoff - timedelta(hours=hours)
    result: list[dict[str, Any]] = []

    for row in rows:
        user = dict(row)
        last_seen = parse_iso(user.get("last_seen") or "")
        if last_seen and last_seen < cutoff:
            result.append(user)
            if len(result) >= limit:
                break

    return result


def list_no_answer_users_for_reminder(hours: int = 3, limit: int = 100) -> list[dict[str, Any]]:
    from datetime import timedelta

    limit, _ = _normalize_limit_offset(limit, 0)

    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM users
            WHERE lead_status=?
              AND phone IS NOT NULL
              AND phone!=''
            ORDER BY no_answer_reminder_at ASC
            LIMIT ?
            """,
            (LEAD_NO_ANSWER, limit * 5),
        ).fetchall()

    now = parse_iso(now_utc_iso())
    if not now:
        return []

    cutoff = now - timedelta(hours=hours)
    result: list[dict[str, Any]] = []

    for row in rows:
        user = dict(row)
        reminder_at = parse_iso(user.get("no_answer_reminder_at") or "")
        if reminder_at and reminder_at <= cutoff:
            result.append(user)
            if len(result) >= limit:
                break

    return result


def mark_no_answer_reminder_sent(tg_id: int) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET no_answer_reminder_at=?, last_seen=? WHERE tg_id=?",
            (now_utc_iso(), now_utc_iso(), tg_id),
        )
        conn.commit()
    add_event(tg_id, "reminder_sent", "no_answer_admin_reminder")
