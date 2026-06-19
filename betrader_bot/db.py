# db.py
from __future__ import annotations

import sqlite3
from typing import Any, Optional, Iterable

from config import SETTINGS
from utils import now_utc_iso, parse_iso
from models import (
    Lang, Step, RiskProfile, LeadStatus, EventType,
    LANG_UZ,
    STEP_CHOOSE_LANG,
    LEAD_NEW,
)


# =========================
# Connection helpers
# =========================
def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(SETTINGS.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Create tables if not exist.
    """
    with _conn() as conn:
        cur = conn.cursor()

        # USERS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,

            lang TEXT NOT NULL DEFAULT 'uz',
            step TEXT NOT NULL DEFAULT 'choose_lang',

            experienced INTEGER,
            risk_profile TEXT,
            amount REAL,
            phone TEXT,

            lead_status TEXT NOT NULL DEFAULT 'new',

            created_at TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
        """)

        # EVENTS (for stats/analytics)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT,
            created_at TEXT NOT NULL
        )
        """)

        # BROADCASTS (admin ads log)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            kind TEXT NOT NULL,         -- text/photo/video/document
            file_id TEXT,
            text TEXT,
            created_at TEXT NOT NULL
        )
        """)

        # Useful indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_lead_status ON users(lead_status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_risk ON users(risk_profile)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_events_type_time ON events(event_type, created_at)")
        conn.commit()


# =========================
# Generic helpers
# =========================
def _row_to_dict(row: sqlite3.Row | None) -> Optional[dict[str, Any]]:
    return dict(row) if row else None


def add_event(tg_id: int, event_type: EventType, payload: str | None = None) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO events (tg_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
            (tg_id, event_type, payload, now_utc_iso()),
        )
        conn.commit()


# =========================
# Users CRUD
# =========================
def upsert_user(tg_id: int, username: str | None, full_name: str | None) -> None:
    """
    Create user if not exists, else update basic fields + last_seen.
    """
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
        conn.execute("UPDATE users SET lang=?, step=?, last_seen=? WHERE tg_id=?",
                     (lang, next_step, now_utc_iso(), tg_id))
        conn.commit()
    add_event(tg_id, "lang_set", lang)


def set_step(tg_id: int, step: Step) -> None:
    with _conn() as conn:
        conn.execute("UPDATE users SET step=?, last_seen=? WHERE tg_id=?",
                     (step, now_utc_iso(), tg_id))
        conn.commit()


def set_experience(tg_id: int, experienced: bool | None, next_step: Step) -> None:
    v = None if experienced is None else (1 if experienced else 0)
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET experienced=?, step=?, last_seen=? WHERE tg_id=?",
            (v, next_step, now_utc_iso(), tg_id)
        )
        conn.commit()
    add_event(tg_id, "experience_set", str(experienced))


def set_risk_profile(tg_id: int, risk: RiskProfile) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET risk_profile=?, last_seen=? WHERE tg_id=?",
            (risk, now_utc_iso(), tg_id)
        )
        conn.commit()
    add_event(tg_id, "risk_selected", risk)


def set_amount(tg_id: int, amount: float) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET amount=?, last_seen=? WHERE tg_id=?",
            (amount, now_utc_iso(), tg_id)
        )
        conn.commit()
    add_event(tg_id, "amount_set", str(amount))


def set_phone(tg_id: int, phone: str) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET phone=?, last_seen=? WHERE tg_id=?",
            (phone, now_utc_iso(), tg_id)
        )
        conn.commit()
    add_event(tg_id, "phone_set", phone)


def set_lead_status(tg_id: int, status: LeadStatus) -> None:
    with _conn() as conn:
        conn.execute("UPDATE users SET lead_status=?, last_seen=? WHERE tg_id=?",
                     (status, now_utc_iso(), tg_id))
        conn.commit()


# =========================
# List / Filters (for Admin)
# =========================
def list_users(limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        return [dict(r) for r in rows]


def list_users_by_risk(risk: RiskProfile, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE risk_profile=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (risk, limit, offset)
        ).fetchall()
        return [dict(r) for r in rows]


def list_users_by_status(status: LeadStatus, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE lead_status=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (status, limit, offset)
        ).fetchall()
        return [dict(r) for r in rows]


# =========================
# Broadcasts
# =========================
def save_broadcast(admin_id: int, kind: str, file_id: str | None, text: str | None) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO broadcasts (admin_id, kind, file_id, text, created_at) VALUES (?, ?, ?, ?, ?)",
            (admin_id, kind, file_id, text, now_utc_iso())
        )
        conn.commit()
    add_event(admin_id, "broadcast_sent", kind)


# =========================
# Stats helpers (fast counts)
# =========================
def count_users() -> int:
    with _conn() as conn:
        return int(conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"])


def count_by_status(status: LeadStatus) -> int:
    with _conn() as conn:
        return int(conn.execute("SELECT COUNT(*) AS c FROM users WHERE lead_status=?", (status,)).fetchone()["c"])


def count_by_risk(risk: RiskProfile) -> int:
    with _conn() as conn:
        return int(conn.execute("SELECT COUNT(*) AS c FROM users WHERE risk_profile=?", (risk,)).fetchone()["c"])


# =========================
# Inactive users (daily report)
# =========================
def list_inactive_new_users(hours: int = 24, limit: int = 100) -> list[dict[str, Any]]:
    """
    Return users with lead_status='new' who haven't been seen for N hours.
    SQLite does not compare ISO perfectly with timezones; simplest reliable:
    pull candidate rows then filter in Python.
    """
    from datetime import timedelta

    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE lead_status=? ORDER BY last_seen ASC LIMIT ?",
            (LEAD_NEW, limit * 5)  # take more, filter later
        ).fetchall()

    cutoff = parse_iso(now_utc_iso())
    if not cutoff:
        return []

    cutoff = cutoff - timedelta(hours=hours)
    result: list[dict[str, Any]] = []

    for r in rows:
        u = dict(r)
        ls = parse_iso(u.get("last_seen") or "")
        if ls and ls < cutoff:
            result.append(u)
            if len(result) >= limit:
                break

    return result