from __future__ import annotations

import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv

# Load .env before importing modules that read env vars.
load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from bot.db.models import add_report, get_db, hotspots, init_db
from utils.external_checker import ExternalCheckerError, analyze_via_external_service
from utils.url_analyzer import UrlValidationError, classify_url, normalize_url


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("phish-api")


app = FastAPI(title="Phishing Detection API", version="1.0.0")

# CORS for local frontend dev (React/Node on 3000, Vite on 5173).
# Override via CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:5173"
cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173").split(
        ","
    )
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CheckUrlIn(BaseModel):
    url: str = Field(..., examples=["https://example.com/login"])


class CheckUrlOut(BaseModel):
    status: str
    reason: str


class ReportIn(BaseModel):
    url: str
    description: Optional[str] = None
    user_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ReportOut(BaseModel):
    ok: bool = True
    message: str = "Thank you, this incident has been reported."


class HotspotsOut(BaseModel):
    top_domains: list[dict]
    top_urls: list[dict]


class ReportLocation(BaseModel):
    lat: float
    lng: float
    url: str
    user_id: str
    timestamp: str
    domain: str


class ReportLocationsOut(BaseModel):
    items: list[ReportLocation]


class SimpleRateLimiter:
    """
    Basic in-memory rate limiter placeholder.

    Notes:
    - Works per-process only (no shared state across workers).
    - Replace with Redis / API gateway in production.
    """

    def __init__(self, *, limit: int = 30, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}

    def check(self, key: str) -> None:
        now = time.time()
        window_start = now - self.window_seconds
        hits = self._hits.get(key, [])
        hits = [t for t in hits if t >= window_start]
        if len(hits) >= self.limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
        hits.append(now)
        self._hits[key] = hits


rate_limiter = SimpleRateLimiter(
    limit=int(os.getenv("API_RATE_LIMIT", "60")),
    window_seconds=int(os.getenv("API_RATE_WINDOW_SEC", "60")),
)


def rate_limit_dep(request: Request) -> None:
    # Key by client IP; can also include headers/user id depending on auth.
    client_ip = request.client.host if request.client else "unknown"
    rate_limiter.check(client_ip)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    logger.info("Database initialized.")


@app.post("/check-url", response_model=CheckUrlOut, dependencies=[Depends(rate_limit_dep)])
def check_url(payload: CheckUrlIn) -> CheckUrlOut:
    try:
        url = normalize_url(payload.url)
        try:
            result = analyze_via_external_service(url)
        except ExternalCheckerError as e:
            logger.warning("External analyzer failed: %s", e)
            raise HTTPException(
                status_code=502,
                detail="External phishing analyzer is unavailable or timed out. Try again shortly.",
            ) from e
        return CheckUrlOut(**result)
    except UrlValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("check-url failed")
        raise HTTPException(status_code=500, detail="Internal error") from e


@app.post("/report", response_model=ReportOut, dependencies=[Depends(rate_limit_dep)])
def report(payload: ReportIn, col=Depends(get_db)) -> ReportOut:
    try:
        url = normalize_url(payload.url)
        add_report(
            col,
            url=url,
            description=payload.description,
            user_id=payload.user_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
        )
        return ReportOut()
    except UrlValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("report failed")
        raise HTTPException(status_code=500, detail="Internal error") from e


@app.get("/hotspots", response_model=HotspotsOut, dependencies=[Depends(rate_limit_dep)])
def get_hotspots(col=Depends(get_db)) -> HotspotsOut:
    try:
        data = hotspots(col)
        return HotspotsOut(**data)
    except Exception as e:
        logger.exception("hotspots failed")
        raise HTTPException(status_code=500, detail="Internal error") from e


@app.get("/reports/locations", response_model=ReportLocationsOut, dependencies=[Depends(rate_limit_dep)])
def get_report_locations(col=Depends(get_db)) -> ReportLocationsOut:
    """
    Return all reports that have a stored location, for use on hotspot maps.
    """
    try:
        docs = list(
            col.find(
                {"location": {"$ne": None}},
                {
                    "_id": 0,
                    "url": 1,
                    "user_id": 1,
                    "timestamp": 1,
                    "domain": 1,
                    "location": 1,
                },
            ).sort("timestamp", -1)
        )
        items: list[ReportLocation] = []
        for d in docs:
            loc = d.get("location") or {}
            try:
                items.append(
                    ReportLocation(
                        lat=float(loc.get("latitude")),
                        lng=float(loc.get("longitude")),
                        url=str(d.get("url") or ""),
                        user_id=str(d.get("user_id") or ""),
                        timestamp=str(d.get("timestamp") or ""),
                        domain=str(d.get("domain") or ""),
                    )
                )
            except (TypeError, ValueError):
                continue
        return ReportLocationsOut(items=items)
    except Exception as e:
        logger.exception("get_report_locations failed")
        raise HTTPException(status_code=500, detail="Internal error") from e

