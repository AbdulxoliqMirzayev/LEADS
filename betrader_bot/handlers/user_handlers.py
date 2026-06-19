# handlers/user_handlers.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from config import SETTINGS
from db import (
    add_event,
    get_user,
    set_amount,
    set_lang,
    set_name,
    set_phone,
    set_risk_profile,
    set_source,
    set_step,
    touch_last_seen,
    upsert_user,
)
from keyboards import (
    kb_admin_main,
    kb_language,
    kb_phone_request,
    kb_risk,
    kb_source,
    menu_labels,
)
from models import (
    LANG_UZ,
    Lang,
    RISK_HALOL,
    RISK_KONSERV,
    RISK_PROFILES,
    RISK_YUQORI,
    STEP_ASK_FREE_QUESTION,
    STEP_MAIN_MENU,
    STEP_WAIT_AMOUNT,
    STEP_WAIT_NAME,
    STEP_WAIT_PHONE,
    STEP_WAIT_RISK,
    STEP_WAIT_SOURCE,
)
from services.ai_service import ask_ai
from services.notify_service import notify_admin_new_lead
from texts import TEXT, risk_text
from utils import extract_amount, fmt_int, normalize_phone
from utils import is_admin

router = Router()

RISK_RATE_RANGES = {
    RISK_HALOL: (0.15, 0.18),
    RISK_KONSERV: (0.15, 0.18),
    RISK_YUQORI: (0.30, 0.50),
}

SOURCE_LABELS = {
    "telegram": "Telegram",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "tiktok": "TikTok",
    "other": "Other",
}

BACK_TEXTS = {
    "⬅️ Ortga",
    "Ortga",
    "⬅️ Назад",
    "Назад",
    "⬅️ Back",
    "Back",
}


def _clean_name(text: str) -> str:
    return " ".join((text or "").strip().split())


def _money(value: float) -> str:
    return f"{fmt_int(value)} USD"


def _profit_range(amount: float, risk: str, months: int) -> tuple[float, float]:
    low, high = RISK_RATE_RANGES[risk]
    return amount * low * months / 12, amount * high * months / 12


def _profit_text(lang: Lang, amount: float, risk: str) -> str:
    rows = []
    for label, months in (("1 oy", 1), ("3 oy", 3), ("6 oy", 6), ("1 yil", 12)):
        low, high = _profit_range(amount, risk, months)
        rows.append(f"{label}: {_money(low)} – {_money(high)}")

    if lang == "ru":
        title = "📊 Ориентировочный расчёт дохода"
        note = "⚠️ Это не гарантия. Фактическая прибыль зависит от состояния рынка."
    elif lang == "en":
        title = "📊 Estimated profit calculation"
        note = "⚠️ This is not guaranteed. Actual profit depends on market conditions."
        rows = [row.replace("1 oy", "1 month").replace("3 oy", "3 months").replace("6 oy", "6 months").replace("1 yil", "1 year") for row in rows]
    else:
        title = "📊 Taxminiy daromad hisob-kitobi"
        note = "⚠️ Bu kafolat emas. Real foyda bozor holatiga qarab o‘zgaradi."

    return (
        f"{risk_text(lang, risk)}\n\n"
        f"{title}\n"
        f"💵 Summa: {_money(amount)}\n\n"
        + "\n".join(rows)
        + f"\n\n{note}"
    )


@router.message(CommandStart())
async def cmd_start(m: Message):
    upsert_user(m.from_user.id, m.from_user.username, m.from_user.full_name)
    touch_last_seen(m.from_user.id)
    add_event(m.from_user.id, "start", "/start")

    if is_admin(m.from_user.id, SETTINGS.ADMIN_IDS):
        await m.answer("🔐 Admin panel", reply_markup=kb_admin_main(), parse_mode=None)
        return

    u = get_user(m.from_user.id)
    lang: Lang = (u.get("lang") if u else LANG_UZ) or LANG_UZ
    await m.answer(TEXT["choose_lang"][lang], reply_markup=kb_language())


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(c: CallbackQuery):
    tg_id = c.from_user.id
    lang = c.data.split(":", 1)[1].strip()
    if lang not in ("uz", "ru", "en"):
        lang = "uz"

    set_lang(tg_id, lang, STEP_WAIT_NAME)
    touch_last_seen(tg_id)

    await c.message.answer(TEXT["ask_name"][lang])
    await c.answer()


