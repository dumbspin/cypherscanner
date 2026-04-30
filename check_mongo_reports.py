from __future__ import annotations

from datetime import timezone
from urllib.parse import urlparse

from dotenv import load_dotenv
import os

from pymongo import MongoClient

from db.models import _default_db_name


def main() -> None:
    load_dotenv()
    uri = os.getenv("MONGODB_URI") or os.getenv("DATABASE_URL")
    if not uri:
        print("No MONGODB_URI or DATABASE_URL set.")
        return

    safe_uri_prefix = uri.split("@")[0] + "@..."
    print("Using URI:", safe_uri_prefix)

    db_name = _default_db_name(uri)
    print("DB name:", db_name)
    collection = os.getenv("MONGODB_COLLECTION", "reports")
    print("Collection:", collection)

    client = MongoClient(uri)
    col = client[db_name][collection]

    count = col.count_documents({})
    print("Total documents in collection:", count)

    print("Most recent 5 reports:")
    for doc in col.find().sort("timestamp", -1).limit(5):
        print(
            {
                "url": doc.get("url"),
                "user_id": doc.get("user_id"),
                "timestamp": doc.get("timestamp"),
                "location": doc.get("location"),
            }
        )


if __name__ == "__main__":
    main()

