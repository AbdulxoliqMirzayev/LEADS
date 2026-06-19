# db.py
from __future__ import annotations

import sqlite3
from typing import Any, Optional

from config import SETTINGS
from utils import now_utc_iso, parse_iso
from models import (
    EventType,
    Lang,
    LeadStatus,
    RiskProfile,
    Step,
    LANG_UZ,
    STEP_CHOOSE_LANG,
    LEAD_NEW,
    LEAD_CALLED,
    LEAD_NO_ANSWER,
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(SETTINGS.DB_PATH)
    conn.row_factory = sqlite3.Row
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

        _ensure_column(cur, "users", "name", "TEXT")
        _ensure_column(cur, "users", "source", "TEXT")
        _ensure_column(cur, "users", "reminder_sent_at", "TEXT")
        _ensure_column(cur, "users", "no_answer_reminder_at", "TEXT")

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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_source ON users(source)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_events_type_time ON events(event_type, created_at)")
        conn.commit()


def _row_to_dict(row: sqlite3.Row | None) -> Optional[dict[str, Any]]:
    return dict(row) if row else None


def add_event(tg_id: int, event_type: EventType, payload: str | None = None) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO events (tg_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
            (tg_id, event_type, payload, now_utc_iso()),
        )
        conn.commit()


def get_google_sheet_uid() -> str:
    return SETTINGS.GOOGLE_SHEETS_SPREADSHEET_ID


def upsert_user(tg_id: int, username: str | None, full_name: str | None) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        exists = cur.execute("SELECT tg_id FROM users WHERE tg_id=?", (tg_id,)).fetchone()

        if exists:
            cur.execute(
                "UPDATE users SET username=?, full_name=?, last_seen=? WHERE tg_id=?",
                (username, full_name, now_utc_iso(), tg_id),
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
                now_utc_iso(), now_utc_iso()
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
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET lang=?, step=?, last_seen=? WHERE tg_id=?",
            (lang, next_step, now_utc_iso(), tg_id),
        )
        conn.commit()
    add_event(tg_id, "lang_set", lang)


def set_step(tg_id: int, step: Step) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET step=?, last_seen=? WHERE tg_id=?",
            (step, now_utc_iso(), tg_id),
        )
        conn.commit()


def set_name(tg_id: int, name: str, next_step: Step) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET name=?, step=?, last_seen=? WHERE tg_id=?",
            (name.strip(), next_step, now_utc_iso(), tg_id),
        )
        conn.commit()
    add_event(tg_id, "name_set", name.strip())


def set_amount(tg_id: int, amount: float, next_step: Step | None = None) -> None:
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
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET source=?, step=?, last_seen=? WHERE tg_id=?",
            (source, next_step, now_utc_iso(), tg_id),
        )
        conn.commit()
    add_event(tg_id, "source_set", source)


def set_lead_status(tg_id: int, status: LeadStatus) -> None:
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
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def list_users_by_risk(risk: RiskProfile, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE risk_profile=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (risk, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def list_users_by_status(status: LeadStatus, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE lead_status=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (status, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def save_broadcast(admin_id: int, kind: str, file_id: str | None, text: str | None) -> None:
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
