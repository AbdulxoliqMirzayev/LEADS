# main.py
import asyncio
import os
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, List

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart

from openai import OpenAI

# ================================
#  CONFIG
# ================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN topilmadi. Uni .env yoki environment variable sifatida yozing.")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY topilmadi. Uni .env yoki environment variable sifatida yozing.")

# Agar /admin faqat sizda ishlasin desangiz, bu yerga ID'ingizni yozing
# Masalan: ADMIN_IDS = [123456789]
ADMIN_IDS: List[int] = []

client = OpenAI(api_key=OPENAI_API_KEY)

# ================================
#  LANGUAGE CONSTANTS
# ================================

LANG_UZ = "uz"
LANG_RU = "ru"
LANG_EN = "en"


# ================================
#  USER STATE
# ================================

@dataclass
class UserState:
    language: str = LANG_UZ
    name: Optional[str] = None
    experienced: Optional[bool] = None
    risk_profile: Optional[str] = None  # "halol", "konservativ", "yuqori"
    last_amount: Optional[float] = None
    msg_count: int = 0
    awaiting_amount: bool = False
    conversation: List[Dict[str, str]] = field(default_factory=list)

    def lead_score(self) -> int:
        score = 0

        # Tajriba
        if self.experienced is True:
            score += 20
        elif self.experienced is False:
            score += 5

        # Risk profili
        if self.risk_profile == "halol":
            score += 5
        elif self.risk_profile == "konservativ":
            score += 15
        elif self.risk_profile == "yuqori":
            score += 25

        # Summaga qarab
        if self.last_amount:
            amt = self.last_amount
            if amt < 1000:
                score += 5
            elif 1000 <= amt < 5000:
                score += 15
            elif 5000 <= amt < 20000:
                score += 25
            else:
                score += 35

        # Xabarlar soni
        score += min(self.msg_count * 2, 20)

        return max(0, min(score, 100))

    def lead_segment(self) -> str:
        s = self.lead_score()
        if s < 40:
            return "Cold"
        elif s < 70:
            return "Warm"
        return "Hot"


user_states: Dict[int, UserState] = {}


def get_user_state(user_id: int) -> UserState:
    if user_id not in user_states:
        user_states[user_id] = UserState()
    return user_states[user_id]


def update_user_from_message(user: UserState, message: Message) -> None:
    if message.from_user:
        user.name = message.from_user.full_name


# ================================
#  KEYBOARDS
# ================================

def get_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O‘zbek", callback_data="lang_uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
            ]
        ]
    )


def get_yes_no_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == LANG_EN:
        yes, no = "Yes", "No"
    elif lang == LANG_RU:
        yes, no = "Да", "Нет"
    else:
        yes, no = "Ha", "Yo‘q"

    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=yes), KeyboardButton(text=no)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == LANG_EN:
        buttons = [
            "📈 What is investment?",
            "⚡ Risk types",
            "🏢 About company",
            "💰 Profit & payouts",
            "💸 Withdrawals",
            "📊 Prop trading conditions",
            "📞 Contact",
            "❓ Ask a question",
            "⬅️ Back to main",
        ]
    elif lang == LANG_RU:
        buttons = [
            "📈 Что такое инвестиции?",
            "⚡ Типы риска",
            "🏢 О компании",
            "💰 Прибыль и выплаты",
            "💸 Вывод средств",
            "📊 Условия prop-трейдинга",
            "📞 Контакты",
            "❓ Задать вопрос",
            "⬅️ В главное меню",
        ]
    else:
        buttons = [
            "📈 Investitsiya nima?",
            "⚡ Risk turlari",
            "🏢 Kompaniya haqida",
            "💰 Foyda va to‘lovlar",
            "💸 Pul yechish",
            "📊 Prop savdo shartlari",
            "📞 Bog‘lanish",
            "❓ Savol berish",
            "⬅️ Asosiy menyu",
        ]

    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=b)] for b in buttons],
        resize_keyboard=True,
    )


def get_risk_profile_keyboard(lang: str) -> InlineKeyboardMarkup:
    if lang == LANG_EN:
        halol = "🟢 Halal / Low risk"
        kons = "🟡 Conservative / Medium risk"
        yuq = "🔴 High return / High risk"
        back = "⬅️ Back to menu"
    elif lang == LANG_RU:
        halol = "🟢 Халал / Низкий риск"
        kons = "🟡 Консервативный / Средний риск"
        yuq = "🔴 Высокодоходный / Высокий риск"
        back = "⬅️ Назад в меню"
    else:
        halol = "🟢 Halol (past risk)"
        kons = "🟡 Konservativ (o‘rta risk)"
        yuq = "🔴 Yuqori daromadli (yuqori risk)"
        back = "⬅️ Asosiy menyuga"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=halol, callback_data="risk_halol")],
            [InlineKeyboardButton(text=kons, callback_data="risk_konservativ")],
            [InlineKeyboardButton(text=yuq, callback_data="risk_yuqori")],
            [InlineKeyboardButton(text=back, callback_data="risk_back_menu")],
        ]
    )


def get_admin_main_keyboard(lang: str) -> InlineKeyboardMarkup:
    if lang == LANG_EN:
        stats = "📊 Global stats"
        risk = "📂 Risk profiles"
        close = "❌ Close"
    elif lang == LANG_RU:
        stats = "📊 Общая статистика"
        risk = "📂 Профили риска"
        close = "❌ Закрыть"
    else:
        stats = "📊 Umumiy statistika"
        risk = "📂 Risk profillari"
        close = "❌ Yopish"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=stats, callback_data="admin_stats")],
            [InlineKeyboardButton(text=risk, callback_data="admin_risk_menu")],
            [InlineKeyboardButton(text=close, callback_data="admin_close")],
        ]
    )


