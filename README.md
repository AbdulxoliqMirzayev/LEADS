# BeTrader Lead Bot

Telegram lead yig'ish boti. Bot foydalanuvchidan til, ism, investitsiya summasi, risk turi, telefon raqami va manbani yig'adi. Leadlar SQLite va Google Sheetsga yoziladi, admin panel orqali status yangilanadi.

## Local run

```powershell
cd C:\LEADS
.\.venv\Scripts\Activate.ps1
python .\betrader_bot\main.py
```

## Railway

Railway start command:

```bash
python betrader_bot/main.py
```

Kerakli environment variables:

```env
TELEGRAM_BOT_TOKEN=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4
ADMIN_IDS=8618220454
DB_PATH=betrader.sqlite3
GOOGLE_SHEETS_SPREADSHEET_ID=
GOOGLE_SHEETS_WORKSHEET=Leads
GOOGLE_SERVICE_ACCOUNT_JSON=
TIMEZONE=Asia/Tashkent
DAILY_REPORT_HOUR=20
DAILY_REPORT_MINUTE=0
```

Railwayda Google Sheets uchun `GOOGLE_SERVICE_ACCOUNT_JSON` ga service account JSON mazmunini to'liq bitta env value sifatida qo'ying. Lokal ishlatishda `GOOGLE_SERVICE_ACCOUNT_FILE=baracap-ac2298016b85.json` ishlatilishi mumkin, lekin JSON fayl GitHubga yuklanmaydi.
