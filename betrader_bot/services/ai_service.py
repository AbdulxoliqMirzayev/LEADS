# services/ai_service.py
from __future__ import annotations

import asyncio
from typing import Optional

import openai
from openai import OpenAI

from config import SETTINGS
from models import Lang, LANG_UZ, LANG_RU, LANG_EN


# OpenAI client
_client: Optional[OpenAI] = OpenAI(api_key=SETTINGS.OPENAI_API_KEY) if SETTINGS.OPENAI_API_KEY else None


def _system_prompt(lang: Lang) -> str:
    """
    BeTrader style: professional, calm, trust-building, risk-aware.
    Replies must follow user's language.
    Keep 3–6 short paragraphs, light professional emojis, end with a question.
    """
    if lang == LANG_RU:
        language_rule = "Отвечай ТОЛЬКО на русском."
    elif lang == LANG_EN:
        language_rule = "Answer ONLY in English."
    else:
        language_rule = "Faqat O‘zbek tilida javob ber."

    return f"""
You are a Senior Financial Advisor at BeTrader.
{language_rule}

Style:
- Professional, calm, trust-building, transparent
- Friendly but not casual
- Not robotic
Rules:
- Never promise guaranteed profit
- Never say 100% safe
- Never hide risk
- Don't argue with user
- Explain risk-return relationship
- Use simple analogies
- Keep answers 3–6 short paragraphs
- Use light professional emojis (1–3 max)
- End with an engagement question

If user asks about:
- company trust/pyramid: explain legal/company presence and that risk exists
- returns: use "may / mumkin" language, no guarantees, mention volatility
- how it works: explain steps simply
- withdrawals/payout: explain generally, ask for plan/tariff details if needed
""".strip()


def _safety_footer(lang: Lang) -> str:
    if lang == LANG_RU:
        return "⚠️ Информация носит общий характер и не является финансовой рекомендацией. Рынок несёт риск."
    if lang == LANG_EN:
        return "⚠️ This is general information, not financial advice. Markets involve risk."
    return "⚠️ Bu umumiy ma’lumot, moliyaviy tavsiya emas. Bozorda risk mavjud."


async def ask_ai(lang: Lang, user_text: str) -> str:
    """
    Main entry for handlers. Returns assistant text in user's language.
    Handles quota/rate errors gracefully.
    """
    if not _client:
        # API key yo'q bo'lsa ham bot yiqilmasin
        if lang == LANG_RU:
            return "AI sozlanmagan: OPENAI_API_KEY topilmadi. ⚙️"
        if lang == LANG_EN:
            return "AI is not configured: OPENAI_API_KEY is missing. ⚙️"
        return "AI sozlanmagan: OPENAI_API_KEY topilmadi. ⚙️"

    system = _system_prompt(lang)

    def _call_openai() -> str:
        resp = _client.chat.completions.create(
            model=SETTINGS.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
            temperature=0.4,
        )
        out = resp.choices[0].message.content or ""
        # Safety footer qo'shamiz (juda uzun bo'lmasin)
        if out and _safety_footer(lang) not in out:
            out = out.rstrip() + "\n\n" + _safety_footer(lang)
        return out

    try:
        return await asyncio.to_thread(_call_openai)

    except openai.RateLimitError:
        # Bu sizda ko'p chiqqan: insufficient_quota / 429
        if lang == LANG_RU:
            return (
                "Hozir AI limiti tugagan yoki balans yetarli emas. ⚙️\n\n"
                "Iltimos, birozdan keyin urinib ko‘ring yoki admin balansni yangilasin."
            )
        if lang == LANG_EN:
            return (
                "AI usage limit reached or balance is insufficient. ⚙️\n\n"
                "Please try again later or ask the admin to top up the balance."
            )
        return (
            "Hozir AI limiti tugagan yoki balans yetarli emas. ⚙️\n\n"
            "Birozdan keyin urinib ko‘ring yoki admin balansni yangilasin."
        )

    except openai.APIConnectionError:
        if lang == LANG_RU:
            return "AI server bilan ulanishda muammo. Internetni tekshirib, qayta urinib ko‘ring. ⚙️"
        if lang == LANG_EN:
            return "Connection issue to AI server. Check internet and try again. ⚙️"
        return "AI server bilan ulanishda muammo. Internetni tekshirib, qayta urinib ko‘ring. ⚙️"

    except openai.APIStatusError:
        if lang == LANG_RU:
            return "AI xizmatida vaqtinchalik muammo. Keyinroq urinib ko‘ring. ⚙️"
        if lang == LANG_EN:
            return "Temporary AI service issue. Please try again later. ⚙️"
        return "AI xizmatida vaqtinchalik muammo. Keyinroq urinib ko‘ring. ⚙️"

    except Exception:
        if lang == LANG_RU:
            return "Texnik xato yuz berdi. Keyinroq qayta urinib ko‘ring. ⚙️"
        if lang == LANG_EN:
            return "A technical error occurred. Please try again later. ⚙️"
        return "Texnik xato yuz berdi. Keyinroq qayta urinib ko‘ring. ⚙️"