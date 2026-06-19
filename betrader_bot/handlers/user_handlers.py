# handlers/user_handlers.py
from __future__ import annotations
from keyboards import (
    kb_language, kb_yes_no, kb_user_menu, kb_risk,
)
from keyboards import (
    kb_language, kb_yes_no, kb_user_menu, kb_risk, kb_phone_request
)
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from utils import extract_amount, normalize_phone, parse_yes_no, fmt_int
from db import (
    upsert_user, touch_last_seen, get_user,
    set_lang, set_experience, set_step,
    set_risk_profile, set_amount, set_phone,
    add_event,
)
from models import (
    Lang, LANG_UZ,
    STEP_CHOOSE_EXPERIENCE, STEP_MAIN_MENU,
    STEP_WAIT_AMOUNT, STEP_WAIT_PHONE,
    STEP_ASK_FREE_QUESTION,
    RISK_PROFILES,
)
from texts import TEXT, risk_text
from keyboards import (
    kb_language, kb_yes_no, kb_user_menu, kb_risk,
)
from utils import extract_amount, normalize_phone, parse_yes_no
from services.ai_service import ask_ai
from services.notify_service import notify_admin_new_lead

router = Router()


# =========================
# /start
# =========================
@router.message(CommandStart())
async def cmd_start(m: Message):
    upsert_user(m.from_user.id, m.from_user.username, m.from_user.full_name)
    touch_last_seen(m.from_user.id)
    add_event(m.from_user.id, "start", "/start")

    u = get_user(m.from_user.id)
    lang: Lang = (u.get("lang") if u else LANG_UZ) or LANG_UZ

    await m.answer(TEXT["choose_lang"][lang], reply_markup=kb_language())


# =========================
# Language callback
# =========================
@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(c: CallbackQuery):
    tg_id = c.from_user.id
    lang = c.data.split(":", 1)[1].strip()
    if lang not in ("uz", "ru", "en"):
        lang = "uz"

    # DB update
    set_lang(tg_id, lang, STEP_CHOOSE_EXPERIENCE)
    touch_last_seen(tg_id)

    await c.message.answer(TEXT["ask_experience"][lang], reply_markup=kb_yes_no(lang))
    await c.answer()


