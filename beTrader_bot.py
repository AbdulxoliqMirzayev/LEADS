"""
╔══════════════════════════════════════════════════════╗
║        TELEGRAM AI SALES BOT  v4.0                  ║
║────────────────────────────────────────────────────── ║
║  Stack : aiogram 3.7+ · google-genai · SQLite        ║
║  Start : python main.py                              ║
║  Env   : TELEGRAM_TOKEN · GEMINI_API_KEY             ║
║          ADMIN_TELEGRAM_ID                           ║
╚══════════════════════════════════════════════════════╝

SUHBAT OQIMI:
  /start
    └─ Til tanlash  [UZ / RU / EN]
         └─ Salom + tajriba?  [Ha / Yo'q]
              ├─ HA  ──► depozit (raqam) ──► risk [3 btn] ──► kontakt ──► AI tavsiya ──► [Boshlash / Savol]
              └─ YO'Q ──► mavzu [6 btn] ──► AI tushuntiradi ──► depozit ──► risk ──► kontakt ──► AI tavsiya ──► [Boshlash / Savol]
  Oxirida:
    - Foydalanuvchiga: xayrlashuv + manager bog'lanadi
    - Adminga: lead ma'lumotlari avtomatik yuboriladi
    - Savol bo'lsa: AI bemalol javob beradi
"""

# ══════════════════════════════════════════════════════
# IMPORTS
# ══════════════════════════════════════════════════════
import asyncio
import logging
import os
import sqlite3
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from google import genai
from google.genai import types as gt

# ══════════════════════════════════════════════════════
# CONFIG  (env variables)
# ══════════════════════════════════════════════════════
TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN", "").strip()
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "").strip()
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))
DB_PATH           = os.getenv("DB_PATH", "bot.db").strip()

# ══════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
)
log = logging.getLogger("BOT")

# ══════════════════════════════════════════════════════
# FSM STATES
# ══════════════════════════════════════════════════════
class S(StatesGroup):
    lang    = State()   # 1 — til tanlash
    exp     = State()   # 2 — tajriba bormi?
    topic   = State()   # 3 — (tajribasiz) mavzu tanlash
    deposit = State()   # 4 — qancha mablag'?
    risk    = State()   # 5 — risk darajasi
    contact = State()   # 6 — telefon / username
    chat    = State()   # 7 — erkin savol-javob

