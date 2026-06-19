# texts.py
from __future__ import annotations
from typing import Dict

from models import Lang, LANG_UZ, LANG_RU, LANG_EN, RiskProfile, RISK_HALOL, RISK_KONSERV, RISK_YUQORI


def t(lang: Lang, uz: str, ru: str, en: str) -> str:
    if lang == LANG_RU:
        return ru
    if lang == LANG_EN:
        return en
    return uz


# =========================
# GLOBAL STATIC INFO
# =========================
COMPANY_CONTACTS = {
    "phone": "+99890 893 55 55",
    "telegram": "@betrader_uz",
    "email": "info@betrader.uz",
    "address": "100011, O‘zbekiston Respublikasi, Toshkent sh., Shayxontoxur tumani, Navoiy ko‘chasi, 3-uy (kvartal 76).",
    "site": "betrader.uz",
    "discount_code": "BTR2024",
}

RISK_TEXTS_UZ = {
    RISK_HALOL: (
        "🟢 **Halol (past risk)**\n"
        "• Maqsad: kapitalni asrash, barqarorlik\n"
        "• Volatillik: past\n"
        "• Kutiladigan daromad: bozor sharoitiga bog‘liq\n\n"
        "📌 Risk past bo‘lsa, daromad ham odatda pastroq bo‘ladi."
    ),
    RISK_KONSERV: (
        "🟡 **Konservativ (o‘rta risk)**\n"
        "• Maqsad: balans — xavf va daromad o‘rtasida\n"
        "• Volatillik: o‘rtacha\n"
        "• Kutiladigan daromad: bozor sharoitiga bog‘liq\n\n"
        "📌 Risk o‘rta bo‘lsa, daromad ham o‘rtacha bo‘lishi mumkin."
    ),
    RISK_YUQORI: (
        "🔴 **Yuqori (agressiv risk)**\n"
        "• Maqsad: yuqori daromad potensiali\n"
        "• Volatillik: yuqori\n"
        "• Kutiladigan daromad: yuqori bo‘lishi mumkin, lekin yo‘qotish riski ham yuqori\n\n"
        "📌 Risk yuqori bo‘lsa, daromad ham yuqori bo‘lishi **mumkin**."
    ),
}

RISK_TEXTS_RU = {
    RISK_HALOL: (
        "🟢 **Низкий риск**\n"
        "• Цель: сохранение капитала, стабильность\n"
        "• Волатильность: низкая\n"
        "• Потенциальная доходность зависит от рынка\n\n"
        "📌 Чем ниже риск — тем чаще ниже потенциальная доходность."
    ),
    RISK_KONSERV: (
        "🟡 **Средний риск**\n"
        "• Цель: баланс риска и доходности\n"
        "• Волатильность: средняя\n"
        "• Потенциальная доходность зависит от рынка\n\n"
        "📌 Средний риск — это обычно средняя потенциальная доходность."
    ),
    RISK_YUQORI: (
        "🔴 **Высокий риск**\n"
        "• Цель: высокая потенциальная доходность\n"
        "• Волатильность: высокая\n"
        "• Доходность может быть выше, но риск просадки тоже выше\n\n"
        "📌 Чем выше риск — тем выше доходность **может** быть."
    ),
}

RISK_TEXTS_EN = {
    RISK_HALOL: (
        "🟢 **Halol (past risk)**\n"
        "• 15–20% yillik (taxminiy)\n"
        "• 1.2–1.6% oylik (o‘rtacha)\n"
        "• Kapitalni saqlashga yo‘naltirilgan\n"
        "• Volatillik: past\n\n"
        "📌 Risk past bo‘lsa, daromad ham odatda pastroq bo‘ladi."
    ),
    RISK_KONSERV: (
        "🟡 **Konservativ (o‘rta risk)**\n"
        "• 20–25% yillik (taxminiy)\n"
        "• 1.8–2.1% oylik (o‘rtacha)\n"
        "• Balansli yondashuv\n"
        "• Volatillik: o‘rtacha\n\n"
        "📌 Risk o‘rta bo‘lsa, daromad ham o‘rtacha bo‘lishi mumkin."
    ),
    RISK_YUQORI: (
        "🔴 **Yuqori (agressiv risk)**\n"
        "• 30% gacha yillik (taxminiy)\n"
        "• 2.3–2.6% oylik (o‘rtacha)\n"
        "• Yuqori daromad potensiali\n"
        "• Volatillik: yuqori\n\n"
        "📌 Risk yuqori bo‘lsa, daromad ham yuqori bo‘lishi **mumkin**."
    ),
}


def risk_text(lang: Lang, risk: RiskProfile) -> str:
    if lang == LANG_RU:
        return RISK_TEXTS_RU[risk]
    if lang == LANG_EN:
        return RISK_TEXTS_EN[risk]
    return RISK_TEXTS_UZ[risk]


