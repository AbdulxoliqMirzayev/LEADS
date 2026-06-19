from __future__ import annotations

from aiogram import Bot

from db import list_incomplete_users_for_reminder, mark_reminder_sent
from models import LANG_EN, LANG_RU, LANG_UZ, Lang


def _reminder_text(lang: Lang, name: str | None) -> str:
    display_name = name or {
        LANG_UZ: "hurmatli mijoz",
        LANG_RU: "уважаемый клиент",
        LANG_EN: "dear client",
    }.get(lang, "hurmatli mijoz")

    if lang == LANG_RU:
        return (
            f"Здравствуйте, {display_name}.\n\n"
            "Вы начали регистрацию в BeTrader, но не завершили ее до конца. "
            "Пожалуйста, оставьте номер телефона, чтобы наш специалист мог связаться с вами.\n\n"
            "Мы ждём вас 🙂"
        )

    if lang == LANG_EN:
        return (
            f"Hello, {display_name}.\n\n"
            "You started registration with BeTrader but did not finish it. "
            "Please leave your phone number so our specialist can contact you.\n\n"
            "We are waiting for you 🙂"
        )

    return (
        f"Assalomu alaykum, {display_name}.\n\n"
        "Siz BeTrader ro'yxatdan o'tish jarayonini boshlagansiz, lekin oxirigacha yakunlamadingiz. "
        "Iltimos, telefon raqamingizni qoldiring, mutaxassislarimiz siz bilan bog'lanadi.\n\n"
        "Sizni kutyapmiz 🙂"
    )


async def send_daily_inactive_report(bot: Bot) -> None:
    """
    24 soatdan ortiq tugallanmagan ro'yxatdan o'tishlarga bir martalik eslatma yuboradi.
    """
    users = list_incomplete_users_for_reminder(hours=24, limit=100)

    for user in users:
        tg_id = user.get("tg_id")
        if not tg_id:
            continue

        lang: Lang = user.get("lang") or LANG_UZ
        name = user.get("name") or user.get("full_name")

        try:
            await bot.send_message(tg_id, _reminder_text(lang, name))
            mark_reminder_sent(tg_id)
        except Exception:
            continue