# ══════════════════════════════════════════════════════
# TARJIMALAR
# ══════════════════════════════════════════════════════
TX = {
# ─────────────────────────── O'ZBEK ───────────────────
"uz": {
    "greeting": (
        "Assalomu alaykum! 👋 Men Amir — sizning shaxsiy moliyaviy maslahatchiyngizman.\n\n"
        "Investitsiya dunyosi juda keng. Keling, sizga mos yo'lni birga topamiz! 🚀"
    ),
    "q_exp"       : "📊 Avval aytib bering — investitsiya yoki moliya sohasida tajribangiz bormi?",
    "btn_exp_yes" : "✅  Ha, tajribam bor",
    "btn_exp_no"  : "🔰  Yo'q, yangi boshlayman",

    "topic_intro" : (
        "Hammasi joyida! Hamma ham bir joydan boshlaydi 😊\n\n"
        "Qaysi yo'nalish sizni eng ko'p qiziqtiradi? Tanlang — sodda tushuntiraman 👇"
    ),
    "topic_btns"  : [
        ("📈  Fond bozori va aksiyalar",        "t_stocks"),
        ("₿   Kripto valyutalar",               "t_crypto"),
        ("🏆  Trading Challenge (Prop Firm)",    "t_challenge"),
        ("🏦  Bank depoziti va obligatsiyalar",  "t_bank"),
        ("🏠  Ko'chmas mulk investitsiyasi",     "t_realestate"),
        ("💸  Passiv daromad olish usullari",    "t_passive"),
    ],

    "q_deposit"      : "💰 Yaxshi! Taxminan qancha mablag' bilan boshlamoqchisiz?\n(Faqat raqam yozing, masalan: 500)",
    "invalid_deposit": "⚠️  Iltimos, faqat raqam kiriting. Masalan: 500",

    "q_risk"    : "⚡ Qanday risk darajasini afzal ko'rasiz?",
    "risk_btns" : [
        ("🟢  Konservativ  — xavfsiz, barqaror o'sish",    "r_low"),
        ("🟡  Muvozanatli — o'rtacha risk va daromad",     "r_mid"),
        ("🔴  Agressiv    — yuqori risk, katta potensial",  "r_high"),
    ],

    "q_contact"    : (
        "Deyarli tugatdik! 👍\n\n"
        "Mutaxassisimiz siz bilan bog'lanishi uchun telefon raqamingiz yoki "
        "Telegram username'ingizni yozing 📞\n(Ma'lumot maxfiy saqlanadi 🔒)"
    ),
    "btn_username" : "📱  Username'imni ulashaman",

    "summary_title": "✅  Barcha ma'lumotlar qabul qilindi!\n\n📋  Sizning profilingiz:\n",
    "lbl_name"    : "👤  Ism",
    "lbl_exp"     : "📊  Tajriba",
    "lbl_topic"   : "🎯  Qiziqish",
    "lbl_deposit" : "💰  Depozit",
    "lbl_risk"    : "⚡  Risk",
    "lbl_contact" : "📞  Kontakt",
    "exp_yes"     : "Bor ✅",
    "exp_no"      : "Yo'q 🔰",
    "analyzing"   : "\n⏳ Siz uchun tavsiya tayyorlanmoqda...",

    "btn_invest"  : "🚀  Investitsiyani boshlash",
    "btn_question": "❓  Savolim bor",

    "farewell": (
        "🎉 Ajoyib qaror!\n\n"
        "Menejerimiz siz bilan <b>yaqin orada</b> bog'lanadi va barcha tafsilotlarni tushuntiradi.\n\n"
        "Shu orada biror savolingiz bo'lsa — men shu yerdaman! 😊\n"
        "Investitsiyalar, fond bozori, kripto, challenge — istalgan mavzuda so'rang."
    ),
    "free_prompt" : "✍️  Savolingizni yozing:",

    "risk_lbl": {
        "r_low" : "Konservativ 🟢",
        "r_mid" : "Muvozanatli 🟡",
        "r_high": "Agressiv 🔴",
    },
},

# ─────────────────────────── RUSSIAN ───────────────────
"ru": {
    "greeting": (
        "Здравствуйте! 👋 Я Амир — ваш персональный финансовый консультант.\n\n"
        "Мир инвестиций огромен. Давайте вместе найдём подходящий путь! 🚀"
    ),
    "q_exp"       : "📊 Скажите — есть ли у вас опыт в инвестициях или финансах?",
    "btn_exp_yes" : "✅  Да, есть опыт",
    "btn_exp_no"  : "🔰  Нет, начинаю с нуля",

    "topic_intro" : (
        "Отлично! Все с чего-то начинали 😊\n\n"
        "Что вас интересует больше всего? Выберите — объясню просто 👇"
    ),
    "topic_btns"  : [
        ("📈  Фондовый рынок и акции",           "t_stocks"),
        ("₿   Криптовалюты",                     "t_crypto"),
        ("🏆  Trading Challenge (Prop Firm)",     "t_challenge"),
        ("🏦  Банковский депозит / облигации",    "t_bank"),
        ("🏠  Инвестиции в недвижимость",         "t_realestate"),
        ("💸  Способы пассивного дохода",         "t_passive"),
    ],

    "q_deposit"      : "💰 Отлично! Какую сумму планируете инвестировать?\n(Только цифры, например: 500)",
    "invalid_deposit": "⚠️  Введите только число. Например: 500",

    "q_risk"    : "⚡ Какой уровень риска вам подходит?",
    "risk_btns" : [
        ("🟢  Консервативный — безопасно, стабильный рост",  "r_low"),
        ("🟡  Умеренный      — средний риск и доходность",   "r_mid"),
        ("🔴  Агрессивный    — высокий риск, большой доход", "r_high"),
    ],

    "q_contact"    : (
        "Почти готово! 👍\n\n"
        "Чтобы наш специалист связался с вами — напишите номер телефона "
        "или Telegram username 📞\n(Данные хранятся конфиденциально 🔒)"
    ),
    "btn_username" : "📱  Поделиться username",

    "summary_title": "✅  Все данные получены!\n\n📋  Ваш профиль:\n",
    "lbl_name"    : "👤  Имя",
    "lbl_exp"     : "📊  Опыт",
    "lbl_topic"   : "🎯  Интерес",
    "lbl_deposit" : "💰  Депозит",
    "lbl_risk"    : "⚡  Риск",
    "lbl_contact" : "📞  Контакт",
    "exp_yes"     : "Есть ✅",
    "exp_no"      : "Нет 🔰",
    "analyzing"   : "\n⏳ Готовлю персональную рекомендацию...",

    "btn_invest"  : "🚀  Начать инвестировать",
    "btn_question": "❓  Есть вопрос",

    "farewell": (
        "🎉 Отличное решение!\n\n"
        "Наш менеджер свяжется с вами <b>в ближайшее время</b> и объяснит все детали.\n\n"
        "Если возникнут вопросы — я здесь! 😊\n"
        "Инвестиции, рынки, крипто, челленджи — спрашивайте всё."
    ),
    "free_prompt" : "✍️  Напишите ваш вопрос:",

    "risk_lbl": {
        "r_low" : "Консервативный 🟢",
        "r_mid" : "Умеренный 🟡",
        "r_high": "Агрессивный 🔴",
    },
},

# ─────────────────────────── ENGLISH ───────────────────
"en": {
    "greeting": (
        "Hello! 👋 I'm Amir — your personal financial advisor.\n\n"
        "The world of investing is vast. Let's find the right path together! 🚀"
    ),
    "q_exp"       : "📊 Tell me — do you have any experience in investments or finance?",
    "btn_exp_yes" : "✅  Yes, I have experience",
    "btn_exp_no"  : "🔰  No, I'm just starting",

    "topic_intro" : (
        "No worries! Everyone starts somewhere 😊\n\n"
        "What interests you the most? Pick one — I'll explain it simply 👇"
    ),
    "topic_btns"  : [
        ("📈  Stock Market & Equities",           "t_stocks"),
        ("₿   Cryptocurrencies",                  "t_crypto"),
        ("🏆  Trading Challenge (Prop Firm)",      "t_challenge"),
        ("🏦  Bank Deposits / Bonds",              "t_bank"),
        ("🏠  Real Estate Investing",              "t_realestate"),
        ("💸  Passive Income Methods",             "t_passive"),
    ],

    "q_deposit"      : "💰 Great! How much are you planning to invest?\n(Numbers only, e.g.: 500)",
    "invalid_deposit": "⚠️  Please enter numbers only. Example: 500",

    "q_risk"    : "⚡ What's your preferred risk level?",
    "risk_btns" : [
        ("🟢  Conservative — safe, steady growth",        "r_low"),
        ("🟡  Balanced     — medium risk & reward",       "r_mid"),
        ("🔴  Aggressive   — high risk, high potential",  "r_high"),
    ],

    "q_contact"    : (
        "Almost done! 👍\n\n"
        "So our specialist can reach you — share your phone number "
        "or Telegram username 📞\n(Your info stays private 🔒)"
    ),
    "btn_username" : "📱  Share my username",

    "summary_title": "✅  All info received!\n\n📋  Your profile:\n",
    "lbl_name"    : "👤  Name",
    "lbl_exp"     : "📊  Experience",
    "lbl_topic"   : "🎯  Interest",
    "lbl_deposit" : "💰  Deposit",
    "lbl_risk"    : "⚡  Risk",
    "lbl_contact" : "📞  Contact",
    "exp_yes"     : "Yes ✅",
    "exp_no"      : "No 🔰",
    "analyzing"   : "\n⏳ Preparing your personalized recommendation...",

    "btn_invest"  : "🚀  Start Investing",
    "btn_question": "❓  I have a question",

    "farewell": (
        "🎉 Excellent decision!\n\n"
        "Our manager will contact you <b>very soon</b> and walk you through everything.\n\n"
        "Questions in the meantime? I'm right here! 😊\n"
        "Investments, markets, crypto, challenges — ask anything."
    ),
    "free_prompt" : "✍️  Type your question:",

    "risk_lbl": {
        "r_low" : "Conservative 🟢",
        "r_mid" : "Balanced 🟡",
        "r_high": "Aggressive 🔴",
    },
},
}