def get_admin_risk_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    if lang == LANG_EN:
        halol = "🟢 Halal / Low"
        kons = "🟡 Conservative / Medium"
        yuq = "🔴 High return / High"
        back = "⬅️ Back"
    elif lang == LANG_RU:
        halol = "🟢 Халал / Низкий"
        kons = "🟡 Консервативный / Средний"
        yuq = "🔴 Высокодоходный / Высокий"
        back = "⬅️ Назад"
    else:
        halol = "🟢 Halol"
        kons = "🟡 Konservativ"
        yuq = "🔴 Yuqori daromadli"
        back = "⬅️ Ortga"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=halol, callback_data="admin_risk_halol")],
            [InlineKeyboardButton(text=kons, callback_data="admin_risk_konservativ")],
            [InlineKeyboardButton(text=yuq, callback_data="admin_risk_yuqori")],
            [InlineKeyboardButton(text=back, callback_data="admin_main")],
        ]
    )


# ================================
#  UTIL FUNKSIYALAR
# ================================

def parse_yes_no(text: str, lang: str) -> Optional[bool]:
    t = text.strip().lower()
    if lang == LANG_EN:
        if t in ("yes", "y", "yeah", "yep"):
            return True
        if t in ("no", "n", "nope"):
            return False
    elif lang == LANG_RU:
        if t == "да":
            return True
        if t == "нет":
            return False
    else:
        if t in ("ha", "xa"):
            return True
        if t in ("yo'q", "yo‘q", "yoq", "yuq"):
            return False
    return None


def extract_amount(text: str) -> Optional[float]:
    digits = re.findall(r"\d+", text.replace("'", "").replace("’", ""))
    if not digits:
        return None
    try:
        value = float("".join(digits))
        if value <= 0:
            return None
        return value
    except ValueError:
        return None