# =========================
# MAIN TEXT MAP
# =========================
TEXT: Dict[str, Dict[Lang, str]] = {
    "choose_lang": {
        LANG_UZ: "Assalomu alaykum! Tilni tanlang 👇",
        LANG_RU: "Здравствуйте! Выберите язык 👇",
        LANG_EN: "Hello! Choose a language 👇",
    },

    "ask_experience": {
        LANG_UZ: "Fond bozori / savdo bo‘yicha tajribangiz bormi?",
        LANG_RU: "Есть ли у вас опыт в рынке/трейдинге?",
        LANG_EN: "Do you have experience with markets/trading?",
    },

    "menu_hint": {
        LANG_UZ: "Menyudan bo‘lim tanlang yoki savolingiz bo‘lsa yozing 🙂",
        LANG_RU: "Выберите раздел в меню или задайте вопрос 🙂",
        LANG_EN: "Choose a section from the menu or ask a question 🙂",
    },

    "ask_risk": {
        LANG_UZ: "Qaysi risk darajasi sizga mos? 👇",
        LANG_RU: "Какой уровень риска вам подходит? 👇",
        LANG_EN: "Which risk level fits you best? 👇",
    },

    "ask_amount": {
        LANG_UZ: "Ajratmoqchi bo‘lgan summangizni yozing (masalan: 1000 yoki 5000). 💰",
        LANG_RU: "Укажите сумму, которую планируете выделить (например: 1000 или 5000). 💰",
        LANG_EN: "Type the amount you plan to allocate (e.g., 1000 or 5000). 💰",
    },

    "ask_phone": {
    LANG_UZ: "Telefon raqamingizni yuboring: 📲 *Kontakt yuborish* tugmasini bosing yoki qo‘lda yozing (masalan: +998901234567).",
    LANG_RU: "Отправьте номер: нажмите 📲 *Отправить контакт* или введите вручную (например: +998901234567).",
    LANG_EN: "Send your phone number: tap 📲 *Send contact* or type it (e.g., +998901234567).",
    },

    "amount_saved": {
        LANG_UZ: "✅ Summa qabul qilindi.",
        LANG_RU: "✅ Сумма сохранена.",
        LANG_EN: "✅ Amount saved.",
    },

    "phone_saved": {
        LANG_UZ: "✅ Telefon raqam saqlandi.",
        LANG_RU: "✅ Телефон сохранён.",
        LANG_EN: "✅ Phone saved.",
    },

    "company_about": {
        LANG_UZ: (
            "🏢 **BeTrader haqida**\n\n"
            "BeTrader — prop savdo kompaniyasi va savdo akademiyasi. "
            "Maqsadimiz: treyderlar uchun qulay shartlar va ta’lim orqali natijaga olib chiqish.\n\n"
            "📌 Muhim: bu yerda ham risk bor — bozor o‘zgaruvchan. "
            "O‘tmishdagi natijalar kelajak uchun kafolat emas.\n\n"
            f"📞 Telefon: {COMPANY_CONTACTS['phone']}\n"
            f"✉️ Email: {COMPANY_CONTACTS['email']}\n"
            f"💬 Telegram: {COMPANY_CONTACTS['telegram']}\n"
            f"📍 Manzil: {COMPANY_CONTACTS['address']}"
        ),
        LANG_RU: (
            "🏢 **О BeTrader**\n\n"
            "BeTrader — prop-трейдинговая компания и торговая академия. "
            "Наша цель — дать трейдерам условия и обучение, чтобы расти системно.\n\n"
            "📌 Важно: рынок несёт риски — волатильность реальна. "
            "Прошлые результаты не гарантируют будущие.\n\n"
            f"📞 Телефон: {COMPANY_CONTACTS['phone']}\n"
            f"✉️ Email: {COMPANY_CONTACTS['email']}\n"
            f"💬 Telegram: {COMPANY_CONTACTS['telegram']}\n"
            f"📍 Адрес: {COMPANY_CONTACTS['address']}"
        ),
        LANG_EN: (
            "🏢 **About BeTrader**\n\n"
            "BeTrader is a prop trading company and trading academy. "
            "Our goal is to provide conditions and education that help traders grow consistently.\n\n"
            "📌 Important: markets are volatile and carry risk. "
            "Past performance is not a guarantee of future results.\n\n"
            f"📞 Phone: {COMPANY_CONTACTS['phone']}\n"
            f"✉️ Email: {COMPANY_CONTACTS['email']}\n"
            f"💬 Telegram: {COMPANY_CONTACTS['telegram']}\n"
            f"📍 Address: {COMPANY_CONTACTS['address']}"
        ),
    },

    "payout_info": {
        LANG_UZ: (
            "💰 **To‘lovlar (Payout)**\n\n"
            "Prop savdoda odatda foyda ulushi (profit split) qo‘llaniladi. "
            "Nisbat vaqt o‘tishi bilan oshishi mumkin (masalan, 80% gacha).\n\n"
            "📌 To‘lovlar shartlari tarif va kelishuvga bog‘liq. "
            "Savol bo‘lsa yozing — aniq tushuntirib beraman."
        ),
        LANG_RU: (
            "💰 **Выплаты (Payout)**\n\n"
            "В проп-трейдинге часто используется profit split. "
            "Доля трейдера может увеличиваться со временем (например, до 80%).\n\n"
            "📌 Условия зависят от тарифа и договорённости. "
            "Если есть вопрос — напишите, объясню."
        ),
        LANG_EN: (
            "💰 **Payouts**\n\n"
            "Prop trading often uses a profit split model. "
            "Your share can increase over time (e.g., up to 80%).\n\n"
            "📌 Exact terms depend on your plan and agreement. "
            "If you have questions, ask — I’ll clarify."
        ),
    },

    "withdraw_info": {
        LANG_UZ: (
            "💸 **Pul yechish**\n\n"
            "Pul yechish tartibi tarif va savdo davriga bog‘liq bo‘ladi. "
            "Odatda payout so‘rovi savdo oyi yakunidan keyin amalga oshiriladi.\n\n"
            "📌 Bozor xavfi mavjud, natijalar kafolatlanmaydi. "
            "Sizga qaysi tarif qiziq — ayting, mos variantni topib beraman."
        ),
        LANG_RU: (
            "💸 **Вывод средств**\n\n"
            "Процесс вывода зависит от тарифа и торгового периода. "
            "Обычно запрос на payout оформляется после окончания торгового месяца.\n\n"
            "📌 Рынок несёт риски, результаты не гарантируются. "
            "Какой тариф вас интересует? Подскажу подходящий."
        ),
        LANG_EN: (
            "💸 **Withdrawals**\n\n"
            "Withdrawal terms depend on your plan and trading period. "
            "Typically, payout requests are made after the trading month ends.\n\n"
            "📌 Markets carry risk; results are not guaranteed. "
            "Which plan are you considering? I can guide you."
        ),
    },

    "investment_info": {
    LANG_UZ: (
        "📈 **Investitsiya nima?**\n\n"
        "Oddiy qilib: investitsiya — pulni hozir sarflamasdan, uni aktivlarga joylab, vaqt o‘tishi bilan oshirishga urinish.\n\n"
        "🔎 Muhim: daromad bo‘lishi uchun risk ham bo‘ladi. Shuning uchun riskni to‘g‘ri tanlash va diversifikatsiya muhim.\n\n"
        "Siz qaysi risk darajasini ko‘rib chiqyapsiz? 🙂"
    ),
    LANG_RU: (
        "📈 **Что такое инвестиции?**\n\n"
        "Просто: инвестиции — это размещение капитала в активах, чтобы со временем попытаться увеличить его.\n\n"
        "🔎 Важно: доходность связана с риском. Поэтому важны выбор риска и диверсификация.\n\n"
        "Какой уровень риска вы рассматриваете? 🙂"
    ),
    LANG_EN: (
        "📈 **What is investing?**\n\n"
        "Simply: investing means allocating money into assets to try to grow it over time.\n\n"
        "🔎 Important: returns come with risk. Choosing the right risk level and diversification matters.\n\n"
        "Which risk level are you considering? 🙂"
    ),
},

    "ask_free_question": {
        LANG_UZ: "Savolingizni yozing — men sizga sodda qilib tushuntirib beraman 🙂",
        LANG_RU: "Напишите вопрос — я объясню простыми словами 🙂",
        LANG_EN: "Ask your question — I’ll explain it simply 🙂",
    },

    "ai_limit": {
        LANG_UZ: "Hozir AI limiti tugagan. Administrator OpenAI balansini yangilashi kerak. ⚙️",
        LANG_RU: "Лимит AI исчерпан. Администратору нужно пополнить баланс OpenAI. ⚙️",
        LANG_EN: "AI usage limit reached. Admin needs to top up OpenAI balance. ⚙️",
    },

    "invalid_amount": {
        LANG_UZ: "Summani sonlarda yozing. Masalan: 1000 yoki 5000.",
        LANG_RU: "Введите сумму числами. Например: 1000 или 5000.",
        LANG_EN: "Type the amount as a number. Example: 1000 or 5000.",
    },

    "invalid_phone": {
        LANG_UZ: "Telefon raqamni to‘g‘ri yozing. Masalan: +998901234567.",
        LANG_RU: "Введите корректный номер. Например: +998901234567.",
        LANG_EN: "Enter a valid phone number. Example: +998901234567.",
    },

    "discount": {
        LANG_UZ: f"🎁 Chegirma kodi: **{COMPANY_CONTACTS['discount_code']}** (aksiya bo‘lishi mumkin).",
        LANG_RU: f"🎁 Промокод: **{COMPANY_CONTACTS['discount_code']}** (может быть акция).",
        LANG_EN: f"🎁 Promo code: **{COMPANY_CONTACTS['discount_code']}** (may be an active offer).",
    },
}