@router.message(F.text | F.contact)
async def on_text(m: Message):
    tg_id = m.from_user.id
    text = (m.text or "").strip()

    upsert_user(tg_id, m.from_user.username, m.from_user.full_name)
    touch_last_seen(tg_id)

    u = get_user(tg_id)
    if not u:
        await m.answer("Xatolik: user topilmadi. /start bosing.")
        return

    lang: Lang = u.get("lang", LANG_UZ) or LANG_UZ
    step = u.get("step")
    labels = menu_labels(lang)

    if text in BACK_TEXTS:
        if step == STEP_WAIT_PHONE:
            set_step(tg_id, STEP_WAIT_RISK)
            await m.answer(TEXT["ask_risk"][lang], reply_markup=kb_risk(lang))
            return
        if step == STEP_WAIT_AMOUNT:
            set_step(tg_id, STEP_WAIT_NAME)
            await m.answer(TEXT["ask_name"][lang], reply_markup=ReplyKeyboardRemove())
            return
        set_step(tg_id, STEP_MAIN_MENU)
        await m.answer(TEXT["menu_hint"][lang], reply_markup=ReplyKeyboardRemove())
        return

    if step == STEP_WAIT_NAME:
        name = _clean_name(text)
        if len(name) < 2:
            await m.answer(TEXT["ask_name"][lang])
            return

        set_name(tg_id, name, STEP_WAIT_AMOUNT)
        await m.answer(TEXT["ask_amount"][lang])
        return

    if step == STEP_WAIT_AMOUNT:
        amount = extract_amount(text)
        if not amount:
            await m.answer(TEXT["invalid_amount"][lang])
            return

        set_amount(tg_id, amount, STEP_WAIT_RISK)
        await m.answer(TEXT["ask_risk"][lang], reply_markup=kb_risk(lang))
        return

    if step == STEP_WAIT_PHONE:
        if m.contact and m.contact.phone_number:
            phone = m.contact.phone_number
        else:
            phone = normalize_phone(text)

        if not phone:
            await m.answer(TEXT["invalid_phone"][lang], reply_markup=kb_phone_request(lang))
            return

        set_phone(tg_id, phone, STEP_WAIT_SOURCE)
        await m.answer(TEXT["phone_saved"][lang], reply_markup=ReplyKeyboardRemove())
        await m.answer(TEXT["ask_source"][lang], reply_markup=kb_source())
        return

    if text == labels["risks"]:
        set_step(tg_id, STEP_WAIT_RISK)
        await m.answer(TEXT["ask_risk"][lang], reply_markup=kb_risk(lang))
        return

    if text == labels["invest"]:
        await m.answer(TEXT["investment_info"][lang], reply_markup=ReplyKeyboardRemove())
        return

    if text == labels["company"] or text == labels["contact"]:
        await m.answer(TEXT["company_about"][lang], reply_markup=ReplyKeyboardRemove())
        return

    if text == labels["payout"]:
        await m.answer(TEXT["payout_info"][lang], reply_markup=ReplyKeyboardRemove())
        return

    if text == labels["withdraw"]:
        await m.answer(TEXT["withdraw_info"][lang], reply_markup=ReplyKeyboardRemove())
        return

    if text == labels["discount"]:
        await m.answer(TEXT["discount"][lang], reply_markup=ReplyKeyboardRemove())
        return

    if text == labels["ask"]:
        set_step(tg_id, STEP_ASK_FREE_QUESTION)
        await m.answer(TEXT["ask_free_question"][lang], reply_markup=ReplyKeyboardRemove())
        return

    if text == labels["back"]:
        set_step(tg_id, STEP_MAIN_MENU)
        await m.answer(TEXT["menu_hint"][lang], reply_markup=ReplyKeyboardRemove())
        return

    add_event(tg_id, "free_question", text[:200])
    ai_reply = await ask_ai(lang, text)
    await m.answer(ai_reply, reply_markup=ReplyKeyboardRemove())


@router.callback_query(F.data.startswith("risk:"))
async def cb_risk(c: CallbackQuery):
    tg_id = c.from_user.id
    u = get_user(tg_id)
    lang: Lang = (u.get("lang") if u else LANG_UZ) or LANG_UZ

    value = c.data.split(":", 1)[1].strip()

    if value == "back":
        set_step(tg_id, STEP_WAIT_AMOUNT)
        await c.message.answer(TEXT["ask_amount"][lang])
        await c.answer()
        return

    if value not in RISK_PROFILES:
        await c.answer("Invalid risk", show_alert=True)
        return

    amount = float((u or {}).get("amount") or 0)
    if amount <= 0:
        set_step(tg_id, STEP_WAIT_AMOUNT)
        await c.message.answer(TEXT["ask_amount"][lang])
        await c.answer()
        return

    set_risk_profile(tg_id, value, STEP_WAIT_PHONE)
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await c.message.answer(_profit_text(lang, amount, value))
    await c.message.answer(TEXT["ask_phone"][lang], reply_markup=kb_phone_request(lang))
    await c.answer()


@router.callback_query(F.data.startswith("source:"))
async def cb_source(c: CallbackQuery):
    tg_id = c.from_user.id
    u = get_user(tg_id)
    lang: Lang = (u.get("lang") if u else LANG_UZ) or LANG_UZ

    source = c.data.split(":", 1)[1].strip()
    if source not in SOURCE_LABELS:
        await c.answer("Invalid source", show_alert=True)
        return

    set_source(tg_id, SOURCE_LABELS[source], STEP_MAIN_MENU)
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await notify_admin_new_lead(c.bot, tg_id)
    await c.message.answer(TEXT["registration_done"][lang], reply_markup=ReplyKeyboardRemove())
    await c.answer()