def fmt_number(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ")


def is_admin(user_id: int) -> bool:
    if not ADMIN_IDS:
        # Agar ADMIN_IDS bo'sh bo'lsa – hozircha hamma /admin ga kira oladi
        return True
    return user_id in ADMIN_IDS


# ================================
#  OPENAI INTEGRATSIYA
# ================================

async def ask_openai(user: UserState, user_text: str) -> str:
    """
    User bilan tabiiy suhbat uchun OpenAI'ga murojaat.
    """
    lang = user.language or LANG_UZ

    # Tilga mos izoh
    if lang == LANG_EN:
        lang_instruction = (
            "Always answer in English. Use 2–5 short paragraphs, simple language, light professional emojis. "
            "You are a senior financial advisor and prop trading mentor at BeTrader in Uzbekistan."
        )
    elif lang == LANG_RU:
        lang_instruction = (
            "Отвечай только на русском языке. 2–5 коротких абзацев, простым понятным языком, "
            "с лёгкими профессиональными эмодзи. Ты – старший финансовый консультант и prop-трейдинг ментор компании BeTrader в Узбекистане."
        )
    else:
        lang_instruction = (
            "Har doim faqat o‘zbek tilida javob ber. 2–5 ta qisqa paragraf, sodda til, yengil professional emoji ishlat. "
            "Sen BeTrader kompaniyasining katta moliyaviy maslahatchisi va prop treyding mentori bo‘lasan."
        )

    # Kompaniya va xavfsizlik haqida sistem prompt
    system_prompt = f"""
{lang_instruction}

Company context (BeTrader, Uzbekistan):
- BeTrader is a proprietary trading (prop trading) company and trading academy in Uzbekistan.
- Traders first pass an evaluation / challenge on a demo account (for example 10 000 USD, 1 month, min 10 trading days, max daily loss 300 USD, max total loss 3000 USD, profit target 1500 USD, participation fee around 350 USD).
- If the trader passes the challenge, they get access to a real funded account and may receive up to 80% of the profit, starting usually from 50/50.
- There is an office in Tashkent and real support via Telegram, Discord, phone and email.
- Education and mentoring is an important part of the offer: the goal is to build long-term relationships with traders.

Safety & risk rules:
- Never promise guaranteed profit, never say “100% safe”.
- Always mention that trading and investing on financial markets involves significant risk, including possible loss of capital.
- Emphasize diversification, risk management, discipline and long-term thinking.
- Do not give personal investment advice like “put all your money here” or “take a loan to invest”.
- Encourage the user to invest only money they can afford to risk.
- Remind that past performance does not guarantee future results.

Conversation style:
- Be calm, kind, and trust-building, not aggressive sales.
- Explain concepts like “what is investment”, “what is prop trading”, “how profit share works”, “how withdrawals work”, “what risks exist”.
- Use simple examples and analogies when needed (but short).
- If user asks specifically about BeTrader, use the company info above, but stay honest about risks.
- If the question is about religion/halal, explain that you are not a religious authority, but you can explain the economic structure transparently.

User language in this chat is: {lang}.
"""

    messages = [{"role": "system", "content": system_prompt}]
    # Oxirgi tarixdan biroz qo'shamiz
    history = user.conversation[-8:]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    # OpenAI chaqiruvini fon threadida bajarish
    def _call_openai():
        resp = client.chat.completions.create(
            model="gpt-5.4",
            messages=messages,
            temperature=0.4,
        )
        return resp.choices[0].message.content

    reply = await asyncio.to_thread(_call_openai)

    user.conversation.append({"role": "user", "content": user_text})
    user.conversation.append({"role": "assistant", "content": reply})
    if len(user.conversation) > 20:
        user.conversation = user.conversation[-20:]

    return reply or ""


# ================================
#  BOT & DISPATCHER
# ================================

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


# ================================
#  START / LANGUAGE
# ================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = get_user_state(message.from_user.id)
    user.language = LANG_UZ
    user.msg_count += 1
    update_user_from_message(user, message)

    text = (
        "Assalomu alaykum! Men BeTrader kompaniyasining AI moliyaviy maslahatchisiman. 🤝\n\n"
        "Avval tilni tanlab olaylik:"
    )
    await message.answer(text, reply_markup=get_language_keyboard())


@dp.callback_query(F.data.startswith("lang_"))
async def lang_chosen(callback: CallbackQuery):
    user = get_user_state(callback.from_user.id)
    if callback.from_user:
        user.name = callback.from_user.full_name

    if callback.data == "lang_uz":
        user.language = LANG_UZ
        text = "Til: 🇺🇿 O‘zbek tanlandi.\n\nFond bozori haqida tajribangiz bormi?"
    elif callback.data == "lang_ru":
        user.language = LANG_RU
        text = "Язык: 🇷🇺 Русский выбран.\n\nЕсть ли у вас опыт торговли или инвестиций на фондовом рынке?"
    else:
        user.language = LANG_EN
        text = "Language: 🇬🇧 English selected.\n\nDo you have any experience with trading or investing on financial markets?"

    await callback.message.answer(text, reply_markup=get_yes_no_keyboard(user.language))
    await callback.answer()


# ================================
#  ADMIN PANEL
# ================================

def build_global_stats_text(lang: str) -> str:
    total = len(user_states)
    halol = kons = yuqori = 0
    cold = warm = hot = 0

    for u in user_states.values():
        if u.risk_profile == "halol":
            halol += 1
        elif u.risk_profile == "konservativ":
            kons += 1
        elif u.risk_profile == "yuqori":
            yuqori += 1

        seg = u.lead_segment()
        if seg == "Cold":
            cold += 1
        elif seg == "Warm":
            warm += 1
        else:
            hot += 1

    if lang == LANG_EN:
        return (
            "📊 Global bot statistics:\n\n"
            f"👥 Total users: {total}\n"
            f"❄️ Cold leads: {cold}\n"
            f"🔥 Warm leads: {warm}\n"
            f"🚀 Hot leads: {hot}\n\n"
            "Risk profiles:\n"
            f"🟢 Halal / Low: {halol}\n"
            f"🟡 Conservative / Medium: {kons}\n"
            f"🔴 High return / High: {yuqori}\n"
        )
    elif lang == LANG_RU:
        return (
            "📊 Общая статистика бота:\n\n"
            f"👥 Всего пользователей: {total}\n"
            f"❄️ Cold лиды: {cold}\n"
            f"🔥 Warm лиды: {warm}\n"
            f"🚀 Hot лиды: {hot}\n\n"
            "Профили риска:\n"
            f"🟢 Халал / низкий: {halol}\n"
            f"🟡 Консервативный / средний: {kons}\n"
            f"🔴 Высокодоходный / высокий: {yuqori}\n"
        )
    else:
        return (
            "📊 Bot umumiy statistikasi:\n\n"
            f"👥 Jami foydalanuvchilar: {total}\n"
            f"❄️ Cold leadlar: {cold}\n"
            f"🔥 Warm leadlar: {warm}\n"
            f"🚀 Hot leadlar: {hot}\n\n"
            "Risk profillari bo‘yicha:\n"
            f"🟢 Halol (past risk): {halol}\n"
            f"🟡 Konservativ (o‘rta risk): {kons}\n"
            f"🔴 Yuqori daromadli (yuqori risk): {yuqori}\n"
        )


def build_risk_profile_text(level: str, lang: str) -> str:
    count = sum(1 for u in user_states.values() if u.risk_profile == level)

    if level == "halol":
        if lang == LANG_EN:
            title = "🟢 Halal / Low risk users"
        elif lang == LANG_RU:
            title = "🟢 Пользователи с халал / низким риском"
        else:
            title = "🟢 Halol (past risk) tanlaganlar"
    elif level == "konservativ":
        if lang == LANG_EN:
            title = "🟡 Conservative / Medium risk users"
        elif lang == LANG_RU:
            title = "🟡 Пользователи с консервативным / средним риском"
        else:
            title = "🟡 Konservativ (o‘rta risk) tanlaganlar"
    else:
        if lang == LANG_EN:
            title = "🔴 High return / High risk users"
        elif lang == LANG_RU:
            title = "🔴 Пользователи с высокодоходным / высоким риском"
        else:
            title = "🔴 Yuqori daromadli (yuqori risk) tanlaganlar"

    return f"{title}\n\nJami / Всего / Total: {count}"


@dp.message(F.text == "/admin")
async def cmd_admin(message: Message):
    user = get_user_state(message.from_user.id)
    update_user_from_message(user, message)

    if not is_admin(message.from_user.id):
        await message.answer("Sizda admin huquqi yo‘q.")
        return

    if user.language == LANG_EN:
        text = "🔐 Admin panel. Choose a section:"
    elif user.language == LANG_RU:
        text = "🔐 Админ-панель. Выберите раздел:"
    else:
        text = "🔐 Admin panel. Kerakli bo‘limni tanlang:"

    await message.answer(text, reply_markup=get_admin_main_keyboard(user.language))


@dp.callback_query(F.data == "admin_stats")
async def admin_stats_cb(callback: CallbackQuery):
    user = get_user_state(callback.from_user.id)
    if not is_admin(callback.from_user.id):
        await callback.answer("Admin rights required.", show_alert=True)
        return

    text = build_global_stats_text(user.language)
    await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard(user.language))
    await callback.answer()


