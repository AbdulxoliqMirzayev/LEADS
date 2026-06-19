# config.py
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# .env fayldan o'qish
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_GOOGLE_SERVICE_ACCOUNT_FILE = str(BASE_DIR / "baracap-ac2298016b85.json")


@dataclass(frozen=True)
class Settings:
    # Telegram
    TELEGRAM_BOT_TOKEN: str

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    AI_SYSTEM_PROMPT_FILE: str

    # Admin
    ADMIN_IDS: set[int]

    # Database
    DB_PATH: str

    # Google Sheets
    GOOGLE_SERVICE_ACCOUNT_JSON: str
    GOOGLE_SERVICE_ACCOUNT_FILE: str
    GOOGLE_SHEETS_SPREADSHEET_ID: str
    GOOGLE_SHEETS_WORKSHEET: str

    # Scheduler
    TIMEZONE: str
    DAILY_REPORT_HOUR: int
    DAILY_REPORT_MINUTE: int


def _parse_admin_ids(raw: str) -> set[int]:
    """
    ADMIN_IDS="123,456" formatdan set[int] qiladi.
    """
    ids: set[int] = set()
    raw = (raw or "").strip()
    if not raw:
        return ids
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


def _resolve_path(raw: str, default: str) -> str:
    value = (raw or default).strip()
    if not value:
        return ""

    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str(BASE_DIR / path)


def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN topilmadi. .env faylga yozing.")

    return Settings(
        TELEGRAM_BOT_TOKEN=token,

        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", "").strip(),
        OPENAI_MODEL=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
        AI_SYSTEM_PROMPT_FILE=os.getenv("AI_SYSTEM_PROMPT_FILE", "").strip(),

        ADMIN_IDS=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),

        DB_PATH=os.getenv("DB_PATH", "betrader.sqlite3").strip(),

        GOOGLE_SERVICE_ACCOUNT_JSON=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip(),
        GOOGLE_SERVICE_ACCOUNT_FILE=_resolve_path(
            os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", ""),
            DEFAULT_GOOGLE_SERVICE_ACCOUNT_FILE,
        ),
        GOOGLE_SHEETS_SPREADSHEET_ID=os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "").strip(),
        GOOGLE_SHEETS_WORKSHEET=os.getenv("GOOGLE_SHEETS_WORKSHEET", "Leads").strip(),

        TIMEZONE=os.getenv("TIMEZONE", "Asia/Tashkent").strip(),
        DAILY_REPORT_HOUR=int(os.getenv("DAILY_REPORT_HOUR", "20")),
        DAILY_REPORT_MINUTE=int(os.getenv("DAILY_REPORT_MINUTE", "0")),
    )


# Global settings (boshqa fayllar shuni import qiladi)
SETTINGS = load_settings()