# ══════════════════════════════════════════════════════
# MAVZU NOMLARI  (profil ko'rsatish uchun)
# ══════════════════════════════════════════════════════
TOPIC_NAME = {
    "t_stocks"    : {"uz":"Fond bozori 📈",    "ru":"Фондовый рынок 📈", "en":"Stock Market 📈"},
    "t_crypto"    : {"uz":"Kripto ₿",          "ru":"Крипто ₿",          "en":"Crypto ₿"},
    "t_challenge" : {"uz":"Trading Challenge 🏆","ru":"Челлендж 🏆",     "en":"Trading Challenge 🏆"},
    "t_bank"      : {"uz":"Bank depoziti 🏦",   "ru":"Банк/Облигации 🏦","en":"Bank/Bonds 🏦"},
    "t_realestate": {"uz":"Ko'chmas mulk 🏠",   "ru":"Недвижимость 🏠",  "en":"Real Estate 🏠"},
    "t_passive"   : {"uz":"Passiv daromad 💸",  "ru":"Пассивный доход 💸","en":"Passive Income 💸"},
    "—"           : {"uz":"—", "ru":"—", "en":"—"},
}

# ══════════════════════════════════════════════════════
# GEMINI SYSTEM PROMPT
# ══════════════════════════════════════════════════════
SYSTEM = """Siz Amir — investment kompaniyasining professional va do'stona moliyaviy maslahatchilar.

USLUB: Issiq, inson kabi, suhbat ko'rinishida. Aqlli do'stingiz kabi gapiring.
FORMAT: Qisqa paragraflar, max 5-6 gap. Emojilardan tabiiy foydalaning.
TIL: Foydalanuvchi qaysi tilda yozsa, AYNAN o'sha tilda javob bering (O'zbek / Rus / Ingliz).

BILIM SOHALARI — barchasini aniq tushuntirishingiz mumkin:
• Aksiyalar, ETF, indeks fondlar, IPO, dividendlar
• Kripto: Bitcoin, Ethereum, DeFi, staking, altcoinlar
• Prop trading / Funded accounts / Trading Challenges (FTMO, MyForexFunds, The5ers)
• Forex, texnik va fundamental tahlil
• Obligatsiyalar, bank depozitlari, fixed income
• Ko'chmas mulk, REITs
• Passiv daromad: dividendlar, P2P, ijara, raqamli mahsulotlar
• Risk boshqaruvi, portfel diversifikatsiyasi, murakkab foiz, DCA

QOIDALAR:
- HECH QACHON "kafolat" yoki aniq foiz va'da bermang
- Riskni qisqacha aytib o'ting, lekin qo'rqitmang
- Murakkab atamalar uchun oddiy taqqoslash ishlating
- Mavzudan chetlashsa — muloyimlik bilan investitsiyaga qaytaring
- Halol, realistik, rag'batlantiruvchi bo'ling"""