@dp.callback_query(F.data == "admin_risk_menu")
async def admin_risk_menu_cb(callback: CallbackQuery):
    user = get_user_state(callback.from_user.id)
    if not is_admin(callback.from_user.id):
        await callback.answer("Admin rights required.", show_alert=True)
        return

    if user.language == LANG_EN:
        text = "📂 Choose risk profile:"
    elif user.language == LANG_RU:
        text = "📂 Выберите профиль риска:"
    else:
        text = "📂 Qaysi risk profilini ko‘rmoqchisiz?"

    await callback.message.edit_text(text, reply_markup=get_admin_risk_menu_keyboard(user.language))
    await callback.answer()


@dp.callback_query(F.data.in_(["admin_risk_halol", "admin_risk_konservativ", "admin_risk_yuqori"]))
async def admin_risk_profile_cb(callback: CallbackQuery):
    user = get_user_state(callback.from_user.id)
    if not is_admin(callback.from_user.id):
        await callback.answer("Admin rights required.", show_alert=True)
        return

    if callback.data == "admin_risk_halol":
        level = "halol"
    elif callback.data == "admin_risk_konservativ":
        level = "konservativ"
    else:
        level = "yuqori"

    text = build_risk_profile_text(level, user.language)
    await callback.message.edit_text(text, reply_markup=get_admin_risk_menu_keyboard(user.language))
    await callback.answer()


@dp.callback_query(F.data == "admin_main")
async def admin_back_main_cb(callback: CallbackQuery):
    user = get_user_state(callback.from_user.id)
    if not is_admin(callback.from_user.id):
        await callback.answer("Admin rights required.", show_alert=True)
        return

    if user.language == LANG_EN:
        text = "🔐 Admin panel. Choose a section:"
    elif user.language == LANG_RU:
        text = "🔐 Админ-панель. Выберите раздел:"
    else:
        text = "🔐 Admin panel. Kerakli bo‘limni tanlang:"

    await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard(user.language))
    await callback.answer()


@dp.callback_query(F.data == "admin_close")
async def admin_close_cb(callback: CallbackQuery):
    await callback.message.edit_text("Admin panel yopildi.")
    await callback.answer()


# ================================
#  RISK PROFIL CALLBACK
# ================================

@dp.callback_query(F.data.in_(["risk_halol", "risk_konservativ", "risk_yuqori", "risk_back_menu"]))
async def risk_profile_cb(callback: CallbackQuery):
    user = get_user_state(callback.from_user.id)

    if callback.data == "risk_back_menu":
        if user.language == LANG_EN:
            text = "Main menu:"
        elif user.language == LANG_RU:
            text = "Главное меню:"
        else:
            text = "Asosiy menyu:"
        await callback.message.answer(text, reply_markup=get_main_menu_keyboard(user.language))
        await callback.answer()
        return

    if callback.data == "risk_halol":
        user.risk_profile = "halol"
    elif callback.data == "risk_konservativ":
        user.risk_profile = "konservativ"
    else:
        user.risk_profile = "yuqori"

    seg = user.lead_segment()
    if user.language == LANG_EN:
        rp = {
            "halol": "Halal / low risk",
            "konservativ": "Conservative / medium risk",
            "yuqori": "High return / high risk",
        }[user.risk_profile]
        text = (
            f"I understand you. You chose **{rp}** profile. ✅\n\n"
            f"Internal lead segment: **{seg}**.\n\n"
            "Now you can use the buttons below, or write any question if something is not clear. 🙂"
        )
    elif user.language == LANG_RU:
        rp = {
            "halol": "Халал / низкий риск",
            "konservativ": "Консервативный / средний риск",
            "yuqori": "Высокодоходный / высокий риск",
        }[user.risk_profile]
        text = (
            f"Я вас понял. Вы выбрали профиль **{rp}**. ✅\n\n"
            f"Внутренний lead-сегмент: **{seg}**.\n\n"
            "Теперь вы можете пользоваться кнопками ниже или просто написать свой вопрос. 🙂"
        )
    else:
        rp = {
            "halol": "Halol (past risk)",
            "konservativ": "Konservativ (o‘rta risk)",
            "yuqori": "Yuqori daromadli (yuqori risk)",
        }[user.risk_profile]
        text = (
            f"Men sizni tushundim. Siz **{rp}** profilini tanladingiz. ✅\n\n"
            f"Lead segment: **{seg}**.\n\n"
            "Endi pastdagi tugmalar orqali davom etishingiz yoki xohlagan savolingizni yozishingiz mumkin. 🙂"
        )

    await callback.message.answer(text, reply_markup=get_main_menu_keyboard(user.language))
    await callback.answer("Risk profili saqlandi.")


# ================================
#  STAT / SIMPLE
# ================================

@dp.message(F.text == "/stats")
async def cmd_stats(message: Message):
    user = get_user_state(message.from_user.id)
    update_user_from_message(user, message)
    text = build_global_stats_text(user.language)
    await message.answer(text)


# ================================
#  STATIC SECTIONS
# ================================

