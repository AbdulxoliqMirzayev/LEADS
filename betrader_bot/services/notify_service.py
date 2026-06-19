from __future__ import annotations

from aiogram import Bot

from config import SETTINGS
from db import add_event, get_user
from keyboards import kb_lead_actions
from services.google_sheets_service import sync_lead_to_google_sheet
from utils import fmt_int, safe_username


def _lead_card_text(u: dict) -> str:
    name = u.get("name") or u.get("full_name") or "-"
    username = safe_username(u.get("username"))
    amount = u.get("amount")
    amount_txt = f"{fmt_int(amount)} USD" if amount else "-"
    phone = u.get("phone") or "-"
    risk = u.get("risk_profile") or "-"
    source = u.get("source") or "-"
    created_at = u.get("created_at") or "-"

    return (
        "🆕 Yangi foydalanuvchi\n\n"
        f"👤 Ism: {name}\n"
        f"📞 Tel: {phone}\n"
        f"💰 Summa: {amount_txt}\n"
        f"📈 Risk: {risk}\n"
        f"📍 Manba: {source}\n"
        f"🔗 Username: {username}\n"
        f"🆔 ID: {u.get('tg_id')}\n"
        f"🕒 Sana: {created_at}\n\n"
        "Statusni belgilang:"
    )


async def notify_admin_new_lead(bot: Bot, tg_id: int) -> None:
    """
    Ro'yxatdan o'tish tugaganda Google Sheetsga yozadi va adminlarga xabar yuboradi.
    """
    u = get_user(tg_id)
    if not u:
        return

    await sync_lead_to_google_sheet(u)

    if not SETTINGS.ADMIN_IDS:
        return

    for admin_id in SETTINGS.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                _lead_card_text(u),
                reply_markup=kb_lead_actions(tg_id),
                parse_mode=None,
            )
        except Exception:
            pass

    add_event(tg_id, "menu_click", "lead_sent_to_admin")
