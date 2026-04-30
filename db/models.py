from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Generator, Optional
from urllib.parse import urlparse

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


def _default_mongo_uri() -> str:
    # Preferred env var: MONGODB_URI
    # Back-compat: DATABASE_URL (if you already set it to a mongodb+srv URI)
    return os.getenv("MONGODB_URI") or os.getenv("DATABASE_URL", "mongodb://127.0.0.1:27017/phishbot")


def _default_db_name(mongo_uri: str) -> str:
    # If URI includes /dbname use it; else allow override via MONGODB_DB; else "phishbot".
    override = os.getenv("MONGODB_DB")
    if override:
        return override

    try:
        parsed = urlparse(mongo_uri)
        # For mongodb URIs, path is like "/hackathon"
        name = (parsed.path or "").lstrip("/")
        return name or "phishbot"
    except Exception:
        return "phishbot"
_client: Optional[MongoClient] = None


def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        # Important: read env lazily so .env loading order doesn't matter.
        mongo_uri = _default_mongo_uri()
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    return _client


def get_database() -> Database:
    mongo_uri = _default_mongo_uri()
    db_name = _default_db_name(mongo_uri)
    return get_mongo_client()[db_name]


def get_reports_collection() -> Collection:
    collection = os.getenv("MONGODB_COLLECTION", "reports")
    return get_database()[collection]


def init_db() -> None:
    # Create helpful indexes. Safe to call multiple times.
    col = get_reports_collection()
    col.create_index([("domain", ASCENDING)])
    col.create_index([("url", ASCENDING)])
    col.create_index([("timestamp", DESCENDING)])
    col.create_index([("user_id", ASCENDING)])
    col.create_index([("location", ASCENDING)])


def get_db() -> Generator[Collection, None, None]:
    # FastAPI dependency that yields the reports collection.
    col = get_reports_collection()
    try:
        yield col
    finally:
        # MongoClient is intended to be reused; do not close per-request.
        pass


def add_report(
    col: Collection,
    *,
    url: str,
    description: Optional[str],
    user_id: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> dict:
    parsed = urlparse(url)
    domain = (parsed.hostname or "").lower()
    location = None
    if latitude is not None and longitude is not None:
        location = {"latitude": float(latitude), "longitude": float(longitude)}
    doc = {
        "url": url,
        "domain": domain,
        "description": description,
        "user_id": str(user_id),
        "timestamp": datetime.now(timezone.utc),
        "location": location,
    }
    res = col.insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


def hotspots(col: Collection, *, top_n: int = 10) -> dict:
    # Aggregate top domains and top URLs.
    top_domains = list(
        col.aggregate(
            [
                {"$match": {"domain": {"$ne": ""}}},
                {"$group": {"_id": "$domain", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": int(top_n)},
                {"$project": {"_id": 0, "domain": "$_id", "count": 1}},
            ]
        )
    )

    top_urls = list(
        col.aggregate(
            [
                {"$group": {"_id": "$url", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": int(top_n)},
                {"$project": {"_id": 0, "url": "$_id", "count": 1}},
            ]
        )
    )
    return {"top_domains": top_domains, "top_urls": top_urls}