async def send_investment_intro(message: Message, user: UserState):
    if user.language == LANG_EN:
        text = (
            "Investment means putting money into assets with the goal of growing capital or generating income over time. 💼\n\n"
            "On classic financial markets this can be stocks, bonds, funds, currencies and so on. "
            "In a **prop trading** model like BeTrader, the trader mainly trades company capital and shares the profit.\n\n"
            "Any investment or trading involves market risk – the value of assets can both grow and fall, "
            "and past performance does not guarantee future results.\n\n"
            "If something is unclear, you can write your question, or choose another section from the menu below. 🙂"
        )
    elif user.language == LANG_RU:
        text = (
            "Инвестиции – это размещение средств в активы с целью увеличить капитал или получать доход со временем. 💼\n\n"
            "На классических рынках это могут быть акции, облигации, фонды, валюты и т.д. "
            "В модели **prop-компании**, как у BeTrader, трейдер в основном торгует капиталом компании и делится прибылью.\n\n"
            "Любые инвестиции и трейдинг связаны с рыночным риском – стоимость активов может как расти, так и падать, "
            "а прошлые результаты не гарантируют будущих.\n\n"
            "Если что-то непонятно, можете написать вопрос или выбрать другой раздел через кнопки ниже. 🙂"
        )
    else:
        text = (
            "Investitsiya – bu pulni vaqt o‘tishi bilan ko‘paytirish yoki daromad olish maqsadida turli aktivlarga joylashtirishdir. 💼\n\n"
            "Klasik moliya bozorida bu aksiyalar, obligatsiyalar, fondlar, valyutalar va boshqalar bo‘lishi mumkin. "
            "**Prop treyding** modelida esa treyder asosan kompaniya kapitali bilan savdo qiladi va foydani ulashadi.\n\n"
            "Har qanday investitsiya va savdo bozor riski bilan bog‘liq – aktivlar narxi ham ko‘tarilishi, ham pasayishi mumkin, "
            "o‘tmishdagi natijalar kelajak natijaga kafolat bermaydi.\n\n"
            "Agar nimadir tushunarsiz bo‘lsa, savolingizni yozishingiz yoki pastdagi menyudan boshqa bo‘limni tanlashingiz mumkin. 🙂"
        )
    await message.answer(text)


async def send_risk_types(message: Message, user: UserState):
    if user.language == LANG_EN:
        text = (
            "At BeTrader you can roughly think about three risk profiles:\n\n"
            "🟢 **Halal / low risk** – expected potential around 15–18% annually in USD, "
            "smaller drawdowns, funds can be frozen for about 3 months.\n\n"
            "🟡 **Conservative / medium risk** – also around 15–18% annually but with a bit more active trading, "
            "balanced between safety and growth.\n\n"
            "🔴 **High return / high risk** – potential can be around 30–50% annually, but volatility and "
            "temporary drawdowns are significantly higher, funds may be locked for about 6 months.\n\n"
            "The higher the risk, the higher the potential return, but also the higher the chance of losses. "
            "Choose the level that matches your psychology and time horizon.\n\n"
            "Which profile feels closer to you? You can select one below, or write any question. 🙂"
        )
    elif user.language == LANG_RU:
        text = (
            "В рамках продуктов BeTrader можно условно выделить три профиля риска:\n\n"
            "🟢 **Halol / низкий риск** – ожидаемый потенциал порядка 15–18% годовых в USD, "
            "меньшие просадки, средства обычно замораживаются примерно на 3 месяца.\n\n"
            "🟡 **Консервативный / средний риск** – также около 15–18% годовых, но торговля чуть активнее, "
            "баланс между безопасностью и ростом.\n\n"
            "🔴 **Высокодоходный / высокий риск** – потенциал порядка 30–50% годовых, но волатильность и "
            "временные просадки существенно выше, средства могут быть заморожены примерно на 6 месяцев.\n\n"
            "Чем выше риск, тем выше потенциальная доходность, но и вероятность убытков. "
            "Важно выбрать уровень, который подходит вашей психологии и горизонту.\n\n"
            "Какой профиль вам ближе? Можете выбрать ниже или просто задать вопрос. 🙂"
        )
    else:
        text = (
            "BeTrader mahsulotlari doirasida taxminan uchta risk profili bor:\n\n"
            "🟢 **Halol (past risk)** – USDda taxminiy 15–18% yillik potensial, "
            "tebranishlar nisbatan kichik, mablag‘lar odatda 3 oyga muzlatiladi.\n\n"
            "🟡 **Konservativ (o‘rta risk)** – taxminan 15–18% yillik, savdo biroz aktivroq, "
            "barqarorlik va o‘sish o‘rtasidagi balans.\n\n"
            "🔴 **Yuqori daromadli (yuqori risk)** – taxminan 30–50% yillik potensial bo‘lishi mumkin, "
            "lekin volatillik va vaqtinchalik minuslar ancha yuqori, mablag‘lar ~6 oyga muzlatilishi mumkin.\n\n"
            "Risk yuqori bo‘lsa, daromad ham yuqori bo‘lishi mumkin, lekin yo‘qotish ehtimoli ham oshadi. "
            "O‘zingizning xarakteringiz va muddatingizga mos variantni tanlash muhim.\n\n"
            "Qaysi profil sizga yaqinroq? Pastdagi tugmalardan tanlashingiz yoki savolingizni yozishingiz mumkin. 🙂"
        )
    await message.answer(text, reply_markup=get_risk_profile_keyboard(user.language))


