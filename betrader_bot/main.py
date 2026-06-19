# main.py
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import SETTINGS
from db import init_db

from handlers.user_handlers import router as user_router
from handlers.admin_handlers import router as admin_router
from handlers.ad_handlers import router as ad_router

from jobs.daily_inactive_report import send_daily_inactive_report


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # 1. Database init
    init_db()

    # 2. Bot va Dispatcher
    bot = Bot(
        token=SETTINGS.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()

    # 3. Routerlar
    dp.include_router(admin_router)
    dp.include_router(ad_router)
    dp.include_router(user_router)

    # 4. Scheduler
    scheduler = AsyncIOScheduler(timezone=SETTINGS.TIMEZONE)

    scheduler.add_job(
        send_daily_inactive_report,
        trigger=CronTrigger(
            hour=SETTINGS.DAILY_REPORT_HOUR,
            minute=SETTINGS.DAILY_REPORT_MINUTE,
        ),
        args=[bot],
        id="daily_inactive_report",
        replace_existing=True,
    )

    scheduler.start()

    logging.info("BeTrader AI Telegram bot ishga tushmoqda...")
    logging.info(
        "Daily inactive report scheduled at %02d:%02d (%s)",
        SETTINGS.DAILY_REPORT_HOUR,
        SETTINGS.DAILY_REPORT_MINUTE,
        SETTINGS.TIMEZONE,
    )

    # 5. Polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())