# ══════════════════════════════════════════════════════
# MAVZU BO'YICHA AI TUSHUNTIRISH PROMPTLARI
# ══════════════════════════════════════════════════════
TOPIC_PROMPTS = {
"t_stocks": {
    "uz": "Aksiyalar va fond bozorini yangi boshlovchi uchun juda sodda tushuntir. Real misol keltir (Apple yoki Tesla). Foyda, risklar, qancha pul bilan boshlash mumkin. Oxirida bitta amaliy maslahat ber.",
    "ru": "Объясни акции и фондовый рынок для новичка очень просто. Реальный пример (Apple или Tesla). Доход, риски, с какой суммы начать. Один практический совет в конце.",
    "en": "Explain stocks and the stock market for a beginner very simply. Real example (Apple or Tesla). Profit, risks, how much to start with. One practical tip at the end.",
},
"t_crypto": {
    "uz": "Kripto valyutalarni yangi boshlovchi uchun sodda tushuntir. Bitcoin nima (oltin kabi analogiya ishlat). Volatillik, foyda va risklar. Eng xavfsiz boshlash yo'li. Bitta maslahat.",
    "ru": "Объясни крипто для новичка просто. Что такое Bitcoin (аналогия с золотом). Волатильность, доход и риски. Самый безопасный старт. Один совет.",
    "en": "Explain crypto for a beginner simply. What is Bitcoin (use gold analogy). Volatility, profits and risks. Safest way to start. One tip.",
},
"t_challenge": {
    "uz": "Trading Challenge (prop firm) nima ekanini sodda tushuntir: o'z pulingni xavf ostiga qo'ymay katta kapital bilan savdo qilish imkoniyati. FTMO kabi firmalar qanday ishlaydi, foyda taqsimoti (masalan 80/20), asosiy talablar. Realistik va halol javob ber.",
    "ru": "Объясни Trading Challenge (prop firm) просто: торговля большим капиталом без риска своих денег. Как работают FTMO и другие, распределение прибыли (80/20), основные требования. Честный реалистичный ответ.",
    "en": "Explain Trading Challenge (prop firm) simply: trading large capital without risking your own money. How FTMO works, profit split (80/20), main requirements. Give an honest, realistic answer.",
},
"t_bank": {
    "uz": "Bank depoziti va obligatsiyalarni sodda tushuntir — eng xavfsiz investitsiya turlari. Foiz daromadi qanday hisoblanydi, inflatsiya ta'siri, kim uchun mos. Bitta maslahat.",
    "ru": "Объясни банковские депозиты и облигации просто — самые безопасные инвестиции. Как рассчитывается доход, влияние инфляции, кому подходит. Один совет.",
    "en": "Explain bank deposits and bonds simply — the safest investments. How income is calculated, inflation impact, who it's for. One tip.",
},
"t_realestate": {
    "uz": "Ko'chmas mulkka investitsiyani yangi boshlovchi uchun tushuntir. Ijara daromadi, qiymat o'sishi, qancha pul kerak, REITs alternativasi. Kim uchun mos?",
    "ru": "Объясни инвестиции в недвижимость для новичка. Арендный доход, рост стоимости, сколько нужно, REITs как альтернатива. Кому подходит?",
    "en": "Explain real estate investing for a beginner. Rental income, appreciation, how much needed, REITs as alternative. Who is it for?",
},
"t_passive": {
    "uz": "Passiv daromad nima ekanini va 5 ta real usulni sodda tushuntir: dividendlar, ijara daromadi, P2P kreditlash, ETF, raqamli mahsulotlar. Oddiy odam uchun eng qulay usulini ayt. Uxlab yotganda ham pul ishlash mumkinmi?",
    "ru": "Объясни пассивный доход и 5 реальных способов просто: дивиденды, аренда, P2P, ETF, цифровые продукты. Какой самый доступный для обычного человека? Можно ли зарабатывать пока спишь?",
    "en": "Explain passive income and 5 real methods simply: dividends, rental, P2P, ETFs, digital products. Which is most accessible for an average person? Can you earn while sleeping?",
},
}

