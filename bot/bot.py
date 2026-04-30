from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import html
from typing import Optional

import requests
from dotenv import load_dotenv
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from utils.url_analyzer import UrlValidationError, classify_message, normalize_url
from utils.external_checker import ExternalCheckerError, analyze_via_external_service


# Load repo-root .env explicitly (prevents accidentally loading other apps' .env files).
_ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(_ENV_PATH, override=True)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("phish-bot")

logger.info("Loaded env file: %s", _ENV_PATH)


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
HTTP_TIMEOUT_SEC = float(os.getenv("HTTP_TIMEOUT_SEC", "10"))


REPORT_URL, REPORT_DESC, REPORT_LOCATION = range(3)

URL_RE = re.compile(r"(https?://[^\s<>()]+|www\.[^\s<>()]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s<>()]*)")


class BotRateLimiter:
    """
    Basic in-memory rate limiting placeholder.
    Replace with Redis / persistent storage for production.
    """

    def __init__(self, *, limit: int = 20, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds
        hits = [t for t in self._hits.get(key, []) if t >= window_start]
        if len(hits) >= self.limit:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True


rate_limiter = BotRateLimiter(
    limit=int(os.getenv("BOT_RATE_LIMIT", "30")),
    window_seconds=int(os.getenv("BOT_RATE_WINDOW_SEC", "60")),
)


def _status_emoji(status: str) -> str:
    status = (status or "").lower()
    if status == "safe":
        return "✅"
    if status == "suspicious":
        return "🟠"
    if status == "malicious":
        return "🚫"
    return "❓"

def _truncate(text: str, limit: int = 3500) -> str:
    # Telegram message limit is 4096 chars; keep some headroom for formatting.
    if text is None:
        return ""
    text = str(text)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _format_result_html(status: str, reason: str) -> str:
    emoji = _status_emoji(status)
    status_esc = html.escape(str(status))
    reason_esc = html.escape(_truncate(reason))
    msg = f"{emoji} <b>Status</b>: <code>{status_esc}</code>\n<b>Reason</b>: {reason_esc}"

    # Keep impact text short enough for Telegram limits, but concrete.
    st = str(status).lower()
    if st in ("suspicious", "malicious"):
        if st == "suspicious":
            impact = (
                "⚠️ <b>Potential impact</b> (if this is a threat):\n"
                "- Credential theft (passwords/OTP)\n"
                "- Account takeover / fraud attempts\n"
                "- Redirects to fake login or payment pages\n"
                "- Malware or unwanted downloads (possible)\n"
                "\n<b>Recommendation:</b> Do NOT click or enter any passwords/OTP."
            )
        else:
            impact = (
                "⚠️ <b>Possible damages</b> (high risk):\n"
                "- Malware infection (spyware/ransomware possible)\n"
                "- Stealing login details and financial information\n"
                "- Unauthorized actions, transfers, or account lockouts\n"
                "- Browser/device compromise and further phishing\n"
                "\n<b>Recommendation:</b> Do NOT proceed. If you already opened it, avoid entering any credentials and run antivirus."
            )
        msg += f"\n\n{impact}"

    return msg


def _bilingual(en: str, hi: str) -> str:
    # Keep it simple: English first, then Hindi.
    return f"{en}\n\n{hi}"


def _trilingual(en: str, hi: str, gh: str) -> str:
    # English + Hindi + Garhwali (Devanagari), simple/common phrasing.
    return f"{en}\n\n{hi}\n\n{gh}"


async def _send_result(
    update: Update,
    *,
    status: str,
    reason: str,
    screenshot_url: Optional[str] = None,
    include_preview: bool = True,
) -> None:
    """
    Send analyzer result. If screenshot_url is present and include_preview=True,
    send it as a photo with caption; otherwise send text.
    """
    msg = _format_result_html(status, reason)

    if screenshot_url and include_preview and update.message:
        try:
            await update.message.reply_photo(
                photo=screenshot_url,
                caption=msg,
                parse_mode=ParseMode.HTML,
            )
            return
        except Exception:
            logger.exception("Failed to send screenshot photo; falling back to text")

    if update.message:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, disable_web_page_preview=False)


