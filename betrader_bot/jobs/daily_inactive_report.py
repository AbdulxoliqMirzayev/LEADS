# jobs/daily_inactive_report.py
from __future__ import annotations

from aiogram import Bot

from config import SETTINGS
from db import list_inactive_new_users
from utils import safe_username, fmt_int


def _build_report_text(users: list[dict]) -> str:
    if not users:
        return (
            "✅ **Kunlik lead report**\n\n"
            "Oxirgi 24 soatda gaplashilmagan yangi leadlar yo‘q."
        )

    lines = [
        "📋 **Kunlik lead report**",
        "",
        f"⏰ Oxirgi 24 soatda gaplashilmagan leadlar: **{len(users)} ta**",
        "",
    ]

    for i, u in enumerate(users, start=1):
        username = safe_username(u.get("username"))
        amount = u.get("amount")
        amount_txt = f"${fmt_int(amount)}" if amount else "-"

        exp = u.get("experienced")
        if exp == 1:
            exp_txt = "Ha"
        elif exp == 0:
            exp_txt = "Yo‘q"
        else:
            exp_txt = "-"

        lines.append(
            f"{i}. 👤 {u.get('full_name') or '-'} | {username}\n"
            f"   📊 Risk: {u.get('risk_profile') or '-'}\n"
            f"   💰 Summa: {amount_txt}\n"
            f"   📚 Tajriba: {exp_txt}\n"
            f"   📞 Telefon: {u.get('phone') or '-'}\n"
        )

    return "\n".join(lines)


async def send_daily_inactive_report(bot: Bot) -> None:
    """
    Har kuni adminlarga 24 soatda gaplashilmagan yangi leadlar ro'yxatini yuboradi.
    """
    if not SETTINGS.ADMIN_IDS:
        return

    users = list_inactive_new_users(hours=24, limit=100)
    text = _build_report_text(users)

    for admin_id in SETTINGS.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            # admin botni bloklagan bo‘lishi mumkin
            continue