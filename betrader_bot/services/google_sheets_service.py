from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from config import SETTINGS
from db import get_google_sheet_uid

logger = logging.getLogger(__name__)

SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)

HEADER = [
    "Sana",
    "Til",
    "Ism",
    "Telefon",
    "Telegram username",
    "Risk turi",
    "Investitsiya summasi",
    "Qayerdan eshitdi",
    "Holati",
]

STATUS_LABELS = {
    "new": "🆕 Yangi",
    "called": "✅ Gaplashildi",
    "no_answer": "📵 Telefon ko'tarmadi",
}

RISK_LABELS = {
    "halol": "🟢 Halol",
    "konservativ": "🟡 Konservativ",
    "yuqori": "🔴 Yuqori daromadli",
}

LANG_LABELS = {
    "uz": "🇺🇿 O'zbek",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}


def _worksheet_name() -> str:
    return SETTINGS.GOOGLE_SHEETS_WORKSHEET or "Leads"


def _service():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    if SETTINGS.GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials = Credentials.from_service_account_info(
            json.loads(SETTINGS.GOOGLE_SERVICE_ACCOUNT_JSON),
            scopes=SCOPES,
        )
    elif SETTINGS.GOOGLE_SERVICE_ACCOUNT_FILE:
        credentials = Credentials.from_service_account_file(
            SETTINGS.GOOGLE_SERVICE_ACCOUNT_FILE,
            scopes=SCOPES,
        )
    else:
        raise RuntimeError("Google service account sozlanmagan.")

    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def _ensure_worksheet(service, spreadsheet_id: str) -> None:
    worksheet = _worksheet_name()
    meta = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields="sheets.properties.title",
    ).execute()
    titles = {
        sheet.get("properties", {}).get("title")
        for sheet in meta.get("sheets", [])
    }
    if worksheet in titles:
        return

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": worksheet,
                        }
                    }
                }
            ]
        },
    ).execute()


def _worksheet_id(service, spreadsheet_id: str) -> int | None:
    worksheet = _worksheet_name()
    meta = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields="sheets.properties(sheetId,title)",
    ).execute()
    for sheet in meta.get("sheets", []):
        props = sheet.get("properties", {})
        if props.get("title") == worksheet:
            return props.get("sheetId")
    return None


def _format_sheet(service, spreadsheet_id: str) -> None:
    sheet_id = _worksheet_id(service, spreadsheet_id)
    if sheet_id is None:
        return

    header_colors = [
        {"red": 0.89, "green": 0.95, "blue": 1.00},  # Sana
        {"red": 0.86, "green": 0.91, "blue": 1.00},  # Til
        {"red": 0.82, "green": 0.89, "blue": 1.00},  # Ism
        {"red": 1.00, "green": 0.86, "blue": 0.86},  # Telefon
        {"red": 0.91, "green": 0.88, "blue": 1.00},  # Telegram username
        {"red": 1.00, "green": 0.94, "blue": 0.80},  # Risk turi
        {"red": 0.86, "green": 0.96, "blue": 0.86},  # Investitsiya summasi
        {"red": 0.92, "green": 0.92, "blue": 0.92},  # Qayerdan eshitdi
        {"red": 1.00, "green": 0.90, "blue": 0.76},  # Holati
    ]
    column_widths = [170, 140, 170, 175, 210, 145, 230, 190, 170]

    requests: list[dict[str, Any]] = []
    for index, color in enumerate(header_colors):
        requests.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": index,
                        "endColumnIndex": index + 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color,
                            "textFormat": {"bold": True},
                            "horizontalAlignment": "CENTER",
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
                }
            }
        )

    requests.append(
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": len(HEADER),
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                        "textFormat": {"bold": False},
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat.bold,horizontalAlignment,verticalAlignment)",
            }
        }
    )

    for index, width in enumerate(column_widths):
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": index,
                        "endIndex": index + 1,
                    },
                    "properties": {"pixelSize": width},
                    "fields": "pixelSize",
                }
            }
        )

    requests.extend(
        [
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": 0,
                        "endIndex": 1,
                    },
                    "properties": {"pixelSize": 28},
                    "fields": "pixelSize",
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": 1,
                    },
                    "properties": {"pixelSize": 26},
                    "fields": "pixelSize",
                }
            },
        ]
    )

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()