async def _post_json(path: str, payload: dict) -> dict:
    url = f"{API_BASE_URL}{path}"

    def _do() -> dict:
        r = requests.post(url, json=payload, timeout=HTTP_TIMEOUT_SEC)
        r.raise_for_status()
        return r.json()

    return await asyncio.to_thread(_do)


async def _analyze_url(url: str) -> dict:
    # Run blocking external call in a thread.
    return await asyncio.to_thread(analyze_via_external_service, url)


def _extract_first_url(text: str) -> Optional[str]:
    if not text:
        return None
    m = URL_RE.search(text)
    if not m:
        return None
    return m.group(0).strip(".,)];\"'")

def _is_url_only_message(message_text: str, extracted: str) -> bool:
    """
    True when user pasted just a URL (or URL with minor punctuation),
    so we should use the external analyzer.
    """
    if not message_text or not extracted:
        return False
    t = message_text.strip()
    # Remove surrounding punctuation and compare.
    cleaned = t.strip().strip(".,)];\"'").strip()
    return cleaned == extracted or cleaned == extracted.strip()


def _rl_ok(update: Update) -> bool:
    user = update.effective_user
    key = str(user.id) if user else "unknown"
    return rate_limiter.allow(key)

async def _auto_report(update: Update, *, url: str, description: Optional[str]) -> None:
    user = update.effective_user
    user_id = str(user.id) if user else "unknown"
    payload = {
        "url": url,
        "description": description,
        "user_id": user_id,
        "latitude": None,
        "longitude": None,
    }
    await _post_json("/report", payload)

async def _auto_report_with_location(
    update: Update, *, url: str, description: Optional[str], latitude: float, longitude: float
) -> None:
    user = update.effective_user
    user_id = str(user.id) if user else "unknown"
    payload = {
        "url": url,
        "description": description,
        "user_id": user_id,
        "latitude": latitude,
        "longitude": longitude,
    }
    await _post_json("/report", payload)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _rl_ok(update):
        await update.message.reply_text(
            _trilingual(
                "Rate limit exceeded. Please wait a bit and try again.",
                "Rate limit हो गया है। कृपया थोड़ी देर बाद फिर कोशिश करें।",
                "Rate limit बणि गे छ। थोड़ देर रुका, फेर कोशिश कर।",
            )
        )
        return

    text = _trilingual(
        "Welcome to the Phishing Detection & Reporting Bot.\n\n"
        "Available commands:\n"
        "- /check <url> — check a URL\n"
        "- /report — report a phishing URL (interactive)\n"
        "- Or simply paste a URL/message — I will analyze it\n"
        "- /start — show this help\n\n"
        "Tip: Always be cautious with links from unknown sources.",
        "Phishing Detection & Reporting Bot में आपका स्वागत है।\n\n"
        "Available commands:\n"
        "- /check <url> — URL की जांच करें\n"
        "- /report — phishing URL रिपोर्ट करें (interactive)\n"
        "- या बस URL/मैसेज पेस्ट करें — मैं जांच करूँगा\n"
        "- /start — मदद देखें\n\n"
        "Tip: अज्ञात लिंक पर क्लिक करने से पहले सावधान रहें।",
        "Phishing Detection & Reporting Bot मा तैरा स्वागत छ।\n\n"
        "Commands:\n"
        "- /check <url> — URL चेक कर\n"
        "- /report — phishing URL रिपोर्ट कर (interactive)\n"
        "- या बस URL/मैसेज पेस्ट कर — मैं जांच करुँल\n"
        "- /start — मदद देख\n\n"
        "सावधान रौ: अनजान लिंक पै क्लिक मत कर।",
    )
    await update.message.reply_text(text)


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _rl_ok(update):
        await update.message.reply_text(
            _trilingual(
                "Rate limit exceeded. Please wait a bit and try again.",
                "Rate limit हो गया है। कृपया थोड़ी देर बाद फिर कोशिश करें।",
                "Rate limit बणि गे छ। थोड़ देर रुका, फेर कोशिश कर।",
            )
        )
        return

    if not context.args:
        await update.message.reply_text(
            _trilingual("Usage: /check <url>", "उपयोग: /check <url>", "उपयोग: /check <url>")
        )
        return

    raw_url = " ".join(context.args).strip()
    try:
        url = normalize_url(raw_url)
    except UrlValidationError as e:
        await update.message.reply_text(
            _trilingual(
                f"Invalid URL: {e}",
                f"गलत URL: {e}",
                f"गलत URL: {e}",
            )
        )
        return

    try:
        # Send directly to the analyzer website backend.
        result = await _analyze_url(url)
        status = result.get("status", "unknown")
        reason = result.get("reason", "")
        screenshot_url = result.get("screenshot_url")
        await _send_result(
            update,
            status=status,
            reason=_trilingual(reason, reason, reason),
            screenshot_url=screenshot_url,
            include_preview=True,
        )
    except requests.HTTPError as e:
        logger.warning("check failed: %s", e, exc_info=True)
        await update.message.reply_text(
            _trilingual(
                "Analyzer error while checking the URL. Please try again later.",
                "URL जांचते समय analyzer में समस्या आई। कृपया थोड़ी देर बाद फिर कोशिश करें।",
                "URL चेक करै बखत analyzer मा दिक्कत ऐगी। थोड़ देर बाद फेर कोशिश कर।",
            )
        )
    except ExternalCheckerError as e:
        logger.warning("external analyzer failed: %s", e, exc_info=True)
        await update.message.reply_text(
            _trilingual(
                "Analyzer is unavailable or timed out. Please try again shortly.",
                "Analyzer उपलब्ध नहीं है या timeout हो गया। कृपया थोड़ी देर बाद फिर कोशिश करें।",
                "Analyzer मिलणु नि या timeout भै गे। थोड़ देर बाद फेर कोशिश कर।",
            )
        )
    except Exception:
        logger.exception("check crashed")
        await update.message.reply_text(
            _trilingual(
                "Unexpected error while checking. Please try again later.",
                "जांच के दौरान अनपेक्षित समस्या आई। कृपया बाद में फिर कोशिश करें।",
                "जांच मा अनजानी दिक्कत ऐगी। बाद मा फेर कोशिश कर।",
            )
        )


