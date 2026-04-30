from __future__ import annotations

import os
from typing import Any

import requests


DEFAULT_EXTERNAL_ANALYZER_BASE = "https://url-phishing-1-y18x.onrender.com"


class ExternalCheckerError(RuntimeError):
    pass


def analyze_via_external_service(url: str) -> dict:
    """
    Calls external phishing analyzer and maps its response to:
      {"status": "safe"|"suspicious"|"malicious", "reason": "string"}

    External service is expected to implement POST {base}/analyze with JSON:
      {"url": "<url>"}
    """
    base = os.getenv("EXTERNAL_ANALYZER_BASE_URL", DEFAULT_EXTERNAL_ANALYZER_BASE).rstrip("/")
    # Render free-tier apps may cold-start; default to a more forgiving timeout.
    timeout = float(os.getenv("EXTERNAL_ANALYZER_TIMEOUT_SEC", "45"))
    endpoint = f"{base}/analyze"

    try:
        r = requests.post(endpoint, json={"url": url}, timeout=timeout)
    except requests.RequestException as e:
        raise ExternalCheckerError(f"Failed to reach external analyzer: {e}") from e

    if not r.ok:
        # Try to surface useful error details.
        detail = None
        try:
            j = r.json()
            detail = j.get("detail") if isinstance(j, dict) else None
        except Exception:
            detail = None
        msg = f"External analyzer returned {r.status_code}"
        if detail:
            msg += f": {detail}"
        raise ExternalCheckerError(msg)

    data: Any = r.json()
    if not isinstance(data, dict):
        raise ExternalCheckerError("External analyzer response was not JSON object.")

    risk_score = data.get("risk_score")
    classification = str(data.get("classification") or "").strip() or "Unknown"
    screenshot_url = str(data.get("screenshot_url") or "").strip()
    blacklisted = bool(data.get("blacklisted", False))
    reasons = data.get("reasons") if isinstance(data.get("reasons"), list) else []

    # Map score -> status (per external project's README).
    try:
        score_int = int(risk_score)
    except Exception:
        score_int = None

    if score_int is None:
        status = "suspicious"
    elif score_int >= 60:
        status = "malicious"
    elif score_int >= 30:
        status = "suspicious"
    else:
        status = "safe"

    # Build a compact explanation for the bot UI.
    parts: list[str] = []
    if score_int is not None:
        parts.append(f"Score: {score_int}/100 ({classification}).")
    else:
        parts.append(f"Classification: {classification}.")

    if blacklisted:
        parts.append("Blacklisted: yes.")

    if reasons:
        top = []
        for item in reasons[:3]:
            if isinstance(item, dict):
                reason = str(item.get("reason") or "").strip()
                module = str(item.get("module") or "").strip()
                if module and reason:
                    top.append(f"{module}: {reason}")
                elif reason:
                    top.append(reason)
        if top:
            parts.append("Top findings: " + " | ".join(top))

    if screenshot_url:
        parts.append(f"Screenshot: {screenshot_url}")

    return {
        "status": status,
        "reason": " ".join(parts).strip() or "No details provided.",
        "screenshot_url": screenshot_url or None,
    }

