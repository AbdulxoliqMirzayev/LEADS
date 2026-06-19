# handlers/admin_handlers.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from config import SETTINGS
from utils import is_admin, safe_username, fmt_int
from db import (
    get_user,
    set_lead_status,
    add_event,
    list_users_by_risk,
    list_users_by_status,
    count_users,
    count_by_risk,
    count_by_status,
)
from models import (
    ADMIN_MARK_EVENT, RiskProfile, LeadStatus,
    RISK_HALOL, RISK_KONSERV, RISK_YUQORI,
    LEAD_NEW, LEAD_CALLED, LEAD_NO_ANSWER,
)
from keyboards import (
    kb_admin_main,
    kb_admin_risk_menu,
    kb_admin_status_menu,
)
from services.google_sheets_service import sync_lead_to_google_sheet

router = Router()


# -------------------------
# Helpers
# -------------------------
def _deny_text() -> str:
    return "⛔ Siz admin emassiz."


def _stats_text() -> str:
    total = count_users()

    new = count_by_status(LEAD_NEW)
    called = count_by_status(LEAD_CALLED)
    no_answer = count_by_status(LEAD_NO_ANSWER)

    halol = count_by_risk(RISK_HALOL)
    kons = count_by_risk(RISK_KONSERV)
    yuq = count_by_risk(RISK_YUQORI)

    return (
        "📊 Admin Statistika\n\n"
        f"👥 Jami user: {total}\n"
        f"🆕 Yangi: {new}\n"
        f"✅ Gaplashildi: {called}\n"
        f"📵 Telefon ko‘tarmadi: {no_answer}\n\n"
        "📌 Risk bo‘yicha:\n"
        f"🟢 Halol: {halol}\n"
        f"🟡 Konservativ: {kons}\n"
        f"🔴 Yuqori: {yuq}\n"
    )


def _lead_line(u: dict) -> str:
    username = safe_username(u.get("username"))
    amount = u.get("amount")
    amount_txt = f"${fmt_int(amount)}" if amount else "-"
    risk = u.get("risk_profile") or "-"
    phone = u.get("phone") or "-"
    status = u.get("lead_status") or "-"
    name = u.get("name") or u.get("full_name") or "-"
    tg_id = u.get("tg_id")

    return f"• {name} | {username} | ID={tg_id} | risk={risk} | summa={amount_txt} | tel={phone} | status={status}"


def _risk_title(risk: RiskProfile) -> str:
    if risk == RISK_HALOL:
        return "🟢 Halol"
    if risk == RISK_KONSERV:
        return "🟡 Konservativ"
    return "🔴 Yuqori"


def _status_title(status: LeadStatus) -> str:
    if status == LEAD_CALLED:
        return "✅ Gaplashildi"
    if status == LEAD_NO_ANSWER:
        return "📵 Telefon ko‘tarmadi"
    return "🆕 Yangi"


# -------------------------
# /admin
# -------------------------
@router.message(F.text == "/admin")
async def admin_entry(m: Message):
    if not is_admin(m.from_user.id, SETTINGS.ADMIN_IDS):
        await m.answer(_deny_text())
        return

    await m.answer("🔐 Admin panel", reply_markup=kb_admin_main(), parse_mode=None)
    add_event(m.from_user.id, "menu_click", "admin_open")


# -------------------------
# Admin callbacks
# -------------------------
@router.callback_query(F.data.startswith("admin:"))
async def admin_callbacks(c: CallbackQuery):
    if not is_admin(c.from_user.id, SETTINGS.ADMIN_IDS):
        await c.answer("No access", show_alert=True)
        return

    action = c.data.split(":", 1)[1]

    if action == "main":
        await c.message.edit_text("🔐 Admin panel", reply_markup=kb_admin_main(), parse_mode=None)
        await c.answer()
        return

    if action == "close":
        await c.message.edit_text("✅ Yopildi.", parse_mode=None)
        await c.answer()
        return

    if action == "stats":
        await c.message.edit_text(_stats_text(), reply_markup=kb_admin_main(), parse_mode=None)
        add_event(c.from_user.id, "menu_click", "admin_stats")
        await c.answer()
        return

    if action == "risk_menu":
        await c.message.edit_text("📂 Risk bo‘yicha leadlar", reply_markup=kb_admin_risk_menu(), parse_mode=None)
        add_event(c.from_user.id, "menu_click", "admin_risk_menu")
        await c.answer()
        return

    if action == "status_menu":
        await c.message.edit_text("✅/📵 Status bo‘yicha", reply_markup=kb_admin_status_menu(), parse_mode=None)
        add_event(c.from_user.id, "menu_click", "admin_status_menu")
        await c.answer()
        return

    # broadcast tugmasi ad_handlers.py da ushlanadi (keyingi bosqichda)
    if action == "broadcast":
        await c.answer()
        return

    await c.answer("Unknown", show_alert=False)


