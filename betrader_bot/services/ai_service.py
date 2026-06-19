from __future__ import annotations

import asyncio
import ast
from pathlib import Path
from typing import Optional

import openai
from openai import OpenAI

from config import SETTINGS
from models import LANG_EN, LANG_RU, LANG_UZ, Lang


_client: Optional[OpenAI] = OpenAI(api_key=SETTINGS.OPENAI_API_KEY) if SETTINGS.OPENAI_API_KEY else None
_prompt_cache: str | None = None


DEFAULT_SYSTEM_PROMPT = """
You are Akmal, a professional BeTrader support and sales representative.

Core rules:
- Never say you are an AI, bot, model, or assistant.
- Match the user's language exactly: Uzbek, Russian, or English.
- Be calm, confident, helpful, and sales-oriented without pressure.
- Support and problem-solving questions have priority over sales.
- Never promise guaranteed profit, fixed profit, or 100% safety.
- Always mention that market results can change and risk exists.
- Explain financial topics simply and clearly.
- Keep answers concise: 2-5 short paragraphs.
- Use light professional emojis only when helpful.
- End with one useful next question when appropriate.

Business goal:
- Help the user understand BeTrader, risk levels, registration, phone contact, payouts, and investment options.
- Build trust through clarity, not unrealistic promises.
""".strip()


def _load_custom_prompt() -> str:
    global _prompt_cache

    if _prompt_cache is not None:
        return _prompt_cache

    path = SETTINGS.AI_SYSTEM_PROMPT_FILE
    if path:
        try:
            prompt_path = Path(path)
            if prompt_path.exists():
                raw = prompt_path.read_text(encoding="utf-8").strip()
                _prompt_cache = _extract_prompt_text(raw)
                if _prompt_cache:
                    return _prompt_cache
        except Exception:
            pass

    _prompt_cache = DEFAULT_SYSTEM_PROMPT
    return _prompt_cache


def _extract_prompt_text(raw: str) -> str:
    if not raw.startswith("SYSTEM_PROMPT"):
        return raw

    try:
        module = ast.parse(raw)
        for node in module.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "SYSTEM_PROMPT":
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            return node.value.value.strip()
    except Exception:
        pass

    marker = '"""'
    first = raw.find(marker)
    last = raw.rfind(marker)
    if first != -1 and last != -1 and last > first:
        return raw[first + len(marker):last].strip()

    return raw


def _system_prompt(lang: Lang) -> str:
    if lang == LANG_RU:
        language_rule = "Ответь только на русском языке."
    elif lang == LANG_EN:
        language_rule = "Answer only in English."
    else:
        language_rule = "Faqat o'zbek tilida javob ber."

    return f"{_load_custom_prompt()}\n\n{language_rule}"


def _safety_footer(lang: Lang) -> str:
    if lang == LANG_RU:
        return "⚠️ Информация носит общий характер и не является финансовой рекомендацией. Рынок несет риск."
    if lang == LANG_EN:
        return "⚠️ This is general information, not financial advice. Markets involve risk."
    return "⚠️ Bu umumiy ma'lumot, moliyaviy tavsiya emas. Bozorda risk mavjud."


def _not_configured(lang: Lang) -> str:
    if lang == LANG_RU:
        return "Модуль консультации сейчас не настроен: OPENAI_API_KEY не найден. ⚙️"
    if lang == LANG_EN:
        return "The consultation module is not configured: OPENAI_API_KEY is missing. ⚙️"
    return "Hozir konsultatsiya moduli sozlanmagan: OPENAI_API_KEY topilmadi. ⚙️"


async def ask_ai(lang: Lang, user_text: str) -> str:
    if not _client:
        return _not_configured(lang)

    system = _system_prompt(lang)

    def _call_openai() -> str:
        resp = _client.chat.completions.create(
            model=SETTINGS.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
            temperature=0.35,
        )
        out = (resp.choices[0].message.content or "").strip()
        footer = _safety_footer(lang)
        if out and footer not in out:
            out = out.rstrip() + "\n\n" + footer
        return out or footer

    try:
        return await asyncio.to_thread(_call_openai)

    except openai.RateLimitError:
        if lang == LANG_RU:
            return "Лимит консультации исчерпан или баланс недостаточен. Попробуйте немного позже. ⚙️"
        if lang == LANG_EN:
            return "The consultation limit has been reached or balance is insufficient. Please try again later. ⚙️"
        return "Hozir konsultatsiya limiti tugagan yoki balans yetarli emas. Birozdan keyin urinib ko'ring. ⚙️"

    except openai.APIConnectionError:
        if lang == LANG_RU:
            return "Проблема с подключением к серверу консультации. Проверьте интернет и попробуйте снова. ⚙️"
        if lang == LANG_EN:
            return "Connection issue with the consultation server. Check the internet and try again. ⚙️"
        return "AI server bilan ulanishda muammo. Internetni tekshirib, qayta urinib ko'ring. ⚙️"

    except openai.APIStatusError:
        if lang == LANG_RU:
            return "Во временной консультационной службе возникла проблема. Попробуйте позже. ⚙️"
        if lang == LANG_EN:
            return "Temporary consultation service issue. Please try again later. ⚙️"
        return "Konsultatsiya xizmatida vaqtinchalik muammo bor. Keyinroq urinib ko'ring. ⚙️"

    except Exception:
        if lang == LANG_RU:
            return "Произошла техническая ошибка. Попробуйте позже. ⚙️"
        if lang == LANG_EN:
            return "A technical error occurred. Please try again later. ⚙️"
        return "Texnik xato yuz berdi. Keyinroq qayta urinib ko'ring. ⚙️"
