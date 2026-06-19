from __future__ import annotations

from aiogram import Bot

from config import SETTINGS
from db import list_no_answer_users_for_reminder, mark_no_answer_reminder_sent
from keyboards import kb_lead_actions
from utils import fmt_int, safe_username


def _reminder_text(user: dict) -> str:
    name = user.get("name") or user.get("full_name") or "-"
    username = safe_username(user.get("username"))
    amount = user.get("amount")
    amount_txt = f"{fmt_int(amount)} USD" if amount else "-"

    return (
        "🔁 Qayta eslatma — telefon ko'tarmadi\n\n"
        f"👤 Ism: {name}\n"
        f"📞 Tel: {user.get('phone') or '-'}\n"
        f"💰 Summa: {amount_txt}\n"
        f"📈 Risk: {user.get('risk_profile') or '-'}\n"
        f"📍 Manba: {user.get('source') or '-'}\n"
        f"🔗 Username: {username}\n"
        f"🆔 ID: {user.get('tg_id')}\n\n"
        "User bilan gaplashsangiz ✅ Gaplashildi tugmasini bosing."
    )


async def send_no_answer_reminders(bot: Bot) -> None:
    if not SETTINGS.ADMIN_IDS:
        return

    users = list_no_answer_users_for_reminder(hours=3, limit=100)
    for user in users:
        tg_id = user.get("tg_id")
        if not tg_id:
            continue

        sent = False
        for admin_id in SETTINGS.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    _reminder_text(user),
                    reply_markup=kb_lead_actions(tg_id),
                    parse_mode=None,
                )
                sent = True
            except Exception:
                continue

        if sent:
            mark_no_answer_reminder_sent(tg_id)
