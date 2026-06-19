# services/notify_service.py
from __future__ import annotations

from aiogram import Bot

from config import SETTINGS
from db import get_user, add_event
from keyboards import kb_lead_actions
from utils import safe_username, fmt_int


def _lead_card_text(u: dict) -> str:
    """
    Admin uchun user profili bo‘yicha chiroyli card.
    """
    username = safe_username(u.get("username"))
    exp = u.get("experienced")
    if exp == 1:
        exp_txt = "Ha"
    elif exp == 0:
        exp_txt = "Yo‘q"
    else:
        exp_txt = "-"

    amount = u.get("amount")
    amount_txt = f"${fmt_int(amount)}" if amount else "-"

    phone = u.get("phone") or "-"

    return (
        "🆕 Yangi Lead\n\n"
        f"👤 Ism: {u.get('full_name') or '-'}\n"
        f"🔗 Username: {username}\n"
        f"🆔 TG ID: {u.get('tg_id')}\n\n"
        f"📊 Risk: {u.get('risk_profile') or '-'}\n"
        f"📚 Tajriba: {exp_txt}\n"
        f"💰 Ajratmoqchi summa: {amount_txt}\n"
        f"📞 Telefon: {phone}\n\n"
        "✅/🤔/❌ Statusni belgilang:"
    )


async def notify_admin_new_lead(bot: Bot, tg_id: int) -> None:
    """
    User risk/profil kiritganda adminlarga xabar yuboradi.
    """
    if not SETTINGS.ADMIN_IDS:
        return

    u = get_user(tg_id)
    if not u:
        return

    text = _lead_card_text(u)

    for admin_id in SETTINGS.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                text,
                reply_markup=kb_lead_actions(tg_id),
            )
        except Exception:
            # Admin bloklagan bo‘lishi mumkin, yoki chat yo‘q
            pass

    add_event(tg_id, "menu_click", "lead_sent_to_admin")