# ══════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════
def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id  INTEGER UNIQUE NOT NULL,
            username     TEXT,
            first_name   TEXT,
            language     TEXT DEFAULT 'uz',
            has_exp      INTEGER DEFAULT 0,
            topic        TEXT DEFAULT '—',
            deposit_text TEXT DEFAULT '—',
            deposit_usd  REAL  DEFAULT 0,
            risk         TEXT DEFAULT '—',
            contact      TEXT DEFAULT '—',
            lead_score   INTEGER DEFAULT 0,
            lead_status  TEXT DEFAULT 'Cold',
            flow_done    INTEGER DEFAULT 0,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            role        TEXT NOT NULL,
            text        TEXT NOT NULL,
            ts          DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
    log.info("Database ready ✅")


def upsert_user(tid: int, uname: Optional[str], fname: Optional[str], lang: str):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            INSERT INTO users (telegram_id, username, first_name, language)
            VALUES (?,?,?,?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                language=excluded.language
        """, (tid, uname, fname, lang))


def set_user(tid: int, **kw):
    if not kw:
        return
    with sqlite3.connect(DB_PATH) as c:
        cols = ", ".join(f"{k}=?" for k in kw)
        c.execute(f"UPDATE users SET {cols} WHERE telegram_id=?", [*kw.values(), tid])


def log_msg(tid: int, role: str, text: str):
    with sqlite3.connect(DB_PATH) as c:
        c.execute(
            "INSERT INTO messages (telegram_id, role, text) VALUES (?,?,?)",
            (tid, role, text),
        )

# ══════════════════════════════════════════════════════
# LEAD SCORING
# ══════════════════════════════════════════════════════
def calc_score(has_exp: bool, dep: float, topic: str, risk: str) -> tuple[int, str]:
    s = 0
    if has_exp:                s += 20
    if dep >= 1000:            s += 30
    elif dep >= 500:           s += 20
    elif dep >= 200:           s += 10
    elif dep >= 50:            s +=  5
    if topic == "t_challenge": s += 25
    elif topic in ("t_stocks", "t_crypto", "t_passive"):   s += 15
    elif topic in ("t_bank", "t_realestate"):               s += 10
    if risk == "r_high":       s += 15
    elif risk == "r_mid":      s += 10
    status = "Hot" if s >= 65 else "Warm" if s >= 30 else "Cold"
    return s, status

# ══════════════════════════════════════════════════════
# GEMINI AI  (google-genai yangi SDK)
# ══════════════════════════════════════════════════════
_gclient: Optional[genai.Client] = None

def _get_client() -> genai.Client:
    global _gclient
    if _gclient is None:
        _gclient = genai.Client(api_key=GEMINI_API_KEY)
    return _gclient


async def ai(prompt: str, lang: str = "uz") -> str:
    """Gemini ga so'rov yuborish — thread pool orqali, blokirovkasiz."""
    try:
        cli  = _get_client()
        full = f"[Til: {lang}]\n\n{prompt}"

        def _call():
            return cli.models.generate_content(
                model="gemini-2.0-flash",
                contents=full,
                config=gt.GenerateContentConfig(
                    system_instruction=SYSTEM,
                    max_output_tokens=500,
                    temperature=0.75,
                ),
            )

        loop = asyncio.get_event_loop()
        resp = await asyncio.wait_for(
            loop.run_in_executor(None, _call),
            timeout=25,
        )
        return resp.text.strip()

    except asyncio.TimeoutError:
        log.warning("Gemini timeout")
    except Exception as e:
        log.error(f"Gemini xato: {e}")

    msgs = {
        "uz": "Kechirasiz, hozir texnik muammo. Biroz kutib qayta yozing. 🙏",
        "ru": "Извините, технический сбой. Попробуйте чуть позже. 🙏",
        "en": "Sorry, technical issue. Please try again shortly. 🙏",
    }
    return msgs.get(lang, msgs["uz"])

# ══════════════════════════════════════════════════════
# KEYBOARD YORDAMCHILAR
# ══════════════════════════════════════════════════════
def kb_lang() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
        InlineKeyboardButton(text="🇷🇺 Русский",   callback_data="lang_ru"),
        InlineKeyboardButton(text="🇬🇧 English",   callback_data="lang_en"),
    ]])


