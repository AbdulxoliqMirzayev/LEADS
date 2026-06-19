# utils.py
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from models import Lang, LANG_UZ, LANG_RU, LANG_EN


# =========================
# Time helpers
# =========================
def now_utc_iso() -> str:
    """
    ISO format UTC time string, e.g. '2026-02-24T06:12:34.123456+00:00'
    """
    return datetime.now(timezone.utc).isoformat()


def parse_iso(dt_str: str) -> Optional[datetime]:
    """
    Safe ISO datetime parser. Returns None if invalid.
    """
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


# =========================
# Admin helper
# =========================
def is_admin(user_id: int, admin_ids: set[int]) -> bool:
    """
    If admin_ids is empty -> dev mode: allow everyone as admin.
    If you want strict admin only, set ADMIN_IDS in .env.
    """
    if not admin_ids:
        return True
    return user_id in admin_ids


# =========================
# Parsing helpers
# =========================
def extract_amount(text: str) -> Optional[float]:
    """
    Extract numeric amount from user message.
    Supports: '1000', '10 000', '1,000', '1.000.000', '5k' (simple).
    Returns float or None.
    """
    if not text:
        return None

    t = text.strip().lower()

    # Handle shorthand '5k', '10k'
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*k\s*$", t)
    if m:
        try:
            val = float(m.group(1)) * 1000
            return val if val > 0 else None
        except Exception:
            return None

    # Keep digits only
    digits = re.findall(r"\d+", t)
    if not digits:
        return None

    try:
        val = float("".join(digits))
        return val if val > 0 else None
    except Exception:
        return None


def normalize_phone(text: str) -> Optional[str]:
    """
    Normalize phone number. Very simple.
    Accepts: +998901234567, 998901234567, 90 123 45 67, etc.
    Returns normalized string like '+998901234567' or None.
    """
    if not text:
        return None

    t = text.strip()
    t = re.sub(r"[^\d+]", "", t)  # keep digits and +

    # If starts with 998..., add +
    if t.startswith("998") and not t.startswith("+"):
        t = "+" + t

    # If starts with 0 and looks like local, you may handle it:
    # Example: 901234567 -> +998901234567 (optional)
    # We'll keep it simple:
    if len(re.findall(r"\d", t)) < 7:
        return None

    return t


def parse_yes_no(text: str, lang: Lang) -> Optional[bool]:
    """
    Parse yes/no based on selected language.
    Returns True/False or None if not recognized.
    """
    if not text:
        return None
    t = text.strip().lower()

    if lang == LANG_EN:
        if t in ("yes", "y", "yeah", "yep", "sure"):
            return True
        if t in ("no", "n", "nope"):
            return False

    elif lang == LANG_RU:
        if t in ("да", "ага", "конечно"):
            return True
        if t in ("нет", "неа"):
            return False

    else:  # LANG_UZ
        # Uzbek inputs: ha/yo'q variants
        if t in ("ha", "xa", "haa", "albatta"):
            return True
        if t in ("yo'q", "yo‘q", "yoq", "yuq", "emas"):
            return False

    return None


# =========================
# Formatting helpers
# =========================
def fmt_int(n: float | int) -> str:
    """
    10000 -> '10 000'
    """
    try:
        return f"{int(n):,}".replace(",", " ")
    except Exception:
        return str(n)


def safe_username(username: Optional[str]) -> str:
    """
    Convert username to @username, or '-' if empty.
    """
    if not username:
        return "-"
    username = username.strip()
    if not username:
        return "-"
    return username if username.startswith("@") else "@" + username