async def send_company_info(message: Message, user: UserState):
    if user.language == LANG_EN:
        text = (
            "🏢 **About BeTrader**\n\n"
            "• One of the first professional prop trading companies and academies in Uzbekistan.\n"
            "• Focus on education, fair evaluation and long-term cooperation with traders.\n"
            "• You pass a trading challenge on a demo account. If you follow the rules and reach the profit target, "
            "you can manage a real funded account and receive up to 80% of the profit.\n"
            "• There is a real office in Tashkent and support via Telegram, Discord, phone and email.\n\n"
            "All information on the website is for educational purposes and is not a recommendation to buy or sell "
            "any securities. Trading on financial markets involves high risk, and past results are not a guarantee of future performance.\n\n"
            "If you want, you can ask anything about the company, evaluation process or safety – just write your question. 🙂"
        )
    elif user.language == LANG_RU:
        text = (
            "🏢 **О компании BeTrader**\n\n"
            "• Одна из первых профессиональных prop-компаний и академий в Узбекистане.\n"
            "• Упор на обучение, честную оценку и долгосрочное сотрудничество с трейдерами.\n"
            "• Сначала вы проходите отбор (challenge) на демо-счёте. Если соблюдаете правила и выполняете цель по прибыли, "
            "получаете доступ к реальному счёту и до 80% от прибыли.\n"
            "• Реальный офис в Ташкенте, поддержка через Telegram, Discord, телефон и email.\n\n"
            "Вся информация на сайте носит образовательный характер и не является рекомендацией покупать или продавать "
            "какие-либо ценные бумаги. Торговля на финансовых рынках связана с высоким риском, а прошлые результаты не гарантируют будущие.\n\n"
            "Если хотите, можете задать любой вопрос о компании, отборе или рисках – просто напишите его. 🙂"
        )
    else:
        text = (
            "🏢 **BeTrader haqida**\n\n"
            "• O‘zbekistondagi professional prop savdo kompaniyalaridan va savdo akademiyalaridan biri.\n"
            "• Maqsad – treyderlar bilan uzoq muddatli hamkorlik, adolatli baholash va kuchli ta’lim berish.\n"
            "• Avval demo hisobda tanlovdan o‘tasiz: qoidalar, maksimal yo‘qotish cheklovlari va foyda maqsadi bor. "
            "Shartlarni bajarsangiz, haqiqiy hisobga o‘tasiz va foydaning 80% gacha qismini olishingiz mumkin.\n"
            "• Toshkentda ofis, Telegram va boshqa kanallar orqali qo‘llab-quvvatlash mavjud.\n\n"
            "Saytdagi ma’lumotlar faqat ma’rifiy maqsadda, qimmatli qog‘oz sotib olish yoki sotishga bevosita tavsiya emas. "
            "Moliyaviy bozorlar bilan ishlashda yuqori risk bor va o‘tmish natijalari kelajak uchun kafolat emas.\n\n"
            "Kompaniya, tanlov jarayoni yoki xavfsizlik haqida savolingiz bo‘lsa, bemalol yozishingiz mumkin. 🙂"
        )
    await message.answer(text)


async def send_profit_payouts(message: Message, user: UserState):
    if user.language == LANG_EN:
        text = (
            "💰 **Profit and payouts**\n\n"
            "In a prop model, you usually trade the company’s capital and share the profit:\n"
            "• Starting profit split can be around 50/50, and with good performance it may grow up to 80% in favor of the trader.\n"
            "• Payouts are normally processed after a trading period (for example, after a month) within several business days.\n"
            "• There can be commissions for the trading platform and per-lot commission – this is discussed individually.\n\n"
            "Remember: there can be both profitable and losing months. There is no guarantee of stable income – it depends on your trading quality and risk management.\n\n"
            "If you want, you can ask how the split or payouts would work in your specific case. 🙂"
        )
    elif user.language == LANG_RU:
        text = (
            "💰 **Прибыль и выплаты**\n\n"
            "В prop-модели вы торгуете капиталом компании и делите прибыль:\n"
            "• Стартовое распределение может быть около 50/50, при стабильных результатах доля трейдера может "
            "увеличиваться до 80%.\n"
            "• Выплаты обычно происходят после торгового периода (например, раз в месяц) в течение нескольких рабочих дней.\n"
            "• Есть комиссия за торговую платформу и комиссия за лот – детали обсуждаются отдельно.\n\n"
            "Важно помнить: могут быть прибыльные и убыточные месяцы. "
            "Стабильный доход не гарантируется – всё зависит от качества вашей торговли и риск-менеджмента.\n\n"
            "Если хотите, можете спросить более конкретно про выплаты под вашу ситуацию. 🙂"
        )
    else:
        text = (
            "💰 **Foyda va to‘lovlar**\n\n"
            "Prop modelida siz asosan kompaniya kapitali bilan savdo qilasiz va foydani ulashasiz:\n"
            "• Boshlang‘ich nisbat ko‘pincha 50/50 atrofida bo‘ladi, natijalar yaxshilangani sayin treyder ulushi 80% gacha oshishi mumkin.\n"
            "• To‘lovlar odatda savdo oyi tugagach, bir necha ish kuni ichida amalga oshiriladi.\n"
            "• Platforma va har bir lot uchun komissiyalar mavjud bo‘lishi mumkin – bu alohida kelishiladi.\n\n"
            "Yodingizda bo‘lsin: ba’zi oylar foydali, ba’zi oylar zararli bo‘lishi mumkin. "
            "Barqaror daromad kafolatlanmaydi – hammasi savdo sifati va risk boshqaruvingizga bog‘liq.\n\n"
            "Istasangiz, aynan siz uchun foyda ulashish va to‘lovlar qanday ishlashi haqida savol berishingiz mumkin. 🙂"
        )
    await message.answer(text)


async def send_withdrawals(message: Message, user: UserState):
    if user.language == LANG_EN:
        text = (
            "💸 **Withdrawals**\n\n"
            "As a funded trader, you can request payouts from your profit after the trading period, "
            "according to the company’s rules.\n\n"
            "• Usually there are no restrictions on how you use withdrawn money.\n"
            "• There can be rules about keeping a minimum balance on the trading account so that the risk stays under control.\n\n"
            "The exact technical details (payment systems, timing, commissions) are clarified with the manager. "
            "If you have a specific question about withdrawals, just write it. 🙂"
        )
    elif user.language == LANG_RU:
        text = (
            "💸 **Вывод средств**\n\n"
            "Как funded-трейдер вы можете запрашивать вывод прибыли по правилам компании после торгового периода.\n\n"
            "• Обычно нет ограничений на то, как вы используете выведенные средства.\n"
            "• Могут быть требования по минимальному балансу на счёте, чтобы сохранять контроль над риском.\n\n"
            "Точные детали (платёжные системы, сроки, комиссии) уточняются с менеджером. "
            "Если у вас есть конкретный вопрос по выводу средств, просто напишите его. 🙂"
        )
    else:
        text = (
            "💸 **Pul yechish**\n\n"
            "Funded treyder sifatida savdo davri yakunlangach, kompaniya qoidalariga muvofiq foydangizdan "
            "pul yechib olishingiz mumkin.\n\n"
            "• Odatda yechilgan puldan foydalanish bo‘yicha cheklov bo‘lmaydi.\n"
            "• Lekin savdo hisobida minimal balansni saqlash kabi qoidalar bo‘lishi mumkin – bu riskni nazorat qilish uchun.\n\n"
            "Texnik detallar (qaysi to‘lov tizimlari, qancha kunda tushishi, komissiyalar) menejer bilan aniq kelishiladi. "
            "Agar pul yechishga doir aniq savolingiz bo‘lsa, bemalol yozing. 🙂"
        )
    await message.answer(text)