async def auto_check_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # If user pastes a URL or a message containing URL, analyze appropriately.
    if not _rl_ok(update):
        return

    # If we are waiting for location/skip from a previous malicious detection,
    # consume this message as the report continuation.
    if context.user_data.get("pending_auto_report"):
        await handle_pending_auto_report(update, context)
        return
    text = (update.message.text or "").strip()
    candidate = _extract_first_url(text)
    if not candidate:
        return
    try:
        url = normalize_url(candidate)
    except UrlValidationError:
        return

    try:
        # If message is just a URL -> external analyzer.
        # If message contains other text + URL -> local rule-based message classifier.
        if _is_url_only_message(text, candidate):
            result = await _analyze_url(url)
            status = result.get("status", "unknown")
            reason = result.get("reason", "")
            screenshot_url = result.get("screenshot_url")

            await _send_result(
                update,
                status=status,
                reason=_trilingual(reason, reason, reason),
                screenshot_url=screenshot_url,
                include_preview=True,
            )
            return
        else:
            result = classify_message(text, url)

            # If locally detected as fraudulent (malicious), ask for location then auto-report.
            status_local = str(result.get("status", "")).lower()
            if status_local == "malicious":
                # Store pending report and request user's location.
                context.user_data["pending_auto_report"] = {
                    "url": url,
                    "description": f"Auto-reported from message: {text[:1000]}",
                }

                kb = ReplyKeyboardMarkup(
                    [[KeyboardButton("Share location", request_location=True)], [KeyboardButton("skip")]],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                )
                await update.message.reply_text(
                    _format_result_html(
                        "malicious",
                        _trilingual(
                            (result.get("reason", "") + " Please share your location to submit the report.").strip(),
                            (result.get("reason", "") + " रिपोर्ट भेजने के लिए कृपया अपनी location साझा करें।").strip(),
                            (result.get("reason", "") + " रिपोर्ट भेजण ला आपणी location साझा कर।").strip(),
                        ),
                    ),
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                    disable_web_page_preview=False,
                )
                return

        status = result.get("status", "unknown")
        reason = result.get("reason", "")
        # If not fraudulent, show a clear safe message tone.
        if str(status).lower() == "safe":
            reason = reason or "No strong phishing signals detected in this message."
            reason = _trilingual(
                "✅ Looks safe. " + reason,
                "✅ यह सुरक्षित लग रहा है। " + reason,
                "✅ ई ठीक लगणु छ। " + reason,
            )
        else:
            reason = _trilingual(reason, reason, reason)
        await _send_result(
            update, status=status, reason=reason, screenshot_url=None, include_preview=False
        )
    except ExternalCheckerError:
        await update.message.reply_text(
            _trilingual(
                "Analyzer is unavailable or timed out. Please try again shortly.",
                "Analyzer उपलब्ध नहीं है या timeout हो गया। कृपया थोड़ी देर बाद फिर कोशिश करें।",
                "Analyzer मिलणु नि या timeout भै गे। थोड़ देर बाद फेर कोशिश कर।",
            )
        )
    except Exception:
        logger.exception("auto_check crashed")
        await update.message.reply_text(
            _trilingual(
                "Unexpected error while checking. Please try again later.",
                "जांच के दौरान अनपेक्षित समस्या आई। कृपया बाद में फिर कोशिश करें।",
                "जांच मा अनजानी दिक्कत ऐगी। बाद मा फेर कोशिश कर।",
            )
        )

