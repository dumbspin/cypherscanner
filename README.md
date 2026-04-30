# Telegram Phishing Detection + Reporting Bot

This project contains:
- A **Telegram bot** (`bot/bot.py`) for URL checking and incident reporting
- A **FastAPI backend** (`api/main.py`) that analyzes URLs and stores reports
- A **MongoDB database** (configured via `MONGODB_URI`; `DATABASE_URL` also works for back-compat)

## Project structure

```
bot/
  bot.py
api/
  main.py
db/
  models.py
utils/
  url_analyzer.py
```

## Setup (Windows / PowerShell)

Create a virtualenv and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configure environment variables

Set your bot token:

```powershell
$env:TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
```

Optional settings:

```powershell
$env:API_BASE_URL="http://127.0.0.1:8000"
$env:MONGODB_URI="mongodb://127.0.0.1:27017/phishbot"
# Optional (overrides the DB name inside the URI):
$env:MONGODB_DB="phishbot"
$env:EXTERNAL_ANALYZER_BASE_URL="https://url-phishing-1-y18x.onrender.com"
$env:EXTERNAL_ANALYZER_TIMEOUT_SEC="45"
$env:LOG_LEVEL="INFO"
```

## Run the backend API

```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

API endpoints:
- `POST /check-url`
- `POST /report`
- `GET /hotspots`

Example:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/check-url -ContentType "application/json" -Body '{"url":"https://example.com"}'
```

## Run the Telegram bot

In a second terminal (keep the API running):

```powershell
python -m bot.bot
```

Commands:
- `/start`
- `/check <url>`
- `/report` (interactive; use `/cancel` to abort)

## Notes

- **Rate limiting**: Both API and bot include a basic in-memory limiter as a placeholder. Replace with Redis/API gateway for production.
- **URL analysis**: Rule-based heuristics in `utils/url_analyzer.py` (length, `@`, subdomain depth, HTTPS, IP hosts, punycode).
- **Database**: Stored in MongoDB collection `reports` (`db/models.py`).