def kb_exp(lang: str) -> InlineKeyboardMarkup:
    t = TX[lang]
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t["btn_exp_yes"], callback_data="exp_yes"),
        InlineKeyboardButton(text=t["btn_exp_no"],  callback_data="exp_no"),
    ]])


def kb_topics(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=cb)]
            for label, cb in TX[lang]["topic_btns"]
        ]
    )


def kb_risk(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=cb)]
            for label, cb in TX[lang]["risk_btns"]
        ]
    )


def kb_username(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=TX[lang]["btn_username"], callback_data="share_uname"),
    ]])


def kb_final(lang: str) -> InlineKeyboardMarkup:
    t = TX[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["btn_invest"],   callback_data="go_invest")],
        [InlineKeyboardButton(text=t["btn_question"], callback_data="go_question")],
    ])

# ══════════════════════════════════════════════════════
# BOT VA DISPATCHER
# ══════════════════════════════════════════════════════
bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML"),
)
dp = Dispatcher(storage=MemoryStorage())


# ─────────────────────── /start ─────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "🌍 <b>Tilni tanlang / Выберите язык / Choose language:</b>",
        reply_markup=kb_lang(),
    )
    await state.set_state(S.lang)


# ─────────────────────── TIL ────────────────────────────────────────────────
@dp.callback_query(S.lang, F.data.startswith("lang_"))
async def on_lang(cb: CallbackQuery, state: FSMContext):
    lang  = cb.data.split("_")[1]          # uz / ru / en
    tid   = cb.from_user.id
    fname = cb.from_user.first_name or "Do'stim"
    uname = cb.from_user.username

    upsert_user(tid, uname, fname, lang)
    log_msg(tid, "sys", f"lang={lang}")
    await state.update_data(lang=lang, fname=fname)

    await cb.message.edit_text(TX[lang]["greeting"])
    await asyncio.sleep(0.5)
    await cb.message.answer(TX[lang]["q_exp"], reply_markup=kb_exp(lang))
    await state.set_state(S.exp)
    await cb.answer()


# ─────────────────────── TAJRIBA ────────────────────────────────────────────
@dp.callback_query(S.exp, F.data.startswith("exp_"))
async def on_exp(cb: CallbackQuery, state: FSMContext):
    has_exp = cb.data == "exp_yes"
    data    = await state.get_data()
    lang    = data["lang"]
    tid     = cb.from_user.id

    await state.update_data(has_exp=has_exp, topic="—")
    set_user(tid, has_exp=int(has_exp))
    log_msg(tid, "user", f"exp={'yes' if has_exp else 'no'}")
    await cb.message.edit_reply_markup()   # tugmalarni o'chirish

    if has_exp:
        # Tajribasi bor → to'g'ri depozitga o'tamiz
        await cb.message.answer(TX[lang]["q_deposit"])
        await state.set_state(S.deposit)
    else:
        # Yangi boshlovchi → mavzu tanlaydi
        await cb.message.answer(TX[lang]["topic_intro"], reply_markup=kb_topics(lang))
        await state.set_state(S.topic)

    await cb.answer()


# ─────────────────────── MAVZU (faqat tajribasizlar) ────────────────────────
@dp.callback_query(S.topic, F.data.startswith("t_"))
async def on_topic(cb: CallbackQuery, state: FSMContext):
    topic = cb.data
    data  = await state.get_data()
    lang  = data["lang"]
    tid   = cb.from_user.id

    await state.update_data(topic=topic)
    set_user(tid, topic=topic)
    log_msg(tid, "user", f"topic={topic}")
    await cb.message.edit_reply_markup()
    await cb.answer()

    # AI tushuntirish yuboramiz
    await bot.send_chat_action(tid, "typing")
    prompt      = TOPIC_PROMPTS.get(topic, {}).get(lang, f"Explain {topic} for a beginner.")
    explanation = await ai(prompt, lang)
    log_msg(tid, "ai", explanation)
    await cb.message.answer(explanation)
    await asyncio.sleep(0.4)

    # Depozit savoliga o'tamiz
    await cb.message.answer(TX[lang]["q_deposit"])
    await state.set_state(S.deposit)


