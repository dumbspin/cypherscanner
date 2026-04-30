import logging
import os
import re
import time
from typing import Optional, cast

import requests
from dotenv import load_dotenv
from flask import Flask, request
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse


load_dotenv()

app = Flask(__name__)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("whatsapp-phish-bot")

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:9000").rstrip("/")
HTTP_TIMEOUT_SEC = float(os.getenv("HTTP_TIMEOUT_SEC", "10"))

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
ENABLE_SIGNATURE_VALIDATION = os.getenv("ENABLE_SIGNATURE_VALIDATION", "false").strip().lower() in (
    "1",
    "true",
    "yes",
)

# URL detection
# Supports:
# - full URLs: http(s)://...
# - "www...."
# - bare domains like example.com/path
URL_RE = re.compile(
    r"(https?://[^\s<>()]+|www\.[^\s<>()]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s<>()]*)",
    re.IGNORECASE,
)

# Text-based phishing keyword detection (case-insensitive)
PHISHING_KEYWORDS = [
    "urgent",
    "verify",
    "blocked",
    "click now",
]


pending_reports: dict[str, dict] = {}
PENDING_TTL_SEC = int(os.getenv("PENDING_TTL_SEC", "600"))  # 10 minutes default

_DB_INITIALIZED = False

# Allow importing the repo-level `db/` package when running this file directly.
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from db.models import get_reports_collection, init_db as init_mongo_db  # noqa: E402


def _now_doc_ts():
    # Keep timezone-aware timestamps consistent with your existing Mongo helpers.
    # (Your FastAPI code uses datetime.now(timezone.utc).)
    import datetime as _dt

    return _dt.datetime.now(_dt.timezone.utc)


def _now_ts() -> float:
    return time.time()


def _extract_first_url(text: str) -> Optional[str]:
    if not text:
        return None
    m = URL_RE.search(text)
    if not m:
        return None
    url = m.group(1).strip()
    # Remove common trailing punctuation that can break URL parsing.
    return url.rstrip(".,);]>\"'")


def _parse_optional_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(cast(str, value).strip())
    except Exception:
        return None


def _keyword_status_and_reason(text: str) -> tuple[str, str]:
    t = (text or "").lower()
    hits = [kw for kw in PHISHING_KEYWORDS if kw in t]
    if not hits:
        return "safe", "No strong phishing keywords detected in your message text."
    # If keywords exist but we didn't find a URL, treat as suspicious.
    return (
        "suspicious",
        "Phishing language detected in your message (keywords: " + ", ".join(sorted(set(hits))) + ").",
    )


def _call_check_url(url: str) -> dict:
    # Existing API expects POST /check-url with JSON: {"url": "<url>"}
    endpoint = f"{API_BASE_URL}/check-url"
    r = requests.post(endpoint, json={"url": url}, timeout=HTTP_TIMEOUT_SEC)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        raise ValueError("Invalid response from /check-url (expected JSON object).")
    status = str(data.get("status", "safe")).strip()
    reason = str(data.get("reason", "")).strip()
    return {"status": status, "reason": reason}


def _ensure_db() -> None:
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return
    init_mongo_db()
    # Optional: helpful uniqueness constraint for WhatsApp "YES" saves.
    try:
        col = get_reports_collection()
        col.create_index("message_sid", unique=True, sparse=True)
    except Exception:
        # Never hard-fail the webhook if Mongo index creation fails.
        logger.exception("Failed to create WhatsApp report indexes (continuing).")
    _DB_INITIALIZED = True


@app.before_request
def _before_request() -> None:
    # Ensure DB schema exists even if running with `flask run`.
    _ensure_db()


def _save_report(
    *,
    message_sid: str,
    from_number: str,
    message_text: str,
    url: str,
    status: str,
    reason: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> None:
    col = get_reports_collection()
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url or "")
        domain = (parsed.hostname or "").lower()
    except Exception:
        domain = ""

    # Store extra WhatsApp-specific fields. Your FastAPI code uses `url/domain/...`
    # for hotspots; extra fields won't break it.
    location = None
    if latitude is not None and longitude is not None:
        location = {"latitude": float(latitude), "longitude": float(longitude)}

    doc = {
        "message_sid": message_sid,
        "from_number": from_number,
        "message_text": message_text,
        "url": url,
        "status": status,
        "reason": reason,
        "domain": domain,
        "timestamp": _now_doc_ts(),
        "location": location,
    }
    col.update_one({"message_sid": message_sid}, {"$setOnInsert": doc}, upsert=True)
    logger.info(
        "Saved WhatsApp report to Mongo message_sid=%s from_number=%s url_domain=%s location=%s",
        message_sid,
        from_number,
        domain,
        "yes" if location is not None else "no",
    )


def _is_yes_reply(body: str) -> bool:
    t = (body or "").strip().lower()
    return t in ("yes", "y", "yeah", "sure")