# =========================
# Main text handler (experience, menu, steps, free questions)
# =========================
@router.message(F.text)
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

    # ---- Step: experience ----
    if step == STEP_CHOOSE_EXPERIENCE:
        yn = parse_yes_no(text, lang)
        # Recognize bo'lmasa ham False qilib yubormaymiz, qayta so'raymiz
        if yn is None:
            await m.answer(TEXT["ask_experience"][lang], reply_markup=kb_yes_no(lang))
            return

        set_experience(tg_id, yn, STEP_MAIN_MENU)
        await m.answer(TEXT["menu_hint"][lang], reply_markup=kb_user_menu(lang))
        return

    # ---- Step: amount ----
    if step == STEP_WAIT_AMOUNT:
        amt = extract_amount(text)
        if not amt:
            await m.answer(TEXT["invalid_amount"][lang])
            return

        set_amount(tg_id, amt)
        # keyingi: telefon
        set_step(tg_id, STEP_WAIT_PHONE)
        await m.answer(TEXT["amount_saved"][lang])
        await m.answer(TEXT["ask_phone"][lang])
        return

    # ---- Step: phone ----
    if step == STEP_WAIT_PHONE:
    # 1) agar contact yuborsa
     if m.contact and m.contact.phone_number:
        phone = m.contact.phone_number
    else:
        phone = normalize_phone(text)

    if not phone:
        await m.answer(TEXT["invalid_phone"][lang], reply_markup=kb_phone_request(lang))
        return

    set_phone(tg_id, phone)
    set_step(tg_id, STEP_MAIN_MENU)
    await m.answer(TEXT["phone_saved"][lang], reply_markup=kb_user_menu(lang))

    await notify_admin_new_lead(m.bot, tg_id)
    return

    # ---- Menu buttons ----
    # Tugmalarni texts.py dagi t(...) bilan emas, keyboards.py da yaratgan label bilan solishtiramiz.
    # Shuning uchun bu yerda har tilda variantlarni tekshiramiz.
    if text in ("⚡ Risklar", "⚡ Риски", "⚡ Risks"):
        add_event(tg_id, "menu_click", "risk_menu")
        await m.answer(TEXT["ask_risk"][lang], reply_markup=kb_risk(lang))
        return

    if text in ( "📈 Investitsiya nima?", "📈 Что такое инвестиции?", "📈 What is investing?"):
        add_event(tg_id, "menu_click", "investment_info")
        await m.answer(TEXT["investment_info"][lang], reply_markup=kb_user_menu(lang))
        return

    if text in ("🏢 Kompaniya", "🏢 О компании", "🏢 Company"):
        add_event(tg_id, "menu_click", "company_about")
        await m.answer(TEXT["company_about"][lang], reply_markup=kb_user_menu(lang))
        return

    if text in ("💰 To‘lovlar", "💰 Выплаты", "💰 Payouts"):
        add_event(tg_id, "menu_click", "payout_info")
        await m.answer(TEXT["payout_info"][lang], reply_markup=kb_user_menu(lang))
        return

    if text in ("💸 Pul yechish", "💸 Вывод", "💸 Withdraw"):
        add_event(tg_id, "menu_click", "withdraw_info")
        await m.answer(TEXT["withdraw_info"][lang], reply_markup=kb_user_menu(lang))
        return

    if text in ("📞 Kontakt", "📞 Контакты", "📞 Contact"):
        add_event(tg_id, "menu_click", "contact")
        # company_about ichida kontaktlar bor, lekin alohida ham chiqaramiz
        await m.answer(TEXT["company_about"][lang], reply_markup=kb_user_menu(lang))
        return

    if text in ("🎁 Chegirma", "🎁 Промокод", "🎁 Promo"):
        add_event(tg_id, "menu_click", "discount")
        await m.answer(TEXT["discount"][lang], reply_markup=kb_user_menu(lang))
        return

    if text in ("❓ Savol", "❓ Вопрос", "❓ Ask"):
        add_event(tg_id, "menu_click", "ask_free_question")
        set_step(tg_id, STEP_ASK_FREE_QUESTION)
        await m.answer(TEXT["ask_free_question"][lang], reply_markup=kb_user_menu(lang))
        return

    if text in ("⬅️ Ortga", "⬅️ Назад", "⬅️ Back"):
        set_step(tg_id, STEP_MAIN_MENU)
        await m.answer(TEXT["menu_hint"][lang], reply_markup=kb_user_menu(lang))
        return

    # ---- Free questions fallback (AI) ----
    add_event(tg_id, "free_question", text[:200])

    ai_reply = await ask_ai(lang, text)
    await m.answer(ai_reply, reply_markup=kb_user_menu(lang))


# =========================
# Risk callback
# =========================
@router.callback_query(F.data.startswith("risk:"))
async def cb_risk(c: CallbackQuery):
    tg_id = c.from_user.id
    u = get_user(tg_id)
    lang: Lang = (u.get("lang") if u else LANG_UZ) or LANG_UZ

    val = c.data.split(":", 1)[1].strip()

    if val == "back":
        set_step(tg_id, STEP_MAIN_MENU)
        await c.message.answer(TEXT["menu_hint"][lang], reply_markup=kb_user_menu(lang))
        await c.answer()
        return

    # Valid risk check
    if val not in RISK_PROFILES:
        await c.answer("Invalid risk", show_alert=True)
        return

    set_risk_profile(tg_id, val)  # DB + event
    set_step(tg_id, STEP_WAIT_AMOUNT)

    # risk info + next questions
    await c.message.answer(risk_text(lang, val))
    await c.message.answer(TEXT["ask_amount"][lang])
    await c.answer()

    # Admin notification (risk tanlangan zahoti)
    await notify_admin_new_lead(c.bot, tg_id)