async def send_prop_conditions(message: Message, user: UserState):
    if user.language == LANG_EN:
        text = (
            "📊 **Prop trading evaluation example**\n\n"
            "Typical challenge example at BeTrader:\n"
            "• Account size: 10 000 USD (demo)\n"
            "• Duration: 1 month, min 10 trading days\n"
            "• Max daily loss: 300 USD\n"
            "• Max total loss: 3000 USD\n"
            "• Profit target: 1500 USD\n"
            "• Participation fee: about 350 USD\n\n"
            "Exact parameters can vary by product and time, so always check the current conditions with the manager.\n\n"
            "If you’d like, you can ask whether these numbers fit your trading style. 🙂"
        )
    elif user.language == LANG_RU:
        text = (
            "📊 **Пример условий prop-отбора**\n\n"
            "Типичный challenge в BeTrader может выглядеть так:\n"
            "• Размер счёта: 10 000 USD (демо)\n"
            "• Срок: 1 месяц, минимум 10 торговых дней\n"
            "• Макс. дневная просадка: 300 USD\n"
            "• Макс. общая просадка: 3000 USD\n"
            "• Цель по прибыли: 1500 USD\n"
            "• Стоимость участия: около 350 USD\n\n"
            "Точные параметры зависят от тарифа и времени, поэтому всегда уточняйте актуальные условия у менеджера.\n\n"
            "Если хотите, можете спросить, насколько такие условия подходят под ваш стиль торговли. 🙂"
        )
    else:
        text = (
            "📊 **Prop savdo tanloviga misol**\n\n"
            "BeTrader’dagi odatiy challenge shartlari taxminan quyidagicha bo‘lishi mumkin:\n"
            "• Hisob hajmi: 10 000 USD (demo)\n"
            "• Muddati: 1 oy, kamida 10 savdo kuni\n"
            "• Maksimal kunlik yo‘qotish: 300 USD\n"
            "• Maksimal umumiy yo‘qotish: 3000 USD\n"
            "• Foyda maqsadi: 1500 USD\n"
            "• Ishtirok narxi: ~350 USD\n\n"
            "Aniq parametrlar tarif va vaqtga qarab o‘zgarishi mumkin, shuning uchun yangilangan shartlarni har doim menejer bilan tekshirish kerak.\n\n"
            "Agar xohlasangiz, bu shartlar sizning savdo uslubingizga qanchalik mosligi haqida so‘rashingiz mumkin. 🙂"
        )
    await message.answer(text)


async def send_contacts(message: Message, user: UserState):
    if user.language == LANG_EN:
        text = (
            "📞 **Contacts**\n\n"
            "• Phone: +998 90 893 55 55\n"
            "• Telegram: @betrader_uz\n"
            "• Email: info@betrader.uz\n"
            "• Address: Tashkent, Uzbekistan (Navoiy street, etc.)\n\n"
            "You can write here to clarify general questions first, then contact the team for personal details. 🙂"
        )
    elif user.language == LANG_RU:
        text = (
            "📞 **Контакты**\n\n"
            "• Телефон: +998 90 893 55 55\n"
            "• Telegram: @betrader_uz\n"
            "• Email: info@betrader.uz\n"
            "• Адрес: Ташкент, Узбекистан (ул. Навои и др.)\n\n"
            "Можете сначала задать общие вопросы здесь, а затем связаться с командой за персональными деталями. 🙂"
        )
    else:
        text = (
            "📞 **Kontaktlar**\n\n"
            "• Telefon: +998 90 893 55 55\n"
            "• Telegram: @betrader_uz\n"
            "• Email: info@betrader.uz\n"
            "• Manzil: Toshkent shahri, Navoiy ko‘chasi va hokazo.\n\n"
            "Avval umumiy savollarni shu yerda so‘rab olishingiz, keyin esa jamoa bilan bevosita bog‘lanishingiz mumkin. 🙂"
        )
    await message.answer(text)


async def send_question_hint(message: Message, user: UserState):
    if user.language == LANG_EN:
        text = (
            "You can ask any question about financial markets, prop trading or BeTrader. ✍️\n\n"
            "For example:\n"
            "• Is prop trading suitable for a beginner?\n"
            "• What are the main risks?\n"
            "• How is this different from a bank deposit?\n\n"
            "Just type your question – AI advisor will answer like a human consultant."
        )
    elif user.language == LANG_RU:
        text = (
            "Вы можете задать любой вопрос о финансовых рынках, prop-трейдинге или BeTrader. ✍️\n\n"
            "Например:\n"
            "• Подойдёт ли prop-компания новичку?\n"
            "• Каковы основные риски?\n"
            "• Чем это отличается от банковского депозита?\n\n"
            "Просто напишите вопрос – AI-консультант ответит в живом, понятном стиле."
        )
    else:
        text = (
            "Fond bozorlari, prop savdo yoki BeTrader haqida xohlagan savolingizni yozishingiz mumkin. ✍️\n\n"
            "Masalan:\n"
            "• Prop kompaniya yangi boshlovchi uchun mosmi?\n"
            "• Asosiy risklar nimalar?\n"
            "• Bank depozitidan nimasi bilan farq qiladi?\n\n"
            "Savolingizni yozing – AI maslahatchi uni inson kabi tushunarli uslubda javob beradi."
        )
    await message.answer(text)