# ─────────────────────── DEPOZIT ────────────────────────────────────────────
@dp.message(S.deposit)
async def on_deposit(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["lang"]
    tid  = msg.from_user.id

    # Raqamni tozalash va tekshirish
    raw = (msg.text or "").strip()
    raw = raw.replace(",", ".").replace(" ", "").replace("$", "").replace("'", "")
    try:
        dep = float(raw)
        if dep <= 0:
            raise ValueError
    except ValueError:
        await msg.answer(TX[lang]["invalid_deposit"])
        return

    dep_text = f"${dep:,.0f}"
    await state.update_data(deposit_text=dep_text, deposit_usd=dep)
    set_user(tid, deposit_text=dep_text, deposit_usd=dep)
    log_msg(tid, "user", f"deposit={dep_text}")

    await msg.answer(TX[lang]["q_risk"], reply_markup=kb_risk(lang))
    await state.set_state(S.risk)


# ─────────────────────── RISK ───────────────────────────────────────────────
@dp.callback_query(S.risk, F.data.startswith("r_"))
async def on_risk(cb: CallbackQuery, state: FSMContext):
    risk = cb.data
    data = await state.get_data()
    lang = data["lang"]
    tid  = cb.from_user.id

    await state.update_data(risk=risk)
    set_user(tid, risk=risk)
    log_msg(tid, "user", f"risk={risk}")
    await cb.message.edit_reply_markup()

    await cb.message.answer(TX[lang]["q_contact"], reply_markup=kb_username(lang))
    await state.set_state(S.contact)
    await cb.answer()


# ─────────────────────── KONTAKT — username tugmasi ─────────────────────────
@dp.callback_query(S.contact, F.data == "share_uname")
async def on_share_uname(cb: CallbackQuery, state: FSMContext):
    tid   = cb.from_user.id
    uname = cb.from_user.username
    contact = f"@{uname}" if uname else f"ID: {tid}"

    await cb.message.edit_reply_markup()
    await state.update_data(contact=contact)
    set_user(tid, contact=contact)
    log_msg(tid, "user", f"contact={contact}")
    await cb.answer()
    await _finish(cb.message, state, tid)


# ─────────────────────── KONTAKT — matn yozilganida ─────────────────────────
@dp.message(S.contact)
async def on_contact_text(msg: Message, state: FSMContext):
    contact = msg.text.strip()
    tid     = msg.from_user.id

    await state.update_data(contact=contact)
    set_user(tid, contact=contact)
    log_msg(tid, "user", f"contact={contact}")
    await _finish(msg, state, tid)


# ══════════════════════════════════════════════════════
# FINISH — xulosa + AI tavsiya + admin xabar
# ══════════════════════════════════════════════════════
async def _finish(target: Message, state: FSMContext, tid: int):
    data         = await state.get_data()
    lang         = data.get("lang",         "uz")
    fname        = data.get("fname",        "—")
    has_exp      = data.get("has_exp",      False)
    topic        = data.get("topic",        "—")
    deposit_text = data.get("deposit_text", "—")
    deposit_usd  = data.get("deposit_usd",  0.0)
    risk         = data.get("risk",         "—")
    contact      = data.get("contact",      "—")
    t            = TX[lang]

    # Teglar
    topic_label = TOPIC_NAME.get(topic, TOPIC_NAME["—"]).get(lang, "—")
    exp_label   = t["exp_yes"] if has_exp else t["exp_no"]
    risk_label  = t["risk_lbl"].get(risk, risk)

    # Lead ball hisoblash
    score, status = calc_score(has_exp, deposit_usd, topic, risk)
    set_user(tid, lead_score=score, lead_status=status, flow_done=1)
    log.info(f"Flow tugadi — user {tid} | score={score} | {status}")

    # ── Profil xulosa ────────────────────────────────
    summary = (
        t["summary_title"]
        + f"  {t['lbl_name']}    : <b>{fname}</b>\n"
        + f"  {t['lbl_exp']}     : {exp_label}\n"
        + f"  {t['lbl_topic']}   : {topic_label}\n"
        + f"  {t['lbl_deposit']} : <b>{deposit_text}</b>\n"
        + f"  {t['lbl_risk']}    : {risk_label}\n"
        + f"  {t['lbl_contact']} : {contact}\n"
        + t["analyzing"]
    )
    await target.answer(summary)
    await bot.send_chat_action(tid, "typing")

    # ── AI shaxsiy tavsiya ───────────────────────────
    _exp_word = "bor" if has_exp else "yoq"
    ai_prompt = (
        f"Foydalanuvchi profili: ism={fname}, tajriba={_exp_word}, "
        f"qiziqish={topic_label}, depozit={deposit_text}, risk={risk_label}. "
        "Ushbu profil uchun issiq, shaxsiy 4-5 gaplik investitsiya tavsiyasi yoz. "
        "Qaysi strategiya mos, realistik natija nima, bitta aniq keyingi qadam."
    )
    ai_text = await ai(ai_prompt, lang)
    log_msg(tid, "ai", ai_text)

    # Tavsiya + tugmalar
    await target.answer(
        ai_text + "\n\n━━━━━━━━━━━━━━━━━━━━",
        reply_markup=kb_final(lang),
    )

    # ── Adminga xabar ────────────────────────────────
    await _notify_admin(
        tid, fname, contact, exp_label, topic_label,
        deposit_text, risk_label, score, status,
    )
    await state.set_state(S.chat)


# ══════════════════════════════════════════════════════
# ADMIN XABARI
# ══════════════════════════════════════════════════════
_EMOJI = {"Hot": "🔥", "Warm": "🌡️", "Cold": "🧊"}


async def _notify_admin(tid, name, contact, exp, topic,
                        deposit, risk, score, status):
    if not ADMIN_TELEGRAM_ID:
        return
    em  = _EMOJI.get(status, "📋")
    bar = "🟩" * (score // 10) + "⬜" * (10 - score // 10)
    text = (
        f"{em} <b>YANGI LEAD — {status.upper()}</b>\n"
        f"{'━' * 28}\n"
        f"👤  Ism       : <b>{name}</b>\n"
        f"📞  Kontakt   : <b>{contact}</b>\n"
        f"📊  Tajriba   : {exp}\n"
        f"🎯  Qiziqish  : {topic}\n"
        f"💰  Depozit   : <b>{deposit}</b>\n"
        f"⚡  Risk      : {risk}\n"
        f"{'━' * 28}\n"
        f"📈  Score     : <b>{score}/100</b>  {bar}\n"
        f"🏷   Status   : {em} <b>{status}</b>\n"
        f"🕐  Vaqt      : {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        f"{'━' * 28}\n"
        f"🆔  Telegram  : {tid}"
    )
    try:
        await bot.send_message(ADMIN_TELEGRAM_ID, text)
        log.info(f"Admin xabar yuborildi → {tid} ({status}, {score})")
    except Exception as e:
        log.error(f"Admin xabar xatosi: {e}")


# ══════════════════════════════════════════════════════
# ERKIN SAVOL-JAVOB (flow tugagandan keyin)
# ══════════════════════════════════════════════════════
@dp.callback_query(S.chat, F.data == "go_invest")
async def on_go_invest(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await cb.message.edit_reply_markup()
    await cb.message.answer(TX[lang]["farewell"])
    await cb.answer()


@dp.callback_query(S.chat, F.data == "go_question")
async def on_go_question(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    await cb.message.edit_reply_markup()
    await cb.message.answer(TX[lang]["free_prompt"])
    await cb.answer()


@dp.message(S.chat)
async def on_free_chat(msg: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "uz")
    tid  = msg.from_user.id
    text = msg.text or ""

    log_msg(tid, "user", text)
    await bot.send_chat_action(tid, "typing")

    # Kontekstli prompt — foydalanuvchi profili bilan
    _exp_w  = "bor" if data.get("has_exp") else "yoq"
    _topic  = data.get("topic", "?")
    _dep    = data.get("deposit_text", "?")
    _risk   = data.get("risk", "?")
    prompt  = (
        f"Kontekst: qiziqish={_topic}, depozit={_dep}, risk={_risk}, tajriba={_exp_w}.\n\n"
        f"Foydalanuvchi savoli: {text}"
    )
    reply = await ai(prompt, lang)
    log_msg(tid, "ai", reply)
    await msg.answer(reply)


# ─────────────────────── CATCH-ALL ──────────────────────────────────────────
@dp.message()
async def catch_all(msg: Message, state: FSMContext):
    cur = await state.get_state()
    if cur is None:
        await msg.answer(
            "👋 Botni ishlatish uchun /start bosing.\n"
            "Нажмите /start для начала.\n"
            "Press /start to begin."
        )


# ══════════════════════════════════════════════════════
# ISHGA TUSHIRISH
# ══════════════════════════════════════════════════════
async def main():
    # Muhim env o'zgaruvchilarni tekshirish
    if not TELEGRAM_TOKEN:
        log.error("❌  TELEGRAM_TOKEN berilmagan! export TELEGRAM_TOKEN=... qiling.")
        return
    if not GEMINI_API_KEY:
        log.error("❌  GEMINI_API_KEY berilmagan! export GEMINI_API_KEY=... qiling.")
        return

    init_db()

    log.info("━" * 48)
    log.info("  🤖  Telegram AI Sales Bot  v4.0")
    log.info(f"  Admin ID : {ADMIN_TELEGRAM_ID or 'BERILMAGAN'}")
    log.info("━" * 48)

    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