def _build_response(*, status: str, reason: str, url_present: bool) -> str:
    if status == "suspicious":
        if url_present:
            return (
                "🟠 Suspicious message. Please verify.\n"
                "Reason:\n"
                f"{reason}\n\n"
                "⚠️ Do NOT trust this link.\n\n"
                "Do you want to report this scam? Reply YES.\n"
                "Optional: Share your location (WhatsApp Attach -> Location) before replying YES."
            )
        return "🟠 Suspicious message. Please verify.\nReason:\n" f"{reason}"
    if status == "malicious":
        if url_present:
            return (
                "🔴 Phishing Alert!\n"
                "Reason:\n"
                f"{reason}\n\n"
                "⚠️ Do NOT click this link.\n\n"
                "Do you want to report this scam? Reply YES.\n"
                "Optional: Share your location (WhatsApp Attach -> Location) before replying YES."
            )
        return (
            "🔴 Phishing Alert!\n"
            "Reason:\n"
            f"{reason}\n\n"
            "⚠️ Do NOT click links from this message (URL not detected)."
        )
    return "🟢 Looks safe."


@app.post("/webhook")
def webhook():
    # Twilio sends form-encoded fields.
    from_number = request.form.get("From", "").strip()
    body = request.form.get("Body", "").strip()
    message_sid = request.form.get("MessageSid", "").strip()
    latitude = _parse_optional_float(request.form.get("Latitude"))
    longitude = _parse_optional_float(request.form.get("Longitude"))

    logger.info("Incoming message from=%s sid=%s body=%r", from_number, message_sid, body[:120])

    if not from_number or body is None:
        return ("Missing fields", 400)

    # Optional signature validation (recommended in production).
    if ENABLE_SIGNATURE_VALIDATION:
        if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN):
            logger.warning("Signature validation enabled but TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN missing.")
        else:
            signature = request.headers.get("X-Twilio-Signature", "")
            validator = RequestValidator(TWILIO_AUTH_TOKEN)
            # Full URL is required for Twilio signature verification.
            url = request.url
            # Use the raw form body for validation.
            params = request.form
            try:
                valid = validator.validate(url, params, signature)
            except Exception:
                valid = False
            if not valid:
                logger.warning("Rejected webhook due to invalid signature.")
                return ("Invalid signature", 403)

    # Handle "YES" report confirmation.
    if from_number in pending_reports and (latitude is not None and longitude is not None):
        pending_reports[from_number]["latitude"] = latitude
        pending_reports[from_number]["longitude"] = longitude
        resp = MessagingResponse()
        resp.message("Location received. Reply YES to submit your report.")
        return str(resp)

    if _is_yes_reply(body):
        pending = pending_reports.get(from_number)
        if not pending:
            resp = MessagingResponse()
            resp.message("I don’t have anything pending to report. Please send the scam link/message first.")
            return str(resp)

        if _now_ts() - pending["created_at"] > PENDING_TTL_SEC:
            pending_reports.pop(from_number, None)
            resp = MessagingResponse()
            resp.message("That report request expired. Please send the link again and reply YES.")
            return str(resp)

        url = pending.get("url") or ""
        status = pending.get("status") or "unknown"
        reason = pending.get("reason") or ""
        message_text = pending.get("message_text") or ""
        pending_lat = pending.get("latitude")
        pending_lon = pending.get("longitude")

        try:
            if message_sid:
                _save_report(
                    message_sid=message_sid,
                    from_number=from_number,
                    message_text=message_text,
                    url=url,
                    status=status,
                    reason=reason,
                    latitude=pending_lat,
                    longitude=pending_lon,
                )
            else:
                # Fallback: if MessageSid missing, still attempt save with a synthetic id.
                _save_report(
                    message_sid=f"no-sid-{int(_now_ts())}",
                    from_number=from_number,
                    message_text=message_text,
                    url=url,
                    status=status,
                    reason=reason,
                    latitude=pending_lat,
                    longitude=pending_lon,
                )
        except Exception:
            logger.exception("Failed to save report")
            resp = MessagingResponse()
            resp.message("Thanks. But I couldn’t save your report due to a server error.")
            return str(resp)

        pending_reports.pop(from_number, None)
        resp = MessagingResponse()
        resp.message("Thanks! Your report has been saved. We appreciate your help.")
        return str(resp)

    # Otherwise: classify message.
    text = body
    url = _extract_first_url(text)
    status: str
    reason: str

    try:
        if url:
            api_result = _call_check_url(url)
            status = api_result.get("status", "safe")
            reason = api_result.get("reason", "")
        else:
            status, reason = _keyword_status_and_reason(text)
    except Exception:
        logger.exception("URL analysis failed")
        # Conservative fallback: treat as suspicious if we saw keywords; else safe.
        status, reason = _keyword_status_and_reason(text)
        if status == "safe":
            status = "suspicious"
            reason = "Could not verify the URL right now. Please avoid clicking and verify the source."

    resp_text = _build_response(status=status, reason=reason, url_present=bool(url))
    resp = MessagingResponse()
    resp.message(resp_text)

    # Only set a pending report when we have a URL and the backend flags it as suspicious/malicious.
    # This ensures the "YES" flow can save the URL.
    if status in ("suspicious", "malicious") and url:
        pending_reports[from_number] = {
            "created_at": _now_ts(),
            "url": url,
            "status": status,
            "reason": reason,
            "message_text": text,
            "latitude": latitude,
            "longitude": longitude,
        }

    return str(resp)


@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    logger.info("Starting WhatsApp webhook server on port %s", port)
    app.run(host="0.0.0.0", port=port, debug=False)