def _lead_row(user: dict[str, Any]) -> list[Any]:
    username = user.get("username") or ""
    if username and not str(username).startswith("@"):
        username = f"@{username}"

    amount = user.get("amount")
    amount_txt = f"{int(amount):,} USD".replace(",", " ") if amount is not None else ""
    risk = RISK_LABELS.get(user.get("risk_profile") or "", user.get("risk_profile") or "")
    status = STATUS_LABELS.get(user.get("lead_status") or "", user.get("lead_status") or "")
    lang = LANG_LABELS.get(user.get("lang") or "", user.get("lang") or "")

    return [
        _format_datetime(user.get("created_at") or ""),
        lang,
        user.get("name") or "",
        user.get("phone") or "",
        username,
        risk,
        amount_txt,
        user.get("source") or "",
        status,
    ]


def _format_datetime(value: str) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
        dt = dt.astimezone(ZoneInfo(SETTINGS.TIMEZONE))
        return dt.strftime("%d.%m.%Y %H:%M da")
    except Exception:
        return value


def _ensure_header(values_api, spreadsheet_id: str) -> list[list[Any]]:
    range_name = f"{_worksheet_name()}!A:I"
    current = values_api.get(
        spreadsheetId=spreadsheet_id,
        range=range_name,
    ).execute().get("values", [])

    if current and current[0] == HEADER:
        return current

    values_api.update(
        spreadsheetId=spreadsheet_id,
        range=f"{_worksheet_name()}!A1:I1",
        valueInputOption="RAW",
        body={"values": [HEADER]},
    ).execute()
    values_api.clear(
        spreadsheetId=spreadsheet_id,
        range=f"{_worksheet_name()}!J:Z",
    ).execute()
    return values_api.get(
        spreadsheetId=spreadsheet_id,
        range=range_name,
    ).execute().get("values", [HEADER])


def _sync_lead(user: dict[str, Any]) -> None:
    spreadsheet_id = get_google_sheet_uid()
    if not spreadsheet_id:
        logger.info("Google Sheets sync skipped: GOOGLE_SHEETS_SPREADSHEET_ID is empty.")
        return

    service = _service()
    _ensure_worksheet(service, spreadsheet_id)
    values_api = service.spreadsheets().values()
    current = _ensure_header(values_api, spreadsheet_id)

    phone = str(user.get("phone") or "")
    target_row = None
    for index, row in enumerate(current[1:], start=2):
        phone_new_format = len(row) >= 4 and str(row[3]) == phone
        phone_old_format = len(row) >= 3 and str(row[2]) == phone
        if phone_new_format or phone_old_format:
            target_row = index
            break

    row_values = _lead_row(user)
    if target_row:
        values_api.update(
            spreadsheetId=spreadsheet_id,
            range=f"{_worksheet_name()}!A{target_row}:I{target_row}",
            valueInputOption="RAW",
            body={"values": [row_values]},
        ).execute()
        _format_sheet(service, spreadsheet_id)
        return

    values_api.append(
        spreadsheetId=spreadsheet_id,
        range=f"{_worksheet_name()}!A:I",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [row_values]},
    ).execute()
    _format_sheet(service, spreadsheet_id)


async def sync_lead_to_google_sheet(user: dict[str, Any]) -> bool:
    try:
        await asyncio.to_thread(_sync_lead, user)
        return True
    except Exception:
        logger.exception("Google Sheets sync failed for tg_id=%s", user.get("tg_id"))
        return False