# -------------------------
# Risk list callbacks
# -------------------------
@router.callback_query(F.data.startswith("admin_risk:"))
async def admin_risk_list(c: CallbackQuery):
    if not is_admin(c.from_user.id, SETTINGS.ADMIN_IDS):
        await c.answer("No access", show_alert=True)
        return

    risk = c.data.split(":", 1)[1].strip()
    if risk not in (RISK_HALOL, RISK_KONSERV, RISK_YUQORI):
        await c.answer("Invalid risk", show_alert=True)
        return

    users = list_users_by_risk(risk, limit=50, offset=0)

    title = _risk_title(risk)
    lines = [f"{title} — {len(users)} ta (birinchi 50 ta)\n"]
    if not users:
        lines.append("Hozircha user yo‘q.")
    else:
        for u in users:
            lines.append(_lead_line(u))

    await c.message.edit_text("\n".join(lines), reply_markup=kb_admin_risk_menu(), parse_mode=None)
    add_event(c.from_user.id, "menu_click", f"admin_risk_list:{risk}")
    await c.answer()


# -------------------------
# Status list callbacks
# -------------------------
@router.callback_query(F.data.startswith("admin_status:"))
async def admin_status_list(c: CallbackQuery):
    if not is_admin(c.from_user.id, SETTINGS.ADMIN_IDS):
        await c.answer("No access", show_alert=True)
        return

    status = c.data.split(":", 1)[1].strip()
    if status not in (LEAD_NEW, LEAD_CALLED, LEAD_NO_ANSWER):
        await c.answer("Invalid status", show_alert=True)
        return

    users = list_users_by_status(status, limit=50, offset=0)

    title = _status_title(status)
    lines = [f"{title} — {len(users)} ta (birinchi 50 ta)\n"]
    if not users:
        lines.append("Hozircha user yo‘q.")
    else:
        for u in users:
            lines.append(_lead_line(u))

    await c.message.edit_text("\n".join(lines), reply_markup=kb_admin_status_menu(), parse_mode=None)
    add_event(c.from_user.id, "menu_click", f"admin_status_list:{status}")
    await c.answer()


# -------------------------
# Lead status set callback (from lead card buttons)
# callback: lead_set:<tg_id>:called|no_answer
# -------------------------
@router.callback_query(F.data.startswith("lead_set:"))
async def lead_set_status(c: CallbackQuery):
    if not is_admin(c.from_user.id, SETTINGS.ADMIN_IDS):
        await c.answer("No access", show_alert=True)
        return

    try:
        payload = c.data.split(":", 1)[1]  # "<tg_id>:<status>"
        tg_id_s, status = payload.split(":", 1)
        tg_id = int(tg_id_s)
    except Exception:
        await c.answer("Bad data", show_alert=True)
        return

    if status not in (LEAD_CALLED, LEAD_NO_ANSWER):
        await c.answer("Invalid status", show_alert=True)
        return

    # DB save
    set_lead_status(tg_id, status)
    user = get_user(tg_id)
    if user:
        await sync_lead_to_google_sheet(user)
    add_event(tg_id, ADMIN_MARK_EVENT[status], f"admin_id:{c.from_user.id}")

    # confirmation
    await c.answer("✅ Saqlandi", show_alert=False)
    try:
        await c.message.edit_text(
            f"{c.message.text}\n\n✅ Status saqlandi: {_status_title(status)}",
            parse_mode=None,
        )
    except Exception:
        pass
