from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


class UrlValidationError(ValueError):
    pass


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise UrlValidationError("URL is required.")

    # If user sends "example.com/path", try to be helpful.
    if not _URL_RE.match(url):
        url = "http://" + url

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UrlValidationError("Only http/https URLs are supported.")
    if not parsed.netloc:
        raise UrlValidationError("URL must include a hostname.")
    if parsed.username or parsed.password:
        # Presence of @ in userinfo is a classic trick; still allow but flag in analysis.
        pass

    # Basic hostname sanity (not full RFC, but blocks obvious garbage).
    host = (parsed.hostname or "").strip().lower()
    if not host or "." not in host:
        raise UrlValidationError("Hostname looks invalid.")
    return url


@dataclass(frozen=True)
class UrlFeatures:
    url_length: int
    has_at: bool
    has_hyphen: bool
    dot_count: int
    is_https: bool
    has_ip_host: bool
    has_punycode: bool


def _is_ip(host: str) -> bool:
    # Very small IP heuristic (IPv4 only) to keep dependencies minimal.
    parts = host.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def extract_features(url: str) -> UrlFeatures:
    parsed = urlparse(url)
    host = (parsed.hostname or "")
    return UrlFeatures(
        url_length=len(url),
        has_at="@" in url,
        has_hyphen="-" in host,
        dot_count=host.count("."),
        is_https=(parsed.scheme.lower() == "https"),
        has_ip_host=_is_ip(host),
        has_punycode=("xn--" in host.lower()),
    )


def classify_url(url: str) -> dict:
    """
    Simple rule-based classifier returning:
      {"status": "safe"|"suspicious"|"malicious", "reason": "..."}
    """
    url = normalize_url(url)
    f = extract_features(url)

    score = 0
    reasons: list[str] = []

    if f.url_length >= 120:
        score += 2
        reasons.append("Unusually long URL.")
    elif f.url_length >= 80:
        score += 1
        reasons.append("Long URL.")

    if f.has_at:
        score += 3
        reasons.append("Contains '@' which can hide the real destination.")

    if f.has_ip_host:
        score += 3
        reasons.append("Uses an IP address instead of a domain name.")

    if f.dot_count >= 4:
        score += 2
        reasons.append("Many subdomains (multiple dots) can be used to spoof brands.")
    elif f.dot_count == 3:
        score += 1
        reasons.append("Multiple subdomains.")

    if f.has_hyphen:
        score += 1
        reasons.append("Hyphenated domain (often used for lookalikes).")

    if f.has_punycode:
        score += 2
        reasons.append("Punycode domain (possible homograph attack).")

    if not f.is_https:
        score += 1
        reasons.append("Not using HTTPS.")

    if score >= 7:
        status = "malicious"
    elif score >= 3:
        status = "suspicious"
    else:
        status = "safe"

    reason = " ".join(reasons) if reasons else "No obvious phishing indicators found."
    return {"status": status, "reason": reason}


_PHISHING_KEYWORDS = {
    "urgent": 2,
    "immediately": 2,
    "verify": 2,
    "verification": 2,
    "suspended": 3,
    "blocked": 2,
    "locked": 2,
    "security alert": 2,
    "account": 1,
    "login": 1,
    "password": 2,
    "otp": 3,
    "one time password": 3,
    "refund": 2,
    "kyc": 2,
    "bank": 1,
    "pay": 1,
    "payment": 1,
    "upi": 2,
    "invoice": 2,
    "claim": 2,
    "winner": 3,
    "prize": 3,
    "click": 1,
    "tap": 1,
    "link": 1,
}


def classify_message(text: str, url: str) -> dict:
    """
    Rule-based message classifier that uses BOTH:
    - URL heuristics (classify_url)
    - message/social-engineering heuristics (keywords/urgency)

    Returns the same shape:
      {"status": "safe"|"suspicious"|"malicious", "reason": "..."}
    """
    msg = (text or "").strip().lower()

    url_result = classify_url(url)
    score = 0
    reasons: list[str] = []

    # Start from URL result severity as baseline.
    if url_result["status"] == "malicious":
        score += 4
        reasons.append("URL indicators look strongly suspicious.")
    elif url_result["status"] == "suspicious":
        score += 2
        reasons.append("URL indicators look suspicious.")

    # Keyword scoring
    kw_hits = []
    for kw, pts in _PHISHING_KEYWORDS.items():
        if kw in msg:
            score += pts
            kw_hits.append(kw)

    if kw_hits:
        reasons.append("Message contains phishing language: " + ", ".join(sorted(set(kw_hits))[:8]) + ".")

    # Extra social engineering patterns
    if "http" in msg and ("@" in msg or "free" in msg):
        score += 1

    if score >= 7:
        status = "malicious"
    elif score >= 3:
        status = "suspicious"
    else:
        status = "safe"

    reason = " ".join(reasons) if reasons else "No strong phishing signals in message text."
    return {"status": status, "reason": reason}

