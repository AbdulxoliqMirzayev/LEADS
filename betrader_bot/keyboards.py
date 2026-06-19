# keyboards.py
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)

from models import (
    Lang, LANG_UZ, LANG_RU, LANG_EN,
    RiskProfile, RISK_HALOL, RISK_KONSERV, RISK_YUQORI,
    LeadStatus, LEAD_PAID, LEAD_THINKING, LEAD_REJECTED,
)
from texts import t


# =========================
# CALLBACK DATA (single source of truth)
# =========================
# User
CB_LANG_PREFIX = "lang:"                # lang:uz
CB_RISK_PREFIX = "risk:"                # risk:halol | risk:back
CB_MENU_PREFIX = "menu:"                # menu:invest | menu:risk | ...

# Admin
CB_ADMIN_PREFIX = "admin:"              # admin:main, admin:stats...
CB_ADMIN_RISK_PREFIX = "admin_risk:"    # admin_risk:halol
CB_ADMIN_STATUS_PREFIX = "admin_status:"  # admin_status:paid
CB_LEAD_SET_PREFIX = "lead_set:"        # lead_set:<tg_id>:paid

# Ads
CB_ADMIN_BROADCAST = "admin:broadcast"  # start broadcast flow


# =========================
# Language selection
# =========================
def kb_language() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O‘zbek", callback_data=f"{CB_LANG_PREFIX}{LANG_UZ}"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data=f"{CB_LANG_PREFIX}{LANG_RU}"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data=f"{CB_LANG_PREFIX}{LANG_EN}"),
    ]])


# =========================
# Yes / No (experience)
# =========================
def kb_yes_no(lang: Lang) -> ReplyKeyboardMarkup:
    yes = t(lang, "Ha", "Да", "Yes")
    no = t(lang, "Yo‘q", "Нет", "No")
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=yes), KeyboardButton(text=no)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


# =========================
# User Main Menu (Reply keyboard)
# =========================
def kb_user_menu(lang: Lang) -> ReplyKeyboardMarkup:
    """
    ReplyKeyboard: foydalanuvchi uchun asosiy menyu.
    Handlerlarda text bo'yicha emas, aynan shu tugmalar matnini tekshiramiz.
    """
    invest = t(lang, "📈 Investitsiya", "📈 Инвестиции", "📈 Investment")
    risks = t(lang, "⚡ Risklar", "⚡ Риски", "⚡ Risks")
    company = t(lang, "🏢 Kompaniya", "🏢 О компании", "🏢 Company")
    payout = t(lang, "💰 To‘lovlar", "💰 Выплаты", "💰 Payouts")
    withdraw = t(lang, "💸 Pul yechish", "💸 Вывод", "💸 Withdraw")
    contact = t(lang, "📞 Kontakt", "📞 Контакты", "📞 Contact")
    ask = t(lang, "❓ Savol", "❓ Вопрос", "❓ Ask")
    discount = t(lang, "🎁 Chegirma", "🎁 Промокод", "🎁 Promo")
    back = t(lang, "⬅️ Ortga", "⬅️ Назад", "⬅️ Back")

    kb = [
        [KeyboardButton(text=invest), KeyboardButton(text=risks)],
        [KeyboardButton(text=company), KeyboardButton(text=payout)],
        [KeyboardButton(text=withdraw), KeyboardButton(text=contact)],
        [KeyboardButton(text=discount), KeyboardButton(text=ask)],
        [KeyboardButton(text=back)],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# =========================
# Risk choose (Inline)
# =========================
def kb_risk(lang: Lang) -> InlineKeyboardMarkup:
    a = t(lang, "🟢 Halol (past)", "🟢 Низкий риск", "🟢 Low risk")
    b = t(lang, "🟡 Konservativ (o‘rta)", "🟡 Средний риск", "🟡 Medium risk")
    c = t(lang, "🔴 Yuqori (agressiv)", "🔴 Высокий риск", "🔴 High risk")
    back = t(lang, "⬅️ Ortga", "⬅️ Назад", "⬅️ Back")

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=a, callback_data=f"{CB_RISK_PREFIX}{RISK_HALOL}")],
        [InlineKeyboardButton(text=b, callback_data=f"{CB_RISK_PREFIX}{RISK_KONSERV}")],
        [InlineKeyboardButton(text=c, callback_data=f"{CB_RISK_PREFIX}{RISK_YUQORI}")],
        [InlineKeyboardButton(text=back, callback_data=f"{CB_RISK_PREFIX}back")],
    ])


# =========================
# Admin panel main
# =========================
def kb_admin_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data=f"{CB_ADMIN_PREFIX}stats")],
        [InlineKeyboardButton(text="📂 Risk bo‘yicha", callback_data=f"{CB_ADMIN_PREFIX}risk_menu")],
        [InlineKeyboardButton(text="✅/🤔/❌ Status bo‘yicha", callback_data=f"{CB_ADMIN_PREFIX}status_menu")],
        [InlineKeyboardButton(text="📢 Reklama yuborish", callback_data=CB_ADMIN_BROADCAST)],
        [InlineKeyboardButton(text="❌ Yopish", callback_data=f"{CB_ADMIN_PREFIX}close")],
    ])


def kb_admin_risk_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Halol", callback_data=f"{CB_ADMIN_RISK_PREFIX}{RISK_HALOL}")],
        [InlineKeyboardButton(text="🟡 Konservativ", callback_data=f"{CB_ADMIN_RISK_PREFIX}{RISK_KONSERV}")],
        [InlineKeyboardButton(text="🔴 Yuqori", callback_data=f"{CB_ADMIN_RISK_PREFIX}{RISK_YUQORI}")],
        [InlineKeyboardButton(text="⬅️ Ortga", callback_data=f"{CB_ADMIN_PREFIX}main")],
    ])


def kb_admin_status_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Investitsiya qildi", callback_data=f"{CB_ADMIN_STATUS_PREFIX}{LEAD_PAID}")],
        [InlineKeyboardButton(text="🤔 O‘ylab ko‘rmoqda", callback_data=f"{CB_ADMIN_STATUS_PREFIX}{LEAD_THINKING}")],
        [InlineKeyboardButton(text="❌ Rad", callback_data=f"{CB_ADMIN_STATUS_PREFIX}{LEAD_REJECTED}")],
        [InlineKeyboardButton(text="⬅️ Ortga", callback_data=f"{CB_ADMIN_PREFIX}main")],
    ])


# =========================
# Lead action (admin marks result after call)
# =========================
def kb_lead_actions(tg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Investitsiya qildi", callback_data=f"{CB_LEAD_SET_PREFIX}{tg_id}:{LEAD_PAID}"),
            InlineKeyboardButton(text="🤔 O‘ylab ko‘rmoqda", callback_data=f"{CB_LEAD_SET_PREFIX}{tg_id}:{LEAD_THINKING}"),
        ],
        [
            InlineKeyboardButton(text="❌ Rad", callback_data=f"{CB_LEAD_SET_PREFIX}{tg_id}:{LEAD_REJECTED}"),
        ],
    ])

def kb_phone_request(lang: Lang) -> ReplyKeyboardMarkup:
    send_contact = t(lang, "📲 Kontakt yuborish", "📲 Отправить контакт", "📲 Send contact")
    back = t(lang, "⬅️ Ortga", "⬅️ Назад", "⬅️ Back")

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=send_contact, request_contact=True)],
            [KeyboardButton(text=back)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )