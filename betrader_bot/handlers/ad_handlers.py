# handlers/ad_handlers.py
from __future__ import annotations

import asyncio
from typing import Dict, Optional, Tuple

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from config import SETTINGS
from utils import is_admin
from db import list_users, save_broadcast, add_event

router = Router()

# Admin broadcast flow state (in-memory)
# admin_id -> True (waiting for ad content)
WAITING_BROADCAST: Dict[int, bool] = {}


def _no_access() -> str:
    return "⛔ Siz admin emassiz."


def _prompt() -> str:
    return (
        "📢 Reklama yuborish rejimi yoqildi.\n\n"
        "Yubormoqchi bo‘lgan reklamani jo‘nating:\n"
        "• Matn\n"
        "• Rasm + caption\n"
        "• Video + caption\n"
        "• Document + caption\n\n"
        "Bekor qilish: /cancel"
    )


def _extract_broadcast_payload(m: Message) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Returns: (kind, file_id, text)
    kind: text | photo | video | document
    """
    text = m.text or m.caption

    if m.photo:
        # biggest photo is last
        file_id = m.photo[-1].file_id
        return "photo", file_id, text

    if m.video:
        return "video", m.video.file_id, text

    if m.document:
        return "document", m.document.file_id, text

    # fallback: text only
    return "text", None, m.text


async def _broadcast_to_all(bot, kind: str, file_id: Optional[str], text: Optional[str]) -> Tuple[int, int]:
    """
    Sends broadcast to all users in DB.
    Returns (sent_count, fail_count)
    """
    sent = 0
    failed = 0

    offset = 0
    limit = 200

    while True:
        users = list_users(limit=limit, offset=offset)
        if not users:
            break

        for u in users:
            tg_id = u.get("tg_id")
            if not tg_id:
                continue

            try:
                if kind == "text":
                    if text:
                        await bot.send_message(tg_id, text)
                    else:
                        # nothing to send
                        continue

                elif kind == "photo":
                    await bot.send_photo(tg_id, photo=file_id, caption=text or "")

                elif kind == "video":
                    await bot.send_video(tg_id, video=file_id, caption=text or "")

                elif kind == "document":
                    await bot.send_document(tg_id, document=file_id, caption=text or "")

                else:
                    # unknown type fallback
                    if text:
                        await bot.send_message(tg_id, text)

                sent += 1

                # Telegram flood’ni kamaytirish uchun kichik pauza
                await asyncio.sleep(0.03)

            except Exception:
                failed += 1
                # user botni blok qilgan bo‘lishi mumkin; ignore
                continue

        offset += limit

    return sent, failed


# =========================
# Admin "Reklama yuborish" callback
# keyboards.py: CB_ADMIN_BROADCAST = "admin:broadcast"
# =========================
@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(c: CallbackQuery):
    if not is_admin(c.from_user.id, SETTINGS.ADMIN_IDS):
        await c.answer("No access", show_alert=True)
        return

    WAITING_BROADCAST[c.from_user.id] = True
    await c.message.answer(_prompt())
    add_event(c.from_user.id, "menu_click", "admin_broadcast_start")
    await c.answer()


# =========================
# /cancel - stop waiting mode
# =========================
@router.message(F.text == "/cancel")
async def cancel(m: Message):
    if not is_admin(m.from_user.id, SETTINGS.ADMIN_IDS):
        await m.answer(_no_access())
        return

    if WAITING_BROADCAST.pop(m.from_user.id, None):
        await m.answer("✅ Bekor qilindi.")
        add_event(m.from_user.id, "menu_click", "admin_broadcast_cancel")
    else:
        await m.answer("ℹ️ Hozir broadcast rejimi yoqilmagan.")


# =========================
# Catch admin message when waiting for broadcast
# =========================
# Catch admin message when waiting for broadcast
@router.message(F.from_user.id.in_(list(SETTINGS.ADMIN_IDS)))
async def admin_broadcast_receive(m: Message):
    # admin bo'lsa ham, broadcast rejimi yoqilmagan bo'lsa ushlamaydi
    if not WAITING_BROADCAST.get(m.from_user.id):
        return  # normal admin message, ignore here

    kind, file_id, text = _extract_broadcast_payload(m)

    # minimal validation
    if kind == "text" and (not text or not text.strip()):
        await m.answer("Iltimos, reklama matnini yuboring yoki rasm/video/document jo'nating. /cancel")
        return

    save_broadcast(m.from_user.id, kind, file_id, text)
    add_event(m.from_user.id, "broadcast_sent", kind)

    await m.answer("🚀 Reklama yuborilmoqda...")

    sent, failed = await _broadcast_to_all(m.bot, kind, file_id, text)

    WAITING_BROADCAST.pop(m.from_user.id, None)

    await m.answer(
        f"✅ Tayyor.\n\n"
        f"📤 Yuborildi: {sent}\n"
        f"⚠️ Yetib bormadi (blok/error): {failed}"
    )