# ================================
#  TEXT HANDLER
# ================================

@dp.message(F.text)
async def handle_text(message: Message):
    user = get_user_state(message.from_user.id)
    user.msg_count += 1
    update_user_from_message(user, message)
    text = (message.text or "").strip()

    # /start, /admin va boshqalarni bu handlerda qayta ishlamaymiz
    if text.startswith("/"):
        return

    # Birinchi bosqich: tajriba savoli
    if user.experienced is None:
        ans = parse_yes_no(text, user.language)
        if ans is not None:
            user.experienced = ans
            if user.language == LANG_EN:
                msg = (
                    "Got it, thank you. 🌟\n\n"
                    "Now you can use the menu below – or ask any question at any time."
                )
            elif user.language == LANG_RU:
                msg = (
                    "Я вас понял, спасибо. 🌟\n\n"
                    "Теперь можете пользоваться меню ниже или в любое время задать вопрос."
                )
            else:
                msg = (
                    "Men sizni tushundim, rahmat. 🌟\n\n"
                    "Endi pastdagi menyudan foydalanishingiz yoki xohlagan payt savol berishingiz mumkin."
                )
            await message.answer(msg, reply_markup=get_main_menu_keyboard(user.language))
            return

        # agar tushunilmasa ham menyuga o'tamiz
        user.experienced = False
        await message.answer(
            "Rahmat, asosiy menyuga o‘tamiz.",
            reply_markup=get_main_menu_keyboard(user.language),
        )
        return

    # Agar kalkulyator uchun summa kutilayotgan bo'lsa (agar keyin qo‘shsangiz)
    if user.awaiting_amount:
        amount = extract_amount(text)
        if amount is None:
            if user.language == LANG_EN:
                await message.answer("Please enter the amount only in numbers. For example: 1000 or 10 000.")
            elif user.language == LANG_RU:
                await message.answer("Пожалуйста, введите сумму только цифрами. Например: 1000 или 10 000.")
            else:
                await message.answer("Iltimos, summani faqat sonlarda kiriting. Masalan: 1000 yoki 10 000.")
            return
        user.last_amount = amount
        user.awaiting_amount = False
        # hozircha bu summadan AI foydalanishi mumkin, alohida kalkulyator yozmasak ham bo‘ladi

    # Menyu tugmalari
    if user.language == LANG_EN:
        if text == "📈 What is investment?":
            await send_investment_intro(message, user)
            return
        if text == "⚡ Risk types":
            await send_risk_types(message, user)
            return
        if text == "🏢 About company":
            await send_company_info(message, user)
            return
        if text == "💰 Profit & payouts":
            await send_profit_payouts(message, user)
            return
        if text == "💸 Withdrawals":
            await send_withdrawals(message, user)
            return
        if text == "📊 Prop trading conditions":
            await send_prop_conditions(message, user)
            return
        if text == "📞 Contact":
            await send_contacts(message, user)
            return
        if text == "❓ Ask a question":
            await send_question_hint(message, user)
            return
        if text == "⬅️ Back to main":
            await message.answer("Main menu:", reply_markup=get_main_menu_keyboard(user.language))
            return
    elif user.language == LANG_RU:
        if text == "📈 Что такое инвестиции?":
            await send_investment_intro(message, user)
            return
        if text == "⚡ Типы риска":
            await send_risk_types(message, user)
            return
        if text == "🏢 О компании":
            await send_company_info(message, user)
            return
        if text == "💰 Прибыль и выплаты":
            await send_profit_payouts(message, user)
            return
        if text == "💸 Вывод средств":
            await send_withdrawals(message, user)
            return
        if text == "📊 Условия prop-трейдинга":
            await send_prop_conditions(message, user)
            return
        if text == "📞 Контакты":
            await send_contacts(message, user)
            return
        if text == "❓ Задать вопрос":
            await send_question_hint(message, user)
            return
        if text == "⬅️ В главное меню":
            await message.answer("Главное меню:", reply_markup=get_main_menu_keyboard(user.language))
            return
    else:
        if text == "📈 Investitsiya nima?":
            await send_investment_intro(message, user)
            return
        if text == "⚡ Risk turlari":
            await send_risk_types(message, user)
            return
        if text == "🏢 Kompaniya haqida":
            await send_company_info(message, user)
            return
        if text == "💰 Foyda va to‘lovlar":
            await send_profit_payouts(message, user)
            return
        if text == "💸 Pul yechish":
            await send_withdrawals(message, user)
            return
        if text == "📊 Prop savdo shartlari":
            await send_prop_conditions(message, user)
            return
        if text == "📞 Bog‘lanish":
            await send_contacts(message, user)
            return
        if text == "❓ Savol berish":
            await send_question_hint(message, user)
            return
        if text == "⬅️ Asosiy menyu":
            await message.answer("Asosiy menyu:", reply_markup=get_main_menu_keyboard(user.language))
            return

    # Agar tugmalarga to'g'ri kelmasa – bu erkin savol, OpenAI javob beradi
    reply = await ask_openai(user, text)
    await message.answer(reply, reply_markup=get_main_menu_keyboard(user.language))


# ================================
#  MAIN
# ================================

async def main():
    print("BeTrader AI Telegram bot ishga tushmoqda...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