async def handle_pending_auto_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    If we previously detected a malicious message and asked for location,
    this handler consumes the next message (location or 'skip') and reports it.
    """
    pending = context.user_data.get("pending_auto_report")
    if not pending:
        return

    if not _rl_ok(update):
        return

    url = pending.get("url")
    desc = pending.get("description")
    if not url:
        context.user_data.pop("pending_auto_report", None)
        await update.message.reply_text(
            _trilingual(
                "Session expired. Please paste the message again.",
                "Session समाप्त हो गया। कृपया मैसेज फिर से पेस्ट करें।",
                "Session खतम भै गे। मैसेज फेर पेस्ट कर।",
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # Accept either a Telegram location, or 'skip' (report without location).
    if update.message.location is not None:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        try:
            await _auto_report_with_location(update, url=url, description=desc, latitude=lat, longitude=lon)
            await update.message.reply_text(
                _trilingual(
                    "✅ Report submitted and saved to the database (with location).",
                    "✅ रिपोर्ट भेज दी गई है और डेटाबेस में सेव हो गई (location सहित)।",
                    "✅ रिपोर्ट भै गई, डेटाबेस मा सेव भै गई (location सहित)।",
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
        except Exception:
            logger.exception("auto-report with location failed")
            await update.message.reply_text(
                _trilingual(
                    "Report failed due to backend error. Please try again later.",
                    "Backend error के कारण रिपोर्ट नहीं हो पाई। कृपया बाद में फिर कोशिश करें।",
                    "Backend दिक्कत सै रिपोर्ट नि भै पाई। बाद मा फेर कोशिश कर।",
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
        finally:
            context.user_data.pop("pending_auto_report", None)
        return

    text = (update.message.text or "").strip().lower()
    if text == "skip":
        try:
            await _auto_report(update, url=url, description=desc)
            await update.message.reply_text(
                _trilingual(
                    "✅ Report submitted and saved to the database.",
                    "✅ रिपोर्ट भेज दी गई है और डेटाबेस में सेव हो गई।",
                    "✅ रिपोर्ट भै गई, डेटाबेस मा सेव भै गई।",
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
        except Exception:
            logger.exception("auto-report failed")
            await update.message.reply_text(
                _trilingual(
                    "Report failed due to backend error. Please try again later.",
                    "Backend error के कारण रिपोर्ट नहीं हो पाई। कृपया बाद में फिर कोशिश करें।",
                    "Backend दिक्कत सै रिपोर्ट नि भै पाई। बाद मा फेर कोशिश कर।",
                ),
                reply_markup=ReplyKeyboardRemove(),
            )
        finally:
            context.user_data.pop("pending_auto_report", None)
        return

    await update.message.reply_text(
        _trilingual(
            "Please share location using the button, or type <code>skip</code>.",
            "बटन से location साझा करें या <code>skip</code> लिखें।",
            "बटन सै location साझा कर या <code>skip</code> लिख।",
        ),
        parse_mode=ParseMode.HTML,
    )


async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _rl_ok(update):
        await update.message.reply_text(
            _trilingual(
                "Rate limit exceeded. Please wait a bit and try again.",
                "Rate limit हो गया है। कृपया थोड़ी देर बाद फिर कोशिश करें।",
                "Rate limit बणि गे छ। थोड़ देर रुका, फेर कोशिश कर।",
            )
        )
        return ConversationHandler.END

    context.user_data.clear()
    await update.message.reply_text(
        _trilingual(
            "Send the phishing URL you want to report.",
            "जिस phishing URL को रिपोर्ट करना है, उसे भेजें।",
            "जे phishing URL तैं रिपोर्ट करणा छ, उ भेज।",
        )
    )
    return REPORT_URL


async def report_got_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _rl_ok(update):
        await update.message.reply_text(
            _trilingual(
                "Rate limit exceeded. Please wait a bit and try again.",
                "Rate limit हो गया है। कृपया थोड़ी देर बाद फिर कोशिश करें।",
                "Rate limit बणि गे छ। थोड़ देर रुका, फेर कोशिश कर।",
            )
        )
        return ConversationHandler.END

    raw_url = (update.message.text or "").strip()
    try:
        url = normalize_url(raw_url)
    except UrlValidationError as e:
        await update.message.reply_text(
            _trilingual(
                f"Invalid URL: {e}\n\nPlease send a valid URL (or /cancel).",
                f"गलत URL: {e}\n\nकृपया सही URL भेजें (या /cancel)।",
                f"गलत URL: {e}\n\nठीक URL भेज (या /cancel)।",
            )
        )
        return REPORT_URL

    context.user_data["report_url"] = url
    await update.message.reply_text(
        _trilingual(
            "Optional: add a short description (how you received it, what it looked like).\n"
            "Or type `skip` to submit without a description.",
            "वैकल्पिक: छोटा विवरण लिखें (कैसे मिला, कैसा लगा)।\n"
            "या बिना विवरण के भेजने के लिए `skip` लिखें।",
            "चाहो त छोटो विवरण लिख (किस तरह मिलि, कैस लागी)।\n"
            "या बिना विवरण `skip` लिख।",
        ),
        parse_mode=ParseMode.HTML,
    )
    return REPORT_DESC


async def report_got_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _rl_ok(update):
        await update.message.reply_text(
            _trilingual(
                "Rate limit exceeded. Please wait a bit and try again.",
                "Rate limit हो गया है। कृपया थोड़ी देर बाद फिर कोशिश करें।",
                "Rate limit बणि गे छ। थोड़ देर रुका, फेर कोशिश कर।",
            )
        )
        return ConversationHandler.END

    desc = (update.message.text or "").strip()
    if desc.lower() == "skip":
        desc = None

    url = context.user_data.get("report_url")
    if not url:
        await update.message.reply_text(
            _trilingual(
                "Report session expired. Please run /report again.",
                "रिपोर्ट session समाप्त हो गया। कृपया /report फिर से चलाएँ।",
                "रिपोर्ट session खतम भै गे। /report फेर चलै।",
            )
        )
        return ConversationHandler.END

    context.user_data["report_desc"] = desc

    # Ask for location with a one-tap button. User can type "skip" as well.
    kb = ReplyKeyboardMarkup(
        [[KeyboardButton("Share location", request_location=True)], [KeyboardButton("skip")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        _trilingual(
            "Please share your location (optional). This helps us map phishing hotspots.\n"
            "Tap <b>Share location</b> or type <code>skip</code>.",
            "कृपया अपनी location साझा करें (वैकल्पिक)। इससे phishing hotspots मैप करने में मदद मिलती है।\n"
            "<b>Share location</b> दबाएँ या <code>skip</code> लिखें।",
            "अपणी location साझा कर (चाहो त)। ई phishing hotspots मैप करणा मा मदद करदू।\n"
            "<b>Share location</b> दबा या <code>skip</code> लिख।",
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return REPORT_LOCATION


async def report_got_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _rl_ok(update):
        await update.message.reply_text(
            _trilingual(
                "Rate limit exceeded. Please wait a bit and try again.",
                "Rate limit हो गया है। कृपया थोड़ी देर बाद फिर कोशिश करें।",
                "Rate limit बणि गे छ। थोड़ देर रुका, फेर कोशिश कर।",
            )
        )
        return ConversationHandler.END

    url = context.user_data.get("report_url")
    desc = context.user_data.get("report_desc")
    if not url:
        await update.message.reply_text(
            _trilingual(
                "Report session expired. Please run /report again.",
                "रिपोर्ट session समाप्त हो गया। कृपया /report फिर से चलाएँ।",
                "रिपोर्ट session खतम भै गे। /report फेर चलै।",
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    user = update.effective_user
    user_id = str(user.id) if user else "unknown"

    lat = None
    lon = None
    if update.message.location is not None:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
    else:
        text = (update.message.text or "").strip().lower()
        if text != "skip":
            await update.message.reply_text(
                _trilingual(
                    "Please share location using the button, or type <code>skip</code>.",
                    "बटन से location साझा करें या <code>skip</code> लिखें।",
                    "बटन सै location साझा कर या <code>skip</code> लिख।",
                ),
                parse_mode=ParseMode.HTML,
            )
            return REPORT_LOCATION

    try:
        payload = {"url": url, "description": desc, "user_id": user_id, "latitude": lat, "longitude": lon}
        await _post_json("/report", payload)
        await update.message.reply_text(
            _trilingual(
                "✅ Success: your phishing report was saved (with location). Thank you, this incident has been reported.",
                "✅ सफल: आपकी phishing रिपोर्ट सेव हो गई (location सहित)। धन्यवाद, घटना रिपोर्ट हो गई।",
                "✅ सफल: तैरी phishing रिपोर्ट सेव भै गई (location सहित)। धन्यवाद, रिपोर्ट भै गई।",
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
    except requests.HTTPError as e:
        logger.warning("report failed: %s", e, exc_info=True)
        await update.message.reply_text(
            _trilingual(
                "Backend error while submitting the report. Please try again later.",
                "रिपोर्ट भेजते समय backend error आया। कृपया बाद में फिर कोशिश करें।",
                "रिपोर्ट भेजणा मा backend दिक्कत ऐगी। बाद मा फेर कोशिश कर।",
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
    except requests.RequestException as e:
        logger.warning("report request failed (connectivity): %s", e, exc_info=True)
        await update.message.reply_text(
            _trilingual(
                f"Could not reach backend API right now. Please ensure the FastAPI server is running at {API_BASE_URL} and try again.\n\nError: {e}",
                f"Backend API तक पहुंच नहीं हो पाई। कृपया FastAPI सर्वर {API_BASE_URL} पर चल रहा है सुनिश्चित करें और फिर कोशिश करें।\n\nError: {e}",
                f"Backend API तक पहुँच नहि भए। कृपया FastAPI server {API_BASE_URL} मा चलत अछि सुनिश्चित करि फेर कोशिश कर।\n\nError: {e}",
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
    except Exception:
        logger.exception("report crashed")
        await update.message.reply_text(
            _trilingual(
                "Unexpected error while submitting. Please try again later.",
                "रिपोर्ट भेजते समय अनपेक्षित समस्या आई। कृपया बाद में फिर कोशिश करें।",
                "रिपोर्ट भेजणा मा अनजानी दिक्कत ऐगी। बाद मा फेर कोशिश कर।",
            ),
            reply_markup=ReplyKeyboardRemove(),
        )

    return ConversationHandler.END


async def report_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        _trilingual("Cancelled.", "रद्द कर दिया।", "रद्द भै गे।"),
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "Missing TELEGRAM_BOT_TOKEN. Set it as an environment variable before running the bot."
        )

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    report_conv = ConversationHandler(
        entry_points=[CommandHandler("report", report_start)],
        states={
            REPORT_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_got_url)],
            REPORT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_got_desc)],
            REPORT_LOCATION: [
                MessageHandler(filters.LOCATION, report_got_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, report_got_location),
            ],
        },
        fallbacks=[CommandHandler("cancel", report_cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(report_conv)
    # If bot asked for location to auto-report a malicious message, accept location updates.
    # (Text replies like "skip" are handled inside `auto_check_message` to avoid intercepting all messages.)
    app.add_handler(MessageHandler(filters.LOCATION, handle_pending_auto_report))
    # Fallback: auto-check URLs pasted as plain messages (added after report flow).
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_check_message))

    logger.info("Bot starting. API_BASE_URL=%s", API_BASE_URL)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

